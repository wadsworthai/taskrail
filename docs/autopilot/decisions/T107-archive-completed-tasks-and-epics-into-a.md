# T107 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the artifact `docs/features/T107-archive-completed-tasks-and-epics-into-a.md` and its
commit `4b8028d` (the only commit on the branch, artifact and index row alone, working tree clean);
`taskrail checks T107 --stage plan` and `taskrail validate` (101 tasks, 0 errors) as the lane ran
them. Two of the plan's load-bearing findings were re-checked against the source by the
orchestrator rather than taken from the report: `src/taskrail/project.py:88` does raise
`depends-unknown` for a dependency that is not in the backlog, and `src/taskrail/ids.py:88`
`used_ids` scans only `backlog.file` and the epic files it lists, so an archive the scan does not
read would let `new` reissue an archived ID.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Trigger and command shape | as recommended (`taskrail archive [--backlog NAME] [--dry-run] [--json]`) · add `--epic`/positional IDs · dry run by default with `--write` | **as recommended** | The row already rules out anything automatic on `done`. Partial archiving has no caller today (YAGNI), and `import`'s dry-run-by-default exists because it converts a foreign file; this is an ordinary backlog edit, and every other writing command writes. |
| 2 | Archive file shape, default path and config key | as recommended (`[[backlog]].archive`, default `{artifacts}/archive.md`, mirroring the backlog's own tables) · bullet list or heading per task · one file per epic | **as recommended** | Keeping real pipe tables with an `ID` column is what makes the file greppable, lets `ids.used_ids` read it with the parser it already has, and lets the existing table merge driver merge it with no new code. The other shapes lose both. |
| 2a | Two backlogs resolving to the same archive path | refuse in the config's checks · allow them to share | **refuse** | Two backlogs sharing an archive would collide on IDs and on epic sections; the refusal is three lines in the existing `problems` list and turns a silent corruption into a message. |
| 2b | `archive = ""` as an off switch | config error · off switch | **config error** | An off switch has no caller: the command is manual, so a repository that does not want archiving simply never runs it. YAGNI. |
| 3 | A reopen after archiving | as recommended (`reopen` of an archived ID exits 3, naming the archive file) · an `unarchive` command or `reopen --from-archive` · the bare `no task T042` | **as recommended** | A lookup and a message, not a mechanism. Moving rows back, and recreating an archived epic's section, is real machinery for a case nobody has had yet; the message tells the human exactly where the row went and that the way back is a new task. |
| 4 | Does `validate` read the archive? | as recommended (no) · parse it for duplicate IDs and non-closed rows | **as recommended** | The hold-back rule keeps every dependency named in a backlog inside that backlog, so there is nothing to check across the boundary. `used_ids` reading the file is allocation, not validation. A second file in every load, for a class of error the command itself cannot produce, is the cost KISS refuses. |
| 5 | The merge driver | as recommended (add each backlog's archive to `known_conflict_paths` as class `backlog`) · leave it out | **as recommended** | It is the path list, not new driver code, and concurrent appends are exactly what §7.4's table merge exists to resolve. |
| 6 | Does this branch archive this repository's `TODO.md` for real? | as recommended (no: demonstrate on a scratch copy, open a follow-up chore) · archive for real here | **as recommended** | `TODO.md` is what every other lane and the orchestrator read, and run 20260918-1 still has open branches carrying rows this would move. Moving 84 rows and epic E07 mid-run puts noise on branches that did not ask for it. Open the follow-up chore on this branch, to be run once the run's branches are merged. |
| 7 | Full epic archiving, or rows only? | full (the `## Epics` row, the section, the epic's own file, the objective carried over) · rows only, leaving an empty epic behind | **full, as the lane recommends** | The principles judge what the change adds, and here the simpler-looking option does not produce the simpler outcome: an empty heading and table left in `TODO.md` is precisely the noise the task exists to remove, and a half-archived epic whose listing row is gone but whose file remains is an inconsistency the next reader has to explain. The `writer.Edits` addition stays minimal — delete a file, refresh the attributes — and is not generalized beyond this caller. |

Given with the answers:

- The row says "completed **and discarded**": treat both closed states the same everywhere, and make a
  test say so explicitly.
- Hold-back is part of the contract, not an implementation detail. `--dry-run` and the command's
  own output must name every row held back and why, so a human who expected a row to move is told
  where it is.
- The follow-up chore from decision 6 is opened with `taskrail new` on this branch; IDs are
  reserved across the clone, so it cannot collide with another lane's.
- Keep to the touch map below: T106 holds `tests/` for its own new file and, on a proven defect,
  `src/taskrail/install.py`. The plan confirms no `install.py` change is needed here.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits what, with T106 and T107 live | split by area · first come first served | **T107: the archive module, its `cli.py`/`config.py`/`ids.py`/`mergedriver.py`/`writer.py` wiring, its own tests, `DESIGN.md` §§3.1/4/7 and a new §7.6, `README.md`. T106: `tests/` (its own new file) and, only on a proven defect, `src/taskrail/install.py` or the wrapper template.** | The two tasks meet only in `tests/` and `install.py`; separate files and an ask-at-the-gate rule keep them apart. |
| 2 | The files both lanes append to | resolve at hand-off as known classes · forbid | **resolve at hand-off**: `TODO.md` rows united by ID, `CHANGELOG.md` bullets, `docs/*/README.md` index rows | They are the known conflict classes of the autopilot skill; every lane appends its own entry and none rewrites another's. |

## implement gate

Reviewed: commit `88e894e` and the diff `d3ca1a4..HEAD` (13 files, +885/-32); `src/taskrail/writer.py`
and the new `cmd_archive` read in full by the orchestrator rather than summarized; the sections of
`DESIGN.md` the diff touches, confirmed to be §4's config example, §7's command table, §7.4's driver
paths and the new §7.6, with `src/taskrail/install.py` and `tests/test_install.py` untouched as the
touch map required; the lane's failing-first run (22 failed, 80 passed), its
`taskrail checks T107 --stage implement` (1243 passed) and `taskrail validate` (102 tasks, 0 errors).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| A | The refusal of decision 2a was built in `cmd_archive` instead of at config load | **accept the command-level refusal as built** · the config-load refusal with a `{artifacts}/{backlog}-archive.md` default | **accept the command-level refusal** | The default is `{artifacts}/archive.md` and the artifacts root is repository-wide, so at config load every two-backlog repository — including `DESIGN.md` §4's own example and four test fixtures — would exit 2 on every command, archiving or not. The decision's intent was that two backlogs never mix in one file; writing is the only operation that could mix them, so the check belongs where the writing is. Changing the default instead would make every single-backlog repository, which is the common case, carry a backlog name in its archive's file name for a clash it cannot have. |
| B | Does `archive` belong in the core skill's CLI list? | **leave the skills untouched, as the lane recommends** · add one line | **leave the skills untouched** | Archiving is a maintainer's periodic cleanup, never a step of a task's procedure, and the skills describe what an agent working a task does. It would also churn the installed copies under `.claude/`, which are a known conflict class, for a line no lane would act on. `DESIGN.md` §7.6 and `README.md` are where a human looks for it. |

Given with the answers: the plan's estimate of three held-back rows was wrong and the code is right —
the approved fixed point holds back nine on this repository's own backlog, because a held row is
itself a dependency further up the chain. Correct the number in the artifact where the plan stated
it, so the record does not carry a figure the implementation disproved. At `verify`, also exercise
the archive whose parent directory does not exist yet, and the second run that appends to an archive
already holding an epic section.
