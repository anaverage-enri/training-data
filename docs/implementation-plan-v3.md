# `training-data` — Implementation Plan v3

A private repo that pulls everything off Garmin Connect, decodes it, and rolls it into
tables Claude can read — so coaching conversations start from your actual data.

**Written to be implemented by hand, in order.** Every module is given complete. Read the
"why" above each one, type or paste it, run the check, then move on. Nothing later depends
on you having understood something earlier by osmosis.

---

## Part 1 — What you're building

```
  ┌────────────────────────────────────────────────────────────────┐
  │ 1. FETCH    Garmin Connect  →  raw/       (.fit + .json)       │
  │ 2. DECODE   raw/*.fit       →  activities/ + streams/          │
  │ 3. METRICS  pure math, no files                                │
  │ 4. ROLLUP   everything      →  tables/*.csv                    │
  │ 5. VALIDATE assert nothing is silently empty; exit 1 if it is  │
  │ 6. COMMIT   git add / commit / push                            │
  └────────────────────────────────────────────────────────────────┘
                                ↓
                        Claude reads tables/
```

Six stages, six files, run in sequence once a day by `launchd`. They are separate so a
failure in stage 4 doesn't cost you a re-download of stage 1.

### The four tables you end up with

| table | grain | what it answers |
|---|---|---|
| `tables/daily-YYYY.csv` | one row per calendar day | "What did I do, and how fresh was I?" **Canonical.** Holds load, hours, CTL/ATL/form, and the headline wellness columns. |
| `tables/weekly-YYYY.csv` | one row per ISO week | "Am I building or digging a hole?" A roll-up of `daily`. |
| `tables/activities-YYYY.csv` | one row per session | "What happened in that session?" |
| `tables/wellness-YYYY.csv` | one row per day | Health **detail** only — sleep stages, SpO2, stress, body-battery, HRV baseline, readiness factors. Columns that are in `daily` are *not* repeated here. |

`daily` is the one to reach for first. A rest day is a row there with `load = 0`, which
matters more than it sounds — see Decision 6.

---

## Part 2 — Your data, measured

Pulled 2026-08-01 → 2026-09-19: **71 activities across 9 sports**, 50 days of wellness.

| sport (`typeKey`) | n | load | hours | load/hour |
|---|---:|---:|---:|---:|
| `running` | 21 | 2609 | 23.5 | 111 |
| `badminton` | 11 | 1980 | 25.0 | 79 |
| `strength_training` | 15 | 151 | 4.6 | 33 |
| `lap_swimming` | 3 | 110 | 3.8 | 29 |
| `walking` | 14 | 88 | 5.0 | 18 |
| `treadmill_running` | 1 | 80 | 0.7 | 114 |
| `hiking` | 2 | 21 | 1.3 | 16 |
| `open_water_swimming` | 1 | 4 | 0.5 | 8 |
| `breathwork` | 3 | 0 | 0.3 | 0 |
| **total** | **71** | **5042** | **64.7** | |

Read the `load/hour` column before you decide what counts as training. Walking is 7.7% of
your hours and 1.7% of your load.

### Three facts that determine the code

**1. Records are not 1 Hz.** Your watch uses smart recording, so sample spacing varies by
sport. Measured median gap between records:

| sport | records | timer (s) | median Δt | effective Hz |
|---|---:|---:|---:|---:|
| running, treadmill, swimming, breathwork | — | — | 1.0 s | 1.00 |
| `strength_training` | 1170 | 2233 | 1.0 s | 0.52 |
| `walking`, `hiking` | 677 / 902 | 2318 / 3131 | 3.0 s | 0.29 |
| **`badminton`** | 3037 | 11805 | **4.0 s** | **0.26** |

Anything that counts records as if they were seconds reports a 3h17m badminton session as
49 minutes. Every time-based metric must weight by the gap to the next record.

**2. Field names are not what you'd guess.** No record stream anywhere has `speed` or
`altitude` — they are `enhanced_speed` and `enhanced_altitude`. Per-sport availability:

| sport | what the records actually carry |
|---|---|
| `running`, `treadmill_running` | full set incl. native **running power** + HRM-600 dynamics |
| `badminton` | HR, `enhanced_speed`, respiration. No power. |
| `lap_swimming` | **only `timestamp` + `heart_rate`** — distance/pace live in `length_mesgs` |
| `strength_training` | timestamp, distance, HR, temperature + **`set_mesgs`** (reps/weight) |
| `walking`, `hiking` | `enhanced_speed`, `enhanced_altitude`, HR. No power. |

