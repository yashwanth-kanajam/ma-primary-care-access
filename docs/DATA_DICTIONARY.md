# Data dictionary

The analytical grain is one Massachusetts county per row. FIPS is text, never a floating-point key. Numeric blank cells in generated CSVs mean missing, not zero. Inputs and raw field codes are documented in [SOURCES.md](SOURCES.md).

## Clean and analytical tables

| Field | Type / unit | Definition |
|---|---|---|
| `fips` | 5-character text | State 25 plus 3-digit county code |
| `county` | text | County name, excluding state suffix |
| `population` | count | ACS total residents, B01001 E001 |
| `population_moe` | people | ACS total population MOE; controlled-total sentinel becomes 0 |
| `pcp_2023`, `pcp_2022` | physician counts | HRSA non-federal primary-care patient-care physician headcounts, specified year |
| `md_2023`, `do_2023` | physician counts | Components of `pcp_2023` |
| `pcp_per_100k` | physicians / 100,000 residents | `pcp_2023 / population * 100000` |
| `pcp_2022_per_100k` | physicians / 100,000 residents | 2022 count divided by the same ACS population |
| `age65` | people | Sum of 12 male/female ACS age cells from 65 through 85+ |
| `age65_moe` | people | Approximate 90% MOE for the age-cell sum |
| `age65_pct` | percent | `age65 / population * 100` |
| `age65_moe_pp` | percentage points | Approximate 90% MOE of age-65-plus percentage |
| `poverty_population` | people | Population for whom poverty status is determined, B17001 E001 |
| `poverty_population_moe` | people | Published 90% MOE for the poverty universe |
| `poverty` | people | People below poverty, B17001 E002 |
| `poverty_moe` | people | Published 90% MOE for below-poverty count |
| `poverty_pct` | percent | `poverty / poverty_population * 100` |
| `poverty_moe_pp` | percentage points | Approximate 90% MOE of poverty percentage |

`data/processed/acs_clean.csv` contains the ACS count inputs; `workforce_clean.csv` contains the physician counts. SQL joins these in `county_metrics` inside the generated `access.duckdb`. `county_indicators.csv` adds the Python-derived percentage MOEs. None of these measures is an appointment count, FTE estimate or measure of realized unmet need.

## Analysis outputs

`analysis/county_comparison.csv` adds:

| Field | Definition |
|---|---|
| `baseline_selected` | True/False baseline decision; blank if indeterminate |
| `selected_scenarios` | Number of the eight defined rules that select the county |
| `scenario_count` | Number of specified rules (8) |
| `evaluated_scenarios` | Rules with a determinate result; 8 for every published county |
| `capacity_stable` | Selected in all four supply/year variants, not necessarily all eight scenarios |
| `screening_group` | Investigate, Not selected, or Indeterminate |

`analysis/sensitivity.csv` has one county/scenario row: `fips`, `county`, `scenario`, `selected` (True/False/blank), and the scenario's physician-rate `capacity_cutoff`. `findings.json` stores weighted benchmarks, exact cutoffs, baseline/supply-stable shortlists, additions/removals and Jaccard similarities.

## Dashboard transport data

`dashboard/Data/dashboard.csv` and its Hyper counterpart contain `panel`, `county`, `fips`, `screening_group`, `polygon`, `point`, `longitude`, `latitude`, `value`, `unit`. Comparison panels have one row per county per indicator. Map rows are exterior-ring vertices with sequential `point` order and a unique `polygon` identifier; their `value` is blank. Every sheet filters a single `panel`. Summing across panels or map vertices is invalid.

`data/processed/quality_checks.json` records expected county coverage, duplicate/unmatched identifiers, boundary count, physician-total reconciliation, column missingness and source-slice hash validation. Build failures identify the violated condition instead of publishing a supposedly complete shortlist.
