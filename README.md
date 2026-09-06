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
│       └── decode.py        # raw/*.fit -> activities/ + streams/
├── raw/
│   ├── activities/YYYY/MM/  # .fit files and their .meta.json siblings
│   └── wellness/YYYY/MM/    # one JSON per day, all endpoints bundled
├── activities/YYYY/MM/      # one small summary JSON per session
├── streams/YYYY/MM/         # one 1-minute-resolution CSV per session
├── tables/                  # the three rollup CSVs
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

## File conventions

Set in `.gitattributes`:

| Pattern | Handling | Where it applies | Why |
| --- | --- | --- | --- |
| `*.fit` | `binary` | `raw/` | FIT activity files are binary — git shouldn't diff them or rewrite line endings. |
| `*.csv` | `text eol=lf` | `streams/`, `tables/` | Consistent line endings for tabular exports across platforms. |
| `*.json` | `text eol=lf` | `raw/`, `activities/` | Same, for JSON exports. |

`.gitignore` covers Python build artifacts (`__pycache__/`, `*.pyc`), virtualenvs (`.venv/`), local secrets (`.env`, `.env.local`), and `.DS_Store`.

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
