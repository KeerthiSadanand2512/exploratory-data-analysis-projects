# Verification

Verified locally on 2026-10-10 using Python 3.13 on macOS.

- Full pipeline rebuilt from the included original 20,000-row CSV.
- Seven tests passed: five SQL/cleaning tests and two Streamlit interaction tests.
- All three notebook files executed successfully with outputs saved.
- Dashboard reads the included processed data and query results without network access.
- README computed findings regenerate from the pipeline.
- Streamlit dashboard screenshot retained from the working app; EDA figures regenerated from the current SQL results.
- Distribution checked for missing notebook outputs, broken local README links, ZIP corruption, and unwanted HTML files.

Run the same checks with `python -m src.pipeline`, `python -m unittest discover -s tests -v`, and `python scripts/execute_notebooks.py` from the project root.
