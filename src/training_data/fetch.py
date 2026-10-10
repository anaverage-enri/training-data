"""Download from Garmin Connect into raw/.

Run with:  uv run python -m training_data.fetch [--since YYYY-MM-DD]
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

    print(f"✓ {n_fits} new FIT files, {n_days} wellness days refreshed")
    if failed:
        print(f"! {len(failed)} calls failed and will be retried on the next run:")
        for label in failed:
            print(f"    {label}")


if __name__ == "__main__":
    main()

