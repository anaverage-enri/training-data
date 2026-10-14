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


def cadence(doc: dict) -> float | None:
    """Whichever cadence the sport has: steps, pedal revs or strokes per minute."""
    s = doc["summary"]
    for key in (
        "averageRunningCadenceInStepsPerMinute",
        "averageBikingCadenceInRevPerMinute",
        "averageSwimCadenceInStrokesPerMinute",
    ):
        if s.get(key) is not None:
            return round(s[key])
    return None


# column name -> where it comes from. Three forms:
#   "a.b.c"                 copy that field
#   ("a.b.c", convert)      copy it through a unit conversion
#   function                call it with the whole document
ACTIVITY_COLUMNS: dict[str, Any] = {
    "date":             ("summary.startTimeLocal", lambda t: t[:10]),
    "start":            ("summary.startTimeLocal", lambda t: t[11:16]),
    "activity_id":      "summary.activityId",
    "name":             "summary.activityName",
    "sport":            "summary.activityType.typeKey",
    # volume
    "duration_min":     ("summary.duration", minutes),
    "moving_min":       ("summary.movingDuration", minutes),
    "distance_km":      ("summary.distance", km),
    "elevation_m":      ("summary.elevationGain", round),
    "speed_kmh":        ("summary.averageSpeed", kmh),
    # intensity
    "avg_hr":           ("summary.averageHR", round),
    "max_hr":           ("summary.maxHR", round),
    "load":             ("summary.activityTrainingLoad", r1),
    "te_aerobic":       ("summary.aerobicTrainingEffect", r1),
    "te_anaerobic":     ("summary.anaerobicTrainingEffect", r1),
    "te_label":         "summary.trainingEffectLabel",
    "z0_min":           below_zone_1,
    "z1_min":           ("summary.hrTimeInZone_1", minutes),
    "z2_min":           ("summary.hrTimeInZone_2", minutes),
    "z3_min":           ("summary.hrTimeInZone_3", minutes),
    "z4_min":           ("summary.hrTimeInZone_4", minutes),
    "z5_min":           ("summary.hrTimeInZone_5", minutes),
    # power (running power on runs, a power meter on rides)
    "avg_power":        ("summary.avgPower", round),
    "norm_power":       ("summary.normPower", round),
    "max_power":        ("summary.maxPower", round),
    "tss":              ("summary.trainingStressScore", r1),
    "intensity_factor": ("summary.intensityFactor", r2),
    "max_20min_power":  ("summary.max20MinPower", round),
    # per sport
    "cadence":          cadence,
    "pool_m":           ("summary.poolLength", cm_to_m),
    "lengths":          "summary.activeLengths",
    "swolf":            ("summary.averageSwolf", round),
    "strokes_per_length": ("summary.avgStrokes", r1),
    "sets":             "summary.activeSets",
    "reps":             "summary.totalReps",
    # conditions at the start
    "weather_temp_c":   ("weather.temp", celsius),
    "weather_feels_c":  ("weather.apparentTemp", celsius),
    "humidity_pct":     "weather.relativeHumidity",
    # body and subjective
    "vo2max":           "summary.vO2MaxValue",
    "body_battery_change": "summary.differenceBodyBattery",
    "calories":         ("summary.calories", round),
    "rpe":              "detail.summaryDTO.directWorkoutRpe",
    "feel":             "detail.summaryDTO.directWorkoutFeel",
}


# ── daily ────────────────────────────────────────────────────────────────────

def primary(by_device: dict | None) -> dict:
    """Garmin keys training status by device id. Return the primary device's entry."""
    entries = [v for v in (by_device or {}).values() if isinstance(v, dict)]
    for entry in entries:
        if entry.get("primaryTrainingDevice"):
            return entry
    return entries[0] if entries else {}


def wake_readiness(snapshots: list | None) -> dict:
    """The earliest AFTER_WAKEUP_RESET snapshot: the score you woke up with.

    Garmin returns several snapshots a day, newest first, and the score moves
    a lot. A day can even hold two wake-up entries: on 2026-10-04 there is one
    at 04:05 (52, before the run) and another at 07:35 (32, after it). The
    earliest is the one that means "morning readiness".

    Falls back to the earliest snapshot of any kind if the watch never logged
    a wake-up that day.
    """
    snapshots = snapshots or []
    wake = [s for s in snapshots if s.get("inputContext") == "AFTER_WAKEUP_RESET"]
    pool = wake or snapshots
    if not pool:
        return {}
    return min(pool, key=lambda s: s.get("timestampLocal") or "")


def prepare_day(doc: dict) -> dict:
    """Add three shortcut keys so DAILY_COLUMNS can stay plain dotted paths."""
    status = doc.get("training_status") or {}
    doc["status"] = primary(pick(status, "mostRecentTrainingStatus.latestTrainingStatusData"))
    doc["balance"] = primary(
        pick(status, "mostRecentTrainingLoadBalance.metricsTrainingLoadBalanceDTOMap")
    )
    doc["readiness"] = wake_readiness(doc.get("training_readiness"))
    return doc
