# T115 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## frame gate

Reviewed: the artifact `docs/spikes/T115-decide-how-the-wrapper-and-the-cli-resol.md` and its commit
`dbf13ba` (artifact and index row alone); the four pieces of code the lane quoted — the wrapper's
`root=` computation, `cli.py`'s `find_root(Path.cwd())`, the `claim` warning in `_freeze_branch`,
and `install.PACKAGE` against `cmd_upgrade`'s `root`; and §9's current sentence.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Narrow the scope by dropping the `upgrade --force` reproduction and relying on the code reading? | **no, keep it** · drop it | **keep it** | It is the case that produces no warning at all, and the one that already cost this repository a silently dropped change. A spike whose recommendation rests on a reading of the case that matters most is the kind of premise this run has had to send back twice. |

No decision was needed at this gate and none was invented. The framing stands as the lane wrote it.

Noted for the `decide` gate, which escalates to the human: the lane's sharpest finding is that the
wrapper already computes its own root — `root=$(cd "$(dirname "$0")/../.." && pwd)` — uses it to read
the pin and to select the `local:` source project, and then never passes it to the CLI. So the
wrapper's location decides *which taskrail runs* and the cwd decides *which repository it acts on*.
That asymmetry, not a missing feature, is what the decision is about, and it should be put to the
human in those terms.

## escalated to the human — the decide gate

`spike:decide` is in this repository's `escalate_gates`, so the gate's three questions went to the
human with the lane's evidence and recommendations.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| Q1 | Should the wrapper pass its own root to the CLI, on all three `exec` paths? | **yes** · document the convention only · only for `local:` pins · a new environment variable | **yes** | The rule collapses to one sentence — the wrapper you invoke is the repository you act on — and it fixes both observed incidents: the claim that cost T106, T108 and T110 a release-and-re-claim, and the cross-checkout `upgrade` that silently reverted a lane's installed copy. The one behaviour change, a wrapper aimed at another repository without `--root`, is a caller who already gets the wrong pinned version today, and `--root` still wins. `taskrail checks` was measured and is untouched by the change, which removes the one objection that would have been decisive. |
| Q2 | A new CLI warning when the wrapper's location and the cwd disagree? | **no new warning; extend the existing one to `done`** · no warning at all · warn when the cwd is outside the resolved root | **no new warning, and `done` warns as `claim` does** | With Q1 adopted the resolved root is the wrapper's, so a disagreement warning would fire only on correct use — a subdirectory, or a deliberate `--root`. `done` is the opposite case: it puts a `✅` into the wrong backlog in total silence, and `_freeze_branch` already computes what it would need. It is the command with the worst blast radius and the only one of the two that reaches the case no root rule can see. |
| Q3 | `DESIGN.md` §9's wording | **the lane's proposed replacement, which follows from Q1** | **as proposed** | It states what the paragraph never did: the wrapper operates on its own checkout and passes that root to the CLI, so which wrapper is invoked decides which repository is acted on, and `--root` overrides it. |

Answered by the human (the repository's maintainer), 2026-09-18.

The lane's answer to the question the orchestrator put to it at the frame gate — what would make a
documented convention stick where three lanes already missed it — is recorded in the artifact and is
why the documentation-only option was declined: "run the wrapper from inside your worktree" is a
**cwd** discipline, and a cwd is ambient state that resets between commands, never appears in the
command an agent copies, and is invisible in a transcript. The three lanes were not missing a
sentence; the thing they controlled, the wrapper path they typed, was already correct. Q1 is the
change that makes that path the thing the rule is about.

## close

Reviewed: the whole diff `origin/main..HEAD` — the spike write-up and its index row, `DESIGN.md`
§9's last paragraph, T115's `✅` and the T118 and T119 rows, with no code, test, configuration or
skill touched; `taskrail validate` (108 tasks, 0 errors); the sandbox deleted and
`git worktree list` unpolluted.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | §9's added sentences stated planned behaviour in the present tense, unmarked | **send it back for the marker** · accept as written | **sent back; `(*planned, T118*)` added** | The wrapper does not pass its own root yet. A reader debugging a cross-checkout symptom would have read §9 as a description of the code and concluded the symptom was impossible — the same failure as the sentence this spike replaced, pointed the other way. `DESIGN.md` already marks the distinction (`(*implemented, T081*)`, and §12 at line 48), so this follows the file rather than inventing a convention. |
| 2 | Where the marker sits | **closing the pair of added sentences** · inside the first | **closing the pair** | The second sentence describes overriding the default the first introduces, so marking only the first would leave it reading as current behaviour. It also matches the house placement at lines 247, 1101 and 1435. |
| 3 | The artifact's *Outcome* still said §9 describes unimplemented behaviour without saying §9 marks it | **one clause, committed separately** | **as decided** | The lane raised it itself. A record of a decision about accuracy that is itself inaccurate would send the next reader looking for an unmarked paragraph. |
| 4 | Pull request type and scope | **`docs` / `repo`** | **`docs` / `repo`** | Every change on the branch is documentation: the write-up, §9's wording and two backlog rows. |
