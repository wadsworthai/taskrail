#!/bin/sh
# Close a run's evidence: a final snapshot, the checks and `taskrail validate` on the remote's
# main, the decision records, and copies of the agents' transcripts for this run's directory.
# Usage: finish.sh <name>
set -eu
. "$(dirname -- "$0")/lib.sh"
RUN=$(run_dir "${1:-}")
NAME=$(basename "$RUN")
"$KIT/bin/snapshot.sh" "$NAME" final
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
git clone -q "$RUN/origin.git" "$W/main"
{
  echo "main: $(git -C "$W/main" log -1 --format='%h %s')"
  echo "== taskrail validate"; (cd "$W/main" && .taskrail/bin/taskrail validate 2>&1) || true
  echo "== test"; (cd "$W/main" && python3 -m unittest discover -s tests -q 2>&1) || true
  echo "== lint"; (cd "$W/main" && python3 -m compileall -q wordstat tests 2>&1 && echo ok) || true
  echo "== backlog"; (cd "$W/main" && .taskrail/bin/taskrail list 2>&1) || true
  echo "== merge log"; cat "$RUN/evidence/merges.log" 2>/dev/null || echo "(none)"
} > "$RUN/evidence/final.txt"
[ -d "$W/main/docs" ] && cp -R "$W/main/docs" "$RUN/evidence/docs-on-main"

# Claude Code: ~/.claude/projects/<directory with non-alphanumerics replaced by ->/
project=$(printf '%s' "$RUN/repo" | sed 's/[^A-Za-z0-9]/-/g')
if [ -d "$HOME/.claude/projects/$project" ]; then
  mkdir -p "$RUN/evidence/transcripts/claude"
  cp -R "$HOME/.claude/projects/$project/." "$RUN/evidence/transcripts/claude/"
fi
# OpenCode: `session list` shows only top-level sessions, so export those in this run's clone and
# every lane's child session, whose IDs are the lane handles recorded in the run files.
if command -v opencode > /dev/null 2>&1; then
  mkdir -p "$RUN/evidence/transcripts/opencode"
  {
    (cd "$RUN/repo" && opencode session list --format json < /dev/null 2> /dev/null) \
      | python3 -c 'import json, sys
text = sys.stdin.read().strip()
for s in (json.loads(text) if text else []):
    if s.get("directory", "").startswith(sys.argv[1]):
        print(s["id"])' "$RUN/repo"
    common=$(git -C "$RUN/repo" rev-parse --path-format=absolute --git-common-dir)
    python3 -c 'import glob, json, sys
for path in glob.glob(sys.argv[1] + "/taskrail/runs/*.json"):
    for task in json.load(open(path)).get("tasks", {}).values():
        handle = task.get("handle") or ""
        if handle.startswith("ses_"):
            print(handle)' "$common"
  } | sort -u | while read -r id; do
    (cd "$RUN/repo" && opencode export "$id" < /dev/null > "$RUN/evidence/transcripts/opencode/$id.json" 2> /dev/null) || true
  done
  rmdir "$RUN/evidence/transcripts/opencode" 2> /dev/null || true
fi
echo "evidence closed: $RUN/evidence (see final.txt)"
