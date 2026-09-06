# training-data

A personal repository for athletic training data and the Python tooling to work with it.

> **Status:** the download and decode halves of the pipeline are written and
> `raw/` holds real data. `fetch.py` is working end to end; `decode.py` is
> written but not yet runnable (it imports helpers from `metrics.py`, which is
> still empty). The rollup and validation stages have not been written.

## Layout

```
.
├── .gitattributes           # file-type handling (binary / line endings)
├── .gitignore               # Python, env, and macOS artifacts
├── .python-version          # 3.13, read by uv
├── pyproject.toml           # project metadata and dependencies
├── uv.lock                  # pinned dependency resolution
├── .sync-state.json         # manifest of already-downloaded activity IDs
├── athlete.toml             # machine-readable athlete config
├── ATHLETE.md               # human/Claude-facing athlete context
├── LOG.md                   # training log, newest entries first
├── .github/
│   └── workflows/
│       ├── label-sync.yml   # sync label definitions from the central manifest
│       ├── path-labeler.yml # label PRs by changed paths
│       └── size-labeler.yml # label PRs by diff size
├── bin/
│   └── login.py             # one-off interactive Garmin login
├── etc/                     # config templates
├── docs/                    # notes, especially verified API field mappings
├── src/
│   └── training_data/
│       ├── config.py        # paths, tuning constants, athlete.toml loader
│       ├── garmin.py        # authenticated client + retry wrapper
│       ├── fetch.py         # Garmin Connect -> raw/
│       ├── decode.py        # raw/*.fit -> activities/ + streams/
│       ├── __init__.py      # package entry point (untracked)
│       ├── metrics.py       # NP, time-in-zone, decoupling (empty)
│       ├── rollup.py        # activities/ + streams/ -> tables/ (empty)
│       └── validate.py      # sanity checks over derived data (empty)
├── raw/
│   ├── activities/YYYY/MM/  # .fit files and their .meta.json siblings
│   └── wellness/YYYY/MM/    # one JSON per day, all endpoints bundled
├── activities/YYYY/MM/      # one small summary JSON per session
├── streams/YYYY/MM/         # one 1-minute-resolution CSV per session
├── tables/                  # rollup CSVs (not built yet)
└── README.md
```

Data flows one way: `raw/` is the immutable landing zone, `activities/` and
`streams/` are derived per-session, and `tables/` holds the rollups built from
those.

Everything under `raw/`, `activities/`, and `streams/` is partitioned as
`YYYY/MM/` — GitHub caps a single directory at 3,000 entries, and a flat
folder would hit that in about two years.

Directories with no data yet (`activities/`, `streams/`, `tables/`, `docs/`,
`etc/`) ship an empty `placeholder.txt` so git tracks them.

## Toolchain

