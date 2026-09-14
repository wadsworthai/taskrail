#!/bin/sh
# Set [autopilot].enabled = true on the trial mainline and push it to the trial remote.
# Usage: enable-autopilot.sh <name>
set -eu
. "$(dirname -- "$0")/lib.sh"
RUN=$(run_dir "${1:-}")
cd "$RUN/repo"
[ "$(git rev-parse --abbrev-ref HEAD)" = main ] || { echo "the orchestrator checkout is not on main" >&2; exit 2; }
git diff --quiet HEAD -- .taskrail/config.toml || { echo ".taskrail/config.toml has local changes; stop and record it" >&2; exit 2; }
grep -q '^enabled = false' .taskrail/config.toml || { echo "no 'enabled = false' line; stop and record it" >&2; exit 2; }
sed -i 's/^enabled = false.*$/enabled = true/' .taskrail/config.toml
.taskrail/bin/taskrail validate > /dev/null
git commit -q -m "chore(wordstat): enable the autopilot" -- .taskrail/config.toml
git push -q origin main
echo "autopilot enabled on main at $(git rev-parse --short HEAD) and pushed"
