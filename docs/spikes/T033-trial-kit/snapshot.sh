#!/bin/sh
# Save a labelled snapshot of the run: status, claims, run files, branches of the clone and the
# remote, worktrees and their uncommitted changes.
# Usage: snapshot.sh <name> <label>      e.g. snapshot.sh claude T001-plan-gate
set -eu
. "$(dirname -- "$0")/lib.sh"
RUN=$(run_dir "${1:-}")
LABEL=$(printf '%s' "${2:?usage: snapshot.sh <name> <label>}" | tr -c 'A-Za-z0-9._-' '-')
D="$RUN/evidence/snapshots/$(utc)-$LABEL"
mkdir -p "$D"
cd "$RUN/repo"
TR=.taskrail/bin/taskrail
$TR autopilot status --json > "$D/status.json" 2>&1 || true
$TR autopilot status > "$D/status.txt" 2>&1 || true
$TR claims --json > "$D/claims.json" 2>&1 || true
common=$(git rev-parse --path-format=absolute --git-common-dir)
[ -d "$common/taskrail/runs" ] && cp -R "$common/taskrail/runs" "$D/runs" || true
git log --all --graph --oneline --decorate > "$D/repo-log.txt"
git -C "$RUN/origin.git" log --all --graph --oneline --decorate > "$D/origin-log.txt"
git worktree list > "$D/worktrees.txt"
git worktree list --porcelain | sed -n 's/^worktree //p' | while read -r wt; do
  printf '== %s\n' "$wt"
  git -C "$wt" status --short --branch
done > "$D/worktree-status.txt"
echo "snapshot: $D"
