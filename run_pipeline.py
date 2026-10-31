"""End-to-end pipeline. Run from project root:  python run_pipeline.py

Stages: load -> validate/clean -> identity & conflicts -> lifecycle -> churn -> maturity/popularity
-> statistics -> figures and exports. Each stage writes its outputs to disk.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import EXPORTS_DIR, PROCESSED_DIR, REPORTS_DIR, RAW_DATA_PATH  # noqa: E402
from src.data_loader import load_raw  # noqa: E402
from src.preprocessing import (  # noqa: E402
    attach_canonical, attribute_conflicts, build_clean_rows, song_master,
)


def write_conflict_report(conflicts: pd.DataFrame, master: pd.DataFrame) -> None:
    """Human-readable attribute-conflict report (Markdown)."""
    lines = ["# Attribute Conflict Report", "",
             "Conflicts are reported, never silently overwritten. Each song keeps its original rows.",
             "A canonical value per song is chosen only for song-level analysis:",
             "most frequent value across rows; ties go to the value that appeared first.",
             "`one_way_switch` = values change once over time (consistent with a real version change);",
             "`interleaved` = values alternate (possible data-entry noise).", "",
             f"Songs with at least one conflict: {int(master['any_attribute_conflict'].sum())} of {len(master)}.", ""]
    if conflicts.empty:
        lines.append("No conflicts found.")
    else:
        lines.append("| Song | Artist | Attribute | Value | Rows | First | Last | Pattern |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for _, r in conflicts.sort_values(["attribute", "song"]).iterrows():
            lines.append(f"| {r.song} | {r.artist} | {r.attribute} | {r.value} | {r.n_rows} | {r.first_date} | {r.last_date} | {r.pattern} |")
    (REPORTS_DIR / "attribute_conflict_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_cleaning() -> dict:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_raw(RAW_DATA_PATH)
    clean, rejected, log = build_clean_rows(raw)
    master = song_master(clean)
    conflicts = attribute_conflicts(clean)
    clean_full = attach_canonical(clean, master)

    clean_full.to_csv(PROCESSED_DIR / "spain_top50_clean.csv", index=False)
    master.to_csv(PROCESSED_DIR / "song_master.csv", index=False)
    rejected.to_csv(PROCESSED_DIR / "rejected_rows.csv", index=False)
    conflicts.to_csv(REPORTS_DIR / "attribute_conflicts.csv", index=False)
    pd.DataFrame(log).to_csv(REPORTS_DIR / "cleaning_log.csv", index=False)

    summary = {
        "raw_rows": int(len(raw)),
        "clean_rows": int(len(clean_full)),
        "rejected_rows": int(len(rejected)),
        "distinct_song_keys": int(master["song_key"].nunique()),
        "distinct_song_titles_normalised": int(master["song_norm"].nunique()),
        "distinct_artist_credits": int(master["artist_norm"].nunique()),
        "songs_with_attribute_conflict": int(master["any_attribute_conflict"].sum()),
        "attribute_conflict_rows": int(len(conflicts)),
        "songs_with_shared_title": int(master["shared_title_flag"].sum()),
        "rows_on_incomplete_snapshots": int((~clean_full["snapshot_complete"]).sum()),
        "first_date": str(clean_full["date"].min().date()),
        "last_date": str(clean_full["date"].max().date()),
    }
    write_conflict_report(conflicts, master)
    (REPORTS_DIR / "cleaning_summary.json").write_text(json.dumps(summary, indent=2))
    return summary




def run_analysis() -> dict:
    """Phases 4–7: lifecycle, churn, maturity, popularity, statistics, figures and exports."""
    import numpy as np
    from src.insights import build_all
    from src.figures import (
        daily_entries_exits, km_by_group, lifecycle_timeline, monthly_turnover,
        popularity_tenure, popularity_vs_rank, stage_distribution,
    )
    from src.maturity_analysis import first_run_survival
    from src.preprocessing import song_master
    from src.config import FIGURES_DIR

    clean = pd.read_csv(PROCESSED_DIR / "spain_top50_clean.csv", parse_dates=["date"])
    clean["is_explicit"] = clean["is_explicit"].astype(bool)
    clean["snapshot_complete"] = clean["snapshot_complete"].astype(bool)
    master = pd.read_csv(PROCESSED_DIR / "song_master.csv")
    # Recompute from the cleaned, typed rows to avoid any CSV round-trip drift
    from src.preprocessing import build_clean_rows
    from src.data_loader import load_raw
    clean_typed, _, _ = build_clean_rows(load_raw(RAW_DATA_PATH))
    master = song_master(clean_typed)
    out = build_all(clean_typed, master)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lc, daily, monthly = out["lifecycle"], out["daily"], out["monthly"]
    lc.to_csv(EXPORTS_DIR / "song_lifecycle.csv", index=False)
    daily.to_csv(EXPORTS_DIR / "daily_rotation.csv", index=False)
    monthly.to_csv(EXPORTS_DIR / "monthly_rotation.csv", index=False)
    out["group_explicit"].to_csv(EXPORTS_DIR / "group_explicit.csv", index=False)
    out["group_album"].to_csv(EXPORTS_DIR / "group_album.csv", index=False)
    out["relationships"].to_csv(EXPORTS_DIR / "relationships.csv", index=False)
    out["family"].to_csv(EXPORTS_DIR / "hypothesis_family_holm.csv", index=False)
    out["popularity_tenure"].to_csv(EXPORTS_DIR / "popularity_by_tenure.csv", index=False)

    surv = out["survival"]
    sf = out["song_frame"]
    daily_entries_exits(daily, FIGURES_DIR / "daily_entries_exits.png")
    monthly_turnover(monthly, FIGURES_DIR / "monthly_turnover.png")
    km_by_group(surv, {
        "Album": surv["song_key"].isin(sf.loc[sf.album_type == "album", "song_key"]),
        "Single": surv["song_key"].isin(sf.loc[sf.album_type == "single", "song_key"]),
    }, "First-run survival: album vs single tracks (observed entries)", FIGURES_DIR / "km_album_vs_single.png")
    km_by_group(surv, {
        "Explicit": surv["song_key"].isin(sf.loc[sf.is_explicit, "song_key"]),
        "Clean": surv["song_key"].isin(sf.loc[~sf.is_explicit, "song_key"]),
    }, "First-run survival: explicit vs clean (observed entries)", FIGURES_DIR / "km_explicit_vs_clean.png")
    stage_distribution(lc, FIGURES_DIR / "stage_distribution_active.png")
    popularity_tenure(out["popularity_tenure"], FIGURES_DIR / "popularity_by_tenure.png")
    popularity_vs_rank(lc, FIGURES_DIR / "popularity_vs_rank.png")
    lifecycle_timeline(clean_typed, lc, FIGURES_DIR / "lifecycle_timeline_top30.png")

    r = out["results"]
    (REPORTS_DIR / "results.json").write_text(json.dumps(r, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    return {"songs": len(lc), "figures": sorted(p.name for p in FIGURES_DIR.glob("*.png")), "kpis": r["kpis"]}


if __name__ == "__main__":
    print(json.dumps(run_cleaning(), indent=2))
    print(json.dumps(run_analysis(), indent=2, default=str))
