# T095 — Ask whether the options no visible repository sets or documents are still wanted

**Verdict** — The seven options T088 found with no visible consumer are **all seven working as
designed**; every one was run in a throwaway repository for this spike, and none is broken. So the
question is purely *is it wanted*, never *is it faulty*, and it is a question **only the human can
answer**, because this repository is public and the private consumers are not visible from it. This
document's output is therefore not a decision but a **questionnaire**: seven numbered questions,
each with one line of re-verified evidence, two named routes — *document it* or *a task proposing
its removal* — a recommendation and a default. **Nothing here removes anything**, and under
[T087](T087-decide-whether-the-design-principles-gov.md)'s verdict, now in `CLAUDE.md`, nothing here
licenses a removal: the design principles judge the change a task makes, not the code already there.

Two results change how the questions must be asked. **First, four of the seven answers cost no new
task at all**: T098 already edits exactly the two regions of `DESIGN.md` — §4's example and §7's
command table — where a *document it* answer for questions 1-6 lands, so those answers extend a task
that exists rather than opening new ones. **Second, a removal answer for questions 1 or 2 must wait
for T094.** Until `validate` warns about a key it does not know, withdrawing a configuration key is
silent for any repository that set it (T088 E2), so a route-B task for either key depends on T094 by
construction.

This spike changed no code, no configuration, no skill, no `DESIGN.md` and no other task's row.

## Question

[T088](T088-measure-the-cli-and-configuration-surfac.md) measured taskrail's option surface from
inside the one repository whose configuration is visible, and found seven options that no file here
sets, passes or — for most of them — documents. The question is not *should these be removed*:

> For each of the seven options, **is it wanted** — and does the answer route it to *document it*
> or to *a task proposing its removal*?

Only the human can answer. This repository is public, taskrail is installed by repositories that are
not, and the publishing constraint in `CLAUDE.md` keeps those out of the write-up. **Nothing in this
document says an option has no consumer.** The strongest claim available, and the one used
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
absence from every `.taskrail/config.toml` visible here is real evidence (questions 1 and 2). A flag
is typed by a human who leaves no file behind, so its absence proves only that no *file* here passes
it (questions 3-7).

## What evidence would answer it

Not the human's memory alone, and not T088's word. Each question needs three things in front of the
person answering:

1. **A re-verified claim**, so they answer about the tool as it stands.
2. **What the option does**, in one clause, from its help text or from running it.
3. **Two named routes**, with a recommendation and a default, so an answer is one word and a skipped
   question still has an outcome.

## Approach

Re-verify each of the seven on today's mainline before asking anything (*V1-V9*); run each of them
in a throwaway repository, which T088 did not do, so a broken option is never mistaken for an unused
one (*V10-V15*); pin down both routes per option so each is concrete (*Options considered*); then
put the seven to the human as a numbered questionnaire at the `decide` gate, which
`[autopilot].escalate_gates = ["spike:decide"]` sends to them. Record the answers, and open the
follow-up tasks afterwards.

## Limits

- **No code, no `DESIGN.md`, no skill and no configuration changed in this task.** The kind's
  `never_edit` is `code` and `specs`; adopting any answer is follow-up work.
- **No removal is decided here**, whatever the answers are. A "not wanted" answer produces a task
  that *proposes* a removal, with its own gates.
- **Three options belong to other tasks and are out of scope**: `[autopilot].handoff` (T096), the
  remote half of claims and branch records (T097), and the `DESIGN.md` documentation defects as a
  batch (T098).
- **This document cannot name a private consumer**, so an answer that rests on one is recorded as
  *the human confirmed a consumer exists*, without the repository, the client or the use.
- The probes in *V10-V15* ran in throwaway repositories outside this one, seeded by `taskrail init`.
  They prove the options work in a fresh repository; they say nothing about any real backlog.

## Evidence

Re-verified in this task's worktree, branch `T095-ask-whether-the-options-no-visible-repos`, base
`origin/main` = `0fd8dcb`. Every command and output below is real; the full list is in
*How to reproduce*.

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
generating epic IDs as `<epic_prefix>01, 02, …`. That is the key's most plausible consumer, and it
matters to the question (see *V9*).

