# T088 — Measure the CLI and configuration surface against YAGNI and report what has no consumer

**Verdict** — The surface is large and thinly consumed, but **the two halves of it fail YAGNI in
opposite ways and must not be treated alike**. Of **46 configuration names**, **9** carry a
non-default value in the only repository whose config is visible; the other 37 are absent from it
or present only repeating their own default. Of **71 long flags**, **39** are named in the shipped
skills; **3** (`epic add --id`, `epic add --file` / `epic split --file`, `next --limit`) appear
nowhere in this repository outside the parser that defines them — not in a skill, a test, a
document or a past write-up. But **the evidence is not symmetric**: a configuration key must be
written in a file to do anything, so its absence from every config file here is real evidence,
while a command or flag is typed by a human who leaves no file behind, so absence there is weak.
The one change this measurement argues for on its own is not a removal: **`taskrail validate`
should warn about a key it does not know**, because today removing any configuration key would be
a *silent* behaviour change for a repository that set it (measured below), while removing a flag
or a command is a loud one. Nothing here licenses a removal; each finding is a task, judged on its
own merits when someone proposes it.

This spike changed no code, no configuration, no skill, no `DESIGN.md` and no task row.

### How to read this report

**A tool built by one repository for many will always look over-supplied from inside that one
repository, and the only measurement that repository can make is of its own use.** Every count
below is a fact about this checkout, not about taskrail's users. That is why the tables classify
options by *where a consumer is visible* rather than by whether one exists, why the strongest
phrase in the document is "no consumer visible in this repository", and why every recommendation
is a question for someone who can see further.

The second thing to carry through the tables is the **asymmetry of E2**: a configuration key must
be written in a file to act, so its absence from every config file here is evidence; a command or
a flag is typed by a human who leaves no file behind, so absence there is not. **This inventory is
not a removal list**, and the two facts above are what stop it becoming one.

## Question

taskrail's command-line and configuration surface is large for a tool with one visible consumer.
The task asks: **for each option in that surface, who consumes it, and what would removing it or
fixing it at a default cost a repository that installed 0.3.0?**

### The task row's figures are wrong and are not used here

The row says "18 subcommands, about 66 distinct flags and 19 first-level config keys". **Those
figures were superseded by [T087](T087-decide-whether-the-design-principles-gov.md), which
re-measured the surface from the live `argparse` tree, and they are corrected in the row itself by
T092** (`chore`, open). T092 is not this task's work and this task does not edit the row. The
measured surface, reproduced independently here, is in *E1* and *E5*: 27 top-level commands, 42
commands at all levels, 71 long flags of taskrail's own, and 9 first-level names in
`.taskrail/config.toml` holding 46 settable names in total.

### What this task is not

Bound by T087's verdict, accepted by the human on 2026-09-18:

- **The design principles are prospective.** **This verdict licenses no removal.** Each finding
  below is a candidate task; each such task is judged on its own merits when it is proposed.
- **"No consumer visible in this repository" is the strongest claim available.** This repository
  is public and the publishing constraint in `CLAUDE.md` keeps private consumers out of the
  write-up. Nothing below says an option has no consumer. Where the investigation found nothing,
  it says so in those words, and every recommendation is a recommendation to *ask*, never to
  remove.

## Evidence

All commands were run in this task's worktree, on branch
`T088-measure-the-cli-and-configuration-surfac`, base `origin/main` = 4a956c4 (the branch was
rebased onto the mainline after T087 was squash-merged). The tree was healthy when it was
measured: `uv run pytest -q` → `1183 passed in 168.18s`.

Three throwaway scripts produced the tables. They live in the session scratchpad, outside the
repository, and are reproduced verbatim under *How to reproduce*.

### E1. The command and flag counts, from the live parser

```
$ uv run python <scratchpad>/surface.py
commands (all levels): 42
top-level commands: 27
distinct long flags (incl --help): 72
distinct long flags (excl --help): 71
```

**How the flags are counted here:** every distinct long option string (`--…`) on the root parser
and on all 42 subparsers, de-duplicated across commands. `--help` is argparse's, not taskrail's, so
**71** is taskrail's own figure and 72 is the same count with `--help` kept. T087 reported 72 by
this method and 70 by another; a reader who recounts and gets 70 or 72 has reproduced the same
tree, not a different one. The command counts, 27 and 42, are exact and have now been produced by
three independent runs.

The 27 top-level commands: `autopilot branch checks claim claims discard done edit epic import
init integration kind list merge-driver new next release reopen reserve-id review self show
unreserve-id upgrade validate workspace`.

### E2. Removing a configuration key is silent; removing a flag or a command is loud

This is the single most important measurement in the report, because it decides what "what would
removing it cost" means for each half of the surface.

A copy of this repository's own config, with two keys that taskrail does not define added inside
existing tables:

```
$ cp .taskrail/config.toml $D/.taskrail/config.toml    # + nonsense_top_key, + [git].nonsense_git_key
$ uv run taskrail --root $D validate
history: not checked (not a git repository)
81 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
$ echo $?
0
```

**`load_config` ignores every key it does not know, and `validate` reports zero errors and zero
warnings.** So if taskrail removed a key in 0.4.0, a repository that set it would keep the line in
its file, keep a green `validate`, and quietly get the default behaviour instead of the one it
configured. There is no error, no warning and no migration signal.

The CLI behaves the opposite way:

