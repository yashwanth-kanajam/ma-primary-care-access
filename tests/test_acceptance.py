import csv
import json
import shutil
import xml.etree.ElementTree as E
import zipfile
from pathlib import Path

import pytest

from ma_access.analysis import SCENARIOS, analyze
from ma_access.dashboard import data_rows, workbook
from ma_access.pipeline import build
from ma_access.sources import FIPS, verify_slices

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    (tmp_path / "data").mkdir()
    shutil.copytree(
        ROOT / "data/raw",
        tmp_path / "data/raw",
        ignore=shutil.ignore_patterns("*.zip", "*.dat", "acs_shells.txt"),
    )
    shutil.copy(ROOT / "data/source_register.json", tmp_path / "data/source_register.json")
    return tmp_path


def test_source_checksum_detects_tampering(project):
    verify_slices(project)
    with (project / "data/raw/ma_workforce.csv").open("a") as f:
        f.write("\n")
    with pytest.raises(ValueError, match="checksum"):
        verify_slices(project)


def test_actual_metrics_reconcile_to_independent_source_sums(project):
    rows, features = build(project)
    assert [r["fips"] for r in rows] == list(FIPS)
    assert len(features) == 14
    with (project / "data/raw/ma_b01001.csv").open() as f:
        raw = list(csv.DictReader(f))
    assert sum(r["population"] for r in rows) == sum(int(r["B01001_E001"]) for r in raw)
    for r in rows:
        assert r["pcp_2023"] == r["md_2023"] + r["do_2023"]
        assert r["pcp_per_100k"] == pytest.approx(r["pcp_2023"] / r["population"] * 100000)
        assert r["poverty_pct"] == pytest.approx(r["poverty"] / r["poverty_population"] * 100)
        assert 0 <= r["age65_pct"] <= 100
    bristol = next(r for r in rows if r["fips"] == "25005")
    assert bristol["pcp_2023"] == 319
    assert bristol["poverty_population"] != bristol["population"]
    q = json.loads((project / "data/processed/quality_checks.json").read_text())
    assert not any(q["missing_by_column"].values())


def test_sensitivity_results_and_no_scores(project):
    rows, features = build(project)
    result = analyze(rows, project / "analysis")
    assert result["baseline_shortlist"] == ["Bristol", "Dukes", "Essex", "Franklin", "Hampden", "Plymouth"]
    assert result["capacity_stable_shortlist"] == ["Bristol", "Dukes", "Franklin", "Hampden", "Plymouth"]
    assert {r["county"] for r in rows if r["selected_scenarios"] == 8} == {"Franklin", "Hampden"}
    assert (
        next(s for s in result["scenarios"] if s["scenario"] == "poverty_context_only")["jaccard_to_baseline"]
        == 0.5
    )
    assert next(s for s in result["scenarios"] if s["scenario"] == "broader_capacity")["added"] == [
        "Barnstable"
    ]
    assert not next(r for r in rows if r["county"] == "Nantucket")["baseline_selected"]
    assert len(list(csv.DictReader((project / "analysis/sensitivity.csv").open()))) == 14 * len(SCENARIOS)
    assert all("score" not in r for r in rows)


def test_malformed_universes_and_workforce_totals_rejected(project):
    p = project / "data/raw/ma_workforce.csv"
    rows = list(csv.DictReader(p.open()))
    rows[0]["phys_nf_prim_care_pc_exc_rsdt_23"] = "9999"
    from ma_access.sources import write_csv

    write_csv(p, rows)
    with pytest.raises(ValueError, match="reconcile"):
        build(project, verify=False)


def test_map_vertices_cannot_multiply_comparison_metrics(project):
    rows, features = build(project)
    analyze(rows, project / "analysis")
    records = data_rows(rows, features)
    assert len([r for r in records if r["panel"] == "Physicians"]) == 14
    assert all(r["value"] is None for r in records if r["panel"] == "Map")
    for panel in ["Physicians", "Poverty", "Age", "Stability"]:
        selected = [r for r in records if r["panel"] == panel]
        assert len(selected) == len({r["fips"] for r in selected}) == 14
    assert {r["fips"] for r in records if r["panel"] == "Map"} == set(FIPS)
    polygons = {}
    for r in records:
        if r["panel"] == "Map":
            polygons.setdefault(r["polygon"], []).append(r)
    for points in polygons.values():
        assert [p["point"] for p in points] == list(range(len(points)))
        assert (points[0]["longitude"], points[0]["latitude"]) == (
            points[-1]["longitude"],
            points[-1]["latitude"],
        )


def test_workbook_panels_have_filters_relative_paths_and_required_attributes():
    root = E.fromstring(workbook())
    assert root.get("source-build") and root.get("version") == "18.1"
    ds = root.find("./datasources/datasource")
    assert ds[0].tag == "connection" and ds[1].tag == "aliases"
    assert ds.find("extract").attrib == {"enabled": "true", "count": "-1", "units": "records"}
    sheets = root.findall("./worksheets/worksheet")
    assert len(sheets) == 5
    assert {s.find(".//groupfilter").get("member").strip('"') for s in sheets} == {
        "Map",
        "Physicians",
        "Poverty",
        "Age",
        "Stability",
    }
    assert {s.get("name") for s in sheets} == {
        z.get("name") for z in root.findall(".//zone") if z.get("name")
    }
    for c in root.findall(".//connection"):
        assert all(not Path(c.get(k, "")).is_absolute() for k in ["directory", "filename", "dbname"])


def test_missing_previous_year_is_indeterminate_not_a_negative_selection(project):
    rows, _ = build(project)
    rows[0]["pcp_2022_per_100k"] = None
    analyze(rows, project / "analysis")
    assert rows[0]["evaluated_scenarios"] == 7
    records = list(csv.DictReader((project / "analysis/sensitivity.csv").open()))
    r = next(
        r for r in records if r["fips"] == rows[0]["fips"] and r["scenario"] == "previous_workforce_year"
    )
    assert r["selected"] == ""


def test_packaged_payload_matches_adjacent_files_and_metric_rows():
    with zipfile.ZipFile(ROOT / "dashboard/MA_Primary_Care_Access.twbx") as z:
        assert z.testzip() is None
        for name in z.namelist():
            assert z.read(name) == (ROOT / "dashboard" / name).read_bytes()
        records = list(csv.DictReader(z.read("Data/dashboard.csv").decode().splitlines()))
    expected = list(csv.DictReader((ROOT / "analysis/county_comparison.csv").open()))
    fields = {
        "Physicians": "pcp_per_100k",
        "Poverty": "poverty_pct",
        "Age": "age65_pct",
        "Stability": "selected_scenarios",
    }
    for panel, field in fields.items():
        actual = {r["fips"]: float(r["value"]) for r in records if r["panel"] == panel}
        assert actual == {r["fips"]: float(r[field]) for r in expected}
    assert all(not r["value"] for r in records if r["panel"] == "Map")


def test_decision_memo_has_two_pages_and_documents_limits():
    from pypdf import PdfReader

    pdf = PdfReader(ROOT / "docs/decision_memo.pdf")
    assert len(pdf.pages) == 2
    text = " ".join(p.extract_text() for p in pdf.pages)
    assert "Nantucket" in text and "not probabilities" in text
    assert all(name in text for name in ["Franklin", "Hampden", "Bristol", "Dukes", "Plymouth", "Essex"])
