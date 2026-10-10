"""Download from Garmin Connect into raw/.

Run with:  uv run python -m training_data.fetch
"""

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
    ACTIVITY_LOOKBACK_DAYS,
    RATE_LIMIT_SLEEP,
    RAW,
    WELLNESS_WINDOW_DAYS,
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


def fetch_wellness(c: Garmin, days: int = WELLNESS_WINDOW_DAYS) -> int:
    """Re-fetch a rolling window of daily wellness. Overwrites existing files."""
    written = 0

    for offset in range(days):
        d = date.today() - timedelta(days=offset)
        iso = d.isoformat()

        print(f"  ↓ {iso}")

        # Each endpoint is a separate API call. Bundle into one file per day
        # so decode/rollup only ever opens one file per date.
        payload = {
            "date": iso,
            "stats": with_retry(lambda: c.get_stats(iso), label=f"stats {iso}"),
            "sleep": with_retry(lambda: c.get_sleep_data(iso), label=f"sleep {iso}"),
            "hrv": with_retry(lambda: c.get_hrv_data(iso), label=f"hrv {iso}"),
            "body_battery": with_retry(
                lambda: c.get_body_battery(iso, iso), label=f"body battery {iso}"
            ),
            "training_readiness": with_retry(
                lambda: c.get_training_readiness(iso), label=f"training readiness {iso}"
            ),
            "training_status": with_retry(
                lambda: c.get_training_status(iso), label=f"training status {iso}"
            ),
            "max_metrics": with_retry(
                lambda: c.get_max_metrics(iso), label=f"max metrics {iso}"
            ),
        }

        out = partition(RAW / "wellness", d)
        (out / f"{iso}.json").write_text(json.dumps(payload, indent=2))
        written += 1
        time.sleep(RATE_LIMIT_SLEEP)

    return written

def main() -> None:
    c = client()

    # -1 because get_activities_by_date is inclusive on BOTH ends:
    # today-29 .. today is 30 days, not 31.
    since = date.today() - timedelta(days=ACTIVITY_LOOKBACK_DAYS - 1)

    print(f"Activities: {since} → {date.today()} ({ACTIVITY_LOOKBACK_DAYS} days)")
    n_act = fetch_activities(c, since)

    first_well = date.today() - timedelta(days=WELLNESS_WINDOW_DAYS - 1)
    print(f"Wellness:   {first_well} → {date.today()} ({WELLNESS_WINDOW_DAYS} days)")
    n_well = fetch_wellness(c)

    print(f"✓ {n_act} new activities, {n_well} wellness days refreshed")
    if failed:
        print(f"! {len(failed)} calls failed and will be retried on the next run:")
        for label in failed:
            print(f"    {label}")


if __name__ == "__main__":
    main()