**3. Garmin already computed a lot of it.** Every FIT carries `time_in_zone_mesgs` (the
watch's own zone boundaries and totals) and `training_load_peak`, which equals Connect's
`activityTrainingLoad`. Two rules, both verified:

- Take the entry where **`reference_mesg == 'session'`**. Files also carry one entry per
  lap — your long run has 30 of them — so `[0]` is not safe.
- `time_in_hr_zone` has **seven** buckets: `[below-Z1, Z1…Z5, above-Z5]`. Connect's
  `hrTimeInZone_1..5` is only the middle five, and the missing below-Z1 bucket is large:
  it is 100% of a strength session, 82% of a walk, 35% of badminton. Use the FIT's seven.

### Wellness: what's present, over all 50 days

| source | field | present |
|---|---|---:|
| `get_rhr_daily` (1 call) | `value` | 50/50 |
| `get_hrv_data_range` (1 call) | `lastNightAvg`, `status`, `weeklyAvg` | 49/50 |
| `get_sleep_daily` (1 call) | `totalSleepTimeInSeconds`, stages, SpO2, `sleepScoreQuality` | 47/50 |
| `get_max_metrics_range` (1 call) | `vo2MaxPreciseValue` | **21/50 — sparse, forward-fill** |
| `get_race_predictions(_type='daily')` (1 call) | 5K/10K/HM/marathon | 50/50 |
| `get_stats` (per day) | `restingHeartRate`, `totalSteps`, stress, body battery | 50/50 |
| `get_training_readiness` (per day) | `score`, `acuteLoad`, `recoveryTime` | 50/50 |
| `get_training_status` (per day) | `trainingStatus`, `vo2Max`, load balance | 50/50 |
| — | `weeklyTrainingLoad` | **0/50 — always null, don't use it** |

Those five range endpoints replace 250 per-day calls with five. Only four endpoints still
need a per-day loop.

**Training status over the window:** `UNPRODUCTIVE_3` ×31, `MAINTAINING_2` ×7,
`PRODUCTIVE_2` ×4, `RECOVERY_2` ×4, `MAINTAINING_3` ×3, `MAINTAINING_4` ×1.

**Race predictions are drifting the wrong way** — half marathon, your A-race on 18 Oct:

```
2026-08-01  2:05:35        2026-08-22  2:13:00        2026-09-12  2:11:37
2026-08-08  2:09:36        2026-08-29  2:12:48        2026-09-19  2:14:22
2026-08-15  2:10:19        2026-09-05  2:11:15        → +8.8 min over 7 weeks
```

### Your configured zones

`get_heart_rate_zones()` returns one entry per sport profile. You have **two**:

| profile | method | rest | max | LTHR | zone floors |
|---|---|---:|---:|---:|---|
| `DEFAULT` | HR_RESERVE | 50 | 201 | **179** | 126 / 141 / 156 / 171 / 186 |
| `RUNNING` | HR_RESERVE | 50 | 201 | **194** | 126 / 141 / 156 / 171 / 186 |

There is no `CYCLING` profile yet, so cycling will fall back to `DEFAULT` — see Part 7.

`get_power_zones_for_sport("CYCLING")` already returns 7 zones at **FTP 200 W**, but
`get_cycling_ftp()` is all-nulls: that 200 is a default, not a test result.

---

## Part 3 — Prior art

| project | what it does | what we took |
|---|---|---|
| [GarminDB](https://github.com/tcgoetz/GarminDB) | Downloads to SQLite, Jupyter analysis | **Keep raw downloads forever** so the derived layer can be rebuilt without re-downloading. Also its daily/weekly/monthly/yearly summary grain — we do daily + weekly. |
| [intervals.icu](https://forum.intervals.icu/t/hrss-normalized-trimp-training-load/569) | Training analysis platform | **HRSS (normalised TRIMP)** as the load metric for sports with HR but no power. Its naming too: CTL = Fitness, ATL = Fatigue, TSB = Form. |
| [garmin-grafana](https://github.com/arpanghosh8453/garmin-grafana) | Dockerised Garmin → InfluxDB → Grafana | Confirms the fetch/store split. We deliberately **don't** use a time-series DB: Claude reads text from git, and CSV diffs. |
| [Garmin FIT Python SDK](https://github.com/garmin/fit-python-sdk) | Official decoder | The decoder itself, and confirmation that smart recording produces variable sample rates. |

We differ from all of them in one way: the output is **text in git**, sized for a language
model to read, not a database for a dashboard to query.

---

## Part 4 — Design decisions

**1. The canonical sport key is Connect's `activityType.typeKey`,** and the behaviour key
is its **family**, resolved from Garmin's own taxonomy. `get_activity_types()` returns 154
types with a `parentTypeId` chain. Walking up that chain until the parent is `all` gives 17
families. Verified:

```
running, treadmill_running, trail_running, track_running   → running
cycling, indoor_cycling, virtual_ride, road_biking,
  gravel_cycling, mountain_biking  (17 variants)           → cycling
lap_swimming, open_water_swimming                          → swimming
badminton, pickleball                                      → racket_sports
strength_training, indoor_rowing, yoga, elliptical         → fitness_equipment
breathwork                                                 → other
```

This is why October needs no code change: whichever of the 17 cycling keys your watch
emits, it lands in the `cycling` family. Unknown keys fall back to `other`.

**2. Garmin's `activityTrainingLoad` is the load currency,** because it is the only number
that prices badminton against running on one scale and is present for every sport.

**3. We compute a second opinion, and treat it as a check, not a replacement.** HRSS
(normalised TRIMP: 1 hour at LTHR = 100) for everything with HR; TSS for anything with
power. Measured against Garmin's load on 69 activities: **r = 0.89**. Weighting per-record
rather than using average HR lifts it to **r = 0.96** on the 8 sessions tested. But the
*ratio* differs systematically by sport (treadmill 0.35, badminton 0.40, strength 1.65), so
HRSS is **not** interchangeable with Garmin's number. Use it to (a) fill in if Garmin's
field is ever missing, and (b) detect drift — if a sport's ratio moves over time, something
changed.

**4. Zone boundaries come from the watch, per activity,** read from each FIT's
`time_in_zone_mesgs`. They then agree with Garmin's own totals by construction. Δt-weighted
time-in-zone reproduces `total_timer_time` to **100.0–103.5%** across all nine sports.

**5. Two namespaces, never mixed.** `garmin_*` columns come from Garmin; `computed_*` are
ours, over the *same seven buckets*. They may disagree — that's the point — but only if
both count the same thing.

**6. CTL/ATL are daily, zero-filled, explicitly seeded.** This is the subtlest thing here.
Over your 50-day window, the same loads give wildly different answers depending on
initialisation:

| method | CTL | note |
|---|---:|---|
| `ewm(alpha=1/42, adjust=False)` | **168.1** | seeds from day 1, which was a 328-load day. Wrong. |
| loop from zero | 67.8 | 42-day ramp; understates for the first 6 weeks |
| loop seeded with mean daily load | **98.7** | closest to the window's mean daily load of 100.8 |
| loop seeded with Garmin `acuteLoad`/7 | 94.3 | also defensible |

We use the explicit loop, seed both CTL and ATL with the mean daily load of the first 7
days, and emit a `ctl_warmup` boolean for rows inside the first 42 days. Once you backfill
years of history the seed stops mattering — but today it is a 45% swing, so it gets a
column rather than a silent default.

**Form convention:** form is reported as the value *before* the day's load is absorbed,
i.e. the freshness you woke up with. (TrainingPeaks does it this way; intervals.icu uses
the post-absorption value. Either is fine; mixing them is not.)

**7. Readiness: take the earliest `AFTER_WAKEUP_RESET` snapshot.** Garmin returns 2–8
snapshots a day, newest first, and the score moves a lot during the day (on 2026-09-01:
51 at 04:30, 35 at 13:05, 23 after training). The morning reading is the one that means
something.

**8. Strip location and identity from `raw/*.meta.json` before writing.** Connect's activity
metadata includes `startLatitude`/`startLongitude` (your home, to 7 decimal places),
`ownerFullName`, `ownerId` and profile-image URLs. The repo is private, but there is no
reason for a GPS trace of your front door to be in a text file. The FIT keeps it; the
committed JSON doesn't.

---

## Part 5 — Build it

Prerequisites: `uv` installed, `bin/login.py` already run once, `garminconnect==0.3.15`
pinned. Each step ends with something you can run.

### Step 1 — `src/training_data/config.py`

Paths, tuning constants, and the sport registry. Everything else imports from here.

```python
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
# Garmin's taxonomy has 17 families; the 8 above are the ones you do. Anything
# else (water_sports, team_sports, winter_sports...) falls back to DEFAULT_FAMILY
# and is therefore counted as NON-training. If you take up kayaking, add it here
# — validate.py fails the run until you do, rather than quietly under-counting.
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
    All 17 cycling variants collapse to "cycling", which is why adding cycling
    in October needs no code change.
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
```

**Check it:** `uv run python -c "from training_data.config import FAMILIES; print(len(FAMILIES))"` → `8`.
(`resolve_family` needs `raw/reference/` from Step 3; it returns `"other"` until then.)

### Step 2 — `src/training_data/metrics.py`

Pure functions: numbers in, numbers out, no files. That makes them testable, and you should
test them, because these produce the numbers you'll train by.

```python
"""Training-load and efficiency maths. Pure functions, no I/O."""

import math

# Banister TRIMP exponent: 1.92 for men, 1.67 for women.
# Garmin's profile endpoint returns null for gender, so it lives in athlete.toml.
TRIMP_K_MALE = 1.92


def zone_bounds_from_fit(messages: dict) -> tuple[list[int], list[float]] | None:
    """Return (zone floors, Garmin's own 7 time-in-zone buckets) from a FIT.

    Uses the entry whose reference_mesg is 'session' — files also carry one
    entry per lap, so index [0] is not safe.

    Floors look like [126, 141, 156, 171, 186, 201]. With 6 floors there are 7
    buckets: below Z1, Z1..Z5, and above max.
    """
    entries = [
        m for m in messages.get("time_in_zone_mesgs", [])
        if m.get("reference_mesg") == "session"
    ]
    if not entries:
        return None
    e = entries[0]
    floors = e.get("hr_zone_high_boundary")
    buckets = e.get("time_in_hr_zone")
    if not floors or not buckets:
        return None
    return list(floors), [float(x) for x in buckets]


def zone_index(hr: float, floors: list[int]) -> int:
    """Bucket index for a heart rate: 0 = below Z1, 6 = above max."""
    i = 0
    while i < len(floors) and hr >= floors[i]:
        i += 1
    return i


def time_in_zones(records: list[dict], floors: list[int], cap_s: int = 10) -> list[float]:
    """Seconds per HR zone, weighted by how long each record actually covers.

    Records are NOT evenly spaced — badminton samples every ~4 s — so counting
    records would report a 3h17m session as 49 minutes. Each record is credited
    with the gap to the next one, capped at cap_s so a long auto-pause doesn't
    get counted as training.

    Returns 7 buckets. The total lands within a few percent of
    session.total_timer_time; validate.py asserts that.
    """
    usable = [r for r in records if r.get("timestamp") and r.get("heart_rate") is not None]
    buckets = [0.0] * (len(floors) + 1)

    for i, r in enumerate(usable):
        if i + 1 < len(usable):
            gap = (usable[i + 1]["timestamp"] - r["timestamp"]).total_seconds()
            dt = min(gap, cap_s)
        else:
            dt = 1.0
        buckets[zone_index(r["heart_rate"], floors)] += dt

    return [round(b, 1) for b in buckets]


def decoupling(records: list[dict], output_key: str | None) -> float | None:
    """Percent drift in output-per-heartbeat, first half vs second half.

    Above ~5% at a steady aerobic effort means durability is the limiter rather
    than fitness. output_key comes from the sport family: "power" for run/bike,
    "enhanced_speed" for walk/hike, None for sports where it's meaningless
    (badminton is stop-start; swimming records carry no speed at all).

    Note `is not None` rather than a truthiness test: a power of 0.0 is a real
    reading, and dropping zeros biases the two halves against each other.
    """
    if output_key is None:
        return None

    usable = [
        r for r in records
        if r.get("heart_rate") is not None and r.get(output_key) is not None
    ]
    if len(usable) < 600:               # under ~10 min of data, not meaningful
        return None

    mid = len(usable) // 2

    def ef(chunk: list[dict]) -> float | None:
        hr = sum(r["heart_rate"] for r in chunk) / len(chunk)
        out = sum(r[output_key] for r in chunk) / len(chunk)
        return out / hr if hr else None

    first, second = ef(usable[:mid]), ef(usable[mid:])
    if not first or second is None:
        return None
    return round((first - second) / first * 100, 2)


def trimp_per_min(hr: float, rest: int, hr_max: int, k: float = TRIMP_K_MALE) -> float:
    """Banister TRIMP for one minute at a given heart rate."""
    hrr = (hr - rest) / (hr_max - rest)
    hrr = max(0.0, min(1.0, hrr))               # clamp: HR can dip below rest
    return hrr * 0.64 * math.exp(k * hrr)


def hrss(records: list[dict], rest: int, hr_max: int, lthr: int,
         cap_s: int = 10, k: float = TRIMP_K_MALE) -> float | None:
    """Heart Rate Stress Score: normalised TRIMP where 1 h at LTHR = 100.

    Computed per record and Δt-weighted, so interval sessions aren't flattened
    the way a single average HR flattens them.

    Correlates with Garmin's activityTrainingLoad at r≈0.96, but the ratio
    differs by sport — treat this as a trend check and a fallback, not as a
    drop-in replacement for Garmin's number.
    """
    usable = [r for r in records if r.get("timestamp") and r.get("heart_rate") is not None]
    if not usable:
        return None

    reference = trimp_per_min(lthr, rest, hr_max, k) * 60      # 1 hour at LTHR
    if reference <= 0:
        return None

    total = 0.0
    for i, r in enumerate(usable):
        if i + 1 < len(usable):
            dt = min((usable[i + 1]["timestamp"] - r["timestamp"]).total_seconds(), cap_s)
        else:
            dt = 1.0
        total += trimp_per_min(r["heart_rate"], rest, hr_max, k) * (dt / 60)

    return round(total / reference * 100, 1)


def tss(normalized_power: float | None, ftp: int | None, duration_s: float | None) -> float | None:
    """Training Stress Score from power. 1 hour at FTP = 100."""
    if not normalized_power or not ftp or not duration_s:
        return None
    intensity = normalized_power / ftp
    return round(duration_s * normalized_power * intensity / (ftp * 3600) * 100, 1)


def load_series(daily_load: list[float], ctl_days: int = 42, atl_days: int = 7,
                seed: float = 0.0) -> list[tuple[float, float, float]]:
    """Fitness (CTL), fatigue (ATL) and form for each day.

    `daily_load` must be DENSE and zero-filled — one entry per calendar day,
    rest days included as 0.0. The decay constants are per day, so feeding it
    weekly rows silently stretches a 6-week window into 10 months.

    Form is recorded BEFORE the day's load is absorbed: the freshness you woke
    up with.

    Do not replace this with pandas' .ewm(adjust=False) — that seeds the series
    with the first value, and on a short window one big opening day dominates
    the result (measured: 168 vs 70 on the same 50 days).
    """
    ctl = atl = float(seed)
    out = []
    for load in daily_load:
        out.append((round(ctl, 1), round(atl, 1), round(ctl - atl, 1)))
        ctl += (load - ctl) / ctl_days
        atl += (load - atl) / atl_days
    return out
```

**Check it:**

```bash
uv run python -c "
from training_data.metrics import load_series, trimp_per_min
print('30 days of 100:', load_series([100]*30)[-1])   # ~(51.5, 99.0, -48.6)
print('1h at LTHR    :', round(trimp_per_min(194,50,201)*60,1))
"
```

Day 30 should show ATL near 100, CTL well below it, and negative form — sustained training
makes you tired before it makes you fit.

### Step 3 — `src/training_data/fetch.py`

Three jobs: reference data, activities, wellness. The reference pull is new and it's what
makes the sport registry and zone handling work without hardcoding.

```python
"""Download from Garmin Connect into raw/.

Run with:  uv run python -m training_data.fetch
"""

import json
import time
import zipfile
from datetime import date, timedelta
from io import BytesIO

from garminconnect import Garmin

from training_data.config import (
    ACTIVITY_LOOKBACK_DAYS,
    RATE_LIMIT_SLEEP,
    RAW,
    REFERENCE,
    STATE_FILE,
    WELLNESS_WINDOW_DAYS,
    partition,
)
from training_data.garmin import client, with_retry

# Connect's activity metadata carries your home coordinates and your name.
# The FIT archive keeps them; the committed JSON should not.
PII_KEYS = {
    "startLatitude", "startLongitude", "endLatitude", "endLongitude",
    "ownerId", "ownerDisplayName", "ownerFullName",
    "ownerProfileImageUrlSmall", "ownerProfileImageUrlMedium",
    "ownerProfileImageUrlLarge",
}


def scrub(activity: dict) -> dict:
    """Drop location and identity fields before writing to disk."""
    return {k: v for k, v in activity.items() if k not in PII_KEYS}


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"activity_ids": [], "last_sync": None}


def save_state(state: dict) -> None:
    state["last_sync"] = date.today().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_reference(c: Garmin) -> int:
    """Taxonomy, zones and thresholds. Cheap, and everything downstream reads it.

    activity_types is the 154-entry tree that resolve_family() walks.
    hr_zones has one entry per sport profile you've configured.
    """
    REFERENCE.mkdir(parents=True, exist_ok=True)
    calls = {
        "activity_types": lambda: c.get_activity_types(),
        "hr_zones": lambda: c.get_heart_rate_zones(),
        "power_zones_running": lambda: c.get_power_zones_for_sport("RUNNING"),
        "power_zones_cycling": lambda: c.get_power_zones_for_sport("CYCLING"),
        "cycling_ftp": lambda: c.get_cycling_ftp(),
        "lactate_threshold": lambda: c.get_lactate_threshold(latest=True),
    }
    written = 0
    for name, fn in calls.items():
        try:
            (REFERENCE / f"{name}.json").write_text(
                json.dumps(with_retry(fn, label=name), indent=2, default=str)
            )
            written += 1
        except Exception as e:                 # a missing profile is not fatal
            print(f"  ! reference {name}: {type(e).__name__}: {e}")
        time.sleep(RATE_LIMIT_SLEEP)
    return written


def fetch_activities(c: Garmin, state: dict, since: date) -> int:
    """Download FITs for activities we don't have. Metadata refreshes every run."""
    known = set(state["activity_ids"])
    new_count = 0

    activities = with_retry(
        lambda: c.get_activities_by_date(since.isoformat(), date.today().isoformat()),
        label="list activities",
    )

    for act in activities:
        aid = str(act["activityId"])
        start = date.fromisoformat(act["startTimeLocal"][:10])
        stamp = act["startTimeLocal"].replace("-", "").replace(":", "").replace(" ", "-")
        base = f"{stamp}-{aid}"
        out_dir = partition(RAW / "activities", start)

        # Refresh metadata every run — you rename sessions and fix sport types later.
        (out_dir / f"{base}.meta.json").write_text(json.dumps(scrub(act), indent=2))

        if aid in known:
            continue

        print(f"  ↓ {base}  ({act.get('activityName', 'untitled')})")
        blob = with_retry(
            lambda: c.download_activity(aid, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL),
            label=f"download {aid}",
        )
        # ORIGINAL is a ZIP, not a bare .fit.
        with zipfile.ZipFile(BytesIO(blob)) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".fit"))
            (out_dir / f"{base}.fit").write_bytes(z.read(name))

        state["activity_ids"].append(aid)
        new_count += 1
        time.sleep(RATE_LIMIT_SLEEP)

    return new_count


def fetch_wellness_ranges(c: Garmin, start: date, end: date) -> int:
    """Five endpoints that each cover the whole window in ONE call.

    This replaces 5 calls/day with 5 calls total. get_sleep_daily chunks itself
    at 28 days internally.
    """
    RANGE_DIR = RAW / "wellness-range"
    RANGE_DIR.mkdir(parents=True, exist_ok=True)
    s, e = start.isoformat(), end.isoformat()
    calls = {
        "rhr": lambda: c.get_rhr_daily(s, e),
        "hrv": lambda: c.get_hrv_data_range(s, e),
        "sleep": lambda: c.get_sleep_daily(s, e),
        "max_metrics": lambda: c.get_max_metrics_range(s, e),
        "race_predictions": lambda: c.get_race_predictions(
            startdate=s, enddate=e, _type="daily"
        ),
    }
    written = 0
    for name, fn in calls.items():
        try:
            (RANGE_DIR / f"{name}-{s}-{e}.json").write_text(
                json.dumps(with_retry(fn, label=name), indent=2, default=str)
            )
            written += 1
        except Exception as ex:
            print(f"  ! range {name}: {type(ex).__name__}: {ex}")
        time.sleep(RATE_LIMIT_SLEEP)
    return written


def fetch_wellness_daily(c: Garmin, days: int = WELLNESS_WINDOW_DAYS) -> int:
    """The four endpoints with no range variant. One file per day."""
    written = 0
    for offset in range(days):
        d = date.today() - timedelta(days=offset)
        iso = d.isoformat()
        print(f"  ↓ {iso}")
        payload = {
            "date": iso,
            "stats": with_retry(lambda: c.get_stats(iso), label=f"stats {iso}"),
            "body_battery": with_retry(
                lambda: c.get_body_battery(iso, iso), label=f"body battery {iso}"
            ),
            "training_readiness": with_retry(
                lambda: c.get_training_readiness(iso), label=f"readiness {iso}"
            ),
            "training_status": with_retry(
                lambda: c.get_training_status(iso), label=f"status {iso}"
            ),
        }
        out = partition(RAW / "wellness", d)
        (out / f"{iso}.json").write_text(json.dumps(payload, indent=2))
        written += 1
        time.sleep(RATE_LIMIT_SLEEP)
    return written


def main() -> None:
    c = client()
    state = load_state()
    today = date.today()

    # -1 because get_activities_by_date is inclusive at both ends.
    since = today - timedelta(days=ACTIVITY_LOOKBACK_DAYS - 1)
    first_well = today - timedelta(days=WELLNESS_WINDOW_DAYS - 1)

    print("Reference:")
    n_ref = fetch_reference(c)

    print(f"Activities: {since} → {today}")
    n_act = fetch_activities(c, state, since)

    print(f"Wellness (ranges): {first_well} → {today}")
    n_rng = fetch_wellness_ranges(c, first_well, today)

    print(f"Wellness (daily):  {first_well} → {today}")
    n_day = fetch_wellness_daily(c)

    save_state(state)
    print(f"✓ {n_ref} reference, {n_act} new activities, "
          f"{n_rng} range files, {n_day} wellness days")


if __name__ == "__main__":
    main()
```

**Check it:**

```bash
uv run python -m training_data.fetch
ls raw/reference/                       # 6 json files
uv run python -c "
from training_data.config import resolve_family
for k in ['treadmill_running','badminton','indoor_cycling','virtual_ride','tennis']:
    print(f'{k:20s} -> {resolve_family(k)}')"
```

Expect `running`, `racket_sports`, `cycling`, `cycling`, `other`.

### Step 4 — Backfill August and September

Before writing the decoder, get multi-sport data on disk. With
`ACTIVITY_LOOKBACK_DAYS = 45` a normal run already reaches back to early August. For a
wider pull, run once with an explicit range:

```bash
uv run python -c "
from datetime import date
from training_data.fetch import fetch_activities, load_state, save_state
from training_data.garmin import client
s = load_state()
n = fetch_activities(client(), s, date(2026, 8, 1))
save_state(s); print(n, 'new')"
```

~70 downloads at 1.5 s ≈ 2 minutes. Confirm you have nine sports:

```bash
uv run python -c "
import json, glob, collections
c = collections.Counter(
    json.load(open(p))['activityType']['typeKey']
    for p in glob.glob('raw/activities/**/*.meta.json', recursive=True))
print(c)"
```

### Step 5 — `src/training_data/decode.py`

FIT → one summary JSON and one 1-minute CSV per session, driven by the sport family.

```python
"""Decode raw/*.fit into activities/*.json and streams/*.csv.

Run with:  uv run python -m training_data.decode
"""

import csv
import json
from datetime import date
from pathlib import Path

from garmin_fit_sdk import Decoder, Stream

from training_data.config import (
    ACTIVITIES,
    RAW,
    STREAMS,
    ZONE_GAP_CAP_S,
    family_of,
    load_athlete,
    partition,
)
from training_data.metrics import decoupling, hrss, time_in_zones, tss, zone_bounds_from_fit

# Fields we downsample into streams/. Note enhanced_* — plain `speed` and
# `altitude` do not exist in these files.
STREAM_FIELDS = [
    "heart_rate", "power", "cadence", "enhanced_speed",
    "enhanced_altitude", "temperature", "enhanced_respiration_rate",
]


def read_fit(path: Path) -> dict:
    """Decode a FIT into a dict of message lists."""
    messages, errors = Decoder(Stream.from_file(str(path))).read(
        apply_scale_and_offset=True,      # raw ints -> watts, bpm
        convert_datetimes_to_dates=True,  # FIT timestamps -> datetime
        expand_components=True,
        merge_heart_rates=True,
    )
    if errors:
        raise RuntimeError(f"{path.name}: {errors}")
    return messages


def downsample(records: list[dict], bucket_s: int = 60) -> list[dict]:
    """Average records into per-minute buckets keyed on ELAPSED TIME.

    Bucketing by list position would be wrong: badminton samples every ~4 s, so
    60 records is 4 minutes of wall clock, not one.
    """
    usable = [r for r in records if r.get("timestamp")]
    if not usable:
        return []

    t0 = usable[0]["timestamp"]
    buckets: dict[int, list[dict]] = {}
    for r in usable:
        minute = int((r["timestamp"] - t0).total_seconds() // bucket_s)
        buckets.setdefault(minute, []).append(r)

    rows = []
    for minute in sorted(buckets):
        chunk = buckets[minute]
        row: dict = {"t_min": minute}
        for f in STREAM_FIELDS:
            vals = [r[f] for r in chunk if r.get(f) is not None]
            row[f] = round(sum(vals) / len(vals), 2) if vals else None
        rows.append(row)
    return rows


def extract_sets(messages: dict) -> list[dict]:
    """Strength sets: one entry per active set.

    The exercise name comes from set.category (a FIT enum). Do NOT try to join
    exercise_title_mesgs by wkt_step_index — that mapping is not what it looks
    like and produces labels attached to the wrong sets.
    """
    out = []
    for s in messages.get("set_mesgs", []):
        if s.get("set_type") != "active":
            continue                                  # skip rest sets
        category = s.get("category")
        if isinstance(category, list):
            category = category[0] if category else None
        out.append({
            "n": len(out) + 1,
            "exercise": category,
            "reps": s.get("repetitions"),
            "weight_kg": s.get("weight"),
            "duration_s": round(s.get("duration") or 0, 1),
        })
    return out


def extract_lengths(messages: dict, pool_length: float | None) -> list[dict]:
    """Pool-swim lengths: pace and SWOLF per length."""
    out = []
    for x in messages.get("length_mesgs", []):
        if x.get("length_type") != "active":
            continue
        t = x.get("total_timer_time") or 0
        strokes = x.get("total_strokes")
        out.append({
            "n": len(out) + 1,
            "duration_s": round(t, 1),
            "strokes": strokes,
            "swolf": round(t + strokes) if (strokes is not None) else None,
            "pace_s_per_100m": round(t / pool_length * 100, 1) if pool_length else None,
        })
    return out


def summarise(messages: dict, typekey: str, family: str, athlete: dict) -> dict:
    """Build the per-activity summary, shaped by the sport family."""
    session = messages["session_mesgs"][0]
    records = messages.get("record_mesgs", [])
    laps = messages.get("lap_mesgs", [])
    fam = family_of(typekey)
    prof = athlete["profile"]
    thresholds = athlete.get("thresholds") or {}

    zones = zone_bounds_from_fit(messages)
    floors, garmin_buckets = zones if zones else ([], [])
    computed = time_in_zones(records, floors, ZONE_GAP_CAP_S) if floors else []

    # FTP is per-family: cycling has its own, everything else uses run power.
    # Both default to 0 in athlete.toml, and `or None` keeps TSS null rather
    # than dividing by a number nobody tested.
    np_watts = session.get("normalized_power")
    ftp = (thresholds.get("bike_ftp") if family == "cycling"
           else thresholds.get("run_ftp")) or None

    # LTHR is per-sport-profile on the watch: RUNNING has its own, everything
    # else falls back to DEFAULT. Mirror that here so HRSS matches the zones.
    lthr = (thresholds.get("run_lthr") if family == "running"
            else thresholds.get("default_lthr")) or prof["max_hr"]

    summary = {
        "start": str(session.get("start_time")),
        "sport": typekey,
        "family": family,
        "sub_sport": session.get("sub_sport"),
        "duration_s": session.get("total_elapsed_time"),
        "moving_time_s": session.get("total_timer_time"),
        "distance_m": session.get("total_distance"),
        "elevation_gain_m": session.get("total_ascent"),
        "avg_hr": session.get("avg_heart_rate"),
        "max_hr": session.get("max_heart_rate"),
        "avg_power": session.get("avg_power"),
        "calories": session.get("total_calories"),
        "rpe": session.get("workout_rpe"),           # you already log these
        "feel": session.get("workout_feel"),
        # Garmin's own numbers
        "garmin_load": session.get("training_load_peak"),
        "garmin_np": np_watts,
        "garmin_te_aerobic": session.get("total_training_effect"),
        "garmin_te_anaerobic": session.get("total_anaerobic_training_effect"),
        "garmin_zones_s": garmin_buckets,
        # ours, over the same seven buckets
        "computed_zones_s": computed,
        "computed_hrss": hrss(
            records, prof["resting_hr_baseline"], prof["max_hr"], lthr, ZONE_GAP_CAP_S
        ),
        "computed_tss": tss(np_watts, ftp, session.get("total_timer_time")),
        "decoupling_pct": decoupling(records, fam["output_key"]),
        "zone_floors": floors,
        "laps": [
            {
                "n": i + 1,
                "duration_s": lap.get("total_timer_time"),
                "distance_m": lap.get("total_distance"),
                "avg_hr": lap.get("avg_heart_rate"),
                "avg_power": lap.get("avg_power"),
            }
            for i, lap in enumerate(laps)
        ],
    }

    if fam["sets"]:
        summary["sets"] = extract_sets(messages)
    if fam["lengths"]:
        summary["lengths"] = extract_lengths(messages, session.get("pool_length"))

    return summary


def main() -> None:
    from training_data.config import resolve_family

    athlete = load_athlete()
    decoded = 0

    for fit_path in sorted((RAW / "activities").rglob("*.fit")):
        base = fit_path.stem
        day = date.fromisoformat(f"{base[0:4]}-{base[4:6]}-{base[6:8]}")

        json_out = partition(ACTIVITIES, day) / f"{base}.json"
        csv_out = partition(STREAMS, day) / f"{base}.csv"
        if json_out.exists() and csv_out.exists():
            continue

        # The sibling metadata is the source of truth for sport type — you can
        # correct a mislabelled session in Connect and a re-run picks it up.
        # with_name(stem + ...) rather than chained with_suffix(): the latter
        # mangles any filename whose stem contains a dot.
        meta_path = fit_path.with_name(fit_path.stem + ".meta.json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        typekey = (meta.get("activityType") or {}).get("typeKey", "other")

        family = resolve_family(typekey)
        print(f"  · decoding {base}  ({typekey} → {family})")
        messages = read_fit(fit_path)

        summary = summarise(messages, typekey, family, athlete)
        summary["activity_id"] = base.split("-")[-1]
        summary["garmin_load"] = summary["garmin_load"] or meta.get("activityTrainingLoad")
        json_out.write_text(json.dumps(summary, indent=2, default=str))

        rows = downsample(messages.get("record_mesgs", []))
        if rows:
            with open(csv_out, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)

        decoded += 1

    print(f"✓ decoded {decoded} activities")
```

**Check it:** zone totals should land within a few percent of moving time, for every sport.

```bash
uv run python -m training_data.decode
uv run python -c "
import json, glob
for p in sorted(glob.glob('activities/**/*.json', recursive=True))[:12]:
    a = json.load(open(p))
    z = sum(a['computed_zones_s'] or [0]); t = a['moving_time_s'] or 0
    print(f\"{a['sport']:22s} {100*z/t if t else 0:6.1f}% of timer\")"
```

Every row should read between roughly 95% and 105%.

### Step 6 — `src/training_data/rollup.py`

The four tables. `daily` is built first; `weekly` is a roll-up of it.

```python
"""Build the tables Claude reads.

Run with:  uv run python -m training_data.rollup
"""

import json

import pandas as pd

from training_data.config import (
    ACTIVITIES,
    ATL_DAYS,
    CTL_DAYS,
    DEFAULT_FAMILY,
    FAMILIES,
    RAW,
    TABLES,
)
from training_data.metrics import load_series


def _latest_range_file(stem: str):
    """Newest raw/wellness-range/{stem}-*.json, or None."""
    files = sorted((RAW / "wellness-range").glob(f"{stem}-*.json"))
    return json.loads(files[-1].read_text()) if files else None


def build_activities() -> pd.DataFrame:
    """One row per session."""
    rows = []
    for path in sorted(ACTIVITIES.rglob("*.json")):
        a = json.loads(path.read_text())
        gz = a.get("garmin_zones_s") or []
        cz = a.get("computed_zones_s") or []
        row = {
            "date": a["start"][:10],
            "activity_id": a.get("activity_id"),
            "sport": a.get("sport"),
            "family": a.get("family"),
            "duration_h": round((a.get("moving_time_s") or 0) / 3600, 3),
            "distance_km": round((a.get("distance_m") or 0) / 1000, 2),
            "elevation_m": a.get("elevation_gain_m"),
            "avg_hr": a.get("avg_hr"),
            "max_hr": a.get("max_hr"),
            "avg_power": a.get("avg_power"),
            "rpe": a.get("rpe"),
            "feel": a.get("feel"),
            "garmin_load": a.get("garmin_load"),
            "garmin_np": a.get("garmin_np"),
            "garmin_te_aerobic": a.get("garmin_te_aerobic"),
            "computed_hrss": a.get("computed_hrss"),
            "computed_tss": a.get("computed_tss"),
            "decoupling_pct": a.get("decoupling_pct"),
            "n_sets": len(a.get("sets") or []) or None,
            "n_lengths": len(a.get("lengths") or []) or None,
        }
        # Seven buckets each, same definition on both sides.
        for i in range(7):
            row[f"garmin_z{i}_s"] = gz[i] if i < len(gz) else None
            row[f"computed_z{i}_s"] = cz[i] if i < len(cz) else None
        rows.append(row)

    return pd.DataFrame(rows).sort_values("date") if rows else pd.DataFrame()


def build_wellness_detail() -> pd.DataFrame:
    """Health detail, one row per day. Columns that live in `daily` are excluded."""
    rows = []
    for path in sorted((RAW / "wellness").rglob("*.json")):
        d = json.loads(path.read_text())
        stats = d.get("stats") or {}
        rows.append({
            "date": d["date"],
            "stress_avg": stats.get("averageStressLevel"),
            "stress_max": stats.get("maxStressLevel"),
            "body_battery_max": stats.get("bodyBatteryHighestValue"),
            "body_battery_min": stats.get("bodyBatteryLowestValue"),
            "steps": stats.get("totalSteps"),
            "floors_climbed": stats.get("floorsAscended"),
            "intensity_minutes_moderate": stats.get("moderateIntensityMinutes"),
            "intensity_minutes_vigorous": stats.get("vigorousIntensityMinutes"),
            "calories_active": stats.get("activeKilocalories"),
        })
    return pd.DataFrame(rows).sort_values("date") if rows else pd.DataFrame()


def _wake_readiness(entries: list) -> dict:
    """Earliest AFTER_WAKEUP_RESET snapshot — the score you woke up with.

    Garmin returns 2-8 snapshots a day, newest first, and the number moves by
    tens of points between morning and evening.
    """
    if not entries:
        return {}
    wake = [e for e in entries if e.get("inputContext") == "AFTER_WAKEUP_RESET"]
    if wake:
        return min(wake, key=lambda e: e.get("timestampLocal") or "")
    return entries[-1]


def _primary_device(mapping: dict) -> dict:
    """Training status is keyed by device id — prefer the primary watch."""
    for v in (mapping or {}).values():
        if isinstance(v, dict) and v.get("primaryTrainingDevice"):
            return v
    return next((v for v in (mapping or {}).values() if isinstance(v, dict)), {})


def build_daily(acts: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar day: training + headline wellness + CTL/ATL/form."""
    # --- dense date index: every day exists, rest days included ---
    if acts.empty:
        return pd.DataFrame()

    acts = acts.copy()
    acts["date"] = pd.to_datetime(acts["date"])
    idx = pd.date_range(acts["date"].min(), pd.Timestamp.today().normalize(), freq="D")
    daily = pd.DataFrame(index=idx)
    daily.index.name = "date"

    # --- training ---
    daily["load"] = acts.groupby("date")["garmin_load"].sum().reindex(idx, fill_value=0.0)
    daily["hrss"] = acts.groupby("date")["computed_hrss"].sum().reindex(idx, fill_value=0.0)
    daily["sessions"] = acts.groupby("date").size().reindex(idx, fill_value=0)

    # Walking/hiking/breathwork are movement, not training — they are 7.7% of
    # your hours and 1.7% of your load, so they get their own column but stay
    # out of training_h.
    training_families = {
        f for f in acts["family"].dropna().unique()
        if FAMILIES.get(f, DEFAULT_FAMILY)["training"]
    }
    is_training = acts["family"].isin(training_families)
    daily["training_h"] = (
        acts[is_training].groupby("date")["duration_h"].sum().reindex(idx, fill_value=0.0).round(2)
    )
    daily["all_h"] = acts.groupby("date")["duration_h"].sum().reindex(idx, fill_value=0.0).round(2)

    # hours per family -> run_h, cycling_h, swimming_h, ...
    by_fam = acts.pivot_table(index="date", columns="family", values="duration_h", aggfunc="sum")
    for fam in by_fam.columns:
        daily[f"{fam}_h"] = by_fam[fam].reindex(idx, fill_value=0.0).round(2)

    # --- wellness from the range endpoints (one call each) ---
    rhr = _latest_range_file("rhr")
    if rhr:
        s = pd.DataFrame(rhr)
        s["calendarDate"] = pd.to_datetime(s["calendarDate"])
        daily["rhr"] = s.set_index("calendarDate")["value"]

    hrv = _latest_range_file("hrv")
    if hrv and hrv.get("hrvSummaries"):
        s = pd.DataFrame(hrv["hrvSummaries"])
        s["calendarDate"] = pd.to_datetime(s["calendarDate"])
        s = s.set_index("calendarDate")
        daily["hrv"] = s["lastNightAvg"]
        daily["hrv_7d"] = s["weeklyAvg"]
        daily["hrv_status"] = s["status"]

    sleep = _latest_range_file("sleep")
    if sleep:
        s = pd.json_normalize(sleep)
        s["calendarDate"] = pd.to_datetime(s["calendarDate"])
        s = s.set_index("calendarDate")
        daily["sleep_h"] = (s["values.totalSleepTimeInSeconds"] / 3600).round(2)
        daily["sleep_quality"] = s.get("values.sleepScoreQuality")

    mm = _latest_range_file("max_metrics")
    if mm:
        vo2 = pd.DataFrame([
            {"calendarDate": x["generic"]["calendarDate"],
             "vo2max": x["generic"]["vo2MaxPreciseValue"]}
            for x in mm if x.get("generic")
        ])
        vo2["calendarDate"] = pd.to_datetime(vo2["calendarDate"])
        # Only ~21 of 50 days carry a reading; carry the last one forward.
        daily["vo2max"] = vo2.set_index("calendarDate")["vo2max"].reindex(idx).ffill()

    rp = _latest_range_file("race_predictions")
    if rp:
        s = pd.DataFrame(rp)
        s["calendarDate"] = pd.to_datetime(s["calendarDate"])
        daily["hm_prediction_s"] = s.set_index("calendarDate")["timeHalfMarathon"]

    # --- per-day files: readiness + training status ---
    ready, status = {}, {}
    for path in sorted((RAW / "wellness").rglob("*.json")):
        d = json.loads(path.read_text())
        ts = pd.Timestamp(d["date"])
        w = _wake_readiness(d.get("training_readiness") or [])
        ready[ts] = (w.get("score"), w.get("acuteLoad"), w.get("recoveryTime"))
        st = _primary_device(
            ((d.get("training_status") or {}).get("mostRecentTrainingStatus") or {})
            .get("latestTrainingStatusData")
        )
        status[ts] = st.get("trainingStatusFeedbackPhrase")
    if ready:
        r = pd.DataFrame.from_dict(
            ready, orient="index", columns=["readiness", "garmin_acute_load", "recovery_time_min"]
        )
        daily = daily.join(r)
    if status:
        daily["training_status"] = pd.Series(status)

    # --- CTL / ATL / form ---
    loads = daily["load"].fillna(0.0).tolist()
    seed = sum(loads[:7]) / 7 if len(loads) >= 7 else 0.0
    series = load_series(loads, CTL_DAYS, ATL_DAYS, seed=seed)
    daily["ctl"] = [s[0] for s in series]
    daily["atl"] = [s[1] for s in series]
    daily["form"] = [s[2] for s in series]
    daily["ctl_warmup"] = [i < CTL_DAYS for i in range(len(daily))]

    return daily.reset_index()


def build_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Roll `daily` up to ISO weeks."""
    if daily.empty:
        return pd.DataFrame()
    d = daily.copy()
    d["week_start"] = pd.to_datetime(d["date"]).dt.to_period("W").dt.start_time

    # Careful: sleep_h also ends in "_h" but is a nightly average, not a weekly
    # total — summing it would report 50-hour weeks of sleep.
    means = [c for c in ("rhr", "hrv", "sleep_h", "readiness", "vo2max") if c in d.columns]
    family_hours = [
        c for c in d.columns
        if c.endswith("_h") and c not in ("training_h", "all_h") and c not in means
    ]
    sums = ["load", "hrss", "sessions", "training_h", "all_h"] + family_hours

    weekly = d.groupby("week_start")[sums].sum().round(2)
    weekly = weekly.join(d.groupby("week_start")[means].mean().round(1))
    # End-of-week values, not averages — these are stocks, not flows.
    weekly = weekly.join(d.groupby("week_start")[["ctl", "atl", "form"]].last())
    if "hm_prediction_s" in d.columns:
        weekly["hm_prediction_s"] = d.groupby("week_start")["hm_prediction_s"].last()
    return weekly.reset_index()


def write_partitioned(df: pd.DataFrame, prefix: str, date_col: str) -> None:
    """One CSV per year: a finished year stops churning in git forever."""
    if df.empty:
        print(f"  – {prefix}: nothing to write")
        return
    df = df.copy()
    df["_year"] = pd.to_datetime(df[date_col]).dt.year
    for year, group in df.groupby("_year"):
        out = TABLES / f"{prefix}-{year}.csv"
        group.drop(columns="_year").to_csv(out, index=False)
        print(f"  → {out.name}  ({len(group)} rows, {len(group.columns)-1} cols)")


def main() -> None:
    TABLES.mkdir(exist_ok=True)

    acts = build_activities()
    daily = build_daily(acts)
    weekly = build_weekly(daily)
    wellness = build_wellness_detail()

    write_partitioned(acts, "activities", "date")
    write_partitioned(daily, "daily", "date")
    write_partitioned(weekly, "weekly", "week_start")
    write_partitioned(wellness, "wellness", "date")
    print("✓ tables rebuilt")


if __name__ == "__main__":
    main()
```

### Step 7 — `src/training_data/validate.py`

The thresholds below come from the measured null-rates in Part 2, not from guesses.

```python
"""Assertions that run before every commit. Exits non-zero on failure.

Run with:  uv run python -m training_data.validate
"""

import json
import sys
from datetime import date

import pandas as pd

from training_data.config import ACTIVITIES, FAMILIES, RAW, STREAMS, TABLES

MAX_FILE_BYTES = 1_000_000
MAX_DIR_ENTRIES = 2_500
ZONE_TOLERANCE = 0.10          # computed zone total vs moving time

failures: list[str] = []


def check(ok: bool, message: str) -> None:
    if not ok:
        failures.append(message)


def main() -> None:
    year = date.today().year

    # 1. every FIT decoded
    fits = {p.stem for p in (RAW / "activities").rglob("*.fit")}
    jsons = {p.stem for p in ACTIVITIES.rglob("*.json")}
    orphans = fits - jsons
    check(not orphans, f"{len(orphans)} FIT files never decoded: {sorted(orphans)[:3]}")

    # 2 & 3. one pass over the decoded summaries:
    #   - zone totals must be close to moving time (catches a regression back
    #     to counting records instead of seconds)
    #   - every family has a FAMILIES entry. Garmin has 17 families and
    #     config.py defines 8; anything else silently counts as non-training,
    #     so fail loudly instead.
    known_other = {"breathwork"}
    unmapped: set[str] = set()
    for p in ACTIVITIES.rglob("*.json"):
        a = json.loads(p.read_text())

        total = sum(a.get("computed_zones_s") or [])
        timer = a.get("moving_time_s") or 0
        if timer > 300 and total:
            ratio = total / timer
            check(abs(ratio - 1) <= ZONE_TOLERANCE,
                  f"{p.name}: zones are {ratio:.0%} of moving time")

        fam, sport = a.get("family"), a.get("sport")
        if fam not in FAMILIES or (fam == "other" and sport not in known_other):
            unmapped.add(f"{sport} → {fam}")

    check(not unmapped, f"sports with no FAMILIES entry: {sorted(unmapped)}")

    # 4. daily table: dense, and the key columns are populated
    daily_csv = TABLES / f"daily-{year}.csv"
    check(daily_csv.exists(), f"missing {daily_csv.name}")
    if daily_csv.exists():
        df = pd.read_csv(daily_csv, parse_dates=["date"])
        gaps = pd.date_range(df["date"].min(), df["date"].max(), freq="D").difference(df["date"])
        check(len(gaps) == 0, f"daily table has {len(gaps)} missing dates")

        recent = df.tail(30)
        for col, floor in (("rhr", 0.95), ("readiness", 0.95),
                           ("sleep_h", 0.85), ("hrv", 0.85)):
            if col in recent:
                filled = recent[col].notna().mean()
                check(filled >= floor,
                      f"{col} only {filled:.0%} populated over the last 30 days")

        for col in ("ctl", "atl", "form", "load"):
            check(col in df.columns and df[col].notna().any(), f"{col} is entirely empty")

    # 5. size and directory limits
    for root in (ACTIVITIES, STREAMS, TABLES):
        for p in root.rglob("*"):
            if p.is_file() and p.stat().st_size > MAX_FILE_BYTES:
                failures.append(f"{p} is {p.stat().st_size // 1024} KB (>1 MB)")
    for root in (RAW, ACTIVITIES, STREAMS):
        for d in root.rglob("*"):
            if d.is_dir():
                n = len(list(d.iterdir()))
                if n > MAX_DIR_ENTRIES:
                    failures.append(f"{d} has {n} entries (cap 3000)")

    if failures:
        print("✗ validation failed:")
        for f in failures:
            print(f"   - {f}")
        sys.exit(1)
    print("✓ validation passed")


if __name__ == "__main__":
    main()
```

### Step 8 — `athlete.toml`

Your current file is stale against Garmin. Replace the thresholds section:

```toml
[profile]
max_hr = 201
resting_hr_baseline = 50        # Garmin's configured value; observed 49-55
weight_kg = 62.0                # Garmin has 62.0 as of 2026-09-07
sex = "male"                    # TRIMP exponent: 1.92 male / 1.67 female

[thresholds]
run_lthr = 194                  # get_heart_rate_zones() RUNNING profile
default_lthr = 179              # DEFAULT profile — applies to any sport with no profile
run_ftp = 264                   # RUNNING power threshold, estimated from weight
bike_ftp = 0                    # set after a real FTP test; 200 is Garmin's placeholder
swim_css_s_per_100m = 0
run_threshold_pace_s_per_km = 0 # see Open items

[load]
ctl_days = 42
atl_days = 7

# HR zone boundaries are NOT here on purpose — they are read per activity from
# each FIT's time_in_zone message, so they always match what the watch used.
```

### Step 9 — Automate

`bin/sync.sh`, the `launchd` agent at 06:30, and the shell aliases are unchanged from your
existing setup; add `validate` before the commit so a bad run can't push:

```bash
$UV run python -m training_data.fetch
$UV run python -m training_data.decode
$UV run python -m training_data.rollup
$UV run python -m training_data.validate   # non-zero exit aborts before commit
```

---

## Part 6 — Verification

```bash
# metrics maths
uv run python -c "
from training_data.metrics import load_series
print(load_series([100]*30)[-1])"          # ~(51.5, 99.0, -48.6)

# family resolution, including October's sports
uv run python -c "
from training_data.config import resolve_family
for k in ['treadmill_running','indoor_cycling','virtual_ride','badminton','tennis']:
    print(k, '->', resolve_family(k))"

# full pipeline
uv run python -m training_data.fetch
uv run python -m training_data.decode
uv run python -m training_data.rollup
uv run python -m training_data.validate

# sanity-read the money table
uv run python -c "
import pandas as pd
d = pd.read_csv('tables/daily-2026.csv')
print(d[['date','load','training_h','ctl','atl','form','readiness']].tail(14).to_string())"
```

What "good" looks like: nine sports in `activities-2026.csv`; every zone total within 10%
of moving time; `daily-2026.csv` with no missing dates and no empty `ctl`/`form`; weekly
load matching the numbers in Part 2 for August and September.

---

## Part 7 — October: the cycling checklist

Structurally, cycling already works — `resolve_family` maps all 17 cycling `typeKey`s to
`cycling`, which has `output_key = "power"`, so decoupling, NP and TSS all engage on the
first ride with no code change. Four things to check after that first ride:

1. **Which `typeKey` did the watch emit?** Indoor trainer, outdoor and Zwift are three
   different keys (`indoor_cycling`, `cycling`/`road_biking`, `virtual_ride`). All map to
   `cycling`; confirm in `activities-2026.csv`.
2. **HR zones fall back to `DEFAULT`.** You have `DEFAULT` (LTHR 179) and `RUNNING`
   (LTHR 194) profiles — there is no `CYCLING` one. Cycling zone maths will use 179 until
   you create a cycling profile on the watch. Not wrong, but know which number you're using.
3. **FTP is a placeholder.** `get_power_zones_for_sport("CYCLING")` returns FTP 200 W, but
   `get_cycling_ftp()` is null — nothing has been tested. Leave `bike_ftp = 0` in
   `athlete.toml` so `computed_tss` stays null rather than quietly wrong; set it after a
   20-minute test.
4. **Does a cycling FIT populate `normalized_power`?** Your running files do. Confirm with
   `uv run python -c "from training_data.decode import read_fit; ..."` on the first ride —
   if not, NP has to be computed from the power stream.

---

## Part 8 — Open items

- **`get_lactate_threshold().speed_and_heart_rate.speed = 0.3139`** — the unit is ambiguous.
  Inverted it gives 3.19 m/s (5:14/km), which sits oddly against a 2:11 half-marathon
  prediction (~6:14/km). HR (192-194) and power (264) from the same payload both
  cross-check against the FIT, so only `speed` is in doubt. Leave
  `run_threshold_pace_s_per_km = 0` until a field test settles it.
- **Strength exercise names.** `set.category` gives the FIT enum (`push_up`, `calf_raise`),
  which is good enough for counting. The readable names in `exercise_title_mesgs` exist but
  the join key is not `wkt_step_index` — joining that way attaches names to the wrong sets.
  Worth solving if you want per-exercise history.
- **`ctl_warmup`.** For the first 42 days of data, CTL is still converging and the column
  says so. Backfilling more history is the real fix, and the backfill is cheap now that
  wellness uses range endpoints.
- **Your half-marathon prediction has slipped 8.8 minutes** since 1 August while training
  status sat at `UNPRODUCTIVE` for 31 of 50 days. That is a coaching question, not a
  pipeline question, but it is the first thing the tables will let you interrogate.
