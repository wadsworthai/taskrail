# T095 — Ask whether the options no visible repository sets or documents are still wanted

**Status: framed.** The verdict belongs at the `decide` gate, and this document is a draft until
then.

## Question

[T088](T088-measure-the-cli-and-configuration-surfac.md) measured taskrail's option surface from
inside the one repository whose configuration is visible, and found seven options that no file in
this repository sets, passes or — for most of them — documents. **T088 licenses no removal**: under
[T087](T087-decide-whether-the-design-principles-gov.md)'s verdict, now in `CLAUDE.md`, the design
principles judge the change a task makes and not the code already there. So the question this spike
answers is not *should these be removed*. It is:

> For each of the seven options, **is it wanted** — and does the answer route it to *document it*
> or to *a task proposing its removal*?

Only the human can answer. This repository is public, taskrail is installed by repositories that
are not, and the publishing constraint in `CLAUDE.md` keeps those out of the write-up. **Nothing in
this document says an option has no consumer.** The strongest claim available, and the one used
throughout, is that no consumer is *visible in this repository*.

The seven, as T088 named them:

| # | Option | T088's class and evidence |
|---|---|---|
| 1 | `[[backlog]].epic_prefix` | E6 — C5: a configuration key with no setter, no test and no line of `DESIGN.md` |
| 2 | `[[backlog]].id_digits` | E6 — C4: no setter, one test |
| 3 | `epic add --id` | E8 — C5: nowhere outside the parser |
| 4 | `epic add --file` | E8 — C5 |
| 5 | `epic split --file` | E8 — C5 |
| 6 | `next --limit` | E8 — C5 |
| 7 | `--owner` | E8 — C4: 147 test occurrences, no skill, no documented workflow |

**The two halves are not equal evidence**, and the questions must not be put as if they were.
T088's E2/E3 asymmetry governs: a configuration key has to be *written in a file* to act, so its
absence from every `.taskrail/config.toml` visible here is real evidence (options 1 and 2). A flag
is typed by a human who leaves no file behind, so its absence proves only that no *file* here
passes it (options 3-7).

## What evidence would answer it

Not the human's memory alone, and not T088's word. Each question needs three things in front of the
person answering:

1. **A re-verified claim.** T088's findings are re-run here against today's mainline, so the human
   is answering about the tool as it stands, not as it stood when it was measured. Where
   re-verification changed a claim, the corrected claim is what is asked about.
2. **What the option does**, in one clause, from its own help text or implementation — so the
   question can be answered without reading this document.
3. **Two named routes**, with a recommendation and a default, so an answer is one word and a
   skipped question still has an outcome.

## Approach

- **Re-verify each of the seven** on today's mainline (`0fd8dcb`), with the exact command and its
  real output, before asking anything. Recorded in *Evidence*, below, at the `frame` stage.
- **Put the seven to the human as a numbered questionnaire** at the `decide` gate, which
  `[autopilot].escalate_gates = ["spike:decide"]` sends to them. That gate report *is* the
  questionnaire; it is written for someone who has not read this document.
- **Record the answers here**, then open one follow-up task per answer that needs one: a `chore`
  documenting the option, or a task proposing its removal, each judged on its own merits when it is
  worked.

## Limits

- **No code, no `DESIGN.md`, no skill and no configuration changes in this task.** The kind's
  `never_edit` is `code` and `specs`; adopting any answer is follow-up work.
- **No removal is decided here**, whatever the answers are. A "not wanted" answer produces a task
  that *proposes* a removal, with its own gates.
- **Three options belong to other tasks and are out of scope**: `[autopilot].handoff` (T096), the
  remote half of claims and branch records (T097), and the `DESIGN.md` documentation defects as a
  batch (T098). Where an answer here overlaps T098's subject, this task says so rather than editing
  the file.
- **This document cannot name a private consumer**, so an answer that rests on one is recorded as
  *the human confirmed a consumer exists*, without the repository, the client or the use.

## Evidence

