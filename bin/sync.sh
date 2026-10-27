#!/usr/bin/env bash
#
# Garmin sync: fetch -> tables -> commit -> push.
#
# Run by launchd once a day, and by hand whenever you want fresh data:
#   ./bin/sync.sh                      # the usual 14-day refresh
#   ./bin/sync.sh --since 2026-09-01   # backfill from a date
#
# set -e : abort on any command failing
# set -u : abort on an undefined variable
# set -o pipefail : a failure anywhere in a pipe fails the whole pipe
set -euo pipefail

# Resolve the repo root from this script's own location, so it works
# regardless of what directory it is invoked from.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

UV=/opt/homebrew/bin/uv           # absolute path: launchd has almost no PATH
DATA=(raw tables LOG.md)          # the only paths this script ever commits
export PYTHONUNBUFFERED=1         # so .sync.log fills as the run goes, not at the end

# Under launchd nobody is watching a terminal, so a failed run says so on screen.
fail() {
  echo "✗ $1" >&2
  osascript -e "display notification \"$1\" with title \"training-data sync\"" || true
  exit 1
}
trap 'fail "Garmin sync failed. See .sync.err"' ERR

echo "── sync $(date '+%F %T') ──"

"$UV" run python -m training_data.fetch "$@"
"$UV" run python -m training_data.tables

# A rebase that stopped on a conflict leaves the repo on no branch at all, and
# every later run would quietly skip the commit. Refuse loudly instead.
branch="$(git branch --show-current)"
if [[ -z "$branch" || -d "$(git rev-parse --git-path rebase-merge)" ]]; then
  fail "Repo is mid-rebase or on a detached HEAD. Fix it by hand."
fi

# Data only ever lands on main. On a feature branch the files are refreshed on
# disk and left uncommitted; the next run on main picks them up.
if [[ "$branch" != "main" ]]; then
  echo "· on '$branch', not main: data refreshed, commit skipped"
  exit 0
fi

git add -- "${DATA[@]}"
if git diff --cached --quiet -- "${DATA[@]}"; then
  echo "· nothing new"
else
  # The trailing paths make this commit ONLY the data, even if you have other
  # changes staged.
  git commit --quiet -m "chore(data): sync $(date +%F)" -- "${DATA[@]}"
fi

# Push whenever main is ahead of GitHub. That includes a commit an earlier run
# made but could not push, so a network blip repairs itself the next day.
git pull --quiet --rebase --autostash     # pick up code merged on GitHub first
if [[ -n "$(git rev-list '@{u}..HEAD')" ]]; then
  git push --quiet
  echo "✓ pushed $(date +%F)"
fi
