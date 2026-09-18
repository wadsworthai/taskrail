# T100 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact at commit 8202d9b, the diff against the base (the artifact only), and the
lane's re-verification of all four premises — in particular the one the orchestrator had only
checked partly: the whole route run for real with `taskrail` absent from `PATH`, bootstrapping from
a tag through `uvx` and then calling the committed wrapper.

Two findings from that probe are worth keeping in the write-up: `init` **pins the version it ran
as**, so the bootstrap tag becomes the pin and the wrapper afterwards reproduces exactly the
taskrail that wrote the repository; and the prerequisite really is `uv` alone.

The branch name came from the kind's template (`T100-make-uvx-the-documented-default-and-stop`)
rather than the orchestrator's brief, which had shortened it. The template is what `show` reports
and what every sibling lane used; the lane was right to follow it, and nothing is renamed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | How far "everything oriented to uvx" reaches in README's *Use* | one sentence above the block · rewrite every example · rewrite some | **one sentence, as recommended** | The examples are a scannable reference; a 22-character prefix on thirty lines would push the aligned comments off and force a re-wrap for no new information. One sentence saying a repository calls taskrail through the wrapper, and that the examples are written short, carries the fact without the noise. Two spellings in one block would read as an oversight. |
| 2 | `taskrail self upgrade` | README and §9 · §9 only · README only · deprecate it | **both places, as recommended** | It reinstalls a global CLI and never touches the pin, so it is meaningless for a repository that never installed one — where upgrading is `uvx --from "git+…@vX.Y.Z" taskrail upgrade`, one command that moves the pin and reinstalls the skills. Documenting the recommended route without its upgrade path would be half a recommendation. Deprecating it is out of scope and a test pins its command string. Confirm the one-command upgrade by running it, as you planned. |
| 3 | Does `init`'s report need a word? | no, leave `install.py` alone · add a note | **no, as recommended** | The task made this conditional on the report assuming a global install, and the lane checked every note it can emit: none mentions installing, upgrading or calling a global `taskrail`. A new note would print on the global-install route too and is a separate task if ever wanted. |
| 4 | `CHANGELOG.md`'s header block, above `## Unreleased` | yes, widen the touch map · leave it | **yes, widen it** | The header teaches `uv tool install` only; leaving it would ship a changelog that contradicts the README beside it. Two lines: lead with the uvx form, keep the other as the alternative. Asking rather than assuming was right — the touch map said `## Unreleased`. |
| 5 | README's *Releasing* step 3 | yes, "on both routes" · leave it | **yes** | Four words, and it makes the release checklist cover the route this task makes the default. A checklist that verifies only the secondary route is the way a documented default quietly stops working. |
| 6 | Open the deferred test task? | yes · note it in the artifact | **yes, open it** | The task deferred it and asked for it only if the work showed it was needed. It did: the route becomes the documented default, nothing in `tests/` exercises it, and the lane had to build a purpose-made `PATH` by hand to prove it works. A chore in E05, 2 points, no dependencies. |

Instructions given with the answers: re-run the bootstrap by copying the commands out of the
rewritten README verbatim, with `taskrail` absent from `PATH`, so the documentation is tested as
written rather than as intended; keep the global-install route fully supported; and touch neither
`DESIGN.md` §4 nor §7, which T098 owns.

## implement gate

Reviewed: the diff read by commit range in the lane's worktree — `DESIGN.md` confined to §9 (two
hunks, 1204-1213 and 1253-1268, with §4 and §7 byte-identical to the base, so nothing for T098 to
sequence), the rewritten README *Install*, the one sentence added to *Use*, the two corrected
comments, `CHANGELOG.md`'s header and entry; `grep -n "optional flags"` confirming the pre-existing
defect the lane reported; and `taskrail checks T100` re-run by the orchestrator, which passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the applied change what was approved? | accept · amend | **accepted** | All six decisions applied and nothing else. No behaviour changed: `install.py`, the wrapper, the generated workflow and the shipped skills are untouched, and `tests/test_install.py:283`, which pins the `self upgrade` command string, still passes because no command changed. |
| 2 | "Two optional flags:" above a list of three, pre-existing and unrelated to this task's subject | fix it here · leave it and open a task | **fix it here** | The `taskrail` skill allows fixing something on the way when it is small and inseparable; this is two characters inside the very section this task rewrites and leaves in its final form. Opening a one-point task for it would be the bureaucracy KISS exists to prevent, and shipping a freshly reviewed section with an obvious miscount would be worse. Reporting it rather than fixing it silently was still the right order. |
| 3 | The evidence standard | accept · ask for more | **accepted, and worth naming** | The lane copied the commands out of the rewritten README verbatim, with `taskrail` absent from `PATH`, so the documentation was tested as written rather than as intended — including that `.taskrail/bin/taskrail validate` runs without a leading `./`. It also ran the upgrade forward from `v0.2.0` to `v0.3.0` to show one command moving the pin, and deliberately did **not** run `self upgrade`, which would have installed a CLI on this machine — the exact side effect the new text attributes to it. |

## Conflict handling agreed for all lanes

Run 20260918-1. T098 is editing `DESIGN.md` §4 and §7; T100 edits §9 only.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by section · shared | **T100: `README.md`, `DESIGN.md` §9, `CHANGELOG.md`; T098: `DESIGN.md` §4 and §7** | The lane confirmed §9 states no configuration key and no command signature, so it needs nothing from T098's sections and asked for no sequencing. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1), appended index rows (2), changelog bullets (2); a conflict inside `DESIGN.md` escalates** | The two lanes write to disjoint sections of that file, so a conflict there would mean one of them strayed. |
| 3 | May this lane change behaviour? | allow · forbid | **forbidden** | It is documentation. The global-install route stays supported exactly as it is, and `install.py` is untouched under decision 3. |
