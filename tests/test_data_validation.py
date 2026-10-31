"""Cleaning and validation tests using small synthetic raw CSVs written to tmp_path."""
import pandas as pd
import pytest

from src.data_loader import load_raw, normalise_header
from src.data_validation import invalid_rank, parse_bool, parse_dates, snapshot_completeness
from src.preprocessing import (
    attach_canonical, attribute_conflicts, build_clean_rows, normalise_text, song_master,
)

HEADER = "date,position,song,artist,popularity,duration_ms,album_type,total_tracks,is_explicit,album_cover_url"


def write_csv(tmp_path, lines):
    p = tmp_path / "raw.csv"
    p.write_text(HEADER.replace("duration_ms", "duration\\_ms") + "  \n" + "\n".join(lines) + "\n", encoding="utf-8")
    return p


def line(date="01-01-2024", pos=1, song="Song A", artist="Artist X", pop=50, dur=200000,
         atype="single", tt=1, exp="FALSE", cover="https://x/y"):
    return f"{date},{pos},{song},{artist},{pop},{dur},{atype},{tt},{exp},{cover}"


def test_normalise_header_handles_escaped_underscore_and_spaces():
    assert normalise_header("duration\\_ms") == "duration_ms"
    assert normalise_header("album_cover_url  ") == "album_cover_url"


def test_load_raw_missing_file_and_missing_column(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_raw(tmp_path / "nope.csv")
    p = tmp_path / "bad.csv"
    p.write_text("date,position\n01-01-2024,1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_raw(p)


def test_normalise_text_casefold_whitespace_and_nfc():
    assert normalise_text("  ROSALÍA  ") == "rosalía"
    assert normalise_text("Rosalía") == normalise_text("ROSALÍA")  # decomposed accent
    assert normalise_text(None) == ""


def test_date_position_bool_and_rank_validation():
    s = pd.Series(["18-05-2024", "31-02-2024", "bad"])
    parsed = parse_dates(s)
    assert parsed.iloc[0] == pd.Timestamp("2024-05-18")
    assert parsed.isna().tolist() == [False, True, True]
    assert parse_bool(pd.Series(["TRUE", "false", "maybe"])).tolist() == [True, False, pd.NA]
    pos = pd.Series([1, 50, 0, 51, None], dtype="Int64")
    assert invalid_rank(pos).tolist() == [False, False, True, True, True]


def test_quarantine_invalid_rows_and_keep_valid(tmp_path):
    p = write_csv(tmp_path, [
        line(),
        line(date="31-13-2024", song="Bad Date"),
        line(pos=99, song="Bad Rank"),
    ])
    clean, rejected, log = build_clean_rows(load_raw(p))
    assert len(clean) == 1 and len(rejected) == 2
    assert set(rejected["song"]) == {"Bad Date", "Bad Rank"}
    assert set(rejected["reject_reason"]) >= {"invalid_date;", "invalid_position;"}


def test_duplicates_flagged_not_dropped(tmp_path):
    p = write_csv(tmp_path, [line(), line()])        # exact duplicate
    clean, _, _ = build_clean_rows(load_raw(p))
    assert len(clean) == 2 and clean["dup_exact_row"].all()
    assert clean["dup_date_position"].all()


def test_same_title_different_artists_not_merged(tmp_path):
    p = write_csv(tmp_path, [
        line(song="BABY HELLO", artist="Rauw Alejandro", pos=1),
        line(song="Baby Hello", artist="Rauw Alejandro & Bizarrap", pos=2),
    ])
    clean, _, _ = build_clean_rows(load_raw(p))
    assert clean["song_key"].nunique() == 2
    assert clean["shared_title_flag"].all()


def test_incomplete_snapshot_is_flagged(tmp_path):
    lines = [line(date="15-10-2024", pos=i, song=f"S{i}") for i in range(1, 9)]
    p = write_csv(tmp_path, lines)
    clean, _, _ = build_clean_rows(load_raw(p))
    assert (~clean["snapshot_complete"]).all()
    assert (clean["date_row_count"] == 8).all()


def test_complete_snapshot_detection():
    rows = pd.DataFrame({"date": [pd.Timestamp("2024-01-01")] * 50 + [pd.Timestamp("2024-01-02")] * 49,
                         "position": list(range(1, 51)) + list(range(1, 50))})
    comp = snapshot_completeness(rows).set_index("date")
    assert bool(comp.loc["2024-01-01", "complete"]) is True
    assert bool(comp.loc["2024-01-02", "complete"]) is False
    assert comp.loc["2024-01-02", "missing_positions"] == 1


def test_attribute_conflicts_and_canonical_are_documented(tmp_path):
    # album -> single one-way switch; canonical = most frequent, tie -> earliest
    lines = [line(date="01-01-2024", pos=1, atype="single"),
             line(date="02-01-2024", pos=1, atype="single"),
             line(date="03-01-2024", pos=1, atype="album"),
             line(date="04-01-2024", pos=1, atype="album"),
             line(date="05-01-2024", pos=1, atype="album")]
    clean, _, _ = build_clean_rows(load_raw(write_csv(tmp_path, lines)))
    conf = attribute_conflicts(clean)
    assert set(conf["attribute"]) == {"album_type"}
    assert set(conf["pattern"]) == {"one_way_switch"}
    master = song_master(clean)
    assert master.iloc[0]["canonical_album_type"] == "album"   # 3 rows vs 2
    assert bool(master.iloc[0]["conflict_album_type"])
    # originals preserved
    attached = attach_canonical(clean, master)
    assert list(attached["album_type"]) == ["single", "single", "album", "album", "album"]


def test_tie_break_prefers_earliest_value(tmp_path):
    lines = [line(date="01-01-2024", pos=1, atype="single"),
             line(date="02-01-2024", pos=1, atype="album")]
    clean, _, _ = build_clean_rows(load_raw(write_csv(tmp_path, lines)))
    assert song_master(clean).iloc[0]["canonical_album_type"] == "single"


def test_interleaved_conflict_is_labelled(tmp_path):
    lines = [line(date="01-01-2024", pos=1, tt=1),
             line(date="02-01-2024", pos=1, tt=5),
             line(date="03-01-2024", pos=1, tt=1)]
    clean, _, _ = build_clean_rows(load_raw(write_csv(tmp_path, lines)))
    conf = attribute_conflicts(clean)
    assert conf["pattern"].iloc[0] == "interleaved"
