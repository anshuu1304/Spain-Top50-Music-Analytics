"""Orchestrates every analysis and returns tidy tables + a results dictionary.

Everything here is computed from the cleaned data. No values are typed in by hand.
"""
import numpy as np
import pandas as pd
from scipy import stats

from src.churn_analysis import daily_rotation, monthly_rotation, rotation_kpis
from src.lifecycle import build_lifecycle, observation_window
from src.maturity_analysis import (
    apply_holm, attribute_sensitivity, compare_two_groups, continuous_numeric_relationships,
    first_run_survival, group_summary, song_frame,
)
from src.popularity_analysis import popularity_by_stage, popularity_by_tenure, popularity_change_summary, popularity_vs_rank
from src.statistical_analysis import (
    bootstrap_median_ci, holm_adjust, kaplan_meier, km_median, mann_whitney, spearman,
)


def build_all(clean: pd.DataFrame, master: pd.DataFrame) -> dict:
    win = observation_window(clean)
    lc = build_lifecycle(clean)
    daily = daily_rotation(clean)
    monthly = monthly_rotation(daily)
    rot = rotation_kpis(daily)
    df = song_frame(lc, master)
    surv = first_run_survival(clean, lc)

    cohort_14oct = set(lc.loc[lc["first_seen"] == pd.Timestamp("2024-10-14"), "song_key"])

    comp_explicit = compare_two_groups(df, "is_explicit", True, False, surv)
    comp_album = compare_two_groups(df, "album_type", "album", "single", surv)
    comp_explicit_x = compare_two_groups(df[~df.song_key.isin(cohort_14oct)], "is_explicit", True, False,
                                         surv[~surv.song_key.isin(cohort_14oct)])
    comp_album_x = compare_two_groups(df[~df.song_key.isin(cohort_14oct)], "album_type", "album", "single",
                                      surv[~surv.song_key.isin(cohort_14oct)])
    comps = apply_holm([comp_explicit, comp_album])

    # Duration and album-size relationships (Spearman; observed-entry restriction for entry measures)
    dur_rel = continuous_numeric_relationships(df, "duration_ms", "duration_ms")
    size_rel = continuous_numeric_relationships(df, "total_tracks", "total_tracks")
    alb_only = df[(df["album_type"] == "album")]
    size_within_album = continuous_numeric_relationships(alb_only, "total_tracks", "total_tracks (albums only)")
    rel_rows = dur_rel + size_rel + size_within_album
    rel_adj = holm_adjust([r["p_value"] for r in rel_rows])
    for r, a in zip(rel_rows, rel_adj):
        r["p_holm"] = float(a)
    rel_df = pd.DataFrame(rel_rows)
    rel_df["n"] = rel_df["n"].astype(int)

    # Duration / album-size nonlinearity check (Kruskal-Wallis across quartiles)
    obs = df[~df["left_censored"]].copy()
    obs["dur_q"] = pd.qcut(obs["duration_ms"], 4, labels=False, duplicates="drop")
    kw_dur = stats.kruskal(*[g["n_appearances"].values for _, g in obs.groupby("dur_q")])

    # Holm across the main family of tests (primary comparisons + relationships)
    primary_p = []
    labels = []
    for c in comps:
        for k in ["appearances_MW", "best_position_MW", "popularity_mean_MW", "rank_volatility_MW", "time_to_peak_MW"]:
            primary_p.append(c[k]["p_value"]); labels.append(f"{c['comparison']} | {k}")
        primary_p.append(c["first_run_logrank"]["p_value"]); labels.append(f"{c['comparison']} | first_run_logrank")
    primary_p += list(rel_df["p_value"]); labels += [f"{a} | {b}" for a, b in zip(rel_df["attribute"], rel_df["outcome"])]
    family_adj = holm_adjust(primary_p)
    family = pd.DataFrame({"test": labels, "p_raw": primary_p, "p_holm_family": family_adj})

    pop_tenure = popularity_by_tenure(clean, lc)
    pop_rank = popularity_vs_rank(lc)
    pop_change = popularity_change_summary(lc)
    pop_stage = popularity_by_stage(lc)

    # KPI framework (definitions in docs/methodology.md)
    obs_exit = lc[(~lc["left_censored"]) & (~lc["right_censored"])]
    km_all = kaplan_meier(surv["duration_days"], surv["event"])
    kpis = {
        "avg_days_on_playlist_cumulative_appearances": float(lc["n_appearances"].mean()),
        "median_observed_first_run_days_KM": km_median(km_all),
        "median_span_days_exited_observed_entry": float(obs_exit["tenure_span_days"].median()),
        "entry_to_peak_days_median_observed_entry": float(lc.loc[~lc["left_censored"], "time_to_peak_days"].median()),
        "avg_playlist_churn_rate_pct_per_day": rot["mean_daily_exit_rate_pct"],
        "daily_turnover_mean": rot["mean_daily_turnover"],
        "retention_stability_index": float(daily["retention_pct"].mean() /
                                           (1 + daily["entries"].std(ddof=1) / daily["entries"].mean())),
        "single_vs_album_appearance_ratio_median": float(
            df.loc[~df.left_censored & (df.album_type == "album"), "n_appearances"].median() /
            df.loc[~df.left_censored & (df.album_type == "single"), "n_appearances"].median()),
        "explicit_minus_clean_km_median_days": (comp_explicit["km_median_A"] - comp_explicit["km_median_B"]),
        "average_peak_position": float(lc["best_position"].mean()),
        "average_reentries_per_song": float(lc["reentries"].mean()),
        "average_reentries_per_observed_entry_song": float(lc.loc[~lc["left_censored"], "reentries"].mean()),
    }
    ci = bootstrap_median_ci(obs_exit["tenure_span_days"], seed=42)
    kpis["median_span_days_exited_observed_entry_95ci"] = [ci[0], ci[1]]

    results = {
        "window": {"first_date": str(win["first_date"].date()), "window_end": str(win["window_end"].date()),
                   "complete_dates": len(win["complete_dates"]), "partial_dates": [str(d.date()) for d in win["partial_dates"]]},
        "rotation": rot,
        "kpis": kpis,
        "comparisons": comps,
        "comparisons_excluding_14oct_cohort": {"explicit": comp_explicit_x, "album": comp_album_x},
        "relationships": rel_rows,
        "duration_quartile_kruskal": {"h": float(kw_dur.statistic), "p": float(kw_dur.pvalue)},
        "popularity_tenure_available": True,
        "popularity_vs_rank": pop_rank,
        "popularity_change": pop_change,
        "popularity_by_stage": pop_stage,
        "attribute_sensitivity": attribute_sensitivity(clean, lc, master),
        "cohort_14oct_size": len(cohort_14oct),
        "cohort_14oct_bad_bunny": int(lc[lc.song_key.isin(cohort_14oct)]["artist"].str.contains("Bad Bunny").sum()),
    }
    return {"lifecycle": lc, "daily": daily, "monthly": monthly, "song_frame": df, "survival": surv,
            "group_explicit": group_summary(df, "is_explicit"), "group_album": group_summary(df, "album_type"),
            "relationships": rel_df, "family": family, "popularity_tenure": pop_tenure,
            "km": km_all, "results": results}
