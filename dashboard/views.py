"""Pure-pandas view models for every dashboard page.

No Streamlit or Plotly imports here, so every table the dashboard shows can be unit tested.
Every function accepts a (possibly empty) filtered DataFrame and returns an empty result rather
than raising when no rows remain.
"""
import numpy as np
import pandas as pd

from src.churn_analysis import monthly_rotation
from src.lifecycle import continuous_runs
from src.maturity_analysis import group_summary

STAGE_ORDER = ["New Entry", "Growth Phase", "Peak Phase", "Mature Phase", "Decline Phase", "Insufficient history"]
FRESH_DAYS = 14


def kpi_summary(sf: pd.DataFrame) -> dict:
    if sf.empty:
        return {"songs": 0}
    return {
        "songs": int(len(sf)),
        "observations": int(sf["n_appearances"].sum()),
        "avg_appearances": float(sf["n_appearances"].mean()),
        "avg_best_position": float(sf["best_position"].mean()),
        "active": int(sf["right_censored"].sum()),
        "exited": int((~sf["right_censored"]).sum()),
        "reentry_share_pct": float((sf["reentries"] > 0).mean() * 100),
        "top10_share_pct": float(sf["ever_top10"].mean() * 100),
    }


def top_songs(sf: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    cols = ["song", "artist", "best_position", "n_appearances", "lifecycle_stage", "status"]
    if sf.empty:
        return pd.DataFrame(columns=cols)
    return sf.sort_values(["best_position", "n_appearances"], ascending=[True, False]).head(n)[cols]


def recent_entries(sf: pd.DataFrame, window_end: pd.Timestamp, days: int = FRESH_DAYS) -> pd.DataFrame:
    cols = ["song", "artist", "first_seen", "best_position", "n_appearances", "lifecycle_stage"]
    if sf.empty:
        return pd.DataFrame(columns=cols)
    m = (~sf["left_censored"]) & (sf["first_seen"] > window_end - pd.Timedelta(days=days))
    return sf.loc[m].sort_values("first_seen", ascending=False)[cols]


def monthly_from(daily_f: pd.DataFrame) -> pd.DataFrame:
    if daily_f.empty:
        return pd.DataFrame(columns=["month", "transitions", "avg_daily_turnover", "total_entries"])
    return monthly_rotation(daily_f)


def rotation_summary(daily_f: pd.DataFrame) -> dict:
    if daily_f.empty:
        return {"transitions": 0}
    return {
        "transitions": int(len(daily_f)),
        "total_entries": int(daily_f["entries"].sum()),
        "total_reentries": int(daily_f["reentries"].sum()),
        "mean_turnover": float(daily_f["daily_turnover"].mean()),
        "mean_retention_pct": float(daily_f["retention_pct"].mean()),
        "zero_entry_days": int((daily_f["entries"] == 0).sum()),
    }


def stage_counts(sf: pd.DataFrame) -> pd.DataFrame:
    act = sf[sf["right_censored"]] if not sf.empty else sf
    counts = act["lifecycle_stage"].value_counts().reindex(STAGE_ORDER).fillna(0).astype(int)
    return counts.rename_axis("stage").reset_index(name="songs")


def stage_by_group(sf: pd.DataFrame, group_col: str) -> pd.DataFrame:
    act = sf[sf["right_censored"]] if not sf.empty else sf
    if act.empty:
        return pd.DataFrame(columns=[group_col, "stage", "songs"])
    t = act.groupby([group_col, "lifecycle_stage"]).size().reset_index(name="songs")
    return t.rename(columns={"lifecycle_stage": "stage"})


def group_table(sf: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if sf.empty or sf[group_col].nunique() < 2:
        return pd.DataFrame()
    return group_summary(sf, group_col)


def album_size_table(sf: pd.DataFrame) -> pd.DataFrame:
    alb = sf[(sf["album_type"] == "album") & sf["total_tracks"].notna()] if not sf.empty else sf
    cols = ["size_band", "songs", "median_appearances_observed_entry", "median_best_position", "median_popularity"]
    if alb.empty:
        return pd.DataFrame(columns=cols)
    bins = [0, 6, 12, 20, 1000]
    labels = ["1-6 tracks", "7-12 tracks", "13-20 tracks", "21+ tracks"]
    alb = alb.assign(size_band=pd.cut(alb["total_tracks"], bins=bins, labels=labels, include_lowest=True))
    rows = []
    for band, g in alb.groupby("size_band", observed=True):
        obs = g[~g["left_censored"]]
        rows.append({"size_band": str(band), "songs": len(g),
                     "median_appearances_observed_entry": float(obs["n_appearances"].median()) if len(obs) else np.nan,
                     "median_best_position": float(g["best_position"].median()),
                     "median_popularity": float(g["popularity_mean"].median())})
    return pd.DataFrame(rows, columns=cols)


def duration_table(sf: pd.DataFrame) -> pd.DataFrame:
    cols = ["duration_quartile", "range_minutes", "songs", "median_appearances_observed_entry", "median_best_position", "median_popularity"]
    if sf.empty or sf["duration_ms"].nunique() < 4:
        return pd.DataFrame(columns=cols)
    q = pd.qcut(sf["duration_ms"], 4, labels=["Q1 (shortest)", "Q2", "Q3", "Q4 (longest)"], duplicates="drop")
    d = sf.assign(duration_quartile=q)
    rows = []
    for label, g in d.groupby("duration_quartile", observed=True):
        obs = g[~g["left_censored"]]
        rows.append({"duration_quartile": str(label),
                     "range_minutes": f"{g['duration_ms'].min() / 60000:.2f}-{g['duration_ms'].max() / 60000:.2f}",
                     "songs": len(g),
                     "median_appearances_observed_entry": float(obs["n_appearances"].median()) if len(obs) else np.nan,
                     "median_best_position": float(g["best_position"].median()),
                     "median_popularity": float(g["popularity_mean"].median())})
    return pd.DataFrame(rows, columns=cols)


def fresh_vs_established(sf: pd.DataFrame, window_end: pd.Timestamp) -> pd.DataFrame:
    cols = ["group", "songs", "active_share_pct", "median_appearances", "median_best_position"]
    if sf.empty:
        return pd.DataFrame(columns=cols)
    obs = sf[~sf["left_censored"]].copy()
    obs["group"] = np.where(obs["first_seen"] > window_end - pd.Timedelta(days=FRESH_DAYS),
                            f"Fresh (entered in last {FRESH_DAYS} days)", "Established (entered earlier)")
    rows = []
    for g, d in obs.groupby("group"):
        rows.append({"group": g, "songs": len(d), "active_share_pct": float(d["right_censored"].mean() * 100),
                     "median_appearances": float(d["n_appearances"].median()),
                     "median_best_position": float(d["best_position"].median())})
    return pd.DataFrame(rows, columns=cols)


def popularity_by_stage(sf: pd.DataFrame) -> pd.DataFrame:
    cols = ["stage", "songs_with_popularity", "median_popularity"]
    act = sf[sf["right_censored"] & sf["popularity_mean"].notna()] if not sf.empty else sf
    if act.empty:
        return pd.DataFrame(columns=cols)
    rows = [{"stage": s, "songs_with_popularity": len(g), "median_popularity": float(g["popularity_mean"].median())}
            for s, g in act.groupby("lifecycle_stage")]
    return pd.DataFrame(rows, columns=cols)


def song_runs(clean: pd.DataFrame, song_key: str) -> pd.DataFrame:
    cols = ["run", "start", "end", "days"]
    dates = sorted(clean.loc[clean["song_key"] == song_key, "date"])
    runs = continuous_runs(dates)
    return pd.DataFrame([{"run": i + 1, "start": s.date(), "end": e.date(), "days": (e - s).days + 1}
                         for i, (s, e) in enumerate(runs)], columns=cols)


def survival_subset(surv: pd.DataFrame, sf: pd.DataFrame) -> pd.DataFrame:
    if surv.empty or sf.empty:
        return surv.iloc[0:0]
    keys = set(sf.loc[~sf["left_censored"], "song_key"])
    return surv[surv["song_key"].isin(keys)]


def data_quality_tables(raw: pd.DataFrame, clean: pd.DataFrame, master: pd.DataFrame,
                        conflicts: pd.DataFrame, cleaning_log: pd.DataFrame) -> dict:
    missing = pd.DataFrame({"column": [c for c in raw.columns if c != "source_row"],
                            "blank_cells": [int((raw[c].astype(str).str.strip() == "").sum()) for c in raw.columns if c != "source_row"]})
    per_date = clean.groupby("date").size()
    dates = pd.DataFrame({"date": per_date.index.date, "rows": per_date.values,
                          "status": np.where(per_date.values == 50, "complete", "incomplete (excluded from transitions)")})
    checks = pd.DataFrame([
        {"check": "Rows loaded", "result": f"{len(raw):,}"},
        {"check": "Rows kept after cleaning", "result": f"{len(clean):,}"},
        {"check": "Exact duplicate rows", "result": f"{int(clean['dup_exact_row'].sum())}"},
        {"check": "Duplicate (date, position)", "result": f"{int(clean['dup_date_position'].sum())}"},
        {"check": "Duplicate (date, song identity)", "result": f"{int(clean['dup_date_song_key'].sum())}"},
        {"check": "Popularity recorded as 0 (treated as missing)", "result": f"{int(clean['popularity_zero_flag'].sum())}"},
        {"check": "Songs with an attribute conflict", "result": f"{int(master['any_attribute_conflict'].sum())} of {len(master)}"},
        {"check": "Songs whose title is credited to several artists (not merged)", "result": f"{int(master['shared_title_flag'].sum())}"},
        {"check": "Dates with a complete 50-song snapshot", "result": f"{int((per_date == 50).sum())} of {len(per_date)}"},
    ])
    return {"missing": missing, "dates": dates, "checks": checks,
            "conflicts": conflicts, "log": cleaning_log}
