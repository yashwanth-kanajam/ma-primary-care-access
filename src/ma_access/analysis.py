"""Transparent screening rules. Selection frequency is not a probability."""

import json
from pathlib import Path

from .pipeline import complete_sum
from .sources import write_csv


def quantile(values, q):
    values = sorted(x for x in values if x is not None)
    if not values:
        return None
    i = (len(values) - 1) * q
    low = int(i)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (i - low)


def benchmarks(rows):
    def rate(n, d, scale):
        num = complete_sum([r[n] for r in rows])
        den = complete_sum([r[d] for r in rows])
        if num is None or den is None or den <= 0:
            raise ValueError("Incomplete statewide benchmark; resolve missing inputs")
        return scale * num / den

    return dict(
        pcp_per_100k=rate("pcp_2023", "population", 100000),
        poverty_pct=rate("poverty", "poverty_population", 100),
        age65_pct=rate("age65", "population", 100),
    )


SCENARIOS = [
    ("baseline", 0.5, "pcp_per_100k", "either", 0),
    ("stricter_capacity", 0.4, "pcp_per_100k", "either", 0),
    ("broader_capacity", 0.6, "pcp_per_100k", "either", 0),
    ("previous_workforce_year", 0.5, "pcp_2022_per_100k", "either", 0),
    ("poverty_context_only", 0.5, "pcp_per_100k", "poverty", 0),
    ("older_context_only", 0.5, "pcp_per_100k", "age", 0),
    ("context_lower_bounds", 0.5, "pcp_per_100k", "either", -1),
    ("context_upper_bounds", 0.5, "pcp_per_100k", "either", 1),
]


def select(row, benchmark, cutoff, capacity, context, moe_direction):
    keys = (
        ["poverty_pct", "age65_pct"]
        if context == "either"
        else (["poverty_pct"] if context == "poverty" else ["age65_pct"])
    )
    values = []
    for k in keys:
        value = row[k]
        moe = row["poverty_moe_pp" if k == "poverty_pct" else "age65_moe_pp"]
        values.append(
            None
            if value is None or (moe_direction and moe is None)
            else max(0, min(100, value + moe_direction * (moe or 0))) >= benchmark[k]
        )
    # Unknown is not evidence of absence: retain an indeterminate result.
    if row[capacity] is None or cutoff is None:
        return None
    if row[capacity] >= cutoff:
        return False
    if True in values:
        return True
    if None in values:
        return None
    return False


def analyze(rows, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    benchmark = benchmarks(rows)
    records = []
    sets = {}
    thresholds = {}
    statuses = {}
    for name, q, capacity, context, direction in SCENARIOS:
        cutoff = quantile([r[capacity] for r in rows], q)
        thresholds[name] = cutoff
        selected = set()
        for row in rows:
            chosen = select(row, benchmark, cutoff, capacity, context, direction)
            statuses[(name, row["fips"])] = chosen
            records.append(
                dict(
                    fips=row["fips"],
                    county=row["county"],
                    scenario=name,
                    selected=chosen,
                    capacity_cutoff=cutoff,
                )
            )
            if chosen is True:
                selected.add(row["fips"])
        sets[name] = selected
    baseline = sets["baseline"]
    names = {r["fips"]: r["county"] for r in rows}
    summaries = []
    for name, _, _, _, _ in SCENARIOS:
        union = baseline | sets[name]
        summaries.append(
            dict(
                scenario=name,
                selected_count=len(sets[name]),
                shortlist=[names[x] for x in sorted(sets[name])],
                added=[names[x] for x in sorted(sets[name] - baseline)],
                removed=[names[x] for x in sorted(baseline - sets[name])],
                jaccard_to_baseline=len(baseline & sets[name]) / len(union) if union else 1.0,
            )
        )
    core = set.intersection(
        *(sets[n] for n in ["baseline", "stricter_capacity", "broader_capacity", "previous_workforce_year"])
    )
    for row in rows:
        row["baseline_selected"] = statuses[("baseline", row["fips"])]
        row["selected_scenarios"] = sum(row["fips"] in selected for selected in sets.values())
        row["scenario_count"] = len(SCENARIOS)
        row["evaluated_scenarios"] = sum(statuses[(s[0], row["fips"])] is not None for s in SCENARIOS)
        row["capacity_stable"] = row["fips"] in core
        row["screening_group"] = (
            "Indeterminate"
            if row["baseline_selected"] is None
            else "Investigate"
            if row["baseline_selected"]
            else "Not selected"
        )
    result = dict(
        benchmarks=benchmark,
        capacity_cutoffs=thresholds,
        baseline_shortlist=[names[x] for x in sorted(baseline)],
        capacity_stable_shortlist=[names[x] for x in sorted(core)],
        scenarios=summaries,
    )
    write_csv(out / "sensitivity.csv", records)
    (out / "findings.json").write_text(json.dumps(result, indent=2) + "\n")
    write_csv(out / "county_comparison.csv", rows)
    return result
