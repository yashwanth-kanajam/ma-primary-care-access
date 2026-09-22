import math

import pytest

from ma_access.analysis import benchmarks, quantile, select
from ma_access.pipeline import complete_sum, keyed, number, percent_moe, rss
from ma_access.sources import FIPS


@pytest.mark.parametrize("raw", [None, "", ".", "N", "(X)", "-999999999", "-888888888", "-666666666"])
def test_missing_and_suppressed_counts_do_not_become_zero(raw):
    assert number(raw) is None


def test_controlled_moe_is_zero_but_controlled_sentinel_is_not_a_count():
    assert number("-555555555", moe=True) == 0
    assert number("-555555555") is None
    assert number("0") == 0


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf"])
def test_nonfinite_counts_rejected(raw):
    with pytest.raises(ValueError, match="Non-finite"):
        number(raw)


def test_aggregation_does_not_ignore_missing_cells():
    assert complete_sum([10, None, 20]) is None
    assert rss([3, None]) is None
    assert complete_sum([10, 0, 20]) == 30
    assert rss([3, 4]) == 5


def test_percentage_moe_uses_subset_formula_and_fallback():
    assert percent_moe(20, 100, 5, 10) == pytest.approx(math.sqrt(25 - 4))
    assert percent_moe(50, 100, 1, 10) == pytest.approx(math.sqrt(1 + 25))
    assert percent_moe(20, 100, 5, 0) == 5
    assert percent_moe(20, 0, 5, 0) is None
    assert percent_moe(20, 100, None, 0) is None


def test_quantile_interpolates_and_keeps_ties():
    assert quantile([20, 0, 10, 30], 0.5) == 15
    assert quantile([10, 10, 10], 0.4) == 10
    assert quantile([None, None], 0.5) is None


@pytest.mark.parametrize("defect", ["duplicate", "missing", "state", "tract", "bad_fips"])
def test_geographic_join_rejects_wrong_grain_or_coverage(defect):
    rows = [{"fips": f} for f in FIPS]
    if defect == "duplicate":
        rows.append(rows[0])
    elif defect == "missing":
        rows.pop()
    else:
        rows[0] = {"fips": {"state": "25", "tract": "25001010100", "bad_fips": "25002"}[defect]}
    with pytest.raises(ValueError):
        keyed(rows, "fips", "test source")


def test_selection_boundary_missing_and_context_rules():
    b = {"poverty_pct": 10, "age65_pct": 20}
    r = {"pcp_per_100k": 70, "poverty_pct": 10, "age65_pct": 15, "poverty_moe_pp": 1, "age65_moe_pp": 1}
    assert select(r, b, 80, "pcp_per_100k", "either", 0) is True
    assert select(r, b, 70, "pcp_per_100k", "either", 0) is False  # Strict supply boundary.
    assert select(r, b, 80, "pcp_per_100k", "age", 0) is False
    assert select(r, b, 80, "pcp_per_100k", "either", -1) is False
    r["poverty_pct"] = None
    assert select(r, b, 80, "pcp_per_100k", "either", 0) is None
    assert select(r, b, 60, "pcp_per_100k", "either", 0) is False
    r["pcp_per_100k"] = None
    assert select(r, b, 80, "pcp_per_100k", "either", 0) is None


def test_state_rates_are_denominator_weighted_not_mean_county_rates():
    rows = [
        dict(pcp_2023=1, population=100, poverty=10, poverty_population=100, age65=10),
        dict(pcp_2023=1, population=900, poverty=180, poverty_population=900, age65=180),
    ]
    b = benchmarks(rows)
    assert b == {"pcp_per_100k": 200, "poverty_pct": 19, "age65_pct": 19}
    rows[0]["poverty"] = None
    with pytest.raises(ValueError, match="Incomplete"):
        benchmarks(rows)
