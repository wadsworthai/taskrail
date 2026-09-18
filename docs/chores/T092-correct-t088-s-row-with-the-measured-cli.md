# T092 — Correct T088's row with the measured CLI and configuration surface

## Goal

T088's row in `TODO.md` still opens with figures that were measured before T087 recounted the
surface: "18 subcommands, about 66 distinct flags and 19 first-level config keys". They are wrong,
and they are the numbers a reader of the backlog sees as the premise of a task that has since been
worked. This chore replaces them, through `taskrail edit`, with the measurement that is now on the
mainline.

**Two premises of this task's own row have changed since it was written, and the `scope` gate must
settle them before anything is edited.**

1. **"before T088 is worked" can no longer be honoured.** T088 was worked, closed and
   squash-merged while this task waited (`45a6b5d`, PR #23). Its artifact,
   `docs/spikes/T088-measure-the-cli-and-configuration-surfac.md`, is on the mainline.
2. **This row's own figures are less precise than T088's.** The row plans "about 70 distinct long
   flags and 9 first-level configuration names holding 42 documented keys". T088 counted from the
   live `argparse` tree and from `src/taskrail/config.py`, stated its method, and reports 71 long
   flags of taskrail's own (72 counting argparse's `--help`) and 9 first-level names holding **46**
   settable names. Writing this row's figures into T088's description unchanged would replace one
   imprecise sentence with another.

The change below therefore takes its figures from T088's merged artifact, not from this row.

## Change set

| File | Change |
|---|---|
| `TODO.md` | T088's description cell only, through `.taskrail/bin/taskrail edit T088 --description "…" --force --json`. No other cell, no other row, no hand editing. |
| `docs/chores/T092-correct-t088-s-row-with-the-measured-cli.md` | This artifact, carried through the stages. |
| `docs/chores/README.md` | One index row for this artifact. |

### The replacement description, in full

> 27 top-level commands, 42 commands at all levels, 71 long flags of taskrail's own (72 counting
> argparse's `--help`) and 9 first-level configuration names holding 46 settable names exist, some
> for a single or hypothetical consumer (claim_remote, branch_record_remote, resource pools and
> groups, notify). No function is unreachable, so the question is not dead code but options nobody
> sets. Report each option with its known consumers, what removing or defaulting it would cost a
> repository that installed 0.3.0, and a recommendation; change nothing in this task. Figures
> re-measured from the live argparse tree and the configuration parser; the counting method is in
> `docs/spikes/T088-measure-the-cli-and-configuration-surfac.md`, E1 and E5.

