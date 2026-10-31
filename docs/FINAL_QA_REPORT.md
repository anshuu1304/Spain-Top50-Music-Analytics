# Final QA Report

Date: 31 October 2026. Scope: the historical Spain Top 50 analysis (18 May to 14 October 2024, with 15 October 2024 partial). These are 2024 observations and do not describe 2026 behaviour.

## 1. What was verified, and how

| Area | Method | Result |
|---|---|---|
| Checkpoint 08 integrity | `unzip -tq` on `checkpoints/checkpoint_08_final.zip` | Passed (earlier checkpoints kept) |
| Pipeline | `python3 run_pipeline.py` regenerated all outputs after the `shared_title_flag` change in `song_frame` | Completed |
| Full test suite | `python3 -m pytest -q tests` | **80 passed, 0 failed** (about 63 s) |
| Independent audit | `scripts/independent_audit.py`: standard library and scipy only, no imports from `src/` or `dashboard/`, reads the raw CSV | **23 of 23 checks agree** with `outputs/reports/results.json` (saved to `outputs/reports/independent_audit.txt`) |
| Dashboard view logic | `tests/test_views.py` on the real dataset | 13 passed: filters change the counts they claim to, KPIs respond to filters, empty states, date filter on daily and monthly data, data-quality checks |
| Dashboard code paths | `tests/test_app_smoke.py` runs `app.py` with stubbed Streamlit and Plotly | 6 passed. **Headless only: this checks that code paths run, not what a browser renders** |
| Hard-coded dashboard literals | Compared with the cleaned data | 8 rows on 15 Oct; 14 shared-title songs; 9 songs with attribute conflicts (32 song-attribute rows); 50 left-censored; 50 right-censored; 20 first appearances and 19 Bad Bunny on 14 Oct. All correct |
| Documents | Headline numbers in the paper, executive summary, QA report and README compared with `results.json` | Consistent after corrections (see section 3) |

## 2. Independent audit: headline numbers

Recomputed from the raw CSV, matching `results.json`:
- 150 complete snapshots; 15 Oct 2024 excluded (8 of 50 positions).
- 149 valid transitions; 198 entries; 198 exits; 60 re-entries.
- Mean daily turnover 1.3289 songs (2.6577% entry rate).
- 61 popularity-zero rows.
- 14 Oct 2024 cohort: 21 entries, 20 first appearances, 19 by Bad Bunny.
- Explicit vs clean (observed-entry songs, cumulative appearances): n = 80 / 58, medians 7.5 / 11, Mann–Whitney p = 0.073.
- Album vs single: n = 76 / 62, medians 4 / 26, Mann–Whitney p = 4.1 × 10⁻⁷.

**Definition note.** Cumulative appearances count every data row a song appears on, including the partial 15 October day. Rotation and transition calculations use complete days only. A first audit draft counted complete days only, which gave slightly different p-values (explicit 0.055, album 2.5 × 10⁻⁷). The pipeline definition is the one documented in `docs/methodology.md`, and the audit now uses it. No pipeline bug was found.

## 3. Corrections made in this review

- Test counts were stale in four places (61 in the QA report, README and status file, plus wrong per-file counts). The suite collects 80 cases from 75 test functions. All corrected.
- Added `tests/test_views.py` (13 tests) and `tests/test_app_smoke.py` (6 tests) to the QA report's test table, with honest descriptions.
- Removed a no-op assertion (`... or True`) from `tests/test_views.py` before the final run.
- Earlier in this release cycle, `song_frame` was missing `shared_title_flag`, which broke the explorer's song detail panel. Fixed and covered by the smoke test.

## 4. Not verified

- **The Streamlit dashboard has not been launched in a browser.** Streamlit and Plotly cannot be installed in this environment (PyPI is unreachable). No claim is made about rendering, layout, widget behaviour, Plotly chart appearance or CSV downloads in a browser.
- Responsive layout at phone widths: not checked.
- The full 15 October 2024 snapshot is not available, so the 42 missing positions remain excluded.

## 5. Open items for the owner

1. Install and launch the dashboard locally (commands in `README.md`), then check each of the seven pages and each filter.
2. Review the 14 shared-title songs and 9 songs with attribute conflicts with the data owner.
3. Investigate the 14 October 2024 wave (20 first appearances, 19 by Bad Bunny) against release metadata.
4. Obtain the full 15 October 2024 snapshot if available.

## 6. Verdict

The analysis, the statistics, the paper and the executive summary agree with each other and with an independent recomputation of the headline figures. The test suite passes. The dashboard is complete in code and tested headlessly, but it is **not verified in a browser**, and that is the main outstanding risk before it is presented as finished.
