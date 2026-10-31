# Methodology

Scope: historical Spain Top 50 snapshots, 18 May 2024 to 15 October 2024. These data describe 2024 and do not describe 2026 market behaviour.

## 1. Data and cleaning
- Source: `Atlantic_Spain.csv` (Google Drive), 7,508 rows, 10 columns. Stored unmodified in `data/raw/`.
- Every field is read as text. Typed copies are created in `src/preprocessing.py`. Original text fields are kept.
- Header cleaning: escaped underscores (`duration\_ms`) and trailing spaces are removed from column names.
- Dates are parsed as `dd-mm-yyyy`. Positions, popularity, duration, track count and the explicit flag are converted and validated.
- Rows that fail hard validation (unparseable date, invalid position, unknown explicit flag) are quarantined in `data/processed/rejected_rows.csv`, not deleted. No rows were quarantined.

## 2. Song identity
- Primary identity: `song_key = normalised title || normalised artist credit`.
- Normalisation: Unicode NFC, whitespace collapsed, case-folded. Accents are kept (for example "rosalía").
- Different artist credits are **never** merged automatically, even if titles match. 14 songs share a title with another artist credit (`shared_title_flag`). Examples include "miamor" by Aitana and by Aitana & Rels B. These may be the same recording with different collaborator credits. This is a known limitation and needs manual review.
- Result: 188 song keys, 181 distinct normalised titles, 101 artist credits.

## 3. Attribute conflicts
- Checked attributes: `album_type`, `is_explicit`, `duration_ms`, `total_tracks`.
- 9 songs have at least one conflict (32 song-attribute-value rows). Each conflict is listed in `outputs/reports/attribute_conflicts.csv`.
- Each conflict is classified:
  - `one_way_switch`: values change once over time, consistent with a real version change (for example single to album, or clean to explicit).
  - `interleaved`: values alternate over time, which may indicate data-entry noise. One case (`total_tracks` for a K-POP track) is interleaved.
- Original values are never overwritten. A **canonical** value is used only for song-level analysis. The rule: most frequent value across rows; ties go to the value that appeared first.
- Sensitivity: an alternative rule ("ever" = any row carries the value) changes group membership for 2 songs (explicit) and 4 songs (album type). The album-type appearance result stays significant under both rules (p < 0.001). The explicit result is non-significant under both.

## 4. Popularity
- The recorded `popularity` value of 0 occurs on 61 rows and is outside the otherwise observed range (minimum non-zero value 3). It is treated as a missing-value marker: `popularity_valid` is missing and the original is kept. Analyses use `popularity_valid`.
- Popularity is a daily series per song, so trajectories over tenure are valid. Tenure analyses use within-song deviations from each song's own mean.

## 5. Observation window and snapshot completeness
- A complete snapshot has exactly 50 rows with positions 1 to 50 once each.
- 150 dates are complete. **15 Oct 2024 has only 8 rows** (positions 1 to 8, all by Bad Bunny). It is treated as an **incomplete snapshot**.
- The observation window for lifecycle logic ends at the last complete snapshot, **14 Oct 2024**.
- The missing 42 songs on 15 Oct are **not** treated as exits. No transition uses 15 Oct.
- Transitions use only consecutive calendar days where both dates are complete. Gaps are never bridged. The dataset has no missing calendar days.

## 6. Lifecycle definitions
- **Appearance**: a song observed on a date.
- **Continuous run**: a block of consecutive calendar days on which the song appears.
- **Re-entry**: a run that starts after an earlier run has ended. Re-entries = number of runs minus 1.
- **Cumulative appearances**: total observed dates on the playlist (not continuous).
- **Right-censored**: still present at window end (last appearance on 14 Oct or 15 Oct). Its tenure is a lower bound, and it is **not** treated as exited.
- **Left-censored**: present on the first observed date (18 May 2024). Its true entry is unknown, so entry-based measures are restricted to songs whose entry was observed (138 songs).
- **Exited (observed)**: last appearance on a complete date before 14 Oct, and absent on the next day. `exit_date = last appearance + 1 day`.
- **Time to peak**: days from first observed appearance to the first date of the best position. For left-censored songs this is measured from the window start, so only observed-entry songs are used for analysis.
- **Rank**: lower position number means better rank. Rank volatility = sample standard deviation of positions.

## 7. Lifecycle stage rules (active songs only)
Thresholds are in `src/config.py`. Stage is evaluated on the song's latest observation.

