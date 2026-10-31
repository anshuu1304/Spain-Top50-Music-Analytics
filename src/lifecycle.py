"""Song-level lifecycle construction.

Definitions (see docs/methodology.md):
* Appearance      : a song observed on a date (one row per date in this dataset).
* Continuous run  : maximal block of consecutive calendar days on which the song appears.
* Re-entry        : a run that begins after an earlier run ended.
* Right-censored  : song still present at the end of the complete-snapshot window.
                    Its tenure is a LOWER bound; it is not an exit.
* Left-censored   : song already present on the first observed date. Its true entry date
                    is unknown; entry-based measures are flagged and excluded from
                    entry-based comparisons.
* Exited (observed): song absent on the first complete date after its last appearance.
                    A missing date that falls in the partial (incomplete) snapshot is
                    never treated as an exit.
"""
import numpy as np
import pandas as pd

from src.config import (
    DECLINE_MIN_LOSS, GROWTH_MIN_GAIN, MIN_OBSERVATIONS, NEW_ENTRY_WINDOW_DAYS,
    RECENT_WINDOW, TOP_N_PEAK,
)


def observation_window(clean: pd.DataFrame) -> dict:
    """Return the observation calendar used for lifecycle logic."""
    complete = sorted(clean.loc[clean["snapshot_complete"], "date"].unique())
    partial = sorted(clean.loc[~clean["snapshot_complete"], "date"].unique())
    all_dates = sorted(clean["date"].unique())
    return {
        "first_date": pd.Timestamp(all_dates[0]),
        "window_end": pd.Timestamp(complete[-1]),           # last COMPLETE snapshot
        "complete_dates": [pd.Timestamp(d) for d in complete],
        "partial_dates": [pd.Timestamp(d) for d in partial],
    }


def continuous_runs(dates: list[pd.Timestamp]) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Split a sorted list of observed dates into (start, end) runs of consecutive calendar days."""
    if not dates:
        return []
    runs = []
    start = prev = dates[0]
    for d in dates[1:]:
        if (d - prev).days == 1:
            prev = d
            continue
        runs.append((start, prev))
        start = prev = d
    runs.append((start, prev))
    return runs


def classify_stage(
    dates: list[pd.Timestamp],
    positions: list[int],
    current_run_start: pd.Timestamp,
    left_censored: bool,
    window_end: pd.Timestamp,
    active: bool,
    is_first_run: bool = True,
) -> tuple[str, str]:
    """Explainable rule-based stage for ACTIVE songs. Returns (stage, reason).

    New Entry requires the song's FIRST run, its entry observed (not left-censored) and that run
    starting within the last NEW_ENTRY_WINDOW_DAYS observed days. A song returning after a gap
    is a re-entry and is classified by the rules below, not as New Entry.
    """
    if not active:
        return "Exited", "not present at window end; exit observed on next complete snapshot"
    reentry_note = "" if is_first_run else " (re-entered song; not a new entry)"
    if is_first_run and (not left_censored) and (window_end - current_run_start).days < NEW_ENTRY_WINDOW_DAYS:
        return "New Entry", f"first run began {current_run_start.date()}, within {NEW_ENTRY_WINDOW_DAYS} observed days"
    if len(positions) < MIN_OBSERVATIONS:
        return "Insufficient history", f"only {len(positions)} appearances (< {MIN_OBSERVATIONS})" + reentry_note

    recent = positions[-RECENT_WINDOW:]
    net_change = recent[0] - recent[-1]                 # + = improvement (lower rank number)
    worsening_steps = sum(1 for a, b in zip(recent, recent[1:]) if b > a)
    latest = positions[-1]

    if net_change <= -DECLINE_MIN_LOSS and worsening_steps >= 2:
        return "Decline Phase", (f"net loss {-net_change} positions over last {len(recent)} appearances; "
                                 f"{worsening_steps} of {len(recent) - 1} steps worsened") + reentry_note
    if latest <= TOP_N_PEAK:
        return "Peak Phase", f"latest position {latest} within Top {TOP_N_PEAK}" + reentry_note
    if net_change >= GROWTH_MIN_GAIN:
        return "Growth Phase", (f"gained {net_change} positions over last {len(recent)} appearances; "
                                f"still outside Top {TOP_N_PEAK}") + reentry_note
    return "Mature Phase", f"stable outside Top {TOP_N_PEAK} (latest {latest}, window change {net_change:+d})" + reentry_note


def build_lifecycle(clean: pd.DataFrame) -> pd.DataFrame:
    """One row per song_key with lifecycle metrics, censoring flags and stage."""
    win = observation_window(clean)
    first_date, window_end = win["first_date"], win["window_end"]
    rows = []
    for key, sub in clean.sort_values(["date", "position"]).groupby("song_key", sort=False):
        dates = list(sub["date"])
        positions = list(sub["position"].astype(int))
        pops = list(sub["popularity_valid"].astype(float))  # NaN where popularity was 0 (missing)
        pops_ok = [x for x in pops if not np.isnan(x)]
        runs = continuous_runs(dates)
        first_seen, last_seen = dates[0], dates[-1]
        left_censored = first_seen == first_date
        active = last_seen >= window_end
        cur_start = runs[-1][0]
        best = min(positions)
        peak_date = dates[positions.index(best)]
        n = len(dates)
        span_days = (last_seen - first_seen).days + 1
        stage, reason = classify_stage(dates, positions, cur_start, left_censored, window_end, active,
                                       is_first_run=len(runs) == 1)

        rec = {
            "song_key": key,
            "song": sub["song"].iloc[0],
            "artist": sub["artist"].iloc[0],
            "first_seen": first_seen,
            "last_seen": last_seen,
            "left_censored": left_censored,
            "status": "Active (right-censored)" if active else "Exited (observed)",
            "right_censored": active,
            "exit_date": (last_seen + pd.Timedelta(days=1)) if not active else pd.NaT,
            "n_appearances": n,
            "n_runs": len(runs),
            "reentries": len(runs) - 1,
            "longest_run_days": max((e - s).days + 1 for s, e in runs),
            "current_run_start": cur_start if active else pd.NaT,
            "current_run_days": ((last_seen - cur_start).days + 1) if active else 0,
            "gap_days_within_tenure": span_days - n,
            "tenure_span_days": span_days,
            "best_position": best,
            "peak_date": peak_date,
            "time_to_peak_days": (peak_date - first_seen).days,
            "first_position": positions[0],
            "last_position": positions[-1],
            "mean_position": float(np.mean(positions)),
            "median_position": float(np.median(positions)),
            "rank_volatility_sd": float(np.std(positions, ddof=1)) if n > 1 else np.nan,
            "popularity_first": pops_ok[0] if pops_ok else np.nan,
            "popularity_max": max(pops_ok) if pops_ok else np.nan,
            "popularity_mean": float(np.mean(pops_ok)) if pops_ok else np.nan,
            "popularity_last": pops_ok[-1] if pops_ok else np.nan,
            "popularity_change": (pops_ok[-1] - pops_ok[0]) if len(pops_ok) > 1 else np.nan,
            "popularity_valid_obs": len(pops_ok),
            "lifecycle_stage": stage,
            "stage_reason": reason,
        }
        rows.append(rec)
    out = pd.DataFrame(rows)
    return out
