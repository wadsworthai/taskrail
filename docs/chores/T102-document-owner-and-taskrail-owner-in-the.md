# T102 — Document `--owner` and `TASKRAIL_OWNER` in the claims section of `DESIGN.md`

## Goal

`--owner` is ten separate parser arguments and the suite's only way to simulate a second person,
yet no shipped skill names it and `DESIGN.md` mentions it twice, both times in passing. The
ordinary way a consumer sets a non-default owner is not the flag at all: it is the
`TASKRAIL_OWNER` environment variable, set once for a CI job, a shared machine or a service
account — the path no search for `--owner` can see. [T095](../spikes/T095-ask-whether-the-options-no-visible-repos.md)
put that to the human and the answer was "document it".

This chore adds one short paragraph to §6, beside the sentence that already states the owner
default. Nothing behavioural changes: no code, no tests, no CLI surface, no skills.

## What was re-verified, and what the task's row got wrong

Everything below was run in this worktree
(`/thezone/shared/repositories/utils/taskrail/.worktrees/T102-document-owner-and-taskrail-owner-in-the`)
at `5d605ca`, the branch's base.

**`--owner` is ten parser arguments — confirmed, and the tenth is not in `cli.py`.**

```
$ grep -rn "add_argument" src/taskrail/*.py src/taskrail/**/*.py | grep -i owner
src/taskrail/autopilot/merged.py:564:    parser.add_argument("--owner", help="who is cleaning up, to release a claim left behind (default: $TASKRAIL_OWNER or user@host)")
src/taskrail/cli.py:1487:    claim.add_argument("--owner", help="claim owner (default: $TASKRAIL_OWNER or user@host)")
src/taskrail/cli.py:1498:    release.add_argument("--owner")
src/taskrail/cli.py:1507:    reserve.add_argument("--owner")
src/taskrail/cli.py:1545:    new.add_argument("--owner")
src/taskrail/cli.py:1555:    workspace.add_argument("--owner", help="who is moving it, checked against a claim and kept on the reservation (default: $TASKRAIL_OWNER or user@host)")
src/taskrail/cli.py:1559:    done.add_argument("--owner")
src/taskrail/cli.py:1564:    discard.add_argument("--owner")
src/taskrail/cli.py:1579:    edit.add_argument("--owner", help="who is editing, checked against an existing claim (default: $TASKRAIL_OWNER or user@host)")
src/taskrail/cli.py:1587:    branch_cmd.add_argument("--owner", help="who is renaming (default: $TASKRAIL_OWNER or user@host)")
```

Nine are added in `build_parser()`; `autopilot merged` adds its own in
`src/taskrail/autopilot/merged.py:564`, registered through `add_arguments(parser)`. The list in
the task's row — `claim`, `release`, `reserve-id`, `new`, `workspace`, `done`, `discard`, `edit`,
`branch`, `autopilot merged` — is exactly right. Checked again against the built parser, not the
source:

```
$ for c in claim release reserve-id new workspace done discard edit branch; do \
      printf '%-12s ' "$c"; .taskrail/bin/taskrail "$c" --help | grep -c -- '--owner'; done
claim        2
release      2
reserve-id   2
new          2
workspace    2
done         2
discard      2
edit         2
branch       2
$ .taskrail/bin/taskrail autopilot merged --help | grep -c -- '--owner'
2
```

All ten resolve the same way, through one function:

```
$ grep -rn "resolve_owner\|default_owner" src/taskrail/*.py src/taskrail/autopilot/*.py
src/taskrail/claims.py:56:def default_owner() -> str:
src/taskrail/autopilot/commands.py:144:        run = runs.create(config, len(named), [], claims.default_owner(), named=named)
src/taskrail/autopilot/commands.py:161:    run = runs.create(config, args.count, kinds, claims.default_owner())
src/taskrail/autopilot/commands.py:493:            released = runs.close(run, reason, claims.default_owner())
src/taskrail/cli.py:264:            owner=args.owner or claims.default_owner(),
src/taskrail/cli.py:328:        released = claims.release(config, args.id, args.owner or claims.default_owner(), force=args.force, local_only=args.local_only)
src/taskrail/cli.py:378:        task_id = ids.reserve(config, backlog, args.owner or claims.default_owner())
src/taskrail/cli.py:497:    task_id = ids.reserve(config, backlog.config, args.owner or claims.default_owner())
src/taskrail/cli.py:663:    owner = args.owner or claims.default_owner()
src/taskrail/cli.py:796:    owner = args.owner or claims.default_owner()
src/taskrail/cli.py:931:    owner = args.owner or claims.default_owner()
src/taskrail/cli.py:1048:    owner = args.owner or claims.default_owner()
```

