"""Decode raw/*.fit into activities/*.json and streams/*.csv.

Run with:  uv run python -m training_data.decode
"""

import csv
import json
from datetime import date
from pathlib import Path

from garmin_fit_sdk import Decoder, Stream

from training_data.config import ACTIVITIES, RAW, STREAMS, load_athlete, partition
from training_data.metrics import aerobic_decoupling, normalized_power, time_in_zones


def read_fit(path: Path) -> dict:
    """Decode a FIT file into a dict of message lists.

    Returns keys like 'session_mesgs', 'lap_mesgs', 'record_mesgs'.
    'record_mesgs' is the 1 Hz timeseries — roughly one entry per second.
    """
    stream = Stream.from_file(str(path))
    decoder = Decoder(stream)

    messages, errors = decoder.read(
        apply_scale_and_offset=True,      # raw integers -> real units (watts, bpm)
        convert_datetimes_to_dates=True,  # FIT timestamps -> Python datetimes
        expand_components=True,           # unpack packed fields
        merge_heart_rates=True,           # fold separate HR messages into records
    )

    if errors:
        raise RuntimeError(f"{path.name}: {errors}")

    return messages


def downsample(records: list[dict], bucket_s: int = 60) -> list[dict]:
    """Average 1 Hz records into per-minute buckets."""
    fields = ["heart_rate", "power", "cadence", "speed", "altitude", "temperature"]
    out = []

    for i in range(0, len(records), bucket_s):
        chunk = records[i : i + bucket_s]
        row = {"t_min": i // bucket_s}

        for f in fields:
            vals = [r[f] for r in chunk if r.get(f) is not None]
            row[f] = round(sum(vals) / len(vals), 2) if vals else None

        out.append(row)

    return out


def summarise(messages: dict, athlete: dict) -> dict:
    """Build the compact per-activity summary."""
    session = messages["session_mesgs"][0]
    records = messages.get("record_mesgs", [])
    laps = messages.get("lap_mesgs", [])

    sport = session.get("sport", "unknown")
    zone_bounds = athlete["zones"].get(sport, athlete["zones"]["run"])

    # Power for bikes, speed for runs — the "output" side of efficiency.
    output_key = "power" if sport == "cycling" else "speed"

    return {
        "start": str(session.get("start_time")),
        "sport": sport,
        "sub_sport": session.get("sub_sport"),
        "duration_s": session.get("total_elapsed_time"),
        "moving_time_s": session.get("total_timer_time"),
        "distance_m": session.get("total_distance"),
        "elevation_gain_m": session.get("total_ascent"),
        "avg_hr": session.get("avg_heart_rate"),
        "max_hr": session.get("max_heart_rate"),
        "avg_power": session.get("avg_power"),
        "normalized_power": normalized_power(records),
        "calories": session.get("total_calories"),
        "zones_s": time_in_zones(records, zone_bounds),
        "decoupling_pct": aerobic_decoupling(records, output_key),
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


def main() -> None:
    athlete = load_athlete()
    decoded = 0

    # rglob("*.fit") walks all subdirectories recursively.
    for fit_path in sorted(RAW.rglob("*.fit")):
        base = fit_path.stem                        # filename without extension
        day = date.fromisoformat(
            f"{base[0:4]}-{base[4:6]}-{base[6:8]}"  # parse YYYYMMDD from the name
        )

        json_out = partition(ACTIVITIES, day) / f"{base}.json"
        csv_out = partition(STREAMS, day) / f"{base}.csv"

        if json_out.exists() and csv_out.exists():
            continue                                # already decoded

        print(f"  · decoding {base}")
        messages = read_fit(fit_path)

        summary = summarise(messages, athlete)
        summary["activity_id"] = base.split("-")[-1]
        json_out.write_text(json.dumps(summary, indent=2))

        rows = downsample(messages.get("record_mesgs", []))
        if rows:
            with open(csv_out, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

        decoded += 1

    print(f"✓ decoded {decoded} activities")


if __name__ == "__main__":
    main()

