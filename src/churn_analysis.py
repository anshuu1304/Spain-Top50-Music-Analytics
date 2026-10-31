"""Daily and monthly playlist rotation metrics on COMPLETE snapshots only.

Formulas (fixed playlist size N = PLAYLIST_SIZE = 50):
  S_d                 = set of song_keys on complete date d
  entries_d           = |S_d \\ S_{d-1}|          (songs replacing older ones; includes re-entries)
  exits_d             = |S_{d-1} \\ S_d|
  retained_d          = |S_d ∩ S_{d-1}|
  reentries_d         = entries whose song appeared on an observed date before d-1
  new_entries_d       = entries_d - reentries_d
  entry_rate_pct      = entries_d / N * 100
  exit_rate_pct       = exits_d   / N * 100
  daily_turnover      = (entries_d + exits_d) / 2     (per spec)
  retention_pct       = retained_d / N * 100

Only consecutive CALENDAR days where both dates are complete are used. The partial
15 Oct 2024 snapshot never contributes a transition, so no exit is invented there.

Because every complete snapshot has exactly N songs, entries_d == exits_d always;
the spec's turnover formula therefore equals entries_d. This is reported explicitly.
"""
import pandas as pd

from src.config import PLAYLIST_SIZE


def _keys_by_date(clean: pd.DataFrame) -> dict:
    complete = clean[clean["snapshot_complete"]]
    return {d: set(g["song_key"]) for d, g in complete.groupby("date")}


def daily_rotation(clean: pd.DataFrame) -> pd.DataFrame:
    sets = _keys_by_date(clean)
    dates = sorted(sets)
    # first observed date each song appears on (any snapshot, incl. partial)
    first_obs = clean.groupby("song_key")["date"].min().to_dict()
    rows = []
    for prev, cur in zip(dates, dates[1:]):
        if (cur - prev).days != 1:
            continue  # never bridge an unexplained gap
        s_prev, s_cur = sets[prev], sets[cur]
        entries = s_cur - s_prev
        exits = s_prev - s_cur
        retained = s_cur & s_prev
        reentries = {k for k in entries if first_obs[k] < prev}
        n_entries, n_exits = len(entries), len(exits)
        rows.append({
            "date": cur,
            "prev_date": prev,
            "size_today": len(s_cur),
            "entries": n_entries,
            "exits": n_exits,
            "retained": len(retained),
            "reentries": len(reentries),
            "new_entries": n_entries - len(reentries),
            "entry_rate_pct": n_entries / PLAYLIST_SIZE * 100,
            "exit_rate_pct": n_exits / PLAYLIST_SIZE * 100,
            "daily_turnover": (n_entries + n_exits) / 2,
            "retention_pct": len(retained) / PLAYLIST_SIZE * 100,
        })
    return pd.DataFrame(rows)


def monthly_rotation(daily: pd.DataFrame) -> pd.DataFrame:
    """Monthly summary. 'avg_*' are per-day averages; 'total_*' are sums of replacements in the month."""
    if daily.empty:
        return daily
    d = daily.assign(month=daily["date"].dt.to_period("M").astype(str))
    out = d.groupby("month").agg(
        transitions=("date", "size"),
        avg_entries=("entries", "mean"),
        avg_exits=("exits", "mean"),
        avg_daily_turnover=("daily_turnover", "mean"),
        avg_entry_rate_pct=("entry_rate_pct", "mean"),
        avg_retention_pct=("retention_pct", "mean"),
        total_entries=("entries", "sum"),
        total_reentries=("reentries", "sum"),
    ).reset_index()
    return out


def rotation_kpis(daily: pd.DataFrame) -> dict:
    if daily.empty:
        return {}
    return {
        "valid_transitions": int(len(daily)),
        "mean_daily_entry_rate_pct": float(daily["entry_rate_pct"].mean()),
        "mean_daily_exit_rate_pct": float(daily["exit_rate_pct"].mean()),
        "mean_daily_turnover": float(daily["daily_turnover"].mean()),
        "mean_retention_pct": float(daily["retention_pct"].mean()),
        "total_entries": int(daily["entries"].sum()),
        "total_reentries": int(daily["reentries"].sum()),
        "share_of_entries_that_are_reentries_pct": float(daily["reentries"].sum() / max(daily["entries"].sum(), 1) * 100),
        "days_with_zero_entries": int((daily["entries"] == 0).sum()),
    }
