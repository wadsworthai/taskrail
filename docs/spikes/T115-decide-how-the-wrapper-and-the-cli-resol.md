# T115 — Decide how the wrapper and the CLI resolve the repository root when the cwd is another checkout

**Verdict** — *pending; this document is the `frame` draft.*

## Question

The wrapper `.taskrail/bin/taskrail` resolves the repository it operates on from the **process
cwd**, not from its own location, while it resolves the **code** it runs from its own location.
A worktree's own wrapper, run from a shell sitting in another checkout, therefore runs the
worktree's taskrail against the other checkout's backlog, claims, config and git state, and says
nothing about it in most commands.

Three decisions are wanted:

1. Should the wrapper derive `--root` from its own path, so that `.worktrees/X/.taskrail/bin/taskrail`
   always operates on `.worktrees/X` whatever the cwd is?
2. Should the CLI warn when the wrapper's location and the resolved root disagree?
3. What should `DESIGN.md` §9 say? Its current text claims `local:<path>` makes "a worktree run its
   own branch's code", which is true of the code and false of the target repository — the sentence
   most likely to have produced the wrong mental model.

## Evidence that would answer it

- What the wrapper actually does with its own path and with the cwd, read from the file it writes
  (`src/taskrail/install.py`) and from the copy on disk.
- Where the CLI takes its root from, per command group (`find_root(Path.cwd())`, `_install_root`,
  `--root`), and which commands already notice a mismatch.
- The **visible** symptom, reproduced: a claim recorded against the wrong checkout, and the exact
  text of the warning `taskrail claim` prints, so its mitigating power can be judged rather than
  assumed.
- The **silent** symptoms, reproduced in a throwaway repository: at least `done` (a status written
  into the wrong checkout's backlog) and `upgrade --force` (the historical incident: a lane ran the
  primary checkout's wrapper inside its own worktree and installed the primary checkout's skill
  sources there, dropping the lane's own change from the installed copy, with no warning at all).
- The legitimate uses that a location-derived `--root` or a new warning must not break: running the
  wrapper from a subdirectory, running a checkout's wrapper against another repository on purpose,
  and `taskrail checks`, which runs commands in another worktree by design.
- What a wrapper that passed `--root` would cost: which commands take a root differently
  (`init`, `checks`, `autopilot`), and whether `--root` given twice is an error.

## Approach

1. Read the wrapper, `find_root`, the claim warning and `install.upgrade`'s choice of sources, and
   quote them exactly.
2. Reproduce each symptom in a throwaway repository under the scratchpad — never in this
   repository's checkouts, and never against another lane's worktree — recording the exact
   commands and their real output.
3. Reproduce the legitimate cases against the same throwaway repository, to see what a
   location-derived root or a warning would do to them.
4. Weigh the options against `CLAUDE.md`'s design principles, KISS and YAGNI in particular, and
   against the fact that a documented convention has already been missed three times in one run.
5. Write the decision with a single recommendation per question, and open follow-up tasks for
   whatever the human accepts.

## Limits

- **Time box**: this is a 2-point spike; the investigation stops once each symptom is reproduced
  once and each legitimate case checked once.
- **No code and no test changes.** The deliverable is this document. If the answer is that the
  wrapper should change, that is a follow-up task, not work done here. The only file outside
  `docs/spikes/` this task may touch is `DESIGN.md` §9's wording, and only if the `decide` gate
  approves it.
- **Not covered**: Windows and non-POSIX shells (the wrapper is `/bin/sh`); `TASKRAIL_BIN`, which
  overrides the wrapper entirely and is out of scope; the globally installed CLI, which has no
  repository location to derive a root from and is unaffected by question 1; and any change to how
  the autopilot orchestrator instructs its lanes, which is a separate surface.
- **Escalation**: this repository sets `escalate_gates = ["spike:decide"]`, so the `decide` gate's
  questions go to the human, not to the orchestrator.

## Evidence

*(to be written in `investigate`)*

## Options considered

*(to be written in `decide`)*

## Recommendation

*(to be written in `decide`)*

## What would change the decision

*(to be written in `decide`)*

## How to reproduce

*(to be written in `investigate`)*
