# T097 — Record whether any repository enables the remote half of claims and branch records

**Verdict** — Both keys are **off in every installation visible here**, exactly as
[T088](T088-measure-the-cli-and-configuration-surfac.md) E6 recorded, and its call-site lists
re-verify line for line. But the row's one concrete proposal — dropping `--fetch` from the core
skill's `show <ID> --json` step — **is the wrong change, and this spike recommends against it on
measured grounds rather than on caution**. Two findings decide it. First, the flag costs a
repository that has the key off *nothing at all*: byte-identical output, exit 0, no message,
0.224s against 1.561s for a real fetch of the same origin, because `cli.py:67` returns before any
git call. Second, for a repository that has the key *on*, that step is not a nicety: the suite's
`test_show_fetch_resolves_a_branch_renamed_in_another_clone` shows that without it `show` reports a
finished task as `pending` with a `template` branch name, and `test_list_and_next_fetch_agree` shows
a dependent task dropping out of `next` entirely. Dropping the flag would trade nothing saved for a
silent wrong base. So the question put to the human is narrowed: **does any repository you can see
set either key**, and should the skill keep the flag as it stands, drop it, or — the route this
spike recommends — **keep it and say plainly that it does nothing unless the repository mirrors
records**.

This spike changed no code, no configuration, no skill, no `DESIGN.md` and no other task's row.

## Question

taskrail's claims and branch records each have a **local half**, which every installation uses, and
a **remote half**, which is off unless a repository names a remote for it:

- `[git].claim_remote` — also publish claims as `refs/taskrail/claims/<ID>`, so a claim made in one
  clone is visible in another (`DESIGN.md` §6.2).
- `[git].branch_record_remote` — also mirror branch records as `refs/taskrail/branches/<ID>`, so a
  branch named or renamed in one clone resolves in another (§6.4).

T088 E6 found that **no repository visible here sets either key**, while both guard code in
`claims.py`, `ids.py`, `branches.py` and `cli.py`, and four flags exist only for them. The question:

> **Does any repository you can see work taskrail from more than one clone — and so set
> `[git].claim_remote` or `[git].branch_record_remote`?** And, whatever the answer, **should the
> core `taskrail` skill go on telling every executor to run `taskrail show <ID> --json --fetch`?**

Only the human can answer the first half. This repository is public, taskrail is installed by
repositories that are not, and the publishing constraint in `CLAUDE.md` keeps them out of this
write-up. **Nothing in this document says either key has no consumer.** The strongest claim
available, and the one used throughout, is that no consumer is *visible in this repository*.

### What this task is not

Bound by [T087](T087-decide-whether-the-design-principles-gov.md)'s verdict, now in `CLAUDE.md`:
the design principles are **prospective**, so **nothing here licenses a removal**. An answer of
"nobody sets them" does not delete a key, a flag or a line of `claims.py`. The only change on the
table is one line of skill text, and even that is put as a question.

## What evidence would answer it

The first half of the question is the human's alone. What this spike puts in front of them:

1. A **re-verified state** of the remote half, measured on today's mainline, saying whether
   anything moved since T088.
2. **What the mechanism does when the key is unset**, run rather than reasoned.
3. **What it does when the key is set**, so *is it wanted* is never confused with *does it work*.
4. **Every place the `--fetch` step reaches a consumer**, so the proposal's blast radius is a fact.
5. **Named routes** with a recommendation and a default, so an answer is one word.

## Approach

Re-verify T088 E6 against the mainline; probe the unset path by running the four flags in this
repository; take the enabled path from the test suite rather than from hand-built clones (see
*Limits*); count the `--fetch` step's consumers exactly; then put three numbered questions to the
human at the `decide` gate, which `[autopilot].escalate_gates = ["spike:decide"]` sends to them.

## Limits

- **Time box: this task's two points.** No code, no `DESIGN.md`, no skill, no configuration and no
  other task's row was changed. The kind's `never_edit` is `code` and `specs`; adopting any answer
  is follow-up work.
