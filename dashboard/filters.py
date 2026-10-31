"""Pure pandas filter logic used by the dashboard (testable without Streamlit)."""
from dataclasses import dataclass, field

import pandas as pd

STAGES = ["New Entry", "Growth Phase", "Peak Phase", "Mature Phase", "Decline Phase",
          "Insufficient history", "Exited"]


@dataclass
class Filters:
    date_start: pd.Timestamp | None = None
    date_end: pd.Timestamp | None = None
    stages: list = field(default_factory=lambda: list(STAGES))
    explicit: str = "All"          # All | Explicit | Clean
    album_type: str = "All"        # All | album | single
    artist_query: str = ""
    song_query: str = ""


def apply_song_filters(lc: pd.DataFrame, f: Filters) -> pd.DataFrame:
    """Filter the song-level lifecycle table. Date filter keeps songs whose observed span overlaps the range."""
    out = lc.copy()
    if f.date_start is not None and f.date_end is not None:
        if f.date_start > f.date_end:
            raise ValueError("Start date is after end date.")
        out = out[(out["last_seen"] >= f.date_start) & (out["first_seen"] <= f.date_end)]
    if f.stages is not None:
        out = out[out["lifecycle_stage"].isin(f.stages)]
    if f.explicit != "All" and "is_explicit" in out.columns:
        out = out[out["is_explicit"] == (f.explicit == "Explicit")]
    if f.album_type != "All" and "album_type" in out.columns:
        out = out[out["album_type"] == f.album_type]
    if f.artist_query.strip():
        out = out[out["artist"].str.contains(f.artist_query.strip(), case=False, regex=False)]
    if f.song_query.strip():
        out = out[out["song"].str.contains(f.song_query.strip(), case=False, regex=False)]
    return out


def apply_daily_filters(daily: pd.DataFrame, f: Filters) -> pd.DataFrame:
    out = daily.copy()
    if f.date_start is not None and f.date_end is not None:
        out = out[(out["date"] >= f.date_start) & (out["date"] <= f.date_end)]
    return out


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")
