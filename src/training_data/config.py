"""Central configuration: paths, constants, athlete settings, sport registry.

No logic beyond simple loaders — one place to change a path.
"""

import json
import tomllib
from datetime import date
from pathlib import Path

# config.py -> training_data -> src -> repo root
REPO = Path(__file__).resolve().parents[2]

RAW = REPO / "raw"
REFERENCE = RAW / "reference"          # taxonomy + zones, refreshed each run
ACTIVITIES = REPO / "activities"
STREAMS = REPO / "streams"
TABLES = REPO / "tables"
STATE_FILE = REPO / ".sync-state.json"
ATHLETE_FILE = REPO / "athlete.toml"

TOKENSTORE = Path.home() / ".garminconnect"

# Garmin revises history: sleep scores recalculate, VO2max backfills,
# training status lags. Re-fetch a rolling window every run.
WELLNESS_WINDOW_DAYS = 14

# Activity lookback. FIT downloads are guarded by .sync-state.json, so a wide
# window costs one list call, not N downloads.
ACTIVITY_LOOKBACK_DAYS = 45

RATE_LIMIT_SLEEP = 1.5          # seconds between API calls
ZONE_GAP_CAP_S = 10             # max seconds credited to one record (absorbs pauses)
CTL_DAYS, ATL_DAYS = 42, 7


def load_athlete() -> dict:
    """Read athlete.toml. 'rb' because tomllib wants bytes."""
    with open(ATHLETE_FILE, "rb") as f:
        return tomllib.load(f)


def load_reference(name: str) -> dict | list | None:
    """Read one file from raw/reference/, or None if fetch hasn't written it."""
    p = REFERENCE / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def partition(root: Path, d: date) -> Path:
    """Return root/YYYY/MM/, creating it. GitHub caps a directory at 3,000 entries."""
    p = root / f"{d:%Y}" / f"{d:%m}"
    p.mkdir(parents=True, exist_ok=True)
    return p
