# T104 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact at commit 7e72dc5, the diff against the base (the artifact and one index row;
the skill untouched, as `scope` requires), and the lane's re-verification — the flag is a silent
no-op with the key unset (byte-identical output, nothing on stderr, 0.255s), exactly two lines in the
repository ship the command, and no test asserts on the clause being changed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The skill wording | accept as written · shorter, dropping the consequence · longer, citing §6.4 | **accept, with one grammatical correction** | The three properties it buys are the right ones: it names the key in full so it can be grepped, it states the *silence* — which is the half a user cannot discover, and the asymmetry with `claims --remote` that produced route C — and it keeps the mirrored consumer's stake so an executor does not drop the flag from habit. Breaking it out of the em-dash sandwich is what stops it being read past. **The correction:** the proposed fifth sentence begins "That `show`'s `base.onto` is the ref to branch from — …", which is a fragment left over from splitting the original sentence. It needs a subject and verb of its own. |
| 2 | `README.md`'s line | same treatment, minimal form · leave it | **change it, minimal form** | Different audience: a human skimming a command reference, not an agent following an instruction, so it gets the named condition and nothing else. The lane's observation decides it — the flag's own `--help` is today more informative than the README line teaching it. |
| 3 | The installed copies colliding with T099 | both lanes regenerate, orchestrator resolves with `upgrade --force` · this lane skips `upgrade` · the orchestrator regenerates after both merge | **both lanes regenerate, as recommended** | The lane's reasoning is right and worth recording: `.taskrail/installed.json` is a map of sha256 hashes and the installed skill is the source with the harness marker replaced, so both are pure functions of the source tree. A rebase conflict there carries no information that can be lost, and `taskrail upgrade --force` reproduces the merged content exactly — known conflict class 3. The one thing to get right is the order: resolve the source `SKILL.md` conflict first, then regenerate. Skipping `upgrade` would leave the branch internally inconsistent in review and only work if T099 merged second, which no lane controls. |

Instructions given with the answers: keep the diff to `SKILL.md` lines 64-68 and `README.md`'s one
line; fix the fragment before committing.

## implement gate

Reviewed: the diff by commit range — the skill's step 3, `README.md`'s one line, and what `upgrade`
regenerated; `taskrail checks T104` re-run by the orchestrator, which passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the change what was approved, with the fragment fixed? | accept · amend | **accepted** | "Take `show`'s `base.onto` as the ref to branch from" is imperative like the rest of the step, and the lane read the whole step back afterwards rather than only the hunk. |
| 2 | The hunk ending two lines further down than named at `scope` | accept · force the old wrap point | **accepted** | The text no longer ends where the original line ended, so the next sentence rewraps across the boundary. Forcing a re-sync would have cost either a 45-character line or a rewrap of the rest of the paragraph. Everything past `and report \`base.reason\`.` is byte-identical, and lines 64-71 are still sixty lines from T099's. Reporting the discrepancy against its own `scope` statement is what made it a decision rather than a surprise. |
| 3 | A `CHANGELOG.md` entry | **yes** · leave it | **yes, add one** | T091 is the exact analogue — shipped skill prose, needing `taskrail upgrade` — and it has an entry. A consumer whose installed `SKILL.md` changes on upgrade should find out why in the changelog. The conflict cost is real but small: appended bullets are known conflict class 2, and this run has resolved several. |

Instructions given with the answers: three or four lines in T091's voice, appended last in
*Unreleased*, ending with `taskrail upgrade`; the touch map is widened to `CHANGELOG.md` for it.

## Conflict handling agreed for all lanes

Run 20260918-1. T099 and T104 both edit `src/taskrail/skills/taskrail/SKILL.md` — the only genuine
file overlap of the run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which lines of the shipped skill? | split by line · one lane only | **T099: the YAML `description` (line 3) and the backlog-file prose (line 11). T104: step 3's `--fetch` clause (lines 64-68)** | Sixty lines apart, each named at its gate, so git replays them as independent hunks. |
| 2 | The installed copies and the manifest | regenerate on both branches, resolve with `upgrade --force` · one lane only | **regenerate on both** | Known conflict class 3, and both files are derived, so nothing is lost. |
| 3 | May either lane touch the other's lines? | allow · forbid | **forbidden** | A conflict inside a shipped skill is not a known conflict class and would escalate to the human. |
