# Metric definitions and screening rules

## Observation unit and time

One row per Massachusetts county, keyed by five-digit text FIPS (`25001` through `25027`, odd county codes). All 14 counties are retained. AHRF 2024-2025 is a release label: the selected workforce observations are from December 31, 2023 and 2022. Census inputs are 2019-2023 ACS five-year estimates. This is a historical comparison, not a 2026 availability estimate or trend model.

## Indicators

| Indicator | Numerator | Denominator / transformation |
|---|---|---|
| Primary-care physicians per 100,000 | `phys_nf_prim_care_pc_exc_rsdt_23` | ACS B01001 E001 total population; multiply by 100,000 |
| Poverty percentage | B17001 E002, below poverty | B17001 E001, population for whom poverty status is determined; multiply by 100 |
| Age 65+ percentage | Sum B01001 E020-E025 and E044-E049 | B01001 E001 total population; multiply by 100 |
| Previous-workforce-year sensitivity | `phys_nf_prim_care_pc_exc_rsdt_22` | Same ACS population denominator; this isolates numerator sensitivity and is not a year-on-year rate comparison |

HRSA's selected primary-care physician definition includes non-federal MDs and DOs principally in general family medicine, general practice, general internal medicine and general pediatrics. It excludes subspecialties, hospital residents and physicians aged 75 or older. The total reconciles to the corresponding MD plus DO fields. It is not the separate HPSA definition, a designation count, or an FTE measure. No HPSA areas are forced into county boundaries.

Population denominators differ by metric. Poverty must not be divided by total residents. Statewide context benchmarks are ratios of summed county numerators and their corresponding denominators, not averages of county percentages. The statewide physician rate is descriptive only and is not the baseline supply cutoff.

## Baseline rule

1. Supply rate is strictly below the unweighted median across the 14 county rates: 78.826789 physicians per 100,000.
2. Poverty share is at or above 9.982174%, OR age-65-plus share is at or above 17.466819%.

Both steps must hold. The context benchmarks are population-weighted Massachusetts rates. The median is a relative investigation screen, not a clinical capacity standard. Equality at the supply cutoff is excluded; equality at a context benchmark is included. The rule was defined before inspecting the resulting county shortlist.

## Sensitivity checks

Eight deterministic scenarios: baseline; supply cutoffs at the 40th and 60th percentiles; 2022 physician counts with the same population denominator and a recalculated median; poverty-only context; age-only context; both county context percentages minus their approximate 90% MOEs; and both plus their MOEs. Percentiles use linear interpolation at index `(n-1)*q`. Context bounds are clipped to 0-100. Benchmarks remain fixed in the MOE scenarios.

`capacity_stable` means selected under baseline, 40th percentile, 60th percentile and previous-workforce-year rules. It is not stability under every possible assumption. `selected_scenarios` counts selections across all eight rules; `evaluated_scenarios` counts rules with non-missing decisions. These are not probabilities. Jaccard similarity is intersection / union of a scenario shortlist and baseline (1 if both are empty).

## Uncertainty and missingness

ACS MOEs are published at 90% confidence. For a sum of age cells, use the square root of the sum of squared MOEs. For a subset proportion `p=N/D`, percentage MOE is `100*sqrt(M_N^2-p^2*M_D^2)/D`; if the radicand is negative, use addition instead. These are Census approximation formulas and do not fully incorporate covariance. They do not establish statistical significance between a county and the state, which includes that county.

Census sentinel -555555555 in an MOE denotes a controlled estimate and is treated as zero sampling error, following Census guidance; its raw annotation is preserved in the source slice. Other negative sentinel estimates/MOEs, blanks and suppressed values become missing, not zero. Sums containing missing values remain missing. Non-finite values are rejected. Zero or missing total-population denominators stop the build. Incomplete statewide benchmark inputs stop analysis; an unavailable previous-year rate creates an indeterminate scenario decision and reduces `evaluated_scenarios`. Published outputs have no missing indicator inputs.

[ACS MOE annotations](https://www.census.gov/data/developers/data-sets/acs-1year/notes-on-acs-estimate-and-annotation-values.html) and [Census derived-estimate formulas](https://www2.census.gov/programs-surveys/acs/tech_docs/statistical_testing/2017StatisticalTesting5year.pdf) document these conventions. The formulas apply to survey-derived estimates; they do not quantify physician-count error.
