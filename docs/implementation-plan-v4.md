# `training-data` — Implementation Plan v4

A repo that pulls your FIT files, wellness data and Garmin's own metrics off Garmin Connect
every day, so a coaching conversation with Claude starts from your actual data instead of from
files you downloaded by hand.

**Written to be implemented by hand, in order.** Every file is given complete. Read the "why"
above each one, type or paste it, run the check, then move on.

The Python listings were run against your account on 2026-10-04 (44 activities, 34 days). The
expected outputs in the checks are what that run printed, so yours should match in shape and,
for past dates, in value.

Two parts were **not** run for real on your machine, and say so where they appear: the
commit-and-push half of `bin/sync.sh` (Step 7 — tested in a throwaway repository) and the
launchd install (Step 8 — syntax-checked only).

v3 is in `docs/archive/`. Part 2 says what was cut from it and why.

---

## Part 1 — What you're building

```
  bin/sync.sh     launchd, daily at 22:30 — or by hand, whenever you want fresh data
  ┌───────────────────────────────────────────────────────────────────────┐
  │ 1. FETCH    Garmin Connect → raw/      FIT + JSON, numbers untouched   │
  │ 2. TABLES   raw/**/*.json  → tables/   two CSVs: select, rename        │
  │ 3. COMMIT   raw/ tables/ LOG.md → main → push                          │
  └───────────────────────────────────────────────────────────────────────┘
                                   ↓
        Claude Code   reads tables/, opens raw/ JSON, decodes a FIT on demand
        claude.ai     reads tables/ + ATHLETE.md + LOG.md via the GitHub connector
```

Two stages and a commit. There is no decode stage, no metrics module and no validator.

### What ends up on disk

```
raw/activities/YYYY/MM/<YYYYMMDD-HHMMSS>-<id>.fit    the original FIT
raw/activities/YYYY/MM/<YYYYMMDD-HHMMSS>-<id>.json   everything Connect knows about that session
raw/wellness/YYYY/MM/YYYY-MM-DD.json                 everything Garmin knows about that day
raw/profile.json                                     zones, thresholds, personal records
tables/activities-YYYY.csv                           one row per session
tables/daily-YYYY.csv                                one row per day
```

| table | grain | what it answers |
|---|---|---|
| `tables/activities-YYYY.csv` | one row per session | "What did I do?" Duration, distance, HR, Garmin load, Training Effect, zone minutes, power, swim and strength counts, weather, RPE. |
| `tables/daily-YYYY.csv` | one row per day | "How did my body respond?" Sleep, HRV, resting HR, stress, body battery, readiness, training status, acute and chronic load, VO2max, race predictions. |

The tables are the index. When a row is not enough, Claude opens the one raw file behind it, or
decodes the FIT.

---

## Part 2 — What changed from v3

v3 computed its own training metrics. Garmin already returns every one of them:

| v3 computed or hand-maintained | Garmin already returns |
|---|---|
| CTL / ATL / form | acute load, chronic load, ACWR and its status, and a four-week load balance against targets — all in `get_training_status` |
| HRSS, TSS | `activityTrainingLoad` on all 44 activities; `trainingStressScore`, `intensityFactor` and a power curve on rides |
| time in zone, from records | `hrTimeInZone_1..5` on every activity; the FIT holds seven HR buckets and the power zones |
| VO2max forward-fill | training status carries the most recent run **and cycling** VO2max for every day |
| zones, LTHR, FTP in `athlete.toml` | `get_heart_rate_zones` (three sport profiles), `get_power_zones`, `get_lactate_threshold` |

So this goes:

| removed | why |
|---|---|
| `metrics.py` — HRSS, TSS, decoupling, steadiness, CTL/ATL | Garmin's numbers are used as they are |
| `decode.py`, `activities/`, `streams/` | no decode stage: a FIT is read on demand, in 0.1–0.5 s |
| `rollup.py` — weekly table, zero-filled series, per-family pivots | replaced by `tables.py`, which only flattens |
| `validate.py` | it checked maths that no longer exists |
| the `FAMILIES` registry and `resolve_family` | nothing branches on sport any more |
| `athlete.toml` | zones and thresholds come from Garmin, in `raw/profile.json` |
| `.sync-state.json` | the activity JSON is the state (Decision 3) |
| the PII scrub | the repo is public by your choice, and everything is committed (Decision 7) |

And this is new: `tables.py`, `fit.py`, `bin/sync.sh`, the launchd job, and a `CLAUDE.md`.

The code that is left is about 800 lines including comments and docstrings: `config.py` 31,
`fetch.py` 289, `tables.py` 288 (over a third of it is the two column lists) and `fit.py` 187.

---

## Part 3 — Your data, measured

Pulled 2026-09-01 → 2026-10-04: **44 activities across 7 sports**, 34 days of wellness.

| sport (`typeKey`) | n | hours | Garmin load |
|---|---:|---:|---:|
| `running` | 16 | 19.4 | 2571 |
| `badminton` | 5 | 10.9 | 830 |
| `cycling` | 3 | 2.9 | 152 |
| `lap_swimming` | 3 | 4.3 | 109 |
| `strength_training` | 10 | 3.7 | 100 |
| `walking` | 4 | 1.1 | 29 |
| `breathwork` | 3 | 0.3 | 0 |
| **total** | **44** | **42.6** | **3791** |

### What Connect already carries, per sport

| sport | fields in the activity list |
|---|---|
| every sport | duration, HR, `activityTrainingLoad`, aerobic and anaerobic Training Effect, `hrTimeInZone_1..5`, calories |
| `running` | distance, speed, running power (avg / normalized / max), cadence, running dynamics, VO2max |
| `cycling` | power (avg / normalized / max), `trainingStressScore`, `intensityFactor`, `max20MinPower`, a power curve, cadence |
| `lap_swimming` | `poolLength`, `activeLengths`, `averageSwolf`, `avgStrokes`, stroke cadence |
| `strength_training` | `activeSets`, `totalReps`, `summarizedExerciseSets` |
| `badminton` | HR and load only |

### Six facts that shape the code

**1. "Morning readiness" is not the first wake-up entry Garmin gives you.**
`get_training_readiness` returns several snapshots a day, newest first. On **14 of the 34 days**
there are *two* `AFTER_WAKEUP_RESET` entries: one when you got up, and another after the
morning session.

| date | on waking | later "wake-up" entry |
|---|---|---|
| 2026-09-04 | 05:17 → **64** | 07:35 → 12 |
| 2026-09-24 | 04:11 → **59** | 07:55 → 1 |
| 2026-10-01 | 04:35 → **54** | 07:45 → 1 |
| 2026-10-04 | 04:05 → **52** | 07:35 → 32 |

The library's `get_morning_training_readiness()` returns the first one in the list — the later
one — so it is wrong on all 14 days. `fetch` therefore stores every snapshot, and `tables` takes
the **earliest** wake-up entry.

**2. Connect's five HR zones do not add up to the session.** `hrTimeInZone_1..5` leave out the
time below zone 1. On the 28 Sep badminton session that is 53 of 120 minutes; on a strength
session it is most of it. The table adds one derived column, `z0_min`, so the six columns sum to
the duration. Checked against the FIT's own below-zone-1 bucket on four sports: it agrees within
seconds.

**3. A night of sleep data is 95% samples.** `get_sleep_data` returned 70 KB and 145 KB for the
two nights already in the repo — per-minute movement, SpO2 and heart rate. With those arrays
dropped, 3.5–3.8 KB is left, and it still holds every number on Garmin's sleep screen.

**4. RPE and feel are not in the activity list.** They come from `get_activity(id)`, as
`directWorkoutRpe` and `directWorkoutFeel`. That is one extra call per new activity.

**5. Some endpoints are empty for your watch.** Endurance score, hill score, running tolerance,
training plans and goals all return nothing for the FR 265S, and `get_cycling_ftp` is all nulls.
None of them is fetched.

**6. Garmin's JSON is not stable between calls, even when the data is.** Two runs a minute apart
changed the bytes of all 19 activity files in the window — with identical content. Two causes:

- The activity list returns the same fields in a different order on every request.
- Each race-prediction row echoes back the window it was asked for (`fromCalendarDate`,
  `toCalendarDate`), so it changes whenever the window slides, which is every night.

Left alone, every nightly commit would rewrite some 30 files for nothing. So `fetch` writes JSON
with sorted keys and drops those two echo fields. After that, three runs over three different
windows (34, 11 and 14 days) changed **zero** files.

### What a sync costs

| data | call | cadence |
|---|---|---|
| activity list | `get_activities_by_date(since, today)` | 1, paged by the library |
| FIT | `download_activity(id, ORIGINAL)` | once per new activity |
| RPE and feel, split summaries, multisport links | `get_activity(id)` | once per new activity |
| weather | `get_activity_weather(id)` | once per new activity |
| daily summary: RHR, stress, body battery, steps, SpO2 | `get_stats(day)` | per day in the window |
| sleep score, stages, sleep need, naps | `get_sleep_data(day)` | per day |
| status, acute and chronic load, load balance, VO2max | `get_training_status(day)` | per day |
| readiness, every snapshot | `get_training_readiness(day)` | per day |
| HRV, race predictions, weight | `get_hrv_data_range`, `get_race_predictions`, `get_weigh_ins` | 1 each per 28-day chunk |
| zones, thresholds, personal records | five profile calls | 5 per sync |

