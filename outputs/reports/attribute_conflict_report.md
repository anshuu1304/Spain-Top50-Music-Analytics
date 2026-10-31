# Attribute Conflict Report

Conflicts are reported, never silently overwritten. Each song keeps its original rows.
A canonical value per song is chosen only for song-level analysis:
most frequent value across rows; ties go to the value that appeared first.
`one_way_switch` = values change once over time (consistent with a real version change);
`interleaved` = values alternate (possible data-entry noise).

Songs with at least one conflict: 9 of 188.

| Song | Artist | Attribute | Value | Rows | First | Last | Pattern |
|---|---|---|---|---|---|---|---|
| COCO LOCO | Maluma | album_type | album | 49 | 2024-08-26 | 2024-10-13 | one_way_switch |
| COCO LOCO | Maluma | album_type | single | 56 | 2024-07-01 | 2024-08-25 | one_way_switch |
| S91 | KAROL G | album_type | album | 21 | 2024-08-13 | 2024-09-04 | one_way_switch |
| S91 | KAROL G | album_type | single | 28 | 2024-07-16 | 2024-08-12 | one_way_switch |
| UN PREVIEW | Bad Bunny | album_type | album | 1 | 2024-10-14 | 2024-10-14 | one_way_switch |
| UN PREVIEW | Bad Bunny | album_type | single | 17 | 2024-09-27 | 2024-10-13 | one_way_switch |
| WHERE SHE GOES | Bad Bunny | album_type | album | 1 | 2024-10-14 | 2024-10-14 | one_way_switch |
| WHERE SHE GOES | Bad Bunny | album_type | single | 139 | 2024-05-21 | 2024-10-06 | one_way_switch |
| FERXXO 151 | Feid | duration_ms | 195320 | 12 | 2024-09-30 | 2024-10-11 | one_way_switch |
| FERXXO 151 | Feid | duration_ms | 195386 | 2 | 2024-10-12 | 2024-10-13 | one_way_switch |
| LUCES DE TECNO | Feid | duration_ms | 163786 | 12 | 2024-09-30 | 2024-10-11 | one_way_switch |
| LUCES DE TECNO | Feid | duration_ms | 164293 | 3 | 2024-10-12 | 2024-10-14 | one_way_switch |
| DESPECHÁ | ROSALÍA | is_explicit | False | 33 | 2024-05-22 | 2024-07-11 | one_way_switch |
| DESPECHÁ | ROSALÍA | is_explicit | True | 16 | 2024-07-12 | 2024-08-08 | one_way_switch |
| LAS BABYS | Aitana | is_explicit | False | 4 | 2024-06-09 | 2024-06-12 | one_way_switch |
| LAS BABYS | Aitana | is_explicit | True | 78 | 2024-06-13 | 2024-08-29 | one_way_switch |
| UN PREVIEW | Bad Bunny | is_explicit | False | 17 | 2024-09-27 | 2024-10-13 | one_way_switch |
| UN PREVIEW | Bad Bunny | is_explicit | True | 1 | 2024-10-14 | 2024-10-14 | one_way_switch |
| COCO LOCO | Maluma | total_tracks | 1 | 56 | 2024-07-01 | 2024-08-25 | one_way_switch |
| COCO LOCO | Maluma | total_tracks | 25 | 49 | 2024-08-26 | 2024-10-13 | one_way_switch |
| FERXXO 151 | Feid | total_tracks | 15 | 12 | 2024-09-30 | 2024-10-11 | one_way_switch |
| FERXXO 151 | Feid | total_tracks | 16 | 2 | 2024-10-12 | 2024-10-13 | one_way_switch |
| K-POP | Travis Scott & Bad Bunny & The Weeknd | total_tracks | 1 | 11 | 2024-07-23 | 2024-08-05 | interleaved |
| K-POP | Travis Scott & Bad Bunny & The Weeknd | total_tracks | 4 | 3 | 2024-07-26 | 2024-07-28 | interleaved |
| LUCES DE TECNO | Feid | total_tracks | 15 | 12 | 2024-09-30 | 2024-10-11 | one_way_switch |
| LUCES DE TECNO | Feid | total_tracks | 16 | 3 | 2024-10-12 | 2024-10-14 | one_way_switch |
| S91 | KAROL G | total_tracks | 1 | 28 | 2024-07-16 | 2024-08-12 | one_way_switch |
| S91 | KAROL G | total_tracks | 9 | 21 | 2024-08-13 | 2024-09-04 | one_way_switch |
| UN PREVIEW | Bad Bunny | total_tracks | 1 | 17 | 2024-09-27 | 2024-10-13 | one_way_switch |
| UN PREVIEW | Bad Bunny | total_tracks | 22 | 1 | 2024-10-14 | 2024-10-14 | one_way_switch |
| WHERE SHE GOES | Bad Bunny | total_tracks | 1 | 139 | 2024-05-21 | 2024-10-06 | one_way_switch |
| WHERE SHE GOES | Bad Bunny | total_tracks | 22 | 1 | 2024-10-14 | 2024-10-14 | one_way_switch |
