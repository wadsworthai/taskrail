# T088 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## frame gate

Reviewed: `docs/spikes/T088-measure-the-cli-and-configuration-surfac.md` at the lane's frame commit,
the diff range against the base (the artifact and one appended index row), `taskrail checks T088`
re-run in the lane's worktree (`no checks` … `passed`), `taskrail validate` in that worktree (81
tasks, 0 errors), and the task row's premise. The row's figures are wrong and T092 exists to correct
them; the lane was given the measured figures in its brief and states in its draft that the row is
superseded, which is the right handling.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | How deep should the per-option detail go for ~110 items? | two layers · a full section per item · only the five options the row names | **two layers, as recommended** | The complete table keeps every item auditable, and the per-option sections go where the YAGNI question actually lives. Detailing only the five the row names would make the row's guess the answer, and that row has already proved unreliable. |
| 2 | Do findings become tasks on this branch, or only a list in the artifact? | propose at `decide`, open after it is answered · open none · open them during `investigate` | **propose at `decide`, open the approved ones before `taskrail done`** | As recommended, and it matches how T087 handled its own follow-ups. Opening rows during `investigate` would commit rows for findings the human has not accepted; opening none would leave the findings depending on someone re-reading the document. |
| 3 | Does the surface include the kind-descriptor schema? | exclude it, say so in *Limits* · include it | **exclude it, stated in *Limits*** | A kind descriptor is a consumer-authored document, not an option this repository ships; including it would add roughly another twenty keys and overflow a 3-point box. If it is worth measuring it deserves its own task, which the write-up may propose. |
| 4 | Flag-counting method | report with and without `--help` · one figure | **report both, and name the method** | Confirmed. Two independent counts of this surface already differed (72 including `--help`, 70 excluding it); a reader must be able to see which number they reproduced. The command counts (27 top-level, 42 at all levels) are exact and were reproduced independently. |

Instructions given with the answers: continue into `investigate` (gate `none`, no commit); keep the
throwaway enumeration script in the session scratchpad, outside the repository; classify by the
consumer ladder the draft defines, and never write that an option has no consumer when what was
verified is that none is visible in this repository.

## decide gate

The orchestrator answered the three organisational questions; the verdict itself went to the human
below. Reviewed: the artifact at commit 178077b, the lane's commits against `origin/main`,
`taskrail checks T088 --stage decide` and `taskrail validate` (81 tasks, 0 errors), and an
independent reproduction of the load-bearing findings — a bogus key added to a copy of this
repository's config left `validate` at 0 errors, 0 warnings, exit 0; `git grep` for `--file`,
`--id` and `--limit` outside `cli.py` returns nothing; `taskrail kind add` exits 2 while §7
documents it, and `list --eligible` is documented and absent; `config.py:48` is
`HANDOFF_MODES = ("sequential",)`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Should T092's description be corrected to the exact figures? | leave it, its executor reads this artifact · someone edits the row | **leave it** | As recommended. The difference is counting method, not fact, and "about 70" and "about 42" are honest. The lane must not edit another task's row, and neither should the orchestrator merely to sharpen an approximation. |
| 2 | A separate task for `--owner`? | fold it into task 2's question list · a task of its own | **fold it into task 2** | As recommended. 147 test occurrences, no skill and no documented workflow make it the clearest "a test but no user", but removal is implausible — it is the suite's only way to simulate a second person — so the likely answer is a line of documentation, not a decision. |
| 3 | Act now on the skills telling every executor to pass `show --json --fetch`, which is a no-op while `branch_record_remote` is unset? | wait for task 4 · change the skill now | **wait for task 4** | The one-line skill change depends on task 4's answer, and `src/taskrail/skills/` is outside this run's touch map. Recorded here so the finding is not lost. |

## escalated to the human

`spike:decide` is in this repository's `[autopilot].escalate_gates`, so the verdict went to the
human, with the alternatives and their costs as the lane stated them.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Accept the surface report and its five follow-up tasks? | accept the report and all five · only task 1 · accept, open nothing · reject the report | **accept the report and all five tasks** | As recommended. The report removes nothing and proposes no removal: each task is a question to be argued on its own merits when worked, which is what T087's prospective verdict requires. Task 1 — `validate` warning about a configuration key it does not define — is the only finding the measurement supports on its own evidence, and it is a precondition for retiring any key safely, since an unknown key today is ignored in silence. |

Answered by the human (the repository's maintainer), through the orchestrator, at the `decide`
gate of run 20260918-1.

## rebase after T087 merged

T087 was squash-merged into `main` as 4a956c4, and `autopilot merged T087 --cleanup` proved the
merge by content and removed its branch and worktree. This branch was stacked on it, so the
orchestrator rebased it while the lane was stopped at the `frame` gate:

```
git rebase --onto origin/main 45137368de55c2d6b55ea62198e0adae1f98af23
```

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts during the rebase | resolve known classes · stop | **none arose** | The lane's single commit touches only its own artifact and one appended index row; `main` already carried T087's rows. |

After the rebase: one commit ahead of `origin/main`, `git diff --check` clean, `taskrail checks T088`
passed, `taskrail validate` reports 81 tasks and 0 errors.

## rebase after T089 merged

T089 was squash-merged into `main` as 15823fc and `autopilot merged T089 --cleanup` proved it by
content. `review T088 --json` reported `rebase.needed: true` onto `origin/main`, with no unmerged
dependency, so the orchestrator rebased at hand-off, while the lane was stopped at the `close` gate:

```
git rebase origin/main
```

Three conflicts, all of the known classes, resolved without the human:

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `docs/spikes/README.md`: a row appended by each side | keep both · stop | **keep both, one entry per task** | Known class 2, appended index rows: T089's row came from the mainline, T088's from this branch. |
| 2 | `docs/autopilot/decisions/README.md`: a row appended by each side | keep both · stop | **keep both, one entry per task** | Known class 2, the same case in the decision-record index. |
| 3 | `TODO.md`: rows added on both sides, and two status cells | keep all rows, `✅` wins per ID · stop | **T093 from the mainline and T094-T098 from this branch all kept; T088 `✅` from this branch, T089 `✅` from the mainline** | Known class 1, backlog rows united by ID: a status that is `✅` on either side stays `✅`, and neither side carries a `Reopens:` commit the other lacks. |

After the rebase: six commits ahead of `origin/main`, `git diff --check` clean, `taskrail checks
T088` passed, `taskrail validate` reports 87 tasks and 0 errors, and the branch's diff adds only
this task's own files and rows.

## Conflict handling agreed for all lanes

Run 20260918-1, extended by the human to T090, T091 and T092 after T087 merged.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | one artifact per lane · shared edits | **Each lane edits only its own `docs/spikes/T0NN-*.md`, one appended row in `docs/spikes/README.md`, and its own rows in `TODO.md` through the CLI** | T088 and T089 run in parallel on the same artifact directory; nothing else is shared. `DESIGN.md` is T089's subject and off limits here; T088's own row is T092's job. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **Known classes only: appended index rows (class 2) and backlog rows (class 1)** | Both are resolved by the orchestrator at hand-off, and `autopilot status` reports them as known overlaps. |
| 3 | May a lane edit `CLAUDE.md`, `src/taskrail/skills/` or code? | allow · forbid in E08 | **Forbidden for the spikes of this run** | T088 and T089 are spikes: they decide, they do not adopt. Adoption is T090 and T091, which are separate tasks. |