A default 14-day run is about 65 calls and took **51 seconds**. The September backfill took
about four minutes.

On disk, those 34 days are 9.2 MB: 8.2 MB of FIT files, 0.6 MB of activity JSON (14 KB each),
0.6 MB of wellness (18 KB a day, down from 124–227 KB) and 18 KB of tables. That is roughly
100 MB a year.

---

## Part 4 — Design decisions

**1. Garmin's numbers, not ours.** Every column in both tables is a field Garmin computed.
`tables.py` selects, renames and converts units. The complete list of what it does beyond that
is three items long: it picks the primary training device out of Garmin's per-device maps, it
picks the earliest wake-up readiness snapshot (Fact 1), and it derives `z0_min` (Fact 2).

**2. `raw/` is verbatim and `tables/` is disposable.** `fetch` writes what Garmin returned, with
two things left out: the per-minute sleep arrays (Fact 3) and the window fields that
race-prediction rows echo back (Fact 6). Keys are written sorted, for the same Fact 6 reason: an
unchanged document must be byte-identical, so a commit shows only what really changed. Both
tables are rebuilt from scratch on every run, in well under a second. So a new column never
needs a re-fetch — add a line, re-run.

**3. The activity JSON is the sync state.** Each activity document has four keys. `summary` is
refreshed on every run, because you rename sessions and fix sport types later. `fit`, `detail`
and `weather` are fetched once. A missing key means "not fetched yet", so there is no separate
state file to keep in step, and a run that died half-way finishes itself next time.

**4. One bad item cannot stall the daily job.** There are two kinds of failure:

- *Run-level* — login, or the activity list. The run aborts with a non-zero exit and nothing is
  committed.
- *Per-item* — one FIT, one detail call, one endpoint for one day. It is logged and skipped. The
  value already on disk is kept (good data is never overwritten with nothing) and the call is
  tried again on the next run.

An activity that has no FIT at all — typed into Connect by hand, or imported as GPX — gets
`"fit": null` and is not asked for again.

**5. FIT files are read on demand.** Nothing is pre-decoded and no stream files are stored.
`fit.py` returns every sample at the watch's own resolution whenever Claude needs it. Storing
per-second CSVs would roughly triple the repo's growth for data that is already in the FIT.

**6. Data reaches `main` only through `bin/sync.sh`.** Never through a code PR. The script
commits only `raw/`, `tables/` and `LOG.md`, and only when the checkout is on `main`; on a
feature branch it refreshes the files and leaves them uncommitted. Your PRs stay code-only and
the size labeler stays honest.

**7. The repo is public and everything is committed.** Your decision, made knowing that it
publishes GPS tracks, the identity fields inside each FIT, and daily health data. So there is no
scrub step. `gh repo edit --visibility private` remains one command if you change your mind,
though it cannot recall what was already public.

**8. Once a day, at 22:30.** That is your latest regular finish — badminton, 21:30 — plus an
hour for the watch to sync, so one run captures the whole day. Every run re-fetches the last 14
days, so the time never affects completeness, only how fresh the tables are. If the Mac is
asleep, launchd runs the job at the next wake.

---

## Part 5 — Build it

Prerequisites: `uv` installed; `bin/login.py` already run (your token from 19 September still
worked on 4 October without a new login); `garminconnect==0.3.15` pinned.

**Slicing it into PRs.** Steps 0–2 are one PR, because the old `fetch.py` does not import once
`config.py` is slimmed. After that, one PR per step works well.

**One rule on every branch: never `git add -A`.** From Step 2 onwards `raw/` and `tables/` hold
data that belongs to `bin/sync.sh` (Decision 6). Stage code by path.

### Step 0 — Clean out

```bash
git switch -c refactor/thin-sync

# Tracked files: `git rm` deletes and stages the deletion.
git rm src/training_data/decode.py athlete.toml .sync-state.json
git rm activities/placeholder.txt streams/placeholder.txt docs/placeholder.txt \
       tables/placeholder.txt etc/placeholder.txt
git rm raw/activities/2026/09/*.meta.json

# Never committed: plain rm.
rm src/training_data/metrics.py src/training_data/rollup.py src/training_data/validate.py

# Plain rm ON PURPOSE (not git rm): Step 3 recreates these two files in the
# new shape, and sync.sh commits that as an ordinary change.
rm raw/wellness/2026/09/*.json

# Empty the package marker — it holds a "Hello" stub — and start tracking it.
# It was never committed, so a fresh clone could not build the package.
: > src/training_data/__init__.py
git add src/training_data/__init__.py

# Start tracking the plans. Nothing under docs/ is committed yet, and the
# placeholder you just removed was the only tracked file there.
git add docs/
```

Nothing of substance is lost. `metrics.py` and the v3 `config.py` are in the archived v3 doc in
full (your copies differ by a comment line and one constant), and `decode.py` stays in git
history.

In `pyproject.toml`, delete the script stub — it points at the function you just removed:

```toml
[project.scripts]
training-data = "training_data:main"
```

and while you are there, replace the placeholder description:

```toml
description = "Sync Garmin Connect data into a repo Claude can read"
```

`pandas` stays in the dependencies. The pipeline no longer imports it, but Claude uses it in
analysis sessions.

**Check it:**

```bash
uv sync
uv run python -c "import training_data; print('package imports')"
```

### Step 1 — `src/training_data/config.py`

Paths and two constants. Replace the whole file — this also discards the uncommitted v3 edit.

```python
"""Central configuration: paths and tuning constants.

No logic beyond partition() — one place to change a path.
"""

from datetime import date
from pathlib import Path

# config.py -> training_data -> src -> repo root
REPO = Path(__file__).resolve().parents[2]

RAW = REPO / "raw"
ACTIVITIES = RAW / "activities"         # <stamp>-<id>.fit and <stamp>-<id>.json
WELLNESS = RAW / "wellness"             # one JSON per day
PROFILE_FILE = RAW / "profile.json"     # zones, thresholds, personal records
TABLES = REPO / "tables"

TOKENSTORE = Path.home() / ".garminconnect"

# Garmin revises history: sleep scores recalculate, training status lags a day,
# and sessions get renamed. Every run re-fetches this many days.
REFRESH_DAYS = 14

RATE_LIMIT_SLEEP = 1.5          # seconds to pause between bursts of API calls


def partition(root: Path, d: date) -> Path:
    """Return root/YYYY/MM/, creating it. GitHub caps a directory at 3,000 entries."""
    p = root / f"{d:%Y}" / f"{d:%m}"
    p.mkdir(parents=True, exist_ok=True)
    return p
```

`garmin.py` is unchanged: it still imports `RATE_LIMIT_SLEEP` and `TOKENSTORE` from here.

**Check it:**

```bash
uv run python -c "from training_data import config; print(config.ACTIVITIES); print(config.REFRESH_DAYS)"
```

Expect `…/training-data/raw/activities` and `14`.

### Step 2 — `src/training_data/fetch.py`

Three ideas carry the whole file.

- **`fill(doc, key, label, fn)`** is the only place an API call can fail quietly. It sets
  `doc[key] = fn()`. If the call fails after retries, the key is left exactly as it was and the
  label is added to a list that `main()` prints at the end. With `once=True` it skips the call
  when the key already exists. Those two behaviours are all of Decisions 3 and 4.
- **Range endpoints first, then the per-day loop.** HRV, race predictions and weight each cover
  a whole window in one call, so they are fetched once per 28-day chunk and indexed by date. The
  four per-day endpoints are then called for each day, and the range rows are merged into the
  same day file.
- **The window heals itself.** With no `--since`, the run starts 14 days back — or at the newest
  wellness file if that is older, so three weeks with the Mac off costs nothing but a longer
  run.

Replace the whole file:

