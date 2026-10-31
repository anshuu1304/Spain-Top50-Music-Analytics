"""Spain Top 50 — song lifecycle and playlist rotation, historical analysis (18 May – 14 Oct 2024).

Run:  streamlit run app.py

Every descriptive number and chart responds to the sidebar filters. Significance tests are
computed once on the full dataset and are labelled as such.
"""
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dashboard import charts, views  # noqa: E402
from dashboard.components import caveat_html, fmt_float, fmt_int, kpi_html  # noqa: E402
from dashboard.filters import STAGES, Filters, apply_daily_filters, apply_song_filters, csv_bytes  # noqa: E402
from dashboard.styling import CSS  # noqa: E402
from src.config import (  # noqa: E402
    DECLINE_MIN_LOSS, GROWTH_MIN_GAIN, MIN_OBSERVATIONS, NEW_ENTRY_WINDOW_DAYS, RAW_DATA_PATH, RECENT_WINDOW, TOP_N_PEAK,
)

st.set_page_config(page_title="Spain Top 50 — Lifecycle & Rotation (2024)", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

FULL_SAMPLE_NOTE = "Full-dataset statistic. Sidebar filters do not change this value."
HISTORICAL_NOTE = ("Historical data: Spain Top 50 snapshots from 18 May to 14 October 2024. "
                   "These do not describe current (2026) market behaviour.")


@st.cache_data(show_spinner="Loading and analysing the dataset…")
def load_bundle(path: str) -> dict:
    from src.data_loader import load_raw
    from src.insights import build_all
    from src.preprocessing import attribute_conflicts, build_clean_rows, song_master
    from src.maturity_analysis import song_frame

    raw = load_raw(path)
    clean, rejected, log = build_clean_rows(raw)
    master = song_master(clean)
    conflicts = attribute_conflicts(clean)
    out = build_all(clean, master)
    dq = views.data_quality_tables(raw, clean, master, conflicts, pd.DataFrame(log))
    return {
        "raw": raw, "clean": clean, "master": master, "out": out, "dq": dq,
        "sf": out["song_frame"], "lc": out["lifecycle"], "daily": out["daily"], "surv": out["survival"],
        "results": out["results"], "rejected_rows": len(rejected),
    }


def init_state(dmin, dmax):
    defaults = {"f_dates": (dmin, dmax), "f_stages": list(STAGES), "f_explicit": "All",
                "f_album": "All", "f_artist": "", "f_song": ""}
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def reset_filters(dmin, dmax):
    st.session_state["f_dates"] = (dmin, dmax)
    st.session_state["f_stages"] = list(STAGES)
    st.session_state["f_explicit"] = "All"
    st.session_state["f_album"] = "All"
    st.session_state["f_artist"] = ""
    st.session_state["f_song"] = ""


def sidebar(dmin, dmax) -> Filters:
    with st.sidebar:
        st.header("Filters")
        dr = st.date_input("Date range", min_value=dmin, max_value=dmax, key="f_dates")
        st.multiselect("Lifecycle stage (include 'Exited' to show songs that left)", STAGES, key="f_stages")
        st.selectbox("Explicit content", ["All", "Explicit", "Clean"], key="f_explicit")
        st.selectbox("Album type", ["All", "album", "single"], key="f_album")
        st.text_input("Artist contains", key="f_artist")
        st.text_input("Song contains", key="f_song")
        st.button("Reset filters", on_click=reset_filters, args=(dmin, dmax))
        st.caption("Date range keeps songs whose observed span overlaps it, and charts only those days.")
    start, end = (dr if isinstance(dr, tuple) and len(dr) == 2 else (dmin, dmax))
    stages = st.session_state["f_stages"]
    return Filters(pd.Timestamp(start), pd.Timestamp(end), stages if stages else [],
                   st.session_state["f_explicit"], st.session_state["f_album"],
                   st.session_state["f_artist"], st.session_state["f_song"])


def empty(msg="No songs match the current filters. Widen the date range or clear a filter."):
    st.info(msg)


def page_overview(B, sf_f, daily_f, f):
    res = B["results"]
    k = views.kpi_summary(sf_f)
    if not k.get("songs"):
        return empty()
    cols = st.columns(5)
    cols[0].markdown(kpi_html("Songs shown", fmt_int(k["songs"]), f"{k['active']} active, {k['exited']} exited"), unsafe_allow_html=True)
    cols[1].markdown(kpi_html("Song-date observations", fmt_int(k["observations"]), "rows in the filtered songs"), unsafe_allow_html=True)
    cols[2].markdown(kpi_html("Avg. appearances", fmt_float(k["avg_appearances"]), "cumulative days on chart"), unsafe_allow_html=True)
    cols[3].markdown(kpi_html("Avg. best position", fmt_float(k["avg_best_position"]), "1 = best; lower is better"), unsafe_allow_html=True)
    cols[4].markdown(kpi_html("Re-entered songs", f"{k['reentry_share_pct']:.0f}%", "returned after a gap"), unsafe_allow_html=True)
    rs = views.rotation_summary(daily_f)
    if rs.get("transitions"):
        st.caption(f"Playlist rotation in the selected dates: mean daily turnover {rs['mean_turnover']:.2f} songs; "
                   f"{rs['total_entries']} entries, of which {rs['total_reentries']} re-entries.")
    left, right = st.columns([3, 2])
    with left:
        fig = charts.monthly_turnover(views.monthly_from(daily_f))
        if fig:
            st.plotly_chart(fig, width="stretch", key="plotly_chart_109")
        else:
            empty("No complete-snapshot days in this date range.")
    with right:
        st.subheader("Key findings (full dataset)")
        cmp_alb = res["comparisons"][1]
        cmp_exp = res["comparisons"][0]
        st.markdown(
            f"- Singles stay longer than album tracks (median appearances {cmp_alb['appearances_MW']['median_b']:.0f} "
            f"vs {cmp_alb['appearances_MW']['median_a']:.0f}; Holm-adjusted p < 0.001).\n"
            f"- Explicit and clean tracks show no significant difference after correction "
            f"(p = {cmp_exp['appearances_MW']['p_holm']:.2f}).\n"
            f"- Duration is unrelated to tenure, rank or popularity.\n"
            f"- Re-entries are {res['rotation']['share_of_entries_that_are_reentries_pct']:.0f}% of all entries.")
        st.caption(FULL_SAMPLE_NOTE)
    t1, t2 = st.columns(2)
    with t1:
        st.subheader("Top-ranked songs (filtered)")
        top = views.top_songs(sf_f)
        st.dataframe(top, width="stretch", hide_index=True)
    with t2:
        st.subheader(f"Recent entries (last {views.FRESH_DAYS} days)")
        rec = views.recent_entries(sf_f, B["window_end"])
        if rec.empty:
            st.info("No first-time entries in the last 14 days under the current filters.")
        else:
            st.dataframe(rec, width="stretch", hide_index=True)


def page_lifecycle(B, sf_f, f):
    if sf_f.empty:
        return empty()
    options = sf_f.sort_values(["song", "artist"])["song_key"].tolist()
    labels = sf_f.set_index("song_key")
    sel = st.selectbox("Select a song", options,
                       format_func=lambda key: f"{labels.loc[key, 'song']} — {labels.loc[key, 'artist']}")
    row = sf_f.set_index("song_key").loc[sel]
    c = st.columns(4)
    c[0].metric("First observed", str(row["first_seen"].date()) + (" (on chart on 18 May)" if row["left_censored"] else ""))
    c[1].metric("Best position", int(row["best_position"]))
    c[2].metric("Days from first observation to best", int(row["time_to_peak_days"]))
    c[3].metric("Lifecycle stage", row["lifecycle_stage"])
    st.caption(f"Status: {row['status']}. Stage rule: {row['stage_reason']}.")
    clean_song = B["clean"][B["clean"]["song_key"] == sel]
    left, right = st.columns(2)
    with left:
        fig = charts.rank_progression(clean_song, f"{row['song']}: rank by date")
        if fig:
            st.plotly_chart(fig, width="stretch", key="plotly_chart_154")
        else:
            empty("No observations for this song.")
    with right:
        runs = views.song_runs(B["clean"], sel)
        fig = charts.runs_timeline(runs.assign(start=pd.to_datetime(runs["start"]), end=pd.to_datetime(runs["end"])),
                                   "Continuous runs on the chart (re-entries = runs after the first)")
        if fig:
            st.plotly_chart(fig, width="stretch", key="plotly_chart_159")
        else:
            empty("No runs for this song.")
        st.dataframe(runs, width="stretch", hide_index=True)
    st.subheader("Stage distribution of active songs (filtered)")
    sc = views.stage_counts(sf_f)
    if sc["songs"].sum() == 0:
        st.info("No active songs in the filtered set.")
    else:
        st.dataframe(sc, width="stretch", hide_index=True)
    with st.expander("How stages are assigned"):
        st.markdown(
            f"- **New Entry:** first continuous run began within the last {NEW_ENTRY_WINDOW_DAYS} observed days, and the entry was observed.\n"
            f"- **Insufficient history:** fewer than {MIN_OBSERVATIONS} appearances.\n"
            f"- **Decline:** net loss of at least {DECLINE_MIN_LOSS} positions over the last {RECENT_WINDOW} appearances, with at least 2 of 3 steps worsening.\n"
            f"- **Peak:** latest position within the Top {TOP_N_PEAK}.\n"
            f"- **Growth:** net gain of at least {GROWTH_MIN_GAIN} positions, still outside the Top {TOP_N_PEAK}.\n"
            f"- **Mature:** otherwise (stable outside the Top {TOP_N_PEAK}).")


def page_rotation(B, daily_f, f):
    st.caption("Playlist-level measures. Song-attribute filters do not apply here; the date range does.")
    if daily_f.empty:
        return empty("No complete-snapshot days in this date range.")
    rs = views.rotation_summary(daily_f)
    cols = st.columns(4)
    cols[0].markdown(kpi_html("Transitions", fmt_int(rs["transitions"]), "consecutive complete days"), unsafe_allow_html=True)
    cols[1].markdown(kpi_html("Mean daily turnover", fmt_float(rs["mean_turnover"], 2), "(entries+exits)/2"), unsafe_allow_html=True)
    cols[2].markdown(kpi_html("Mean retention", f"{rs['mean_retention_pct']:.1f}%", "share of 50 kept from previous day"), unsafe_allow_html=True)
    cols[3].markdown(kpi_html("Zero-entry days", fmt_int(rs["zero_entry_days"]), f"of {rs['transitions']} transitions"), unsafe_allow_html=True)
    fig = charts.daily_flow(daily_f)
    st.plotly_chart(fig, width="stretch", key="plotly_chart_188")
    fig = charts.monthly_turnover(views.monthly_from(daily_f))
    if fig:
        st.plotly_chart(fig, width="stretch", key="plotly_chart_190")
    peak = daily_f.loc[daily_f["entries"].idxmax()]
    st.markdown(caveat_html(
        "With a fixed 50-song playlist, entries always equal exits, so daily turnover equals daily entries. "
        f"The busiest day in this range is {pd.Timestamp(peak['date']).date()} with {int(peak['entries'])} entries; "
        "see the Release strategy page for the 14 October 2024 wave."), unsafe_allow_html=True)
    with st.expander("Formulas"):
        st.markdown("Entry rate % = entries / 50 × 100. Exit rate % = exits / 50 × 100. "
                    "Turnover = (entries + exits) / 2. Retention % = retained / 50 × 100. "
                    "Transitions use only consecutive complete days; 15 Oct 2024 (8 rows) is excluded.")


def page_maturity(B, sf_f, surv_f, f):
    res = B["results"]
    st.caption(FULL_SAMPLE_NOTE + " Descriptive tables and curves below respond to the filters.")
    tbl = views.group_table(sf_f, "is_explicit")
    if tbl.empty:
        empty("Both explicit and clean songs are needed to compare them. Clear the explicit filter to see the comparison.")
    else:
        tbl = tbl.assign(is_explicit=tbl["is_explicit"].map({True: "Explicit", False: "Clean"}))
        st.dataframe(tbl, width="stretch", hide_index=True)
    left, right = st.columns(2)
    with left:
        sub = surv_f.merge(sf_f[["song_key", "is_explicit"]], on="song_key") if not surv_f.empty else surv_f
        curves = {"Explicit": (sub.loc[sub.is_explicit, "duration_days"], sub.loc[sub.is_explicit, "event"]),
                  "Clean": (sub.loc[~sub.is_explicit, "duration_days"], sub.loc[~sub.is_explicit, "event"])} if not sub.empty else {}
        fig = charts.km_curves(curves, "First-run survival: explicit vs clean (observed entries)") if curves else None
        if fig:
            st.plotly_chart(fig, width="stretch", key="plotly_chart_217")
        else:
            empty("No observed-entry songs in this selection.")
    with right:
        fig = charts.grouped_stage_bar(views.stage_by_group(sf_f, "is_explicit").assign(
            is_explicit=lambda d: d["is_explicit"].map({True: "Explicit", False: "Clean"})),
            "is_explicit", "Lifecycle stage of active songs")
        if fig:
            st.plotly_chart(fig, width="stretch", key="plotly_chart_222")
        else:
            empty("No active songs in this selection.")
    st.subheader("Full-dataset significance tests (explicit vs clean)")
    c = res["comparisons"][0]
    rows = [
        {"measure": "Cumulative appearances (observed entries)", **_mw_row(c["appearances_MW"])},
        {"measure": "Best position", **_mw_row(c["best_position_MW"])},
        {"measure": "Mean popularity", **_mw_row(c["popularity_mean_MW"])},
        {"measure": "Time to peak (observed entries)", **_mw_row(c["time_to_peak_MW"])},
        {"measure": "Rank volatility", **_mw_row(c["rank_volatility_MW"])},
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.markdown(caveat_html(
        f"First-run survival log-rank p = {c['first_run_logrank']['p_value']:.2f}. No measure is significant after "
        f"Holm correction. The all-songs appearance test (p = {c['appearances_all_songs_MW_descriptive']['p_value']:.4f}) is "
        "not used: explicit songs were less often on the chart on the first day, which biases it."), unsafe_allow_html=True)


def _mw_row(t):
    return {"median A": round(t["median_a"], 2), "median B": round(t["median_b"], 2),
            "p (raw)": f"{t['p_value']:.4f}", "p (Holm family)": f"{t['p_holm']:.4f}",
            "rank-biserial": round(t["rank_biserial"], 3)}


def page_strategy(B, sf_f, surv_f, f):
    res = B["results"]
    st.caption(FULL_SAMPLE_NOTE + " Descriptive tables and curves below respond to the filters.")
    left, right = st.columns(2)
    with left:
        tbl = views.group_table(sf_f, "album_type")
        if tbl.empty:
            empty("Both album and single tracks are needed to compare them.")
        else:
            st.dataframe(tbl, width="stretch", hide_index=True)
    with right:
        sub = surv_f.merge(sf_f[["song_key", "album_type"]], on="song_key") if not surv_f.empty else surv_f
        curves = {"Album": (sub.loc[sub.album_type == "album", "duration_days"], sub.loc[sub.album_type == "album", "event"]),
                  "Single": (sub.loc[sub.album_type == "single", "duration_days"], sub.loc[sub.album_type == "single", "event"])} if not sub.empty else {}
        fig = charts.km_curves(curves, "First-run survival: album vs single (observed entries)") if curves else None
        if fig:
            st.plotly_chart(fig, width="stretch", key="plotly_chart_260")
        else:
            empty("No observed-entry songs in this selection.")
    c = res["comparisons"][1]
    x = res["comparisons_excluding_14oct_cohort"]["album"]
    st.markdown(caveat_html(
        f"Full dataset: singles stay longer (appearances Holm-adjusted p < 0.001). Excluding the 14 October 2024 cohort "
        f"(which is mostly album tracks) the difference remains (p = {x['appearances_MW']['p_value']:.4f}) but is weaker. "
        f"The album survival difference is borderline after correction (Holm p = {c['first_run_logrank']['p_holm']:.3f}), "
        f"and the popularity difference is not significant after correction (Holm p = {c['popularity_mean_MW']['p_holm']:.2f})."),
        unsafe_allow_html=True)
    st.subheader("Album size (album tracks only)")
    at = views.album_size_table(sf_f)
    if at.empty:
        empty("No album tracks in this selection.")
    else:
        st.dataframe(at, width="stretch", hide_index=True)
        fig = charts.bar_chart(at["size_band"], at["median_appearances_observed_entry"], "Median appearances by album size",
                               "Album size", "Median appearances (observed entries)", color=None)
        if fig:
            st.plotly_chart(fig, width="stretch", key="plotly_chart_277")
    rel = {r["outcome"]: r for r in res["relationships"] if r["attribute"] == "total_tracks (albums only)"}
    if rel:
        st.caption(f"Within albums: total tracks vs cumulative appearances rho = {rel['cumulative appearances']['rho']:.2f} "
                   f"(Holm p = {rel['cumulative appearances']['p_holm']:.4f}). Across all songs the raw correlation is "
                   "confounded by format (singles have one track), so only the within-album result is reported.")
    st.subheader("Song duration (quartiles)")
    dt = views.duration_table(sf_f)
    if dt.empty:
        empty("Not enough songs to form duration quartiles.")
    else:
        st.dataframe(dt, width="stretch", hide_index=True)
    st.caption(f"Full dataset: duration quartiles differ in appearances by Kruskal-Wallis p = {res['duration_quartile_kruskal']['p']:.2f}; "
               "no duration effect is claimed.")
    st.subheader("Fresh vs established songs")
    fv = views.fresh_vs_established(sf_f, B["window_end"])
    if fv.empty:
        empty()
    else:
        st.dataframe(fv, width="stretch", hide_index=True)
    st.subheader("Popularity by lifecycle stage (active songs)")
    ps = views.popularity_by_stage(sf_f)
    if ps.empty:
        empty("No active songs with popularity data in this selection.")
    else:
        st.dataframe(ps, width="stretch", hide_index=True)
    st.subheader("Recommendations (from the full-dataset findings)")
    st.markdown(
        "1. Plan for fast turnover: the median first run was "
        f"{res['kpis']['median_observed_first_run_days_KM']:.0f} days, so campaigns should concentrate on the first two weeks.\n"
        "2. Measure debut performance separately: most songs reach their best position on the first observed day.\n"
        "3. Verify the 14 October 2024 wave against release records before drawing album-strategy conclusions.\n"
        "4. Use singles where chart longevity is the goal, pending release-date confirmation.\n"
        "5. Do not base format decisions on explicit status or duration; the data show no reliable link.")


def page_explorer(B, sf_f, daily_f, f):
    st.write(f"{len(sf_f)} songs match the filters.")
    if sf_f.empty:
        return empty()
    cols = ["song", "artist", "album_type", "is_explicit", "first_seen", "last_seen", "status",
            "n_appearances", "reentries", "best_position", "time_to_peak_days", "popularity_mean", "lifecycle_stage"]
    table = sf_f[cols].sort_values("best_position")
    st.dataframe(table, width="stretch", hide_index=True)
    c1, c2 = st.columns(2)
    c1.download_button("Download filtered songs (CSV)", csv_bytes(table), "filtered_songs.csv", "text/csv")
    c2.download_button("Download filtered daily rotation (CSV)", csv_bytes(daily_f), "filtered_daily_rotation.csv", "text/csv")
    st.subheader("Song detail")
    key = st.selectbox("Choose a song", sf_f.sort_values("song")["song_key"].tolist(),
                       format_func=lambda k: sf_f.set_index("song_key").loc[k, "song"] + " — " + sf_f.set_index("song_key").loc[k, "artist"])
    row = sf_f.set_index("song_key").loc[key]
    detail = {"Status": row["status"], "Stage": row["lifecycle_stage"], "Stage reason": row["stage_reason"],
              "Cumulative appearances": int(row["n_appearances"]), "Re-entries": int(row["reentries"]),
              "Longest run (days)": int(row["longest_run_days"]), "Best position": int(row["best_position"]),
              "Median position": float(row["median_position"]), "Rank volatility (SD)": fmt_float(row["rank_volatility_sd"], 2),
              "Mean popularity": fmt_float(row["popularity_mean"], 1), "Album type": row["album_type"],
              "Explicit": bool(row["is_explicit"]), "Total tracks": int(row["total_tracks"]) if pd.notna(row["total_tracks"]) else "n/a",
              "Duration (min)": fmt_float(row["duration_ms"] / 60000, 2) if pd.notna(row["duration_ms"]) else "n/a",
              "Attribute conflict": bool(row["any_attribute_conflict"]),
              "Shared title (other artist credits exist)": bool(row["shared_title_flag"])}
    detail_table = pd.DataFrame({
        "Metric": list(detail.keys()),
        "Value": [str(v) for v in detail.values()]
    })
    st.dataframe(detail_table, width="stretch", hide_index=True)


def page_quality(B):
    dq, res = B["dq"], B["results"]
    st.markdown(caveat_html(HISTORICAL_NOTE), unsafe_allow_html=True)
    st.subheader("Dataset overview")
    st.dataframe(dq["checks"], width="stretch", hide_index=True)
    left, right = st.columns(2)
    with left:
        st.subheader("Missing values (blank cells per column)")
        st.dataframe(dq["missing"], width="stretch", hide_index=True)
    with right:
        st.subheader("Snapshot completeness by date")
        incomplete = dq["dates"][dq["dates"]["status"] != "complete"]
        st.write(f"{len(dq['dates'])} dates. Incomplete: {len(incomplete)}.")
        st.dataframe(incomplete if not incomplete.empty else dq["dates"].head(0), width="stretch", hide_index=True)
    st.subheader("Cleaning log")
    st.dataframe(dq["log"], width="stretch", hide_index=True)
    st.subheader("Attribute conflicts")
    if dq["conflicts"].empty:
        st.info("No attribute conflicts.")
    else:
        conflicts = dq["conflicts"].copy()
        if "value" in conflicts.columns:
            conflicts["value"] = conflicts["value"].astype("string")
        st.dataframe(conflicts, width="stretch", hide_index=True)
    st.subheader("KPI definitions")
    kpis = pd.DataFrame([
        ("Average days on playlist", "Mean cumulative appearances", "Right-censored and left-truncated"),
        ("Median observed tenure", "Kaplan-Meier median of first continuous run (observed entries)", "Undefined if the curve never reaches 0.5"),
        ("Entry-to-peak time", "Median days from first observation to best position (observed entries)", "Many songs peak on day 0"),
        ("Churn rate", "Mean daily exit rate %, over valid consecutive complete days", "Equals entry rate by construction"),
        ("Daily turnover", "(entries + exits) / 2", "Equals daily entries for a fixed 50-song playlist"),
        ("Retention Stability Index", "Mean retention % / (1 + CV of daily entries)", "Custom index; roughly 0 to 100; higher = steadier"),
        ("Explicit lifecycle difference", "KM median first-run length, explicit minus clean", "Replaces a composite score"),
        ("Single vs album longevity ratio", "Median appearances album / single (observed entries)", "Ratio of medians"),
        ("Average peak position", "Mean of best position per song", "1 = best"),
        ("Average re-entry frequency", "Mean re-entries per song", "Reported for all songs and observed entries"),
    ], columns=["KPI", "Definition", "Note"])
    st.dataframe(kpis, width="stretch", hide_index=True)
    st.subheader("Known limitations")
    st.markdown(
        "- Historical 2024 data from one playlist; not generalisable to 2026 or other charts.\n"
        "- 50 songs were already charted on 18 May (entry unobserved); 50 were still charted on 14 Oct (exit unobserved).\n"
        "- 15 Oct 2024 holds only 8 of 50 positions. It is excluded from transitions and not treated as exits.\n"
        "- The 14 Oct 2024 entry wave (20 first appearances, 19 by one artist) influences album and stage comparisons.\n"
        "- Popularity recorded as 0 is treated as missing (assumption).\n"
        "- Songs credited to different artist strings are kept separate; 14 titles need review.\n"
        "- Associations are not causal.")


def main():
    st.title("Spain Top 50: song lifecycle and playlist rotation")
    st.markdown(caveat_html(HISTORICAL_NOTE + " Rank 1 is the best position."), unsafe_allow_html=True)
    if not RAW_DATA_PATH.exists():
        st.error("The dataset file is missing. Place Atlantic_Spain.csv in data/raw/ and reload the page.")
        return
    try:
        B = load_bundle(str(RAW_DATA_PATH))
    except Exception:
        st.error("The dataset could not be processed. Check that the file matches the expected format.")
        return
    B["window_end"] = pd.Timestamp(B["results"]["window"]["window_end"])
    dmin = B["clean"]["date"].min().date()
    dmax = B["clean"]["date"].max().date()
    init_state(dmin, dmax)
    f = sidebar(dmin, dmax)
    try:
        sf_f = apply_song_filters(B["sf"], f)
    except ValueError as e:
        st.error(str(e))
        return
    daily_f = apply_daily_filters(B["daily"], f)
    surv_f = views.survival_subset(B["surv"], sf_f)

    tabs = st.tabs(["Overview", "Song lifecycle", "Rotation & churn", "Content maturity",
                    "Release strategy", "Song explorer", "Data quality & methodology"])
    with tabs[0]:
        page_overview(B, sf_f, daily_f, f)
    with tabs[1]:
        page_lifecycle(B, sf_f, f)
    with tabs[2]:
        page_rotation(B, daily_f, f)
    with tabs[3]:
        page_maturity(B, sf_f, surv_f, f)
    with tabs[4]:
        page_strategy(B, sf_f, surv_f, f)
    with tabs[5]:
        page_explorer(B, sf_f, daily_f, f)
    with tabs[6]:
        page_quality(B)


if __name__ == "__main__":
    main()
