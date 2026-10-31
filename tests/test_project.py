"""Project-level reconciliation tests against the REAL dataset (skipped if the file is absent)."""
import pandas as pd
import pytest

from src.config import RAW_DATA_PATH
from src.data_loader import load_raw
from src.preprocessing import build_clean_rows
from src.lifecycle import build_lifecycle, observation_window
from src.churn_analysis import daily_rotation

pytestmark = pytest.mark.skipif(not RAW_DATA_PATH.exists(), reason="raw dataset not present")


@pytest.fixture(scope="module")
def real():
    clean, rejected, _ = build_clean_rows(load_raw(RAW_DATA_PATH))
    return clean, rejected


def test_no_rows_lost(real):
    clean, rejected = real
    assert len(clean) == 7508 and len(rejected) == 0


def test_window_and_partial_day(real):
    clean, _ = real
    win = observation_window(clean)
    assert win["first_date"] == pd.Timestamp("2024-05-18")
    assert win["window_end"] == pd.Timestamp("2024-10-14")          # last COMPLETE snapshot
    assert win["partial_dates"] == [pd.Timestamp("2024-10-15")]
    assert len(win["complete_dates"]) == 150


def test_active_songs_match_final_complete_snapshot(real):
    clean, _ = real
    lc = build_lifecycle(clean)
    final = set(clean.loc[clean["date"] == "2024-10-14", "song_key"])
    assert len(final) == 50
    assert set(lc.loc[lc["right_censored"], "song_key"]) == final


def test_entries_and_exits_reconcile_with_lifecycle(real):
    clean, _ = real
    lc = build_lifecycle(clean)
    d = daily_rotation(clean)
    # every complete snapshot has 50 songs, so entries must equal exits each day
    assert (d["entries"] == d["exits"]).all()
    # total entry events = runs that began after the first observed date
    total_runs = int(lc["n_runs"].sum())
    left = int(lc["left_censored"].sum())
    assert int(d["entries"].sum()) == total_runs - left
    # total exit events = runs that ended before the window end (i.e. re-entries + observed exits)
    exited = int((~lc["right_censored"]).sum())
    assert int(d["exits"].sum()) == int(lc["reentries"].sum()) + exited


def test_no_transition_uses_partial_day(real):
    clean, _ = real
    d = daily_rotation(clean)
    assert pd.Timestamp("2024-10-15") not in set(d["date"])


def test_every_appearance_accounted_for(real):
    clean, _ = real
    lc = build_lifecycle(clean)
    assert int(lc["n_appearances"].sum()) == len(clean)


def test_popularity_and_duration_ranges(real):
    clean, _ = real
    assert clean["popularity"].between(0, 100).all()
    assert clean["duration_ms"].between(118_693, 444_631).all()


def test_full_analysis_runs_and_has_no_missing_core_kpis(real):
    from src.preprocessing import song_master
    from src.insights import build_all
    clean, _ = real
    out = build_all(clean, song_master(clean))
    k = out["results"]["kpis"]
    for name in ["avg_days_on_playlist_cumulative_appearances", "average_peak_position",
                 "avg_playlist_churn_rate_pct_per_day", "retention_stability_index"]:
        assert pd.notna(k[name]), name
    # Phase-level invariant: album-type comparison is computed on observed-entry songs only
    comp = out["results"]["comparisons"][1]
    assert comp["appearances_MW"]["n_a"] + comp["appearances_MW"]["n_b"] == int((~out["song_frame"].left_censored).sum())