### V2. `[[backlog]].id_digits` — T088's *table* holds; its *prose* over-claimed

```
$ git grep -n "id_digits" -- DESIGN.md tests
DESIGN.md:971:  `id_digits` is refused, with the `id_digits` value that would keep it when only padding differs.
tests/test_import.py:462:    ("T1", "T002", "id-format", "id_digits"),
```

T088's E5 table records `§4: –` and `TEST: 1`, and both are right. But its *Recommendation 2* calls
`id_digits` "undocumented", and this spike's task row inherited that framing. **It is documented** —
once, at `DESIGN.md:971`, inside §7.3's account of what `taskrail import` refuses and what it
suggests instead. What is true is narrower, and is what question 2 asks about: §4's example
configuration (lines 130-225) lists `prefix` and not `id_digits`, so a reader who learns the
configuration from §4 cannot discover the key, and **nothing anywhere says it also sets the width of
the IDs `taskrail new` generates** (`src/taskrail/ids.py:148`), which is its more common effect.

### V3-V6. The four flags with nothing outside the parser — the claim holds

```
$ git grep -n -F -e '--file' -e '--id' -e '--limit' -- ':!src/taskrail/cli.py' ':!docs' ':!TODO.md'
(no output)
```

`docs/` and `TODO.md` are excluded because T088's own write-up, its decision record and this task's
row now discuss the three strings; they did not exist when T088 ran. Outside them the result is
unchanged: the strings appear nowhere but the parser that defines them.

What each does, from its own help:

```
$ .taskrail/bin/taskrail epic add --help
  --id ID               epic ID (default: next in the backlog)
  --file FILE           put the epic in this file
  --own-file            put the epic in todo/<id>-<slug>.md
                        (usage line: [--file FILE | --own-file] — mutually exclusive)
$ .taskrail/bin/taskrail epic split --help
  --file FILE        target file (default: todo/<id>-<slug>.md)
$ .taskrail/bin/taskrail next --help
  --limit LIMIT
```

**`next --limit` is worse than T088 recorded.** It is absent from §7, and it has *no help text at
all* — the line above is the whole of it. It is the only one of the seven that a user cannot
discover from `--help` either.

### V7. `--owner` — 147 test occurrences confirmed, and it is ten flags, not one

```
$ git grep -cF -- '--owner' -- tests | awk -F: '{n+=$2} END {print n}'
147
$ git grep -cF -- '--owner' -- src/taskrail/skills src/taskrail/integrations
0
$ git grep -nF -- '--owner' -- DESIGN.md
DESIGN.md:867    # taskrail workspace <ID> [--branch NAME] [--owner O]
DESIGN.md:1319   # autopilot merged <ID> [--run R] [--cleanup] [--no-fetch] [--owner O]
$ git grep -cF -- '--owner' -- docs | awk -F: '{n+=$2} END {print n}'
56               # across 16 past task write-ups
```

T088 counts distinct long option *strings*, so `--owner` is one entry in its 71. In the parser it is
**ten separate arguments**: `claim`, `release`, `reserve-id`, `new`, `workspace`, `done`, `discard`,
`edit`, `branch` and `autopilot merged`. `DESIGN.md` names it on two of the ten.

**And it has an environment-variable equivalent** (`DESIGN.md:492`): "The owner defaults to
`$TASKRAIL_OWNER`, then `user@host`." A consumer needing a non-default owner — CI, a shared machine,
a service account — would set `TASKRAIL_OWNER` once rather than pass a flag to ten commands. That is
a consumer path no grep for `--owner` can see, and it is why question 7's *document it* route names
the variable rather than the flag.

### V8. Both configuration keys point at the same invisible consumer

