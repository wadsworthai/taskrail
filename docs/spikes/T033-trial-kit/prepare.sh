#!/bin/sh
# Build the throwaway T033 trial kit: taskrail's source at one pinned commit, the kit's scripts,
# and one seed repository bundled so that every run starts from the same commit.
#
# Usage: prepare.sh <absolute-kit-dir> [taskrail-commit]   (default commit: 977064f)
set -eu
[ $# -ge 1 ] || { echo "usage: prepare.sh <absolute-kit-dir> [taskrail-commit]" >&2; exit 2; }
KIT=$1
COMMIT=${2:-977064f}
case "$KIT" in /*) ;; *) echo "the kit directory must be an absolute path" >&2; exit 2 ;; esac
[ ! -e "$KIT" ] || { echo "$KIT already exists; remove it or choose another path" >&2; exit 2; }
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE_REPO=$(git -C "$HERE" rev-parse --show-toplevel)

mkdir -p "$KIT/bin" "$KIT/taskrail" "$KIT/runs" "$KIT/seed"
git -C "$SOURCE_REPO" archive "$COMMIT" | tar -x -C "$KIT/taskrail"
git -C "$SOURCE_REPO" rev-parse "$COMMIT^{commit}" > "$KIT/taskrail/COMMIT"
for f in "$HERE"/*.sh "$HERE"/*.py "$HERE"/*.json "$HERE"/*.md; do [ ! -e "$f" ] || cp "$f" "$KIT/bin/"; done
chmod +x "$KIT"/bin/*.sh "$KIT"/bin/*.py

S="$KIT/seed/repo"
git init -q -b main "$S"
cp -R "$HERE/seed/." "$S/"
cd "$S"
git config user.name "Trial Maintainer"
git config user.email "trial@example.invalid"

cat > AGENTS.md <<'EOF'
# Working on wordstat

- Python 3 standard library only; add no dependencies.
- Checks: `python3 -m unittest discover -s tests -q` (test) and
  `python3 -m compileall -q wordstat tests` (lint).
- Every user-visible change appends one bullet at the end of the `Unreleased` section of
  `CHANGELOG.md`.
- User-facing behaviour follows `docs/policy.md`. Changing that document is the maintainer's
  decision.
- Commit messages: Conventional Commits with the scope `wordstat`, e.g. `fix(wordstat): ...`.
- The backlog is `TODO.md`, managed with taskrail: use the taskrail skills and run the CLI as
  `.taskrail/bin/taskrail`.
EOF
printf '@AGENTS.md\n' > CLAUDE.md

uv run --quiet --project "$KIT/taskrail" taskrail init \
  --integration claude --integration opencode > /dev/null
ln -s "$KIT/taskrail" .taskrail/src

python3 - <<'EOF'
import re
path = ".taskrail/config.toml"
text = open(path, encoding="utf-8").read()
text, n = re.subn(r'^version = .*$',
                  'version = "local:.taskrail/src"   # taskrail source pinned for this repository',
                  text, count=1, flags=re.M)
assert n == 1, "no version line"
for old, new in (('# test = "make test"', 'test = "python3 -m unittest discover -s tests -q"'),
                 ('# lint = "make lint"', 'lint = "python3 -m compileall -q wordstat tests"')):
    assert old in text, old
    text = text.replace(old, new)
text += '''
[autopilot]
enabled = false
max_lanes = 3
governing = ["AGENTS.md", "CLAUDE.md", "docs/policy.md"]
escalate_gates = ["spike:decide"]
silent_minutes = 20
notify = '{ date -u +%Y-%m-%dT%H:%M:%SZ; echo "event=$TASKRAIL_EVENT run=$TASKRAIL_RUN task=$TASKRAIL_TASK"; cat; echo; } >> "$(git rev-parse --path-format=absolute --git-common-dir)/../../evidence/notify.log"'
notify_on = ["escalation", "lane-done", "lane-failed"]

[[autopilot.resource]]
name = "PORT"
values = ["54301", "54302", "54303"]
'''
open(path, "w", encoding="utf-8").write(text)
EOF

TR=.taskrail/bin/taskrail
$TR epic add --name "wordstat 0.2" --objective "Richer statistics without breaking the default output" \
  --done-when "the five tasks below are merged" > /dev/null
$TR new --epic E01 --kind feature --pts 1 --title "Add a --lines flag that also reports the line count" \
  --description "wordstat FILE --lines prints lines: N after words: N; stats() returns the line count." > /dev/null
$TR new --epic E01 --kind feature --pts 2 --depends-on T001 \
  --title "Add a --json flag that prints the statistics as one JSON object" \
  --description "Includes lines when --lines is given; the plain text output stays the default (docs/policy.md)." > /dev/null
$TR new --epic E01 --kind bug --pts 1 --title "Stop miscounting words around repeated whitespace and newlines" \
  --description "wordstat reports 3 words for 'a b ' and for 'a  b', and 1 for 'a<newline>b': stats() splits on single spaces." > /dev/null
$TR new --epic E01 --kind chore --pts 1 --title "Document the exit code for an unreadable file in the output policy" \
  --description "wordstat exits 1 when the file cannot be read, but docs/policy.md lists only 0 and 2." > /dev/null
$TR new --epic E01 --kind spike --pts 2 --title "Decide whether word counting should follow Unicode word boundaries" \
  --description "Compare str.split with a regular expression on sample texts with punctuation and non-Latin scripts; recommend one." > /dev/null
$TR validate > /dev/null

git add -A
git commit -q -m "chore(wordstat): start wordstat and its backlog"
git bundle create -q "$KIT/seed/seed.bundle" main
git rev-parse HEAD > "$KIT/seed/COMMIT"
echo "kit ready: $KIT"
echo "taskrail $(cat "$KIT/taskrail/COMMIT")"
echo "seed     $(cat "$KIT/seed/COMMIT")"
