"""Field-level validation rules. Each rule returns a boolean mask of INVALID values.

Nothing here deletes data: callers decide whether an invalid row is quarantined.
"""
import pandas as pd

from src.config import (
    DATE_FORMAT, DURATION_MAX_MS, DURATION_MIN_MS, PLAYLIST_SIZE,
    POPULARITY_MAX, POPULARITY_MIN,
)

_BOOL_MAP = {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}


def parse_dates(s: pd.Series) -> pd.Series:
    """Parse dd-mm-yyyy and yyyy-mm-dd dates; invalid values become NaT."""
    values = s.str.strip()

    dates = pd.to_datetime(values, format=DATE_FORMAT, errors="coerce")

    iso_mask = dates.isna()
    dates.loc[iso_mask] = pd.to_datetime(
        values.loc[iso_mask],
        format="%Y-%m-%d",
        errors="coerce",
    )

    return dates


def parse_bool(s: pd.Series) -> pd.Series:
    """Normalise TRUE/FALSE-style text to a nullable boolean. Unknown values become <NA>."""
    return s.str.strip().str.lower().map(_BOOL_MAP).astype("boolean")


def to_int(s: pd.Series) -> pd.Series:
    """Numeric conversion; non-numeric text becomes <NA>."""
    return pd.to_numeric(s.str.strip(), errors="coerce").astype("Int64")


def invalid_rank(position: pd.Series) -> pd.Series:
    return position.isna() | (position < 1) | (position > PLAYLIST_SIZE) | (position % 1 != 0)


def invalid_popularity(pop: pd.Series) -> pd.Series:
    return pop.isna() | (pop < POPULARITY_MIN) | (pop > POPULARITY_MAX)


def implausible_duration(dur: pd.Series) -> pd.Series:
    """Warning-level: outside [30 s, 30 min] or non-numeric."""
    return dur.isna() | (dur < DURATION_MIN_MS) | (dur > DURATION_MAX_MS)


def invalid_total_tracks(tt: pd.Series) -> pd.Series:
    return tt.isna() | (tt < 1)


def snapshot_completeness(positions_by_date: pd.DataFrame) -> pd.DataFrame:
    """Given rows with columns [date, position], report per-date completeness.

    A snapshot is COMPLETE only if it has exactly PLAYLIST_SIZE rows AND the positions
    are exactly 1..PLAYLIST_SIZE with no duplicates.
    """
    g = positions_by_date.groupby("date")["position"]
    out = pd.DataFrame({
        "n_rows": g.size(),
        "n_distinct_positions": g.nunique(),
        "min_position": g.min(),
        "max_position": g.max(),
    })
    out["missing_positions"] = PLAYLIST_SIZE - out["n_distinct_positions"]
    out["complete"] = (out["n_rows"] == PLAYLIST_SIZE) & (out["n_distinct_positions"] == PLAYLIST_SIZE)
    return out.reset_index()