`epic_prefix` and `id_digits` are each read by `taskrail import` (`importer.py:291` and
`importer.py:347`) as well as by the validator and the ID generator. T088's E7 records that `import`
"converts a foreign backlog once", is documented, is 684 lines with a 608-line test file, and **was
never run in this repository** — taskrail was extracted with its history, not imported. So the class
of repository most likely to need either key is exactly the class this repository cannot see: one
that arrived with an existing backlog whose epics are `EP01` and whose tasks are `T0001`.

### V9. A repository that needs `epic_prefix` is never told the key exists

This is the sharpest result in the spike, and it was produced by running the tool rather than by
grepping it. In a throwaway repository with the seeded default configuration, giving an epic the ID
an imported backlog would have:

```
$ uv run taskrail --root $P epic add --id EP01 --name "Foreign prefix" --objective "…"
TODO.md:9: error: epic ID `EP01` does not match `E` plus two or more digits [epic-id]
TODO.md:11: error: section `EP01` is not in the Epics table [epic-unlisted]
taskrail: the change would leave the backlog invalid; nothing was written        (exit 1)
```

The message quotes the prefix's **value**, `E`, and never names `epic_prefix`; §4 does not list the
key; so the fix — `epic_prefix = "EP"` — is discoverable only by reading `config.py`. **Questions 1
and 3 are therefore coupled**: `--id` is how a caller gives an epic a foreign ID, `epic_prefix` is
the key that makes that ID legal, and neither is documented. Whatever the human answers, the error
message is a defect in its own right; it is a code change, so it is not T098's and it is named as an
optional extra under question 1 rather than folded in.

### V10-V15. All seven options work — none is broken

T088 classified the seven but never ran them, and its E6 says of `epic_prefix` that "nothing here
proves it works". This spike ran each one in a throwaway repository seeded by `taskrail init`
(`$P` below; `$Q` is a second one whose config sets both keys). A broken option would be a different
question, so this had to be settled before asking anything.

| V | Option | Command | Result |
|---|---|---|---|
| V10 | `epic add --id` | `epic add --id E42 --name … --objective …` | `{"id": "E42", …}`, exit 0 — the chosen ID is used |
| V11 | `epic add --file` | `epic add --file epics/custom.md --name … --objective …` | `{"id": "E43", "file": "epics/custom.md", …}` — the epic lands at the named path |
| V12 | `epic split --file` | `epic split E42 --file epics/split-here.md` | `{"id": "E42", "file": "epics/split-here.md", …}` — moved to the named path |
| V13 | `next --limit` | `next` then `next --limit 2` | three rows, then the first two — it truncates the list |
| V14 | `epic_prefix` | `epic_prefix = "EP"`, then `epic add --name … --objective …` | `{"id": "EP01", …}` — epics are generated with the configured prefix |
| V15 | `id_digits` | `id_digits = 4`, then `new --epic EP01 --kind chore --title …` | `{"id": "T0001", …}`, and `validate` → `0 error(s), 0 warning(s)` |

**What V11 and V12 add to question 4 and 5.** `--own-file` writes `todo/<id>-<slug>.md` and nothing
else; `--file` accepts any path. So the two are not duplicates: `--file` is the escape hatch for a
repository whose epic files live somewhere other than `todo/`, which is precisely a layout choice
this repository cannot see into another. That is worth the human knowing before answering.

**What V14 and V15 add to questions 1 and 2.** Both keys do exactly what their names suggest, in a
repository seeded today. They are not vestigial code that stopped working; they are working options
that this repository never had a reason to set.

### V16. None of the seven is a recent speculative addition

```
$ git log --oneline -S'"--limit"' -- src/taskrail/cli.py
eceb908 feat(taskrail): add backlog parsing, validation and read-only queries
$ git log --oneline -S'"--id"' -- src/taskrail/cli.py
34a93e5 feat(taskrail): add write commands with minimal, pre-validated diffs
$ git log --oneline -S'epic_prefix' -- src/taskrail/config.py     # id_digits likewise
34a93e5 feat(taskrail): add write commands with minimal, pre-validated diffs
eceb908 feat(taskrail): add backlog parsing, validation and read-only queries
$ git log --format='%h %ad %s' --date=short --reverse | head -5
fcb8d48 2026-09-09 chore: initialize repository
eceb908 2026-09-13 feat(taskrail): add backlog parsing, validation and read-only queries
3fef36f 2026-09-13 feat(taskrail): add task claims and race-free ID reservation
a563400 2026-09-13 fix(taskrail): keep machine details out of remote claims
34a93e5 2026-09-13 feat(taskrail): add write commands with minimal, pre-validated diffs
```