```python
"""Download from Garmin Connect into raw/.

Run with:  uv run python -m training_data.fetch [--since YYYY-MM-DD]

Everything is written as Garmin returned it. Nothing is computed here.
"""

import argparse
import json
import time
import zipfile
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Iterator

from garminconnect import Garmin

from training_data.config import (
    ACTIVITIES,
    PROFILE_FILE,
    RATE_LIMIT_SLEEP,
    REFRESH_DAYS,
    WELLNESS,
    partition,
)
from training_data.garmin import client, with_retry

# Calls that failed for good during this run. They are reported at the end and
# tried again on the next run; they do not stop this one.
failed: list[str] = []


def load(path: Path) -> dict:
    """Read a JSON file, or return {} if it does not exist yet."""
    return json.loads(path.read_text()) if path.exists() else {}


def save(path: Path, doc: dict) -> None:
    """Write a JSON file with its keys sorted.

    Garmin returns the same fields in a different order on every call. Sorting
    makes an unchanged document byte-identical, so git only sees real changes.
    """
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")


def fill(doc: dict, key: str, label: str, fn: Callable[[], Any], once: bool = False) -> None:
    """Set doc[key] = fn().

    once=True skips the call when the key is already there. That is how a FIT
    or an activity's detail gets fetched exactly one time.

    If the call fails even after retries, doc[key] is left exactly as it was:
    good data is never overwritten with nothing, and one bad item cannot stop
    the run. The label is remembered so main() can report it.
    """
    if once and key in doc:
        return
    try:
        doc[key] = with_retry(fn, label=label)
    except Exception as e:
        print(f"  ! {label}: {type(e).__name__}: {e}")
        failed.append(label)


def default_since() -> date:
    """First day of the refresh window.

    Normally REFRESH_DAYS back. If the newest wellness file is older than that
    — the Mac was off for three weeks — reach back to it instead, so the gap
    fills itself.
    """
    floor = date.today() - timedelta(days=REFRESH_DAYS - 1)
    files = sorted(WELLNESS.rglob("*.json"))    # YYYY/MM/YYYY-MM-DD sorts by date
    if not files:
        return floor
    return min(floor, date.fromisoformat(files[-1].stem))


# ── activities ───────────────────────────────────────────────────────────────

def download_fit(c: Garmin, aid: str, fit_path: Path) -> str | None:
    """Download one activity's original file. Returns its name, or None if it has no FIT."""
    blob = c.download_activity(aid, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL)

    # GOTCHA: ORIGINAL returns a ZIP archive, not a bare .fit file.
    # BytesIO wraps the bytes so zipfile can read them like a file.
    with zipfile.ZipFile(BytesIO(blob)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".fit")]
        if not names:
            return None                       # e.g. a session imported as GPX
        fit_path.write_bytes(z.read(names[0]))
    return fit_path.name


def fetch_activities(c: Garmin, since: date) -> int:
    """List activities since `since` and fetch whatever is missing. Returns the new FIT count."""
    # Not wrapped in fill(): if the list itself fails, the run should fail.
    activities = with_retry(
        lambda: c.get_activities_by_date(since.isoformat(), date.today().isoformat()),
        label="list activities",
    )
    new_fits = 0
    listed = set()                            # every name Connect still knows about

    for act in activities:
        aid = str(act["activityId"])
        start = date.fromisoformat(act["startTimeLocal"][:10])

        # Filename: 20260826-071233-19283746
        # Sortable by time, unique by ID, no spaces or colons.
        stamp = act["startTimeLocal"].replace("-", "").replace(":", "").replace(" ", "-")
        base = f"{stamp}-{aid}"
        listed.add(base)
        out_dir = partition(ACTIVITIES, start)
        doc_path = out_dir / f"{base}.json"
        fit_path = out_dir / f"{base}.fit"

        # The JSON document IS the sync state. `summary` is refreshed on every
        # run, because titles and sport types get edited later. The other keys
        # are fetched once; a missing key means "not fetched yet".
        doc = load(doc_path)
        known = set(doc)                      # keys fetched on earlier runs
        doc["summary"] = act

        had_fit = fit_path.exists()
        if had_fit:
            doc.setdefault("fit", fit_path.name)    # downloaded on an earlier run
        elif act.get("manualActivity"):
            doc.setdefault("fit", None)             # typed into Connect: no file exists
        fill(doc, "fit", f"fit {base}", lambda: download_fit(c, aid, fit_path), once=True)

        # RPE and feel, split summaries, and the parent/child links of a multisport.
        fill(doc, "detail", f"detail {base}", lambda: c.get_activity(aid), once=True)
        # Temperature, humidity and dew point at the start.
        fill(doc, "weather", f"weather {base}", lambda: c.get_activity_weather(aid), once=True)

        save(doc_path, doc)

        if fit_path.exists() and not had_fit:
            new_fits += 1
            print(f"  ↓ {base}  ({act.get('activityName', 'untitled')})")
        if set(doc) - known - {"summary"}:    # something new was fetched: pause
            time.sleep(RATE_LIMIT_SLEEP)

    # A file inside the window that Connect did not list was deleted there, or
    # had its start time edited (which gives it a new name). Nothing is removed
    # automatically: say so, and leave the decision to a human.
    for path in sorted(ACTIVITIES.rglob("*.json")):
        day = date.fromisoformat(f"{path.stem[:4]}-{path.stem[4:6]}-{path.stem[6:8]}")
        if day >= since and path.stem not in listed:
            print(f"  ? {path.stem} is on disk but no longer in Connect")

    return new_fits


# ── wellness ─────────────────────────────────────────────────────────────────

def chunks(start: date, end: date, days: int = 28) -> Iterator[tuple[date, date]]:
    """Yield (first, last) pairs covering start..end, each at most `days` long.

    Garmin's range endpoints reject long windows, so a backfill is cut up.
    """
    while start <= end:
        last = min(start + timedelta(days=days - 1), end)
        yield start, last
        start = last + timedelta(days=1)


def by_date(
    rows: list[dict] | None, key: str = "calendarDate", drop: tuple[str, ...] = ()
) -> dict[str, dict]:
    """Index a list of per-day rows by their date, leaving out the `drop` fields."""
    return {row[key]: {k: v for k, v in row.items() if k not in drop} for row in rows or []}


def strip_series(payload: dict | None) -> dict:
    """Drop the per-minute arrays from a sleep payload and keep the summary.

    get_sleep_data returns 70-145 KB a night, nearly all of it movement, SpO2
    and heart-rate samples. What is left — dailySleepDTO plus a few totals —
    is about 4 KB and holds every number Garmin shows on the sleep screen.
    """
    return {k: v for k, v in (payload or {}).items() if not isinstance(v, list)}


def fetch_ranges(c: Garmin, first: date, last: date) -> dict[str, dict[str, dict]]:
    """The three endpoints that cover a whole window in ONE call each.

    Returns {"hrv": {"2026-09-01": {...}, ...}, "race_predictions": {...}, "weight": {...}}.
    An endpoint that failed is simply absent, so the day files keep what they had.
    """
    s, e = first.isoformat(), last.isoformat()
    out: dict = {}
    fill(out, "hrv", f"hrv {s}..{e}",
         lambda: by_date((c.get_hrv_data_range(s, e) or {}).get("hrvSummaries")))
    # Each race-prediction row repeats the window it was asked for. Kept, that
    # would rewrite every day file every night as the window slides.
    fill(out, "race_predictions", f"race predictions {s}..{e}",
         lambda: by_date(c.get_race_predictions(startdate=s, enddate=e, _type="daily"),
                         drop=("fromCalendarDate", "toCalendarDate")))
    fill(out, "weight", f"weight {s}..{e}",
         lambda: by_date(c.get_weigh_ins(s, e).get("dailyWeightSummaries"), key="summaryDate"))
    return out


def fetch_day(c: Garmin, d: date, ranges: dict[str, dict[str, dict]]) -> None:
    """Write raw/wellness/YYYY/MM/YYYY-MM-DD.json: every source for one day, in one file."""
    iso = d.isoformat()
    path = partition(WELLNESS, d) / f"{iso}.json"
    doc = load(path)
    doc["date"] = iso

    fill(doc, "stats", f"stats {iso}", lambda: c.get_stats(iso))
    fill(doc, "sleep", f"sleep {iso}", lambda: strip_series(c.get_sleep_data(iso)))
    fill(doc, "training_status", f"training status {iso}", lambda: c.get_training_status(iso))
    # Every snapshot of the day, not just one: tables.py picks the morning one.
    fill(doc, "training_readiness", f"training readiness {iso}",
         lambda: c.get_training_readiness(iso))

    for key, rows in ranges.items():
        doc[key] = rows.get(iso)              # None on a day Garmin has no row for

    save(path, doc)


def fetch_wellness(c: Garmin, since: date) -> int:
    """Re-fetch every day from `since` to today. Overwrites existing files."""
    written = 0
    for first, last in chunks(since, date.today()):
        ranges = fetch_ranges(c, first, last)
        d = first
        while d <= last:
            fetch_day(c, d, ranges)
            written += 1
            d += timedelta(days=1)
            time.sleep(RATE_LIMIT_SLEEP)
    return written


# ── profile ──────────────────────────────────────────────────────────────────

def fetch_profile(c: Garmin) -> None:
    """Zones, thresholds and personal records, as Garmin has them right now.

    One file, overwritten each run — git history is the record of when a
    threshold changed.
    """
    doc = load(PROFILE_FILE)
    fill(doc, "hr_zones", "hr zones", lambda: c.get_heart_rate_zones())
    fill(doc, "power_zones", "power zones", lambda: c.get_power_zones())
    fill(doc, "lactate_threshold", "lactate threshold",
         lambda: c.get_lactate_threshold(latest=True))
    fill(doc, "cycling_ftp", "cycling ftp", lambda: c.get_cycling_ftp())
    fill(doc, "personal_records", "personal records", lambda: c.get_personal_record())
    save(PROFILE_FILE, doc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download from Garmin Connect into raw/.")
    parser.add_argument(
        "--since",
        type=date.fromisoformat,
        help=f"first day to fetch, YYYY-MM-DD (default: the last {REFRESH_DAYS} days)",
    )
    since = parser.parse_args().since or default_since()
    today = date.today()

    c = client()                              # raises if the token is missing or rejected

    print(f"Activities: {since} → {today}")
    n_fits = fetch_activities(c, since)

    print(f"Wellness:   {since} → {today}")
    n_days = fetch_wellness(c, since)

    print("Profile")
    fetch_profile(c)

    print(f"✓ {n_fits} new FIT files, {n_days} wellness days refreshed")
    if failed:
        print(f"! {len(failed)} calls failed and will be retried on the next run:")
        for label in failed:
            print(f"    {label}")


if __name__ == "__main__":
    main()
```

