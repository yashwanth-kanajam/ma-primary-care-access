"""Two-page decision memo, generated from the checked county results."""

import csv
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def create_memo(root):
    root = Path(root)
    result = json.loads((root / "analysis/findings.json").read_text())
    with (root / "analysis/county_comparison.csv").open() as f:
        rows = list(csv.DictReader(f))
    selected = [r for r in rows if r["county"] in result["baseline_shortlist"]]
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="MemoTitle",
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=23,
            textColor=colors.HexColor("#173b4a"),
            spaceAfter=12,
        )
    )
    styles.add(ParagraphStyle(name="MemoBody", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="MemoSmall", fontName="Helvetica", fontSize=8, leading=10, spaceAfter=5))
    styles.add(
        ParagraphStyle(
            name="MemoHead",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#173b4a"),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    flow = []

    def para(text, style="MemoBody"):
        flow.append(Paragraph(text, styles[style]))

    def table(data, widths):
        cells = [[Paragraph(str(c), styles["MemoSmall"]) for c in row] for row in data]
        t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eff2")),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#8aabbc")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8f9")]),
                ]
            )
        )
        flow.append(t)
        flow.append(Spacer(1, 8))

    para("Massachusetts primary-care access", "MemoTitle")
    para("Decision memo | County investigation screen | 2023 workforce and 2019-2023 ACS", "MemoSmall")
    para("Decision: where to investigate next", "MemoHead")
    para(
        "Investigate <b>"
        + ", ".join(result["baseline_shortlist"])
        + "</b>. This is a shortlist for gathering local evidence, not a finding of unmet need or a recommendation to build a clinic."
    )
    para(
        "<b>Franklin and Hampden</b> are the most consistent signals: both are selected in all eight tested scenarios. Bristol, Dukes and Plymouth remain selected across the supply-threshold and workforce-year checks but depend more on which population context is emphasized. Essex is sensitive to the supply cutoff."
    )
    table(
        [["County", "Physicians / 100k", "Poverty %", "Age 65+ %", "Selected / 8"]]
        + [
            [
                r["county"],
                f"{float(r['pcp_per_100k']):.1f}",
                f"{float(r['poverty_pct']):.1f}",
                f"{float(r['age65_pct']):.1f}",
                r["selected_scenarios"],
            ]
            for r in selected
        ],
        [108, 100, 85, 90, 100],
    )
    para("How the screen works", "MemoHead")
    b = result["benchmarks"]
    c = result["capacity_cutoffs"]["baseline"]
    para(
        f"Select counties below the unweighted county median of <b>{c:.1f} primary-care physicians per 100,000 residents</b> and at or above the Massachusetts population-weighted poverty benchmark (<b>{b['poverty_pct']:.2f}%</b>) or age-65-plus benchmark (<b>{b['age65_pct']:.2f}%</b>). No composite score or clinical adequacy threshold is used."
    )
    para(
        "The numerator is HRSA AHRF non-federal MDs and DOs in primary-care patient care, excluding hospital residents and physicians aged 75 or older. It is a headcount, not appointment capacity or full-time equivalents. Rates use ACS total residents; poverty percentages use the separate population for whom poverty status is determined."
    )
    para("What the shortlist leaves out", "MemoHead")
    para(
        "Nantucket has only 8 counted physicians (55.9 per 100,000), but its poverty and older-population percentages fall below the chosen context benchmarks. Its exclusion illustrates a rule limitation, especially where seasonal population and island travel matter. Suffolk has high poverty but a high physician count; county averages may conceal neighborhood barriers. Neither exclusion establishes adequate access."
    )
    flow.append(PageBreak())
    para("Stability, uncertainty and next evidence", "MemoTitle")
    para("How much does the decision change?", "MemoHead")
    labels = {
        "baseline": "Baseline",
        "stricter_capacity": "40th-percentile supply cutoff",
        "broader_capacity": "60th-percentile supply cutoff",
        "previous_workforce_year": "2022 workforce; same population",
        "poverty_context_only": "Poverty context only",
        "older_context_only": "Older-population context only",
        "context_lower_bounds": "County context minus 90% MOE",
        "context_upper_bounds": "County context plus 90% MOE",
    }
    data = [["Assumption", "Count", "Change from baseline"]]
    for s in result["scenarios"]:
        changes = []
        if s["added"]:
            changes.append("Add " + ", ".join(s["added"]))
        if s["removed"]:
            changes.append("Remove " + ", ".join(s["removed"]))
        data.append([labels[s["scenario"]], str(s["selected_count"]), "; ".join(changes) or "No change"])
    table(data, [211, 42, 230])
    para(
        "The five-county supply-stable set is Bristol, Dukes, Franklin, Hampden and Plymouth. Selection frequencies describe these eight chosen rules; they are not probabilities or confidence levels. Context-MOE checks hold statewide benchmarks fixed and are not formal tests of county-state differences."
    )
    para("Limits that could change the recommendation", "MemoHead")
    para(
        "The workforce snapshot is from 2023, not current availability. ACS values summarize 2019-2023 rather than a single year. The physician definition excludes nurse practitioners and physician assistants and cannot show hours, insurance acceptance, open panels, language access or cross-county patient flows. Resident denominators omit seasonal demand. County averages mask within-county differences. ACS percentage margins are approximations; no provider-count uncertainty interval is available here."
    )
    para("Recommended next step", "MemoHead")
    para(
        "Begin local evidence collection in Franklin and Hampden, then assess Bristol, Dukes and Plymouth against the intended service model. Keep Essex and Barnstable as threshold-sensitive cases. Before any investment decision, obtain appointment waits, new-patient and insurance acceptance, clinician FTE/open-panel information, travel and ferry access, subcounty deprivation, and seasonal population. Recheck Nantucket explicitly rather than treating its exclusion as reassurance."
    )
    para("Sources and reproducibility", "MemoHead")
    para(
        "HRSA AHRF 2024-2025 county release, 2023 and 2022 primary-care physician fields; Census 2019-2023 ACS five-year tables B01001 and B17001; Census 2023 county boundaries (1:500,000). Download URLs, retrieval time and SHA-256 hashes are in data/source_register.json. All 14 Massachusetts counties join by five-digit county FIPS. See docs/METRICS.md for exact definitions and analysis/sensitivity.csv for every county/scenario result.",
        "MemoSmall",
    )

    def footer(c, doc):
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#52626b"))
        c.drawString(
            56, 28, "Public aggregate data | Investigation only | No clinic-site or unmet-need claim"
        )
        c.drawRightString(A4[0] - 56, 28, str(doc.page))

    (root / "docs").mkdir(exist_ok=True)
    doc = SimpleDocTemplate(
        str(root / "docs/decision_memo.pdf"),
        pagesize=A4,
        rightMargin=56,
        leftMargin=56,
        topMargin=42,
        bottomMargin=42,
        title="Massachusetts primary-care access: decision memo",
        author="Yashwanth Kanajam",
        invariant=1,
    )
    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
