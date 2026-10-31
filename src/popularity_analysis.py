"""Popularity vs lifecycle maturity.

Time dimension: popularity is recorded on EVERY observed date, so it is a daily series per song
(not a static snapshot). Tenure-trajectory analysis therefore uses a within-song deviation
(popularity minus that song's own mean), removing between-song level differences.
Only observed-entry songs are used for tenure-day analysis (day 0 = first observed appearance).
"""
import numpy as np
import pandas as pd
from scipy import stats

from src.statistical_analysis import spearman

TENURE_BUCKETS = [(0, 7), (8, 14), (15, 30), (31, 60), (61, 9999)]


def popularity_by_tenure(clean: pd.DataFrame, lc: pd.DataFrame) -> pd.DataFrame:
    obs_keys = set(lc.loc[~lc["left_censored"], "song_key"])
    d = clean[clean["song_key"].isin(obs_keys) & clean["popularity_valid"].notna()].copy()
    d["popularity"] = d["popularity_valid"].astype(float)
    first = d.groupby("song_key")["date"].transform("min")
    d["tenure_day"] = (d["date"] - first).dt.days
    d["song_mean_pop"] = d.groupby("song_key")["popularity"].transform("mean")
    d["pop_deviation"] = d["popularity"] - d["song_mean_pop"]
    rows = []
    for lo, hi in TENURE_BUCKETS:
        sub = d[(d["tenure_day"] >= lo) & (d["tenure_day"] <= hi)]
        label = f"{lo}-{hi}" if hi < 9999 else f"{lo}+"
        rows.append({"tenure_bucket_days": label, "observations": len(sub), "songs": sub["song_key"].nunique(),
                     "mean_popularity": sub["popularity"].mean(),
                     "mean_within_song_deviation": sub["pop_deviation"].mean(),
                     "se_within_song_deviation": sub["pop_deviation"].std(ddof=1) / np.sqrt(len(sub)) if len(sub) > 1 else np.nan})
    return pd.DataFrame(rows)


def popularity_vs_rank(lc: pd.DataFrame) -> dict:
    lc = lc.dropna(subset=["popularity_mean", "popularity_first", "popularity_max"])
    return {
        "popularity_mean_vs_best_position": spearman(lc["popularity_mean"], lc["best_position"]),
        "popularity_first_vs_best_position": spearman(lc["popularity_first"], lc["best_position"]),
        "popularity_max_vs_best_position": spearman(lc["popularity_max"], lc["best_position"]),
    }


def popularity_change_summary(lc: pd.DataFrame) -> dict:
    obs = lc[~lc["left_censored"] & (lc["n_appearances"] >= 2) & lc["popularity_change"].notna()]
    ch = obs["popularity_change"]
    # Wilcoxon signed-rank on last-minus-first popularity for observed-entry songs with >=2 appearances
    nz = ch[ch != 0]
    p = float(stats.wilcoxon(nz).pvalue) if len(nz) >= 10 else np.nan
    return {"n": int(len(obs)), "median_change": float(ch.median()), "mean_change": float(ch.mean()),
            "share_increase_pct": float((ch > 0).mean() * 100), "share_decrease_pct": float((ch < 0).mean() * 100),
            "wilcoxon_p_value": p}


def popularity_by_stage(lc: pd.DataFrame) -> dict:
    act = lc[lc["right_censored"] & lc["popularity_mean"].notna()]
    groups = [g["popularity_mean"].values for _, g in act.groupby("lifecycle_stage") if len(g) >= 3]
    if len(groups) < 2:
        return {"kruskal_h": np.nan, "p_value": np.nan, "groups": len(groups)}
    h, p = stats.kruskal(*groups)
    return {"kruskal_h": float(h), "p_value": float(p), "groups": len(groups),
            "median_by_stage": act.groupby("lifecycle_stage")["popularity_mean"].median().to_dict()}
