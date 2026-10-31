"""Statistical helper and maturity-analysis tests with hand-computed expectations."""
import numpy as np
import pandas as pd

from src.statistical_analysis import (
    chi_square, chi_square_permutation, holm_adjust, kaplan_meier, km_median, logrank_test,
    mann_whitney, spearman,
)


def test_kaplan_meier_hand_computed():
    # durations [1,2,2,3,5], events [1,1,0,1,0]
    # t=1: n=5,d=1 -> S=0.8 ; t=2: n=4,d=1 -> S=0.6 ; t=3: n=2,d=1 -> S=0.3
    km = kaplan_meier([1, 2, 2, 3, 5], [1, 1, 0, 1, 0])
    assert km["time"].tolist() == [1.0, 2.0, 3.0]
    assert km["n_risk"].tolist() == [5, 4, 2]
    np.testing.assert_allclose(km["survival"].values, [0.8, 0.6, 0.3])
    assert km_median(km) == 3.0


def test_km_median_nan_when_never_below_half():
    km = kaplan_meier([5, 6, 7], [0, 0, 0])            # no events at all
    assert np.isnan(km_median(km))


def test_logrank_identical_groups_not_significant():
    d = [3, 5, 7, 9, 11]
    e = [1, 0, 1, 1, 0]
    r = logrank_test(d, e, d, e)
    assert abs(r["chi2"]) < 1e-9
    assert r["p_value"] > 0.99


def test_logrank_detects_clear_difference():
    short = [1, 2, 3, 4, 5, 6, 7, 8]
    long_ = [30, 40, 50, 60, 70, 80, 90, 100]
    r = logrank_test(short, [1] * 8, long_, [1] * 8)
    assert r["p_value"] < 0.01


def test_mann_whitney_rank_biserial_extremes():
    r = mann_whitney([1, 2, 3], [4, 5, 6])
    assert r["rank_biserial"] == -1.0          # group a entirely below group b
    r2 = mann_whitney([4, 5, 6], [1, 2, 3])
    assert r2["rank_biserial"] == 1.0


def test_mann_whitney_too_small_returns_nan():
    assert np.isnan(mann_whitney([1], [2, 3, 4])["p_value"])


def test_spearman_perfect_and_undefined():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40])["rho"] == 1.0
    assert np.isnan(spearman([1, 1, 1, 1], [1, 2, 3, 4])["rho"])


def test_holm_adjustment_hand_computed():
    # sorted p: 0.01 (x3=0.03), 0.03 (x2=0.06), 0.04 (x1=0.04 -> cummax 0.06)
    adj = holm_adjust([0.01, 0.04, 0.03])
    np.testing.assert_allclose(adj, [0.03, 0.06, 0.06])


def test_holm_caps_at_one():
    assert holm_adjust([0.9])[0] == 0.9
    assert (holm_adjust([0.8, 0.9]) <= 1).all()


def test_chi_square_cramers_v_hand_computed():
    t = pd.DataFrame([[10, 0], [0, 10]])
    r = chi_square(t)
    assert abs(r["cramers_v"] - 1.0) < 1e-9
    assert r["dof"] == 1


def test_permutation_test_is_seeded_and_reproducible():
    t = pd.DataFrame([[8, 1, 0], [0, 1, 9]])
    a = chi_square_permutation(t, n_perm=300, seed=7)["p_value_permutation"]
    b = chi_square_permutation(t, n_perm=300, seed=7)["p_value_permutation"]
    assert a == b
    assert a < 0.05


def test_zero_popularity_becomes_missing(tmp_path):
    from src.data_loader import load_raw
    from src.preprocessing import build_clean_rows
    header = "date,position,song,artist,popularity,duration\\_ms,album_type,total_tracks,is_explicit,album_cover_url"
    p = tmp_path / "pop.csv"
    p.write_text(header + "\n01-01-2024,1,A,X,0,200000,single,1,FALSE,u\n02-01-2024,1,A,X,80,200000,single,1,FALSE,u\n",
                 encoding="utf-8")
    clean, _, _ = build_clean_rows(load_raw(p))
    assert clean["popularity_zero_flag"].tolist() == [True, False]
    assert pd.isna(clean["popularity_valid"].iloc[0])
    assert clean["popularity"].tolist() == [0, 80]          # original preserved
