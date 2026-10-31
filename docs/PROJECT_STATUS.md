# Project Status

Last updated: 31 October 2026

## Scope and data period (important)
- All analysis covers the historical Spain Top 50 snapshots from 18 May 2024 to 15 Oct 2024.
- These are 2024 observations. They do NOT represent current 2026 market behaviour.
- The 31 October 2026 deadline is the submission date, not the data period.

## Status by phase
| Phase | Status | Where |
|---|---|---|
| 1 Setup and dataset acquisition | Done | Dataset from Google Drive (`Atlantic_Spain.csv`, 7,508 rows) in `data/raw/` |
| 2 Data audit | Done | `outputs/reports/data_profile_phase2.md` |
| 3 Cleaning and identity | Done | `src/data_loader.py`, `src/data_validation.py`, `src/preprocessing.py`, `outputs/reports/attribute_conflict_report.md` |
| 4 Lifecycle and churn | Done | `src/lifecycle.py`, `src/churn_analysis.py` |
| 5 Maturity and popularity | Done | `src/maturity_analysis.py`, `src/popularity_analysis.py`, `src/insights.py` |
| 6 Statistics and KPIs | Done | `src/statistical_analysis.py`, `outputs/reports/results.json`, `outputs/exports/hypothesis_family_holm.csv`; independent recomputation in `scripts/independent_audit.py` (23/23 checks agree) |
| 7 Visualisation | Done (static) | `outputs/figures/*.png` (8 figures) |
| 8 Dashboard | Written, **not run** | `app.py`, `dashboard/`. Streamlit and Plotly not installed in the build environment |
| 9 Paper and summary | Done | `docs/research_paper.md` + PDF, `docs/executive_summary.md` + PDF |
| 10 Testing and QA | Done (80 tests pass, headless); dashboard UI not browser-tested | `tests/`, `docs/qa_report.md` |
| 11 Packaging | Done | `README.md`, `requirements.txt`, checkpoint ZIPs |

## Open items before submission
1. **Run the Streamlit dashboard** (`pip install -r requirements.txt`, then `streamlit run app.py`) and check every page and filter. This was not possible in the build environment.
2. Obtain the full 15 Oct 2024 snapshot to confirm the 42 missing positions (currently excluded, not treated as exits).
3. Review the 14 shared-title song identities and 9 attribute conflicts with the data owner.
4. Investigate the 14 Oct 2024 entry wave (20 first appearances, 19 by Bad Bunny) using release metadata.

## Environment limitations
- The sandbox cannot reach PyPI. Installed: pandas, numpy, scipy, matplotlib, seaborn, openpyxl, pytest.
- Not installed: streamlit, plotly, statsmodels (statsmodels is not used).

## Final release
- Final QA: `docs/FINAL_QA_REPORT.md`. Test suite 80 passed. Independent audit 23/23 agree.
- Dashboard: code and headless tests only. **Not browser-tested.**

## Resume commands
    cd spain-top50-intelligence
    python3 run_pipeline.py          # cleaning, analysis, figures, exports
    python3 -m pytest -q tests       # expected: 80 passed
    streamlit run app.py             # dashboard (requires streamlit and plotly)