Re-verified in this task's worktree, branch `T095-ask-whether-the-options-no-visible-repos`, base
`origin/main` = `0fd8dcb`. Each command below was run there; the outputs are real. The full list is
in *How to reproduce*.

### V1. `[[backlog]].epic_prefix` — T088's claim holds

```
$ grep -c "epic_prefix" DESIGN.md
0
$ git grep -n "epic_prefix" -- src/taskrail tests .taskrail
src/taskrail/config.py:29,174,175,176,177,178,194     # default "E", parse, two validations, construct
src/taskrail/backlog.py:200,240                       # the epic-ID regex and its error message
src/taskrail/cli.py:1327
src/taskrail/importer.py:291
                                                      # no hit under tests/ or .taskrail/
```

Absent from `DESIGN.md` entirely, from every test and from the only visible configuration file, as
T088 recorded. **One addition T088 did not have:** a past write-up names it —
`docs/features/T005-import-tasks-from-table-based-backlogs-w.md:67` describes `taskrail import`
generating epic IDs as `<epic_prefix>01, 02, …`. That is the key's most plausible consumer and it
matters to the question (see V8).

### V2. `[[backlog]].id_digits` — T088's *table* holds; its *prose* over-claimed

```
$ git grep -n "id_digits" -- DESIGN.md tests
DESIGN.md:971:  `id_digits` is refused, with the `id_digits` value that would keep it when only padding differs.
tests/test_import.py:462:    ("T1", "T002", "id-format", "id_digits"),
```

T088's table records `§4: –` and `TEST: 1`, and both are right. But its *Recommendation 2* calls
`id_digits` "undocumented", and the task row for this spike inherits that framing. **It is
documented** — once, at `DESIGN.md:971`, inside §7.3's description of what `taskrail import` refuses
and what it suggests instead. What is true is narrower and is what this spike asks about:
§4's example configuration (lines 130-225) lists `prefix` and not `id_digits`, so a reader who
learns the configuration from §4 cannot discover the key, and nothing anywhere says it also sets
the width of the IDs `taskrail new` generates (`src/taskrail/ids.py:148`).

### V3-V6. The four flags with nothing outside the parser — the claim holds

```
$ git grep -n -F -e '--file' -e '--id' -e '--limit' -- ':!src/taskrail/cli.py' ':!docs' ':!TODO.md'
(no output)
```

`docs/` and `TODO.md` are excluded because T088's own write-up, its decision record and this task's
row now discuss the three strings; they were not excluded in T088, which ran before those files
existed. Outside them, the result is unchanged: the strings appear nowhere but the parser that
defines them.

What each one does, from its own help:

```
$ .taskrail/bin/taskrail epic add --help
  --id ID               epic ID (default: next in the backlog)
  --file FILE           put the epic in this file
  --own-file            put the epic in todo/<id>-<slug>.md
                        (--file and --own-file are mutually exclusive)
$ .taskrail/bin/taskrail epic split --help
  --file FILE        target file (default: todo/<id>-<slug>.md)
$ .taskrail/bin/taskrail next --help
  --limit LIMIT
```

**`next --limit` is worse than T088 recorded.** It is absent from §7, and it also has *no help text
at all* — the line above is the whole of it. It is the one option of the seven that a user cannot
discover from `--help` either.

### V7. `--owner` — 147 test occurrences confirmed, and it is ten flags, not one

```
$ git grep -cF -- '--owner' -- tests               | awk -F: '{n+=$2} END {print n}'
147
$ git grep -cF -- '--owner' -- src/taskrail/skills src/taskrail/integrations
0
$ git grep -cF -- '--owner' -- DESIGN.md
2          # workspace (line 867) and autopilot merged (line 1319) only
$ git grep -cF -- '--owner' -- docs | awk -F: '{n+=$2} END {print n}'
56         # across 16 past task write-ups
```

T088 counts distinct long option *strings*, so `--owner` is one entry in its 71. In the parser it
is **ten separate arguments**:

