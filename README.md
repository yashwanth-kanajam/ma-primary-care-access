# Massachusetts Primary Care Access Planning

**Which Massachusetts counties warrant deeper investigation for primary-care access, and how stable is that shortlist under different reasonable assumptions?**

## Key finding

The baseline screen selects **Bristol, Dukes, Essex, Franklin, Hampden and Plymouth**.

**Franklin and Hampden remained on the investigation shortlist across all eight tested parameter settings, which produced five distinct shortlist outcomes.** Essex drops out under a stricter supply threshold; Barnstable enters under a broader one. Four of the eight settings reproduce the baseline shortlist exactly, so how often a county is selected should not be read as a probability.

![Massachusetts counties on the baseline investigation shortlist, shown beside primary-care physicians per 100,000 residents by county against the county median](docs/img/shortlist_overview.svg)

*Left: the six baseline shortlist counties. Right: primary-care physicians per 100,000 residents against the county median of 78.8. Built from `dashboard/Data/dashboard.csv`, the same data behind the Tableau workbook.*

## What it means

These counties are where to gather evidence next, not where to allocate resources. The screen does not measure unmet need or appointment availability. Insurance acceptance, travel time and within-county variation would all be needed before a service decision.

The [two-page decision memo](docs/decision_memo.pdf) covers the finding, the recommendation, the uncertainty and the information still missing.

## Data sources

All sources are public U.S. federal data:

| Source | Publisher | Coverage | Used for |
|---|---|---|---|
| AHRF 2024–2025 county file | HRSA | 2023 counts, 2022 for a prior-year check | Non-federal primary-care physician headcounts (MDs and DOs in patient care; excludes hospital residents and physicians aged 75+; **excludes NPs and PAs**) |
| ACS 2019–2023 five-year estimates | US Census Bureau | 2019–2023 | Population and age (B01001), poverty (B17001), and margins of error. Five-year coverage includes the small island counties |
| Cartographic boundary file, 1:500,000 | US Census Bureau | 2023 | County geometry for the map |

Download URLs and retrieval dates are in [`data/source_register.json`](data/source_register.json), and the [source notes](docs/SOURCES.md) explain field selection and time alignment. Massachusetts extracts are committed so the analysis runs offline.

## Approach

All 14 Massachusetts counties are joined on five-digit county FIPS codes, and the build stops if a county is missing, duplicated or has an unrecognized code.

The baseline screen selects counties where physician supply falls **below the county median** *and* either poverty or the age-65+ share is **at or above its Massachusetts population-weighted benchmark**. Physician supply, poverty and age stay as separate indicators rather than being combined into a single score, so each rule can be judged on its own.

Poverty uses *population with poverty status determined* as its denominator, not total population. Python handles acquisition, validation and margins of error; SQL joins the sources and calculates the county measures. The [metric definitions](docs/METRICS.md) give each calculation in full.

## Sensitivity and validation

Eight parameter settings vary the capacity threshold, the workforce year, the population-context rule and the margin-of-error bounds. The outcome of every setting is in [`analysis/findings.json`](analysis/findings.json), and [`analysis/county_comparison.csv`](analysis/county_comparison.csv) keeps all 14 counties, including those never selected.

Automated checks cover geographic joins, denominators, analytical outputs and sensitivity behavior. Suppressed or unavailable values are carried as missing, not zero. The margin-of-error settings are sensitivity ranges, not significance tests. More in [validation](docs/VERIFICATION.md).

## Tableau dashboard

Download [`dashboard/MA_Primary_Care_Access.twbx`](dashboard/MA_Primary_Care_Access.twbx) and open it in Tableau Desktop or Tableau Public; it includes its extract, so no account or upload is needed. The county map and four comparison views share the baseline-shortlist colors. The [dashboard notes](dashboard/README.md) describe units and interactions.

## Reproduce locally

Requires Python 3.11+.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps .
.venv/bin/python -m pytest -q
.venv/bin/ma-access run
.venv/bin/ma-access memo
.venv/bin/ma-access dashboard
```

To rebuild the extracts from the original federal sources, run `.venv/bin/ma-access fetch`.

## Repository contents

| Directory | Contents |
|---|---|
| `data/` | Source register, Massachusetts raw slices, cleaned tables and quality results |
| `src/ma_access/` | Download and extraction, validation, sensitivity analysis, memo and workbook generation |
| `src/ma_access/sql/` | SQL analytical layer and denominator calculations |
| `analysis/` | County comparison, per-setting selections and findings |
| `tests/` | Geographic grain, missingness, transforms, metrics and artifact checks |
| `dashboard/` | Tableau workbook, extract, packaged CSV and display notes |
| `docs/` | Decision memo, data dictionary, methods, limitations and validation |

## Limitations

Physician headcounts are not full-time equivalents, open panels, insurance acceptance or patient travel time, and they exclude nurse practitioners and physician assistants. ACS values describe a five-year period, not the current year.

County averages can hide neighbourhood barriers and cross-county care, and resident counts miss seasonal population. Nantucket has low physician supply but misses the baseline context rule, which reflects the screening design, not adequate access. A high-supply county such as Suffolk can still contain real barriers.

See the [data dictionary](docs/DATA_DICTIONARY.md) and [full limitations](docs/LIMITATIONS.md).
