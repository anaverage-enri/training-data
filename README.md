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

