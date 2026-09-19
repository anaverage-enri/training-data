# `training-data` — Complete Implementation Plan

A private GitHub repo that automatically pulls everything off Garmin Connect, decodes it,
rolls it into Claude-readable tables, and becomes the single source of truth for your
triathlon and badminton coaching.

**Written assuming you've never used Python.** Every Python concept is explained against
its TypeScript/Node equivalent the first time it appears. Every file is given in full,
with its exact name, location, and purpose.

---

## Table of contents

- [Part 0 — Orientation](#part-0--orientation)
- [Part 1 — Python for a TypeScript developer](#part-1--python-for-a-typescript-developer)
- [Part 2 — Install the toolchain](#part-2--install-the-toolchain)
- [Part 3 — Where files live, and dotfiles integration](#part-3--where-files-live-and-dotfiles-integration)
- [Part 4 — Create the repo](#part-4--create-the-repo)
- [Part 5 — Set up the Python project](#part-5--set-up-the-python-project)
- [Part 6 — Authentication](#part-6--authentication)
- [Part 7 — Foundation modules](#part-7--foundation-modules)
- [Part 8 — fetch.py](#part-8--fetchpy)
- [Part 9 — decode.py](#part-9--decodepy)
- [Part 10 — metrics.py](#part-10--metricspy)
- [Part 11 — rollup.py](#part-11--rolluppy)
- [Part 12 — validate.py](#part-12--validatepy)
- [Part 13 — The sync script](#part-13--the-sync-script)
- [Part 14 — Scheduling with launchd](#part-14--scheduling-with-launchd)
- [Part 15 — Wire into your dotfiles](#part-15--wire-into-your-dotfiles)
- [Part 16 — Connect Claude](#part-16--connect-claude)
- [Part 17 — Backfill history](#part-17--backfill-history)
- [Runbook](#runbook--when-it-breaks)
- [Build checklist](#build-checklist)

---

## Part 0 — Orientation

### What you're building

Six things run in sequence, once a day, on your Mac:

```
  ┌──────────────────────────────────────────────────────────────┐
  │  1. FETCH     Garmin Connect API  →  raw/*.fit, raw/*.json   │
  │  2. DECODE    raw/*.fit           →  activities/, streams/   │
  │  3. METRICS   (pure calculations, used by rollup)            │
  │  4. ROLLUP    everything          →  tables/*.csv            │
  │  5. VALIDATE  assert nothing is broken; abort if it is       │
  │  6. COMMIT    git add, commit, push                          │
  └──────────────────────────────────────────────────────────────┘
                              ↓
                      Claude reads tables/
```

Each step is a separate file so you can run and debug them independently. That matters a
lot when you're learning — if this were one script, a failure in step 4 would mean
re-downloading everything just to test a fix.

### The architecture decisions, and why

| Decision | Choice | Reasoning |
|---|---|---|
| Where the fetch runs | Your Mac, via `launchd` | Garmin's Cloudflare bot detection blocks datacenter IPs. GitHub Actions runners get flagged. |
| Scheduler | `launchd`, not `cron` | A missed `StartCalendarInterval` job fires once on wake. `cron` silently skips it. Your Mac sleeps. |
| Credentials | Interactive login, once per machine | The OAuth token auto-refreshes forever. Your password is a one-time bootstrap secret, not a daily one. |
| Repo layout | One repo, code + data together | The decoder and the data schema change together. Split repos give you version skew. |
| Directory partitioning | `YYYY/MM` everywhere | GitHub caps a single directory at 3,000 entries. A flat folder dies in year two. |
| Raw storage | `.fit` binary files, never modified | Already compact. Source of truth. Always re-decodable if you change your mind. |
| Decoded storage | Small summary JSON + 1-minute streams | Full 1 Hz JSON is 10–15× the FIT size, roughly 2 GB/year. Not worth it. |
| Table format | Year-partitioned CSV | Claude's GitHub connector reads text, not binary. Parquet would arrive as garbage bytes. |
| Wellness refresh | Rolling 14-day re-fetch | **Garmin revises history.** Sleep scores recalculate, VO2max backfills, training status lags a day. |

### Scale over time

At ~10–12 sessions/week: roughly **180 MB/year**, **1.8 GB after a decade**. GitHub
recommends staying under 10 GB of on-disk `.git` size, so you have decades of headroom.

---

## Part 1 — Python for a TypeScript developer

Read this once. Everything below will make sense afterward.

### Mental model translation

| TypeScript / Node | Python | Note |
|---|---|---|
| `package.json` | `pyproject.toml` | Project metadata and dependencies |
| `package-lock.json` | `uv.lock` | Exact resolved versions. Commit it. |
| `node_modules/` | `.venv/` | Per-project dependency folder. Never commit. |
| `nodenv` | `uv python` | Manages which Python version you're on |
| `npm ci` | `uv sync --frozen` | Install exactly what's locked |
| `npm install x` | `uv add x` | Add a dependency |
| `npm run x` | `uv run x` | Run inside the project environment |
| `npx` | `uvx` | Run a tool without installing it |
| `const x = 1` | `x = 1` | No keyword. There is no `const`. |
| `null` / `undefined` | `None` | One value instead of two |
| `{ a: 1 }` | `{"a": 1}` | A "dict". Keys usually quoted strings. |
| `[1, 2]` | `[1, 2]` | A "list". Same. |
| `` `hi ${name}` `` | `f"hi {name}"` | The `f` prefix is required |
| `arr.map(f)` | `[f(x) for x in arr]` | "List comprehension" |
| `arr.filter(p)` | `[x for x in arr if p(x)]` | Same syntax, plus `if` |
| `camelCase` | `snake_case` | Convention for variables and functions |
| `// comment` | `# comment` | |
| `function f() {}` | `def f():` | |
| `throw new Error("x")` | `raise ValueError("x")` | |

### Five things that will trip you up

**1. Indentation is syntax, not style.** No braces. A block is defined by being indented.
Four spaces, always. A wrong indent is a syntax error, not a lint warning.

```python
if x > 5:
    print("big")      # inside the if
print("always")       # outside the if
```

**2. Type hints exist but are not enforced.** `def f(x: int) -> str:` is documentation for
humans and editors. Python will happily pass a string. This is the opposite of TypeScript
strict mode and it's the thing you'll find most uncomfortable. Write them anyway — Cursor
uses them for autocomplete.

**3. `if __name__ == "__main__":` is the entry-point guard.** A Python file runs top to
bottom when executed. That block means "only run this when this file is executed directly,
not when another file imports it." It's the rough equivalent of a `bin` entry in
package.json.

**4. A folder becomes importable by containing `__init__.py`.** Usually empty. That's why
`src/training_data/__init__.py` exists below despite having nothing in it.

**5. `pathlib.Path` uses `/` to join paths.** This looks bizarre and is genuinely the
nicest thing in the standard library:

```python
from pathlib import Path
p = Path.home() / "code" / "training-data" / "tables"
p.mkdir(parents=True, exist_ok=True)   # like mkdir -p
```

### How you'll run things

You never "activate" a virtual environment. `uv run` handles it:

```bash
uv run python -m training_data.fetch     # run a module inside src/
uv run python bin/login.py               # run a standalone script
```

`python -m package.module` means "run this module as a program." It's how you run code
living inside `src/training_data/`.

---

## Part 2 — Install the toolchain

### 2.1 What you need

You already have Homebrew and git. You need one new tool.

```bash
brew install uv
uv --version
```

**Why `uv` rather than pip/pyenv/virtualenv:** Python's tooling is historically four
separate programs that each do a third of what npm does. `uv` is a single Rust binary from
the Ruff team that replaces all of them — it installs Python versions, creates the virtual
environment, resolves dependencies, writes a lockfile, and runs your code. Coming from
`nodenv` + `npm`, it's the only option that won't make you hate this.

You do **not** need to install Python separately. `uv` downloads and manages interpreters
itself. macOS ships an old Python 3.9 that wouldn't work here anyway — `garminconnect`
requires 3.12+.

### 2.2 Confirm gh is authenticated

```bash
brew install gh          # if you don't have it
gh auth status
```

If not authenticated: `gh auth login`, choose HTTPS, and let it configure git credentials.
This matters later — a scheduled background job that prompts for a password just hangs
forever with no useful error.

---

## Part 3 — Where files live, and dotfiles integration

This part is specific to your bare-repo dotfiles setup and contains one genuinely
important security warning. Read it before creating anything.

### 3.1 Where to put the repo

```
~/code/training-data
```

Adjust to wherever you keep repos, but **do not put it in `~/Documents`, `~/Desktop`, or
`~/Downloads`.** Those are protected by macOS TCC (Transparency, Consent and Control). A
`launchd` background job trying to read them gets denied, often with no useful error — the
job just fails silently every morning and you spend an evening debugging a permissions
problem that looks exactly like a code bug. `~/code` is unprotected.

### 3.2 The dotfiles boundary

Your dotfiles are a bare repo at `~/.dotfiles` with `$HOME` as the work tree. That means
**every file in your home directory is potentially trackable**, which is powerful and also
the source of the risk below.

| Category | Where it lives | Tracked by |
|---|---|---|
| Pipeline code and data | `~/code/training-data/` | The `training-data` repo |
| Shell aliases for the project | `~/.zshrc` or `~/.config/zsh/` | **Dotfiles** |
| Generated launchd agent | `~/Library/LaunchAgents/` | Neither — generated by bootstrap |
| **Garmin OAuth token** | `~/.garminconnect/` | **Neither. Must be gitignored.** |

### 3.3 ⚠️ Critical: exclude the token from your dotfiles

`~/.garminconnect/garmin_tokens.json` is an OAuth token that refreshes indefinitely and
**bypasses SSO — which means it bypasses your MFA.** It is more dangerous to leak than your
password, because a leaked password still hits a second factor and a leaked token doesn't.

Because your dotfiles work tree is `$HOME`, this file sits *inside* your dotfiles work
tree. One careless `dot add -A` and it's in your git history permanently.

Do this **now**, before running any login script:

```bash
cat >> ~/.gitignore <<'EOF'

# Garmin OAuth tokens — MFA-bypassing credential, never track
.garminconnect/

# Generated launchd agents (built by training-data/bin/bootstrap.sh)
Library/LaunchAgents/com.enri.garmin-sync.plist
EOF
```

Then verify with your dotfiles alias (substitute whatever yours is called):

```bash
dot check-ignore -v ~/.garminconnect/garmin_tokens.json
```

If that prints a matching rule, you're safe. If it prints nothing, the ignore rule isn't
being picked up — fix that before continuing.

Also confirm your dotfiles repo hides untracked files, which is standard for this setup:

```bash
dot config --local status.showUntrackedFiles no
```

### 3.4 Should the launchd plist live in dotfiles?

**No — generate it instead.** It contains an absolute path to the repo, which is
machine-specific. Tracking derived, path-dependent artifacts in dotfiles causes drift you
won't notice until a new machine behaves subtly differently. `bin/bootstrap.sh` generates
it from a template in the repo, which keeps the repo as the single source of truth for its
own automation. That's why it's in the gitignore block above.

---

## Part 4 — Create the repo

### 4.1 Create and clone

```bash
cd ~/code
gh repo create training-data --private --clone
cd training-data
```

**Private, permanently.** Every ride's FIT file contains your home address at 1-second GPS
resolution. Never add collaborators, never flip visibility to show someone the pipeline.

### 4.2 Folder structure

```bash
mkdir -p bin etc docs raw activities streams tables
```

What every directory is for:

| Path | Purpose | Written by | Claude reads? |
|---|---|---|---|
| `bin/` | Shell scripts and hand-run entry points | you | no |
| `etc/` | Config templates (the launchd plist template) | you | no |
| `docs/` | Your notes, especially verified API field mappings | you | no |
| `src/training_data/` | All the Python modules | you | no |
| `raw/` | Downloaded `.fit` files and raw API JSON. **Never edited.** | `fetch.py` | no |
| `activities/` | One small summary JSON per session | `decode.py` | on demand |
| `streams/` | One 1-minute-resolution CSV per session | `decode.py` | on demand |
| `tables/` | The three rollup CSVs | `rollup.py` | **yes, primarily** |

### 4.3 `.gitignore`

Create `~/code/training-data/.gitignore`:

```gitignore
# Python
.venv/
__pycache__/
*.pyc

# Local logs from the scheduled job
.sync.log
.sync.err

# macOS
.DS_Store
```

**Note what is deliberately absent: `.sync-state.json`.** That file gets committed. It's
the manifest of which activities you've already downloaded, and it's how a fresh clone on
a new machine knows not to re-download four years of history.

### 4.4 `.gitattributes`

Create `~/code/training-data/.gitattributes`:

```
# FIT files are binary — stop git trying to diff or convert line endings
*.fit binary
*.zip binary

# Force LF on text data files
*.csv text eol=lf
*.json text eol=lf
*.md text eol=lf
```

### 4.5 `athlete.toml` — machine-readable config

This is the file your **code** reads. Create `~/code/training-data/athlete.toml`:

```toml
# Machine-readable athlete config. Read by src/training_data/config.py.
# The human/Claude-facing version is ATHLETE.md — keep them in sync.

[profile]
max_hr = 189
resting_hr_baseline = 48
weight_kg = 68.0

# HR zone boundaries in bpm. Each entry is [lower, upper).
# Sport-specific because run and bike zones differ.
[zones.run]
z1 = [0, 138]
z2 = [138, 152]
z3 = [153, 163]
z4 = [164, 174]
z5 = [174, 250]

[zones.cycling]
z1 = [0, 132]
z2 = [132, 146]
z3 = [147, 157]
z4 = [158, 168]
z5 = [168, 250]

[thresholds]
run_lthr = 168
run_threshold_pace_s_per_km = 252   # 4:12/km
bike_ftp = 265
swim_css_s_per_100m = 98            # 1:38/100m

[load]
ctl_days = 42   # chronic (fitness) exponential window
atl_days = 7    # acute (fatigue) exponential window
```

TOML because Python 3.11+ reads it with zero dependencies (`tomllib` is in the standard
library), and it's less error-prone to hand-edit than JSON.

### 4.6 `ATHLETE.md` — human and Claude context

This is the file **Claude** reads. It's the highest-value file in the repo, because data
without context produces generic coaching.

```markdown
# Athlete Context

## Current block
- **A race:** [name, date, distance]
- **Phase:** [base / build / peak / taper / off-season]
- **Weekly hours target:** X

## Thresholds
Machine-readable versions live in `athlete.toml`. Update both together.

| Metric | Value | Last tested |
|---|---|---|
| Run LTHR | 168 bpm | 2026-06-14 |
| Run threshold pace | 4:12/km | 2026-06-14 |
| Bike FTP | 265 W | 2026-05-02 |
| Swim CSS | 1:38/100m | 2026-07-01 |
| Max HR | 189 bpm | observed |

## HR zones (run)
Z1 <138 · Z2 138–152 · Z3 153–163 · Z4 164–174 · Z5 >174

## Injury history and constraints
- [e.g. left achilles tendinopathy, Nov 2025 — flares above 60 km/week]

## Badminton
- Sessions per week, typical intensity, how it interacts with run load.
- Badminton load is HR-only (no power or pace data).

## Equipment
- Watch model, HRM strap vs optical, power meter, indoor trainer.
- Note when equipment changes — it creates step changes in the data that
  look like fitness changes but aren't.
```

### 4.7 `LOG.md` — coaching continuity

```markdown
# Training Log

Newest entries at the top. Claude appends here at the end of each review session
so the next session starts with context rather than a cold read of numbers.

---
```

### 4.8 Commit the skeleton

```bash
git add -A
git commit -m "chore: scaffold repo structure and athlete config"
git push
```

---

## Part 5 — Set up the Python project

### 5.1 Initialise with uv

```bash
cd ~/code/training-data
uv init --package --name training-data --python 3.13
```

`--package` creates a `src/` layout, which is what makes `uv run python -m training_data.fetch`
work later. `--python 3.13` pins the interpreter.

This creates:

- `pyproject.toml` — your package.json equivalent
- `.python-version` — pins the interpreter, like `.node-version`
- `src/training_data/__init__.py` — the empty file that makes the folder importable

### 5.2 Add dependencies

```bash
uv add "garminconnect==0.3.6"
uv add garmin-fit-sdk
uv add pandas
```

Each command updates `pyproject.toml`, resolves versions, writes `uv.lock`, and installs
into `.venv/`. Same as `npm install x`.

**Why `garminconnect` is pinned exactly and the others aren't:** this is an unofficial
client hitting Garmin's internal endpoints. In March 2026 Garmin changed its auth flow and
deployed Cloudflare bot detection, which killed the `garth` library the entire Python
ecosystem depended on. `garminconnect` 0.3.0 replaced garth with a native auth engine using
TLS impersonation, and 0.3.6 is the current working version. It works *today*. Pinning
means a `uv sync` on a new machine six months from now installs the exact version you
tested, rather than surprising you at 6:30am.

### 5.3 Commit the lockfile

```bash
git add pyproject.toml uv.lock .python-version
git commit -m "build: add Python toolchain and pinned dependencies"
```

`uv.lock` is committed for the same reason `package-lock.json` is. Never hand-edit it.

### 5.4 Create the module files

```bash
touch src/training_data/{config,garmin,fetch,decode,metrics,rollup,validate}.py
```

Seven modules, each doing exactly one thing:

| Module | Responsibility | Depends on |
|---|---|---|
| `config.py` | Paths and athlete config. No logic. | nothing |
| `garmin.py` | Builds an authenticated API client. | config |
| `fetch.py` | Downloads from Garmin → `raw/` | config, garmin |
| `decode.py` | `raw/*.fit` → `activities/`, `streams/` | config, metrics |
| `metrics.py` | Pure math. No file I/O. | nothing |
| `rollup.py` | Everything → `tables/*.csv` | config, metrics |
| `validate.py` | Assertions. Exits non-zero on failure. | config |

`metrics.py` has no I/O deliberately. Pure functions are the easiest thing in the world to
test, and you'll want to verify the CTL/ATL math against numbers you can check by hand.

---

## Part 6 — Authentication

**Goal: prove you can log in and make one API call. Do not proceed until this works.**

### 6.1 How the auth actually works

1. You log in interactively **once**, typing your password and MFA code.
2. The library exchanges that for an OAuth token and writes
   `~/.garminconnect/garmin_tokens.json` with `0600` permissions.
3. Every subsequent run reads that token, which refreshes itself in the background,
   indefinitely.
4. Your password is never stored anywhere.

This is why there's no `.env` file and no secret management in this project. There is
nothing to store.

### 6.2 `bin/login.py`

Create `~/code/training-data/bin/login.py`:

```python
#!/usr/bin/env python3
"""Interactive Garmin Connect login. Run once per machine.

Writes an OAuth token to ~/.garminconnect/. Your password is never saved,
never written to disk, and never enters your shell history.
"""

# `from X import Y` is like `import { Y } from "x"` in TypeScript.
from getpass import getpass       # reads a password without echoing it
from pathlib import Path          # filesystem paths; uses / to join

from garminconnect import Garmin

# Path.home() is ~ . The / operator joins path segments.
TOKENSTORE = Path.home() / ".garminconnect"


def main() -> None:
    """`-> None` is a type hint meaning 'returns nothing'. Documentation only."""
    email = input("Garmin email: ")
    password = getpass("Garmin password: ")   # not echoed to the terminal

    # `prompt_mfa` is a callback the library calls if MFA is required.
    # `lambda: x` is an anonymous function taking no arguments, like `() => x`.
    client = Garmin(
        email=email,
        password=password,
        prompt_mfa=lambda: input("MFA one-time code: "),
    )

    # login() with a path argument saves the token there for reuse.
    client.login(str(TOKENSTORE))

    print(f"✓ Token written to {TOKENSTORE}")
    print("  Your password was not saved. Daily syncs resume from this token.")


# Only run main() when this file is executed directly, not when imported.
if __name__ == "__main__":
    main()
```

### 6.3 Run it

```bash
uv run python bin/login.py
```

Type your email, password, and MFA code.

### 6.4 Verify the token landed safely

```bash
ls -la ~/.garminconnect/
# Expect: drwx------ on the directory, -rw------- on garmin_tokens.json
```

If permissions are looser, fix them:

```bash
chmod 700 ~/.garminconnect && chmod 600 ~/.garminconnect/*
```

And re-confirm your dotfiles are ignoring it:

```bash
dot check-ignore -v ~/.garminconnect/garmin_tokens.json
```

### 6.5 Smoke test

```bash
uv run python -c "
from garminconnect import Garmin
from pathlib import Path
c = Garmin()
c.login(str(Path.home() / '.garminconnect'))
print('Logged in as:', c.get_full_name())
print('Steps yesterday:', c.get_stats('2026-08-28')['totalSteps'])
"
```

If that prints your name and a step count, **authentication is solved.** This is the
hardest and most fragile part of the whole project and it's now behind you.

### 6.6 Discover the real API surface — do not skip this

The library ships a `demo.py` with 130+ methods across 13 categories. **The 0.3.x rewrite
changed method names and response shapes, so most tutorials you find online are wrong.**

List what's available:

```bash
uv run python -c "
from garminconnect import Garmin
print('\n'.join(m for m in dir(Garmin) if m.startswith('get_')))
"
```

Then dump one real day and read it:

```bash
uv run python -c "
import json
from garminconnect import Garmin
from pathlib import Path
c = Garmin(); c.login(str(Path.home() / '.garminconnect'))
print(json.dumps(c.get_sleep_data('2026-08-28'), indent=2))
" | head -60
```

Record what you find in `docs/api-notes.md`: the exact method name, and the exact key path
to every field you care about. Is resting heart rate at `stats["restingHeartRate"]`, or
nested under a summary object? Guessing wrong here produces a pipeline that silently
writes empty columns for weeks.

One known gotcha, already confirmed: `get_training_readiness()` returns a **list** of
snapshots, not a single dict. That was an explicit fix in version 0.3.5.

```bash
git add bin/login.py docs/api-notes.md
git commit -m "feat(auth): add interactive login and document API surface"
```

---

## Part 7 — Foundation modules

### 7.1 `src/training_data/config.py`

Every other module imports from here. One place to change a path.

```python
"""Central configuration: paths and athlete settings.

No logic here — just constants and simple loaders. Every other module imports
from this file so there's exactly one place to change a path.
"""

import tomllib                    # TOML reader, built into Python 3.11+
from datetime import date
from pathlib import Path

# __file__ is this file's path. .resolve() makes it absolute.
# .parents[2] goes up three levels: config.py -> training_data -> src -> repo root
REPO = Path(__file__).resolve().parents[2]

RAW = REPO / "raw"
ACTIVITIES = REPO / "activities"
STREAMS = REPO / "streams"
TABLES = REPO / "tables"
STATE_FILE = REPO / ".sync-state.json"
ATHLETE_FILE = REPO / "athlete.toml"

TOKENSTORE = Path.home() / ".garminconnect"

# How many days back to re-fetch wellness every run.
# Garmin revises history: sleep scores recalculate, VO2max backfills,
# training status lags a day. Re-fetching a window keeps us in sync.
WELLNESS_WINDOW_DAYS = 14

# Seconds to sleep between API calls. Garmin rate-limits aggressively.
RATE_LIMIT_SLEEP = 1.5


def load_athlete() -> dict:
    """Read athlete.toml into a dictionary.

    'rb' means read-binary, which tomllib requires.
    The `with` block auto-closes the file, like a try/finally.
    """
    with open(ATHLETE_FILE, "rb") as f:
        return tomllib.load(f)


def partition(root: Path, d: date) -> Path:
    """Return root/YYYY/MM/ and create it if needed.

    Partitioning matters: GitHub caps a single directory at 3,000 entries,
    and a flat activities/ folder hits that in about two years.

    f"{d:%Y}" formats the date as a 4-digit year, like strftime.
    """
    p = root / f"{d:%Y}" / f"{d:%m}"
    p.mkdir(parents=True, exist_ok=True)   # like mkdir -p
    return p
```

### 7.2 `src/training_data/garmin.py`

```python
"""Authenticated Garmin Connect client, with retry handling."""

import time
from typing import Any, Callable

from garminconnect import Garmin

from training_data.config import RATE_LIMIT_SLEEP, TOKENSTORE


def client() -> Garmin:
    """Return a logged-in client using the cached OAuth token.

    No credentials needed — bin/login.py already wrote the token.
    Raises if the token is missing or rejected, which is what we want:
    fail loudly rather than silently syncing nothing.
    """
    c = Garmin()
    c.login(str(TOKENSTORE))
    return c


def with_retry(fn: Callable[[], Any], attempts: int = 3, label: str = "") -> Any:
    """Call fn(), retrying with exponential backoff on failure.

    Garmin returns 429 (rate limited) and 403 (Cloudflare) fairly often.
    Backing off handles the transient cases; after `attempts` tries we give up
    and let the exception propagate so the run fails visibly rather than
    writing partial data.
    """
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i == attempts - 1:
                raise                           # last attempt: re-raise
            wait = RATE_LIMIT_SLEEP * (2 ** i)  # 1.5s, 3s, 6s
            print(f"  ! {label} failed ({e}); retrying in {wait:.1f}s")
            time.sleep(wait)
```

```bash
git add src/training_data/config.py src/training_data/garmin.py
git commit -m "feat(core): add config and authenticated client helpers"
```

---

## Part 8 — `fetch.py`

**Goal: `raw/` fills with FIT files and wellness JSON, idempotently.**

### 8.1 The two-window strategy

This is the design detail that separates a pipeline that stays correct from one that
silently drifts:

- **Activities** — download the FIT only if the ID isn't in `.sync-state.json`. But
  re-fetch the *metadata* every run, because you might rename a session or fix its sport
  type in Connect days later.
- **Wellness** — always re-fetch the last 14 days and overwrite. Garmin recalculates sleep
  scores, backfills VO2max, and updates training status after the fact. A naive "fetch
  yesterday only" job diverges from what Connect shows and you won't notice for months.

### 8.2 The code

Create `src/training_data/fetch.py`:

```python
"""Download from Garmin Connect into raw/.

Run with:  uv run python -m training_data.fetch
"""

import json
import time
import zipfile
from datetime import date, timedelta
from io import BytesIO

from garminconnect import Garmin

from training_data.config import (
    RATE_LIMIT_SLEEP,
    RAW,
    STATE_FILE,
    WELLNESS_WINDOW_DAYS,
    partition,
)
from training_data.garmin import client, with_retry


def load_state() -> dict:
    """Read the manifest of already-downloaded activity IDs.

    This file IS committed to git, so a fresh clone on a new machine knows
    not to re-download years of history.
    """
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"activity_ids": [], "last_sync": None}


def save_state(state: dict) -> None:
    state["last_sync"] = date.today().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_activities(c: Garmin, state: dict, since: date) -> int:
    """Download new activities. Returns the count of new FIT files."""
    known = set(state["activity_ids"])       # set = fast membership checks
    new_count = 0

    activities = with_retry(
        lambda: c.get_activities_by_date(since.isoformat(), date.today().isoformat()),
        label="list activities",
    )

    for act in activities:
        aid = str(act["activityId"])
        start = date.fromisoformat(act["startTimeLocal"][:10])

        # Filename: 20260826-071233-19283746
        # Sortable by time, unique by ID, no spaces or colons.
        stamp = act["startTimeLocal"].replace("-", "").replace(":", "").replace(" ", "-")
        base = f"{stamp}-{aid}"

        out_dir = partition(RAW, start)

        # Always refresh metadata — titles and sport types get edited later.
        (out_dir / f"{base}.meta.json").write_text(json.dumps(act, indent=2))

        if aid in known:
            continue                          # already have the FIT, skip

        print(f"  ↓ {base}  ({act.get('activityName', 'untitled')})")

        blob = with_retry(
            lambda: c.download_activity(
                aid, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL
            ),
            label=f"download {aid}",
        )

        # GOTCHA: ORIGINAL returns a ZIP archive, not a bare .fit file.
        # BytesIO wraps the bytes so zipfile can read them like a file.
        with zipfile.ZipFile(BytesIO(blob)) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".fit"))
            (out_dir / f"{base}.fit").write_bytes(z.read(name))

        state["activity_ids"].append(aid)
        new_count += 1
        time.sleep(RATE_LIMIT_SLEEP)

    return new_count


def fetch_wellness(c: Garmin, days: int = WELLNESS_WINDOW_DAYS) -> int:
    """Re-fetch a rolling window of daily wellness. Overwrites existing files."""
    written = 0

    for offset in range(days):
        d = date.today() - timedelta(days=offset)
        iso = d.isoformat()

        # Each endpoint is a separate API call. Bundle into one file per day
        # so decode/rollup only ever opens one file per date.
        payload = {
            "date": iso,
            "stats": with_retry(lambda: c.get_stats(iso), label=f"stats {iso}"),
            "sleep": with_retry(lambda: c.get_sleep_data(iso), label=f"sleep {iso}"),
            "hrv": with_retry(lambda: c.get_hrv_data(iso), label=f"hrv {iso}"),
            "body_battery": with_retry(
                lambda: c.get_body_battery(iso, iso), label=f"bb {iso}"
            ),
            "training_readiness": with_retry(
                lambda: c.get_training_readiness(iso), label=f"readiness {iso}"
            ),
            "training_status": with_retry(
                lambda: c.get_training_status(iso), label=f"status {iso}"
            ),
            "max_metrics": with_retry(
                lambda: c.get_max_metrics(iso), label=f"vo2 {iso}"
            ),
        }

        out = partition(RAW / "wellness", d)
        (out / f"{iso}.json").write_text(json.dumps(payload, indent=2))
        written += 1
        time.sleep(RATE_LIMIT_SLEEP)

    return written


def main() -> None:
    c = client()
    state = load_state()
    since = date.today() - timedelta(days=WELLNESS_WINDOW_DAYS)

    print("Fetching activities...")
    n_act = fetch_activities(c, state, since)

    print("Fetching wellness...")
    n_well = fetch_wellness(c)

    save_state(state)
    print(f"✓ {n_act} new activities, {n_well} wellness days refreshed")


if __name__ == "__main__":
    main()
```

### 8.3 Verify field names against your own data

```bash
uv run python -m training_data.fetch
cat raw/wellness/2026/08/2026-08-28.json | head -80
```

The **exact keys** inside each response are undocumented and version-dependent. Write the
real paths into `docs/api-notes.md` — you'll need them in `rollup.py`.

### 8.4 Idempotency test

Run it twice. The second run should download zero new activities:

```bash
uv run python -m training_data.fetch
uv run python -m training_data.fetch   # should say "0 new activities"
```

If the second run re-downloads, `.sync-state.json` isn't being written or read correctly.
Fix that before moving on — it's the difference between a 5-second daily job and a
rate-limited one.

```bash
git add src/training_data/fetch.py .sync-state.json
git commit -m "feat(fetch): download activities and rolling wellness window"
```

---

## Part 9 — `decode.py`

**Goal: turn binary FIT files into two readable derivatives.**

### 9.1 What comes out

**A summary JSON (~5 KB)** at `activities/YYYY/MM/{base}.json`:

```json
{
  "activity_id": "19283746",
  "start": "2026-08-26T07:12:33+09:00",
  "sport": "cycling",
  "duration_s": 10842,
  "moving_time_s": 10440,
  "distance_m": 92400,
  "elevation_gain_m": 1180,
  "avg_hr": 142, "max_hr": 171,
  "avg_power": 198, "normalized_power": 224,
  "zones_s": {"z1": 1200, "z2": 5400, "z3": 2100, "z4": 1500, "z5": 240},
  "decoupling_pct": 4.2,
  "laps": [{"n": 1, "duration_s": 1200, "distance_m": 9800, "avg_hr": 131}]
}
```

**A 1-minute stream CSV** at `streams/YYYY/MM/{base}.csv`. A 5-hour ride becomes 300 rows
instead of 18,000. You keep the *shape* of the session — did the second half fade? did HR
drift upward at constant power? — at 1/60th the size.

```csv
t_min,heart_rate,power,cadence,speed,altitude,temperature
0,98,0,0,0.0,42.1,24
1,124,168,84,7.9,44.0,24
```

**Latitude and longitude are deliberately excluded.** Your home address is the start point
of every ride. It stays in the FIT archive, not in the layer you'll be reading and sharing.

### 9.2 The code

```python
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
```

### 9.3 Test on one file first

Before running the whole thing, inspect a single FIT to see what your watch actually
records:

```bash
uv run python -c "
from training_data.decode import read_fit
from pathlib import Path
p = next(Path('raw').rglob('*.fit'))
m = read_fit(p)
print('Message types:', list(m.keys()))
print()
print('First record:', m['record_mesgs'][0])
print()
print('Session keys:', sorted(m['session_mesgs'][0].keys()))
"
```

Field availability varies by sport and device. A pool swim has `length_mesgs` and no
`power`. A treadmill run has no `altitude`. Adjust `summarise()` to what you actually have.

```bash
git add src/training_data/decode.py
git commit -m "feat(decode): convert FIT files to summaries and 1-min streams"
```

---

## Part 10 — `metrics.py`

**Goal: the calculations that make this pipeline worth building.**

Pure functions — data in, number out, no files touched. That makes them trivial to test,
and you should test them, because these are the numbers you'll make training decisions
from.

```python
"""Training-load and efficiency calculations.

Pure functions only: no file I/O, no API calls. Easy to test in isolation.
"""


def training_load_series(
    daily_load: list[float], ctl_days: int = 42, atl_days: int = 7
) -> list[tuple[float, float, float]]:
    """Exponentially weighted fitness, fatigue, and form.

    CTL (chronic training load) = fitness, a 42-day exponential average.
    ATL (acute training load)   = fatigue, a 7-day exponential average.
    TSB (training stress balance) = form = CTL - ATL.

    TSB is computed BEFORE adding today's load, because today's session hasn't
    been absorbed yet. Positive TSB = fresh, negative = fatigued.
    """
    ctl = atl = 0.0
    out = []

    for load in daily_load:
        tsb = ctl - atl                    # yesterday's values
        ctl += (load - ctl) / ctl_days
        atl += (load - atl) / atl_days
        out.append((round(ctl, 1), round(atl, 1), round(tsb, 1)))

    return out


def time_in_zones(records: list[dict], bounds: dict) -> dict:
    """Seconds spent in each HR zone.

    `bounds` looks like {"z1": [0, 138], "z2": [138, 152], ...}
    Records are ~1 Hz, so counting records approximates counting seconds.

    This is the single most useful derived field in the repo: it tells you
    whether you're actually training polarized, or drifting into the grey zone
    where you're too tired to go hard and going too hard to recover.
    """
    zones = {z: 0 for z in bounds}

    for r in records:
        hr = r.get("heart_rate")
        if hr is None:
            continue
        for name, (lo, hi) in bounds.items():
            if lo <= hr < hi:
                zones[name] += 1
                break

    return zones


def aerobic_decoupling(records: list[dict], output_key: str) -> float | None:
    """Percent drift in output-per-heartbeat, first half vs second half.

    Above roughly 5% at a steady aerobic effort means durability is the limiter
    rather than fitness. A rising trend at constant training load is one of the
    earliest signals of accumulating fatigue.

    `float | None` means "a float, or nothing" — like `number | null`.
    """
    usable = [r for r in records if r.get("heart_rate") and r.get(output_key)]

    if len(usable) < 600:          # under 10 minutes of data, not meaningful
        return None

    mid = len(usable) // 2         # // is integer division

    def ef(chunk: list[dict]) -> float:
        """Efficiency factor: mean output divided by mean heart rate."""
        out = sum(r[output_key] for r in chunk) / len(chunk)
        hr = sum(r["heart_rate"] for r in chunk) / len(chunk)
        return out / hr

    first, second = ef(usable[:mid]), ef(usable[mid:])
    return round((first - second) / first * 100, 2)


def normalized_power(records: list[dict], window: int = 30) -> int | None:
    """Normalized Power: 4th root of the mean of the 30s rolling average^4.

    Weights hard surges more heavily than a plain average, which is why it
    reflects the physiological cost of a variable ride better than avg power.
    """
    powers = [r.get("power") for r in records if r.get("power") is not None]

    if len(powers) < window:
        return None

    rolling = [
        sum(powers[i : i + window]) / window
        for i in range(len(powers) - window + 1)
    ]

    mean_4th = sum(p ** 4 for p in rolling) / len(rolling)
    return round(mean_4th ** 0.25)
```

### 10.1 Verify the load math by hand

```bash
uv run python -c "
from training_data.metrics import training_load_series
r = training_load_series([100] * 30)   # 30 days of constant load
print('Day 1 (ctl, atl, tsb):', r[0])
print('Day 30 (ctl, atl, tsb):', r[-1])
"
```

Day 30 should show ATL close to 100, CTL well below it, and a negative TSB. That's the
correct shape: sustained training makes you fatigued before it makes you fit.

**Also capture Garmin's own numbers.** The watch computes EPOC-based training load, acute
load, and load ratio. Store those in the tables alongside your computed CTL/ATL so you can
reconcile when they disagree, rather than wondering which one is "right."

```bash
git add src/training_data/metrics.py
git commit -m "feat(metrics): add CTL/ATL/TSB, zones, decoupling, normalized power"
```

---

## Part 11 — `rollup.py`

**Goal: the three CSVs Claude actually reads.**

### 11.1 The three tables

**`tables/wellness-YYYY.csv`** — one row per day.

**`tables/activities-YYYY.csv`** — one row per session, the summary JSON flattened.

**`tables/weekly-YYYY.csv`** — one row per ISO week. **This is the money table.** It turns
"am I overreaching?" into a 52-row read instead of reasoning across 200 files.

### 11.2 Why year-partitioned

`wellness-2026.csv` stops changing on 31 December and is never rewritten again. Git stores
a complete new blob every time a file changes, so one giant `wellness.csv` rewritten daily
accumulates a full copy in history on every single commit, forever. Year partitions cap
that at one year of churn.

### 11.3 The code

```python
"""Build the rollup tables Claude reads.

Run with:  uv run python -m training_data.rollup
"""

import json

import pandas as pd

from training_data.config import ACTIVITIES, RAW, TABLES, load_athlete
from training_data.metrics import training_load_series


def build_wellness() -> pd.DataFrame:
    """One row per day, from raw/wellness/**/*.json.

    A DataFrame is a table — think of it as a typed 2D array with named
    columns. pandas is the standard tool for this in Python.
    """
    rows = []

    for path in sorted((RAW / "wellness").rglob("*.json")):
        d = json.loads(path.read_text())
        stats = d.get("stats") or {}
        sleep = (d.get("sleep") or {}).get("dailySleepDTO") or {}
        hrv = (d.get("hrv") or {}).get("hrvSummary") or {}
        status = d.get("training_status") or {}

        # .get() with a default avoids KeyError when a field is missing —
        # important because Garmin omits fields on days you didn't wear the watch.
        rows.append({
            "date": d["date"],
            "rhr": stats.get("restingHeartRate"),
            "hrv_overnight": hrv.get("lastNightAvg"),
            "hrv_status": hrv.get("status"),
            "hrv_7d": hrv.get("weeklyAvg"),
            "sleep_h": round((sleep.get("sleepTimeSeconds") or 0) / 3600, 2),
            "stress_avg": stats.get("averageStressLevel"),
            "body_battery_max": stats.get("bodyBatteryHighestValue"),
            "body_battery_min": stats.get("bodyBatteryLowestValue"),
            "steps": stats.get("totalSteps"),
            "training_status": status.get("trainingStatus"),
        })

    # NOTE: the exact key paths above are PLACEHOLDERS until you verify them
    # against your own data. See docs/api-notes.md from Part 6.6.

    return pd.DataFrame(rows).sort_values("date")


def build_activities() -> pd.DataFrame:
    """One row per activity, from activities/**/*.json."""
    rows = []

    for path in sorted(ACTIVITIES.rglob("*.json")):
        a = json.loads(path.read_text())
        zones = a.get("zones_s") or {}

        rows.append({
            "date": a["start"][:10],
            "activity_id": a.get("activity_id"),
            "sport": a.get("sport"),
            "duration_h": round((a.get("moving_time_s") or 0) / 3600, 3),
            "distance_km": round((a.get("distance_m") or 0) / 1000, 2),
            "elevation_m": a.get("elevation_gain_m"),
            "avg_hr": a.get("avg_hr"),
            "avg_power": a.get("avg_power"),
            "normalized_power": a.get("normalized_power"),
            "decoupling_pct": a.get("decoupling_pct"),
            # ** unpacks a dict into the outer dict, like TS object spread
            **{f"{z}_s": zones.get(z, 0) for z in ("z1", "z2", "z3", "z4", "z5")},
        })

    return pd.DataFrame(rows).sort_values("date")


def build_weekly(acts: pd.DataFrame, well: pd.DataFrame, athlete: dict) -> pd.DataFrame:
    """Aggregate to ISO weeks and attach CTL/ATL/TSB."""
    acts = acts.copy()
    acts["date"] = pd.to_datetime(acts["date"])
    acts["week"] = acts["date"].dt.to_period("W").dt.start_time

    # Pivot hours by sport into columns: swim_h, run_h, cycling_h, ...
    hours = acts.pivot_table(
        index="week", columns="sport", values="duration_h", aggfunc="sum"
    ).fillna(0)
    hours.columns = [f"{c}_h" for c in hours.columns]

    zone_cols = [f"z{i}_s" for i in range(1, 6)]
    zones = acts.groupby("week")[zone_cols].sum()
    total_z = zones.sum(axis=1).replace(0, 1)          # avoid divide-by-zero
    for i in range(1, 6):
        zones[f"z{i}_pct"] = (zones[f"z{i}_s"] / total_z * 100).round(1)

    weekly = hours.join(zones[[f"z{i}_pct" for i in range(1, 6)]])
    weekly["total_h"] = hours.sum(axis=1).round(2)

    # Wellness averages per week
    well = well.copy()
    well["date"] = pd.to_datetime(well["date"])
    well["week"] = well["date"].dt.to_period("W").dt.start_time
    wk_well = well.groupby("week")[["rhr", "hrv_overnight", "sleep_h"]].mean().round(1)
    wk_well.columns = ["avg_rhr", "avg_hrv", "avg_sleep_h"]

    weekly = weekly.join(wk_well)

    # Load series. This uses hours*50 as a placeholder proxy — replace it with
    # Garmin's own training load numbers once you've verified that field path.
    loads = (weekly["total_h"] * 50).fillna(0).tolist()
    series = training_load_series(
        loads, athlete["load"]["ctl_days"], athlete["load"]["atl_days"]
    )
    weekly["ctl"] = [s[0] for s in series]
    weekly["atl"] = [s[1] for s in series]
    weekly["tsb"] = [s[2] for s in series]

    return weekly.reset_index().rename(columns={"week": "week_start"})


def write_partitioned(df: pd.DataFrame, prefix: str, date_col: str) -> None:
    """Write one CSV per year: tables/{prefix}-2026.csv"""
    df = df.copy()
    df["_year"] = pd.to_datetime(df[date_col]).dt.year

    for year, group in df.groupby("_year"):
        out = TABLES / f"{prefix}-{year}.csv"
        group.drop(columns="_year").to_csv(out, index=False)
        print(f"  → {out.name}  ({len(group)} rows)")


def main() -> None:
    TABLES.mkdir(exist_ok=True)
    athlete = load_athlete()

    well = build_wellness()
    acts = build_activities()
    weekly = build_weekly(acts, well, athlete)

    write_partitioned(well, "wellness", "date")
    write_partitioned(acts, "activities", "date")
    write_partitioned(weekly, "weekly", "week_start")

    print("✓ tables rebuilt")


if __name__ == "__main__":
    main()
```

> **The key paths in `build_wellness()` are placeholders.** Replace them with what you
> actually found in Part 6.6. This is the single most likely source of silently empty
> columns, which is exactly what `validate.py` exists to catch.

```bash
git add src/training_data/rollup.py
git commit -m "feat(rollup): build wellness, activity, and weekly tables"
```

---

## Part 12 — `validate.py`

**Goal: fail loudly instead of writing garbage quietly.**

A pipeline that writes empty rows for three weeks is far worse than one that breaks on day
one. You only find out when you ask Claude about a trend and the answer is subtly wrong.

```python
"""Assertions that run before every commit. Exits non-zero on failure.

Run with:  uv run python -m training_data.validate
"""

import sys
from datetime import date, timedelta

import pandas as pd

from training_data.config import ACTIVITIES, RAW, STREAMS, TABLES, WELLNESS_WINDOW_DAYS

MAX_FILE_BYTES = 1_000_000    # GitHub's recommended single-object limit
MAX_DIR_ENTRIES = 2_500       # early warning; the hard cap is 3,000

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    """Record a failure instead of raising, so we report all problems at once."""
    if not condition:
        failures.append(message)


def main() -> None:
    year = date.today().year
    wellness_csv = TABLES / f"wellness-{year}.csv"

    check(wellness_csv.exists(), f"missing {wellness_csv.name}")

    if wellness_csv.exists():
        df = pd.read_csv(wellness_csv)
        recent = df.tail(WELLNESS_WINDOW_DAYS)

        # 1. Every date in the window is present
        expected = {
            (date.today() - timedelta(days=i)).isoformat()
            for i in range(1, WELLNESS_WINDOW_DAYS)
        }
        missing = expected - set(df["date"].astype(str))
        check(not missing, f"missing wellness dates: {sorted(missing)[:5]}")

        # 2. Core fields are populated most of the time
        for col in ("rhr", "sleep_h"):
            filled = recent[col].notna().sum()
            check(filled >= 10, f"{col} only populated {filled}/{len(recent)} recent days")

    # 3. Every FIT has a decoded summary
    fits = {p.stem for p in RAW.rglob("*.fit")}
    jsons = {p.stem for p in ACTIVITIES.rglob("*.json")}
    orphans = fits - jsons
    check(not orphans, f"{len(orphans)} FIT files never decoded: {sorted(orphans)[:3]}")

    # 4. No file exceeds GitHub's recommended object size
    for root in (ACTIVITIES, STREAMS, TABLES):
        for p in root.rglob("*"):
            if p.is_file() and p.stat().st_size > MAX_FILE_BYTES:
                failures.append(f"{p} is {p.stat().st_size // 1024} KB (>1 MB)")

    # 5. No directory approaches GitHub's 3,000-entry cap
    for root in (RAW, ACTIVITIES, STREAMS):
        for d in root.rglob("*"):
            if d.is_dir():
                n = len(list(d.iterdir()))
                if n > MAX_DIR_ENTRIES:
                    failures.append(f"{d} has {n} entries (cap 3000)")

    if failures:
        print("✗ validation failed:")
        for f in failures:
            print(f"   - {f}")
        sys.exit(1)          # non-zero exit stops sync.sh before it commits

    print("✓ validation passed")


if __name__ == "__main__":
    main()
```

```bash
uv run python -m training_data.validate
git add src/training_data/validate.py
git commit -m "feat(validate): assert data integrity before commit"
```

---

## Part 13 — The sync script

### 13.1 `bin/sync.sh`

This is what `launchd` actually runs. Create `~/code/training-data/bin/sync.sh`:

```bash
#!/usr/bin/env bash
#
# Daily Garmin sync. Run by launchd; also runnable by hand.
#
# set -e : abort on any command failing — this is why validate.py's
#          non-zero exit stops the commit from happening
# set -u : abort on undefined variable
# set -o pipefail : a failure anywhere in a pipe fails the whole pipe
set -euo pipefail

# Resolve the repo root from this script's own location, so it works
# regardless of what directory it's invoked from.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

UV=/opt/homebrew/bin/uv     # absolute path: launchd has almost no PATH

echo "── sync $(date '+%F %T') ──"

$UV run python -m training_data.fetch
$UV run python -m training_data.decode
$UV run python -m training_data.rollup
$UV run python -m training_data.validate    # exits 1 on failure → set -e aborts

if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "chore(data): sync $(date +%F)"
  git push
  echo "✓ pushed $(date +%F)"
else
  echo "· nothing new"
fi
```

```bash
chmod +x bin/sync.sh
```

### 13.2 Why `chore(data):` specifically

You'll generate ~350 automated commits a year. The scope keeps them filterable so your
actual work stays readable:

```bash
git log --invert-grep --grep='^chore(data)'       # human commits only
git log --oneline --grep='^chore(data)' | wc -l   # how many syncs have run
```

This follows COMMITS.md: `chore` for maintenance with no production impact, with a scope
naming the affected area.

### 13.3 Test it by hand

```bash
./bin/sync.sh
```

Watch it run all five stages and push. If the push prompts for credentials, fix that now
with `gh auth login` — under `launchd` there is no terminal to prompt to, so it would hang
forever.

```bash
git add bin/sync.sh
git commit -m "feat(sync): add end-to-end sync entrypoint"
```

---

## Part 14 — Scheduling with launchd

### 14.1 The plist template

Create `~/code/training-data/etc/com.enri.garmin-sync.plist.tmpl`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.enri.garmin-sync</string>

  <key>ProgramArguments</key>
  <array>
    <string>__REPO__/bin/sync.sh</string>
  </array>

  <!-- 06:30 daily: after overnight sleep and HRV have been processed,
       before you're awake and looking at the numbers. -->
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>6</integer>
    <key>Minute</key><integer>30</integer>
  </dict>

  <key>StandardOutPath</key><string>__REPO__/.sync.log</string>
  <key>StandardErrorPath</key><string>__REPO__/.sync.err</string>

  <key>WorkingDirectory</key><string>__REPO__</string>

  <!-- launchd gives a nearly empty environment. Without this, git and uv
       aren't found and the job fails with a confusing "command not found". -->
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
</dict>
</plist>
```

`__REPO__` gets substituted at install time, which is why this is a template and the
generated plist isn't tracked anywhere.

### 14.2 `bin/bootstrap.sh` — the new-machine story

Create `~/code/training-data/bin/bootstrap.sh`:

```bash
#!/usr/bin/env bash
#
# One-time setup on a new machine.
# Usage: git clone ... && cd training-data && ./bin/bootstrap.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

REPO="$(pwd)"
PLIST="$HOME/Library/LaunchAgents/com.enri.garmin-sync.plist"

command -v uv >/dev/null || { echo "Install uv first: brew install uv"; exit 1; }
command -v gh >/dev/null || { echo "Install gh first: brew install gh"; exit 1; }

echo "→ Installing Python dependencies from the lockfile"
uv sync --frozen        # --frozen = install exactly what's locked, like npm ci

echo "→ Checking Garmin authentication"
if [[ ! -f "$HOME/.garminconnect/garmin_tokens.json" ]]; then
  echo "  No token found. Starting interactive login (expect an MFA prompt)."
  uv run python bin/login.py
else
  echo "  Existing token found."
fi

echo "→ Installing the launchd agent"
mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__REPO__|$REPO|g" etc/com.enri.garmin-sync.plist.tmpl > "$PLIST"

# bootstrap/bootout are the modern replacements for load/unload.
launchctl bootout "gui/$(id -u)/com.enri.garmin-sync" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "✓ Done. Syncing daily at 06:30."
echo "  Run now:  launchctl kickstart -p gui/$(id -u)/com.enri.garmin-sync"
```

```bash
chmod +x bin/bootstrap.sh
./bin/bootstrap.sh
```

### 14.3 launchd commands you'll actually use

```bash
# Trigger immediately, without waiting for 06:30
launchctl kickstart -p gui/$(id -u)/com.enri.garmin-sync

# Is it loaded? What was the last exit code?
launchctl print gui/$(id -u)/com.enri.garmin-sync | head -30

# Watch the logs
tail -f ~/code/training-data/.sync.log
tail -f ~/code/training-data/.sync.err

# Unload (e.g. before editing the plist)
launchctl bootout gui/$(id -u)/com.enri.garmin-sync
```

`bootstrap` / `bootout` / `kickstart` are the modern domain-target syntax. You'll find
`launchctl load` and `unload` in older guides; they're deprecated and give worse errors.

### 14.4 The sleep behaviour that makes this work

`StartCalendarInterval` has a specific property: if the scheduled time passes while your
Mac is asleep, launchd runs the job **once** on wake. `cron` just skips it silently. Since
your MacBook is closed at 06:30 most mornings, this is the entire reason for choosing
launchd.

```bash
git add etc/ bin/bootstrap.sh
git commit -m "feat(launchd): add scheduled daily sync agent and bootstrap"
```

---

## Part 15 — Wire into your dotfiles

### 15.1 Shell aliases

Add to wherever your aliases live (`~/.zshrc`, or a sourced file like
`~/.config/zsh/aliases.zsh`):

```zsh
# ── training-data ──────────────────────────────────────────────
export TRAINING_DATA="$HOME/code/training-data"

alias td="cd $TRAINING_DATA"
alias tdsync="$TRAINING_DATA/bin/sync.sh"
alias tdlog="tail -50 $TRAINING_DATA/.sync.log"
alias tderr="tail -50 $TRAINING_DATA/.sync.err"

# Run the scheduled job now instead of waiting for 06:30
alias tdrun="launchctl kickstart -p gui/$(id -u)/com.enri.garmin-sync"

# Is the sync healthy? Uses your existing eza and bat.
tdstatus() {
  echo "Last sync commit:"
  git -C "$TRAINING_DATA" log -1 --grep='^chore(data)' --format='  %ar — %s'
  echo "\nTable freshness:"
  eza -l --time-style=relative "$TRAINING_DATA/tables/"
  echo "\nRecent errors:"
  tail -5 "$TRAINING_DATA/.sync.err" 2>/dev/null || echo "  (none)"
}

# This week's numbers in bat
tdweek() {
  bat "$TRAINING_DATA/tables/weekly-$(date +%Y).csv" --language csv
}
```

Commit them to your dotfiles:

```bash
dot add ~/.zshrc          # or your aliases file
dot commit -m "feat(zsh): add training-data aliases and status helper"
dot push
```

### 15.2 Brewfile

If you keep one:

```ruby
brew "uv"    # Python toolchain for training-data
brew "gh"
```

### 15.3 Confirm the security boundary once more

```bash
# Should print a matching ignore rule, not nothing:
dot check-ignore -v ~/.garminconnect/garmin_tokens.json

# Should show the token is NOT tracked:
dot ls-files ~/.garminconnect/ 2>/dev/null || echo "not tracked — correct"

# The repo itself shouldn't be tracked in dotfiles either:
dot ls-files ~/code/ 2>/dev/null || echo "not tracked — correct"
```

### 15.4 Final map of what lives where

```
~/.dotfiles                       ← bare repo (dotfiles)
~/.zshrc                          ← TRACKED by dotfiles (aliases above)
~/.gitignore                      ← TRACKED by dotfiles (excludes .garminconnect/)
~/.garminconnect/                 ← IGNORED. Holds the MFA-bypassing token.
~/Library/LaunchAgents/
  └── com.enri.garmin-sync.plist  ← IGNORED. Generated by bootstrap.sh.
~/code/training-data/             ← its own repo, separate from dotfiles
```

---

## Part 16 — Connect Claude

### 16.1 GitHub connector — for quick questions

The Projects GitHub integration syncs **selected file names and contents on one branch**
into project knowledge, and everything selected has to fit in the context window. It does
not fetch commit history or PRs, and it cannot read binary files.

So in your `Ironman Training & Badminton` project, select **only**:

- `ATHLETE.md`
- `LOG.md`
- `tables/*.csv`

Do not point it at the repo root. `raw/` is binary and `streams/` would exhaust the context
budget while adding nothing. Hit **Sync now** after each week's push.

### 16.2 Claude Code on the local clone — for the weekly review

This is the bigger upgrade. The connector reads files *into context*; Claude Code can
*execute* over them. "Compare my RHR over three months and analyse the trend" becomes an
actual computation with pandas, rather than a reading-comprehension exercise over a CSV.

Create `~/code/training-data/CLAUDE.md`:

```markdown
# CLAUDE.md — coaching context

You are my endurance coach. Read `ATHLETE.md` first for goals, zones, and thresholds,
then `LOG.md` for what we discussed last time.

## Where the data lives
- `tables/weekly-*.csv` — **start here** for any trend question
- `tables/wellness-*.csv` — one row per day
- `tables/activities-*.csv` — one row per session
- `activities/YYYY/MM/*.json` — per-session detail including laps and zone time
- `streams/YYYY/MM/*.csv` — 1-minute resolution, for pacing and drift analysis
- `raw/` — FIT archive. Do not read; binary and huge.

DuckDB reads these directly, no import step:
`SELECT * FROM 'tables/wellness-*.csv' WHERE date > '2026-06-01'`

## Working style
- Trends over single days. Daily HRV and readiness are noisy; use 7-day windows.
- Always check zone distribution before commenting on intensity. Grey-zone drift is
  invisible in volume numbers alone.
- Badminton is HR-only (no power or pace). Treat it as load, not as a quality session.
- Note when equipment changed — it creates step changes that look like fitness changes.
- At the end of a review, append your findings to `LOG.md` under a dated heading.
```

Then open a session:

```bash
cd ~/code/training-data && claude
```

### 16.3 Close the loop

The `LOG.md` append is what turns this from an analysis tool into something resembling an
actual coaching relationship. Without it, every session starts cold and you get generic
advice. With it, Claude picks up where it left off.

```bash
git add CLAUDE.md
git commit -m "docs: add Claude Code coaching context"
```

---

## Part 17 — Backfill history

**Do this last, once the daily pipeline has run cleanly for a few days.**

Backfilling is where you'll trip rate limits. Garmin will return 429s, and aggressive
retrying risks a temporary block — which would also break the daily sync you just got
working.

Rules:

- Chunk by month, oldest first
- 4–5 seconds between activity downloads (not the 1.5s of normal operation)
- Checkpoint `.sync-state.json` after each month so an interruption resumes
- Commit per month, not one giant commit — a multi-GB push can hit GitHub's 2 GB push cap
- Run it overnight; expect several hours for multiple years

Add `src/training_data/backfill.py` as a variant of `fetch.py` taking a date range and a
longer sleep, then:

```bash
uv run python -m training_data.backfill --from 2023-01 --to 2026-07 --sleep 5
```

---

## Runbook — when it breaks

| Symptom | Likely cause | Action |
|---|---|---|
| `401` on login | Garmin changed the auth flow again | Check `cyberjunky/python-garminconnect` issues; bump the pin |
| `403` or CAPTCHA | Cloudflare flagged you | Stop for a few hours. Confirm you're on home Wi-Fi, not a VPN |
| `429` | Rate limited | Increase `RATE_LIMIT_SLEEP`, shrink the window, retry tomorrow |
| Token rejected | Cache went stale | `rm -rf ~/.garminconnect && uv run python bin/login.py` |
| Silently empty columns | Field key paths changed | `validate.py` should catch it; re-inspect raw JSON, fix `rollup.py` |
| Job never runs | launchd PATH or path substitution | `launchctl print gui/$(id -u)/com.enri.garmin-sync`, then check `.sync.err` |
| Push rejected, too large | Backfill in one commit | Split by month |
| Push hangs forever | Git prompting for credentials | `gh auth login`, then test `./bin/sync.sh` by hand |
| `ModuleNotFoundError` | Running `python` instead of `uv run python` | Always prefix with `uv run` |

### Two standing risks worth internalising

**1. This is an unofficial client.** Garmin's Connect Developer Program requires applicants
to be a legal entity and rejects personal-use applications, so there's no sanctioned path
for an individual. Automated access outside the official API isn't something Garmin
formally blesses. Budget for it breaking a few times a year, and don't build anything on
top of this you can't afford to lose.

**2. GitHub is not your backup.** Garmin Connect is one copy, this repo is a second. That's
two. If this data matters to you long term, keep a third somewhere off-platform.

---

## Build checklist

Work top to bottom. Don't start a phase until the previous one runs clean.

```
Setup
[ ] brew install uv gh; gh auth status is clean
[ ] Dotfiles ~/.gitignore excludes .garminconnect/ — VERIFIED with dot check-ignore
[ ] Repo created private at ~/code/training-data (NOT in ~/Documents)

Skeleton
[ ] Folder structure, .gitignore, .gitattributes
[ ] athlete.toml with your real zones and thresholds
[ ] ATHLETE.md and LOG.md written

Python
[ ] uv init --package, dependencies added, uv.lock committed
[ ] Seven empty module files created

Auth  ← hardest part; don't proceed past this
[ ] bin/login.py runs, token written with 0600 perms
[ ] Smoke test prints your name and a step count
[ ] docs/api-notes.md records VERIFIED method names and field paths

Pipeline
[ ] fetch.py downloads activities (unzipping the ORIGINAL zip correctly)
[ ] Second run of fetch.py downloads 0 new — idempotency confirmed
[ ] decode.py produces summary JSON + 1-min CSV, no lat/lon in the CSV
[ ] metrics.py: CTL/ATL/TSB sanity-checked by hand
[ ] rollup.py produces three year-partitioned tables
[ ] rollup.py field paths replaced with VERIFIED ones from api-notes.md
[ ] validate.py catches a deliberately broken file and exits 1

Automation
[ ] bin/sync.sh runs end to end and pushes without prompting
[ ] Commits use the chore(data): scope
[ ] launchd agent installed; kickstart runs it successfully
[ ] Logs appear in .sync.log

Dotfiles
[ ] Aliases added and committed to dotfiles
[ ] uv and gh added to Brewfile
[ ] Security boundary re-verified

Claude
[ ] Connector syncing ONLY ATHLETE.md, LOG.md, tables/
[ ] CLAUDE.md written; a Claude Code review session tested
[ ] LOG.md has its first real entry

Finally
[ ] Backfill, chunked by month, overnight
```

---

## A note on the design

The point of all this is better feedback, not just better plumbing. Readiness and HRV
scores are noisy day to day and only become meaningful as 7-day trends — which is exactly
why `weekly-YYYY.csv` is the table to reach for first, and why the rollups exist at all.

Build it to surface trends, and resist letting a single red morning score override a
session you feel good about.
