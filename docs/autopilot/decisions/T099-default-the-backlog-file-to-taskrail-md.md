# T099 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan artifact at commit bb09b1e, the diff against the base (the artifact and one index
row; no source touched, as `plan` requires), and the six probes the lane ran rather than assumed —
that `file` is required today, what `validate` says when it names a missing file, that `upgrade`
leaves a seeded file byte-identical, how T094's warning interacts, and the demonstration of the
problem itself: `init` over a repository that already keeps its own `TODO.md` adopts it silently and
leaves the repository failing `validate` out of the box.

The strongest thing in the plan is E4, and it should lead the write-up: **`file` is required today,
so no configuration that loads at all omits it**, which means adding a default cannot change any
existing repository's behaviour. That is a proof, not a reassurance, and it is what makes the rest
of the change safe.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Parser default, `init`'s seed, or both? | both, from one constant, with `init` still writing the key · seed only · parser only | **both, as recommended** | Seed-only leaves "the default" living in a template and a hand-written config still unable to omit the key; parser-only leaves `init` seeding `TODO.md`, which is the actual complaint. Writing the key explicitly in the seed is right for the reason given: the seed already writes `mainline` and `artifacts` though both have defaults, and a config that names its file survives any later change of default. |
| 2 | `README.md`, which T100 is rewriting | **defer it** · edit now and resolve at rebase · a follow-up task | **defer: do not touch `README.md` in this stage** | T100 is published and waiting to be merged, and it rewrites the very sentences these two words live in. A conflict inside `README.md` is not a known conflict class, so it would escalate to the human — for two words. Do the rest first; when you reach the `implement` gate, ask, and the orchestrator will say whether T100 is on the mainline. If it is, its branch is rebased and the two swaps are applied to the final text; if it is not, they become a one-line follow-up. |
| 3 | The shipped `taskrail` skill | stop naming a file · swap `TODO.md` for `TASKRAIL.md` · leave it, open a follow-up | **edit both lines, with one amendment to the wording** | The prose line should stop fixing a name, as proposed: the file is whatever the config names. But the YAML `description` is what drives skill triggering, and removing every concrete file name from it loses a real trigger word. Name the default as an example instead of as the only possibility — "a Markdown file, `TASKRAIL.md` by default" — so the description stays true and still matches a human who says "look at the backlog file". Run `taskrail upgrade` afterwards so this repository's installed copies match, as `CLAUDE.md` requires, and expect `.claude/` files in the diff. |
| 4 | Rename `DEFAULT_TODO` and its `# TODO` heading | rename to `DEFAULT_BACKLOG` and `# Backlog` · leave both | **rename, as recommended** | A file called `TASKRAIL.md` whose first line is `# TODO` is the kind of small incongruity that makes a reader doubt the rest. The cost is three mechanical test references and one line of §3.1. |
| 5 | The `DESIGN.md` line list, including §1 and §7.3 outside the sections the row named | approve as listed · restrict to §3, §4, §9 | **approved as listed, and §9 needs nothing** | §1 states the file name, so it would be left false. §7.3's sentence about `init` leaving an existing `TODO.md` alone becomes false the moment this lands, and the lane was right to refuse to leave it. §9 is correct as written and staying out of it also keeps this lane clear of T100. The §4 example must stay valid TOML, since `tests/test_config_unknown_keys.py` parses it — T094's drift guard, now doing its job for a change it never anticipated. |
| 6 | Confirm the intended behaviour change | confirm · reconsider | **confirmed** | `init` creating `TASKRAIL.md` beside an existing `TODO.md` instead of adopting it is the point of the task. Keep the adoption path explicit in the write-up: set `file = "TODO.md"`, or `taskrail import TODO.md --write`. |

Instructions given with the answers: tests before the implementation, one per acceptance criterion,
each observed failing; name the forward-compatibility cost in the `CHANGELOG.md` bullet — a config
written for the new CLI that omits `file` will not load on v0.3.0 or earlier; and rename or migrate
nothing, this repository's own `TODO.md` included.

## implement gate

Reviewed: the change in `config.py` and `install.py` read by commit range — one constant, a
dataclass default, `expect(..., DEFAULT_BACKLOG_FILE)` in place of `required=True`, and the seed
with its renamed constant and heading; the red-first evidence, where eight of nine tests failed for
their own assertions and the ninth, the regression guard on behaviour that must not move, passed
before and after; and `taskrail checks T099` re-run by the orchestrator, which passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the implementation what was approved? | accept · amend | **accepted** | Both halves from one constant, `init` still writing the key, `TABLE_KEYS` untouched so T094 keeps warning about a misspelling of `file`, and `seed()` itself unchanged — which is what makes the "nothing existing changes" criteria hold. |
| 2 | The eleven existing tests it had to update | accept · question them | **accepted** | Each was a test that goes through `init` and then assumes the seeded name, including `.gitattributes`' `/TODO.md merge=taskrail`. The ones deliberately left alone — `conftest.py`'s `BASE_CONFIG` and everything built on it, which writes `file = "TODO.md"` itself — are a second, larger proof that a repository naming its file is untouched. |
| 3 | The test the lane corrected rather than the code | accept · investigate | **accepted** | Its first version asserted the whole repository was byte-identical after `upgrade`, which is false: `upgrade` legitimately rewrites the version pin. Narrowing it to the backlog file and the `file = "TODO.md"` line pins the property that matters. Correcting a test that was wrong, and saying so, is better than loosening one that was right. |
| 4 | The README swaps, deferred at the `plan` gate | accept · re-check | **accepted** | The lane read T100's merged text before editing, found both sentences survived word for word, left the two occurrences that name the *source* of an import, and recorded the intended final text in the artifact in case the rebase conflicts on the neighbouring line. That is the deferral doing exactly what it was for. |

## Conflict handling agreed for all lanes

Run 20260918-1. T101 edits one line of `cli.py`; T102 edits `DESIGN.md` §6.2; T100 is handed off and
waiting to be merged.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `DESIGN.md`, edited by two live lanes | split by section · one lane only | **T099 takes §1, §3.1, §4 and §7.3; T102 takes §6.2; neither enters §9, which T100 rewrote** | Three lanes have now written to this file in one run without a conflict, because each was given sections and asked to name its lines at the gate. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1), appended index rows (2), changelog bullets (2); a conflict inside `DESIGN.md`, `README.md` or `cli.py` escalates** | Which is why decision 2 defers the README rather than betting on a clean merge. |
| 3 | May this lane migrate an existing backlog file? | allow · forbid | **forbidden** | The task is a default, not a migration. Nothing renames an existing repository's file or offers to. |
