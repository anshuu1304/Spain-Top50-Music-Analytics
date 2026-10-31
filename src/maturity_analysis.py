"""Content-maturity analysis: explicit vs clean, singles vs albums, duration, album size.

Unit of analysis = song (song_key). Attributes use the CANONICAL value (see preprocessing);
a sensitivity check re-runs the key comparisons with a different attribute rule.

Censoring: 'tenure' for songs already present on the first date is left-truncated; entry-based
measures (time to peak, first-run duration) use only songs whose entry was observed.
"""
import numpy as np
import pandas as pd

from src.config import TOP_N_PEAK
from src.lifecycle import continuous_runs, observation_window
from src.statistical_analysis import (
    chi_square, chi_square_permutation, holm_adjust, kaplan_meier, km_median, logrank_test, mann_whitney, spearman,
)


def first_run_survival(clean: pd.DataFrame, lc: pd.DataFrame) -> pd.DataFrame:
    """Survival data for the FIRST continuous run of songs whose entry was observed.

    duration_days = length of the first run; event = 1 if the run ended before the window end.
    """
    win = observation_window(clean)
    end = win["window_end"]
    out = []
    entered = lc.loc[~lc["left_censored"], "song_key"]
    for key, sub in clean[clean["song_key"].isin(entered)].sort_values("date").groupby("song_key"):
        runs = continuous_runs(list(sub["date"]))
        s, e = runs[0]
        out.append({"song_key": key, "duration_days": (e - s).days + 1, "event": int(e < end)})
    return pd.DataFrame(out)


