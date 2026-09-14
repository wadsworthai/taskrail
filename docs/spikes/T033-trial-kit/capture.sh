#!/bin/sh
# Save `taskrail autopilot status --json` every INTERVAL seconds (default 60) into
# evidence/status/. Read-only: status takes no lock and never fetches. Stop it with Ctrl-C.
# Usage: capture.sh <name> [interval-seconds]
set -eu
. "$(dirname -- "$0")/lib.sh"
RUN=$(run_dir "${1:-}")
INTERVAL=${2:-60}
cd "$RUN/repo"
echo "capturing status every ${INTERVAL}s into $RUN/evidence/status (Ctrl-C to stop)"
while :; do
  ts=$(utc)
  if ! .taskrail/bin/taskrail autopilot status --json > "$RUN/evidence/status/$ts.json" 2> "$RUN/evidence/status/$ts.err"; then
    echo "$ts: status exited non-zero, see $ts.err"
  fi
  [ -s "$RUN/evidence/status/$ts.err" ] || rm -f "$RUN/evidence/status/$ts.err"
  sleep "$INTERVAL"
done