```
$ uv run python -c "…walk the parser…"   # see How to reproduce
claim: --owner            release: --owner       reserve-id: --owner    new: --owner
workspace: --owner        done: --owner          discard: --owner       edit: --owner
branch: --owner           autopilot merged: --owner
```

Of the ten, `DESIGN.md` names it on two. **And it has an environment-variable equivalent**
(`DESIGN.md:492`): "The owner defaults to `$TASKRAIL_OWNER`, then `user@host`." A consumer who needs
a non-default owner — CI, a shared machine, a service account — would set `TASKRAIL_OWNER` once
rather than pass a flag to ten commands, which is a consumer path no grep for `--owner` can see.

### V8. Both configuration keys point at the same invisible consumer

`epic_prefix` and `id_digits` are each read by `taskrail import`
(`importer.py:291` and `importer.py:347`) as well as by the validator and the ID generator. T088's
E7 records that `import` "converts a foreign backlog once", is documented, is 684 lines with a
608-line test file, and **was never run in this repository** — taskrail was extracted with its
history, not imported. So the class of repository most likely to need either key is exactly the
class this repository cannot see: one that arrived with an existing backlog whose epics are `EP01`
and whose tasks are `T0001`. That is context the human needs to answer 1 and 2, and it is why those
two questions are worth asking even though the keys look dead from here.

### V9. A repository that needs `epic_prefix` is not told the key exists

`backlog.py:240` refuses a mismatched epic ID with

```python
f"epic ID `{epic_id}` does not match `{backlog_config.epic_prefix}` plus two or more digits"
```

The message quotes the prefix's *value* and never names the key, and §4 does not list it, so a
repository whose epics are `EP01` sees an error whose fix — `epic_prefix = "EP"` — is discoverable
only by reading `config.py`. Whatever the human answers for question 1, this is a defect in its own
right, and T098 is the task that owns it.

## Options considered

*To be completed at the `decide` stage.*

## Recommendation

*To be completed at the `decide` stage.*

## What would change the decision

*To be completed at the `decide` stage.*

## How to reproduce

From a checkout at `0fd8dcb` or later, in the repository root.

```bash
grep -c "epic_prefix" DESIGN.md                                 # V1: 0
git grep -n "epic_prefix" -- src/taskrail tests .taskrail       # V1: implementation only
git grep -n "id_digits" -- DESIGN.md tests                      # V2: DESIGN.md:971, one test
sed -n '130,160p' DESIGN.md                                     # V2: §4's example has prefix, not id_digits
git grep -n -F -e '--file' -e '--id' -e '--limit' \
    -- ':!src/taskrail/cli.py' ':!docs' ':!TODO.md'             # V3-V6: no output
.taskrail/bin/taskrail epic add --help                          # V3-V5
.taskrail/bin/taskrail epic split --help                        # V5
.taskrail/bin/taskrail next --help                              # V6: --limit LIMIT, no help text
git grep -cF -- '--owner' -- tests                              # V7: 147 in total
git grep -cF -- '--owner' -- src/taskrail/skills src/taskrail/integrations   # V7: 0
git grep -nF -- '--owner' -- DESIGN.md                          # V7: lines 867 and 1319
git grep -nF 'TASKRAIL_OWNER' -- DESIGN.md                      # V7: line 492
git grep -n "epic_prefix\|id_digits" -- src/taskrail/importer.py src/taskrail/ids.py   # V8
sed -n '236,242p' src/taskrail/backlog.py                       # V9: the error message
```

Which commands define each flag, from the live parser (V7):

```python
from taskrail.cli import build_parser

def walk(parser, path):
    for action in parser._actions:
        for opt in action.option_strings:
            if opt in ("--owner", "--id", "--file", "--limit"):
                print(f"{' '.join(path) or '<root>'}: {opt}  help={action.help!r}")
        if action.__class__.__name__ == "_SubParsersAction":
            for name, sub in action.choices.items():
                walk(sub, path + [name])

walk(build_parser(), [])
```

## Outcome

*To be completed after the `decide` gate.*