```
$ sed -n '56,57p' src/taskrail/claims.py
def default_owner() -> str:
    return os.environ.get("TASKRAIL_OWNER") or f"{getpass.getuser()}@{socket.gethostname()}"
```

(The four bare sites are `cmd_workspace` at `:663`, `_change_status` at `:796`, `cmd_edit` at
`:931` and `cmd_branch` at `:1048`. `_change_status` is the body of both `cmd_done` and
`cmd_discard` (`cli.py:832-838`), so `done` and `discard` share one site: ten commands, nine call
sites, one `default_owner()`.)

**The rest of T095's measurements — confirmed.**

```
$ grep -rn -- '--owner' tests/ | wc -l
147
$ grep -rc -- '--owner' src/taskrail/skills/ .claude/skills/ | grep -v ':0$'
(no output: not one occurrence in any shipped or installed skill)
$ grep -n -- '--owner\|TASKRAIL_OWNER' DESIGN.md
511:else's needs `--force`. The owner defaults to `$TASKRAIL_OWNER`, then `user@host`.
886:`taskrail workspace <ID> [--branch NAME] [--owner O]` carries a `missing` row into the task's own
1338:| `autopilot merged <ID> [--run R] [--cleanup] [--no-fetch] [--owner O]` | *Implemented (T031).* …
```

Two mentions of the flag (§7.1's `workspace` paragraph and §12.1's `autopilot merged` row), and
the one sentence about the default at line 511.

**The section number in the task's row is wrong: the sentence is in §6.1, not §6.2.**

```
$ grep -n '^### 6' DESIGN.md
481:### 6.1 Local claim — always on
519:### 6.2 Remote claim — optional
532:### 6.3 ID allocation
546:### 6.4 Task branches
```

Line 511 falls inside §6.1 *Local claim — always on*, thirty lines above §6.2. §6.2 is *Remote
claim — optional*: it is about `claim_remote`, the pushed `refs/taskrail/claims/<ID>` ref and what
is deliberately left out of it, and says nothing about who the owner is or how it is chosen. The
numbering has not shifted under the task either — it was already 6.1/6.2 at `f54b52b`, the commit
that added T102's row. The mistake is inherited: T098's write-up parks this item with the same
words ("`--owner`'s sentence, which belongs in §6.2"), so both descend from one miscount in T095.
The **intent** is unambiguous — "beside the line that already says the owner defaults to
`$TASKRAIL_OWNER` then `user@host`" names line 511 exactly — and both sub-sections are inside §6,
which is the boundary the row actually asserts ("Section 6 only, so it does not overlap T098").
Decision 1 below.

**For the next reader:** T102's own row in `TODO.md` and T098's write-up both say this paragraph
belongs in "§6.2". They are wrong, and they are left as they are — merged records of what was
believed at the time, not worth widening a chore's touch map to rewrite. The paragraph is in
**§6.1**, after the sentence it qualifies. Anyone following the "§6.2" pointer should read it
here first.

**Two more places `TASKRAIL_OWNER` reaches that `--owner` does not** (found while walking the
resolution sites, and the strongest evidence for the paragraph the human asked for):
`autopilot start` and `autopilot close` record `claims.default_owner()`
(`autopilot/commands.py:144,161,493`) and have **no** `--owner` flag at all
(`src/taskrail/autopilot/commands.py:514-560` — `start` takes only `--count`, `--kinds`,
`--tasks`; `close` takes `--reason`). So the environment variable is not merely the convenient
path for ten commands; it is the *only* path for two more.

