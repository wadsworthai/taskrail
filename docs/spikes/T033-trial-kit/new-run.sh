#!/bin/sh
# Create one trial run from the seed bundle: a bare remote, the orchestrator's clone, the
# trial-local permission files and an evidence directory.
# Usage: new-run.sh <name>        e.g. new-run.sh claude, new-run.sh opencode
set -eu
. "$(dirname -- "$0")/lib.sh"
RUN=$(run_dir "${1:-}")
[ ! -e "$RUN" ] || { echo "$RUN already exists" >&2; exit 2; }
mkdir -p "$RUN/evidence/status" "$RUN/evidence/snapshots"

git init -q --bare -b main "$RUN/origin.git"
git -C "$RUN/origin.git" fetch -q "$KIT/seed/seed.bundle" main:main
git clone -q "$RUN/origin.git" "$RUN/repo"
cd "$RUN/repo"
git config user.name "Trial Maintainer"
git config user.email "trial@example.invalid"

# The same allowlist for both agents; @REPO@ becomes this clone's absolute path.
sed "s|@REPO@|$RUN/repo|g" "$KIT/bin/claude-settings.local.json" > .claude/settings.local.json
sed "s|@REPO@|$RUN/repo|g" "$KIT/bin/opencode.json" > opencode.json
printf '.claude/settings.local.json\nopencode.json\n' >> .git/info/exclude

.taskrail/bin/taskrail validate > /dev/null

{
  echo "run:       $(basename "$RUN")"
  echo "created:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "taskrail:  $(cat "$KIT/taskrail/COMMIT")"
  echo "seed:      $(cat "$KIT/seed/COMMIT")"
  echo "claude:    $(claude --version 2>/dev/null < /dev/null || echo 'not found')"
  echo "opencode:  $(opencode --version 2>/dev/null < /dev/null || echo 'not found')"
  echo "git:       $(git --version)"
  echo "uv:        $(uv --version)"
  echo "python:    $(python3 --version)"
} > "$RUN/evidence/environment.txt"
if command -v opencode > /dev/null 2>&1; then
  opencode debug agent general < /dev/null > "$RUN/evidence/opencode-agent-general.json" 2>&1 || true
  opencode debug skill < /dev/null 2>&1 | python3 -c 'import json, sys
try:
    print("\n".join(sorted(s["name"] for s in json.load(sys.stdin))))
except Exception as error:
    print("could not list skills:", error)' > "$RUN/evidence/opencode-skills.txt"
fi

cat > "$RUN/evidence/timeline.md" <<'TL'
# Timeline

Times are local wall-clock. One row per event: every prompt you type, every answer from the
answer sheet, every permission prompt (allowed or denied), every merge, compaction or restart,
and anything unexpected.

| Time | Event | What prompted it | What you did or answered | Answer sheet row |
|------|-------|------------------|--------------------------|------------------|
TL
echo "run ready: $RUN"
echo "orchestrator directory: $RUN/repo"
