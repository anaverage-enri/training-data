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
    STATE_FILE,
    WELLNESS_WINDOW_DAYS,
    partition,
)
from training_data.garmin import client, with_retry


def load_state() -> dict:
    """Read the manifest of already-downloaded activity IDs.

    This file IS committed to git, so a fresh clone on a new machine knows
    not to re-download years of history.
    """
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"activity_ids": [], "last_sync": None}


def save_state(state: dict) -> None:
    state["last_sync"] = date.today().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_activities(c: Garmin, state: dict, since: date) -> int:
    """Download new activities. Returns the count of new FIT files."""
    known = set(state["activity_ids"])       # set = fast membership checks
    new_count = 0

    activities = with_retry(
        lambda: c.get_activities_by_date(since.isoformat(), date.today().isoformat()),
        label="list activities",
    )

    for act in activities:
        aid = str(act["activityId"])
        start = date.fromisoformat(act["startTimeLocal"][:10])

        # Filename: 20260826-071233-19283746
        # Sortable by time, unique by ID, no spaces or colons.
        stamp = act["startTimeLocal"].replace("-", "").replace(":", "").replace(" ", "-")
        base = f"{stamp}-{aid}"

        out_dir = partition(RAW, start)

        # Always refresh metadata — titles and sport types get edited later.
        (out_dir / f"{base}.meta.json").write_text(json.dumps(act, indent=2))

        if aid in known:
            continue                          # already have the FIT, skip

        print(f"  ↓ {base}  ({act.get('activityName', 'untitled')})")

        blob = with_retry(
            lambda: c.download_activity(
                aid, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL
            ),
            label=f"download {aid}",
        )

        # GOTCHA: ORIGINAL returns a ZIP archive, not a bare .fit file.
        # BytesIO wraps the bytes so zipfile can read them like a file.
        with zipfile.ZipFile(BytesIO(blob)) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".fit"))
            (out_dir / f"{base}.fit").write_bytes(z.read(name))

        state["activity_ids"].append(aid)
        new_count += 1
        time.sleep(RATE_LIMIT_SLEEP)

    return new_count


def fetch_wellness(c: Garmin, days: int = WELLNESS_WINDOW_DAYS) -> int:
    """Re-fetch a rolling window of daily wellness. Overwrites existing files."""
    written = 0

    for offset in range(days):
        d = date.today() - timedelta(days=offset)
        iso = d.isoformat()

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
    state = load_state()

    # -1 because get_activities_by_date is inclusive on BOTH ends:
    # today-29 .. today is 30 days, not 31.
    since = date.today() - timedelta(days=ACTIVITY_LOOKBACK_DAYS - 1)

    print(f"Activities: {since} → {date.today()} ({ACTIVITY_LOOKBACK_DAYS} days)")
    n_act = fetch_activities(c, state, since)

    first_well = date.today() - timedelta(days=WELLNESS_WINDOW_DAYS - 1)
    print(f"Wellness:   {first_well} → {date.today()} ({WELLNESS_WINDOW_DAYS} days)")
    n_well = fetch_wellness(c)

    save_state(state)
    print(f"✓ {n_act} new activities, {n_well} wellness days refreshed")


if __name__ == "__main__":
    main()

