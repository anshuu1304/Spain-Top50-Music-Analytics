# QA Report

Date: 30 October 2026 (submission-day review). Scope: the 2024 Spain Top 50 analysis.

## 1. Tests executed
| Suite | Tests | Result | What it covers |
|---|---|---|---|
| tests/test_data_validation.py | 12 | 12 passed | Header handling, loading errors, text normalisation (NFC, casefold), date/bool/rank validation, quarantine, duplicate flags, shared titles, incomplete snapshots, attribute conflicts and canonical rule, tie-break, interleaved pattern |
| tests/test_lifecycle.py | 14 | 14 passed | Run splitting, re-entry and censoring on a hand-built 6-day scenario, observed exit date, time to peak, stage rules (parametrised), new-entry and re-entry rules |
| tests/test_churn.py | 5 | 5 passed | Entries, exits, re-entries, retention and turnover against hand-calculated values; partial snapshot creates no transition; gaps are not bridged; monthly totals |
| tests/test_maturity.py | 12 | 12 passed | Kaplan–Meier (hand-computed table and median), log-rank (identical and clearly different groups), Mann–Whitney rank-biserial extremes, Spearman, Holm (hand-computed), chi-square Cramér's V, seeded permutation test, zero-popularity handling |
| tests/test_project.py | 8 | 8 passed | Real data: 7,508 rows kept, window and partial day, active songs equal the final complete snapshot, entries and exits reconcile with lifecycle totals, every appearance accounted for, full analysis runs with core KPIs present |
| tests/test_dashboard.py | 10 | 10 passed | Pure-pandas filter logic: date overlap, invalid range, stage/explicit/album filters, search, empty results, CSV round-trip |
| tests/test_views.py | 13 | 13 passed | Dashboard view models on the real dataset: explicit and album filters match canonical counts, KPIs respond to filters, active/exited partition, date filter on daily and monthly series, empty-result states, duration and album-size coverage, data-quality checks match the pipeline |
| tests/test_app_smoke.py | 6 | 6 passed | Headless smoke test of `app.py` with stubbed Streamlit and Plotly (code paths only; no browser): default view, empty selection, explicit filter, narrow date range with no match, reset, missing dataset error |
| **Total** | **80** | **80 passed, 0 failed** | Run with `python3 -m pytest -q tests` (80 collected cases from 75 test functions; some are parametrised) |

Each reported pass corresponds to an executed test in this environment.

## 2. Not executed (and why)
| Item | Status | Reason |
|---|---|---|
| Streamlit app launch (`streamlit run app.py`) | **Not run** | Streamlit is not installed, and the sandbox cannot reach PyPI |
| Plotly charts in `dashboard/charts.py` | **Not run** | Plotly is not installed |
| Interactive filters, widgets, CSV download buttons in the browser | **Not run** | Requires the app to be running |
| `app.py` compile | Passed | `python3 -m py_compile app.py dashboard/*.py` |
| Responsive layout, screen sizes | **Not checked** | Requires a browser |
| statsmodels models | **Not used** | Not installed; not required by any analysis |

The Streamlit dashboard is therefore **unverified in a running state**. Its data and filter logic are tested. Its user interface is not. Before submission, run `pip install -r requirements.txt`, then `streamlit run app.py`, and check every page.

## 3. Issues found and fixed during QA
| # | Issue | Severity | Fix |
|---|---|---|---|
| 1 | Test fixture placed the same song at two positions on one day, which went unnoticed | Medium | Rewrote the scenario with explicit placements and asserted appearance counts |
| 2 | "New Entry" counted songs returning after a gap, so re-entries were mislabelled | High | Requires the song's first run and an observed entry; re-entry test added |
| 3 | Explicit and album appearance comparisons were confounded by left-censoring (songs already charted on day 1) | High | Primary tests restricted to observed-entry songs; all-songs result kept as descriptive only. The explicit "significant" result disappeared |
| 4 | Chi-square invalid where expected counts < 5 | Medium | Permutation test (seeded) added where needed |
| 5 | Lifecycle stage tests included "Exited", so they measured right-censoring, not lifecycle | High | Stage tests restricted to active songs |
| 6 | Zero popularity values (61 rows) distorted popularity means | High | Zero treated as missing (`popularity_valid`); original kept; test added |
| 7 | Album-size correlation was driven by album format (singles have 1 track) | High | Within-album analysis added and reported as the album-size result |
| 8 | 14 October 2024 wave (20 first appearances, 19 by one artist) was driving the album and stage results | High | Sensitivity analysis excluding the cohort; reported as a caveat. Album effect survives; stage association does not |
| 9 | Canonical attribute rule could hide version changes | Medium | Conflicts classified (one-way switch vs interleaved); alternative rule run as sensitivity |
| 10 | Pipeline entry point defined before the function it called | Low | Moved to end of file |
| 11 | Timeline figure title clipped | Low | Shortened |
| 12 | Cleanup command deleted the earlier checkpoint_02 ZIP by mistake | Low | Checkpoint 03 contains all current work. Checkpoints are rebuilt on each milestone |
| 13 | Stale "Environment" note in PROJECT_STATUS | Low | Updated |

## 4. Data integrity checks
- Row count preserved: 7,508 in, 7,508 clean, 0 rejected.
- Every appearance is accounted for in the lifecycle table (sum of appearances = 7,508).
- Entries reconcile: 198 = (188 songs − 50 present on day 1) + 60 re-entries.
- Exits reconcile: 198 = 138 observed exits + 60 re-entries.
- Active songs (50) equal the 14 October complete snapshot exactly.
- Analysis is reproducible: `python3 run_pipeline.py` regenerates all outputs. Random procedures use fixed seeds.

## 5. Risk assessment
| Risk | Level | Mitigation |
|---|---|---|
| Dashboard fails to run in the reviewer's environment | Medium | Requirements pinned by name; run instructions in README; UI unverified (see §2) |
| Results mistaken for 2026 market behaviour | High | Stated on every page, in every document and in the paper |
| Conclusions driven by one release wave | High | Sensitivity analysis; wave identified and disclosed |
| Multiple-comparison false positives | Medium | Holm correction across 27 tests; raw and adjusted p-values both reported |
| Popularity zero misread as a real score | Medium | Treated as missing; assumption documented |
| Shared-title songs merged or split incorrectly | Medium | Not merged; flagged for review |
| Incomplete snapshot read as exits | High | Excluded from transitions; unit-tested |
| Statistical significance overstated | Medium | Effect sizes and practical interpretation reported; "robust" claims limited to those that survive correction and sensitivity |

## 6. Final quality assessment
The analytics and dashboard view logic are verified by 80 executed tests, including hand-computed synthetic scenarios and reconciliation against the real data. Analytical conclusions have been checked against censoring, multiple comparisons and sensitivity to attribute rules and to the 14 October cohort.

The Streamlit dashboard is **not verified** in a running state. The headless smoke tests exercise its code paths with stubbed Streamlit and Plotly; they do not establish that the rendered page looks correct or that widgets behave in a browser. Before submission, it needs to be launched and every page and filter checked in a browser. This is the main outstanding item.

## 7. Remaining limitations
- Historical data only (May–October 2024), one playlist.
- Dashboard not executed here (see §2).
- PDFs were checked by text extraction and by rendering one page of the paper (tables and figure legible). The remaining pages were not rendered individually.
- Release dates are not in the dataset, so release-to-playlist timing cannot be measured.