Applied in this order:
1. **New Entry**: the song's *first* run started within the last 7 observed calendar days (window end minus start < 7), and the entry was observed. A song returning after a gap is not a New Entry.
2. **Insufficient history**: fewer than 4 appearances.
3. Let *recent* be the last 4 positions in time order. `net_change = recent[first] - recent[last]` (positive = improvement). `worsening_steps` = number of the 3 steps where the position number increased.
4. **Decline Phase**: `net_change <= -5` **and** `worsening_steps >= 2`. Requiring at least 2 of 3 steps avoids classifying a song on one poor observation.
5. **Peak Phase**: latest position <= 10.
6. **Growth Phase**: `net_change >= 5` and latest position > 10.
7. **Mature Phase**: otherwise (stable outside the Top 10).

Songs that are not active at window end have status "Exited" (no active stage).

## 8. Rotation and churn (fixed 50-song playlist, N = 50)
For each valid transition from day d-1 to day d (both complete, consecutive):
- Entries = |S_d \ S_{d-1}|. Exits = |S_{d-1} \ S_d|. Retained = |S_d ∩ S_{d-1}|.
- Re-entries = entries whose song appeared on an observed date before day d-1. New entries = entries - re-entries.
- Entry rate % = entries / 50 × 100. Exit rate % = exits / 50 × 100.
- Daily turnover = (entries + exits) / 2 (per specification).
- Retention % = retained / 50 × 100.

**Consequence**: every complete snapshot contains exactly 50 songs, so entries always equal exits. Daily turnover therefore equals the daily entry count. This is a property of the fixed-size playlist, not a finding.

Monthly tables report averages per day, and totals for the replacements in the month. They are not cumulative turnover.

## 9. Statistical methods
- Survival: Kaplan–Meier estimates on the **first continuous run** of observed-entry songs. Event = run ended before the window end. Log-rank test for group comparisons.
- Two-group comparisons of continuous outcomes: Mann–Whitney U (two-sided). Effect size = rank-biserial correlation (−1 to 1; sign shows which group tends to be higher).
- Associations: Spearman rank correlation.
- Lifecycle stage distribution (active songs only): chi-square with Cramér's V. Because expected counts were below 5, a seeded permutation test (10,000 permutations, seed 42) is reported.
- Multiple comparisons: Holm step-down adjustment over the family of primary tests (explicit, album, duration, album size, popularity, and the within-album test). Both raw and adjusted p-values are reported.
- Medians: percentile bootstrap 95% CI (5,000 resamples, seed 42).
- Statistical significance is not treated as practical importance. Correlation is not treated as causation.

## 10. KPI framework
| # | KPI | Definition | Notes |
|---|---|---|---|
| 1 | Average days on playlist | Mean cumulative appearances across all 188 songs | Right-censored and left-truncated; treat as lower bound |
| 2 | Median observed playlist tenure | Kaplan–Meier median of first-run length (observed-entry songs) | Censored tail may leave the median undefined; reported when defined |
| 3 | Entry-to-peak time | Median days from first observed appearance to best position (observed-entry songs) | 60% are 0 days: best position was on the first observed day |
| 4 | Average playlist churn rate | Mean daily exit rate % over valid transitions | Equals mean entry rate by construction |
| 5 | Daily turnover | Mean (entries + exits)/2 | Equals mean daily entries in a fixed 50-song playlist |
| 6 | Retention Stability Index (RSI) | mean daily retention % ÷ (1 + CV of daily entries), where CV = sample SD / mean | Scale roughly 0–100; higher = more stable. A custom index, so interpret with care |
| 7 | Explicit lifecycle difference | Kaplan–Meier median first-run length, explicit minus clean (days), with log-rank test | Replaces a composite score: no non-arbitrary composite was justified |
| 8 | Single vs album longevity ratio | Median cumulative appearances, album ÷ single (observed-entry songs) | Ratio of medians, not of means |
| 9 | Average peak position | Mean of each song's best (lowest) position | 1 = best |
| 10 | Average re-entry frequency | Mean re-entries per song (all songs and observed-entry songs reported separately) | — |

## 11. Reproducibility
- `python3 run_pipeline.py` regenerates all processed data, reports, exports and figures from `data/raw/Atlantic_Spain.csv`.
- Random procedures use fixed seeds (42).
- No external API is used.
