"""Local Tableau Public workbook; no publishing or external map service."""

import json
import tempfile
import xml.etree.ElementTree as E
import zipfile
from pathlib import Path

from .sources import write_csv

FIELDS = [
    ("panel", "string"),
    ("county", "string"),
    ("fips", "string"),
    ("screening_group", "string"),
    ("polygon", "string"),
    ("point", "integer"),
    ("longitude", "real"),
    ("latitude", "real"),
    ("value", "real"),
    ("unit", "string"),
]
PANELS = [
    ("County map", "Map", ""),
    ("Primary-care physicians per 100,000 residents", "Physicians", "Physicians per 100,000"),
    ("Poverty context", "Poverty", "Percent below poverty"),
    ("Older-population context", "Age", "Percent age 65 and over"),
    ("Shortlist sensitivity", "Stability", "Selections across 8 scenarios"),
]


def el(parent, tag, text=None, **attrs):
    child = E.SubElement(parent, tag, attrs)
    if text is not None:
        child.text = str(text)
    return child


def data_rows(counties, features):
    result = []
    by_fips = {r["fips"]: r for r in counties}
    for row in counties:
        for panel, key, unit in [
            ("Physicians", "pcp_per_100k", "physicians per 100,000"),
            ("Poverty", "poverty_pct", "percent"),
            ("Age", "age65_pct", "percent"),
            ("Stability", "selected_scenarios", "of 8 scenarios"),
        ]:
            record = {k: None for k, _ in FIELDS}
            record.update(
                panel=panel,
                county=row["county"],
                fips=row["fips"],
                screening_group=row["screening_group"],
                value=row[key],
                unit=unit,
            )
            result.append(record)
    # Polygon exteriors form a display-only map. No metric is aggregated from vertices.
    for feature in features:
        row = by_fips[feature["properties"]["fips"]]
        geometry = feature["geometry"]
        polygons = (
            geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        )
        for index, polygon in enumerate(polygons):
            for point, (lon, lat) in enumerate(polygon[0]):
                record = {k: None for k, _ in FIELDS}
                record.update(
                    panel="Map",
                    county=row["county"],
                    fips=row["fips"],
                    screening_group=row["screening_group"],
                    polygon=f"{row['fips']}-{index}",
                    point=point,
                    longitude=lon,
                    latitude=lat,
                    unit="boundary vertex",
                )
                result.append(record)
    return result