```
$ .taskrail/bin/taskrail list --nonexistent-flag
taskrail: error: unrecognized arguments: --nonexistent-flag        (exit 2)

$ .taskrail/bin/taskrail nonexistent
taskrail: error: argument command: invalid choice: 'nonexistent' (choose from validate, list,
show, next, claim, release, claims, reserve-id, unreserve-id, init, upgrade, integration, self,
new, workspace, done, discard, reopen, edit, branch, review, checks, epic, kind, autopilot,
import, merge-driver)
```

A removed flag or command fails immediately, by name, at the call site.

One mitigation applies to both: the version pin. `src/taskrail/install.py:220` writes a wrapper
that runs "the taskrail version pinned in `.taskrail/config.toml`", so a repository that installed
0.3.0 keeps running v0.3.0 until the pin changes. The pin changes when it runs `taskrail upgrade`
(`install.py:482`: `.taskrail/config.toml (version pin → …)`). **The moment of cost is therefore
the upgrade** — which is exactly when a warning would be read and a CHANGELOG entry consulted.

### E3. The evidence is not symmetric between the two halves

A configuration key has to be written in a `.taskrail/config.toml` to have any effect. There is
exactly one such file visible in this repository, and this task read all of it. So "no visible
setter" is a fact about a file, and it is strong.

A command or a flag is typed by a human at a terminal, or by an agent following a skill. The skill
leaves a trace; the human leaves none. `taskrail list` could be the most-used command in the tool
and still appear in no file. **Every class below marked C3/C4/C5 for a command or a flag is
therefore weaker evidence than the same class for a configuration key**, and the recommendations
treat it that way.

The classification method also has a measured blind spot. Commands were first counted by grepping
for the string `taskrail <command>`; that missed `list`, `claims` and `kind list`, which the core
skill names without the prefix:

```
$ grep -n "Useful commands" -A1 src/taskrail/skills/taskrail/SKILL.md
36:Useful commands: `next`, `list [--epic E01] [--state pending]`, `show <ID>`, `claims`,
37-`kind list`.
```

Those three are corrected to C1 in the table. Counts for a key whose name is preceded by `\n`
inside a Python string (`'\n[git]\nclaim_remote = "origin"'`) are likewise undercounted by
`grep -w`, so the tables use unanchored counts.

### E4. What the only visible installation actually turned on

```
$ cat .taskrail/installed.json
{ "version": "v0.3.0", "integrations": ["claude"], "extras": {}, "files": { … } }

$ git config merge.taskrail.driver
(no output)

$ ls /thezone/…/taskrail/.git/hooks/ | grep -v sample
(no output)

$ ls .github/workflows/
ls: cannot access '.github/workflows/': No such file or directory
```

The one installation visible took **no extras**: `"extras": {}` means `init` was run without
`--github-workflow`, `--pre-commit` and `--merge-driver`, and one integration of the two shipped
was chosen. So:

- **`taskrail merge-driver` (706 lines in `src/taskrail/mergedriver.py`, 905 lines of tests) is
  installed in no repository visible here.** Its four label flags — `--marker-size`,
  `--path`, `--base-label`, `--current-label`, `--other-label` — are consumed by a git config
  string (`mergedriver.py:36`) that this repository does not have. The `taskrail` skill's rebase
  step already accounts for this ("When the repository's merge driver is installed
  (`git config merge.taskrail.driver` prints a command)…"), so the tool is correct; it is simply
  unused here.
- `init --github-workflow` and `init --pre-commit` have no visible consumer either.
- The second integration, `opencode`, ships (`integration list` returns `claude` and `opencode`)
  and is installed by nobody visible.

### E5. The configuration surface, key by key

`.taskrail/config.toml` in this repository was read in full; `install.py`'s `default_config` is
what `taskrail init` seeds; `DESIGN.md` §4 (lines 109-205) is the documented example. Columns:
**SET** — written in this repository's config; **SEED** — written by `init`; **§4** — in the
DESIGN.md example; **TEST** — appears under `tests/`; **CLASS** — the consumer ladder from the
`frame` stage (C1 used here, C2 seeded, C3 documented only, C4 test only, C5 nothing but the
implementation).

| Key | SET | SEED | §4 | TEST | Class | Note |
|---|---|---|---|---|---|---|
| `version` | ✓ | ✓ | ✓ | ✓ | **C1** | `local:.` here; a pin elsewhere |
| `[[backlog]].name` | ✓ | ✓ | ✓ | ✓ | **C1** | required |
| `[[backlog]].prefix` | ✓ | ✓ | ✓ | ✓ | **C1** | required |
| `[[backlog]].file` | ✓ | ✓ | ✓ | ✓ | **C1** | required |
| `[[backlog]].mainline` | ✓ | ✓ | ✓ | ✓ | **C1** | set to its own default `main` |
| `[[backlog]].artifacts` | ✓ | ✓ | ✓ | ✓ | **C1** | set to its own default `docs` |
| `[[backlog]].may_depend_on` | – | – | ✓ | 2 | **C3** | only one backlog is visible |
| `[[backlog]].epic_prefix` | – | – | – | **0** | **C5** | **absent from DESIGN.md entirely** |
| `[[backlog]].id_digits` | – | – | – | 1 | **C4** | not in §4; one `test_import.py` case |
| `[columns].custom` | `[]` | `[]` | ✓ | ✓ | **C1** | present, set to "off" |
| `[columns].aliases` | – | comment | ✓ | ✓ | **C4** | 252-line `test_column_aliases.py` |
| `[points].scale` | ✓ | ✓ | ✓ | ✓ | **C1** | a real choice (default is empty) |
| `[git].push_task_branch` | ✓ | ✓ | ✓ | ✓ | **C1** | set to its own default `true` |
| `[git].commit` | – | – | ✓ | ✓ | **C3/C4** | 269-line `test_commit_policy.py` |
| `[git].claim_remote` | `""` | `""` | ✓ | 3 | **C1 as empty** | **no non-empty setter visible** |
| `[git].branch_record_remote` | – | – | ✓ | ✓ | **C3/C4** | 382-line dedicated test file |
| `[git].claim_grace_minutes` | – | – | ✓ | ✓ | **C3** | default relied on; named in the autopilot skill |
| `[git].worktree` | ✓ | ✓ | ✓ | ✓ | **C1** | set to its own default |
| `[git].worktree_dir` | ✓ | ✓ | ✓ | ✓ | **C1** | set to its own default |
| `[git].task_branch` | – | – | ✓ | ✓ | **C3/C4** | the whole §13 workflow; see below |
| `[review].remote` | ✓ | ✓ | ✓ | ✓ | **C1** | set to its own default |
| `[review].fetch` | ✓ | ✓ | ✓ | ✓ | **C1** | set to its own default |
| `[review].rebase` | ✓ | ✓ | ✓ | ✓ | **C1** | set to its own default |
| `[review].provider` | – | ✓ | ✓ | 4 | **C2** | seeded as `auto` |
| `[review].web_url` | – | ✓ | ✓ | 3 | **C2** | seeded empty; for self-hosted hosts |
| `[review].url_template` | – | ✓ | ✓ | 1 | **C2** | seeded empty |
| `[review].scope` | – | ✓ | ✓ | ✓ | **C2** | the skills pass `--scope` per task instead |
| `[kinds].allowed` | – | – | ✓ | ✓ | **C3/C4** | 187-line `test_allowed_kinds.py` |
| `[checks].<name>` | ✓ | comment | ✓ | ✓ | **C1** | `test = "uv run pytest -q"` |
| `[autopilot].enabled` | ✓ | – | ✓ | ✓ | **C1** | not seeded: opt-in by hand |
| `[autopilot].max_lanes` | ✓ | – | ✓ | ✓ | **C1** | set to its own default `3` |
| `[autopilot].kinds` | – | – | ✓ | 2 | **C4** | |
| `[autopilot].governing` | `[]` | – | ✓ | ✓ | **C1 as empty** | set to "off" with a comment saying why |
| `[autopilot].read_first` | ✓ | – | ✓ | ✓ | **C1** | a real choice |
| `[autopilot].escalate_gates` | ✓ | – | ✓ | ✓ | **C1** | a real choice; this gate is one of them |
| `[autopilot].decisions` | – | – | ✓ | ✓ | **C3** | default template used |
| `[autopilot].decisions_index` | – | – | ✓ | ✓ | **C3** | default template used |
| `[autopilot].silent_minutes` | – | – | ✓ | ✓ | **C3** | default used |
| `[autopilot].handoff` | – | – | ✓ | ✓ | **C3** | **`HANDOFF_MODES = ("sequential",)`: one legal value** |
| `[autopilot].notify` | – | – | ✓ | ✓ | **C4** | 532-line `test_autopilot_notify.py` |
| `[autopilot].notify_on` | – | – | ✓ | ✓ | **C4** | |
| `[[autopilot.group]].name` | – | – | ✓ | ✓ | **C4** | |
| `[[autopilot.group]].limit` | – | – | ✓ | ✓ | **C4** | |
| `[[autopilot.group]].column` / `.match` | – | – | ✓ | ✓ | **C4** | column predicate, §5.4 |
| `[[autopilot.resource]].name` | – | – | ✓ | ✓ | **C4** | |
| `[[autopilot.resource]].values` | – | – | ✓ | ✓ | **C4** | |

**46 settable names.** Of them, **9 carry a value different from the built-in default** in the only
visible config: `version`, the three required `[[backlog]]` keys, `[points].scale`,
`[checks].test`, `[autopilot].enabled`, `[autopilot].read_first` and
`[autopilot].escalate_gates`. Thirteen more are written in that file repeating their own default
(`mainline`, `artifacts`, `worktree`, `worktree_dir`, `push_task_branch`, `max_lanes`, the three
`[review]` keys) or set to "off" (`claim_remote = ""`, `columns.custom = []`, `governing = []`).
The remaining 24 appear in no config file in this repository.

### E6. The four weakest configuration findings, in detail

**`[[backlog]].epic_prefix` — the one C5 in the surface.** It is parsed and validated with two
dedicated error messages, used in three places, and appears in no configuration file, no test and
**no line of `DESIGN.md`**:

```
$ grep -n "epic_prefix" DESIGN.md
(no output)
$ git grep -n "epic_prefix" -- src/taskrail
src/taskrail/config.py:29,174,175,176,177,178,194     # default, parse, two validations, construct
src/taskrail/importer.py:291
src/taskrail/cli.py:1327
src/taskrail/backlog.py:200
$ git grep -c "epic_prefix" -- tests
(no output)
```

A consumer cannot discover it by reading the documentation, and nothing here proves it works.
Note the asymmetry of E2 cuts *against* keeping it quietly: a repository that found it in the
source and set `epic_prefix = "EP"` would, after a removal, silently get `E` back.

**`[git].claim_remote` and `[git].branch_record_remote` — the remote half of §6.** `claim_remote`
is written as `""` in both this repository's config and the seed; `branch_record_remote` is written
nowhere at all. Between them they guard:

```
$ git grep -n "claim_remote" -- src/taskrail ':!src/taskrail/config.py'
claims.py:117,131,144,149,150,151,158,210,231   ids.py:111,112   cli.py:347,348,355   install.py:194
$ git grep -n "branch_record_remote" -- src/taskrail ':!src/taskrail/config.py'
branches.py:7,136,138,162,167   cli.py:67,71,77,78,1468,1476,1481
```

and four CLI flags exist only for them: `claims --remote` (`cli.py:347`, which prints
`taskrail: [git].claim_remote is not configured` when it is unset) and `--fetch` on `list`, `show`
and `next`, whose help text is literally "first fetch branch records mirrored to
`[git].branch_record_remote`" (`cli.py:1468,1476,1481`). `--local-only` on `claim`, `release`,
`edit` and `branch` exists to suppress the same two mechanisms. **A consequence worth stating:**
the `taskrail` skill instructs every executor to run `taskrail show <ID> --json --fetch`, and in
the only repository visible that fetch does nothing, because the key it fetches from is unset.

**`[autopilot].handoff` — an option with one legal value.** `config.py:47` is
`HANDOFF_MODES = ("sequential",)`, §4 documents it as "the only value", and `_autopilot` raises a
configuration error for anything else. It is a setting whose entire range is its default.

**`[autopilot].notify`, `notify_on`, `[[autopilot.group]]`, `[[autopilot.resource]]` — configured
by nobody visible, but with a consumed command surface.** This is the distinction the report exists
to draw. The *keys* have no setter here. The *commands and flags they feed* are named in the
shipped autopilot skill and run in every autopilot run, including this one:

```
$ git grep -n "notify\|--group\|--resource" -- src/taskrail/skills/taskrail-autopilot/SKILL.md
 67: taskrail autopilot lane <ID> --run <R> --group <G>
140: taskrail autopilot notify --event escalation --run <R> --task <ID>
151: taskrail autopilot notify --event lane-failed --run <R> --task <ID>
177: taskrail checks <ID> --resource NAME=VALUE
182: taskrail autopilot notify --event lane-done --run <R> --task <ID>
```

With `[autopilot].notify` empty, that command is a no-op by design (`autopilot/notify.py:76`:
`result["skipped"] = "no command in [autopilot].notify"`). So the orchestrator of this run has been
dutifully sending notifications to nowhere. The mechanism is 116 lines plus a 532-line test file;
resources and groups are about 90 code sites, concentrated in `autopilot/dispatch.py` (26 and 32),
`checks.py` (22) and `config.py` (9 and 12), with `test_autopilot_overlaps.py` (145 lines) and
parts of several other test files.

### E7. The command surface, command by command

**C1** means named in a shipped skill, in `CLAUDE.md`, or proven run here by an artefact it left.

| Command | Consumer found | Class |
|---|---|---|
| `validate` | core skill; `CLAUDE.md` Commands; the CI workflow template | **C1** |
| `list` | core skill, *Useful commands* | **C1** |
| `show` | core skill, step 2 | **C1** |
| `next` | core skill, step 1 | **C1** |
| `claim` | core skill, step 4 | **C1** |
| `release` | `DESIGN.md` §6.1; **no skill names it** | **C3** |
| `claims` | core skill, *Useful commands* | **C1** |
| `reserve-id` | `DESIGN.md` §6.3; no skill, no README | **C3** |
| `unreserve-id` | `DESIGN.md` §6.3; no skill, no README | **C3** |
| `init` | `.taskrail/installed.json` proves it ran here | **C1** |
| `upgrade` | `CLAUDE.md` *Backlog*; the core skill | **C1** |
| `integration` (group) | — | parent |
| `integration list` | `DESIGN.md` §7 only | **C3** |
| `self` (group) | — | parent |
| `self upgrade` | README; the release chores' write-ups | **C1** |
| `new` | core skill, *Creating tasks* | **C1** |
| `workspace` | core skill, step 3 | **C1** |
| `done` | core skill, step 8 | **C1** |
| `discard` | core skill | **C1** |
| `reopen` | core skill, *Reopening a task* | **C1** |
| `edit` | core skill, *Editing tasks* | **C1** |
| `branch` | core skill, step 3 | **C1** |
| `review` | core skill, step 8 | **C1** |
| `checks` | core skill, step 5; every executor skill | **C1** |
| `epic` (group) | — | parent |
| `epic add` | core skill, *Creating tasks* | **C1** |
| `epic split` | core skill, *Creating tasks* | **C1** |
| `kind` (group) | — | parent |
| `kind list` | core skill, *Useful commands* | **C1** |
| `autopilot` (group) | — | parent |
| `autopilot start` / `extend` / `next` / `lane` / `decision` / `approve-governing` / `notify` / `status` / `close` / `merged` | the autopilot skill names all ten | **C1** |
| `import` | `DESIGN.md` §7.3, README; **no skill, never run here** | **C3** |
| `merge-driver` | §7.4 and a git config no visible repository has (E4) | **C3** |

31 of the 37 non-group commands have a consumer visible here. The six that do not — `release`,
`reserve-id`, `unreserve-id`, `integration list`, `import`, `merge-driver` — are all documented,
all tested, and all plausibly typed by a human, which E3 says this method cannot see.

`import` is the largest of them: `src/taskrail/importer.py` is 684 lines with a 608-line test file,
9 of the 71 flags, and a purpose — converting a foreign backlog once — that by construction nobody
runs twice. This repository never ran it: it was extracted with its history, not imported.

**Two commands are documented and do not exist.** `DESIGN.md` §7 offers
`taskrail kind list / kind add <dir>` and `taskrail list [--epic E01] [--eligible] [--fetch]`:

```
$ .taskrail/bin/taskrail kind add examples
taskrail kind: error: argument kind_command: invalid choice: 'add' (choose from list)

$ .taskrail/bin/taskrail list --help
usage: taskrail list [-h] [--json] [--fetch] [--backlog BACKLOG] [--epic EPIC]
                     [--state {pending,claimed,blocked,done-branch,…}] [--kind KIND] [--allow-invalid]
```

There is no `kind add` and no `--eligible`; `--state` replaced the latter. This matters for the
YAGNI question in the other direction: `examples/spec-kit/` ships as a repository-local kind, and
the only documented way to install it does not exist. (§5.2 shows the real way — copy it to
`.taskrail/types/<kind>/` — so nothing is broken, only mis-documented.)

### E8. The flag surface, all 71, by class

Produced by `<scratchpad>/flags.sh` (reproduced below), then corrected for the blind spot in E3.

**C1 — named in a shipped skill (39 of 71).** `--breaking --check --cleanup --column --count
--decision --depends-on --description --done-when --epic --event --fetch --force --gate --group
--handle --ignore-deps --json --kind --kinds --name --objective --own-file --path --pts --publish
--question --reason --resource --root --run --scope --stage --state --task --tasks --title --type
--workspace`. Five further `--…` strings in those skill files are git's, not taskrail's, and are
discarded: `--no-track`, `--onto`, `--grep`, `--abbrev-ref`, `--unset-upstream`.

The other 32 fall out as follows.

**C1 by machine — consumed by installed machinery, not by a person (5).** `--marker-size`,
`--base-label`, `--current-label`, `--other-label` are read by the git merge-driver config string
(`mergedriver.py:36`), which E4 shows no visible repository has installed; `--version` is read by
the `.taskrail/bin/taskrail` wrapper (`install.py:239`:
`have=$(taskrail --version | sed 's/^taskrail //')`), which every command in this task went
through.

**C2 — reaches a consumer through `init` (4).** `--integration`, `--github-workflow`,
`--pre-commit`, `--merge-driver`. Only `--integration` was used in the one visible installation.

**C3 — documented in `DESIGN.md`, no setter or caller visible (14).** `--allow-invalid`,
`--backlog`, `--branch`, `--default-kind`, `--epic-level`, `--epic-name`, `--history-limit`,
`--local-only`, `--no-fetch`, `--no-history`, `--remote`, `--status`, `--takeover`, `--write`.

**C4 — exercised only by its own test (6).** `--dry-run` (1 test; also used by the release chores'
write-ups), `--message` (1), `--no-push` (1), `--owner` (**147 test occurrences, 0 in any skill,
2 in `DESIGN.md`**), `--tag` (1), `--worktree` (1 test, in `test_current_branch.py:337`).

`--owner` deserves its own line: it is the most heavily tested flag in the tool and the only way
the test suite can simulate a second person, yet no skill tells an agent to pass it and no
documented workflow needs it. It is the clearest example of *a test but no user* that the `frame`
stage's C4 class was created to name.

**C5 — nothing anywhere but the parser that defines it (3).**

```
$ git grep -n -F -e '--file' -e '--id' -e '--limit' -- ':!src/taskrail/cli.py'
(no output — the three strings appear nowhere else in the repository)
```

- `epic add --id ID` — "epic ID (default: next in the backlog)". It lets a caller choose an ID by
  hand, which is the one thing the core skill forbids in its first paragraph: "**The CLI owns
  IDs.** Never invent an ID."
- `epic add --file FILE` and `epic split --file FILE` — put the epic in a named file instead of
  `todo/<id>-<slug>.md`. `--own-file` (C1) covers the documented case.
- `next --limit LIMIT` — undocumented in §7, which describes `next` as `[--fetch]` only.

All three are absent from `DESIGN.md`, from every test, from every skill and from all 76 past task
write-ups under `docs/` (12 bugs + 19 chores + 39 features + 1 research + 5 spikes). They are the
only options in the surface for which no consumer of any kind was found, and E3's caveat still
applies: a human could be typing them.

The classes account for the surface exactly: 39 + 5 + 4 + 14 + 6 + 3 = **71**.

### E9. What removing or defaulting each weak option would cost a repository on 0.3.0

Costs follow directly from E2 and the version pin, so they group rather than needing 46 separate
arguments.

| Group | Cost of removing | Cost of fixing at the default |
|---|---|---|
| Any configuration key (`epic_prefix`, `claim_remote`, `branch_record_remote`, `task_branch`, `commit`, `handoff`, `notify*`, groups, resources, `kinds.allowed`, `columns.aliases`, `id_digits`, `may_depend_on`, `[review]` keys) | **Silent.** The line stays, `validate` stays green, behaviour reverts at the next `taskrail upgrade`. A repository that had set it loses what it configured with no message. For `claim_remote`, `branch_record_remote` or `task_branch` that is a change to how the repository is *worked*, not a cosmetic one. | Identical to removing: the key is ignored either way. There is no cheaper middle option today. |
| A CLI flag (`--id`, `--file`, `--limit`, `--owner`, `--worktree`, `--takeover`, …) | **Loud**: exit 2, `unrecognized arguments: --x`, at the call site. A script or skill that used it fails immediately and visibly. | Same: an accepted-but-ignored flag would be worse, because it would fail silently. |
| A command (`import`, `merge-driver`, `release`, `reserve-id`, …) | **Loud**: exit 2 listing the commands that exist. For `merge-driver` the failure lands inside a git merge, through the driver line in `.git/config`, which is a bad place to discover it. | n/a |
| Anything, for a repository that has not upgraded | **Zero.** The wrapper runs the pinned version (`install.py:220`); nothing changes until the pin does. | Zero. |

The practical asymmetry: **a flag or command removal announces itself and can be fixed in one
edit; a configuration removal cannot be noticed at all.** That is what makes the unknown-key
warning the highest-value finding in this report, and it is what should be built *before* any
option is retired, not after.

## Options considered

### How to treat the surface as a whole

| Option | What it means | Cost |
|---|---|---|
| **A. Report, warn, and route each finding to its own task (recommended)** | Change nothing now. Open one task to make unknown configuration keys loud, and one task per coherent group of options that asks the human — who can see the private consumers — whether it is still wanted. | The surface stays as it is until each question is answered. Several small tasks instead of one sweep. |
| B. Retire the weak options in one sweep | One chore removes `epic_prefix`, `--id`, `--file`, `--limit`, `handoff`, and defaults the rest. | Forbidden by T087: the principles are prospective and this spike licenses no removal. It would also break E2's rule — silent configuration losses — for consumers this repository cannot see, which is precisely the failure the publishing constraint exists to prevent. |
| C. Report and do nothing else | Write the measurement; open no tasks. | The findings then depend on someone re-reading this document. T087's verdict routes existing-code questions through the backlog; with no task, there is no route. |
| D. Deprecate everything weak with a warning first | Add a deprecation warning to every C3/C4/C5 option. | ~30 warnings for a problem whose measured size is one C5 key and three C5 flags. Fails the rule of three and KISS on the principles' own terms. |

### What to do about the documentation defects (E7)

| Option | What it means | Cost |
|---|---|---|
| **E. Fix the four documentation defects as one small chore (recommended)** | `DESIGN.md` §4 gains `epic_prefix` and `id_digits`; §7 drops `kind add` and replaces `--eligible` with `--state`; §7 gains `--limit`, `--file`, `--id` or the task that removes them settles them first. | One `DESIGN.md` chore. It overlaps T089's subject (whether `DESIGN.md` is split), so it should be sequenced after T089 decides. |
| F. Fold them into the option tasks | Each option's task fixes its own documentation. | Spreads a five-minute documentation fix over four tasks and leaves §7 wrong for months. |

## Recommendation

**Change nothing in this task; open five tasks, in this order.** Each is a prospective change to be
argued on its own merits when it is proposed, and none of them is a decision to remove anything.

1. **Make an unknown configuration key loud** (`feature`, small). `taskrail validate` warns —
   not errors — for a key under a known table that taskrail does not define, naming the key and
   the table. This is the only finding this measurement supports on its own evidence (E2): today
   a typo in `.taskrail/config.toml` is as silent as a removal, and until it is loud, *no*
   configuration key can be retired safely. It also pays for itself immediately, for typos, long
   before any removal is considered.

2. **Ask the human about the five options with no visible setter and no documentation**
   (`spike` or `chore`, small): `[[backlog]].epic_prefix` (C5, undocumented — E6),
   `[[backlog]].id_digits` (C4, undocumented), `epic add --id`, `epic add --file` /
   `epic split --file` and `next --limit` (C5 — E8). For each, the question to the human is "does
   any repository you can see use this?", and the answers split into *document it* or *propose
   removing it*. Nothing here is decided by this spike.

3. **Ask about `[autopilot].handoff`** (`chore`, trivial). It has exactly one legal value and
   `DESIGN.md` says so. Either a second mode is planned — in which case the key is a placeholder
   that should say so — or it is a setting with no settings.

4. **Record the state of the remote half of §6** (`spike`, small): `claim_remote`,
   `branch_record_remote`, `claims --remote`, `--fetch` on three commands, `--local-only` on four.
   No repository visible here enables either key, and the skill's `show --fetch` step is therefore
   a no-op in the only installation visible (E6). The question for the human is whether a private
   consumer runs taskrail from more than one clone. **If the answer is no, the recommendation is
   still not removal** — it is to stop telling every executor to pass `--fetch`, which is a one-line
   change to a skill and costs nothing to reverse.

5. **Fix the documentation defects** (`chore`, small), as option E: `epic_prefix` and `id_digits`
   missing from §4; `kind add` and `list --eligible` documented but absent (E7). Sequence it after
   T089, which decides whether `DESIGN.md` is restructured.

**Not recommended, explicitly:** any task that removes `import`, `merge-driver`, the autopilot's
groups, resources or notification, `[git].task_branch` or `[git].commit`. Each of them is large,
tested, documented and recent, and each is exactly the kind of option whose consumer this
repository cannot see. The measurement says they are unused *here*; it does not say they are
unused. If they are to be reconsidered, the question belongs to whoever can see the private
installations, and it should be asked before any work is planned, not after.

**A note on the shape of the result.** The honest headline is not "taskrail has 46 options and uses
9". It is, as *How to read this report* puts it, that a tool built by one repository for many will
always look over-supplied from inside that one repository, and the only measurement that
repository can make is of its own use. What YAGNI can say from here is narrow and worth saying:
**four options exist that nobody here can even discover, one has a single legal value, and no
configuration key can be withdrawn safely until an unknown key is reported.** Everything else is a
question for the human, and this document's job is to have asked it precisely.

Each recommendation above rests on the asymmetry of E2, and is weaker or stronger accordingly.
Recommendation 1 rests on it directly and is the strongest thing here. Recommendations 2 and 4
concern configuration keys *and* flags, and the flag half of each is the weaker half, because a
human typing `next --limit` leaves nothing for a grep to find. Recommendation 3 rests on a value
list in the source, not on a search, so the asymmetry does not touch it. None of them is an
instruction to remove an option; all of them are instructions to ask.

## What would change the decision

- **A second visible consumer repository.** Any option this report calls C3/C4/C5 would move to C1
  the moment a second config file is visible. The report's classes are statements about one file,
  not about the world.
- **The human naming a private consumer** for any option above. That settles that option and
  should be recorded, so the next audit does not re-ask it.
- **The unknown-key warning being built.** Once a removed key produces a message, the cost table
  in E9 changes completely: configuration removals become as loud as flag removals, and the
  recommendations above can be revisited on much cheaper terms.
- **`taskrail init` seeding `[autopilot]`.** It does not today (E5), so every autopilot consumer
  writes that table by hand. If the seed grew it, the "no visible setter" evidence for
  `notify`, `groups` and `resources` would have to be re-read: a seeded empty key is a different
  thing from an absent one.
- **A measured cost of the surface.** Nothing in this report measures a *harm* — no bug traced to
  an unused option, no consumer confused by one. If such a case appears, the argument for retiring
  an option stops being aesthetic and the recommendations should be re-weighed.
- **Counting differently.** A reader who counts 70 or 72 flags rather than 71 has reproduced the
  same parser; if a recount produced a materially different *number of commands* (not 27 and 42),
  the whole measurement should be redone, because those two are exact.

## How to reproduce

From a checkout at 4a956c4 or later, in the repository root.

```bash
uv run pytest -q                                   # 1183 passed: the tree measured was healthy
cat .taskrail/config.toml                          # E5: the only config file visible
cat .taskrail/installed.json                       # E4: "extras": {}, one integration
git config merge.taskrail.driver                   # E4: no output — the merge driver is not installed
ls .git/hooks | grep -v sample ; ls .github/workflows   # E4: no hook, no workflow
sed -n '109,205p' DESIGN.md                        # E5: the documented example config
sed -n '/^def default_config/,/^DEFAULT_TODO/p' src/taskrail/install.py   # E5: what init seeds
sed -n '605,633p' DESIGN.md                        # E7: the §7 command table
grep -n "epic_prefix" DESIGN.md                    # E6: no output
git grep -n "epic_prefix" -- src/taskrail tests    # E6: implementation only
git grep -n -F -e '--file' -e '--id' -e '--limit' -- ':!src/taskrail/cli.py'   # E8: no output
.taskrail/bin/taskrail kind add examples           # E7: invalid choice: 'add'
.taskrail/bin/taskrail list --help                 # E7: --state, not --eligible
.taskrail/bin/taskrail list --nonexistent-flag     # E2: exit 2, named
grep -n "Useful commands" -A1 src/taskrail/skills/taskrail/SKILL.md   # E3: the method's blind spot
```

**E2, the silent-key probe** (it writes only under `$D`, never in the repository):

```bash
D=$(mktemp -d); mkdir -p "$D/.taskrail"
cp TODO.md "$D/TODO.md"
sed -e 's/^version = "local:."/nonsense_top_key = "x"\nversion = "local:."/' \
    -e 's/^claim_remote = ""/claim_remote = ""\nnonsense_git_key = true/' \
    .taskrail/config.toml > "$D/.taskrail/config.toml"
uv run taskrail --root "$D" validate; echo "exit=$?"    # 0 errors, 0 warnings, exit 0
```

**E1, the surface count** (`surface.py`; `--per-command` prints the flags of each of the 42
commands):

```python
import sys
from taskrail.cli import build_parser

def walk(parser, path, rows, flags):
    own = set()
    for a in parser._actions:
        own.update(s for s in a.option_strings if s.startswith("--"))
        if a.__class__.__name__ == "_SubParsersAction":
            for name, sub in a.choices.items():
                rows.append(" ".join(path + [name]))
                walk(sub, path + [name], rows, flags)
    flags[" ".join(path) or "<root>"] = sorted(own)

rows, flags = [], {}
walk(build_parser(), [], rows, flags)
allflags = set().union(*flags.values())
if "--per-command" in sys.argv:
    for cmd in ["<root>"] + rows:
        print(f"{cmd}: {' '.join(flags.get(cmd, []))}")
    raise SystemExit
print("commands (all levels):", len(rows))
print("top-level commands:", len([c for c in rows if " " not in c]))
print("distinct long flags (incl --help):", len(allflags))
print("distinct long flags (excl --help):", len(allflags - {"--help"}))
```

**E8, the flag classification** (`flags.sh`). Each column is a fixed-string `git grep -F` for the
flag over one path set; the parser files are excluded from `CODE` so a flag's own definition does
not count as its consumer. `ART` is `docs/`, the past task write-ups: evidence that an option was
exercised once during development, not that anything consumes it now.

```sh
set -eu
flags=$(uv run python -c '
from taskrail.cli import build_parser
f=set()
def w(p):
    for a in p._actions:
        f.update(s for s in a.option_strings if s.startswith("--"))
        if a.__class__.__name__=="_SubParsersAction":
            [w(s) for s in a.choices.values()]
w(build_parser()); f.discard("--help"); print("\n".join(sorted(f)))')
for f in $flags; do
  c() { git grep -cF -- "$f" -- "$@" | awk -F: '{n+=$2} END {print n+0}'; }
  printf '%-20s %5s %5s %5s %5s %5s %5s\n' "$f" \
    "$(c src/taskrail/skills src/taskrail/integrations)" \
    "$(c .taskrail .claude .github CLAUDE.md README.md)" \
    "$(c src/taskrail ':!src/taskrail/cli.py' ':!src/taskrail/importer.py' \
         ':!src/taskrail/skills' ':!src/taskrail/integrations')" \
    "$(c tests)" "$(c DESIGN.md CHANGELOG.md)" "$(c docs)"
done
```

The 39/32 split of E8 comes from intersecting that flag set with the `--…` strings in the shipped
skills, which is exact where a grep count is not:

```python
import re, pathlib
from taskrail.cli import build_parser
flags = set()
def w(p):
    for a in p._actions:
        flags.update(s for s in a.option_strings if s.startswith("--"))
        if a.__class__.__name__ == "_SubParsersAction":
            [w(s) for s in a.choices.values()]
w(build_parser()); flags.discard("--help")
found = set()
for d in ("src/taskrail/skills", "src/taskrail/integrations"):
    for p in pathlib.Path(d).rglob("*"):
        if p.is_file():
            found |= set(re.findall(r"--[a-z][a-z-]*", p.read_text()))
print(len(flags), len(flags & found))           # 71 39
print(sorted(flags - found))                    # the 32
print(sorted(found - flags))                    # git's own: --abbrev-ref --grep --no-track --onto --unset-upstream
```

`commands.sh` is the same shape with `taskrail <command>` as the search string; **its output must
be corrected by hand** for `list`, `claims` and `kind list`, which the core skill names without the
`taskrail ` prefix (E3). `config.sh` does the same for the configuration keys, reading the §4
example from `sed -n '109,205p' DESIGN.md` and the seed from `default_config`; its `-w` counts
undercount keys written after `\n` inside a Python string, so the tables above use unanchored
counts.

## Outcome

The `decide` gate of this spike is escalated to the human by
`[autopilot].escalate_gates = ["spike:decide"]`. On 2026-09-18 the human **accepted the report and
all five follow-up tasks**, taking none of the alternatives offered (task 1 alone, none at all, or
rejecting the report). The orchestrator answered the other three decisions as recommended: T092's
row is left alone, `--owner` is folded into T095's question list rather than given a task, and the
core skill's `--fetch` step is not touched here but carried in T097's description. The orchestrator
also re-ran the load-bearing evidence independently — the unknown-key probe of E2, the empty
`git grep` for `--file`, `--id` and `--limit`, `kind add` exiting 2 while §7 documents it, and
`HANDOFF_MODES = ("sequential",)` — rather than taking this document's word for them.

Two things were made more prominent at that gate, on the orchestrator's note: *How to read this
report*, which states up front that the measurement is of one repository's use and not of
taskrail's users, and the closing paragraph of *Recommendation*, which says for each
recommendation how strongly the E2/E3 asymmetry supports it. Both exist to keep a future reader
from turning this inventory into a removal list.

## Follow-ups

Opened on this task's branch after the `decide` gate, so the measurement and its routing are
reviewed together. The human accepted all five on 2026-09-18; the answers are recorded in
[`docs/autopilot/decisions/T088-measure-the-cli-and-configuration-surfac.md`](../autopilot/decisions/T088-measure-the-cli-and-configuration-surfac.md).
Each is a prospective change, to be judged on its own merits when it is worked; **none of them is
a decision to remove anything**, and each carries the evidence class it rests on, so its executor
can see how strong that evidence is.

| ID | Kind | Pts | Title | Evidence it rests on |
|---|---|---|---|---|
| T094 | `feature` | 2 | Warn about a key taskrail does not know in `.taskrail/config.toml` | **E2**, the strongest in the report: a configuration removal, and equally a typo, is silent today |
| T095 | `spike` | 2 | Ask whether the options no visible repository sets or documents are still wanted | **E6** (`epic_prefix`, `id_digits`: config keys, strong evidence) and **E8** (`epic add --id`, `epic add --file` / `epic split --file`, `next --limit`, `--owner`: flags, weaker evidence — see E3) |
| T096 | `chore` | 1 | Settle whether `autopilot.handoff` is a placeholder or a setting with no settings | **E6**: `HANDOFF_MODES = ("sequential",)` in the source; no search involved, so E3's caveat does not apply |
| T097 | `spike` | 2 | Record whether any repository enables the remote half of claims and branch records | **E6**: two configuration keys with no setter here, and the `show --json --fetch` step the core skill prescribes, which is a no-op in the only installation visible |
| T098 | `chore` | 1 | Fix the configuration and CLI documentation defects `DESIGN.md` carries | **E6** and **E7**: `epic_prefix` and `id_digits` missing from §4; `kind add` and `list --eligible` documented and absent |

T098 depends on T089, which decided not to split `DESIGN.md`, so it edits the file as it stands,
touching §4's example and §7's command table only — not the top of the file, where T089's own
follow-up T093 adds a reading map.

T088's own row was deliberately **not** edited from this task: its figures are corrected by T092,
which belongs to another lane. T092's description plans "about 70 distinct long flags" and "42
documented keys" where this measurement gives 71 flags (72 counting `--help`) and 46 settable
names, 40 of them outside the two repeatable tables. The difference is counting method, not fact,
and this document states its method in E1 and E5; T092's row is left alone.