**Check it** — fetch yesterday and today, twice:

```bash
uv run python -m training_data.fetch --since $(date -v-1d +%F)
uv run python -m training_data.fetch --since $(date -v-1d +%F)
```

The first run downloads; the second must not. On 2026-10-04 the two runs printed:

```
Activities: 2026-10-03 → 2026-10-04
  ↓ 20261004-050508-24596344251  (Huyen Hoc Mon Running)
  ↓ 20261003-181256-24588920847  (Strength Training 💪🏻)
Wellness:   2026-10-03 → 2026-10-04
Profile
✓ 2 new FIT files, 2 wellness days refreshed
```

```
Activities: 2026-10-03 → 2026-10-04
Wellness:   2026-10-03 → 2026-10-04
Profile
✓ 0 new FIT files, 2 wellness days refreshed
```

Then look at the shape of what landed — the size of each key, in characters:

```bash
uv run python -c "
import glob, json
for pattern in ('raw/activities/**/*.json', 'raw/wellness/**/*.json'):
    p = sorted(glob.glob(pattern, recursive=True))[-1]
    print(p)
    print('  ', {k: len(json.dumps(v)) for k, v in json.load(open(p)).items()})"
```

```
raw/activities/2026/10/20261004-050508-24596344251.json
   {'detail': 8377, 'fit': 33, 'summary': 7241, 'weather': 435}
raw/wellness/2026/10/2026-10-04.json
   {'date': 12, 'hrv': 288, 'race_predictions': 133, 'sleep': 3845, 'stats': 3867, 'training_readiness': 3569, 'training_status': 2249, 'weight': 4}
```

Four keys on the activity, eight on the day, in alphabetical order because `save()` sorts them.
`sleep` under 4,000 characters confirms the arrays were stripped. `weight` is `null` (4
characters) on any day without a weigh-in.

A line starting with `?` means a session on disk is no longer in Garmin Connect — see Part 7.

### Step 3 — Backfill September

```bash
uv run python -m training_data.fetch --since 2026-09-01
```

About four minutes: 2.7 s per activity and 3.1 s per day. On 2026-10-04 it ended with
`✓ 42 new FIT files, 34 wellness days refreshed`. Your count of new files is the total minus
what is already on disk — the two September FITs in the repo and whatever Step 2 fetched are
recognised, not downloaded again.

If any call failed, the run still finishes and lists it under `! N calls failed and will be
retried on the next run`. Running the same command again fills those in.

**Check it:**

```bash
find raw/activities -name '*.fit'  | wc -l      # 44 on 2026-10-04
find raw/wellness   -name '*.json' | wc -l      # one per day since 1 September
uv run python -c "
import collections, glob, json
print(collections.Counter(
    json.load(open(p))['summary']['activityType']['typeKey']
    for p in glob.glob('raw/activities/**/*.json', recursive=True)))"
```

Expect seven sports, matching the table in Part 3.

To go further back later, it is the same command with an earlier date. Nothing else changes.

### Step 4 — `src/training_data/tables.py`

Each table is a dict: column name on the left, where it comes from on the right. A source takes
one of three forms.

```python
"avg_hr":       "summary.averageHR",              # copy that field
"duration_min": ("summary.duration", minutes),    # copy it through a unit conversion
"z0_min":       below_zone_1,                     # call a function with the whole document
```

`pick()` follows the dotted path and returns `None` the moment anything is missing, so a sport
without a field simply leaves the cell empty. That is the whole reason there is no sport
registry: a swim has no `avgPower`, so `avg_power` is blank on that row.

Create the file:

```python
"""Flatten raw/ JSON into the two CSVs Claude reads first.

Run with:  uv run python -m training_data.tables

Every column is a number Garmin computed. This module only selects, renames
and converts units — the exceptions are listed in the docstrings below.
Both tables are rebuilt from scratch on every run, so adding a column is one
line in a dict followed by a re-run.
"""

import csv
import json
from typing import Any

from training_data.config import ACTIVITIES, TABLES, WELLNESS


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


DAILY_COLUMNS: dict[str, Any] = {
    "date":                   "date",
    # sleep (last night)
    "sleep_score":            "sleep.dailySleepDTO.sleepScores.overall.value",
    "sleep_quality":          "sleep.dailySleepDTO.sleepScores.overall.qualifierKey",
    "sleep_h":                ("sleep.dailySleepDTO.sleepTimeSeconds", hours),
    "deep_h":                 ("sleep.dailySleepDTO.deepSleepSeconds", hours),
    "rem_h":                  ("sleep.dailySleepDTO.remSleepSeconds", hours),
    "light_h":                ("sleep.dailySleepDTO.lightSleepSeconds", hours),
    "awake_h":                ("sleep.dailySleepDTO.awakeSleepSeconds", hours),
    "sleep_need_h":           ("sleep.dailySleepDTO.sleepNeed.actual", min_to_hours),
    "nap_min":                ("sleep.dailySleepDTO.napTimeSeconds", minutes),
    "sleep_stress":           ("sleep.dailySleepDTO.avgSleepStress", round),
    # HRV
    "hrv":                    "hrv.lastNightAvg",
    "hrv_7d":                 "hrv.weeklyAvg",
    "hrv_status":             "hrv.status",
    "hrv_baseline_low":       "hrv.baseline.balancedLow",
    "hrv_baseline_high":      "hrv.baseline.balancedUpper",
    # the day
    "rhr":                    "stats.restingHeartRate",
    "rhr_7d":                 "stats.lastSevenDaysAvgRestingHeartRate",
    "stress_avg":             "stats.averageStressLevel",
    "stress_max":             "stats.maxStressLevel",
    "body_battery_high":      "stats.bodyBatteryHighestValue",
    "body_battery_low":       "stats.bodyBatteryLowestValue",
    "body_battery_at_wake":   "stats.bodyBatteryAtWakeTime",
    "steps":                  "stats.totalSteps",
    "intensity_min_moderate": "stats.moderateIntensityMinutes",
    "intensity_min_vigorous": "stats.vigorousIntensityMinutes",
    "active_kcal":            ("stats.activeKilocalories", round),
    "spo2_avg":               "stats.averageSpo2",
    "respiration_avg":        "stats.avgWakingRespirationValue",
    # readiness on waking
    "readiness":              "readiness.score",
    "readiness_level":        "readiness.level",
    "readiness_feedback":     "readiness.feedbackShort",
    "recovery_time_h":        ("readiness.recoveryTime", min_to_hours),
    # training status
    "training_status":        "status.trainingStatusFeedbackPhrase",
    "acute_load":             "status.acuteTrainingLoadDTO.dailyTrainingLoadAcute",
    "chronic_load":           "status.acuteTrainingLoadDTO.dailyTrainingLoadChronic",
    "acwr":                   "status.acuteTrainingLoadDTO.dailyAcuteChronicWorkloadRatio",
    "acwr_status":            "status.acuteTrainingLoadDTO.acwrStatus",
    "load_aerobic_low":       ("balance.monthlyLoadAerobicLow", round),
    "load_aerobic_high":      ("balance.monthlyLoadAerobicHigh", round),
    "load_anaerobic":         ("balance.monthlyLoadAnaerobic", round),
    "load_focus":             "balance.trainingBalanceFeedbackPhrase",
    # fitness
    "vo2max_run":             "training_status.mostRecentVO2Max.generic.vo2MaxPreciseValue",
    "vo2max_bike":            "training_status.mostRecentVO2Max.cycling.vo2MaxPreciseValue",
    "pred_5k":                ("race_predictions.time5K", clock),
    "pred_10k":               ("race_predictions.time10K", clock),
    "pred_hm":                ("race_predictions.timeHalfMarathon", clock),
    "pred_marathon":          ("race_predictions.timeMarathon", clock),
    "weight_kg":              ("weight.latestWeight.weight", kg),
}


# ── plumbing ─────────────────────────────────────────────────────────────────

def build_row(doc: dict, columns: dict[str, Any]) -> dict:
    """Apply a column map to one document."""
    row = {}
    for name, source in columns.items():
        if callable(source):
            row[name] = source(doc)
            continue
        path, convert = source if isinstance(source, tuple) else (source, None)
        value = pick(doc, path)
        row[name] = convert(value) if (convert and value is not None) else value
    return row


def write_table(prefix: str, rows: list[dict]) -> None:
    """One CSV per year: a finished year stops changing in git."""
    TABLES.mkdir(exist_ok=True)
    by_year: dict[str, list[dict]] = {}
    for row in rows:
        by_year.setdefault(row["date"][:4], []).append(row)

    for year, group in sorted(by_year.items()):
        out = TABLES / f"{prefix}-{year}.csv"
        with open(out, "w", newline="") as f:
            # lineterminator: csv defaults to \r\n, and .gitattributes wants LF.
            w = csv.DictWriter(f, fieldnames=list(group[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(group)
        print(f"  → {out.name}  ({len(group)} rows, {len(group[0])} columns)")


def main() -> None:
    activities = []
    for path in sorted(ACTIVITIES.rglob("*.json")):
        doc = json.loads(path.read_text())
        if "summary" in doc:                  # skips anything that is not ours
            activities.append(build_row(doc, ACTIVITY_COLUMNS))
    activities.sort(key=lambda r: (r["date"], r["start"]))

    days = [
        build_row(prepare_day(json.loads(path.read_text())), DAILY_COLUMNS)
        for path in sorted(WELLNESS.rglob("*.json"))
    ]

    write_table("activities", activities)
    write_table("daily", days)
    print("✓ tables rebuilt")


if __name__ == "__main__":
    main()
```