- **No removal is decided or recommended here**, whatever the answers are.
- **The enabled path rests on the test suite, not on two clones built by hand.** This was decided
  at the `frame` gate, against the lane's own recommendation, and the reason belongs in the record:
  T095 spent its probes proving seven options worked because *nothing else did*, so "unused" could
  have been hiding "broken". Here `tests/test_branch_records_remote.py` is 382 lines of exactly that
  proof — 16 tests over a `mirrored` fixture that clones a bare origin for real — and no amount of
  hand-clone time would change the three answers the human gives. *V7* cites it; *V4* and *V5* are
  the paths this spike ran itself, and they are the ones the proposal turns on.
- **This document cannot name a private consumer.** An answer resting on one is recorded as *the
  human confirmed a consumer exists*, with no repository, client or use named.
- **The `--local-only` flags** on `claim`, `release`, `edit` and `branch` suppress the same two
  mechanisms. They are described for completeness and no question is put about them: they are inert
  when the keys are unset and harmless when they are set.
- **`autopilot status --fetch` is a different flag that shares the name** — it fetches each
  mainline's remote, not branch records (`autopilot/commands.py:563`). It is out of scope, and it is
  named here because a future reader who conflates the two loses an hour to it.

## Evidence

Gathered in this task's worktree, branch `T097-record-whether-any-repository-enables-th`, base
`origin/main` = `df64fe6`. Every command and output below is real; the full list is in
*How to reproduce*.

### V1. Both keys are off, and there is exactly one configuration file to be off in

```
$ git ls-files | grep -i config.toml
.taskrail/config.toml

$ grep -n -A5 '^\[git\]' .taskrail/config.toml
16:[git]
17-worktree = "required"        # "required": one worktree per task; "never": a branch in this checkout
18-worktree_dir = ".worktrees"
19-push_task_branch = true      # `taskrail review --publish` pushes the task branch
20-claim_remote = ""            # e.g. "origin" to also claim across machines

$ grep -rn "branch_record_remote" .taskrail/
(no output — exit 1)

$ sed -n '/^def default_config/,/^DEFAULT_TODO/p' src/taskrail/install.py | grep "claim_remote\|branch_record_remote"
claim_remote = ""            # e.g. "origin" to also claim across machines
```

So `claim_remote` is present and empty in both the only config file and the seed `taskrail init`
writes; `branch_record_remote` is in **neither**. It is documented — `DESIGN.md:161` carries
`branch_record_remote = ""` in §4's example — so a consumer can discover it; nothing here sets it.

And the clone agrees with the config:

```
$ git for-each-ref 'refs/taskrail/**' --format='%(refname)'
(no output)
```

**Not one `refs/taskrail/*` ref exists in this clone**, neither a claim nor a branch record. Local
claims live in `$(git rev-parse --git-common-dir)/taskrail/`, never in refs (§6.4), so the ref
namespace is empty exactly because both remote halves are off.

### V2. T088 E6's call-site lists re-verify, line for line — nothing moved

E6 lists the guarded sites individually, which makes it checkable rather than merely citable:

```
$ git grep -n "claim_remote" -- src/taskrail ':!src/taskrail/config.py'
claims.py:117,131,144,149,150,151,158,210,231   ids.py:111,112   cli.py:347,348,355   install.py:194

$ git grep -n "branch_record_remote" -- src/taskrail ':!src/taskrail/config.py'
branches.py:7,136,138,162,167   cli.py:67,71,77,78,1468,1476,1481
```

**Identical to E6's, line number for line number.** The task asked whether the count had moved
since T088; it has not. (T095's lane found two of T088's *prose* claims over-stated when it
re-checked them. Its call-site tables, checked here, hold.)

The test side matches too: `claim_remote` appears three times under `tests/` and
`branch_record_remote` four, but the counts understate the coverage, because both are set through a
module constant or a fixture rather than per test — see *V7*.

### V3. The four flags, and a fifth that only shares a name

