# Data Dictionary

## Raw file: `data/raw/Atlantic_Spain.csv`
| Column | Type in source | Meaning | Notes |
|---|---|---|---|
| date | text dd-mm-yyyy | Snapshot date | 18 May 2024 to 15 Oct 2024 |
| position | integer | Playlist rank on that date | 1 = best. Valid range 1–50 |
| song | text | Track title as shown | Original spelling and case kept |
| artist | text | Artist credit as shown | Collaborator credits differ between rows for some songs |
| popularity | integer | Spotify-style popularity score (0–100) | 0 is treated as missing |
| duration_ms | integer | Track duration in milliseconds | Range 118,693–444,631 |
| album_type | text | `album` or `single` | Can change over time for a song |
| total_tracks | integer | Tracks on the release | Range 1–49 |
| is_explicit | text TRUE/FALSE | Explicit-content flag | Can change over time for a song |
| album_cover_url | text | Artwork URL | Not used in analysis; dashboard does not depend on it |

## Processed: `data/processed/spain_top50_clean.csv` (one row per song-date)
| Column | Meaning |
|---|---|
| source_row | Line number in the raw file (header = line 1) |
| date, position, song, artist, popularity, duration_ms, album_type, total_tracks, is_explicit, album_cover_url | Typed copies of the originals (text originals are unchanged) |
| song_norm, artist_norm | Normalised title / artist credit |
| song_key | Song identity: `song_norm || artist_norm` |
| popularity_zero_flag | True where popularity == 0 |
| popularity_valid | popularity with 0 set to missing |
| warn_popularity, warn_duration, warn_total_tracks | Soft validation warnings (row kept) |
| dup_exact_row, dup_date_position, dup_date_song_key | Duplicate flags (no duplicates found) |
| date_row_count | Number of rows on this date |
| snapshot_complete | True if the date has exactly 50 unique positions 1–50 |
| shared_title_flag | Title also credited to another artist string; not merged |
| canonical_album_type, canonical_is_explicit, canonical_duration_ms, canonical_total_tracks | Song-level canonical values (see methodology §3) |
| any_attribute_conflict | Song has at least one conflicting attribute |

## Processed: `data/processed/song_master.csv` (one row per song_key)
Original example text, normalised keys, canonical attributes and per-attribute conflict flags (`conflict_*`).

## Exports: `outputs/exports/`
| File | Grain | Contents |
|---|---|---|
| song_lifecycle.csv | song | Lifecycle metrics, censoring flags, stage and stage reason |
| daily_rotation.csv | valid transition | Entries, exits, re-entries, rates, turnover, retention |
| monthly_rotation.csv | month | Averages per day and monthly totals |
| group_explicit.csv / group_album.csv | group | Descriptive summaries |
| relationships.csv | attribute × outcome | Spearman results with Holm adjustment |
| hypothesis_family_holm.csv | test | Raw and family-adjusted p-values |
| popularity_by_tenure.csv | tenure bucket | Popularity and within-song deviation by days since first observed appearance |

## Key lifecycle columns (song_lifecycle.csv)
| Column | Meaning |
|---|---|
| first_seen, last_seen | First and last observed dates |
| left_censored | Present on 18 May 2024 (entry unobserved) |
| right_censored / status | Active at window end (not an exit) / Exited (observed) |
| exit_date | Day after last appearance, for observed exits |
| n_appearances | Cumulative observed dates |
| n_runs, reentries | Continuous runs and re-entries (runs - 1) |
| longest_run_days, current_run_start, current_run_days | Run-length measures |
| gap_days_within_tenure | Calendar days inside the span not observed on the playlist |
| best_position, peak_date, time_to_peak_days | Best rank and timing (time measured from first observed date) |
| mean_position, median_position, rank_volatility_sd | Rank distribution (lower = better) |
| popularity_first/max/mean/last/change, popularity_valid_obs | Popularity summaries (zeros excluded) |
| lifecycle_stage, stage_reason | Rule-based stage and the reason |
