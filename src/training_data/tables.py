from typing import Any


def pick(doc: Any, path: str) -> Any:
    """Follow a dotted path through nested dicts: pick(d, "a.b.c") is d["a"]["b"]["c"].

    Returns None the moment anything is missing, instead of raising.
    """
    for key in path.split("."):
        if not isinstance(doc, dict):
            return None
        doc = doc.get(key)
    return doc


# Unit conversions: Garmin's unit in, the table's unit out.
def minutes(seconds): return round(seconds / 60, 1)
def hours(seconds): return round(seconds / 3600, 2)
def min_to_hours(mins): return round(mins / 60, 1)
def km(metres): return round(metres / 1000, 2)
def kmh(metres_per_second): return round(metres_per_second * 3.6, 1)
def cm_to_m(centimetres): return round(centimetres / 100, 1)
def kg(grams): return round(grams / 1000, 1)
def celsius(fahrenheit): return round((fahrenheit - 32) * 5 / 9, 1)
def r1(x): return round(x, 1)
def r2(x): return round(x, 2)


def clock(seconds: float) -> str:
    """7998 -> '2:13:18'."""
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


# ── activities ───────────────────────────────────────────────────────────────

def below_zone_1(doc: dict) -> float | None:
    """Minutes spent below zone 1.

    Connect's hrTimeInZone_1..5 leave this out, so the five zones do not add
    up to the session: it is 44% of a badminton session and most of a strength
    one. This is the single derived column in the table — duration minus the
    five zones — and it agrees with the FIT's own below-Z1 bucket to within a
    few seconds.
    """
    s = doc["summary"]
    zones = [s.get(f"hrTimeInZone_{i}") for i in range(1, 6)]
    if s.get("duration") is None or None in zones:
        return None
    return minutes(max(0.0, s["duration"] - sum(zones)))