All six of the flags and keys were built on 2026-09-13, in commits 2 and 5 of the repository — the
original construction of the parser and the configuration loader. `--owner` was extended to `branch`
later, by T019 (`cc238cb`). **None of them was added later on request**, and none has grown a
visible consumer since. That is neutral between the two routes, and the human should have it: these
are original scaffolding rather than options added on a guess later. But the weight of that cuts
both ways and should not be overstated: the repository's first commit is 2026-09-09 and these were
written on 2026-09-13, so "nothing here has needed them yet" is a statement about five days of a
young tool, not about a long unused tenure.

## Options considered

### The shape of the question put to the human

| Option | What it means | Cost |
|---|---|---|
| **A. A numbered questionnaire: one block per option, both routes named, a recommendation and a default (recommended)** | The `decide` gate report is the questionnaire, written for someone who has not read this document: per option, what it does, one line of evidence, a yes/no question, routes A and B, and a default if skipped. | Longer to write than a bare list. Seven answers in one sitting, each one word. |
| B. One line per option, no routes | "Is `epic_prefix` wanted? y/n" ×7. | Shortest to read, but the human then has to invent the route, which is the part this spike can do for them — and the routes differ per option (four fold into T098; one needs T094 first). |
| C. Group the seven into three questions | Two configuration keys, four epic/`next` flags, `--owner`. | Forces one answer onto options whose evidence differs in strength, which is exactly what T088's E2/E3 asymmetry warns against, and hides that question 7's answer is all but settled. |
| D. Recommend an answer per option and ask only for exceptions | "Unless you say otherwise, all seven are documented." | Tempting, and it is what the defaults do — but it buries questions 1 and 2, where a *removal* answer is genuinely open and the evidence is strongest. The defaults carry it without hiding it. |

### Where each *document it* answer lands

Settled by reading the two tasks that already exist, so no route is invented twice:

| # | Option | Route A lands in | New task needed? |
|---|---|---|---|
| 1 | `epic_prefix` | §4's example config | **No** — T098's description already names it |
| 2 | `id_digits` | §4's example config, plus one clause on its effect on `new` | **No** for §4; the clause is one `taskrail edit` on T098's row |
| 3 | `epic add --id` | §7's command table, line 648 | **No** — T098 already edits that table |
| 4 | `epic add --file` | §7's command table, line 648 | **No** — same row |
| 5 | `epic split --file` | §7's command table, line 648 | **No** — same row |
| 6 | `next --limit` | §7's command table, line 635 — **and** a `help=` string in `cli.py` | §7: no. The help string is code, so a separate one-line `chore` |
| 7 | `--owner` | §6.2, beside `DESIGN.md:492` where the owner default is already described | **Yes** — T098 touches §4 and §7 only |

T098's description says it touches "only those two regions so the reading map T093 adds at the top
does not conflict", and §4's example and §7's command table are exactly where answers 1-6 land.
T088's own option E anticipated this: "§7 gains `--limit`, `--file`, `--id` **or** the task that
removes them settles them first." **This task does not edit T098's row**; whether the extension is a
`taskrail edit` on it or a separate chore is for whoever acts on the answers.

### Where each *propose removing it* answer lands

