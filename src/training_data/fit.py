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
