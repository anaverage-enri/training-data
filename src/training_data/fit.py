import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from garmin_fit_sdk import Decoder, Stream

from training_data.config import ACTIVITIES


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
