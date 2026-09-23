# Validation

What was checked, and what is deliberately not claimed.

## Data integrity

- All 14 Massachusetts counties have matching ACS, workforce and boundary FIPS. The analytical join is one-to-one, and no selected input is missing an indicator value.
- Physician totals reconcile to their MD and DO components. Rate and percentage checks each use their own source denominator rather than a shared population figure.
- The four committed Massachusetts source slices match the SHA-256 hashes pinned in `data/source_register.json`. Re-running `ma-access fetch` re-extracts identical slices from the cached national downloads, so an upstream change surfaces for review instead of silently altering results.
- Suppressed and unavailable source values are carried as missing, never as zero. Incomplete statewide benchmark inputs stop the run rather than producing a partial answer.

## Analytical checks

Automated regression and reconciliation checks cover FIPS grain and coverage, suppressed values, controlled margins of error, denominator weighting, physician reconciliation, screening boundaries, missing scenario decisions, sensitivity outcomes, packaged metric agreement, and the two-page memo contract.

A separate set of checks runs against the installed package outside the source checkout, confirming the analysis behaves the same when installed as a dependency rather than run from the working tree. `pip check` reports no broken requirements.

## Reproduction

A clean clone installed from `requirements-lock.txt` and the project package. The `run`, `memo` and `dashboard` commands all succeeded, and SQL package resources resolved correctly. Generated CSV, JSON, workbook XML and PDF bytes matched the checked-in outputs.

Database, ZIP-container and Hyper binary bytes are **not** asserted to be deterministic. Tabular values are.

## Dashboard and memo

- Hyper read-back verified 5,625 dashboard rows: 56 county/indicator comparison rows plus 5,569 map vertices. Map rows carry no indicator value, which prevents map fan-out.
- Tableau rendering was **verified manually**, not automatically: the workbook was opened in Tableau Public 2026.2.2, and the county map and all four comparison views render without errors. Chart transport values and panel filters were checked programmatically. No automated visual or interaction check is claimed.
- The decision memo is exactly two pages, both visually inspected for clipping, overlap and legibility.

## Privacy

Source data are public county aggregates and boundary geometry. No patient-level or clinician-level records are included. A scan of repository contents found no absolute machine paths, credential patterns, or broken local Markdown links.

## What this does not establish

These checks confirm that the pipeline computes what it claims to compute, reproducibly. They do not validate the underlying premise: that the chosen indicators measure primary-care access. Physician headcounts are not appointment availability, and a county appearing on the shortlist is a prompt to investigate, not evidence of unmet need. See [LIMITATIONS.md](LIMITATIONS.md).
