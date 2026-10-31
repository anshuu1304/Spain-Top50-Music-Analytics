"""Churn and rotation tests with hand-computed expectations on synthetic 50-slot snapshots."""
import pandas as pd

from src.churn_analysis import daily_rotation, monthly_rotation, rotation_kpis
from tests.helpers import make_clean

def base_keys():
    return {p: f"s{p} || a" for p in range(1, 51)}


def days():
    d1 = base_keys()
    d2 = {**d1, 1: "n1 || a", 2: "n2 || a"}           # 2 entries, 2 exits (s1, s2)
    d3 = {**d2, 1: "s1 || a"}                         # s1 returns (re-entry); n1 exits
    d4 = dict(d3)                                     # no change
    d5 = {**d4, 3: "n3 || a"}                         # n3 new; s3 exits
    d6 = dict(d5)
    out = []
    for ds, keys in [("2024-03-01", d1), ("2024-03-02", d2), ("2024-03-03", d3),
                     ("2024-03-04", d4), ("2024-03-05", d5), ("2024-03-06", d6)]:
        out.append((ds, True, {p: (k, 60) for p, k in keys.items()}))
    # partial 15-day style snapshot: 8 rows, must never create a transition or exit
    out.append(("2024-03-07", False, {p: (d6[p], 60) for p in range(1, 9)}))
    return out


def test_transitions_entries_exits_reentries():
    d = daily_rotation(make_clean(days())).set_index("date")
    assert len(d) == 5                                   # 5 valid transitions D1->D6
    t2 = d.loc["2024-03-02"]
    assert (t2.entries, t2.exits, t2.reentries, t2.new_entries, t2.retained) == (2, 2, 0, 2, 48)
    t3 = d.loc["2024-03-03"]
    assert (t3.entries, t3.exits, t3.reentries, t3.new_entries) == (1, 1, 1, 0)
    t4 = d.loc["2024-03-04"]
    assert (t4.entries, t4.exits) == (0, 0)
    t5 = d.loc["2024-03-05"]
    assert (t5.entries, t5.exits, t5.new_entries) == (1, 1, 1)


def test_formulas_match_spec():
    d = daily_rotation(make_clean(days())).set_index("date")
    t2 = d.loc["2024-03-02"]
    assert t2.entry_rate_pct == 2 / 50 * 100              # 4.0
    assert t2.exit_rate_pct == 2 / 50 * 100
    assert t2.daily_turnover == (2 + 2) / 2                # 2.0
    assert t2.retention_pct == 48 / 50 * 100              # 96.0


def test_partial_snapshot_never_creates_exits():
    d = daily_rotation(make_clean(days()))
    assert pd.Timestamp("2024-03-07") not in set(d["date"])
    k = rotation_kpis(d)
    assert k["total_entries"] == 4 and k["total_reentries"] == 1
    assert k["total_entries"] == 2 + 1 + 0 + 1 + 0        # reconciles to the daily table


def test_gap_days_are_not_bridged():
    # remove 2024-03-04: transition 03-03 -> 03-05 must NOT be counted as one day
    rows = [r for r in days() if r[0] != "2024-03-04"]
    d = daily_rotation(make_clean(rows))
    assert pd.Timestamp("2024-03-05") not in set(d["date"])
    assert pd.Timestamp("2024-03-03") in set(d["date"])  # 03-02 -> 03-03 still valid


def test_monthly_totals():
    d = daily_rotation(make_clean(days()))
    m = monthly_rotation(d)
    assert int(m.total_entries.sum()) == 4
    assert int(m.transitions.sum()) == 5
