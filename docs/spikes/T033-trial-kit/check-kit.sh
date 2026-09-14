#!/bin/sh
# Check the kit through the taskrail CLI alone, without any agent: seed a run named "dryrun",
# exercise the refusal, start, next, the escalation flag, notify, one manual lane from claim to
# a squash merge proved by `autopilot merged`, the capture, snapshot and finish scripts, and
# OpenCode's reading of the trial config. Removes the dry run afterwards unless KEEP=1.
# Usage: check-kit.sh
set -eu
. "$(dirname -- "$0")/lib.sh"
NAME=dryrun
RUN=$(run_dir "$NAME")
BIN="$KIT/bin"
[ ! -e "$RUN" ] || { echo "$RUN exists; remove it first" >&2; exit 2; }

ok() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; exit 1; }
field() { python3 -c 'import json, sys
d = json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."):
    d = d[int(k)] if isinstance(d, list) else d[k]
print(d if not isinstance(d, (dict, list)) else json.dumps(d))' "$@"; }

"$BIN/new-run.sh" "$NAME" > /dev/null || fail "new-run"
ok "new-run: seeded $RUN"
cd "$RUN/repo"
TR=.taskrail/bin/taskrail
T="$RUN/check"
mkdir -p "$T"

$TR validate > "$T/validate.txt" 2>&1 && ok "validate: $(cat "$T/validate.txt")"
[ "$($TR --version)" = "taskrail 0.2.0.dev0" ] && ok "pinned taskrail runs through .taskrail/src ($(cat "$KIT/taskrail/COMMIT" | cut -c1-7))"
set +e; $TR autopilot start --count 5 --json > "$T/start-disabled.json" 2> "$T/start-disabled.err"; code=$?; set -e
[ $code -eq 5 ] && ok "start while disabled exits 5: $(cat "$T/start-disabled.err")" || fail "start while disabled exited $code"

"$BIN/enable-autopilot.sh" "$NAME" > /dev/null && ok "enable-autopilot: committed and pushed"
$TR autopilot start --count 5 --json > "$T/start.json"
R=$(field "$T/start.json" run.id)
ok "start --count 5: run $R"

$TR autopilot next --run "$R" --json > "$T/next.json"
python3 - "$T/next.json" <<'PY' > "$T/next.txt"
import json, sys
d = json.load(open(sys.argv[1]))
print("dispatched:", [(t["id"], t["resources"], t["environment"]) for t in d["dispatch"]])
print("limited_by:", d.get("limited_by"), "skipped:", [(s["id"], s.get("reason")) for s in d.get("skipped", [])])
PY
grep -q "dispatched: \[('T001'" "$T/next.txt" && grep -q "'T003'" "$T/next.txt" && grep -q "'T004'" "$T/next.txt" \
  && ! grep -q "'T005'" "$T/next.txt" && ok "next dispatches T001, T003, T004 with ports; $(sed -n 2p "$T/next.txt")" \
  || { cat "$T/next.txt"; fail "unexpected first dispatch"; }

lane() {  # lane <ID>: create the worktree and claim, as a lane would
  $TR show "$1" --json --fetch > "$T/show-$1.json"
  b=$(field "$T/show-$1.json" branch); w=$(field "$T/show-$1.json" worktree); o=$(field "$T/show-$1.json" base.onto)
  git worktree add -q --no-track "$w" -b "$b" "$o"
  (cd "$w" && $TR claim "$1" --run "$R" --json > "$T/claim-$1.json")
  $TR autopilot lane "$1" --run "$R" --handle "dry-$1" --state running > /dev/null
  printf '%s\n' "$w"
}
W1=$(lane T001); W4=$(lane T004)
ok "lanes T001 and T004: worktrees created with --no-track and claimed with --run"

printf '\n| 1 | file cannot be read |\n' >> "$W4/docs/policy.md"
$TR autopilot lane T004 --run "$R" --state gate --gate scope > /dev/null
$TR autopilot status --run "$R" --json > "$T/status-governing.json"
python3 - "$T/status-governing.json" <<'PY' && ok "status flags T004's uncommitted docs/policy.md change as a governing escalation"
import json, sys
d = json.load(open(sys.argv[1]))
t = [t for r in d["runs"] for t in r["tasks"] if t["id"] == "T004"][0]
assert t["governing_touched"] == ["docs/policy.md"] and t["escalation"] == ["governing"], t
PY
$TR autopilot notify --event escalation --run "$R" --task T004 --message "dry run" --json > "$T/notify.json"
grep -q "event=escalation run=$R task=T004" "$RUN/evidence/notify.log" && ok "notify appends to evidence/notify.log"

(
  cd "$W1"
  printf '\nRun `python3 -m wordstat --help` for the options.\n' >> README.md
  printf -- '- Point the README at --help (dry run).\n' >> CHANGELOG.md
  TASKRAIL_RESOURCE_PORT=$(field "$T/next.json" dispatch.0.environment.TASKRAIL_RESOURCE_PORT) \
    python3 -m unittest discover -s tests -q > "$T/checks-T001.txt" 2>&1 || { cat "$T/checks-T001.txt"; exit 1; }
  git add -A && git commit -q -m "docs(wordstat): point the README at --help (dry run)"
  $TR done T001 > /dev/null && git commit -q -am "chore(wordstat): mark T001 done"
  $TR review T001 --json > "$T/review.json"
  $TR review T001 --publish --json --type feat --scope wordstat > "$T/publish.json"
)
ok "T001 lane: checks $(tail -1 "$T/checks-T001.txt"), done, review, publish pushed=$(field "$T/publish.json" push.pushed)"
[ "$(field "$T/review.json" rebase.needed)" = False ] && ok "review --json: no rebase needed"
$TR autopilot lane T001 --run "$R" --state handed-off > /dev/null
TITLE=$(field "$T/publish.json" pull_request.title)
BRANCH=$(field "$T/show-T001.json" branch)
"$BIN/squash-merge.sh" "$NAME" "$BRANCH" "$TITLE" > "$T/merge.txt" && ok "squash-merge: $(cat "$T/merge.txt")"

$TR autopilot merged T001 --run "$R" --cleanup --json > "$T/merged.json"
[ "$(field "$T/merged.json" merged)" = True ] && [ ! -e "$W1" ] \
  && ok "merged --cleanup: merged via $(field "$T/merged.json" via), worktree removed" \
  || { cat "$T/merged.json"; fail "merge not proved or worktree kept"; }
$TR autopilot status --run "$R" --json > "$T/status-after.json"
python3 - "$T/status-after.json" <<'PY' && ok "status: T001 done-merged"
import json, sys
d = json.load(open(sys.argv[1]))
states = {t["id"]: t["state"] for r in d["runs"] for t in r["tasks"]}
assert states.get("T001") == "done-merged", states
PY

timeout 3 "$BIN/capture.sh" "$NAME" 1 > /dev/null 2>&1 || true
[ -n "$(ls "$RUN/evidence/status")" ] && ok "capture: $(ls "$RUN/evidence/status" | wc -l) status file(s) written"
"$BIN/snapshot.sh" "$NAME" dry-check > /dev/null && ok "snapshot: $(ls "$RUN/evidence/snapshots")"
"$BIN/finish.sh" "$NAME" > /dev/null && grep -q 'OK' "$RUN/evidence/final.txt" && ok "finish: checks pass on the remote's main"

if command -v opencode > /dev/null 2>&1; then
  (cd "$RUN/repo" && timeout 60 opencode debug config < /dev/null > "$T/opencode-config.json" 2>&1)
  python3 - "$T/opencode-config.json" <<'PY' && ok "opencode reads the trial config: model and permissions"
import json, sys
d = json.load(open(sys.argv[1]))
assert d["model"] == "github-copilot/claude-opus-5", d.get("model")
p = d["permission"]
assert p["bash"]["git push *"] == "ask" and p["bash"]["git *"] == "allow" and p["edit"] == "allow", p
PY
fi
python3 -m json.tool "$RUN/repo/.claude/settings.local.json" > /dev/null && ok "Claude Code settings file is valid JSON"

if [ "${KEEP:-0}" = 1 ]; then echo "kept $RUN"; else
  git -C "$RUN/repo" worktree list --porcelain | sed -n 's/^worktree //p' | tail -n +2 | while read -r w; do git -C "$RUN/repo" worktree remove --force "$w"; done
  rm -rf "$RUN"; echo "removed $RUN"
fi
