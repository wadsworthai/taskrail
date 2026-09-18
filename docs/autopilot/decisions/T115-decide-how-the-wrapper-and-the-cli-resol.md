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
