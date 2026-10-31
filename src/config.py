"""Project-wide constants and documented analytical thresholds.

All thresholds live here so the methodology document, the code and the tests
refer to one source of truth.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Atlantic_Spain.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
EXPORTS_DIR = PROJECT_ROOT / "outputs" / "exports"

EXPECTED_COLUMNS = [
    "date", "position", "song", "artist", "popularity", "duration_ms",
    "album_type", "total_tracks", "is_explicit", "album_cover_url",
]
DATE_FORMAT = "%d-%m-%Y"
PLAYLIST_SIZE = 50          # a complete daily snapshot has exactly these positions 1..50
TOP_N_PEAK = 10             # "Peak Phase" threshold: position <= 10

# Plausibility bounds (warnings, not deletions)
DURATION_MIN_MS = 30_000
DURATION_MAX_MS = 1_800_000
POPULARITY_MIN = 0
POPULARITY_MAX = 100

# Lifecycle classification thresholds (see docs/methodology.md)
NEW_ENTRY_WINDOW_DAYS = 7    # first appearance of current run within last 7 observed days
GROWTH_MIN_GAIN = 5          # positions gained over the recent window to call "Growth"
DECLINE_MIN_LOSS = 5         # positions lost over the recent window to call "Decline"
RECENT_WINDOW = 4            # number of most recent complete-snapshot appearances used
MIN_OBSERVATIONS = 4         # fewer appearances than this -> "Insufficient history"

ATTRIBUTES_CHECKED_FOR_CONFLICTS = ["album_type", "is_explicit", "duration_ms", "total_tracks"]
