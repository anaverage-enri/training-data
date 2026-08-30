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
