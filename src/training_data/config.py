"""Central configuration: paths and athlete settings.

No logic here — just constants and simple loaders. Every other module imports
from this file so there's exactly one place to change a path.
"""

import tomllib                    # TOML reader, built into Python 3.11+
from datetime import date
from pathlib import Path

# __file__ is this file's path. .resolve() makes it absolute.
# .parents[2] goes up three levels: config.py -> training_data -> src -> repo root
REPO = Path(__file__).resolve().parents[2]

RAW = REPO / "raw"
ACTIVITIES = REPO / "activities"
STREAMS = REPO / "streams"
TABLES = REPO / "tables"
STATE_FILE = REPO / ".sync-state.json"
ATHLETE_FILE = REPO / "athlete.toml"

TOKENSTORE = Path.home() / ".garminconnect"

# How many days back to re-fetch wellness every run.
# Garmin revises history: sleep scores recalculate, VO2max backfills,
# training status lags a day. Re-fetching a window keeps us in sync.
WELLNESS_WINDOW_DAYS = 14

# Seconds to sleep between API calls. Garmin rate-limits aggressively.
RATE_LIMIT_SLEEP = 1.5


def load_athlete() -> dict:
    """Read athlete.toml into a dictionary.

    'rb' means read-binary, which tomllib requires.
    The `with` block auto-closes the file, like a try/finally.
    """
    with open(ATHLETE_FILE, "rb") as f:
        return tomllib.load(f)


def partition(root: Path, d: date) -> Path:
    """Return root/YYYY/MM/ and create it if needed.

    Partitioning matters: GitHub caps a single directory at 3,000 entries,
    and a flat activities/ folder hits that in about two years.

    f"{d:%Y}" formats the date as a 4-digit year, like strftime.
    """
    p = root / f"{d:%Y}" / f"{d:%m}"
    p.mkdir(parents=True, exist_ok=True)   # like mkdir -p
    return p
