# T112 — Replace section 12.3's unverified note on old lane handles with the measured reason

## Goal

`DESIGN.md` §12.3 ends with a shrug: after describing how a compacted or new orchestrator session
resumes a lane by its handle "while the agent can still reach it", it says the T033 trial saw a new
Claude Code session restart a lane instead, and that "whether an earlier session's handle still
reaches a lane is not verified".

[T057](../spikes/T057-check-autopilot-compaction-and-old-lane.md) measured it (its evidence E4) and
its decision record opened this chore to spend the finding. The design should carry the structural
reason instead of the open question — scoped to the one agent that was measured, and without
touching the restart-from-branch procedure T055 already wrote.

## Evidence

Everything below was read in this worktree
(`/thezone/shared/repositories/utils/taskrail/.worktrees/T112-replace-section-12-3-s-unverified-note-o`)
at `5dfcd8e`, the branch's base.

### The sentence to replace

```
$ sed -n '1422,1431p' DESIGN.md
### 12.3 Orchestrator and lanes

**The orchestrator** is the session the human talks to. It keeps a lane handle per task in the
run file, and a lane commits everything it finishes on its branch. A compacted or new
orchestrator session therefore rebuilds the run from `autopilot status` and the decision
records, resumes each lane by its handle while the agent can still reach it, and otherwise
restarts the lane from its branch with the lane brief's restart section, once the lane is
stopped at a gate or `silent` (T033 F2, *implemented, T055*). In the T033 trial a new Claude
Code session restarted a lane rather than resuming it; whether an earlier session's handle
still reaches a lane is not verified.
```

Only the last sentence — lines 1429 (from "In the T033 trial") to 1431 — is in this task's scope.

### What T057 measured (E4, quoted from the merged artifact)

`docs/spikes/T057-check-autopilot-compaction-and-old-lane.md`, section **E4 — A lane's conversation
belongs to the session that launched it**:

> The store keeps each lane conversation under its orchestrator session's own directory, named by
> the handle the run file records. Across the nine runs:
>
> ```
> lane handles recorded across all runs : 38
> handles with a transcript in the store: 38
> handles owned by more than one session: 0
> sessions holding lane transcripts     : 3
> transcripts stored outside a session  : 0
> ```
>
> There is no shared namespace a second session could address. This is the structural reason behind
> T033's F2 — a new session restarted a lane from its branch instead of resuming it — and it means
> that outcome was not an accident of one probe on one day.

The same artifact states the scope of that measurement under *Limits*:

> **One agent only.** Everything measured is Claude Code with one model; the storage layout in E4 is
> that agent's, and another agent may differ. OpenCode was not exercised at all.

And its decision record (`docs/autopilot/decisions/T057-check-autopilot-compaction-and-old-lane.md`,
decision 2) names this task's contract:

> B replaces §12.3's unverified sentence with the measured structural reason.

### Nothing in the suite asserts on §12.3

Two tests read the repository's own `DESIGN.md`, and both slice a section that is not §12.3:

```
$ grep -rn 'parents\[1\] / "DESIGN.md"\|ROOT / "DESIGN.md"' tests/
tests/test_config_unknown_keys.py:16:DESIGN = Path(__file__).resolve().parents[1] / "DESIGN.md"
tests/test_autopilot_parked.py:286:    design = (ROOT / "DESIGN.md").read_text(encoding="utf-8")

$ grep -rn 'design\[design.index\|DESIGN.read_text' tests/
tests/test_autopilot_parked.py:286:    design = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
tests/test_autopilot_parked.py:287:    section = design[design.index("### 12.7 Resources") : design.index("### 12.8 ")]
tests/test_config_unknown_keys.py:34:    section = DESIGN.read_text(encoding="utf-8").split("## 4. Configuration")[1]
```

`test_config_unknown_keys.py` parses §4's TOML fence; `test_autopilot_parked.py` slices §12.7 up to
§12.8, and also asserts on two strings it looks for in the whole file
(`--state running\|gate\|…` and `holds_lane`), neither of which is in §12.3. No slice boundary and
no whole-file assertion moves when text inside §12.3 changes. The other `DESIGN.md` matches in
`tests/` are module docstrings and a fixture the test writes itself
(`tests/test_autopilot_read_first.py:90–96`).

### The claim appears nowhere else