Python 3.13 (pinned in `.python-version`), managed with
[uv](https://docs.astral.sh/uv/). Dependencies are declared in
`pyproject.toml` and locked in `uv.lock`:

| Package | Used for |
| --- | --- |
| `garminconnect` | Garmin Connect API client (pinned to `0.3.6`) |
| `garmin-fit-sdk` | decoding `.fit` files |
| `pandas` | rollup tables |

```bash
uv sync                                   # create .venv and install deps
uv run python bin/login.py                # once per machine — writes an OAuth token
uv run python -m training_data.fetch      # Garmin Connect -> raw/
uv run python -m training_data.decode     # raw/ -> activities/ + streams/
```

`bin/login.py` writes an OAuth token to `~/.garminconnect/`; the password is
never stored. Every later run reads that token, so no credentials live in the
repo or the environment.

## Pipeline

| Stage | Module | Status | What it does |
| --- | --- | --- | --- |
| Auth | `bin/login.py` | working | Interactive login, once per machine. Caches an OAuth token in `~/.garminconnect/`. |
| Fetch | `fetch.py` | working | Downloads new activity FITs plus a rolling 14-day window of daily wellness into `raw/`. |
| Decode | `decode.py` | written, not runnable | Turns each `raw/*.fit` into a summary JSON in `activities/` and a 1-minute CSV in `streams/`. |
| Rollup | `rollup.py` | empty file | Will build the CSVs in `tables/`. |
| Validate | `validate.py` | empty file | Will sanity-check the derived data. |

`decode.py` imports `normalized_power`, `time_in_zones`, and
`aerobic_decoupling` from `metrics.py`, which is still an empty file — so the
decode stage raises `ImportError` until those land. Nothing downstream of it
runs yet either.

Tuning constants live at the top of `config.py`:

| Constant | Value | Why |
| --- | --- | --- |
| `WELLNESS_WINDOW_DAYS` | 14 | Garmin revises history — sleep scores recalculate, VO2max backfills, training status lags a day. |
| `ACTIVITY_LOOKBACK_DAYS` | 30 | Catches late uploads and edited metadata; costs one list call, not N. |
| `RATE_LIMIT_SLEEP` | 1.5s | Garmin rate-limits aggressively; `garmin.py` also retries with exponential backoff. |

## Athlete context and state

| File | Read by | Holds |
| --- | --- | --- |
| `athlete.toml` | `config.py` | max HR, resting HR, weight, HR zone boundaries per sport, thresholds (LTHR, FTP, CSS), and the CTL/ATL exponential windows |
| `ATHLETE.md` | humans and Claude | the same thresholds in prose, plus race block, schedule, injury history, and equipment |
| `LOG.md` | humans and Claude | session-by-session review notes, newest first |
| `.sync-state.json` | `fetch.py` | activity IDs already downloaded, and the last sync date |

`athlete.toml` and `ATHLETE.md` overlap on purpose — one is machine-readable,
one is context. **Update both together.**

`.sync-state.json` is committed deliberately: a fresh clone on a new machine
knows not to re-download years of history. Activity metadata is refreshed on
every run regardless, since titles and sport types get edited after the fact.

## File conventions

Set in `.gitattributes`:

| Pattern | Handling | Where it applies | Why |
| --- | --- | --- | --- |
| `*.fit` | `binary` | `raw/activities/` | FIT activity files are binary — git shouldn't diff them or rewrite line endings. |
| `*.zip` | `binary` | anywhere | Same; Garmin serves FIT downloads as ZIP archives. |
| `*.csv` | `text eol=lf` | `streams/`, `tables/` | Consistent line endings for tabular exports across platforms. |
| `*.json` | `text eol=lf` | `raw/`, `activities/` | Same, for JSON exports. |
| `*.md` | `text eol=lf` | anywhere | Same, for prose. |

`.gitignore` covers the virtualenv (`.venv/`), Python build artifacts
(`__pycache__/`, `*.pyc`), the local sync job's logs (`.sync.log`,
`.sync.err`), and `.DS_Store`. No secrets are ignored because none are
written into the repo — the Garmin OAuth token lives in `~/.garminconnect/`.

## CI

All three workflows are thin callers into reusable workflows in
[`anaverage-enri/.github`](https://github.com/anaverage-enri/.github), so the
actual logic is maintained centrally.

| Workflow | Trigger | Permissions | Purpose |
| --- | --- | --- | --- |
| `label-sync.yml` | Manual (`workflow_dispatch`) | `contents: read`, `issues: write` | Reconciles this repo's labels with the central manifest. Takes an optional `delete-other-labels` boolean (default `false`) to also remove labels not declared there. |
| `path-labeler.yml` | PR `opened` / `synchronize` / `reopened` | `contents: read`, `pull-requests: write` | Labels a PR based on which paths it touches. |
| `size-labeler.yml` | PR `opened` / `synchronize` / `reopened` | `contents: read`, `pull-requests: write` | Labels a PR based on the size of its diff. |

Label definitions live in the central manifest rather than in this repo — run
`label-sync` after they change upstream.

## Workflow

Changes land on `main` through pull requests; both labelers run automatically on
each PR.
