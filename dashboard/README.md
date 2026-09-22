# Massachusetts access dashboard

Open `MA_Primary_Care_Access.twbx` in Tableau Public 2026.2.2. The package embeds `Data/access.hyper` and the source CSV; the adjacent `.twb` also works when its `Data/` directory is preserved. No external map service or account is needed for the local workbook. Do not publish it to Tableau Public without user review.

The county map and comparison panels show physician supply, poverty, age-65-plus share, and selections across the eight sensitivity scenarios. Orange indicates the baseline shortlist; blue indicates not selected. Nonselection does not establish adequate access. Selections out of eight are not probabilities.

A sheet-specific filter keeps each measure separate. County map vertices have no numerical indicator value and cannot inflate comparison totals. Coastlines are generalized; only polygon exteriors are rendered. Geography is for orientation, not travel-time analysis. County labels and tooltips identify the displayed marks; comparisons use the full county list.

Build from the repository root:

```sh
.venv/bin/ma-access dashboard
```

The optional pinned Hyper API dependency is required. The converter disables Hyper usage telemetry and verifies all extracted rows against the CSV. Binary Hyper bytes may vary. Generated `validation.json` deliberately leaves native rendering false; a successful XML/extract check cannot prove application compatibility.

The user confirmed that the county map and all four comparison views render without an error in Tableau Public 2026.2.2. App control was returning an older workbook window, so this native check is recorded as user-confirmed rather than an automated visual check. See [verification](../docs/VERIFICATION.md) for the final observed application result. No publishing is performed by the build command.
