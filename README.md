# training-data

A personal repository for athletic training data and the Python tooling to work with it.

> **Status:** early scaffolding. Repository configuration, CI, and the directory
> layout have landed. The data directories are still empty and no application
> code has been written yet.

## Layout

```
.
├── .gitattributes           # file-type handling (binary / line endings)
├── .gitignore               # Python, env, and macOS artifacts
├── .github/
│   └── workflows/
│       ├── label-sync.yml   # sync label definitions from the central manifest
│       ├── path-labeler.yml # label PRs by changed paths
│       └── size-labeler.yml # label PRs by diff size
├── bin/                     # shell scripts and hand-run entry points
├── etc/                     # config templates
├── docs/                    # notes, especially verified API field mappings
├── src/
│   └── training_data/       # all the Python modules  (not yet created)
├── raw/                     # downloaded .fit files and raw API JSON
├── activities/              # one small summary JSON per session
├── streams/                 # one 1-minute-resolution CSV per session
├── tables/                  # the three rollup CSVs
└── README.md
```

Data flows one way: `raw/` is the immutable landing zone, `activities/` and
`streams/` are derived per-session, and `tables/` holds the rollups built from
those.

Each directory ships an empty `placeholder.txt` so git tracks it while it is
still empty.

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