def workbook():
    root = E.Element(
        "workbook",
        {"version": "18.1", "source-platform": "mac", "source-build": "2026.2.2 (20262.26.0819.2015)"},
    )
    el(root, "preferences")
    ds = el(
        el(root, "datasources"),
        "datasource",
        name="access",
        caption="Massachusetts county access indicators",
        inline="true",
        version="18.1",
    )
    con = el(ds, "connection", directory="Data", filename="dashboard.csv", server="", **{"class": "textscan"})
    relation = el(con, "relation", name="dashboard.csv", table="[dashboard#csv]", type="table")
    columns = el(
        relation, "columns", header="yes", separator=",", locale="en_US", **{"character-set": "UTF-8"}
    )
    el(ds, "aliases", enabled="yes")
    definitions = []
    for i, (name, kind) in enumerate(FIELDS):
        el(columns, "column", name=name, datatype=kind, ordinal=str(i))
        is_measure = name in {"longitude", "latitude", "value"}
        definition = dict(
            name=f"[{name}]",
            datatype=kind,
            role="measure" if is_measure else "dimension",
            type="quantitative" if is_measure else ("ordinal" if name == "point" else "nominal"),
        )
        definitions.append(definition)
        field = el(ds, "column", **definition)
        field.set(
            "caption",
            {
                "county": "County",
                "screening_group": "Baseline shortlist",
                "value": "Indicator",
                "longitude": "Longitude",
                "latitude": "Latitude",
                "fips": "County FIPS",
            }.get(name, name.replace("_", " ").title()),
        )
    extract = el(ds, "extract", enabled="true", count="-1", units="records")
    con = el(
        extract,
        "connection",
        dbname="Data/access.hyper",
        schema="Extract",
        access_mode="readonly",
        authentication="auth-none",
        **{"class": "hyper", "default-settings": "yes"},
    )
    el(con, "relation", name="Extract", table="[Extract].[Extract]", type="table")
    sheets = el(root, "worksheets")
    for title, panel, axis_title in PANELS:
        sheet = el(sheets, "worksheet", name=title)
        el(
            el(el(el(sheet, "layout-options"), "title"), "formatted-text"),
            "run",
            title,
            fontsize="12",
            bold="true",
        )
        table = el(sheet, "table")
        view = el(table, "view")
        el(
            el(view, "datasources"),
            "datasource",
            name="access",
            caption="Massachusetts county access indicators",
        )
        deps = el(view, "datasource-dependencies", datasource="access")
        for d in definitions:
            el(deps, "column", **d)
        for name, _kind in FIELDS:
            measure = name in {"longitude", "latitude", "value"}
            el(
                deps,
                "column-instance",
                column=f"[{name}]",
                derivation="Sum" if measure else "None",
                name=f"[{'sum' if measure else 'none'}:{name}:{'qk' if measure else 'ok' if name == 'point' else 'nk'}]",
                pivot="key",
                type="quantitative" if measure else "ordinal" if name == "point" else "nominal",
            )
        filt = el(view, "filter", column="[access].[none:panel:nk]", **{"class": "categorical"})
        el(filt, "groupfilter", function="member", level="[none:panel:nk]", member='"' + panel + '"')
        el(el(view, "slices"), "column", "[access].[none:panel:nk]")
        el(view, "aggregation", value="true")
        style = el(table, "style")
        markstyle = el(style, "style-rule", element="mark")
        el(markstyle, "format", attr="mark-labels-show", value="false" if panel == "Map" else "true")
        encoding = el(
            markstyle, "encoding", attr="color", field="[access].[none:screening_group:nk]", type="palette"
        )
        for label, color in [("Investigate", "#b65a2b"), ("Not selected", "#8aabbc")]:
            el(el(encoding, "map", to=color), "bucket", '"' + label + '"')
        axis = el(style, "style-rule", element="axis")
        el(
            axis,
            "format",
            attr="title",
            field="[access].[sum:longitude:qk]" if panel == "Map" else "[access].[sum:value:qk]",
            scope="cols",
            value="Longitude" if panel == "Map" else axis_title,
            **{"class": "0"},
        )
        pane = el(el(table, "panes"), "pane")
        el(el(pane, "view"), "breakdown", value="auto")
        el(pane, "mark", **{"class": "Polygon" if panel == "Map" else "Bar"})
        enc = el(pane, "encodings")
        el(enc, "color", column="[access].[none:screening_group:nk]")
        if panel == "Map":
            el(enc, "lod", column="[access].[none:county:nk]")
            el(enc, "lod", column="[access].[none:polygon:nk]")
            el(enc, "path", column="[access].[none:point:ok]")
        el(table, "rows", "[access].[sum:latitude:qk]" if panel == "Map" else "[access].[none:county:nk]")
        el(table, "cols", "[access].[sum:longitude:qk]" if panel == "Map" else "[access].[sum:value:qk]")
    title = "Massachusetts primary-care access investigation"
    dashboard = el(el(root, "dashboards"), "dashboard", name=title)
    el(dashboard, "style")
    el(dashboard, "size", minwidth="1400", maxwidth="1400", minheight="1150", maxheight="1150")
    zones = el(dashboard, "zones")
    intro = el(zones, "zone", id="1", x="1500", y="1000", w="97000", h="11500", **{"type-v2": "text"})
    el(
        el(intro, "formatted-text"),
        "run",
        "MASSACHUSETTS | PRIMARY-CARE ACCESS\n2023 physicians; 2019-2023 ACS. Orange: baseline shortlist. Blue: not selected.\nInvestigation screen only: physician counts do not prove unmet need or identify a clinic site.\nLower supply + poverty or older-population context; see decision memo for thresholds and uncertainty.",
        fontsize="14",
        bold="true",
    )
    positions = [
        (1500, 14000, 46500, 25000),
        (50500, 14000, 48000, 49000),
        (1500, 42000, 46500, 25000),
        (1500, 70000, 46500, 26000),
        (50500, 66000, 48000, 30000),
    ]
    for i, ((name, _, _), pos) in enumerate(zip(PANELS, positions, strict=False), 2):
        el(
            zones,
            "zone",
            id=str(i),
            name=name,
            **dict(zip(["x", "y", "w", "h"], map(str, pos), strict=False)),
        )
    window = el(el(root, "windows"), "window", name=title, maximized="true", **{"class": "dashboard"})
    viewpoints = el(window, "viewpoints")
    for name, _, _ in PANELS:
        el(el(viewpoints, "viewpoint", name=name), "zoom", type="entire-view")
    el(window, "active", id="-1")
    E.indent(root)
    return E.tostring(root, encoding="utf-8", xml_declaration=True)


def create(root, rows, features):
    from tableauhyperapi import (
        Connection,
        CreateMode,
        HyperProcess,
        Inserter,
        SqlType,
        TableDefinition,
        TableName,
        Telemetry,
    )

    root = Path(root)
    out = root / "dashboard"
    (out / "Data").mkdir(parents=True, exist_ok=True)
    records = data_rows(rows, features)
    write_csv(out / "Data/dashboard.csv", records)
    types = {"string": SqlType.text(), "integer": SqlType.big_int(), "real": SqlType.double()}
    table = TableDefinition(
        TableName("Extract", "Extract"), [TableDefinition.Column(n, types[k]) for n, k in FIELDS]
    )
    with tempfile.TemporaryDirectory() as temp:
        with HyperProcess(
            Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_dir": temp}
        ) as process:
            with Connection(
                process.endpoint, str(out / "Data/access.hyper"), CreateMode.CREATE_AND_REPLACE
            ) as con:
                con.catalog.create_schema("Extract")
                con.catalog.create_table(table)
                expected = [[r[n] for n, _ in FIELDS] for r in records]
                with Inserter(con, table) as insert:
                    insert.add_rows(expected)
                    insert.execute()
                actual = con.execute_list_query('SELECT * FROM "Extract"."Extract"')
                if sorted(actual, key=repr) != sorted(expected, key=repr):
                    raise ValueError("Hyper values differ from CSV records")
    xml = workbook()
    (out / "MA_Primary_Care_Access.twb").write_bytes(xml)
    with zipfile.ZipFile(out / "MA_Primary_Care_Access.twbx", "w", zipfile.ZIP_DEFLATED) as z:
        for name in ["MA_Primary_Care_Access.twb", "Data/dashboard.csv", "Data/access.hyper"]:
            z.write(out / name, name)
    (out / "validation.json").write_text(
        json.dumps(
            dict(
                extract_rows=len(records),
                county_count=len(rows),
                extract_readback_verified=True,
                publishing_performed=False,
                native_rendering_verified=False,
            ),
            indent=2,
        )
        + "\n"
    )
