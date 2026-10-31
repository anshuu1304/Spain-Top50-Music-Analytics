"""Statistical helpers: survival (Kaplan-Meier, log-rank), rank tests, effect sizes, corrections.

All functions are small, documented and tested. No ML models are used.
"""
import numpy as np
import pandas as pd
from scipy import stats


# ---------- survival ----------
def kaplan_meier(durations, events) -> pd.DataFrame:
    """Kaplan-Meier estimator. events: 1 = observed exit, 0 = right-censored."""
    t = np.asarray(durations, dtype=float)
    e = np.asarray(events, dtype=int)
    times = np.unique(t[e == 1])
    rows, s = [], 1.0
    for ti in times:
        n_risk = int(np.sum(t >= ti))
        d = int(np.sum((t == ti) & (e == 1)))
        s *= 1 - d / n_risk
        rows.append({"time": ti, "n_risk": n_risk, "n_events": d, "survival": s})
    return pd.DataFrame(rows, columns=["time", "n_risk", "n_events", "survival"])


def km_median(km: pd.DataFrame):
    """Smallest time where survival <= 0.5; NaN if the curve never reaches 0.5 (censored tail)."""
    hit = km.loc[km["survival"] <= 0.5, "time"]
    return float(hit.iloc[0]) if len(hit) else float("nan")


def logrank_test(dur_a, ev_a, dur_b, ev_b) -> dict:
    """Two-group log-rank test (chi-square, 1 df)."""
    t = np.concatenate([np.asarray(dur_a, float), np.asarray(dur_b, float)])
    e = np.concatenate([np.asarray(ev_a, int), np.asarray(ev_b, int)])
    g = np.concatenate([np.zeros(len(dur_a), int), np.ones(len(dur_b), int)])
    O1 = E1 = V = 0.0
    for ti in np.unique(t[e == 1]):
        at = t >= ti
        n = at.sum()
        n1 = (at & (g == 0)).sum()
        n2 = n - n1
        d = ((t == ti) & (e == 1)).sum()
        d1 = ((t == ti) & (e == 1) & (g == 0)).sum()
        O1 += d1
        E1 += d * n1 / n
        if n > 1:
            V += d * (n1 * n2 / n**2) * (n - d) / (n - 1)
    chi2 = (O1 - E1) ** 2 / V if V > 0 else float("nan")
    p = float(stats.chi2.sf(chi2, 1)) if V > 0 else float("nan")
    return {"chi2": float(chi2), "p_value": p, "observed_group_a": int(O1), "expected_group_a": float(E1)}


# ---------- rank / two-group tests ----------
def mann_whitney(a, b) -> dict:
    """Two-sided Mann-Whitney U with rank-biserial effect size.

    rank_biserial in [-1, 1]: positive = group a tends to have larger values than group b.
    """
    a = pd.Series(a).dropna().astype(float)
    b = pd.Series(b).dropna().astype(float)
    if len(a) < 2 or len(b) < 2:
        return {"n_a": len(a), "n_b": len(b), "U": np.nan, "p_value": np.nan, "rank_biserial": np.nan,
                "median_a": a.median() if len(a) else np.nan, "median_b": b.median() if len(b) else np.nan}
    res = stats.mannwhitneyu(a, b, alternative="two-sided")
    U = res.statistic
    rbc = 2 * U / (len(a) * len(b)) - 1
    return {"n_a": len(a), "n_b": len(b), "U": float(U), "p_value": float(res.pvalue),
            "rank_biserial": float(rbc), "median_a": float(a.median()), "median_b": float(b.median())}


def spearman(x, y) -> dict:
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 3 or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return {"n": len(d), "rho": np.nan, "p_value": np.nan}
    r = stats.spearmanr(d["x"], d["y"])
    return {"n": len(d), "rho": float(r.statistic), "p_value": float(r.pvalue)}


def chi_square(table: pd.DataFrame) -> dict:
    """Chi-square test of independence with Cramér's V. Flags low expected counts."""
    chi2, p, dof, expected = stats.chi2_contingency(table.values, correction=False)
    n = table.values.sum()
    k = min(table.shape) - 1
    v = float(np.sqrt(chi2 / (n * k))) if k > 0 else np.nan
    low_expected = bool((expected < 5).any())
    return {"chi2": float(chi2), "dof": int(dof), "p_value": float(p), "cramers_v": v,
            "min_expected": float(expected.min()), "low_expected_cells": low_expected}


def chi_square_permutation(table: pd.DataFrame, n_perm: int = 10_000, seed: int = 42) -> dict:
    """Permutation chi-square test for sparse tables (valid when expected counts are small).

    Shuffles the group labels n_perm times, keeping the stage labels fixed.
    """
    rng = np.random.default_rng(seed)
    row_labels = np.repeat(np.arange(table.shape[0]), table.values.sum(axis=1))
    col_labels = np.repeat(np.arange(table.shape[1]), table.values.sum(axis=0))
    # Build the observed pairing from the table
    obs_chi2 = chi_square(table)["chi2"]
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(col_labels)
        t = np.zeros_like(table.values)
        np.add.at(t, (row_labels, perm), 1)
        t = pd.DataFrame(t)
        if t.values.sum(axis=0).min() == 0 or t.values.sum(axis=1).min() == 0:
            continue
        chi2 = stats.chi2_contingency(t.values, correction=False)[0]
        if chi2 >= obs_chi2 - 1e-12:
            count += 1
    p = (count + 1) / (n_perm + 1)
    return {"chi2": obs_chi2, "p_value_permutation": float(p), "n_perm": n_perm, "seed": seed}


def bootstrap_median_ci(values, n_boot=5000, seed=42, alpha=0.05):
    """Percentile bootstrap CI for the median (reproducible via fixed seed)."""
    x = np.asarray(pd.Series(values).dropna(), dtype=float)
    if len(x) < 3:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    meds = np.median(rng.choice(x, size=(n_boot, len(x)), replace=True), axis=1)
    return (float(np.quantile(meds, alpha / 2)), float(np.quantile(meds, 1 - alpha / 2)))


# ---------- multiple comparisons ----------
def holm_adjust(p_values) -> np.ndarray:
    """Holm step-down adjusted p-values (monotone, capped at 1)."""
    p = np.asarray(p_values, dtype=float)
    out = np.full_like(p, np.nan)
    idx = np.where(~np.isnan(p))[0]
    order = idx[np.argsort(p[idx])]
    m = len(order)
    running = 0.0
    for rank, i in enumerate(order):
        adj = (m - rank) * p[i]
        running = max(running, adj)
        out[i] = min(running, 1.0)
    return out