**Check it:**

```bash
uv run python -m training_data.tables
```

```
  → activities-2026.csv  (44 rows, 43 columns)
  → daily-2026.csv  (34 rows, 49 columns)
✓ tables rebuilt
```

Row counts must equal the two `find … | wc -l` counts from Step 3. Then read the last three
days against the Garmin Connect app:

```bash
uv run python -c "
import csv
for r in list(csv.DictReader(open('tables/daily-2026.csv')))[-3:]:
    print(r['date'], 'sleep', r['sleep_score'], '| hrv', r['hrv'], '| readiness', r['readiness'],
          '| acute', r['acute_load'], 'chronic', r['chronic_load'], '|', r['training_status'],
          '| HM', r['pred_hm'])"
```

```
2026-10-02 sleep 70 | hrv 67 | readiness 10 | acute 962 chronic 766 | UNPRODUCTIVE_4 | HM 2:13:07
2026-10-03 sleep 71 | hrv 47 | readiness 35 | acute 820 chronic 749 | UNPRODUCTIVE_4 | HM 2:13:20
2026-10-04 sleep 57 | hrv 51 | readiness 52 | acute 876 chronic 769 | UNPRODUCTIVE_4 | HM 2:13:18
```

The `readiness 52` on 4 October is the 04:05 snapshot, not the 07:35 one (32) — Fact 1 working.

And confirm the zone columns add up, which is Fact 2 working:

```bash
uv run python -c "
import csv
rows = list(csv.DictReader(open('tables/activities-2026.csv')))
print(max(abs(sum(float(r[f'z{i}_min']) for i in range(6)) - float(r['duration_min'])) for r in rows))"
```

Expect `0.2` or less: a rounding remainder, in minutes.

### Step 5 — `src/training_data/fit.py`

The FIT reader. `read_fit()` is the function you already had in `decode.py`; everything else
here prints.

It is a tool for Claude, not a pipeline stage. Nothing calls it during a sync.

```python
"""Read one FIT file on demand.

Run with:  uv run python -m training_data.fit <activity id or path> [--records N]

In code:   from training_data.fit import read_fit
           records = read_fit(path)["record_mesgs"]     # every sample the watch wrote

Nothing here is stored. The FIT stays the single source of truth for laps,
swim lengths, strength sets and the full-resolution stream.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from garmin_fit_sdk import Decoder, Stream

from training_data.config import ACTIVITIES

LAP_COLUMNS = [
    "total_timer_time", "total_distance", "avg_heart_rate", "max_heart_rate",
    "enhanced_avg_speed", "avg_power", "normalized_power", "avg_cadence",
    "total_ascent", "num_active_lengths", "total_strokes", "intensity", "lap_trigger",
]
LENGTH_COLUMNS = [
    "length_type", "total_timer_time", "swim_stroke", "total_strokes",
    "avg_speed", "avg_swimming_cadence",
]
SET_COLUMNS = ["set_type", "category", "repetitions", "weight", "duration"]
RECORD_COLUMNS = [
    "heart_rate", "enhanced_speed", "power", "cadence",
    "enhanced_altitude", "enhanced_respiration_rate", "temperature",
]

# Garmin closes the top power zone with a boundary of 4000 W. Treat it as "no upper limit".
OPEN_ENDED = 4000


def read_fit(path: Path | str) -> dict:
    """Decode a FIT file into a dict of message lists.

    Keys look like 'session_mesgs', 'lap_mesgs', 'record_mesgs', 'length_mesgs'
    (pool swims) and 'set_mesgs' (strength). 'record_mesgs' is the stream: one
    entry per sample, usually every second, but every ~4 s for badminton.
    """
    messages, errors = Decoder(Stream.from_file(str(path))).read(
        apply_scale_and_offset=True,      # raw integers -> real units (watts, bpm)
        convert_datetimes_to_dates=True,  # FIT timestamps -> Python datetimes
        expand_components=True,           # unpack packed fields
        merge_heart_rates=True,           # fold separate HR messages into records
    )
    if errors:
        raise RuntimeError(f"{Path(path).name}: {errors}")
    return messages


def find(target: str) -> Path:
    """Accept a path, or an activity id as printed in tables/activities-*.csv."""
    if Path(target).exists():
        return Path(target)
    matches = sorted(ACTIVITIES.rglob(f"*-{target}.fit"))
    if not matches:
        sys.exit(f"no FIT file found for '{target}'")
    return matches[0]


def text(value: Any) -> str:
    """Format one value for printing."""
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, datetime):           # FIT timestamps are UTC
        return f"{value:%Y-%m-%d %H:%M:%S} UTC"
    if isinstance(value, list):               # e.g. a set's exercise category
        return "/".join(dict.fromkeys(str(v) for v in value))
    return str(value)


def print_table(title: str, rows: list[dict], columns: list[str]) -> None:
    """Print rows as an aligned table, dropping columns that are empty in every row."""
    columns = [c for c in columns if any(r.get(c) is not None for r in rows)]
    if not rows or not columns:
        return
    cells = [[str(i + 1)] + [text(r.get(c)) for c in columns] for i, r in enumerate(rows)]
    header = ["#"] + columns
    widths = [max(len(header[i]), *(len(row[i]) for row in cells)) for i in range(len(header))]

    print(f"\n{title}")
    for row in [header] + cells:
        print("  " + "  ".join(cell.rjust(width) for cell, width in zip(row, widths)))


def print_fields(title: str, mesg: dict) -> None:
    """Print every named field of one message, skipping GPS corners and blanks."""
    print(f"\n{title}")
    for key, value in mesg.items():
        # Unnamed fields have integer keys; _lat/_long are raw GPS units.
        if not isinstance(key, str) or key.endswith(("_lat", "_long")) or value is None:
            continue
        print(f"  {key:36s} {text(value)}")


def print_zones(messages: dict) -> None:
    """The watch's own time-in-zone totals for the whole session.

    Files also carry one entry per lap, so take the one that refers to the
    session. HR has one more bucket than it has boundaries: the first is time
    BELOW zone 1, which Connect's five-zone summary leaves out.
    """
    entry = next(
        (m for m in messages.get("time_in_zone_mesgs", []) if m.get("reference_mesg") == "session"),
        None,
    )
    if not entry:
        return
    for name, bounds_key, times_key in (
        ("HR zones (bpm)", "hr_zone_high_boundary", "time_in_hr_zone"),
        ("Power zones (W)", "power_zone_high_boundary", "time_in_power_zone"),
    ):
        bounds, times = entry.get(bounds_key), entry.get(times_key)
        if not bounds or not times:
            continue
        print(f"\n{name}")
        for i, seconds in enumerate(times):
            low = bounds[i - 1] if i > 0 else 0
            high = bounds[i] if i < len(bounds) else None
            if low is None or low >= OPEN_ENDED:      # unused slot: runs have 5 power zones
                continue
            top = high is None or high >= OPEN_ENDED
            label = f">{low}" if top else f"{low}-{high}"
            print(f"  {label:>10}  {seconds / 60:6.1f} min")


def stream(records: list[dict], every_s: int) -> list[dict]:
    """Average the stream into buckets of `every_s` seconds of ELAPSED time.

    Bucketing by list position would be wrong: samples are not evenly spaced
    (badminton records every ~4 s), so 60 records is not one minute.
    """
    usable = [r for r in records if r.get("timestamp")]
    if not usable:
        return []
    t0 = usable[0]["timestamp"]
    buckets: dict[int, list[dict]] = {}
    for r in usable:
        buckets.setdefault(int((r["timestamp"] - t0).total_seconds() // every_s), []).append(r)

    rows = []
    for n in sorted(buckets):
        elapsed = n * every_s
        row: dict = {"elapsed": f"{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}"}
        for field in RECORD_COLUMNS:
            values = [r[field] for r in buckets[n] if r.get(field) is not None]
            row[field] = sum(values) / len(values) if values else None
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Print one FIT file as text.")
    parser.add_argument("target", help="activity id, or path to a .fit file")
    parser.add_argument(
        "--records", type=int, metavar="N",
        help="also print the stream, averaged every N seconds (1 = every sample)",
    )
    args = parser.parse_args()

    path = find(args.target)
    messages = read_fit(path)

    print(f"# {path.name}")
    for session in messages.get("session_mesgs", []):
        print_fields("Session", session)
    print_zones(messages)
    print_table("Laps", messages.get("lap_mesgs", []), LAP_COLUMNS)
    print_table("Lengths", messages.get("length_mesgs", []), LENGTH_COLUMNS)
    print_table("Sets", messages.get("set_mesgs", []), SET_COLUMNS)
    if args.records:
        rows = stream(messages.get("record_mesgs", []), args.records)
        print_table(f"Stream, every {args.records} s", rows, ["elapsed"] + RECORD_COLUMNS)


if __name__ == "__main__":
    main()
```