```
$ git grep -n -- '"--fetch"\|"--remote"' src/taskrail/cli.py src/taskrail/autopilot
cli.py:1468: listing.add_argument("--fetch", …, help="first fetch branch records mirrored to [git].branch_record_remote")
cli.py:1476: show.add_argument("--fetch",    …, help="first fetch branch records mirrored to [git].branch_record_remote")
cli.py:1481: nxt.add_argument("--fetch",     …, help="first fetch branch records mirrored to [git].branch_record_remote")
cli.py:1503: listing_claims.add_argument("--remote", …, help="also list claims made from other clones")
autopilot/commands.py:563: status.add_argument("--fetch", …, help="fetch each mainline's remote first")
```

The row's four are correct. **`autopilot status --fetch` is a fifth flag with the same spelling and
a different meaning**, and it is not part of this mechanism.

### V4. With `branch_record_remote` unset, `--fetch` costs nothing — measured, not assumed

The guard:

```
$ sed -n '64,69p' src/taskrail/cli.py
def _fetch_records(project: Project) -> None:
    """Bring mirrored branch records into this clone before any branch is resolved; a failure only warns (§6.4)."""
    config = project.config
    if not config.branch_record_remote:
        return
```

Run on all three commands that take the flag:

```
$ taskrail show T097 --json > show-plain.json          ; taskrail show T097 --json --fetch > show-fetch.json
$ diff show-plain.json show-fetch.json ; echo "exit=$?"
exit=0
$ taskrail list --json | diff - <(taskrail list --json --fetch) ; echo "exit=$?"
exit=0
$ taskrail next --json | diff - <(taskrail next --json --fetch) ; echo "exit=$?"
exit=0
```

All three are **byte-identical**, all exit 0, and all three `--fetch` runs printed **nothing on
stderr** — no warning, no note that the flag did nothing.

That it never touches the network is measurable, because this repository's `origin` is a real
remote over SSH (`git@github.com:…`):

```
$ time taskrail show T097 --json --fetch > /dev/null
real  0m0.224s          # the whole command, Python startup included

$ time git fetch origin > /dev/null
real  0m1.561s          # one real fetch of the same origin
```

**0.224s against 1.561s.** The flag does not reach the network, and `DESIGN.md:588` already says so
in as many words: *"in `show`, `list` and `next` only with `--fetch`, which does nothing while the
setting is off."*

So the cost the row hoped to remove by dropping `--fetch` is **zero, measured**: no time, no
network, no output, no warning. What remains of the case for dropping it is that it is a word an
executor reads and cannot act on — a documentation cost, not a runtime one.

### V5. `claims --remote` with `claim_remote` empty is a refusal, not a no-op

This is the asymmetry the task asked about, and the two flags behave oppositely:

```
$ taskrail claims --remote ; echo "exit=$?"
taskrail: [git].claim_remote is not configured        (on stderr)
exit=2

$ taskrail claims ; echo "exit=$?"
T095   abigail@archlinux        T095-ask-whether-the-options-no-visible-repos live
T097   abigail@archlinux        T097-record-whether-any-repository-enables-th live
exit=0
```

`--remote` **prints nothing at all** — not even the local claims it would have listed without the
flag — and exits 2. That is defensible (you asked for remote claims and there is no remote), and it
is not proposed for change here. It matters for one reason: **a user who passes `--remote` by
mistake learns the key exists; a user who passes `--fetch` learns nothing.** That contrast is the
strongest argument for route C below.

### V6. The skill's `--fetch` is not redundant with what `claim` already does

Nine commands fetch mirrored records:

```
$ git grep -n "_fetch_records" -- src/taskrail
cli.py:119 cmd_list    cli.py:147 cmd_show   cli.py:204 cmd_next      # only with --fetch
cli.py:233 cmd_claim   cli.py:474 cmd_new    cli.py:648 cmd_workspace
cli.py:978 cmd_edit    cli.py:1038 cmd_branch
cli.py:1195 cmd_review   # before resolving the branch, which another clone may have renamed
```

