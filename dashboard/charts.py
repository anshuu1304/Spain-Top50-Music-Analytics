"""Plotly chart builders. Each takes prepared DataFrames and returns a Figure, or None when there is
no data to show (the page then displays an empty-state message). No sample data is ever generated."""
import plotly.graph_objects as go

from dashboard.styling import LAYOUT, PALETTE


def _finish(fig, title, xtitle="", ytitle=""):
    fig.update_layout(title=title, xaxis_title=xtitle, yaxis_title=ytitle, **LAYOUT)
    return fig


def daily_flow(daily):
    if daily is None or daily.empty:
        return None
    fig = go.Figure()
    fig.add_bar(x=daily["date"], y=daily["new_entries"], name="New entries", marker_color=PALETTE["bronze"])
    fig.add_bar(x=daily["date"], y=daily["reentries"], name="Re-entries", marker_color=PALETTE["slate"])
    fig.add_bar(x=daily["date"], y=-daily["exits"], name="Exits (shown below zero)", marker_color=PALETTE["burgundy"])
    fig.update_layout(barmode="relative")
    return _finish(fig, "Daily entries and exits (complete snapshots)", "Date", "Songs")


def monthly_turnover(monthly):
    if monthly is None or monthly.empty:
        return None
    fig = go.Figure(go.Bar(x=monthly["month"], y=monthly["avg_daily_turnover"], marker_color=PALETTE["slate"],
                           customdata=monthly[["transitions", "total_entries"]],
                           hovertemplate="%{x}<br>average daily turnover %{y:.2f}<br>days %{customdata[0]}"
                                         "<br>total entries %{customdata[1]}<extra></extra>"))
    return _finish(fig, "Average daily turnover by month", "Month", "Songs per day")


def km_curves(curves: dict, title):
    """curves: {label: (durations, events)} already restricted to the filtered songs."""
    from src.statistical_analysis import kaplan_meier
    colors = [PALETTE["burgundy"], PALETTE["slate"]]
    fig = go.Figure()
    for (label, (dur, ev)), c in zip(curves.items(), colors):
        if len(dur) == 0:
            continue
        km = kaplan_meier(dur, ev)
        xs = [0] + km["time"].tolist()
        ys = [1] + km["survival"].tolist()
        fig.add_scatter(x=xs, y=ys, mode="lines", line=dict(shape="hv", color=c), name=f"{label} (n={len(dur)})")
    if not fig.data:
        return None
    fig.update_yaxes(range=[0, 1.02])
    return _finish(fig, title, "Days in first continuous run on the Top 50", "Share still on the playlist")


def grouped_stage_bar(tbl, group_col, title):
    """tbl: columns [group_col, stage, songs] for active songs."""
    if tbl is None or tbl.empty:
        return None
    fig = go.Figure()
    palette = [PALETTE["burgundy"], PALETTE["slate"], PALETTE["bronze"], PALETTE["grey"]]
    for i, (g, d) in enumerate(tbl.groupby(group_col)):
        fig.add_bar(x=d["stage"], y=d["songs"], name=str(g), marker_color=palette[i % len(palette)])
    fig.update_layout(barmode="group")
    return _finish(fig, title, "Lifecycle stage", "Active songs")


def bar_chart(x, y, title, xtitle, ytitle, color=None, hover=None):
    if x is None or len(x) == 0:
        return None
    fig = go.Figure(go.Bar(x=list(x), y=list(y), marker_color=color or PALETTE["bronze"],
                           hovertemplate=hover))
    return _finish(fig, title, xtitle, ytitle)


def scatter_popularity_rank(lc):
    d = lc.dropna(subset=["popularity_max", "best_position"]) if lc is not None else None
    if d is None or d.empty:
        return None
    fig = go.Figure(go.Scatter(
        x=d["best_position"], y=d["popularity_max"], mode="markers",
        marker=dict(color=PALETTE["bronze"], size=7, opacity=0.8),
        text=d["song"] + " — " + d["artist"],
        hovertemplate="%{text}<br>best position %{x}<br>max popularity %{y}<extra></extra>"))
    fig.update_xaxes(autorange="reversed", title="Best position (1 = best)")
    return _finish(fig, "Popularity vs best rank", "", "Maximum observed popularity")


def rank_progression(clean_song, title):
    if clean_song is None or clean_song.empty:
        return None
    d = clean_song.sort_values("date")
    fig = go.Figure(go.Scatter(x=d["date"], y=d["position"], mode="lines+markers",
                               line=dict(color=PALETTE["charcoal"]), marker=dict(size=5),
                               hovertemplate="%{x|%d %b %Y}<br>position %{y}<extra></extra>"))
    fig.update_yaxes(title="Position (1 = best)", range=[50.5, 0.5])
    return _finish(fig, title, "Date")


def runs_timeline(runs, title):
    if runs is None or runs.empty:
        return None
    fig = go.Figure()
    for _, r in runs.iterrows():
        fig.add_scatter(x=[r["start"], r["end"]], y=[r["run"], r["run"]], mode="lines+markers",
                        line=dict(color=PALETTE["burgundy"], width=8), name=f"run {r['run']}",
                        hovertemplate=f"run {r['run']}: %{{x|%d %b}}<extra></extra>")
    fig.update_yaxes(title="Run", dtick=1, autorange="reversed")
    return _finish(fig, title, "Date")
