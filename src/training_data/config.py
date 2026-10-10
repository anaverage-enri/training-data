"""Central configuration: paths, constants, athlete settings, sport registry.

No logic beyond simple loaders — one place to change a path.
"""

from datetime import date
from pathlib import Path

# config.py -> training_data -> src -> repo root
REPO = Path(__file__).resolve().parents[2]

RAW = REPO / "raw"
ACTIVITIES = RAW / "activities"         # <stamp>-<id>.fit and <stamp>-<id>.json
WELLNESS = RAW / "wellness"             # one JSON per day
TABLES = REPO / "tables"

TOKENSTORE = Path.home() / ".garminconnect"

# Garmin revises history: sleep scores recalculate, VO2max backfills,
# training status lags. Re-fetch a rolling window every run.
WELLNESS_WINDOW_DAYS = 14

# Activity lookback. FIT downloads are guarded by .sync-state.json, so a wide
# window costs one list call, not N downloads.
ACTIVITY_LOOKBACK_DAYS = 45

RATE_LIMIT_SLEEP = 1.5          # seconds between API calls


def partition(root: Path, d: date) -> Path:
    """Return root/YYYY/MM/, creating it. GitHub caps a directory at 3,000 entries."""
    p = root / f"{d:%Y}" / f"{d:%m}"
    p.mkdir(parents=True, exist_ok=True)
    return p
