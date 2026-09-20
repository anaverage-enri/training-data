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

# Sport families. Keys are Garmin's own parent types (see resolve_family).
# output_key = the field used for efficiency/decoupling, or None to skip.
FAMILIES: dict[str, dict] = {
    "running":           {"output_key": "power",          "training": True,  "sets": False, "lengths": False},
    "cycling":           {"output_key": "power",          "training": True,  "sets": False, "lengths": False},
    "swimming":          {"output_key": None,             "training": True,  "sets": False, "lengths": True},
    "racket_sports":     {"output_key": None,             "training": True,  "sets": False, "lengths": False},
    "fitness_equipment": {"output_key": None,             "training": True,  "sets": True,  "lengths": False},
    "walking":           {"output_key": "enhanced_speed", "training": False, "sets": False, "lengths": False},
    "hiking":            {"output_key": "enhanced_speed", "training": False, "sets": False, "lengths": False},
    "other":             {"output_key": None,             "training": False, "sets": False, "lengths": False},
}
# Garmin's taxonomy has 17 families; the 8 above are the ones counted towards training. Anything
# else (water_sports, team_sports, winter_sports...) falls back to DEFAULT_FAMILY
# and is therefore counted as NON-training. If taking up something new, add it here
# — validate.py fails the run until that, rather than quietly under-counting.
DEFAULT_FAMILY = FAMILIES["other"]


def load_athlete() -> dict:
    """Read athlete.toml. 'rb' because tomllib wants bytes."""
    with open(ATHLETE_FILE, "rb") as f:
        return tomllib.load(f)


def load_reference(name: str) -> dict | list | None:
    """Read one file from raw/reference/, or None if fetch hasn't written it."""
    p = REFERENCE / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def resolve_family(typekey: str) -> str:
    """Map a Connect typeKey to its top-level family.

    Garmin's taxonomy is a tree: treadmill_running -> running -> all.
    Walk up parentTypeId until the parent is the root, and return that node.
    All 17 cycling variants collapse to "cycling"
    """
    types = load_reference("activity_types") or []
    by_id = {t["typeId"]: t for t in types}
    by_key = {t["typeKey"]: t for t in types}

    node = by_key.get(typekey)
    seen: set[int] = set()
    while node and node["typeId"] not in seen:
        seen.add(node["typeId"])
        parent = by_id.get(node["parentTypeId"])
        if parent is None or parent["typeKey"] == "all":
            return node["typeKey"]
        node = parent
    return "other"                      # unknown key (e.g. tennis) -> other


def family_of(typekey: str) -> dict:
    """Capability flags for a typeKey. Never raises."""
    return FAMILIES.get(resolve_family(typekey), DEFAULT_FAMILY)


def partition(root: Path, d: date) -> Path:
    """Return root/YYYY/MM/, creating it. GitHub caps a directory at 3,000 entries."""
    p = root / f"{d:%Y}" / f"{d:%m}"
    p.mkdir(parents=True, exist_ok=True)
    return p
