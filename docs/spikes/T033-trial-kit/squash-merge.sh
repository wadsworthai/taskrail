#!/bin/sh
# Stand in for a code host's "squash and merge": squash a task branch from the trial remote onto
# its main as one commit titled like the pull request, and push. Logs to evidence/merges.log.
# Usage: squash-merge.sh <name> <branch> "<pull request title>"
set -eu
. "$(dirname -- "$0")/lib.sh"
RUN=$(run_dir "${1:-}")
BRANCH=${2:?usage: squash-merge.sh <name> <branch> "<title>"}
TITLE=${3:?usage: squash-merge.sh <name> <branch> "<title>"}
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
git clone -q "$RUN/origin.git" "$W/c"
cd "$W/c"
git config user.name "Trial Maintainer"
git config user.email "trial@example.invalid"
git rev-parse -q --verify "refs/remotes/origin/$BRANCH" > /dev/null \
  || { echo "no branch $BRANCH on the trial remote" >&2; exit 3; }
before=$(git rev-parse --short main)
head=$(git rev-parse --short "origin/$BRANCH")
if git merge-base --is-ancestor main "origin/$BRANCH"; then based=yes; else based=no; fi
if ! git merge --squash "origin/$BRANCH" > "$W/merge.out" 2>&1; then
  cat "$W/merge.out" >&2
  printf '%s CONFLICT branch=%s head=%s main=%s based-on-main=%s\n' "$(utc)" "$BRANCH" "$head" "$before" "$based" >> "$RUN/evidence/merges.log"
  echo "squash merge of $BRANCH conflicts with main; nothing was merged" >&2
  exit 1
fi
if git diff --cached --quiet; then
  echo "squashing $BRANCH changes nothing; nothing was merged" >&2
  exit 1
fi
git commit -q -m "$TITLE"
git push -q origin main
after=$(git rev-parse --short HEAD)
printf '%s MERGED branch=%s head=%s main=%s->%s based-on-main=%s title=%s\n' "$(utc)" "$BRANCH" "$head" "$before" "$after" "$based" "$TITLE" >> "$RUN/evidence/merges.log"
echo "squash-merged $BRANCH into main as $after: $TITLE"
