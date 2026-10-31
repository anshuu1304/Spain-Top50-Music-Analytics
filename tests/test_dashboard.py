"""Dashboard logic tests. Streamlit/Plotly are NOT required: the filter layer is pure pandas."""
import pandas as pd
import pytest

from dashboard.filters import STAGES, Filters, apply_daily_filters, apply_song_filters, csv_bytes


@pytest.fixture
def lc():
    return pd.DataFrame({
        "song": ["Alpha", "Beta", "Gamma", "Delta"],
        "artist": ["Ann X", "Bob Y", "Ann Z", "Cy Q"],
        "first_seen": pd.to_datetime(["2024-05-18", "2024-06-01", "2024-08-01", "2024-09-01"]),
        "last_seen": pd.to_datetime(["2024-10-14", "2024-06-10", "2024-09-01", "2024-10-14"]),
        "lifecycle_stage": ["Mature Phase", "Exited", "Exited", "New Entry"],
        "is_explicit": [True, False, True, False],
        "album_type": ["album", "single", "album", "single"],
    })


def test_no_filters_returns_everything(lc):
    assert len(apply_song_filters(lc, Filters())) == 4


def test_date_filter_keeps_overlapping_spans(lc):
    f = Filters(pd.Timestamp("2024-06-05"), pd.Timestamp("2024-07-31"))
    out = apply_song_filters(lc, f)
    # Alpha spans the whole window (overlaps); Beta ended 2024-06-10 (overlaps); Gamma starts after range
    assert set(out["song"]) == {"Alpha", "Beta"}


def test_invalid_date_range_raises(lc):
    with pytest.raises(ValueError):
        apply_song_filters(lc, Filters(pd.Timestamp("2024-10-01"), pd.Timestamp("2024-01-01")))


def test_stage_and_explicit_and_album_filters(lc):
    assert set(apply_song_filters(lc, Filters(stages=["Exited"]))["song"]) == {"Beta", "Gamma"}
    assert set(apply_song_filters(lc, Filters(explicit="Explicit"))["song"]) == {"Alpha", "Gamma"}
    assert set(apply_song_filters(lc, Filters(explicit="Clean"))["song"]) == {"Beta", "Delta"}
    assert set(apply_song_filters(lc, Filters(album_type="single"))["song"]) == {"Beta", "Delta"}


def test_artist_and_song_search_case_insensitive(lc):
    assert set(apply_song_filters(lc, Filters(artist_query="ANN"))["song"]) == {"Alpha", "Gamma"}
    assert set(apply_song_filters(lc, Filters(song_query="elt"))["song"]) == {"Delta"}


def test_empty_result_is_handled(lc):
    out = apply_song_filters(lc, Filters(song_query="does-not-exist"))
    assert out.empty


def test_empty_stage_selection_returns_empty(lc):
    assert apply_song_filters(lc, Filters(stages=[])).empty


def test_daily_filter(lc):
    daily = pd.DataFrame({"date": pd.to_datetime(["2024-06-01", "2024-07-01", "2024-08-01"]), "entries": [1, 2, 3]})
    out = apply_daily_filters(daily, Filters(pd.Timestamp("2024-06-15"), pd.Timestamp("2024-07-15")))
    assert out["entries"].tolist() == [2]


def test_csv_export_round_trip(lc):
    raw = csv_bytes(lc[["song", "artist"]])
    back = pd.read_csv(pd.io.common.BytesIO(raw))
    assert list(back.columns) == ["song", "artist"] and len(back) == 4


def test_stage_vocabulary_matches_spec():
    for s in ["New Entry", "Growth Phase", "Peak Phase", "Mature Phase", "Decline Phase"]:
        assert s in STAGES
