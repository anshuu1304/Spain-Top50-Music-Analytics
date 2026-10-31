"""View-model tests on the REAL dataset: each filter must change the numbers it claims to change."""
import datetime as dt

import pandas as pd
import pytest

from dashboard import views
from dashboard.filters import Filters, apply_daily_filters, apply_song_filters
from src.churn_analysis import daily_rotation
from src.config import RAW_DATA_PATH
from src.insights import build_all
from src.lifecycle import build_lifecycle
from src.maturity_analysis import song_frame
from src.preprocessing import build_clean_rows, song_master
from src.data_loader import load_raw

pytestmark = pytest.mark.skipif(not RAW_DATA_PATH.exists(), reason="raw dataset not present")


@pytest.fixture(scope="module")
def world():
    clean, _, _ = build_clean_rows(load_raw(RAW_DATA_PATH))
    master = song_master(clean)
    out = build_all(clean, master)
    return {"clean": clean, "master": master, "sf": out["song_frame"], "daily": out["daily"],
            "surv": out["survival"], "results": out["results"]}


def test_explicit_filter_matches_canonical_counts(world):
    sf = world["sf"]
    ex = apply_song_filters(sf, Filters(explicit="Explicit"))
    cl = apply_song_filters(sf, Filters(explicit="Clean"))
    assert len(ex) == int(sf["is_explicit"].sum())
    assert len(cl) == int((~sf["is_explicit"]).sum())
    assert len(ex) + len(cl) == len(sf)


def test_album_filter_matches_counts(world):
    sf = world["sf"]
    assert len(apply_song_filters(sf, Filters(album_type="album"))) == int((sf.album_type == "album").sum())
    assert len(apply_song_filters(sf, Filters(album_type="single"))) == int((sf.album_type == "single").sum())


def test_kpis_change_when_filter_changes(world):
    sf = world["sf"]
    all_k = views.kpi_summary(sf)
    single_k = views.kpi_summary(apply_song_filters(sf, Filters(album_type="single")))
    assert all_k["songs"] == 188
    assert single_k["songs"] < all_k["songs"]
    assert single_k["avg_appearances"] != all_k["avg_appearances"]


def test_active_and_exited_partition(world):
    k = views.kpi_summary(world["sf"])
    assert k["active"] == 50 and k["exited"] == 138 and k["active"] + k["exited"] == k["songs"]


def test_date_filter_restricts_daily_and_monthly(world):
    f = Filters(pd.Timestamp("2024-07-01"), pd.Timestamp("2024-07-31"))
    d = apply_daily_filters(world["daily"], f)
    assert d["date"].min() >= pd.Timestamp("2024-07-01") and d["date"].max() <= pd.Timestamp("2024-07-31")
    m = views.monthly_from(d)
    assert list(m["month"]) == ["2024-07"]


def test_empty_result_pages_return_empty_not_error(world):
    sf = world["sf"]
    none = apply_song_filters(sf, Filters(song_query="no-such-song-xyz"))
    assert views.kpi_summary(none) == {"songs": 0}
    assert views.top_songs(none).empty
    assert views.album_size_table(none).empty
    assert views.duration_table(none).empty
    assert views.stage_counts(none)["songs"].sum() == 0


def test_album_size_bands_cover_all_albums(world):
    sf = world["sf"]
    t = views.album_size_table(sf)
    assert int(t["songs"].sum()) == int((sf.album_type == "album").sum())


def test_duration_quartiles_cover_all_songs(world):
    t = views.duration_table(world["sf"])
    assert int(t["songs"].sum()) == len(world["sf"])
    assert len(t) == 4


def test_fresh_vs_established_partitions_observed_entries(world):
    sf = world["sf"]
    end = pd.Timestamp(world["results"]["window"]["window_end"])
    t = views.fresh_vs_established(sf, end)
    assert int(t["songs"].sum()) == int((~sf.left_censored).sum())


def test_recent_entries_are_observed_and_within_window(world):
    sf = world["sf"]
    end = pd.Timestamp(world["results"]["window"]["window_end"])
    r = views.recent_entries(sf, end)
    assert len(r) > 0
    assert (r["first_seen"] > end - pd.Timedelta(days=14)).all()


def test_stage_counts_sum_to_active(world):
    sc = views.stage_counts(world["sf"])
    assert int(sc["songs"].sum()) == 50
    assert set(sc["stage"]) == set(views.STAGE_ORDER)


def test_song_runs_reconcile_with_reentries(world):
    sf = world["sf"]
    reentrant = sf[sf["reentries"] > 0].iloc[0]
    runs = views.song_runs(world["clean"], reentrant["song_key"])
    assert len(runs) == reentrant["n_runs"]
    assert int(runs["days"].sum()) == int(reentrant["n_appearances"])   # every appearance sits in exactly one run


def test_data_quality_checks_match_pipeline(world):
    from src.preprocessing import attribute_conflicts
    raw = load_raw(RAW_DATA_PATH)
    dq = views.data_quality_tables(raw, world["clean"], world["master"], attribute_conflicts(world["clean"]), pd.DataFrame())
    checks = dict(zip(dq["checks"]["check"], dq["checks"]["result"]))
    assert checks["Rows loaded"] == "7,508"
    assert checks["Dates with a complete 50-song snapshot"] == "150 of 151"
    assert checks["Popularity recorded as 0 (treated as missing)"] == "61"
