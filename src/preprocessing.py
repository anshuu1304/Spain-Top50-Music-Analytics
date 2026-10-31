"""Cleaning pipeline: typed, normalised, flagged — never silently altered.

Key design rules (documented in docs/methodology.md):
* Original text fields (song, artist, album_type, is_explicit...) are kept untouched.
* Normalised helper columns are added beside them (song_norm, artist_norm, song_key).
* Song identity = normalised title + normalised artist credit. Different artist
  credits are NEVER merged automatically, even when the title matches.
* Duplicates are flagged, not dropped.
* Attribute conflicts are listed in a report. A canonical value per song is chosen by
  a documented rule and stored in separate columns (canonical_*); original values stay.
* Rows that fail hard validation are quarantined in a rejects table, not deleted.
"""
import unicodedata
import re

import pandas as pd

from src.config import (
    ATTRIBUTES_CHECKED_FOR_CONFLICTS, PLAYLIST_SIZE,
)
from src.data_validation import (
    implausible_duration, invalid_popularity, invalid_rank, invalid_total_tracks,
    parse_bool, parse_dates, snapshot_completeness, to_int,
)


def normalise_text(value) -> str:
    """Unicode NFC, collapse whitespace, casefold. Accents are KEPT (e.g. 'rosalía')."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = unicodedata.normalize("NFC", str(value)).strip()
    s = re.sub(r"\s+", " ", s)
    return s.casefold()


def build_clean_rows(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Return (clean_rows, rejected_rows, cleaning_log)."""
    log: list[dict] = []
    df = raw.copy()

    df["date"] = parse_dates(df["date"])
    df["position"] = to_int(df["position"])
    df["popularity"] = to_int(df["popularity"])
    df["duration_ms"] = to_int(df["duration_ms"])
    df["total_tracks"] = to_int(df["total_tracks"])
    df["is_explicit"] = parse_bool(df["is_explicit"])
    df["album_type"] = df["album_type"].str.strip().str.lower()

    # Hard-validation failures are quarantined (not deleted)
    reason = pd.Series("", index=df.index, dtype="object")
    reason[df["date"].isna()] += "invalid_date;"
    reason[invalid_rank(df["position"]).fillna(True).astype(bool)] += "invalid_position;"
    reason[df["is_explicit"].isna()] += "invalid_is_explicit;"
    hard_bad = reason != ""
    rejected = df.loc[hard_bad].assign(reject_reason=reason[hard_bad])
    log.append({"step": "quarantine_hard_failures", "rows_affected": int(hard_bad.sum()),
                "detail": "rows with unparseable date, invalid position or unknown explicit flag"})
    df = df.loc[~hard_bad].copy()

    # Popularity = 0 never occurs outside a small set of dates and the non-zero minimum is 3,
    # so 0 is treated as a missing-value marker (documented assumption). Original kept as `popularity`.
    df["popularity_zero_flag"] = df["popularity"] == 0
    df["popularity_valid"] = df["popularity"].where(~df["popularity_zero_flag"]).astype("Float64")
    log.append({"step": "popularity_zero_as_missing", "rows_affected": int(df["popularity_zero_flag"].sum()),
                "detail": "popularity == 0 treated as missing in popularity_valid (original kept); "
                          "non-zero minimum is 3, zeros cluster on specific dates"})

    # Soft-validation warnings (kept, flagged)
    df["warn_popularity"] = invalid_popularity(df["popularity"])
    df["warn_duration"] = implausible_duration(df["duration_ms"])
    df["warn_total_tracks"] = invalid_total_tracks(df["total_tracks"])
    for col in ["warn_popularity", "warn_duration", "warn_total_tracks"]:
        log.append({"step": col, "rows_affected": int(df[col].sum()), "detail": "soft validation warning (row kept)"})

    # Text normalisation: originals preserved
    df["song_norm"] = df["song"].map(normalise_text)
    df["artist_norm"] = df["artist"].map(normalise_text)
    df["song_key"] = df["song_norm"] + " || " + df["artist_norm"]
    log.append({"step": "normalise_text", "rows_affected": len(df),
                "detail": "song_norm/artist_norm = NFC + collapse whitespace + casefold; originals kept"})

    # Duplicate flags (never dropped)
    original_fields = ["date", "position", "song", "artist", "popularity", "duration_ms",
                       "album_type", "total_tracks", "is_explicit", "album_cover_url"]
    df["dup_exact_row"] = df.duplicated(subset=original_fields, keep=False)
    df["dup_date_position"] = df.duplicated(subset=["date", "position"], keep=False)
    df["dup_date_song_key"] = df.duplicated(subset=["date", "song_key"], keep=False)
    for col in ["dup_exact_row", "dup_date_position", "dup_date_song_key"]:
        log.append({"step": col, "rows_affected": int(df[col].sum()), "detail": "duplicate flag (rows kept)"})

    # Snapshot completeness per date
    comp = snapshot_completeness(df[["date", "position"]].dropna())
    df = df.merge(comp[["date", "n_rows", "complete"]].rename(columns={"n_rows": "date_row_count", "complete": "snapshot_complete"}),
                  on="date", how="left")
    log.append({"step": "snapshot_completeness", "rows_affected": int((~df["snapshot_complete"]).sum()),
                "detail": f"rows on dates that do not have exactly {PLAYLIST_SIZE} unique positions 1..{PLAYLIST_SIZE}"})

    # Shared-title flag: same normalised title under >1 artist credit
    artists_per_title = df.groupby("song_norm")["artist_norm"].nunique()
    shared = artists_per_title[artists_per_title > 1].index
    df["shared_title_flag"] = df["song_norm"].isin(shared)
    log.append({"step": "shared_title_flag", "rows_affected": int(df["shared_title_flag"].sum()),
                "detail": "titles credited to more than one artist string; NOT merged, flagged for review"})

    df = df.sort_values(["date", "position"]).reset_index(drop=True)
    rejected = rejected.reset_index(drop=True)
    return df, rejected, log


