"""Lifecycle tests: hand-computed expectations on synthetic data plus stage rules."""
import pandas as pd
import pytest

from src.lifecycle import build_lifecycle, classify_stage, continuous_runs
from tests.helpers import full_day, make_clean

D = [f"2024-01-0{i}" for i in range(1, 7)]  # D1..D6, all complete


def scenario():
    """Explicit per-day placements (no overlapping writes).

    alpha: D1 pos5, D2 pos5, D3 pos4, (absent D4,D5), D6 pos3
    beta : D2 pos12, D3 pos10, D4 pos7, (absent D5,D6)
    gamma: D3 pos30, D4 pos25, D5 pos20, D6 pos15
    """
    placements = {
        0: {5: "alpha || a"},
        1: {5: "alpha || a", 12: "beta || b"},
        2: {4: "alpha || a", 10: "beta || b", 30: "gamma || c"},
        3: {7: "beta || b", 25: "gamma || c"},
        4: {20: "gamma || c"},
        5: {3: "alpha || a", 15: "gamma || c"},
    }
    pops = {"alpha || a": 70, "beta || b": 60, "gamma || c": 40}
    days = []
    for i, ds in enumerate(D):
        named = {p: (k, pops[k]) for p, k in placements[i].items()}
        days.append((ds, True, full_day(named)))
    return make_clean(days)


def test_runs_split_on_missing_day():
    dates = [pd.Timestamp(x) for x in ["2024-01-01", "2024-01-02", "2024-01-04", "2024-01-05"]]
    assert continuous_runs(dates) == [
        (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")),
        (pd.Timestamp("2024-01-04"), pd.Timestamp("2024-01-05")),
    ]


def test_alpha_reentry_and_censoring():
    lc = build_lifecycle(scenario()).set_index("song_key")
    a = lc.loc["alpha || a"]
    assert a["n_appearances"] == 4                      # D1,D2,D3,D6
    assert a["n_runs"] == 2 and a["reentries"] == 1     # gap D4-D5 is a re-entry
    assert a["left_censored"]                           # present on first observed date
    assert a["right_censored"] and a["status"].startswith("Active")
    assert pd.isna(a["exit_date"])
    assert a["gap_days_within_tenure"] == 2             # span D1..D6 = 6 days, 4 appearances
    assert a["best_position"] == 3 and a["peak_date"] == pd.Timestamp("2024-01-06")
    assert a["time_to_peak_days"] == 5                  # D6 - D1
    assert a["current_run_start"] == pd.Timestamp("2024-01-06")


def test_beta_observed_exit_not_censored():
    lc = build_lifecycle(scenario()).set_index("song_key")
    b = lc.loc["beta || b"]
    assert b["n_appearances"] == 3
    assert b["first_seen"] == pd.Timestamp("2024-01-02")
    assert b["last_seen"] == pd.Timestamp("2024-01-04")
    assert not b["left_censored"]
    assert not b["right_censored"]
    assert b["status"] == "Exited (observed)"
    assert b["exit_date"] == pd.Timestamp("2024-01-05")  # first complete day after last appearance
    assert b["best_position"] == 7 and b["peak_date"] == pd.Timestamp("2024-01-04")
    assert b["time_to_peak_days"] == 2
    assert b["lifecycle_stage"] == "Exited"


def test_gamma_is_new_entry_and_rank_improvement():
    lc = build_lifecycle(scenario()).set_index("song_key")
    g = lc.loc["gamma || c"]
    assert g["first_position"] == 30 and g["last_position"] == 15
    assert g["lifecycle_stage"] == "New Entry"            # run began 3 days before window end
    assert g["right_censored"]


# ---- stage rules: pure unit tests with hand-computed expectations ----
END = pd.Timestamp("2024-06-30")
LONG_AGO = END - pd.Timedelta(days=60)
RECENT = END - pd.Timedelta(days=2)


def stage(positions, left=True, run_start=LONG_AGO, active=True, first_run=True):
    dates = [END - pd.Timedelta(days=len(positions) - 1 - i) for i in range(len(positions))]
    return classify_stage(dates, positions, run_start, left, END, active, is_first_run=first_run)[0]


@pytest.mark.parametrize("positions, expected", [
    ([40, 38, 35, 33], "Growth Phase"),        # net gain 7, latest 33 outside top 10
    ([12, 14, 17, 20], "Decline Phase"),       # net loss 8, 3 of 3 steps worsened
    ([5, 5, 5, 25], "Mature Phase"),           # one poor observation must NOT be decline
    ([3, 4, 5, 6], "Peak Phase"),              # latest 6 within top 10, net change -3 only
    ([20, 18, 16, 14], "Growth Phase"),        # net gain 6, latest 14 outside top 10
    ([8, 9, 25, 9], "Peak Phase"),             # latest in top 10 beats growth/mature rules
])
def test_stage_rules(positions, expected):
    assert stage(positions) == expected


def test_insufficient_history():
    assert stage([10, 9]) == "Insufficient history"


def test_new_entry_requires_observed_entry():
    # Same recent start, but left-censored: entry unobserved, so not "New Entry"
    assert stage([40, 38, 35, 33], left=True, run_start=RECENT) != "New Entry"
    assert stage([40, 38, 35, 33], left=False, run_start=RECENT) == "New Entry"


def test_reentry_within_window_is_not_new_entry():
    # Returned 2 days ago after an absence: a re-entry, so it must not be labelled New Entry
    assert stage([40, 38, 35, 33], left=False, run_start=RECENT, first_run=False) != "New Entry"


def test_exited_songs_have_no_active_stage():
    assert stage([10, 9, 8, 7], active=False) == "Exited"