**Check it** — one of each sport, by the `activity_id` from the table:

```bash
uv run python -m training_data.fit 24588920847                 # strength: a Sets table
uv run python -m training_data.fit 24578694322                 # swim: a Lengths table
uv run python -m training_data.fit 24572694492                 # ride: Power zones
uv run python -m training_data.fit 24596344251 --records 600   # long run: a 10-minute stream
```

The strength session ends with its sets:

```
Sets
   #  set_type  category  repetitions  weight  duration
   1    active   warm_up                          65.36
   2    active   push_up           20             51.54
   3    active     squat           20    0.00     45.96
   4      rest                                    60.00
```

The ride shows the seven HR buckets and the power zones the watch used:

```
HR zones (bpm)
       0-124    27.9 min
     124-138    39.5 min
     138-152    12.9 min
     …
Power zones (W)
         0-0     0.0 min
        0-90    36.4 min
      90-122    24.8 min
     …
        >245     0.1 min
```

And the long run's stream, every 600 s:

```
Stream, every 600 s
   #  elapsed  heart_rate  enhanced_speed   power  cadence  enhanced_altitude  enhanced_respiration_rate  temperature
   1  0:00:00      150.65            2.20  193.50    87.86              13.07                      33.91        30.01
   2  0:10:00      157.69            2.13  188.23    86.91              12.99                      34.98        30.18
   …
  12  1:50:00      162.67            2.29  210.93    90.50               8.66                      35.51        30.00
```

All 44 files decoded without error in 6.6 s; the slowest took 0.5 s.

### Step 6 — `CLAUDE.md`, `ATHLETE.md`, `README.md`

**`CLAUDE.md`**, at the repo root. This is what makes the data easy for Claude to reach: Claude
Code reads it at the start of every session in this folder.

````markdown
# CLAUDE.md — coaching context

You are my endurance coach. I am training for triathlon, working toward an Ironman, and I play
badminton three times a week. Read `ATHLETE.md` first for goals, races and constraints, then the
newest entries in `LOG.md` for what we covered last time.

## Is the data fresh?

A launchd job syncs once a day at 22:30. Before a review, check:

```bash
tail -n 1 tables/daily-*.csv | cut -c1-40      # the last day in the table
git log -1 --format=%cr -- tables               # when the tables were last committed
```

If today is missing, or I mention a session you cannot see, refresh first:

```bash
uv run python -m training_data.fetch && uv run python -m training_data.tables
```

That takes about a minute and updates the files without committing anything. Committing is the
job of `./bin/sync.sh` — the nightly run, or me running it by hand. Do not commit or push data
yourself. If the fetch prints a line starting with `?`, tell me: a session on disk is no longer in
Garmin Connect.

## Where the data lives

| path | what it holds | use it for |
|---|---|---|
| `tables/activities-YYYY.csv` | one row per session | **start here** for anything about training |
| `tables/daily-YYYY.csv` | one row per day: sleep, HRV, readiness, training status, load | **start here** for recovery and trends |
| `raw/profile.json` | HR and power zones, lactate threshold, FTP, personal records | current thresholds |
| `raw/activities/YYYY/MM/<stamp>-<id>.json` | everything Connect knows about one session | when a table row is not enough |
| `raw/activities/YYYY/MM/<stamp>-<id>.fit` | the original FIT file | laps, lengths, sets, the per-second stream |
| `raw/wellness/YYYY/MM/YYYY-MM-DD.json` | everything for one day, including every readiness snapshot | one day in detail |

Read the tables first and open raw files one at a time. A month of raw JSON is over 1 MB; the two
tables for the same month are under 20 KB.

## Looking inside a session

A `.fit` file is binary — do not open it with Read. Decode it:

```bash
uv run python -m training_data.fit <activity_id>                # session, zones, laps, lengths, sets
uv run python -m training_data.fit <activity_id> --records 60   # plus the stream, averaged per minute
```

For real analysis — drift, pacing, power distribution — load every sample into pandas:

```bash
uv run python -c "
import pandas as pd
from training_data.fit import find, read_fit
df = pd.DataFrame(read_fit(find('<activity_id>'))['record_mesgs'])
print(df[['heart_rate', 'enhanced_speed', 'power']].describe())"
```

## Reading the numbers

Every number is Garmin's own; nothing is recomputed here. An empty cell means Garmin has no
value. It does not mean zero.

**Sessions (`activities`)**

- `load` is Garmin's training load for the session. `te_aerobic` and `te_anaerobic` are Training
  Effect, 0–5.
- `z1_min` … `z5_min` are minutes in Garmin's five HR zones. `z0_min` is the time below zone 1 —
  the one derived column, duration minus the five zones. The six add up to `duration_min`.
- `duration_min` is the length of the session. `moving_min` only means something for runs, rides
  and walks.
- `speed_kmh`: run pace in min/km is `60 / speed_kmh`; swim pace per 100 m is `6 / speed_kmh`.
- `avg_power` and `norm_power` are running power on runs and a power meter on rides. `tss` and
  `intensity_factor` exist only on rides.
- `cadence` is steps per minute on foot, rpm on the bike, strokes per minute in the pool.
- `rpe` is my rating on Garmin's 10–100 scale (30 means 3/10). `feel` runs 0 very weak, 25 weak,
  50 normal, 75 strong, 100 very strong.
- `weather_*` is the weather-station reading at the start. It is blank for indoor sessions.

**Days (`daily`)**

- `readiness` is the earliest wake-up snapshot of the day: the score I woke up with. It drops
  after training. Every snapshot is in the raw day file under `training_readiness`.
- `acute_load` is Garmin's short-term load, `chronic_load` its long-term baseline, and `acwr`
  their ratio.
- `load_aerobic_low`, `load_aerobic_high` and `load_anaerobic` are the four-week load split.
  `load_focus` is Garmin's verdict on the balance.
- `vo2max_run` and `vo2max_bike` are the most recent estimates as of that day. `pred_*` are race
  predictions as h:mm:ss.
- `sleep_*` describes the night that ended on that date. `hrv` is the overnight average in ms;
  `hrv_baseline_low` to `hrv_baseline_high` is my balanced range.

**FIT units.** The `fit` command prints Garmin's raw fields: speed in m/s, distance in m, times in
seconds, timestamps in UTC (I am UTC+7). For running, `avg_cadence` is strides per minute —
double it for steps — and `avg_step_length` and `avg_vertical_oscillation` are in mm.

## Working style

- Trends over single days. Daily HRV and readiness are noisy; use 7-day windows.
- Check the zone columns before commenting on intensity. Grey-zone drift is invisible in volume
  alone.
- Badminton is HR-only: no power, no meaningful pace. Treat it as load, not as a quality session.
- It is hot and humid here: outdoor sessions start at 25–32 °C. Read heart rate and pace against
  `weather_feels_c` before calling a session a bad one.
- Note when equipment changed. It creates step changes that look like fitness changes.
- At the end of a review, append what we found and agreed to `LOG.md` under a dated heading. The
  next sync commits it.

## Housekeeping

- `raw/` and `tables/` are generated. Never edit them by hand. To add a column, add a line to
  `src/training_data/tables.py` and re-run `uv run python -m training_data.tables`.
- Data is committed only by `./bin/sync.sh`, and only on `main`.
````

**`ATHLETE.md`.** Replace the `## Thresholds` and `## HR zones (run)` sections — both are stale
against Garmin — with a pointer:

```markdown
## Thresholds and zones
Garmin is the source of truth. `raw/profile.json` holds the current HR zones per sport, power
zones, lactate threshold and FTP, refreshed on every sync. They are not copied here, because
copies go stale.

Not tested yet: bike FTP (Garmin's 200 W is a placeholder) and swim CSS.
```

While you are in the file, bring `## Current block` up to date: it still describes only the
18 October half marathon, and Claude reads it as the goal.