def conflict_pattern(sub: pd.DataFrame, attr: str) -> str:
    """Classify how a conflicting attribute varies over time.

    one_way_switch : values form contiguous time blocks (value changes = distinct values - 1),
                     consistent with a real version/release change (e.g. single -> album).
    interleaved    : values alternate over time; more likely data-entry or source noise.
    """
    seq = sub.sort_values(["date", "position"])[attr].astype(str).tolist()
    changes = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    n_distinct = len(set(seq))
    return "one_way_switch" if changes == n_distinct - 1 else "interleaved"


def attribute_conflicts(clean: pd.DataFrame) -> pd.DataFrame:
    """One row per (song_key, attribute, value) for every song whose attribute varies."""
    rows = []
    for attr in ATTRIBUTES_CHECKED_FOR_CONFLICTS:
        n_vals = clean.groupby("song_key")[attr].nunique(dropna=False)
        for key in n_vals[n_vals > 1].index:
            sub = clean.loc[clean["song_key"] == key]
            pattern = conflict_pattern(sub, attr)
            vc = sub.groupby(attr, dropna=False).agg(n_rows=("date", "size"), first_date=("date", "min"),
                                                      last_date=("date", "max")).reset_index()
            for _, r in vc.iterrows():
                rows.append({
                    "song_key": key,
                    "song": sub["song"].iloc[0],
                    "artist": sub["artist"].iloc[0],
                    "attribute": attr,
                    "value": r[attr],
                    "n_rows": int(r["n_rows"]),
                    "first_date": r["first_date"].date(),
                    "last_date": r["last_date"].date(),
                    "n_distinct_values": int(n_vals[key]),
                    "pattern": pattern,
                })
    return pd.DataFrame(rows)


def canonical_value(sub: pd.DataFrame, attr: str):
    """Canonical rule: most frequent value across rows; ties -> earliest first appearance; then value order."""
    agg = sub.groupby(attr, dropna=False).agg(n=("date", "size"), first=("date", "min")).reset_index()
    agg = agg.sort_values(["n", "first"], ascending=[False, True])
    return agg.iloc[0][attr]


def song_master(clean: pd.DataFrame) -> pd.DataFrame:
    """One row per song_key with original examples, canonical attributes and conflict flags."""
    records = []
    for key, sub in clean.groupby("song_key", sort=False):
        rec = {
            "song_key": key,
            "song_norm": sub["song_norm"].iloc[0],
            "artist_norm": sub["artist_norm"].iloc[0],
            "song_original": sub.sort_values("date")["song"].iloc[0],
            "artist_original": sub.sort_values("date")["artist"].iloc[0],
            "shared_title_flag": bool(sub["shared_title_flag"].iloc[0]),
        }
        for attr in ATTRIBUTES_CHECKED_FOR_CONFLICTS:
            rec[f"canonical_{attr}"] = canonical_value(sub, attr)
            rec[f"conflict_{attr}"] = bool(sub[attr].nunique(dropna=False) > 1)
        records.append(rec)
    out = pd.DataFrame(records)
    out["any_attribute_conflict"] = out[[f"conflict_{a}" for a in ATTRIBUTES_CHECKED_FOR_CONFLICTS]].any(axis=1)
    return out


def attach_canonical(clean: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Add canonical_* columns to every row (originals untouched)."""
    cols = ["song_key"] + [f"canonical_{a}" for a in ATTRIBUTES_CHECKED_FOR_CONFLICTS] + ["any_attribute_conflict"]
    return clean.merge(master[cols], on="song_key", how="left")
