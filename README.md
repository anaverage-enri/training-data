# training-data

A personal repository for athletic training data and the Python tooling to work with it.

> **Status:** early scaffolding. Only repository configuration and CI have landed so far — no application code or data files yet.

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
└── README.md
```

## File conventions

Set in `.gitattributes`:

| Pattern | Handling | Why |
| --- | --- | --- |
| `*.fit` | `binary` | FIT activity files are binary — git shouldn't diff them or rewrite line endings. |
| `*.csv` | `text eol=lf` | Consistent line endings for tabular exports across platforms. |
| `*.json` | `text eol=lf` | Same, for JSON exports. |

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

