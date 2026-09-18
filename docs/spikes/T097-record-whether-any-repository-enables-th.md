# T097 — Record whether any repository enables the remote half of claims and branch records

> **Draft — `frame` stage.** The Question, what would answer it, the Approach and the Limits are
> settled below; Evidence, Options considered, Recommendation, What would change the decision and
> How to reproduce are written at the `investigate` and `decide` stages.

## Question

taskrail's claims and branch records each have a **local half**, which every installation uses, and
a **remote half**, which is off unless a repository names a remote for it:

- `[git].claim_remote` — also publish claims as refs under `refs/taskrail/claims/`, so a claim made
  in one clone is visible in another.
- `[git].branch_record_remote` — also mirror branch records as `refs/taskrail/branches/<ID>`, so a
  branch named or renamed in one clone resolves in another.

[T088](T088-measure-the-cli-and-configuration-surfac.md) E6 found that **no repository visible here
sets either key**: `claim_remote` is written as `""` in this repository's `.taskrail/config.toml`
and in the seed `taskrail init` writes, and `branch_record_remote` is written nowhere at all. Both
keys nonetheless guard code in `claims.py`, `ids.py`, `branches.py` and `cli.py`, and four flags
exist only for them — `claims --remote`, and `--fetch` on `list`, `show` and `next`.

The question this task puts to the human is therefore:

> **Does any repository you can see work taskrail from more than one clone — and so set
> `[git].claim_remote` or `[git].branch_record_remote`?** And, whatever the answer, **should the
> core `taskrail` skill go on telling every executor to run `taskrail show <ID> --json --fetch`?**

Only the human can answer the first half. This repository is public, taskrail is installed by
repositories that are not, and the publishing constraint in `CLAUDE.md` keeps them out of this
write-up. **Nothing in this document will say either key has no consumer**; the strongest claim
available, and the one used throughout, is that no consumer is *visible in this repository*.

### What this task is not

Bound by [T087](T087-decide-whether-the-design-principles-gov.md)'s verdict, now in `CLAUDE.md`:
the design principles are **prospective**, so **nothing here licenses a removal**. An answer of
"nobody sets them" does not delete a key, a flag or a line of `claims.py`. It produces, at most, a
task that *proposes* something, argued on its own merits when it is worked.

The one concrete proposal already named, in the task's own row, is much smaller than a removal.
The core skill's step 3 reads:

```
$ sed -n '63,66p' src/taskrail/skills/taskrail/SKILL.md
   claiming, in the checkout you are in. Under `"task"`: run `git fetch <base.remote>` first, with
   the mainline's own remote that `show` reported, then `taskrail show <ID> --json --fetch` —
   which also brings in branch names other clones recorded, when the repository mirrors them: its
   `base.onto` is the ref to branch from — the local or the remote mainline, whichever is further
```

That `--fetch` does nothing when `branch_record_remote` is unset, which is every installation
visible here. Dropping it would be a **one-line skill change, reversible, costing nothing to
propose** — but the skill ships to every consumer, and if a consumer *does* set the key, that step
is exactly what makes a branch renamed in another clone resolvable. Which is why the human's answer
decides it, and why this task asks before proposing anything.

## What evidence would answer it

The first half of the question is answered by the human alone. What this spike must put in front of
them, so the answer is one word and rests on today's tool rather than on T088's word:

1. **A re-verified state of the remote half** — the call sites, the flags and the configuration
   lines, measured on today's mainline, with a note if anything moved since T088.
2. **What the mechanism does when the key is unset**, run rather than reasoned: what `--fetch`
   actually does, and what `claims --remote` prints.
3. **What it does when the key is set**, run in a throwaway two-clone repository. T095 found the
   same discipline worth the cost: a broken option must never be mistaken for an unused one, and
   *is it wanted* is a different question from *does it work*.
4. **Every place the skill's `--fetch` step and its siblings reach a consumer**, so the proposal's
   blast radius is a fact and not a guess.
5. **Two named routes for the `--fetch` step**, each concrete, with a recommendation and a default,
   so a skipped question still has an outcome.

## Approach

1. Re-verify T088 E6's claims about both keys against the mainline — the call-site lists especially,
   which E6 gives line by line and which this task checks rather than recounts from scratch.
2. Probe the mechanism with both keys unset, in this repository: `show --json --fetch`, `list
   --fetch`, `next --fetch`, `claims --remote`, with exit codes and real output.
3. Probe it with both keys set, in throwaway clones outside this repository, so the keys are shown
   working and the question stays *is it wanted*.
4. Enumerate every consumer of the `--fetch` step: the core skill, the README's command list, the
   tests and `DESIGN.md`.
5. Put the result to the human at the `decide` gate as a **numbered questionnaire with a default
   per line**, in the shape T095 used, since they have seen that format once already.

The questionnaire planned is three questions:

| # | Question | Routes | Recommended / default |
|---|---|---|---|
| 1 | Does any repository you can see set `[git].claim_remote`? | **A** it is used — record that and re-ask nothing / **B** no consumer visible to you either | A |
| 2 | Does any repository you can see set `[git].branch_record_remote`? | **A** / **B** as above | A |
| 3 | Should the core skill keep `--fetch` in its `show <ID> --json` step? | **A** keep as it stands / **B** open a task proposing it be dropped / (a third route may be added at `decide` if the evidence turns one up) | decided by the answers to 1 and 2; default **A** |

Questions 1 and 2 are about a fact only the human holds. Question 3 is the only one with a change
behind it, and it is a one-line change to one file.

## Limits

- **Time box: this task's two points.** The investigation stops when the three questions can be put
  with re-verified evidence behind each.
- **No code, no `DESIGN.md`, no skill, no configuration and no other task's row is changed here.**
  The kind's `never_edit` is `code` and `specs`; adopting any answer is follow-up work. Two other
  lanes are running: T094 is in `config.py`, `project.py`, `DESIGN.md` and `CHANGELOG.md`, and
  T095 is at its own `decide` gate. This task touches its artifact, that artifact's index row, and
  its own backlog row through the CLI.
- **No removal is decided here**, whatever the answers are, and none is recommended. A "no
  consumer" answer produces a task that *proposes* one line of skill text, not a deletion of the
  remote half.
- **This document cannot name a private consumer.** An answer resting on one is recorded as *the
  human confirmed a consumer exists*, with no repository, client or use named.
- **The `--local-only` flags** on `claim`, `release`, `edit` and `branch` suppress the same two
  mechanisms and are described here for completeness, but no question is put about them: they are
  inert when the keys are unset and harmless when they are set.
- **`autopilot status --fetch` is a different flag** that happens to share the name — it fetches
  each mainline's remote, not branch records — and is out of scope.
