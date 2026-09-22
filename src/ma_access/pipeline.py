"""Validate source grains, calculate indicators in SQL, and retain uncertainty."""

import csv
import json
import math
from pathlib import Path

import duckdb

from .sources import DO23, FIPS, MD23, PC22, PC23, verify_slices, write_csv


def number(value, moe=False):
    if value is None or str(value).strip() in {"", ".", "NA", "N", "(X)", "**", "***"}:
        return None
    n = float(value)
    if not math.isfinite(n):
        raise ValueError("Non-finite source value")
    if moe and n == -555555555:
        return 0.0  # Census-controlled total: no sampling error.
    if n < 0:
        return None
    return n


def complete_sum(values):
    return None if any(v is None for v in values) else sum(values)


def rss(values):
    return None if any(v is None for v in values) else math.sqrt(sum(v * v for v in values))


def percent_moe(numerator, denominator, num_moe, den_moe):
    if any(x is None for x in [numerator, denominator, num_moe, den_moe]) or denominator <= 0:
        return None
    p = numerator / denominator
    variance = num_moe**2 - p * p * den_moe**2
    if variance < 0:
        variance = num_moe**2 + p * p * den_moe**2
    return 100 * math.sqrt(variance) / denominator


def keyed(rows, key, label):
    result = {}
    for row in rows:
        fips = row[key]
        if fips not in FIPS:
            raise ValueError(f"{label}: incompatible county identifier {fips}")
        if fips in result:
            raise ValueError(f"{label}: duplicate county {fips}")
        result[fips] = row
    if set(result) != set(FIPS):
        raise ValueError(f"{label}: missing counties {sorted(set(FIPS) - set(result))}")
    return result


def load_sources(root):
    raw = Path(root) / "data/raw"

    def read(name):
        with (raw / name).open() as f:
            return list(csv.DictReader(f))

    age = read("ma_b01001.csv")
    poverty = read("ma_b17001.csv")
    for rows in [age, poverty]:
        for r in rows:
            if not r["GEO_ID"].startswith("0500000US") or len(r["GEO_ID"]) != 14:
                raise ValueError("ACS geography is not a county")
            r["fips"] = r["GEO_ID"][9:]
    a = keyed(age, "fips", "age")
    p = keyed(poverty, "fips", "poverty")
    w = keyed(read("ma_workforce.csv"), "fips_st_cnty", "workforce")
    boundaries = json.loads((raw / "ma_counties.geojson").read_text())["features"]
    keyed([f["properties"] for f in boundaries], "fips", "boundaries")
    acs = []
    workforce = []
    for fips in FIPS:
        ar = a[fips]
        pr = p[fips]
        wr = w[fips]
        ages = [f"{i:03}" for i in list(range(20, 26)) + list(range(44, 50))]
        row = dict(
            fips=fips,
            population=number(ar["B01001_E001"]),
            population_moe=number(ar["B01001_M001"], True),
            age65=complete_sum([number(ar["B01001_E" + i]) for i in ages]),
            age65_moe=rss([number(ar["B01001_M" + i], True) for i in ages]),
            poverty_population=number(pr["B17001_E001"]),
            poverty_population_moe=number(pr["B17001_M001"], True),
            poverty=number(pr["B17001_E002"]),
            poverty_moe=number(pr["B17001_M002"], True),
        )
        for n, d in [("age65", "population"), ("poverty", "poverty_population")]:
            if row[n] is not None and row[d] is not None and row[n] > row[d]:
                raise ValueError("Numerator exceeds its universe")
        if row["population"] is None or row["population"] <= 0:
            raise ValueError("Population denominator must be positive")
        acs.append(row)
        wr = dict(
            fips=fips,
            county=wr["cnty_name_st_abbrev"].split(",")[0],
            pcp_2023=number(wr[PC23]),
            pcp_2022=number(wr[PC22]),
            md_2023=number(wr[MD23]),
            do_2023=number(wr[DO23]),
        )
        if (
            all(wr[k] is not None for k in ["pcp_2023", "md_2023", "do_2023"])
            and wr["pcp_2023"] != wr["md_2023"] + wr["do_2023"]
        ):
            raise ValueError("MD plus DO does not reconcile to physician total")
        if any(v is not None and v != int(v) for k, v in wr.items() if k not in {"fips", "county"}):
            raise ValueError("Workforce counts must be integers")
        workforce.append(wr)
    return acs, workforce, boundaries


def build(root, verify=True):
    root = Path(root)
    if verify:
        verify_slices(root)
    acs, workforce, boundaries = load_sources(root)
    out = root / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "acs_clean.csv", acs)
    write_csv(out / "workforce_clean.csv", workforce)
    db = out / "access.duckdb"
    if db.exists():
        db.unlink()
    with duckdb.connect(str(db)) as con:
        for name, file in [("acs", "acs_clean.csv"), ("workforce", "workforce_clean.csv")]:
            con.execute(
                f"CREATE TABLE {name} AS SELECT * FROM read_csv(?, types={{'fips':'VARCHAR'}}, nullstr='')",
                [str(out / file)],
            )
        con.execute((Path(__file__).parent / "sql/indicators.sql").read_text())
        cur = con.execute("SELECT * FROM county_metrics ORDER BY fips")
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, r, strict=False)) for r in cur.fetchall()]
    if len(rows) != 14:
        raise ValueError("Join changed county grain")
    for row in rows:
        row["age65_moe_pp"] = percent_moe(
            row["age65"], row["population"], row["age65_moe"], row["population_moe"]
        )
        row["poverty_moe_pp"] = percent_moe(
            row["poverty"], row["poverty_population"], row["poverty_moe"], row["poverty_population_moe"]
        )
    write_csv(out / "county_indicators.csv", rows)
    checks = dict(
        counties=14,
        expected_fips=list(FIPS),
        unmatched_fips=[],
        duplicate_fips=[],
        geometry_count=14,
        workforce_total_matches_md_plus_do=True,
        missing_by_column={k: sum(r[k] is None for r in rows) for k in rows[0]},
        source_slice_checksums_verified=verify,
    )
    (out / "quality_checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    return rows, boundaries