def song_frame(lc: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Song-level analysis table: lifecycle + canonical content attributes."""
    attrs = master[["song_key", "canonical_album_type", "canonical_is_explicit",
                    "canonical_duration_ms", "canonical_total_tracks", "any_attribute_conflict",
                    "shared_title_flag"]]
    df = lc.merge(attrs, on="song_key", how="left")
    df["is_explicit"] = df["canonical_is_explicit"].astype(bool)
    df["album_type"] = df["canonical_album_type"]
    df["duration_ms"] = df["canonical_duration_ms"].astype(float)
    df["total_tracks"] = df["canonical_total_tracks"].astype(float)
    df["ever_top10"] = df["best_position"] <= TOP_N_PEAK
    df["reentry_flag"] = df["reentries"] > 0
    return df


def group_summary(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Descriptive summary per group. Entry-based measures use observed-entry songs only."""
    obs = df[~df["left_censored"]]
    rows = []
    for g, sub in df.groupby(group_col):
        s_obs = obs[obs[group_col] == g]
        rows.append({
            group_col: g,
            "songs": len(sub),
            "median_cumulative_appearances": float(sub["n_appearances"].median()),
            "mean_cumulative_appearances": float(sub["n_appearances"].mean()),
            "median_best_position": float(sub["best_position"].median()),
            "share_top10_ever_pct": float(sub["ever_top10"].mean() * 100),
            "median_rank_volatility_sd": float(sub["rank_volatility_sd"].median()),
            "share_with_reentry_pct": float(sub["reentry_flag"].mean() * 100),
            "median_popularity_mean": float(sub["popularity_mean"].median()),
            "observed_entry_songs": len(s_obs),
            "median_time_to_peak_days_observed_entry": float(s_obs["time_to_peak_days"].median()) if len(s_obs) else np.nan,
            "share_right_censored_pct": float(sub["right_censored"].mean() * 100),
        })
    return pd.DataFrame(rows)


def compare_two_groups(df: pd.DataFrame, group_col: str, a_val, b_val, surv: pd.DataFrame) -> dict:
    """Full comparison set for a binary attribute. Returns raw test results (corrections applied later)."""
    A = df[df[group_col] == a_val]
    B = df[df[group_col] == b_val]
    res = {"comparison": f"{group_col}: {a_val} vs {b_val}"}
    # Appearance counts are left-truncated for songs already charted on day 1; the primary test
    # therefore uses observed-entry songs only. The all-songs test is kept as descriptive context.
    res["appearances_all_songs_MW_descriptive"] = mann_whitney(A["n_appearances"], B["n_appearances"])
    res["appearances_MW"] = mann_whitney(A.loc[~A["left_censored"], "n_appearances"],
                                         B.loc[~B["left_censored"], "n_appearances"])
    res["best_position_MW"] = mann_whitney(A["best_position"], B["best_position"])          # lower = better
    res["popularity_mean_MW"] = mann_whitney(A["popularity_mean"], B["popularity_mean"])
    res["rank_volatility_MW"] = mann_whitney(A["rank_volatility_sd"], B["rank_volatility_sd"])
    oA = A[~A["left_censored"]]
    oB = B[~B["left_censored"]]
    res["time_to_peak_MW"] = mann_whitney(oA["time_to_peak_days"], oB["time_to_peak_days"])
    # survival on first observed runs
    sA = surv[surv["song_key"].isin(oA["song_key"])]
    sB = surv[surv["song_key"].isin(oB["song_key"])]
    res["first_run_logrank"] = logrank_test(sA["duration_days"], sA["event"], sB["duration_days"], sB["event"])
    res["km_median_A"] = km_median(kaplan_meier(sA["duration_days"], sA["event"]))
    res["km_median_B"] = km_median(kaplan_meier(sB["duration_days"], sB["event"]))
    # lifecycle distribution (chi-square, active + exited)
    # Stage is defined only for ACTIVE songs. Including "Exited" would test right-censoring,
    # not lifecycle stage. Active-only sample is small, so a permutation p-value is also reported.
    act = df[df["right_censored"]]
    ct = pd.crosstab(act[group_col], act["lifecycle_stage"])
    res["stage_active_n"] = int(len(act))
    res["stage_chi2"] = chi_square(ct) if ct.shape[0] == 2 and ct.shape[1] >= 2 else None
    if res["stage_chi2"] and res["stage_chi2"]["low_expected_cells"]:
        res["stage_chi2_permutation"] = chi_square_permutation(ct, n_perm=10_000, seed=42)
    res["stage_table"] = ct.to_dict()
    res["n_a"], res["n_b"] = len(A), len(B)
    return res


def apply_holm(results: list[dict]) -> list[dict]:
    """Adjust the primary p-value of each comparison family across all tests (Holm)."""
    keys = []
    pvals = []
    for r in results:
        for k in ["appearances_MW", "best_position_MW", "popularity_mean_MW", "rank_volatility_MW",
                  "time_to_peak_MW", "first_run_logrank"]:
            keys.append((r["comparison"], k))
            pvals.append(r[k]["p_value"] if k != "first_run_logrank" else r[k]["p_value"])
    adj = holm_adjust(pvals)
    lookup = {k: a for k, a in zip(keys, adj)}
    for r in results:
        for k in ["appearances_MW", "best_position_MW", "popularity_mean_MW", "rank_volatility_MW",
                  "time_to_peak_MW", "first_run_logrank"]:
            r[k]["p_holm"] = float(lookup[(r["comparison"], k)])
    return results


def attribute_sensitivity(clean: pd.DataFrame, lc: pd.DataFrame, master: pd.DataFrame) -> dict:
    """Does the conflict-resolution rule change the explicit / album-type conclusions?

    Alternative rule: 'ever' = song is flagged if ANY appearance carries the attribute value.
    Reports how many songs change group and whether the appearance-test conclusion changes.
    """
    base = song_frame(lc, master)
    ever_explicit = clean.groupby("song_key")["is_explicit"].apply(lambda s: bool(s.any()))
    ever_album = clean.groupby("song_key")["album_type"].apply(lambda s: bool((s == "album").any()))
    alt = base.copy()
    alt["is_explicit"] = alt["song_key"].map(ever_explicit).astype(bool)
    alt["album_type"] = np.where(alt["song_key"].map(ever_album), "album", "single")
    changed_explicit = int((alt["is_explicit"] != base["is_explicit"]).sum())
    changed_album = int((alt["album_type"] != base["album_type"]).sum())
    ms_base = mann_whitney(base.loc[~base.left_censored & base.is_explicit, "n_appearances"],
                           base.loc[~base.left_censored & ~base.is_explicit, "n_appearances"])
    ms_alt = mann_whitney(alt.loc[~alt.left_censored & alt.is_explicit, "n_appearances"],
                          alt.loc[~alt.left_censored & ~alt.is_explicit, "n_appearances"])
    mb_base = mann_whitney(base.loc[~base.left_censored & (base.album_type == "album"), "n_appearances"],
                           base.loc[~base.left_censored & (base.album_type == "single"), "n_appearances"])
    mb_alt = mann_whitney(alt.loc[~alt.left_censored & (alt.album_type == "album"), "n_appearances"],
                          alt.loc[~alt.left_censored & (alt.album_type == "single"), "n_appearances"])
    return {
        "songs_changed_group_explicit": changed_explicit,
        "songs_changed_group_album_type": changed_album,
        "explicit_appearances_p_canonical": ms_base["p_value"],
        "explicit_appearances_p_ever": ms_alt["p_value"],
        "album_appearances_p_canonical": mb_base["p_value"],
        "album_appearances_p_ever": mb_alt["p_value"],
    }


def continuous_numeric_relationships(df: pd.DataFrame, x: str, label: str) -> list[dict]:
    """Spearman of a numeric attribute against outcomes, with the observed-entry restriction where needed."""
    obs = df[~df["left_censored"]]
    out = []
    for y, ylab, data in [
        ("n_appearances", "cumulative appearances", df),
        ("best_position", "best position (lower = better)", df),
        ("popularity_mean", "mean popularity", df),
        ("reentries", "re-entries", df),
        ("time_to_peak_days", "time to peak (observed entry)", obs),
    ]:
        r = spearman(data[x], data[y])
        out.append({"attribute": label, "outcome": ylab, **r})
    return out