```
$ grep -rn "not verified\|still reaches\|previous session" src/ .claude/skills/ README.md CHANGELOG.md
src/taskrail/skills/taskrail-autopilot/SKILL.md:163:   that still reaches it, or restart it from its branch with the lane brief's restart workspace
.claude/skills/taskrail-autopilot/SKILL.md:163:   that still reaches it, or restart it from its branch with the lane brief's restart workspace
```

That line is the restart *procedure* ("resume by a handle that still reaches it, or restart from the
branch"), not the unverified claim, and it stays correct under the measurement: an orchestrator
resuming its own run's lanes is exactly the case where the handle does reach. It is also a file
another lane of this run owns, so this chore does not touch it.

## Change set

One file, one sentence.

**`DESIGN.md`** — §12.3, lines 1429–1431. Replace

> In the T033 trial a new Claude Code session restarted a lane rather than resuming it; whether an
> earlier session's handle still reaches a lane is not verified.

with

> On Claude Code a handle reaches a lane only from the session that launched it: the lane's
> conversation is stored under that session, keyed by the handle the run file records, and across
> nine runs all 38 recorded handles resolved under exactly one session each, none shared and none
> stored outside a session (T057 E4). A new session there restarts the lane from its branch, as the
> T033 trial did; another agent may store lane conversations differently.

The paragraph's first half — the procedure, `(T033 F2, *implemented, T055*)` — is unchanged, and so
is every other sentence of §12.3.

## Decisions needed

1. **The exact replacement wording**, and how it stays scoped to the agent measured without becoming
   a paragraph. Recommended: the two-sentence form above. It names the agent first ("On Claude
   Code"), gives the mechanism, carries the four figures as one clause, cites `T057 E4` in the
   citation style §12.3 already uses for `T033 F2`, keeps T033's observation as a consequence rather
   than as the evidence, and closes with one clause for portability.
   - Alternative A — one sentence: "On Claude Code a lane's conversation is stored under the session
     that launched it, keyed by the handle the run file records — across nine runs all 38 recorded
     handles resolved under exactly one session each, none shared and none stored outside a session
     (T057 E4) — so a new session there cannot address a previous session's lane and restart from
     the branch is the only path; another agent's store may differ." Shorter by a line, but it is one
     long sentence with an aside inside a dash pair, and it drops the T033 trial.
   - Alternative B — end the portability clause harder: "…; whether another agent's store allows a
     cross-session resume is unmeasured." More explicit that the gap moved rather than closed;
     slightly heavier, and it reintroduces the word the task is removing.
   - Alternative C — drop the figures and keep only the mechanism. Rejected in the recommendation:
     the figures are what turns "not verified" into "measured", and they are one clause.

2. **No `CHANGELOG.md` entry.** Recommended: none. `CHANGELOG.md` records user-facing changes to the
   tool, and this changes no behaviour, CLI surface, configuration or skill. The three most recent
   documentation-only tasks on `main` (T102, T097, T095) touched `TODO.md`, their artifact and its
   index and nothing else.

## Out of scope

- **The restart-from-branch procedure**, in §12.3 and in `taskrail-autopilot/SKILL.md` — the row
  says to leave it as it stands, and T055 wrote it. It also remains correct under the measurement.
- **`src/taskrail/skills/taskrail-autopilot/SKILL.md` and its installed copy** — another lane of this
  run (T111) owns that file. If the replacement needed a matching change there, this lane stops and
  says so instead of editing it.
- **The rest of §12** — §12.1 and wherever a run's count is chosen belong to T111; this lane touches
  §12.3 only.
- **T057's other two findings** (the orchestrator context budget, and a run that crosses a compaction
  boundary) — the first is T111, the second was deliberately not opened.
- **`CHANGELOG.md`**, per decision 2 above.
- **Code, tests and configuration** — none changes.

## Verification

- `taskrail checks T112 --stage implement` — the suite (`uv run pytest -q`); `lint` is not
  configured for this repository, which will be reported as such.
- `git diff` on the branch shows one file changed and one sentence replaced: no other line of
  `DESIGN.md`, and no other file but this artifact, its index row and the `TODO.md` status cell.
- `grep -n "not verified" DESIGN.md` returns nothing in §12.
- `.taskrail/bin/taskrail validate` passes.