**`README.md`.** Replace everything from the status line down to, but not including,
`## File conventions`:

````markdown
> **Status:** working end to end. `bin/sync.sh` fetches from Garmin Connect,
> rebuilds the tables and commits the data; launchd runs it daily at 22:30.

## Layout

```
.
├── .gitattributes           # file-type handling (binary / line endings)
├── .gitignore               # Python, env, sync logs and macOS artifacts
├── .python-version          # 3.13, read by uv
├── pyproject.toml           # project metadata and dependencies
├── uv.lock                  # pinned dependency resolution
├── CLAUDE.md                # coaching context and data map, read by Claude Code
├── ATHLETE.md               # goals, races, schedule, injuries, equipment
├── LOG.md                   # coaching log, newest entries first
├── .github/
│   └── workflows/
│       ├── label-sync.yml   # sync label definitions from the central manifest
│       ├── path-labeler.yml # label PRs by changed paths
│       └── size-labeler.yml # label PRs by diff size
├── bin/
│   ├── login.py             # one-off interactive Garmin login
│   ├── sync.sh              # fetch -> tables -> commit -> push
│   └── bootstrap.sh         # one-time machine setup, installs the launchd job
├── etc/
│   └── com.enri.garmin-sync.plist.tmpl
├── docs/                    # implementation plans; superseded ones in archive/
├── src/
│   └── training_data/
│       ├── config.py        # paths and tuning constants
│       ├── garmin.py        # authenticated client + retry wrapper
│       ├── fetch.py         # Garmin Connect -> raw/
│       ├── tables.py        # raw/ JSON -> tables/ CSVs
│       └── fit.py           # read one FIT file on demand
├── raw/
│   ├── activities/YYYY/MM/  # <stamp>-<id>.fit and <stamp>-<id>.json
│   ├── wellness/YYYY/MM/    # one JSON per day, all sources merged
│   └── profile.json         # zones, thresholds, personal records
└── tables/                  # activities-YYYY.csv, daily-YYYY.csv
```

Data flows one way. `raw/` is what Garmin returned, untouched; `tables/` is
rebuilt from it on every run, so it can always be deleted and regenerated.
Every number in both is Garmin's own — nothing is recomputed here.

Everything under `raw/` is partitioned as `YYYY/MM/` — GitHub caps a single
directory at 3,000 entries, and a flat folder would hit that in about two years.

## Toolchain