| # | Option | The task it opens | Depends on |
|---|---|---|---|
| 1 | `epic_prefix` | Propose fixing the epic prefix at `E`: `config.py` (default, parse, two validations, construct), `backlog.py:200,240`, `cli.py:1327`, `importer.py:291` | **T094** |
| 2 | `id_digits` | Propose fixing the ID width at 3: `config.py`, `ids.py:148`, `importer.py:347,362,366`, `project.py:35,42` — and it would delete the behaviour `DESIGN.md:971` documents | **T094** |
| 3 | `epic add --id` | Propose removing it, leaving epic IDs always sequential | — |
| 4+5 | `epic add --file`, `epic split --file` | One task for both: the same idea in two commands, leaving `--own-file` and the `todo/<id>-<slug>.md` default | — |
| 6 | `next --limit` | Propose removing it | — |
| 7 | `--owner` | Not recommended — see question 7 | — |

**Why 1 and 2 depend on T094.** T088's E2 measured that `load_config` ignores a key it does not
know and `validate` reports zero errors and zero warnings, so withdrawing a configuration key is
*silent*: a repository that set it keeps the line, keeps a green `validate`, and quietly gets the
default at its next `taskrail upgrade`. T094 makes that loud. Removing either key before T094 lands
would be the exact failure the publishing constraint exists to prevent, for a consumer this
repository cannot see. Removing a *flag* is loud already (exit 2, `unrecognized arguments`), so
questions 3-6 carry no such dependency.

### A tension worth naming under question 3

The core `taskrail` skill opens with "**The CLI owns IDs.** Never invent an ID." `epic add --id` is
the one command that lets a caller invent one. That is the strongest argument for route B — and
*V9* is the strongest argument against it: an imported backlog whose epics are `EP01` needs both
`--id` and `epic_prefix`, and `taskrail import` is the one command this repository never ran. The
human is the only person who can say which of those two situations is real.

## Recommendation

**Put the seven questions to the human as the `decide` gate report, in the form of the questionnaire
below, and open no task until they answer.** The recommendations and defaults are:

