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