Python 3.13 (pinned in `.python-version`), managed with
[uv](https://docs.astral.sh/uv/). Dependencies are declared in
`pyproject.toml` and locked in `uv.lock`:

| Package | Used for |
| --- | --- |
| `garminconnect` | Garmin Connect API client (pinned to `0.3.15`) |
| `garmin-fit-sdk` | decoding `.fit` files on demand |
| `pandas` | analysis sessions; the pipeline itself does not import it |

```bash
./bin/bootstrap.sh                    # once per machine: deps, Garmin login, launchd job
./bin/sync.sh                         # fetch -> tables -> commit -> push
./bin/sync.sh --since 2026-09-01      # backfill from a date
uv run python -m training_data.fit <activity id> [--records N]
```

`bin/login.py` writes an OAuth token to `~/.garminconnect/`; the password is
never stored. Every later run reads that token, so no credentials live in the
repo or the environment.

## Pipeline

| Stage | Module | What it does |
| --- | --- | --- |
| Auth | `bin/login.py` | Interactive login, once per machine. Caches an OAuth token in `~/.garminconnect/`. |
| Fetch | `fetch.py` | Downloads new FIT files, each activity's Connect detail and weather, a rolling 14-day window of daily wellness, and the current zones and thresholds into `raw/`. |
| Tables | `tables.py` | Flattens `raw/` JSON into `tables/activities-YYYY.csv` and `tables/daily-YYYY.csv`. |
| Sync | `bin/sync.sh` | Runs both, then commits `raw/`, `tables/` and `LOG.md` on `main` and pushes. |
| Schedule | launchd | Runs `bin/sync.sh` daily at 22:30; a missed run fires on wake. |

`fit.py` is not a stage. It reads one FIT file when asked, and prints the
session, zones, laps, swim lengths, strength sets and, optionally, the stream.

Tuning constants live at the top of `config.py`:

| Constant | Value | Why |
| --- | --- | --- |
| `REFRESH_DAYS` | 14 | Garmin revises history — sleep scores recalculate, training status lags a day, sessions get renamed. Every run re-fetches this window. |
| `RATE_LIMIT_SLEEP` | 1.5s | Garmin rate-limits aggressively; `garmin.py` also retries with exponential backoff. |

There is no state file. An activity's JSON records what has been fetched for
it, so an interrupted run finishes itself the next time.

## Athlete context

| File | Read by | Holds |
| --- | --- | --- |
| `CLAUDE.md` | Claude Code | the coaching brief: where the data lives and how to read it |
| `ATHLETE.md` | humans and Claude | race block, schedule, injury history, equipment |
| `LOG.md` | humans and Claude | session-by-session review notes, newest first |
| `raw/profile.json` | Claude | HR and power zones, lactate threshold, FTP and personal records, as Garmin has them |

Thresholds and zones are not written down by hand anywhere: Garmin is the
source of truth, and `raw/profile.json` is refreshed on every sync.
````

Two smaller edits further down:

- In the `## File conventions` table, the "Where it applies" column for `*.csv` becomes
  `tables/`, and for `*.json` becomes `raw/`.
- Under `## Workflow`, add: "Data is the exception. `bin/sync.sh` commits `raw/`, `tables/` and
  `LOG.md` straight to `main` as `chore(data): sync YYYY-MM-DD`."

**claude.ai.** In your coaching Project, connect this repo through the GitHub integration and
select only `ATHLETE.md`, `LOG.md`, `raw/profile.json` and `tables/*.csv`. Leave the rest of
`raw/` unselected: the FITs are binary and a month of raw JSON is over 1 MB. Press **Sync now** when you want the
Project to see the latest push.

### Step 7 — `bin/sync.sh`

The one command. launchd runs it; you run it. Create `bin/sync.sh`:

```bash
#!/usr/bin/env bash
#
# Garmin sync: fetch -> tables -> commit -> push.
#
# Run by launchd once a day, and by hand whenever you want fresh data:
#   ./bin/sync.sh                      # the usual 14-day refresh
#   ./bin/sync.sh --since 2026-09-01   # backfill from a date
#
# set -e : abort on any command failing
# set -u : abort on an undefined variable
# set -o pipefail : a failure anywhere in a pipe fails the whole pipe
set -euo pipefail

# Resolve the repo root from this script's own location, so it works
# regardless of what directory it is invoked from.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

UV=/opt/homebrew/bin/uv           # absolute path: launchd has almost no PATH
DATA=(raw tables LOG.md)          # the only paths this script ever commits
export PYTHONUNBUFFERED=1         # so .sync.log fills as the run goes, not at the end

# Under launchd nobody is watching a terminal, so a failed run says so on screen.
fail() {
  echo "✗ $1" >&2
  osascript -e "display notification \"$1\" with title \"training-data sync\"" || true
  exit 1
}
trap 'fail "Garmin sync failed. See .sync.err"' ERR

echo "── sync $(date '+%F %T') ──"

"$UV" run python -m training_data.fetch "$@"
"$UV" run python -m training_data.tables

# A rebase that stopped on a conflict leaves the repo on no branch at all, and
# every later run would quietly skip the commit. Refuse loudly instead.
branch="$(git branch --show-current)"
if [[ -z "$branch" || -d "$(git rev-parse --git-path rebase-merge)" ]]; then
  fail "Repo is mid-rebase or on a detached HEAD. Fix it by hand."
fi

# Data only ever lands on main. On a feature branch the files are refreshed on
# disk and left uncommitted; the next run on main picks them up.
if [[ "$branch" != "main" ]]; then
  echo "· on '$branch', not main: data refreshed, commit skipped"
  exit 0
fi

git add -- "${DATA[@]}"
if git diff --cached --quiet -- "${DATA[@]}"; then
  echo "· nothing new"
else
  # The trailing paths make this commit ONLY the data, even if you have other
  # changes staged.
  git commit --quiet -m "chore(data): sync $(date +%F)" -- "${DATA[@]}"
fi

# Push whenever main is ahead of GitHub. That includes a commit an earlier run
# made but could not push, so a network blip repairs itself the next day.
git pull --quiet --rebase --autostash     # pick up code merged on GitHub first
if [[ -n "$(git rev-list '@{u}..HEAD')" ]]; then
  git push --quiet
  echo "✓ pushed $(date +%F)"
fi
```

```bash
chmod +x bin/sync.sh
```

Five details worth knowing:

- `git commit … -- raw tables LOG.md` commits *only* those paths, whatever else you have staged.
- `git pull --rebase --autostash` runs before the push because code PRs merged on GitHub leave
  your local `main` behind. Side effect: a change you had *staged* comes back *unstaged*.
- It pushes whenever `main` is ahead of GitHub, not only after a fresh commit. So if a push fails
  — no network at 22:30 — the next run sends that commit along.
- If a rebase ever stops on a conflict (say `LOG.md` was edited on GitHub and here), the repo is
  left on no branch. Every later run then fails with a notification rather than quietly
  skipping the commit. To recover: `git rebase --abort`, reconcile the file, run it again.
- The commit message `chore(data): sync …` keeps roughly 350 automated commits a year filterable:
  `git log --invert-grep --grep='^chore(data)'` shows only your own.

**How this was tested.** The fetch-and-tables half ran for real, on a feature branch — that is
the output just below. The git half ran in a throwaway repository with a stand-in for `uv`,
across seven cases: unrelated changes staged and unstaged; nothing new; a code commit already on
the remote; a feature branch; a failed fetch; a failed push that recovers on the next run; and
a `LOG.md` conflict. It has never pushed to your GitHub repo. Your first run on `main` is that
test.

**Check it,** first on the feature branch you are on:

```bash
./bin/sync.sh
```

```
── sync 2026-10-04 22:20:51 ──
Activities: 2026-09-21 → 2026-10-04
Wellness:   2026-09-21 → 2026-10-04
Profile
✓ 0 new FIT files, 14 wellness days refreshed
  → activities-2026.csv  (44 rows, 43 columns)
  → daily-2026.csv  (34 rows, 49 columns)
✓ tables rebuilt
· on 'feat/sync-script', not main: data refreshed, commit skipped
```

Then merge the PR, and make the first data commit from `main`:

```bash
git switch main && git pull
./bin/sync.sh          # ends with: ✓ pushed 2026-10-04
./bin/sync.sh          # ends with: · nothing new
git log --oneline -1   # chore(data): sync 2026-10-04
```

That second `· nothing new` is Fact 6 working: with unsorted keys it would have found some 30
changed files and committed again.

If the push asks for credentials, fix that now — `gh auth login`, or check the keychain helper —
because under launchd there is no terminal to answer the prompt.

### Step 8 — Schedule it with launchd

**This step was not run on your machine.** Both files were syntax-checked, and the plist that
the template generates passed `plutil -lint`, but nothing was installed. The `kickstart` in the
check below is the real test.

Create `etc/com.enri.garmin-sync.plist.tmpl` (run `mkdir -p etc` first: Step 0 removed the
placeholder that kept the folder). `__REPO__` is substituted at install time, which is why this
is a template and the generated plist is not tracked anywhere.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.enri.garmin-sync</string>

  <key>ProgramArguments</key>
  <array>
    <string>__REPO__/bin/sync.sh</string>
  </array>

  <!-- 22:30 daily: an hour after the latest regular session ends, so one run
       captures the whole day. If the Mac is asleep, launchd runs it on wake.
       For a second run, replace this <dict> with an <array> of two <dict>s. -->
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>22</integer>
    <key>Minute</key><integer>30</integer>
  </dict>

  <key>StandardOutPath</key><string>__REPO__/.sync.log</string>
  <key>StandardErrorPath</key><string>__REPO__/.sync.err</string>

  <key>WorkingDirectory</key><string>__REPO__</string>

  <!-- launchd gives a nearly empty environment. Without this, git and uv
       aren't found and the job fails with a confusing "command not found". -->
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
</dict>
</plist>
```

Create `bin/bootstrap.sh`, which installs it:

```bash
#!/usr/bin/env bash
#
# One-time setup on a machine: dependencies, Garmin login, and the daily job.
# Usage: ./bin/bootstrap.sh        (safe to run again — it replaces the agent)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

REPO="$(pwd)"
LABEL="com.enri.garmin-sync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

command -v uv >/dev/null || { echo "Install uv first: brew install uv"; exit 1; }

echo "→ Installing Python dependencies from the lockfile"
uv sync --frozen        # --frozen = install exactly what's locked, like npm ci

echo "→ Checking Garmin authentication"
if [[ ! -f "$HOME/.garminconnect/garmin_tokens.json" ]]; then
  echo "  No token found. Starting interactive login (expect an MFA prompt)."
  uv run python bin/login.py
else
  echo "  Existing token found."
fi

echo "→ Installing the launchd agent"
mkdir -p "$HOME/Library/LaunchAgents"
# The template holds __REPO__ placeholders; the real plist needs absolute paths.
sed "s|__REPO__|$REPO|g" "etc/$LABEL.plist.tmpl" > "$PLIST"

# bootstrap/bootout are the modern replacements for load/unload.
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "✓ Done. Syncing daily at 22:30."
echo "  Run now:  launchctl kickstart -p gui/$(id -u)/$LABEL"
```

```bash
chmod +x bin/bootstrap.sh
./bin/bootstrap.sh
```

Your dotfiles `.gitignore` already excludes both the generated plist and `~/.garminconnect/`.

**Check it:**

```bash
launchctl kickstart -p gui/$(id -u)/com.enri.garmin-sync     # run it now
tail -20 .sync.log                                           # same output as running by hand
launchctl print gui/$(id -u)/com.enri.garmin-sync | grep -E "state|last exit"
```

`last exit code = 0` is what you want. `.sync.log` and `.sync.err` are already in `.gitignore`.

The commands you will actually use:

```bash
./bin/sync.sh                                                # fresh data now
tail -50 .sync.err                                           # why did last night's run fail?
launchctl bootout gui/$(id -u)/com.enri.garmin-sync          # stop the daily job
./bin/bootstrap.sh                                           # start it again
```

---

## Part 6 — Verification

```bash
# 1. The pipeline, end to end, twice. The second run must change nothing.
./bin/sync.sh
./bin/sync.sh                      # · nothing new

# 2. Row counts equal file counts.
find raw/activities -name '*.json' | wc -l
find raw/wellness   -name '*.json' | wc -l
wc -l tables/*.csv                 # each is its count + 1 header line

# 3. Every FIT decodes.
for f in $(find raw/activities -name '*.fit'); do
  uv run python -m training_data.fit "$f" > /dev/null || echo "FAILED: $f"
done

# 4. The daily job ran.
launchctl print gui/$(id -u)/com.enri.garmin-sync | grep "last exit"
```

What "good" looks like: seven sports in `activities-2026.csv`; one row per day in
`daily-2026.csv` with no gaps; `readiness` matching the score you woke up with; zone columns
summing to the duration; a `chore(data)` commit each day.

Then the real test. Open Claude Code in the repo:

```bash
cd ~/Personal/Projects/training-data && claude
```

and ask for a review of last week. It should check freshness, answer from `tables/`, decode at
least one FIT without being told how, and append to `LOG.md`.

---

## Part 7 — Open items

- **Deleted or re-timed sessions are not removed.** If you delete a duplicate recording in
  Connect, its files stay in `raw/` and its row stays in the table, counting that load twice.
  Editing a start time has the same effect, because the file name changes. `fetch` prints
  `? <name> is on disk but no longer in Connect` for anything inside the window; delete that
  `.fit` and `.json` pair by hand and the next run drops the row. Nothing is deleted
  automatically, on purpose.
- **Multisport.** You have no brick or race on file yet, so parent/child handling is untested.
  `get_activity` exposes `isMultiSportParent` and `childIds`. After the first brick, check
  whether the table shows the parent, the legs, or both, before trusting that week's totals.
- **Cycling FTP disagrees with itself.** `get_power_zones` says 200 W, which is a default;
  `get_cycling_ftp` is empty; and your ride FITs compute TSS and IF against 163 W. Until you test
  it, read `tss` and `intensity_factor` as provisional.
- **Lactate-threshold speed** (`0.3139`) still has an ambiguous unit, as v3 noted. HR (194) and
  power (278 W) from the same payload are sound.
- **Swim detail.** Your three pool sessions are short on active lengths (150 m in the latest),
  so `swolf` and `strokes_per_length` rest on very few lengths for now.
- **Garmin's own estimates move.** Half-marathon prediction went from 2:12:02 on 1 September to
  2:13:18 on 4 October, and training status was `UNPRODUCTIVE` on 9 of the 34 days. That is a
  coaching question, and the first thing the tables let you ask.

---

## Appendix — Extending it

**A new column.** Add one line to `ACTIVITY_COLUMNS` or `DAILY_COLUMNS` in `tables.py` and run
`uv run python -m training_data.tables`. No re-fetch. To find the path, open one raw JSON file.

**A new per-day endpoint.** Add one `fill(doc, "key", …)` line to `fetch_day()` in `fetch.py`,
then backfill with `--since`.

**A second daily run.** In the plist template, replace the `StartCalendarInterval` `<dict>` with
an `<array>` holding two `<dict>`s, then run `./bin/bootstrap.sh` again.

**Lap-level text for claude.ai.** claude.ai sees the tables but cannot decode a FIT. If session
rows prove too thin there, have `sync.sh` save `fit.py`'s output next to each new FIT as a
`.txt` file.

**The Garmin calendar.** `get_scheduled_workouts(year, month)` returns races and planned
sessions, at about 50 KB a month untrimmed. Worth adding when you want planned-versus-done.
