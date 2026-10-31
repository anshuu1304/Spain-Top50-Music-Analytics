"""Static figures (matplotlib) for the report. Palette: charcoal, bronze, slate, burgundy."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.statistical_analysis import kaplan_meier  # noqa: E402

PALETTE = {"charcoal": "#2B2B2B", "bronze": "#B08D57", "slate": "#6B7C8F", "burgundy": "#7A2E3A", "grey": "#B8B8B8"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 12})


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def daily_entries_exits(daily: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(daily["date"], daily["entries"], color=PALETTE["bronze"], lw=1, alpha=0.6, label="Daily entries")
    ax.plot(daily["date"], daily["entries"].rolling(7, min_periods=1).mean(), color=PALETTE["burgundy"], lw=2, label="Entries, 7-day mean")
    ax.plot(daily["date"], daily["reentries"], color=PALETTE["slate"], lw=1, ls=":", label="of which re-entries")
    ax.set_title("Daily song entries into the Top 50 (complete snapshots only, 2024)")
    ax.set_ylabel("Songs per day"); ax.set_xlabel("Date (2024)")
    ax.legend(frameon=False)
    _save(fig, path)


def monthly_turnover(monthly: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(monthly["month"], monthly["avg_daily_turnover"], color=PALETTE["slate"])
    for x, (y, n) in enumerate(zip(monthly["avg_daily_turnover"], monthly["transitions"])):
        ax.text(x, y + 0.03, f"{y:.2f}\n(n={n} days)", ha="center", fontsize=8)
    ax.set_title("Average daily turnover by month (songs per day, (entries+exits)/2)")
    ax.set_ylabel("Average daily turnover (songs)"); ax.set_ylim(0, monthly["avg_daily_turnover"].max() * 1.35)
    _save(fig, path)


def km_by_group(surv: pd.DataFrame, group_col_map: dict, title: str, path, labels=("A", "B")):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = [PALETTE["burgundy"], PALETTE["slate"]]
    for (name, mask), c in zip(group_col_map.items(), colors):
        s = surv[mask]
        km = kaplan_meier(s["duration_days"], s["event"])
        ax.step(np.r_[0, km["time"]], np.r_[1, km["survival"]], where="post", color=c, lw=2,
                label=f"{name} (n={len(s)})")
    ax.set_title(title)
    ax.set_xlabel("Days in first continuous run on the Top 50")
    ax.set_ylabel("Share still on playlist (Kaplan-Meier)")
    ax.set_ylim(0, 1.02); ax.legend(frameon=False)
    _save(fig, path)


def stage_distribution(lc: pd.DataFrame, path):
    act = lc[lc["right_censored"]]
    order = ["New Entry", "Growth Phase", "Peak Phase", "Mature Phase", "Decline Phase", "Insufficient history"]
    counts = act["lifecycle_stage"].value_counts().reindex(order).fillna(0)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(counts.index[::-1], counts.values[::-1], color=PALETTE["bronze"])
    for i, v in enumerate(counts.values[::-1]):
        ax.text(v + 0.3, i, str(int(v)), va="center")
    ax.set_title(f"Lifecycle stage of the {len(act)} songs active at window end (14 Oct 2024)")
    ax.set_xlabel("Songs")
    _save(fig, path)


def popularity_tenure(pop_tenure: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(pop_tenure))
    y = pop_tenure["mean_within_song_deviation"]
    e = 1.96 * pop_tenure["se_within_song_deviation"]
    ax.errorbar(x, y, yerr=e, fmt="o-", color=PALETTE["charcoal"], ecolor=PALETTE["grey"], capsize=4)
    ax.axhline(0, color=PALETTE["grey"], lw=1)
    ax.set_xticks(x); ax.set_xticklabels(pop_tenure["tenure_bucket_days"])
    ax.set_xlabel("Days since first observed appearance (observed-entry songs)")
    ax.set_ylabel("Popularity vs own average (points)")
    ax.set_title("Within-song popularity over playlist tenure (95% CI)")
    _save(fig, path)


def popularity_vs_rank(lc: pd.DataFrame, path):
    d = lc.dropna(subset=["popularity_max", "best_position"])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    c = np.where(d["right_censored"], PALETTE["burgundy"], PALETTE["slate"])
    ax.scatter(d["best_position"], d["popularity_max"], c=c, s=18, alpha=0.8)
    ax.invert_xaxis()
    ax.set_xlabel("Best playlist position (1 = best; axis reversed)")
    ax.set_ylabel("Maximum observed popularity")
    ax.set_title("Popularity vs best rank (red = active at window end)")
    _save(fig, path)


def lifecycle_timeline(clean: pd.DataFrame, lc: pd.DataFrame, path, top_n=30):
    """Gantt-style: first-to-last observed span with observed days highlighted, for top songs by best rank."""
    top = lc.sort_values(["best_position", "n_appearances"], ascending=[True, False]).head(top_n)
    fig, ax = plt.subplots(figsize=(10, 9))
    for i, (_, r) in enumerate(top.iloc[::-1].iterrows()):
        days = clean.loc[clean.song_key == r.song_key, "date"]
        ax.scatter(days, [i] * len(days), s=6, color=PALETTE["bronze"] if not r.right_censored else PALETTE["burgundy"])
    ax.set_yticks(range(len(top))); ax.set_yticklabels([f"{s} ({a})"[:40] for s, a in zip(top.iloc[::-1].song, top.iloc[::-1].artist)], fontsize=8)
    ax.set_title(f"Top {top_n} songs by best rank: observed dates (red = active)")
    ax.set_xlabel("Date (2024)")
    _save(fig, path)