**Six of the nine fetch unconditionally** (suppressed only by `--local-only` or `--no-fetch`); only
`list`, `show` and `next` need the flag, because those three are the commands documented never to
need the network (`DESIGN.md:808`).

It would be easy to conclude that the skill's `show --fetch` is therefore redundant — `claim`
fetches anyway. **It is not, and the order is why.** The core skill runs `show --json --fetch` in
step 3 to read `base.onto`, *then* creates the branch and worktree from it; `claim` is step 4,
after the worktree exists. A record fetched at `claim` time arrives after the branch was already
cut from the wrong base.

### V7. With the key set, that step is load-bearing — from the suite

```
$ uv run pytest tests/test_branch_records_remote.py -q
................                                                         [100%]
16 passed in 5.33s

$ uv run pytest tests/test_claims.py -q
............................                                             [100%]
28 passed in 3.86s
```

The fixture is not a mock:

```
$ sed -n '94,97p' tests/test_branch_records_remote.py
@pytest.fixture
def mirrored(git_repo, tmp_path_factory):
    """Clone A of a bare origin, with branch records mirrored to it; `clone()` makes more clones."""
    return setup_origin(git_repo, tmp_path_factory, MIRRORED)
```

`MIRRORED` is `BASE_CONFIG + '\n[git]\nbranch_record_remote = "origin"\n'`, and `clone()` runs a
real `git clone` of a real bare origin. Two of the sixteen tests are this task's question exactly:

```
$ sed -n '254,268p' tests/test_branch_records_remote.py
def test_show_fetch_resolves_a_branch_renamed_in_another_clone(mirrored, capsys):
    …
    plain = data(other, "show", "T001", capsys=capsys)
    assert (plain["branch"], plain["branch_source"], plain["state"]) == (T001, "template", "pending")
    assert refs(other, "refs/taskrail") == ""

    fetched = data(other, "show", "T001", "--fetch", capsys=capsys)
    assert (fetched["branch"], fetched["branch_source"], fetched["state"]) == (NAME, "recorded", "done-branch")
    base = data(other, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["dependency"]) == (f"origin/{NAME}", "T001")
```

**In a mirrored repository, the same `show` without `--fetch` reports a task that is finished on a
renamed branch as `pending`, with a `template` branch name** — and the dependent task T002 only
then resolves `base.onto` to `origin/<renamed>`. The second:

```
$ sed -n '270,280p' tests/test_branch_records_remote.py
def test_list_and_next_fetch_agree(mirrored, capsys):
    …
    unfetched = [t["id"] for t in data(repo.clone(), "next", capsys=capsys)]
    assert "T002" not in unfetched
    eligible = [t["id"] for t in data(repo.clone(), "next", "--fetch", capsys=capsys)]
    assert "T002" in eligible and "T001" not in eligible
```

**Without `--fetch`, a dependent task is not eligible at all** — `next` does not offer it.

So for a repository with the key on, an executor told to drop `--fetch` would branch from a stale
base and could be told its own dependency is unfinished. That is the measured cost of route B, and
it is not small.

### V8. The blast radius of dropping `--fetch` is two lines, not one

```
$ git grep -n -- "--fetch" -- src/taskrail/skills src/taskrail/integrations README.md CLAUDE.md
src/taskrail/skills/taskrail/SKILL.md:64:   … then `taskrail show <ID> --json --fetch` —
README.md:50:taskrail show T012 --json --fetch      # …after fetching branch names other clones recorded
```

**The task's row named only the skill.** `README.md:50` teaches the same command to a human reader,
so route B touches two files (three counting `.claude/skills/taskrail/SKILL.md`, the installed copy
that `taskrail upgrade` regenerates — never edited by hand, per `CLAUDE.md`).

`DESIGN.md` needs no change under any route: §6.4 (line 588) and §7's table already state the
condition correctly.

### V9. The skill already carries the condition — in a subordinate clause

