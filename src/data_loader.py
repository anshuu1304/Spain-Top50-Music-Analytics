"""Load the raw Atlantic Spain CSV without altering its values."""
from pathlib import Path

import pandas as pd

from src.config import EXPECTED_COLUMNS, RAW_DATA_PATH


def normalise_header(name: str) -> str:
    """Strip whitespace and the escaped underscores present in the source header."""
    return name.replace("\\_", "_").strip()


def load_raw(path: Path | str = RAW_DATA_PATH) -> pd.DataFrame:
    """Read every field as text so no value is silently coerced on load.

    Adds `source_row` (1-based line number in the file, header = line 1) for traceability.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}. See README for how to place it.")
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    df.columns = [normalise_header(c) for c in df.columns]
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing expected columns: {missing}")
    df.insert(0, "source_row", range(2, len(df) + 2))
    return df
