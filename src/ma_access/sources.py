"""Pinned public downloads and small, traceable Massachusetts source slices."""

import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

SOURCES = {
    "ahrf.zip": (
        "HRSA AHRF 2024-2025 county files",
        "https://data.hrsa.gov/DataDownload/AHRF/AHRF_2024-2025_CSV.zip",
    ),
    "ahrf_docs.zip": (
        "HRSA AHRF 2024-2025 technical documentation",
        "https://data.hrsa.gov/DataDownload/AHRF/AHRF_USER_TECH_2024-2025.zip",
    ),
    "acs_b01001.dat": (
        "Census 2019-2023 ACS five-year B01001",
        "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-b01001.dat",
    ),
    "acs_b17001.dat": (
        "Census 2019-2023 ACS five-year B17001",
        "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/acsdt5y2023-b17001.dat",
    ),
    "counties.zip": (
        "Census 2023 county cartographic boundaries, 1:500,000",
        "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip",
    ),
    "acs_shells.txt": (
        "Census 2023 five-year table shells",
        "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/documentation/ACS20235YR_Table_Shells.txt",
    ),
}
FIPS = tuple(f"25{i:03}" for i in range(1, 28, 2))
PC23 = "phys_nf_prim_care_pc_exc_rsdt_23"
PC22 = "phys_nf_prim_care_pc_exc_rsdt_22"
MD23 = "md_nf_prim_care_pc_excl_rsdnt_23"
DO23 = "do_nf_prim_care_pc_excl_rsdnt_23"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def fetch(root):
    root = Path(root)
    raw = root / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    register = json.loads((root / "data/source_register.json").read_text())
    for name, (_, url) in SOURCES.items():
        path = raw / name
        if not path.exists():
            temp = path.with_suffix(path.suffix + ".part")
            try:
                with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as f:
                    for block in iter(lambda: response.read(1024 * 1024), b""):
                        f.write(block)
                if digest(temp) != register["downloads"][name]["sha256"]:
                    raise ValueError(
                        f"{name}: upstream content changed; review the source register before use"
                    )
                temp.replace(path)
            finally:
                if temp.exists():
                    temp.unlink()
        if digest(path) != register["downloads"][name]["sha256"]:
            raise ValueError(f"{name}: source checksum mismatch")
    extract(root)
    verify_slices(root)


def extract(root):
    import shapefile

    root = Path(root)
    raw = root / "data/raw"
    for table in ["b01001", "b17001"]:
        with (raw / f"acs_{table}.dat").open() as f:
            reader = csv.DictReader(f, delimiter="|")
            rows = [r for r in reader if r["GEO_ID"] in {"0500000US" + x for x in FIPS}]
        if len(rows) != 14:
            raise ValueError("Expected exactly 14 Massachusetts ACS county rows")
        write_csv(raw / f"ma_{table}.csv", rows)
    with zipfile.ZipFile(raw / "ahrf.zip") as z:
        member = next(n for n in z.namelist() if n.endswith("/AHRF2025hp.csv"))
        fields = ["fips_st_cnty", "cnty_name_st_abbrev", PC23, PC22, MD23, DO23]
        with z.open(member) as stream:
            rows = [
                {k: r[k] for k in fields}
                for r in csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))
                if r["fips_st_cnty"] in FIPS
            ]
    if len(rows) != 14:
        raise ValueError("Expected exactly 14 Massachusetts workforce rows")
    write_csv(raw / "ma_workforce.csv", rows)
    with zipfile.ZipFile(raw / "counties.zip") as z:

        def content(ext):
            return io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith(ext))))

        reader = shapefile.Reader(shp=content(".shp"), shx=content(".shx"), dbf=content(".dbf"))
        features = []
        for item in reader.iterShapeRecords():
            attrs = item.record.as_dict()
            if attrs["STATEFP"] == "25":
                features.append(
                    dict(
                        type="Feature",
                        properties={"fips": attrs["GEOID"], "county": attrs["NAME"]},
                        geometry=item.shape.__geo_interface__,
                    )
                )
    if {f["properties"]["fips"] for f in features} != set(FIPS):
        raise ValueError("Boundary county coverage mismatch")
    features.sort(key=lambda f: f["properties"]["fips"])
    (raw / "ma_counties.geojson").write_text(
        json.dumps(dict(type="FeatureCollection", features=features), sort_keys=True, separators=(",", ":"))
        + "\n"
    )


def verify_slices(root):
    root = Path(root)
    register = json.loads((root / "data/source_register.json").read_text())
    for name, expected in register["slices"].items():
        if digest(root / "data/raw" / name) != expected["sha256"]:
            raise ValueError(f"{name}: source slice checksum mismatch")
