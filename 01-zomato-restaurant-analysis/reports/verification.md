# Verification record

Verified on 2026-10-08 with Python 3.13.5, macOS arm64. Direct dependencies are pinned in requirements.txt; the full installed environment is in requirements-lock.txt. The Ubuntu CI workflow is included but has not been run on GitHub.

- Executed the complete cleaning → DuckDB → report → EDA pipeline against the included raw files.
- Executed all ten SQL queries; independently reconciled raw row counts, rated-only averages, delivery percentages, high-rating booking counts, country/city totals and cuisine counts using pandas.
- Five automated test groups passed, including duplicate/missing/invalid-input checks and Streamlit's AppTest for default values, country, rated status, combined city/delivery filters and empty results.
- Executed all three notebooks without cell errors using the current environment's Python kernel.
- Opened the running Streamlit dashboard in a browser and visually checked its metrics, tabs and charts. Reviewed all six static figures for layout and readable labels.
- Extracted the release ZIP into a fresh temporary directory, then successfully reran the pipeline, tests and all notebooks there. Execution used the installed dependencies but no original-project data paths.
- Confirmed that all 12 generated CSV files, six figures, quality audit, findings and README reproduce byte-for-byte after rebuilding the extracted copy.
- ZIP integrity check passed. Virtual environments, bytecode, caches, temporary files and original personal folder paths are excluded from the release.

## Test result

```
.....                                                                    [100%]
5 passed in 1.12s
```

## Confirmed snapshot metrics

9,551 restaurants; 7,403 rated; 2,148 unrated; 15 countries; 1,380 ratings ≥4.0; 287 of those offer booking (20.80%). Nine missing cuisines, 18 zero costs and 497 zero-coordinate pairs are retained and documented.

Limitations: No Power BI artifact, public deployment or GitHub upload is claimed. Historical provenance, collection date and redistribution license were not supplied. See README.md for data limitations and public-sharing considerations.

## Dashboard screenshot update

Added reports/figures/dashboard.png from the running Streamlit dashboard and embedded it in README.md. The screenshot is a static preview, separate from the six generated EDA figures. All five test groups passed after the update.
