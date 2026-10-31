# Spain Top 50 — Song Lifecycle, Playlist Rotation and Content Maturity (2024)

Client context: Atlantic Recording Corporation. Market: Spain.

**Scope:** historical analysis of Spain Top 50 daily snapshots from **18 May to 15 October 2024**. Findings describe 2024 and do not describe current (2026) market behaviour.

## What it does
- Cleans and validates the daily Top 50 file, keeping every original value and flagging problems rather than deleting them.
- Builds a song-level lifecycle: first/last appearance, continuous runs, re-entries, peak and time to peak, rank and popularity summaries.
- Handles censoring: songs already charted on the first day are *left-censored*; songs still charted at the end are *right-censored* and are not counted as exits.
- Measures playlist rotation (entries, exits, turnover, retention) on complete consecutive snapshots only.
- Compares explicit vs clean and album vs single tracks, and tests duration and album size, using Kaplan–Meier, log-rank, Mann–Whitney, Spearman and Holm correction.
- Produces figures, exports, a Streamlit dashboard, a research paper, an executive summary and a QA report.

## Project layout
```
app.py                  Streamlit dashboard (7 pages)
run_pipeline.py         End-to-end pipeline: cleaning, analysis, figures, exports
requirements.txt        Dependencies
src/                    Analytical core (loader, validation, preprocessing, lifecycle,
                        churn, maturity, popularity, statistics, insights, figures)
dashboard/              Filters (pure pandas), Plotly charts, styling, components
tests/                  80 pytest cases (synthetic edge cases + real-data reconciliation)
scripts/                Independent audit (standard library and scipy only; 23 checks)
data/raw/               Atlantic_Spain.csv (place the source file here)
data/processed/         Cleaned data, song master, rejected rows
outputs/reports/        Profile, attribute conflicts, cleaning log, results.json
outputs/exports/        Lifecycle, rotation, group summaries, Holm table
outputs/figures/        Static figures (PNG)
docs/                   Methodology, data dictionary, research paper, executive summary, QA report
checkpoints/            Milestone ZIP backups
```

## Installation

### macOS (Terminal, zsh)
Check the Python version first. It must be 3.10 or newer. If `python3` is missing or older, install Python 3.12 from python.org or with Homebrew (`brew install python@3.12`).
```bash
python3 --version
cd spain-top50-intelligence
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```
Run the remaining commands in the same Terminal window, with `.venv` active (the prompt shows `(.venv)`).

### Windows and Linux
```bash
cd spain-top50-intelligence
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Data
Place the source file at `data/raw/Atlantic_Spain.csv`. It has 10 columns (`date, position, song, artist, popularity, duration_ms, album_type, total_tracks, is_explicit, album_cover_url`). The file is the one supplied as Google Drive `Atlantic_Spain.csv`.

## Run the analysis
```bash
python3 run_pipeline.py
```
This regenerates `data/processed/`, `outputs/` and all figures from the raw file.

## Run the tests
```bash
python3 -m pytest -q tests
```
Expected: 80 passed (about 1 minute). The dashboard tests use stubs and do not start a browser.

## Run the independent audit
```bash
python3 scripts/independent_audit.py
```
Expected: `23/23 checks agree`.

## Run the dashboard
```bash
streamlit run app.py
```
Open the URL Streamlit prints (usually http://localhost:8501).

**Status:** the dashboard logic and filters are tested, but the interface was not run in the environment used to build this project. Check each page after launch (see `docs/qa_report.md` §2).

## Methodology and definitions
See `docs/methodology.md` for every definition, threshold and KPI formula. In brief:
- **Complete snapshot:** exactly 50 unique positions 1–50. 15 October 2024 has only 8 rows and is excluded from transitions.
- **Observation window:** 18 May to 14 October 2024 for lifecycle logic.
- **Lifecycle stages:** New Entry, Growth, Peak (top 10), Mature, Decline, plus "Insufficient history" for songs with fewer than 4 appearances.
- **Turnover:** (entries + exits) / 2 per day. In a fixed 50-song playlist this equals daily entries.

## Known limitations
- Historical 2024 data from one playlist. Results do not generalise to 2026 or to other charts.
- Release dates are not in the dataset.
- The 14 October 2024 entry wave (mostly one artist) affects album and stage comparisons. See the sensitivity analysis.
- Popularity 0 is treated as missing (assumption).
- 14 song titles credited to different artists are kept separate and need manual review.
- Associations are not causal.

## Deliverables
- `docs/research_paper.md` (and PDF)
- `docs/executive_summary.md` (and PDF)
- `docs/methodology.md`, `docs/data_dictionary.md`, `docs/qa_report.md`
- `outputs/reports/attribute_conflict_report.md`
- `outputs/figures/*.png`
- `docs/FINAL_QA_REPORT.md` (final verification; lists what was and was not tested)
- `docs/PROJECT_STATUS.md` (phase status and open items)
- `scripts/independent_audit.py` and `outputs/reports/independent_audit.txt` (23 of 23 checks agree with `results.json`)