| # | Option | Recommended route | If skipped |
|---|---|---|---|
| 1 | `[[backlog]].epic_prefix` | **A — document it** (T098, no new task) | A |
| 2 | `[[backlog]].id_digits` | **A — document it** (T098, plus one clause) | A |
| 3 | `epic add --id` | **A — document it** (T098's §7 row) | A |
| 4 | `epic add --file` | **A — document it** (T098's §7 row) | A |
| 5 | `epic split --file` | **A — document it** (T098's §7 row) | A |
| 6 | `next --limit` | **A — document it**, plus a one-line `help=` chore | A |
| 7 | `--owner` | **A — document it**, naming `$TASKRAIL_OWNER` | A |

**Route A is the recommendation and the default for all seven, and the reason is not timidity.** It
is that route A is nearly free — four of the seven cost no new task, because T098 already edits the
two regions where they land — while route B costs a task, a review and a version's worth of risk to
a consumer nobody here can see. T087 makes the principles prospective; T088 E2 makes a configuration
removal silent; the publishing constraint makes the consumer invisible. Under those three, "write
one line of documentation" is the proportionate answer to "nobody here sets it", and "propose a
removal" needs a positive reason that only the human has.

**Question 7 is all but settled and is presented that way.** `--owner` has 147 test occurrences, is
the suite's only way to simulate a second person, and spans ten commands with a `TASKRAIL_OWNER`
equivalent that no grep for the flag can see. Removal is implausible; one line of documentation is
the answer. It stays on the list because it costs the human one word and closes the question in the
record.

### The questionnaire

*Answer with the number and A or B — for example `1 B, 2 A, 3 A, 4 A, 5 A, 6 A, 7 A`. Anything you
skip takes the default on its line. **A** = document it; **B** = open a task proposing its removal.
Nothing is removed by any answer: B opens a task that proposes a removal and is judged on its own
merits when it is worked.*

**1. `[[backlog]].epic_prefix`** — sets the letters epic IDs start with; default `E`.
Visible here: absent from `DESIGN.md` entirely, from every test, and from the only config file
(`grep -c "epic_prefix" DESIGN.md` → `0`). It works: with `epic_prefix = "EP"`, `epic add` produced
`EP01`. Its likely consumer is a repository that ran `taskrail import` on a backlog whose epics were
already `EP01` — the one command this repository never ran, because it was extracted, not imported.
And today such a repository is refused with ``epic ID `EP01` does not match `E` plus two or more
digits``, which names the prefix's value but never the key.
**Q: does any repository you can see set `epic_prefix`, or have a backlog whose epics are not `E##`?**
→ **A (recommended, default)**: T098 already adds it to §4's example — no new task. *Optional extra:
a small task making the error message name the key, since that is code and not T098's.*
→ **B**: a task proposing the prefix be fixed at `E`, which must depend on T094.

**2. `[[backlog]].id_digits`** — sets the zero-padded width of generated task IDs; default `3`
(`T001`), so `4` gives `T0001`.
Visible here: not in §4's example, one test, no config file sets it. It is documented once, at
`DESIGN.md:971`, but only as a hint in `taskrail import`'s refusal message — nothing anywhere says
it also sets the width of the IDs `taskrail new` generates. It works: with `id_digits = 4`, `new`
produced `T0001` and `validate` stayed green.
**Q: does any repository you can see set `id_digits`, or have task IDs that are not three digits?**
→ **A (recommended, default)**: T098 already adds it to §4's example; one clause is added saying it
also governs `taskrail new`. No new task.
→ **B**: a task proposing the width be fixed at 3, which must depend on T094 and which would delete
the behaviour `DESIGN.md:971` documents.

**3. `epic add --id E##`** — choose an epic's ID instead of taking the next one in the backlog.
Visible here: the string `--id` appears nowhere in this repository outside the parser that defines
it. It works (`epic add --id E42` produced `E42`). Against it: the core skill's first paragraph says
"**The CLI owns IDs.** Never invent an ID." For it: an imported backlog with foreign epic IDs needs
exactly this, together with question 1.
**Q: does anyone you can see pass `--id` to `epic add`?**
→ **A (recommended, default)**: one line in §7's command table, which T098 already edits — no new
task.
→ **B**: a task proposing its removal, leaving epic IDs always sequential.

**4. `epic add --file PATH`** and **5. `epic split --file PATH`** — put an epic in a named file
instead of `todo/<id>-<slug>.md`.
Visible here: `--file` appears nowhere outside the parser; `--own-file`, which writes the
`todo/…` default, is named in the core skill and is the documented way. Both work (`--file
epics/custom.md` put the epic exactly there). They are not duplicates of `--own-file`: `--file`
takes any path, so it is the escape hatch for a repository whose epic files live somewhere other
than `todo/` — a layout choice this repository cannot see in another.
**Q: does any repository you can see keep its epic files outside `todo/`?**
→ **A (recommended, default for both)**: one line in §7's command table, which T098 already edits —
no new task.
→ **B**: one task proposing both be removed, leaving `--own-file` and the default path.

**6. `next --limit N`** — show only the first N eligible tasks.
Visible here: absent from §7, absent from every skill and test, **and it has no help text at all** —
`taskrail next --help` prints the bare line `--limit LIMIT`. It is the only one of the seven that
cannot be discovered from `--help` either. It works (`next --limit 2` returned the first two of
three).
**Q: does anyone you can see pass `--limit` to `next`?**
→ **A (recommended, default)**: one line in §7's command table (T098, no new task), **plus** a
one-line `chore` giving the flag a `help=` string, since that is code and T098 is documentation.
→ **B**: a task proposing its removal.

**7. `--owner OWNER`** — act as someone other than the default owner. It is not one flag but ten:
`claim`, `release`, `reserve-id`, `new`, `workspace`, `done`, `discard`, `edit`, `branch` and
`autopilot merged`.
Visible here: 147 occurrences under `tests/`, 0 in any skill, 2 in `DESIGN.md` (on `workspace` and
`autopilot merged` only). It is the test suite's only way to simulate a second person. **And it has
an environment-variable equivalent**: `DESIGN.md:492` says the owner defaults to `$TASKRAIL_OWNER`,
then `user@host` — so a consumer needing a non-default owner (CI, a shared machine, a service
account) would set the variable once rather than pass the flag ten times, and no grep for `--owner`
could see them doing it. **Removal is implausible and this question expects the answer A.**
**Q: confirm `--owner` stays and is documented?**
→ **A (recommended, default)**: a small `chore` adding one sentence to §6.2, beside the existing
line about the owner default, saying every command that acts as a person takes `--owner` and that
`$TASKRAIL_OWNER` is the ordinary way to set it. This is the one route-A answer that needs its own
task, because T098 touches §4 and §7 and this belongs in §6.
→ **B**: not recommended — it would remove the suite's only second-person mechanism.

**One thing that is not a question.** Whatever you answer to 1, the error message at
`backlog.py:240` refuses a foreign epic ID by quoting the prefix's value and never naming
`epic_prefix`. That is a defect on its own terms and it is code, so it is neither T098's nor this
task's; it is offered as the optional extra under question 1.

## What would change the decision

- **The human naming a private consumer** for any of the seven. That settles that option as *wanted*
  and should be recorded here, so the next audit does not re-ask it. It is the single thing this
  spike exists to obtain.
- **T094 landing.** Once `validate` warns about a key it does not know, a configuration removal stops
  being silent, and questions 1 and 2 can be revisited on much cheaper terms. Until then, route B for
  either key is blocked on it.
- **A second visible consumer repository.** Every "no visible setter" here is a statement about one
  `.taskrail/config.toml`. A second one would re-class questions 1 and 2 immediately.
- **`taskrail import` being run by anyone.** It is the common consumer of both configuration keys
  (*V8*), and this repository never ran it. A consumer who imports a foreign backlog answers
  questions 1, 2 and 3 at once.
- **An option turning out to be broken.** *V10-V15* found all seven working, so no question here is
  about a defect. If one later fails, its question is void and becomes a bug.
- **The core skill's "never invent an ID" rule changing.** It is the argument for removing
  `epic add --id`; if the rule softens, question 3's balance moves.

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
git log --oneline -S'"--limit"' -- src/taskrail/cli.py          # V16: eceb908
git log --format='%h %ad %s' --date=short --reverse | head -5   # V16: the first commits
```

Which commands define each flag, from the live parser (*V7*):

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

**V10-V15, the probes.** They write only under `$P` and `$Q`, throwaway directories outside this
repository. `git init` is needed because several commands refuse to run outside a git repository.

```bash
P=$(mktemp -d); uv run taskrail --root "$P" init; git -C "$P" init -q -b main
git -C "$P" add -A; git -C "$P" -c user.email=p@l -c user.name=p commit -qm probe

uv run taskrail --root "$P" epic add --id E42 --name "Chosen ID" --objective "…" --json   # V10
uv run taskrail --root "$P" epic add --file epics/custom.md --name "Named" --objective "…" --json   # V11
uv run taskrail --root "$P" epic split E42 --file epics/split-here.md --json              # V12
uv run taskrail --root "$P" new --epic E42 --kind chore --title "First probe task" --pts 1
uv run taskrail --root "$P" new --epic E42 --kind chore --title "Second probe task" --pts 1
uv run taskrail --root "$P" new --epic E42 --kind chore --title "Third probe task" --pts 1
uv run taskrail --root "$P" next; uv run taskrail --root "$P" next --limit 2              # V13
uv run taskrail --root "$P" epic add --id EP01 --name "Foreign prefix" --objective "…"    # V9: exit 1

Q=$(mktemp -d); uv run taskrail --root "$Q" init; git -C "$Q" init -q -b main
# add `epic_prefix = "EP"` and `id_digits = 4` under [[backlog]] in "$Q/.taskrail/config.toml"
uv run taskrail --root "$Q" epic add --name "Foreign prefix" --objective "…" --json       # V14: EP01
uv run taskrail --root "$Q" new --epic EP01 --kind chore --title "Probe task" --pts 1 --json  # V15: T0001
uv run taskrail --root "$Q" validate                                                      # V15: 0 errors
```

## Outcome

*To be completed after the `decide` gate, with the human's seven answers and the follow-up tasks
each one opens.*
