#!/usr/bin/env bash
#
# set -e : abort on any command failing
# set -u : abort on an undefined variable
# set -o pipefail : a failure anywhere in a pipe fails the whole pipe
set -euo pipefail

# Resolve the repo root from this script's own location, so it works
# regardless of what directory it is invoked from.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

UV=/opt/homebrew/bin/uv           # absolute path: launchd has almost no PATH
export PYTHONUNBUFFERED=1         # so .sync.log fills as the run goes, not at the end

echo "── sync $(date '+%F %T') ──"

"$UV" run python -m training_data.fetch "$@"
"$UV" run python -m training_data.tables