What changes and what does not: only the first clause's four figures are replaced, and one closing
clause is appended that names where the method lives. The suspect options, the framing ("not dead
code but options nobody sets"), the deliverable and "change nothing in this task" are kept
verbatim, because they are what the task was actually judged against.

Counts are not repeated without their method, because they do not survive being repeated without
it: T087 got 70 flags by one method and 72 by another from the same parser tree, and "46 settable
names" is not the same count as T087's "42 documented keys" — the difference is what a repeatable
table (`[[autopilot.group]]`, `[[autopilot.resource]]`) contributes, not a disagreement about the
parser. The final clause carries the reader to E1 and E5 rather than trying to state a method in a
one-line cell.

## Decisions needed

### D1 — What is this task still for?

Its stated purpose, getting T088 started from correct numbers, cannot be served. Three options
were costed:

- **Correct the row from T088's artifact** (recommended). The backlog row stops contradicting the
  merged write-up, and T088's artifact keeps a promise it already made in public: "they are
  corrected in the row itself by T092 (`chore`, open)". That forward reference is on the mainline;
  discarding T092 leaves it dangling. Cost: one `edit` and this artifact.
- **Correct it minimally** — replace the four wrong figures and stop, without the closing clause
  naming the method. Cheaper by one clause, and it loses the one thing that makes the figures
  re-checkable. The recommended option is this option plus that clause; I do not think the clause
  is worth dropping.
- **Discard the task** (`taskrail discard`, needs the human's say-so). Defensible only if the row
  is judged pure history. I recommend against it: the row is what a future reader meets first, the
  artifact points at this task by ID for the correction, and the work is a single command.

**Recommendation: correct the row from T088's artifact, with the description quoted above.**

### D2 — `--force` on a closed task

T088 is `done`, so `taskrail edit` refuses it (exit 5) and `--force` is required. The `taskrail`
skill calls `--force` "a decision to report at your next gate"; this is that report. Nothing about
the task's state changes — `--force` here only lifts the guard against editing a row that is no
longer pending, which is exactly the situation the correction exists for. **Recommendation: use
`--force`, on this row only.**

### D3 — Leave this task's own row alone?

T092's row still says "Replace T088's figures with these through taskrail edit, before T088 is
worked", with the superseded figures and a premise that no longer holds. **Recommendation: leave
it.** It is the closed record of what was planned, this artifact records what was done instead,
and editing it would rewrite history rather than correct a live premise. Say so if you want it
edited too; it is one more `edit`, in the same worktree.

## Decisions taken

All three were approved at the `scope` gate on 2026-09-18; the record is in
`docs/autopilot/decisions/T092-correct-t088-s-row-with-the-measured-cli.md` (`1911e1c`).

- **D1 — correct the row, do not discard**, with the closing method clause kept: two honest counts
  of the same parser tree gave 70 and 72, so a figure without its method is not re-checkable, and
  that clause is the only thing that makes these figures better than the ones they replace. The
  task's stated purpose (starting T088 from correct numbers) is spent, but its work is not: T088's
  merged artifact names T092 by ID as the place its row is corrected, and discarding would strand
  that forward reference on the mainline.
- **D2 — `--force`, on T088's description cell only.** It lifts the guard against editing a row
  that is not pending and changes no status, which the verification below shows.
- **D3 — leave T092's own row alone.** The distinction that decides it: **T088's row stated facts
  that were false and that a reader would act on; T092's row states an intention that expired.**
  An expired intention is not false, it is overtaken, and the row is the record of what was
  planned. What was done instead belongs here, in the artifact, and that is where it is.

## Out of scope

- `DESIGN.md` — T093's subject in this run; nothing here needs it.
- `CLAUDE.md`, any source file under `src/`, any skill, any test.
- `docs/spikes/T088-measure-the-cli-and-configuration-surfac.md` — the artifact is already correct;
  this task changes the row to agree with it, never the other way round.
- Any other `TODO.md` row, this task's included (D3), and any cell of T088's row other than its
  description.
- The follow-ups T088 opened (T094–T098) and the `DESIGN.md` documentation defects they cover.

## Verification

All commands were run in this task's worktree, on branch
`T092-correct-t088-s-row-with-the-measured-cli`, base `origin/main` = `b61bd41`.

**1. The edit went through the CLI, and refuses without `--force`.** Before the change, a probe at
the `scope` stage showed the guard, and wrote nothing:

```
$ .taskrail/bin/taskrail edit T088 --description "probe: does edit refuse a done task" --json
taskrail: T088 is done, not pending; pass --force to edit it anyway
exit=5
```

The approved edit, with `--force`, reported exactly one changed field and one changed file:

```
$ .taskrail/bin/taskrail edit T088 --description "…" --force --json
{ "id": "T088",
  "changes": { "description": { "from": "18 subcommands, about 66 distinct flags and 19 first-level config keys exist, …",
                                "to":   "27 top-level commands, 42 commands at all levels, 71 long flags of taskrail's own (72 counting argparse's --help) and 9 first-level configuration names holding 46 settable names exist, …" } },
  "branch": { "name": "T088-measure-the-cli-and-configuration-surfac", "recorded": false },
  "files": [ "TODO.md" ] }
exit=0
```

**2. One row, one cell, and the status untouched.**

```
$ git diff --stat
 TODO.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

The changed line is T088's row at `TODO.md:129`; its `✅`, ID, kind, points, dependency and title
cells are byte-identical on both sides of the diff, and only the description cell differs.

**3. The row and the status read back as intended.**

```
$ .taskrail/bin/taskrail show T088 --json
  "status": "done", "state": "done",
  "description": "27 top-level commands, 42 commands at all levels, 71 long flags of taskrail's own
  (72 counting argparse's --help) and 9 first-level configuration names holding 46 settable names
  exist, … Figures re-measured from the live argparse tree and the configuration parser; the
  counting method is in docs/spikes/T088-measure-the-cli-and-configuration-surfac.md, E1 and E5."
```

`--force` changed no status: T088 is still `done`.

**4. The backlog is valid.**

```
$ .taskrail/bin/taskrail validate
87 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit=0
```

**5. The stage's checks pass.**

```
$ .taskrail/bin/taskrail checks T092 --stage implement
== test: uv run pytest -q
1183 passed in 151.17s (0:02:31)
== lint: not configured
passed test
not configured lint
T092 …: passed
exit=0
```

`lint` is not configured in this repository, and the CLI reports it as such rather than as a pass.

**The figures now in the row agree with the merged artifact**, E1 (`commands (all levels): 42`,
`top-level commands: 27`, `distinct long flags (excl --help): 71`) and E5 (`46 settable names`
under 9 first-level names).