```
$ sed -n '64,66p' src/taskrail/skills/taskrail/SKILL.md
   the mainline's own remote that `show` reported, then `taskrail show <ID> --json --fetch` —
   which also brings in branch names other clones recorded, when the repository mirrors them: its
   `base.onto` is the ref to branch from — …
```

**"when the repository mirrors them"** is already there. The skill does not claim the fetch always
does something. That weakens route B — the text is not misleading today, only easy to read past,
since the condition sits mid-sentence between two em dashes in the middle of the longest step in
the skill — and it is what makes route C a one-line clarification rather than a new rule.

## Options considered

Questions 1 and 2 have no options: they are facts the human holds, and either answer is recorded.
Question 3 is the only one with a change behind it.

| Route | What it means | Cost | Against it |
|---|---|---|---|
| **A. Keep the step exactly as it stands** | No change to any file. | Zero. | The question recurs at the next audit, because nothing in the record says it was asked and settled. The clause of *V9* stays easy to read past. |
| **B. Drop `--fetch` from the step** (the row's proposal) | One word out of `SKILL.md:64`, and `README.md:50` with it (*V8*). | Two lines, reversible. | **Recommended against.** It saves nothing measurable (*V4*: 0.224s, no network, no output) and costs a mirrored consumer a stale `base.onto` and a dependency that drops out of `next` (*V7*). It also removes the executor's only pre-workspace fetch (*V6*). |
| **C. Keep the flag; make the condition explicit** | Rewrite the clause so it says plainly that the fetch does nothing unless the repository sets `[git].branch_record_remote`, and matters when it does. | One line in `SKILL.md`, optionally one comment in `README.md`. No behaviour change anywhere. | It spends a task on wording. |
| D. Make `--fetch` warn when the key is unset | `show --fetch` would print a note, as `claims --remote` effectively does (*V5*). | Code, a test, and noise in three commands' output for every installation with the key off. | Not recommended and not offered as a route: it changes the tool to fix a sentence in a skill, and `DESIGN.md:588` already documents the behaviour. Recorded here so the option is visibly considered, not overlooked. |

**Route B is only available if question 2 is answered B.** If any repository sets
`branch_record_remote`, *V7* settles it: the step stays.

## Recommendation

**Put the three questions below to the human and open no task until they answer.** The defaults:

| # | Question | Recommended route | If skipped |
|---|---|---|---|
| 1 | Does any repository you can see set `[git].claim_remote`? | record the answer either way | B |
| 2 | Does any repository you can see set `[git].branch_record_remote`? | record the answer either way | B |
| 3 | What happens to the skill's `--fetch` step? | **C — keep it, say the condition plainly** | **C** |

**Route C is recommended, and route B — the proposal the task's own row named — is recommended
against.** The row assumed the fetch was dead weight in every visible installation and therefore
worth dropping. The first half is true and the second does not follow: *V4* measures the weight at
zero, and *V7* measures what it carries when the key is on. A change that saves nothing and can
silently mislead an executor in someone else's repository is the wrong side of the trade, and
T087's prospective principles do not ask for it.

C is recommended over A because the cost of A is not zero either: the question comes back. One
sentence in the skill records the answer where the next reader of that step will find it, changes
no behaviour, ships to every consumer harmlessly, and is reversible in one line.

### The questionnaire

*Answer with the number and a letter — for example `1 B, 2 B, 3 C`. Anything you skip takes the
default on its line. **Nothing is removed by any answer**: no route deletes a key, a flag or a line
of `claims.py`, and route B on question 3 opens a task that proposes one word be dropped from a
skill, judged on its own merits when it is worked.*

**1. `[git].claim_remote`** — off by default; set to a remote name (`"origin"`) it also pushes each
claim as `refs/taskrail/claims/<ID>`, so two clones cannot claim the same task. `DESIGN.md` §6.2
gives the reason it is off: it needs network, permission to push, and a server that accepts refs
outside `refs/heads` and `refs/tags`.
Visible here: written as `""` in the only `.taskrail/config.toml` in the repository and in the seed
`taskrail init` writes; not one `refs/taskrail/*` ref exists in this clone. Its one flag,
`claims --remote`, exits 2 with `taskrail: [git].claim_remote is not configured`.
**Q: does any repository you can see set `claim_remote` — that is, do two people or two machines
ever claim tasks from the same backlog?**
→ **A**: yes. Recorded here as *the human confirmed a consumer exists*, with nothing named. That
settles the key; no task, and the next audit does not re-ask it.
→ **B (default)**: none you can see either. Also recorded — and still **no removal**: the key stays,
the code stays, and the record simply says the answer was sought and not found.

**2. `[git].branch_record_remote`** — off by default and independent of `claim_remote`, though they
usually name the same remote. Set, it mirrors each task's branch record as
`refs/taskrail/branches/<ID>`, so a branch renamed in one clone resolves in another.
Visible here: absent from the only config file *and* from the seed — it is documented only, in
`DESIGN.md:161`'s example, as `branch_record_remote = ""`.
**Q: does any repository you can see set `branch_record_remote` — that is, does anyone work the same
backlog from more than one clone?**
→ **A**: yes. Recorded as above, and it **settles question 3 at route A or C**: route B is off the
table, because without the fetch such a repository's executors read a stale base (see question 3).
→ **B (default)**: none you can see either. Recorded; nothing is removed.

**3. The core skill's `--fetch` step.** Step 3 of the `taskrail` skill tells every executor, in
every consuming repository, to run `taskrail show <ID> --json --fetch` before it creates the task's
branch. Here is the sentence as it stands today, so you can judge the text and not a paraphrase of
it:

> *"Under `"task"`: run `git fetch <base.remote>` first, with the mainline's own remote that `show`
> reported, then `taskrail show <ID> --json --fetch` — which also brings in branch names other
> clones recorded, when the repository mirrors them: its `base.onto` is the ref to branch from …"*

What was measured: with the key off the flag is **free and silent** — identical output, exit 0, no
message, 0.224s against 1.561s for a real fetch of the same origin, because the code returns before
touching git. With the key **on** it is load-bearing: the suite shows `show` without it reporting a
finished task as `pending` on a `template` branch name, and `next` without it dropping a dependent
task from the eligible list altogether.
**Q: keep the step as it is, drop the flag, or keep it and say the condition plainly?**
→ **A**: keep it exactly as it stands. No task. Costs nothing now; the question returns at the next
audit with nothing in the skill to answer it.
→ **B**: open a task proposing `--fetch` be dropped from that step — the proposal this task's row
named. **Recommended against**, on the two measurements above, and unavailable if you answered A to
question 2. Note its blast radius is two lines, not one: `README.md:50` teaches the same command,
which the row missed.
→ **C (recommended, default)**: a small `chore` rewriting that clause so the skill says plainly that
the fetch does nothing unless the repository sets `[git].branch_record_remote`, and that it is what
makes a branch renamed in another clone resolvable when it does. One line, no behaviour change,
reversible, and it puts the answer where the next reader of that step will find it.

**One thing that is not a question.** `claims --remote` refuses with exit 2 and prints nothing —
not even the local claims — when the key is empty, while `--fetch` says nothing at all. Both are
defensible and neither is proposed for change. It is recorded because the contrast is the reason
route C exists: the flag that fails loudly teaches a user the key exists, and the silent one cannot.

## What would change the decision

- **The human naming a private consumer** for either key. That settles it, and it is the single
  thing this spike exists to obtain. An answer of A to question 2 removes route B outright.
- **A second visible consumer repository.** Every "no visible setter" here is a statement about one
  `.taskrail/config.toml` (*V1*). A second one would re-class both keys immediately.
- **`taskrail init` seeding `branch_record_remote`.** It seeds `claim_remote = ""` and not the
  other (*V1*), so a seeded empty key and an absent one are being read as the same evidence. If the
  seed grew, question 2's "absent" would become "present and off", which is weaker evidence.
- **The core skill's step 3 being restructured** so the workspace is created after the claim. The
  whole of *V6* — why the flag is not redundant — rests on `show` running before the branch is cut.
- **A repository adopting `task_branch = "current"`.** `DESIGN.md:554` says `branch_record_remote`
  is then accepted but pushes nothing, because no record is written. In such a repository the
  `--fetch` step is skipped anyway, and question 3 does not arise.
- **T094 landing.** It makes an unknown configuration key loud. It changes nothing here, because no
  route touches a key — but it is the precondition any *future* proposal about these two keys would
  need, and it is worth knowing that it is not this task's dependency.
- **A measured harm.** Nothing in this report measures a cost of the remote half existing: no bug
  traced to it, no consumer confused by it, 0.224s of runtime. If such a case appears, the balance
  of question 3 moves.

## How to reproduce

From a checkout at `df64fe6` or later, in the repository root. Nothing below writes anything.

```bash
git ls-files | grep -i config.toml                       # V1: exactly one config file
grep -n -A5 '^\[git\]' .taskrail/config.toml             # V1: claim_remote = ""
grep -rn "branch_record_remote" .taskrail/               # V1: no output, exit 1
sed -n '/^def default_config/,/^DEFAULT_TODO/p' src/taskrail/install.py | grep claim_remote
git for-each-ref 'refs/taskrail/**'                      # V1: no output — no claim, no record

git grep -n "claim_remote" -- src/taskrail ':!src/taskrail/config.py'          # V2
git grep -n "branch_record_remote" -- src/taskrail ':!src/taskrail/config.py'  # V2
git grep -n -- '"--fetch"' src/taskrail/cli.py src/taskrail/autopilot          # V3: 3 + 1 unrelated

.taskrail/bin/taskrail show T097 --json > /tmp/a.json                          # V4
.taskrail/bin/taskrail show T097 --json --fetch > /tmp/b.json
diff /tmp/a.json /tmp/b.json                                                   # V4: identical
time .taskrail/bin/taskrail show T097 --json --fetch > /dev/null               # V4: ~0.2s
time git fetch origin                                                          # V4: ~1.5s
sed -n '64,69p' src/taskrail/cli.py                                            # V4: the guard
sed -n '588p' DESIGN.md                                                        # V4: documented

.taskrail/bin/taskrail claims --remote ; echo "exit=$?"                        # V5: exit 2
.taskrail/bin/taskrail claims                                                  # V5: the local claims

git grep -n "_fetch_records" -- src/taskrail                                   # V6: 9 sites
sed -n '58,70p' src/taskrail/skills/taskrail/SKILL.md                          # V6, V9: the step

uv run pytest tests/test_branch_records_remote.py -q                           # V7: 16 passed
uv run pytest tests/test_claims.py -q                                          # V7: 28 passed
sed -n '94,97p;254,280p' tests/test_branch_records_remote.py                   # V7: the two tests

git grep -n -- "--fetch" -- src/taskrail/skills src/taskrail/integrations README.md CLAUDE.md   # V8
```

## Outcome

The `decide` gate of this spike is escalated to the human by
`[autopilot].escalate_gates = ["spike:decide"]`. The answers are recorded here and in
[`docs/autopilot/decisions/T097-record-whether-any-repository-enables-th.md`](../autopilot/decisions/T097-record-whether-any-repository-enables-th.md)
when they arrive.

At the `frame` gate the orchestrator approved the question and the three-question format, added
route C to question 3, and **declined** the lane's proposal to build throwaway clones for the
enabled path, directing it to the test suite instead — the reason is in *Limits*, and *V7* is the
result. Both of the lane's corrections to the task's row were accepted into the questionnaire:
`README.md:50` carries the same `--fetch` (so route B's blast radius is two lines, not one), and
`autopilot status --fetch` is an unrelated flag sharing the name.
