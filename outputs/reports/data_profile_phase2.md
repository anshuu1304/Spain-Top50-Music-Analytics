# Dataset Profile — Atlantic_Spain.csv (Phase 2)

Source: Google Drive file 1SJDw9bbNnxCVNyRSRJdKhj7r0xEftPw_ ("Atlantic_Spain.csv", text/csv, 3,707,510 bytes, modified 2026-01-12), read via the Google Drive connector. Stored unmodified at data/raw/Atlantic_Spain.csv (extracted from the connector's JSON `fileContent`).

## Structure
- 7,508 data rows x 10 columns; all rows have 10 fields.
- Columns: date, position, song, artist, popularity, duration_ms, album_type, total_tracks, is_explicit, album_cover_url.
- Raw header contains escaped underscores (`duration\_ms`) and trailing spaces in the last column name; normalised on load.

## Date coverage
- 18 May 2024 to 15 Oct 2024: 151 distinct dates, 151 calendar days, no gaps.
- Note: the observation window is about 5 months in 2024. It is not current data.

## Playlist completeness
- 150 of 151 dates have exactly 50 entries.
- 15 Oct 2024 has only 8 rows (incomplete snapshot). Treat as partial; exclude from churn calculations that need a full snapshot.

## Validity
- Positions: all integers 1–50, no gaps or out-of-range values.
- No blank cells, no unparseable dates.
- Popularity 0–100; duration_ms 118,693–444,631; total_tracks 1–49. All numeric.
- No exact duplicate rows; no duplicate (date, position); no duplicate (date, song, artist).
- album_type: single (4,773), album (2,735). No unexpected categories.
- is_explicit: FALSE (4,617), TRUE (2,891). Stored as text; needs boolean normalisation.
- album_cover_url: all https.

## Identity and consistency issues (to handle in preprocessing, not silently)
- 188 unique (song, artist) pairs; 181 unique song titles; 101 unique artist strings.
- 7 song titles are credited to more than one artist string (e.g. "BABY HELLO" by "Rauw Alejandro" and "Rauw Alejandro & Bizarrap"; "miamor" by "Aitana" and "Aitana & Rels B"). These look like the same track with different collaborator credits. They are not merged automatically. Decision needed on identity rule.
- No artist-name case or whitespace variants.
- Attribute conflicts within the same (song, artist): album_type varies for 4 pairs; is_explicit varies for 3; duration_ms varies for 2; total_tracks varies across 13 song titles. Needs investigation before lifecycle attributes are attached.

## Open items for Phase 3
1. Decide song identity rule (recommended: normalised (song, artist) key; keep the 7 shared titles as separate identities, documented).
2. Resolve attribute conflicts: take the modal value per song with a logged conflict count, or flag them.
3. Exclude or flag 15 Oct 2024 as an incomplete snapshot.
4. Right-censoring: the window ends 15 Oct 2024, so songs present on that date are censored.
