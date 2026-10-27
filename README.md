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