**Two commands that act on the backlog and take no owner:** `reopen` and `unreserve-id`. Neither
reads an owner nor checks a claim (`cmd_unreserve_id` never mentions one; `cmd_reopen` reads the
claim map only to report the task's state). This matters for decision 2: the loose phrase "every
command that acts as a person" is not quite true of the program, while "every command that
records an owner or checks one against a claim" is exactly the ten.

## Change set

Three files: one paragraph in `DESIGN.md`, this artifact, and one index row.

### 1. `DESIGN.md` §6.1 — one paragraph after line 511

Inserted as its own paragraph immediately after the paragraph that ends
"…The owner defaults to `$TASKRAIL_OWNER`, then `user@host`." and before the paragraph beginning
"A claim is **stale** when…". Applied as drafted (the hybrid of decision 2), now at lines
513–519:

> Every command that records an owner or checks one against a claim takes `--owner` to override
> that default: `claim`, `release`, `reserve-id`, `new`, `workspace`, `done`, `discard`, `edit`,
> `branch` and `autopilot merged`. Setting `TASKRAIL_OWNER` in the environment covers all of them
> at once, and is the ordinary way to give a CI job, a shared machine or a service account an
> identity of its own; it also names the owner for `autopilot start` and `autopilot close`, which
> record one but take no flag. `--owner` is for the exception — acting as someone else for a
> single command — and the test suite, where it is how a second person is simulated.

Three sentences, not one: the rule and its ten commands, the variable and why a consumer uses it,
and the division of labour between them. The middle sentence is the one the human said yes to.

### 2. `docs/chores/T102-…md` and `docs/chores/README.md`

This artifact and one appended index row.

## Decisions needed

**All three were answered at the `scope` gate as recommended** (record:
`docs/autopilot/decisions/T102-document-owner-and-taskrail-owner-in-the.md`, commit `67b54a4`):
write in **§6.1** beside line 511 and note the discrepancy for the next reader rather than rewrite
the merged records that carry it; keep **both** the rule and the ten names; **keep** the
`autopilot start` / `autopilot close` clause. The paragraph stands exactly as drafted below.

1. **Write in §6.1, where the sentence actually is, or in §6.2, as the row's words say?**
   Recommendation: **§6.1**, beside line 511. The row's own pointer ("beside the line that already
   says the owner defaults to `$TASKRAIL_OWNER` then `user@host`") is unambiguous, and that line is
   in §6.1; §6.2 is about the optional pushed claim ref and would strand the paragraph away from
   everything it qualifies. §6.1 and §6.2 are both inside §6, so the row's real boundary — "§6
   only, so it does not overlap T098" — is respected either way, and there is no extra conflict
   risk: the other lane touching this file (T099) is in §3, §4 and §9.
   Alternatives: (a) put it in §6.2 as written, which satisfies the literal words and produces a
   paragraph about the local default under a heading about the remote ref; (b) put it in §6.1 and
   also correct "§6.2" wherever the backlog records it, which is editing another task's artifact
   and T095's row — out of this task's touch map.

2. **Name the ten commands, or state the rule generally?** Recommendation: **both**, as drafted —
   the rule first ("every command that records an owner or checks one against a claim"), then the
   ten names. Cost: the list dates the moment an eleventh appears, and no test enforces it. Why it
   is still worth paying: the rule in front of it is a *definition*, so an eleventh command that
   takes `--owner` satisfies the sentence even before anyone updates the list — the paragraph
   degrades into being incomplete, never into being wrong; and this file is audited against the
   live parser about once a month (T088, T092, T095, T098), which is how the four stale statements
   before this one were caught.
   Alternatives: (a) the general phrase alone — never stale, but it sends every reader to
   `--help` to learn which commands it means, and the row itself is what prompted this task
   because nobody could see the surface; (b) the ten names alone, with no rule — precise today,
   simply wrong the day an eleventh lands.

3. **Mention `autopilot start` and `autopilot close`** (the clause "it also names the owner for
   `autopilot start` and `autopilot close`, which record one but take no flag")? Recommendation:
   **yes, keep it** — it is the sharpest proof of the human's own reason for saying yes, that the
   variable is a surface no search for `--owner` can find, and it is one clause. Alternative: drop
   it and keep the paragraph to the ten commands, at the cost of leaving `TASKRAIL_OWNER` looking
   like a convenience rather than the only identity two commands have.

## Out of scope

- **Any behaviour.** No code, no tests, no CLI surface. In particular, five of the ten `--owner`
  arguments carry no argparse `help=` string at all — `release`, `reserve-id`, `new`, `done` and
  `discard` (`cli.py:1498,1507,1545,1559,1564`), against the other five, which do. That is a code
  defect of the same family as T101's `next --limit`; it is reported at the gate, not fixed here.
  Answered at the gate: report only, open nothing — T101 measured 65 such arguments across the
  CLI, this is the second lane to hit the same defect, and the orchestrator is putting the whole
  family to the human rather than letting two lanes patch two instances of it.
- **§7's command table and §12.1's `autopilot merged` row.** They are T098's ground and the row
  says §6 only.
- **The shipped skills**, which name `--owner` nowhere. Whether a skill should is a separate
  question the human has not been asked.
- **`README.md`, `CLAUDE.md`, `CHANGELOG.md`.** `DESIGN.md` is a repository document, not shipped;
  T093, T096 and T098 all changed it with no changelog entry.
- **The reading map** at the top of `DESIGN.md`: no numbered section is added.
- **Correcting "§6.2" in T095's and T098's write-ups.** They are finished accounts of what their
  authors believed; the correction lives here.

## Verification

Every command below was run after the edit, in this worktree. Nothing here is reasoned about.

**The diff is one hunk, a pure insertion, inside §6.1.**

```
$ git diff --stat
 DESIGN.md | 8 ++++++++
 1 file changed, 8 insertions(+)

$ git diff DESIGN.md
@@ -510,6 +510,14 @@
 `record_remote` (§6.4); the exit code stays 0. `taskrail release <ID>` removes a claim; releasing someone
 else's needs `--force`. The owner defaults to `$TASKRAIL_OWNER`, then `user@host`.

+Every command that records an owner or checks one against a claim takes `--owner` to override
+that default: `claim`, `release`, `reserve-id`, `new`, `workspace`, `done`, `discard`, `edit`,
+`branch` and `autopilot merged`. Setting `TASKRAIL_OWNER` in the environment covers all of them at
+once, and is the ordinary way to give a CI job, a shared machine or a service account an identity
+of its own; it also names the owner for `autopilot start` and `autopilot close`, which record one
+but take no flag. `--owner` is for the exception — acting as someone else for a single command —
+and the test suite, where it is how a second person is simulated.
+
 A claim is **stale** when its worktree no longer exists, or when its branch does not exist and
```

No existing line is modified or deleted. The paragraph lands at lines 513–519, and §6.1 now runs
481–526:

```
$ grep -n '^### 6' DESIGN.md
481:### 6.1 Local claim — always on
527:### 6.2 Remote claim — optional
540:### 6.3 ID allocation
554:### 6.4 Task branches
```

**The list of ten is a statement about the built parser, re-checked after the edit:**

```
$ for c in claim release reserve-id new workspace done discard edit branch; do \
      printf '%-16s ' "$c"; .taskrail/bin/taskrail "$c" --help | grep -o -- '--owner OWNER' | head -1; done
claim            --owner OWNER
release          --owner OWNER
reserve-id       --owner OWNER
new              --owner OWNER
workspace        --owner OWNER
done             --owner OWNER
discard          --owner OWNER
edit             --owner OWNER
branch           --owner OWNER
$ .taskrail/bin/taskrail autopilot merged --help | grep -o -- '--owner OWNER' | head -1
--owner OWNER
```

And the exclusions the sentence's rule implies really are excluded — every one of these prints no
`--owner` at all: `reopen`, `unreserve-id`, `review`, `validate`, `show`, `list`, `next`, `claims`,
and the two the paragraph names:

```
$ .taskrail/bin/taskrail autopilot start --help
usage: taskrail autopilot start [-h] [--json] [--count COUNT] [--kinds KINDS] [--tasks TASKS]
$ .taskrail/bin/taskrail autopilot close --help
usage: taskrail autopilot close [-h] [--json] --reason REASON run
```

**Every clause exercised for real**, in a throwaway repository (`git init`, `taskrail init`, one
epic, one task):

```
$ taskrail --root <probe> claim T001 --json | grep owner        # no variable, no flag
    "owner": "abigail@archlinux",                               # → user@host
$ taskrail --root <probe> release T001 --json | grep owner
    "owner": "abigail@archlinux",

$ TASKRAIL_OWNER=ci@build-agent taskrail --root <probe> claim T001 --json | grep owner
    "owner": "ci@build-agent",                                  # the variable, no flag anywhere
$ TASKRAIL_OWNER=ci@build-agent taskrail --root <probe> claims
T001   ci@build-agent           master                         live

$ taskrail --root <probe> release T001                          # back to user@host
taskrail: T001 is claimed by ci@build-agent; pass --force to release someone else's claim
exit=4

$ TASKRAIL_OWNER=ci@build-agent taskrail --root <probe> done T001 --owner someone@else
taskrail: T001 is claimed by ci@build-agent; pass --force
exit=4                                                          # the flag overrode the variable
                                                                # for that one command
$ TASKRAIL_OWNER=ci@build-agent taskrail --root <probe> done T001 --json
{ "id": "T001", "status": "done", "commit": "stages", … }       # the variable's owner closes it
```

That is the paragraph's three sentences, each demonstrated: the default, the variable covering
commands with no flag on them, and `--owner` overriding the variable for a single command.

**The repository is undisturbed.**

```
$ taskrail --root <worktree> checks T102
== test: uv run pytest -q
1196 passed in 135.61s (0:02:15)
== lint: not configured
passed test
not configured lint
T102 in /thezone/shared/repositories/utils/taskrail/.worktrees/T102-document-owner-and-taskrail-owner-in-the: passed
exit=0

$ taskrail --root <worktree> validate
93 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit=0
```

1196 passed, the same count T098 recorded at `464b958`, which is the point: this task changed no
code.
