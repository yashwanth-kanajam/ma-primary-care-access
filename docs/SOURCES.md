# Sources and provenance

The machine-readable register is [data/source_register.json](../data/source_register.json). It records exact URLs, retrieval time, byte counts and SHA-256 hashes for each original download and each committed Massachusetts slice. Full national files remain in the ignored download cache. The raw slices preserve published cell values; cleaning happens separately.

## HRSA workforce

[HRSA Area Health Resources Files downloads](https://data.hrsa.gov/data/download?AHRF=&data=AHRF), county release 2024-2025. The selected member of `AHRF_2024-2025_CSV.zip` is `NCHWA-2024-2025+AHRF+COUNTY+CSV/AHRF2025hp.csv`.

| Retained field | Meaning |
|---|---|
| `fips_st_cnty` | Five-digit state/county FIPS |
| `cnty_name_st_abbrev` | County name and state abbreviation |
| `phys_nf_prim_care_pc_exc_rsdt_23` | 2023 non-federal primary-care patient-care physicians, excluding hospital residents and age 75+ |
| `phys_nf_prim_care_pc_exc_rsdt_22` | Same definition, 2022 |
| `md_nf_prim_care_pc_excl_rsdnt_23` | MD component, 2023 |
| `do_nf_prim_care_pc_excl_rsdnt_23` | DO component, 2023 |

The AHRF User Guide and Technical Documentation workbook in `AHRF_USER_TECH_2024-2025.zip` identify the upstream AMA Physician Professional Data and reference-year definitions. Only Massachusetts county rows and these six fields are retained in `ma_workforce.csv`; no clinician-level records are used. HRSA lists no usage limitation for its AHRF download. Upstream source credits remain applicable; no claim of ownership over source data is made.

## Census demographic context

[Census 2023 table-based ACS five-year summary files](https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData/) provide B01001 (sex by age) and B17001 (poverty status). Both represent 2019-2023. Documentation comes from the corresponding [table shells](https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/documentation/ACS20235YR_Table_Shells.txt).

The full pipe-delimited table files contain estimates and MOEs for many geographic levels. Extraction retains only `GEO_ID = 0500000US` followed by one of Massachusetts's 14 county FIPS codes. All columns and cell strings for those rows are retained in `ma_b01001.csv` and `ma_b17001.csv`; names are joined from the HRSA/boundary sources, not guessed from ACS row order. The Census API requires a key, so reproduction uses the public summary-file downloads instead.

Five-year estimates are used to cover the small counties consistently. The 2023 endpoint aligns with the workforce observation year more closely than the newer 2024 ACS release, but remains a period estimate rather than a 2023 point estimate. Only the two needed demographic tables are included.

## County boundaries

[Census 2023 cartographic boundary files](https://www.census.gov/geographies/mapping-files/2023/geo/carto-boundary-file.html), national counties at 1:500,000. Extraction retains `STATEFP=25`, the county `GEOID`, name and geometry. The committed `ma_counties.geojson` is the Massachusetts subset, serialized deterministically. Native shapefile coordinates use NAD83 geographic longitude/latitude. GeoJSON is used locally as a coordinate container; no precision geodesy or datum transformation is claimed.

This geometry is a display resource, not an additional access indicator. Every boundary FIPS must match the same 14-county analytical key set. Polygon rings do not participate in rate denominators or shortlist decisions.

## Reproduce and verify provenance

`ma-access fetch` downloads missing full-source files, checks their pinned hashes, extracts the Massachusetts slices and checks those hashes. A publisher replacement or local alteration fails validation. `ma-access run` verifies the committed slice hashes without downloading national files. No authentication key, credential or private patient data is needed.

The expected county set is Barnstable (25001), Berkshire (25003), Bristol (25005), Dukes (25007), Essex (25009), Franklin (25011), Hampden (25013), Hampshire (25015), Middlesex (25017), Nantucket (25019), Norfolk (25021), Plymouth (25023), Suffolk (25025) and Worcester (25027). Non-county geography, unknown codes, duplicated counties or missing counties are errors; there is no name-only fallback or many-to-many geographic join.
