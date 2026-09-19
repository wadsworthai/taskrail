# Changelog

Releases are tagged `vX.Y.Z`. Use one in a repository without installing anything:

```bash
uvx --from "git+https://github.com/wadsworthai/taskrail.git@vX.Y.Z" taskrail upgrade
```

In a repository that has no `.taskrail/` yet, that is `taskrail init --integration <agent>`
instead of `upgrade`. To install the CLI on your machine as well:
`uv tool install taskrail --from "git+https://github.com/wadsworthai/taskrail.git@vX.Y.Z"`.

## Unreleased

- **`epic add` no longer reissues the ID of an archived epic.** It allocated one above the highest
  epic in the `## Epics` table, and `taskrail archive` removes a whole epic from that table, so once
  the highest-numbered epic was archived the next `epic add` handed its ID out again, beside the
  archive's section of that ID, and a later `archive` filed the new epic's rows under the old one's
  heading. It now also counts the epic sections in the backlog's archive on the working tree, and
  `--id` refuses an archived epic's ID with exit 5, as it already refused a live one. `validate`
  still never reads the archive. Epic IDs are still neither scanned across branches nor reserved,
  unlike task IDs (T122).

- **`done` and `discard` now warn when the checkout they wrote to is not on the task's branch.**
  Run against another checkout — the mainline, say — they ticked that checkout's row, released the
  claim, printed `<ID> done` and exited 0, while the branch that carries the pull request kept its
  `⬜`; nothing was printed and `--json` had no field to read. `claim` has warned about the same
  mistake since it started recording a task's branch, and the two commands never asked. They now
  print the same kind of warning on stderr and return it in `--json` as `warning` (`null` when
  there is none), with the exit code unchanged at 0. The wording is retrospective, since the row is
  already written when it prints: it names the checkout, the branch it is on and the task's branch,
  and says the row on that branch is unchanged. It is silent where there is no branch to compare:
  under `[git].task_branch = "current"`, outside git, and on a detached `HEAD`, which `claim`
  already covers. This is the only cover for the case no rule about resolving the repository root
  can catch, where the path a command was invoked by and the directory it ran in agree and are both
  the wrong checkout (T119).

- **The wrapper now acts on the checkout it lives in, whatever the current directory is.**
  `.taskrail/bin/taskrail` already computed its own checkout's root and used it to read the version
  pin and to find a `local:` source, and then did not pass it on, so the wrapper decided which
  taskrail *ran* while the current directory decided which repository it *acted on*. Running one
  checkout's wrapper from a shell sitting in another wrote there instead: a claim recorded against
  the wrong checkout, and `upgrade` installing one checkout's skill sources into another — the
  second with no `--force`, since the digest guard only skips a file a human edited, and leaving
  `git status` clean in the damaged checkout, so it read as "forgot to run `upgrade`" rather than
  as an overwrite. The wrapper now passes `--root "$root"` on all three paths that run the CLI.
  `--root` still points it at another repository and overrides that default, because it is a global
  flag whose last occurrence wins; `TASKRAIL_BIN` is unchanged, since it delegates to a binary of
  the caller's choosing. **An installed repository picks the fix up with `taskrail upgrade`**: the
  wrapper is a managed file, so an untouched one is rewritten and one edited locally is left alone
  and reported as `edited locally; --force replaces it`. **One caller changes behaviour**: a
  repository that deliberately ran one checkout's wrapper against another repository without
  `--root` now acts on the wrapper's own checkout, and must pass `--root` to keep aiming elsewhere
  — such a caller was already running the wrong pinned version for its target, since the pin comes
  from the wrapper's own config (T115 decided this, T118 applied it).

- **The workflow `--github-workflow` generates now runs with least privilege.** It set no
  `permissions`, so its `validate` job ran with the repository's default `GITHUB_TOKEN`
  permissions — read-write on every scope in repositories created before GitHub changed that
  default, and in any organisation that still sets it so — while the job only checks the
  repository out and runs `taskrail validate`, which writes nothing back. The template now grants
  `contents: read` at the workflow level, the shape this repository's own `ci.yml` already uses,
  and every scope a `permissions` block leaves unnamed is `none`. It is `contents: read` rather
  than no scopes at all because `actions/checkout` still has to read a private repository.
  **An installed repository picks this up with `taskrail upgrade`**: the workflow is a managed
  file, so an untouched one is rewritten. **A repository whose workflow was edited locally is
  left alone** — `upgrade` reports it as `edited locally; --force replaces it` — and has to add
  the two lines itself:

  ```yaml
  permissions:
    contents: read
  ```

  (T120.)

- **The workflow `--github-workflow` generates now names action tags that exist.** It pinned
  `astral-sh/setup-uv@v10`, and that project publishes bare major tags only through `v7` — its
  tenth line exists only as `v10.0.0`, `v10.0.1` and `v10.1.0` — so GitHub could not resolve the
  step and the `validate` job failed before it ran anything, in every repository that installed
  the extra at `v0.1.0`, `v0.2.0` or `v0.3.0`. The template now pins both of its actions to exact
  release tags, `actions/checkout@v7.0.1` and `astral-sh/setup-uv@v10.1.0`, the same pair this
  repository's own CI uses; a test keeps every `uses:` in that shape, since not every action
  publishes a floating major. **An installed repository picks the fix up with `taskrail upgrade`**:
  the workflow is a managed file, so an untouched one is rewritten, and one edited locally is left
  alone and reported as `edited locally; --force replaces it` — a repository in that case changes
  the `setup-uv` line itself (T116).

- **The autopilot skill now says what bounds a run — the orchestrator's context — and tells the
  orchestrator to plan the count against it.** A run's count was chosen with no idea of its ceiling.
  A lane ends with its task, while the orchestrator accumulates every lane's report, every gate
  answer and every hand-off, so the orchestrator's session is the one that fills up, and compaction
  is not the limit that matters. `taskrail-autopilot` now has the orchestrator measure its own cost
  per dispatched task, propose the count it can hold when the human asks for more, and send the rest
  to a fresh session through *Resume a run* — the planned path for a long backlog, not only a
  recovery. The rule is in the portable skill and carries no numbers; the measured figures, which
  are one agent's and one model's, are attributed in the Claude Code integration note and in
  DESIGN.md §12.1: nine of this repository's own runs, 36,728 and 44,343 tokens of orchestrator
  context per dispatched task on the two long ones over a 32k–39k session overhead — roughly 21 to
  26 tasks in a 1M context — against 38 lanes that peaked at 78k–356k and never compacted (T057
  measured it, T111 wrote it down). No CLI behaviour changed.

- **`next --limit` refuses a value below 1 instead of answering it wrongly.** `--limit` took any
  integer and was used only as a slice bound, so `--limit 0` printed `no eligible tasks` (and `[]`
  with `--json`) and exited 0 — indistinguishable from a backlog with nothing eligible — while a
  negative value silently dropped that many tasks from the **end** of the list and reported the
  rest as a complete answer. It now uses the same converter as `validate --history-limit`:
  `--limit 0` and `--limit=-1` exit 2 with
  `argument --limit: expected a whole number of at least 1, got \`0\``, printing nothing to
  stdout, and a non-numeric value gets that message too instead of `invalid int value`. **A script
  passing 0 or a negative `--limit` now fails where it used to exit 0**; every value of 1 or more
  behaves exactly as before (T109).

- **`taskrail archive` moves closed tasks and closed epics out of the backlog.** A backlog kept
  every row it ever had, so a long-lived one grew without bound and a reader met years of finished
  work before the open rows. The new command — run by the human, never automatic on `done` — moves
  every `✅` and `❌` row into the document `[[backlog]].archive` names (default
  `{artifacts}/archive.md`), and an epic whose rows all move goes whole: its `## Epics` row, its
  section, its own file where it has one, and its objective and `Done when:` carried across. A
  closed row that a row staying behind depends on is held back and named in the output, which is
  what keeps the backlog valid: `validate` never reads the archive. The archive is the same
  Markdown as the backlog, so `grep` still finds a task, `ids` counts archived IDs as used — an
  archived ID is never allocated again — and the merge driver merges two branches' archives row by
  row, its `.gitattributes` block naming the archive from `init --merge-driver` and `upgrade`. An
  archived task is not reopened: `taskrail reopen` exits 3 naming the archive file the ID sits in.

- **A task waiting for the human no longer holds an autopilot lane, and the answer puts it back in
  the queue.** A lane stopped at an escalated gate kept its lane until the human replied, so a run
  with `max_lanes = 3` and two escalations had one lane working while `autopilot next` reported
  `limited_by: max_lanes`. An `escalated` task now keeps its claim, branch and worktree but frees
  its lane and its resource values, exactly as a `failed` one has always done, so `next` may start
  another task in its place. When the human answers, the orchestrator records the new lane state
  `taskrail autopilot lane <ID> --run <R> --state parked`, and the next `next --run <R>` sends the
  task back before any task that has never started — oldest answer first, subject to `max_lanes`,
  the group limits and the resources, but not to the run's count, which already held it — with
  `restart: true` in its entry so the lane resumes on its own branch. An answer that arrives while
  every lane is busy waits: `next` lists it in `parked` with why, and `autopilot status` reports
  every task's `holds_lane`, false for a task that keeps its workspace but no lane. Nothing caps
  those parked workspaces, so a run may hold `max_lanes` working lanes plus every task waiting for
  a human (T105).

- **uvx is the documented default, and nothing has to be installed on the machine.** The
  no-global-install route already worked — the committed wrapper runs the pinned version through
  `uvx`, and the generated GitHub workflow installs only `uv` — but the documentation taught
  `uv tool install` alone. README's *Install* and *Use* and DESIGN.md §9 now lead with bootstrapping
  through `uvx --from "git+<repo>@<tag>" taskrail init` and calling `.taskrail/bin/taskrail`
  afterwards, since `init` pins the version it ran as and the wrapper reproduces it. They also say
  what upgrading means with no CLI installed: `uvx --from "git+<repo>@<tag>" taskrail upgrade`
  moves the pin, where `self upgrade` only replaces a global CLI. Installing globally stays
  supported and documented, and no behaviour changed (T100).
- **The backlog file defaults to `TASKRAIL.md`, and taskrail no longer takes `TODO.md`.**
  `[[backlog]].file` was required and `init` seeded it as `TODO.md` — the one name a consuming
  repository is most likely to be using for its own list, which `init` then silently adopted as the
  backlog, leaving the repository failing `validate` out of the box. `file` is now optional and
  defaults to `TASKRAIL.md`, `init` writes that name in the config it seeds and creates that file,
  and a repository's own `TODO.md` is left where it is. **Nothing changes for an existing
  repository**: `file` was required, so no config that loads at all omits it, and `init` and
  `upgrade` never rewrite or re-seed a backlog file that exists. Nothing is renamed and nothing
  offers to rename; to keep `TODO.md`, write `file = "TODO.md"`, or convert it with
  `taskrail import TODO.md --write`. The one cost: a config written for this version that *omits*
  `file` will not load on v0.3.0 or earlier, which exits 2 with `missing required key \`file\``
  (T099).

- **`validate` warns about a name in `.taskrail/config.toml` that taskrail does not define.** A key
  taskrail does not know was ignored in silence, so a typo did nothing and no configuration key
  could be withdrawn without a repository quietly losing what it had set. `validate` now reports it
  as a warning — in its text and in `--json` — naming the key and the table it sits in, with
  `did you mean …?` for a near miss, and one warning for a whole table it does not know. It is never
  an error: the exit code stays 0 and every command goes on working, so a config written for another
  version still loads (T094).

- **Every executor reads the repository's own instructions before it plans.** The `taskrail` skill's
  procedure now opens its stages step by telling the executor to read the repository's agent
  instruction files, if it has any, and follow what they ask of the work at hand — so every kind
  does what `taskrail-chore` alone did, whatever agent runs it. Run `taskrail upgrade` to install
  it (T091).

- **A refused ID now names the configuration key that would accept it.** `validate` refused an
  epic or task ID by quoting the prefix it expected — ``epic ID `EP01` does not match `E` plus two
  or more digits`` — so a repository whose epics are numbered `EP01` was told what taskrail wanted
  but not which key would let it keep its own numbering, and the fix was discoverable only by
  reading the source. Both messages now name the key: `epic_prefix` for an epic ID and `prefix` for
  a task ID. Nothing else changes — the `epic-id` and `task-id` codes, the exit codes and the
  `--json` shape are as they were (T103).
- **The core skill says plainly what `show --fetch` needs.** Step 3 tells every executor to run
  `taskrail show <ID> --json --fetch` before it branches, and its condition sat mid-sentence, so the
  flag read as unconditional. It now says that the fetch does nothing, and says nothing, unless the
  repository sets `[git].branch_record_remote` — and that where it is set it brings in the branch
  names other clones recorded, without which a task finished on a branch renamed elsewhere reads as
  pending on a template name. README's command reference names the key too. No behaviour changed:
  the flag, its guard and the key are untouched. Run `taskrail upgrade` to install it (T104).
- **The config `init` seeds now shows the autopilot's keys, commented out.** `init` configures no
  autopilot and no flag does, so a repository that wanted one wrote the `[autopilot]` section from
  scratch after finding the keys in DESIGN.md §12 — the only hand work a real install left. The
  seeded `.taskrail/config.toml` now ends with a commented block carrying `enabled`, `max_lanes`,
  `read_first`, `governing` and `escalate_gates`, next to the commented examples `[columns]` and
  `[checks]` already had, so enabling the autopilot is uncommenting it. Every line is a comment:
  the seeded config parses exactly as before, `[autopilot]` is still absent from it, and
  `autopilot start` still refuses with exit 5 until a repository opts in. Nothing reaches an
  existing repository — `upgrade` moves the version pin and never rewrites a config — so README's
  install section now says the section is written by hand and where its keys are documented (T003).

## 0.3.0

Adds the current-branch workflow (DESIGN.md §13) for a repository worked by a single maintainer:
`[git] task_branch = "current"` works a task on the checked-out branch, `commit = "on-done"` commits
a task's changes only when it is done, a stage with `gate = "decisions"` stops only for a decision,
and `review` closes a current-branch task with a report instead of publishing it. The skills follow
each setting. Every setting is off by default, so a repository that sets none of them works as it
did in 0.2.0.

- **The skills follow the repository's workflow.** The `taskrail` skill reads `task_branch`,
  `close.commit`, `close.review` and each stage's gate from `show`: under `task_branch = "current"`
  it skips the workspace step, claims in the checkout and closes with `review --json` as a report,
  **asking the human before any push**; under `commit = "on-done"` it commits nothing before `done`
  and then commits everything the task changed; a `"decisions"` gate stops only for a decision. The
  executor skills, the Claude Code and OpenCode notes and the autopilot skill follow, and the README
  documents a single-maintainer configuration (T084).
- **Close a current-branch task with a report.** Under `[git] task_branch = "current"`,
  `taskrail review <ID>` fetches, rebases and pushes nothing: it keeps its `--json` keys with
  `fetched`, `rebase.enabled`, `push.enabled` and `published` `false` and a reference pull request
  title and body without a link, and adds `commits` (the commits on `HEAD` naming the task)
  and `upstream` (the branch's upstream and how many commits it lacks). `--publish` exits 5 naming
  the setting. `show` adds `close.review`: `"publish"`, or `"report"` under `"current"` (T083).
- **A `decisions` gate.** A stage in a core, local or override kind descriptor may set
  `gate = "decisions"`: the executor stops as soon as a decision appears during the stage and never
  to approve the stage. `validate` accepts it, `show` and `kind list` report it, and the autopilot
  records and escalates it like any gate (DESIGN.md §5.6, §12.6; T082).
- **Work tasks on the checked-out branch with `[git] task_branch = "current"`.** With
  `worktree = "never"` (required, exit 2 otherwise), a task has no branch of its own: `show`, `list`
  and `next` report the checked-out branch with `branch_source` `"current"`, no `base` or worktree,
  and never `done-branch`, `discarded-branch` or a stacked base; `claim` records that branch without a
  warning or branch record; `new --workspace`, `workspace` and `branch` exit 5; `new` does not warn
  on the mainline; `checks` runs in the checkout; and `autopilot start`, `extend` and `next` exit 5.
  `show`, `list` and `next` report the setting as `task_branch` under every configuration (T080).
- **Commit a task's changes only when it is done.** `[git] commit = "on-done"`, or a top-level
  `commit = "on-done"` in a kind descriptor, which wins over `[git]` either way, makes a task's
  effective commit policy `"on-done"`: `show --json` and `kind list --json` then report every
  stage's `commit` as `false`, and each descriptor carries `commit` and `commit_source`; `show` adds
  `close.commit`, and `done` and `discard` report `commit` and tell the executor to commit everything
  the task changed. Any other value exits 2 in `[git]` and is a `kind-invalid` error in a descriptor.
  `autopilot start`, `extend` and `next` exit 5 when a kind the run drives commits on done (T081).

## 0.2.0

Adds the autopilot (DESIGN.md §12), `edit`, `import`, `checks`, `workspace`, `branch` and a merge
driver for backlog tables and changelogs. Read the entries marked **Behaviour change** before
upgrading.

- **A task's worktree is one path from every checkout, created where it is reported.**
  `show`, `list`, `next` and `autopilot next` report `worktree` relative to `worktree_base`, an
  absolute directory they also report: the main checkout of an ordinary clone, or the directory
  holding a bare repository. `new --workspace` and `workspace <ID>` create the task's worktree at
  `<worktree_dir>/<branch>` under it from any checkout, and refuse when that path exists; the
  `taskrail` skill and the lane brief join the two instead of reading `git worktree list`. Before,
  an existing worktree came out absolute when read from inside it or from another worktree, one
  created inside another worktree was nested below it, and a bare repository's worktrees were read
  against and created in the bare directory itself (T072, T073, T075).
- **`autopilot merged --cleanup` keeps worktrees nested in the one it removes.** It now refuses (exit
  5) and removes nothing when another registered worktree lies inside the task's worktree, naming
  those worktrees; before, one in an ignored directory such as a `.worktrees/` that an earlier
  `new --workspace` nested there was deleted with its uncommitted work (T074).
- **Named autopilot runs, extended runs and prepared workspaces.** `autopilot start --tasks IDs`
  starts a run that works only those tasks, in the order given, with their number as its count;
  `autopilot extend R --tasks IDs` adds tasks to such a run and `--count N` sets a count-only run's
  count. A task whose row lives only on its own branch, as `new --workspace` leaves it, is found by
  the autopilot commands and `taskrail checks` from any checkout — `new --workspace` now records its
  branch — so `next` and `status` count the same lanes wherever they run. `prior_work.prepared` marks
  a branch that holds only the task's row, and the lane brief works in it instead of stopping (T071).
- **taskrail has its own repository.** It was extracted with its history from a larger repository,
  where it lived in a subdirectory and was tagged `taskrail-vX.Y.Z`. Releases are now tagged
  `vX.Y.Z` at `github.com/wadsworthai/taskrail` and install without `#subdirectory`; the wrapper,
  `taskrail self upgrade`, the pin that `init` and `upgrade` write and the installed skills'
  `source` all follow. Reinstall from the new repository, then run `taskrail upgrade` in each
  repository to move its wrapper and pin.
- **A row missing from its base.** `show`, `list` and `next` report `base.row` (`on-base`,
  `on-branch` or `missing`), `autopilot next` skips a task whose row only the checkout has,
  `taskrail workspace <ID>` moves such a row with its ID into the task's own branch and worktree,
  and `new` without `--workspace` warns on a mainline checkout (T070).
- **`autopilot merged` for a branch whose task was discarded on it.** The content checks now run for
  a head whose row is `✅` or `❌`, and a proven merge reports `closed` (`done` or `discarded`),
  `confirmations.row_discarded_on_mainline`, and is recorded with that `status`. A recorded discard
  merge makes the task `discarded`, never `done-merged`, and the task's newest record decides;
  `--cleanup` removes the worktree and local branch of a merged discarded branch as for a done one
  (T067).
- **`autopilot next` skips a task closed on an unpulled mainline.** A candidate whose row is `✅` or
  `❌` on the local mainline or `<remote>/<mainline>` but still `⬜` in the checkout — a merge that
  was not pulled — is reported in `skipped` as `done-merged` or `discarded` instead of being
  dispatched again; `autopilot status` no longer reads a task as closed on one mainline ref when the
  other has a `Reopens: <ID>` commit that ref lacks (T064).
- **Chosen resource values for checks.** `taskrail checks <ID> --resource NAME=VALUE` passes a pool
  value to the checks of a lane whose values were released, refusing one another lane holds
  (exit 4), so the orchestrator's hand-off and after-merge re-runs need no environment prefix
  (T066).
- **`autopilot close` abandons a run.** `taskrail autopilot close <R> --reason …` records who closed
  the run, when and why, and releases its dispatches and resources. `next` then ignores the run, so
  its lanes, group places and resource values are free again, and `status` lists it only when named
  with `--run`. `next --run`, `lane`, `decision` and `claim --run` refuse a closed run with exit 5.
  Claims naming the run are kept and reported, for the human to release (T048).
- **A stacked task keeps its fork point after `done`.** `claim <ID> --run R` also keeps the
  claim's `base` in the run's lane, and `autopilot merged` reads it after a live claim and before
  `merge-base` (`fork_source: "run-base"`), so a dependent whose dependency was rebased at hand-off
  still gets its `git rebase --onto` command (T047).
- **Branch records across clones.** With `[git].branch_record_remote` set, a task's branch record
  is pushed as `refs/taskrail/branches/<ID>` by `branch`, `claim` and `new --workspace --branch`,
  and fetched by `claim`, `branch`, `new --workspace`, `review` and `show`/`list`/`next --fetch`,
  so another clone resolves a renamed branch; the later record wins, and failures only warn (T036).
- **Allowed kinds.** `[kinds].allowed` in config restricts a repository to a closed set of task
  kinds; `validate` rejects tasks of any other kind with `task-kind-disallowed` (T018).
- **Prior work in `show`.** `prior_work` reports an existing artifact, the task branch, and
  commits whose subject names the task, so an executor notices earlier attempts; it never blocks.
- **Each mainline's own remote.** `show`, `new --workspace` and `review` take the base, fetch, push and pull request link from `branch.<mainline>.remote` when it names a configured remote, and report it as `remote` and `remote_source`. Behaviour change: this tracking config now wins over `[review].remote`, which becomes the fallback.
- **Column aliases.** `[columns].aliases` maps a core column onto a repository's own header,
  such as `Pts = "Size"`, so a backlog keeps its established headers (T021).
- **Skills follow the allowed kinds.** `init` and `upgrade` install a shipped executor skill only
  when a kind the repository resolves uses it, and remove unedited copies that are no longer
  used, except while kind resolution reports errors (T025).
- **`new --column` refuses every core column.** `--column` for `✓`, `ID`, `Kind`, `Depends On`,
  `Title`, `Pts` or `Description`, in any letter case and aliased or not, now exits 2 and names
  the flag that fills it. Behaviour change: it used to overwrite `--kind`, `--title` or `--pts`,
  silently drop `ID` and `✓`, or report a missing column for another letter case (T026).
- **An unreadable `installed.json` stops `init` and `upgrade`.** A manifest with merge-conflict
  markers, invalid JSON, a value that is not an object, bytes that are not UTF-8, or that cannot
  be read at all now makes both commands exit 2, name the file and write nothing, `--force`
  included. Behaviour change: `init` used to overwrite it, dropping the recorded integrations,
  extras and digests, and `upgrade` reported it missing (exit 3) or crashed (T027).
- **Stacked bases and `done-branch`.** A task `✅` only at its own branch tip, not on the
  mainline, is `done-branch`: `next` never offers it and `claim` refuses it. A dependent of one
  such task branches from that branch — `show`'s `base` (now with `commit` and `dependency`),
  `new --workspace` and `review`'s `rebase.dependency` — while two or more make it `blocked`.
  Claims record `base` with its fork point, and ignore unknown keys when read (T017).
- **A reopen clears `done-branch`.** A task reopened on its mainline is no longer `done-branch`
  because its old branch, or that branch's remote copy, still says `✅`: a tip counts only if it
  contains every mainline commit with a `Reopens: <ID>` trailer, so `next` offers the task and
  `claim` accepts it again, while a branch done after the reopen is `done-branch` as before (T034).
- **Conditional stages.** A `[[stage]]` with `column` and `match` applies only to tasks whose
  custom column matches, case-insensitively, and one with `judgement = true` is left to the
  executor; `show --json` reports `column`, `match`, `judgement` and a boolean `applies` for each
  stage, and `validate` reports an undeclared column as `stage-column-unknown` (T020).
- **Named and renamed task branches.** `taskrail branch <ID> <NAME>` names a task's branch or
  renames it with `git branch -m`, and `new --workspace --branch NAME` creates one under a chosen
  name. The name is recorded in the git common directory and outlives `done`, so `show`, `review`,
  `done-branch`, a dependent's base, prior work and the claim all follow it; `show` adds
  `branch_source` and reports the worktree the branch is checked out in. `claim` records the
  template name it is claimed on, so a hand-edited title no longer moves the branch, and warns
  when claimed on another branch. A pushed branch is renamed only with `--force`, and the remote
  is never changed (T019).
- **Autopilot runs.** `[autopilot]` in config (the single-value keys of DESIGN.md §12.9);
  `autopilot start --count N` creates a local run file under the git common directory and is
  refused with exit 5 until `[autopilot].enabled` is true; `claim --run` ties a lane's claim to a
  run; `autopilot lane` and `autopilot decision` record lanes, hand-offs and run-level decisions;
  and `autopilot status` derives every run task's state with idle lanes, files touched by more
  than one lane and the hand-off queue (T029).
- **Routes match like stage predicates.** A `[[route]]`'s `when` values may be lists, and routes
  report `route-unreachable` (warning) when an earlier route always pre-empts them. Behaviour
  change: columns resolve and values compare case-insensitively after trimming, so a task whose
  cell differs from a route value only in letter case or padding now takes that route instead of
  the kind's `skill`, and of two routes differing only in case the first now wins for both; `""` as
  a value is `kind-invalid`; and a route on a column `[columns].custom` does not declare, a core
  column or an alias is the error `route-column-unknown`, which replaces the warning
  `route-column-undeclared` (T035).
- **Forced releases of remote claims.** With `claim_remote` set, `release --force`, `done`, `discard`
  and `claim --takeover` delete the remote claim with a lease on its recorded commit instead of
  exiting 2 with `stale info`. When the delete still fails, `done` and `discard` say the row was
  written and name `taskrail release <ID> --force` as the retry; a claim record without its pushed
  commit is refused with the ref to delete by hand (T037).
- **`autopilot next` dispatches lanes.** `taskrail autopilot next --run R` returns the tasks to start
  now — `taskrail next`'s order, within `max_lanes`, the run's count and kinds, and the
  `[[autopilot.group]]` limits — with `show`'s fields and one value of each `[[autopilot.resource]]`
  per lane, records the dispatch in the run and releases the values of lanes that ended; without
  `--run` it is a preview. `autopilot status` reports a dispatched, unclaimed task as `dispatched`,
  and `autopilot lane --group` exits 2 unless the name is a configured judgement group (T030).
- **Autopilot notifications and escalation flags.** `autopilot notify --event … --run R [--task ID]
  [--message …]` runs `[autopilot].notify` through the shell for the events in `notify_on`, with a
  message on stdin and `TASKRAIL_EVENT`, `TASKRAIL_RUN` and `TASKRAIL_TASK` set; a failing or
  hanging command is reported and never blocks (exit 0). `autopilot lane --gate STAGE` records the
  stage a lane is stopped at, and `autopilot status` flags each lane with `governing_touched` (files
  matching `[autopilot].governing` paths or globs), `escalate_gate` (a `kind:stage` listed in
  `escalate_gates`) and `escalation` (T032).
- **Merge detection by content.** `autopilot merged <ID>` runs `git fetch --prune`, then proves a
  finished task branch is in its mainline by ancestry, a first-parent commit with the same tree,
  the same patch-id, or a no-op `git merge-tree`, so squash merges are found; the `✅` row and an
  `(ID)` title are reported only as confirmations. A proven merge is recorded in the runs holding
  the task, and `autopilot status` counts it as `done-merged` while its commit stays on the
  mainline. `--cleanup` then removes the task's worktree and local branch, refusing with exit 5
  when the merge is unproven or the worktree has uncommitted or untracked files, is locked, is the
  main worktree or holds the current directory. Stacked dependents are listed with their
  `git rebase --onto` command (T031).
- **Import a table-based backlog.** `taskrail import <file>` converts a Markdown backlog made of
  task tables under headings, with no `## Epics` table, into one `validate` accepts: headings
  become epics, `--column`, `--status`, `--kind` and `--default-kind` map its headers and values,
  and IDs, row order, prose and escaped pipes are kept byte for byte. It is a dry run printing the
  result unless `--write`, refuses unmapped values with exit 5, and a second run changes nothing
  (T005).
- **Task branches without an upstream.** `new --workspace` and the core skill's workspace step
  create the task branch with `--no-track`, so it no longer tracks the mainline or a dependency's
  branch it started from, and a plain `git push` cannot land on them; `review --publish` still
  sets the task's own remote branch as upstream. A branch created earlier keeps tracking its base
  until `git branch --unset-upstream` is run on it (T038).
- **The `taskrail-autopilot` skill.** `init` and `upgrade` install it in every repository, whatever
  `[kinds].allowed` says. It makes the agent the orchestrator of a run the human asked for with a
  task count, and stops when `autopilot start` exits 5: dispatch with `autopilot next`, a lane brief
  template, gate criteria per gate type, decision records written before each answer, escalation,
  the three known conflict classes, sequential hand-off and follow-through with `autopilot merged`.
  Installed skills now include every file of a skill directory, such as `references/`, as managed
  files, and the agent notes in `integrations/<agent>.md` are split per skill by
  `<!-- taskrail:skill <name> -->`, so the core skill's notes are unchanged and the autopilot skill
  gets its own Claude Code and OpenCode notes (T024).
- **Reopens without a trailer.** `validate` reads the latest 500 commits that change backlog files
  and warns with `reopen-untraced` for a task pending in the working tree whose latest move from
  `✅` or `❌` back to `⬜` no commit since records with a `Reopens: <ID>` trailer, since the rebase
  rule and `done-branch` detection cannot see such a reopen. The exit code is unchanged;
  `--history-limit N` and `--no-history` bound or skip the check, and `--json` reports what was
  examined in `history` (T012).
- **Edit existing task rows.** `taskrail edit <ID>` changes a task's title, points, dependencies,
  description, kind or custom columns, one cell each and validated before anything is written.
  It refuses closed, `done-branch` and someone else's claimed tasks without `--force`, keeps a
  recorded branch name, and records the old template name when a title change would move a branch
  that exists. The core skill points to it instead of hand edits (T014).
- **A git merge driver for backlog tables.** `init --merge-driver` marks the backlog, epic and
  artifact index files in `.gitattributes` and defines `taskrail merge-driver` in the clone's git
  config, so `git merge`, `rebase` and `cherry-pick` unite table rows by ID, merge a row's cells
  three-way, keep `✅` unless the other side has a `Reopens:` commit, and leave markers only around
  rows and text that really conflict; everything else merges as git would. `upgrade`, `epic add
  --own-file` and `epic split` keep the block current (T004).
- **Changelog bullets in the merge driver.** The driver also merges tight bullet lists under the
  same heading bullet by bullet: bullets both sides add are all kept, current side first; a bullet
  one side moved appears once, where it moved; markers remain only around a bullet edited
  differently on both sides, or edited on one and deleted on the other; lists it cannot match are
  left to git. `init --merge-driver` and `upgrade` add every `CHANGELOG.md` to the `.gitattributes`
  block, and any file with its own `merge=taskrail` line gets the same merge (T040).
- **The GitHub workflow fetches full history.** The workflow `init --github-workflow` writes now
  checks out with `fetch-depth: 0`, so `validate`'s reopen check examines the history instead of
  a single commit. `upgrade` rewrites an unedited workflow; one edited locally is reported as
  skipped — add `fetch-depth: 0` to its checkout step by hand, or pass `--force` (T039).
- **`autopilot lane --gate close`.** `close` names the stop after `taskrail done` for a task of any
  kind, even one whose kind is not defined, so the orchestrator can record the close it reviews;
  the other `--gate` rules are unchanged, and an unknown stage's message now lists `close` too. The
  `taskrail-autopilot` skill records the close stop this way (T050).
- **No governing escalation after `done-branch`.** `autopilot status` no longer lists `governing`
  in `escalation`, nor prints `ESCALATE: governing …`, for a `done-branch` or `handed-off` task, as
  it already dropped `escalate_gate`; `governing_touched` still lists the paths. The autopilot
  skill's close review escalates a governing path the task's decision record does not show
  escalated (T049).
- **A closing lane stays `running`.** Between `taskrail done` and its commit, `autopilot status`
  reports the lane `running` — the `✅` in the working tree of its branch's worktree counts once the
  claim is released — with its `touched` files, instead of `pending`. `autopilot next` skips any
  candidate that still occupies a lane (`running`, `gate` or `escalated` without a claim, as well as
  `dispatched`), with the reason `<state> in run R`, so such a task is not dispatched twice (T054).
- **Autopilot skill text from the T033 trial.** The `taskrail-autopilot` skill hands a branch off
  with its ID, branch, pull request title, body and link; refills a lane once its close is
  reviewed instead of at hand-off; says that `taskrail new` IDs never collide across lanes and that
  an unclaimed dispatch expires after `[git].claim_grace_minutes`; and resumes a run from a new
  session by lane handle, restarting a lane from its branch with a new restart section of the lane
  brief when the handle no longer reaches it (T055).
- **`taskrail checks <ID>`.** Runs a task's configured checks — every applying stage's, or those of
  `--stage` or `--check` — in its worktree, found from its claim or its checked-out branch, with
  the worktree's own configuration and its autopilot lane's resources as
  `TASKRAIL_RESOURCE_<NAME>`, from anywhere in the clone; every check runs, `--json` captures each
  one's output, and a failing check exits 6. The core skill runs stage checks this way and lists
  exit 6, and the Claude Code notes describe a command shape an allowlist can match: one command
  per call, absolute paths, `git -C` and `--root` instead of `cd … &&` chains (T052).
- **A stable hand-off queue.** `autopilot status` orders `handoff.queue` by when each task was
  finished — the author time of the commit that turned its row ✅ on its branch — instead of the
  branch tip's commit time, so rebasing a waiting branch or committing a decision record on it no
  longer moves the task to the back, and a branch left only on the remote no longer jumps to the
  front (T053).
- **OpenCode note on escalations during blocking batches.** The `taskrail-autopilot` skill's
  OpenCode note has the orchestrator end its turn with the question at an escalation instead of
  starting another blocking batch of task calls, and record handles and check `silent` lanes as
  soon as a batch returns (T056).
- **Known conflict classes apart in `autopilot status`.** Files several lanes touch that belong to a
  known conflict class — backlog and epic files, artifact and decision-record indexes, changelogs,
  and `.taskrail/installed.json` with the skill copies it records — are reported in
  `known_overlaps`, each with its `class` and `tasks`, and printed under their own heading after
  the real overlaps (T051).
- **`[autopilot].read_first`.** The documents the orchestrator reads first to answer gates now have
  their own key, so `governing` only escalates; without the key they are the `governing` entries.
  `autopilot status` reports `read_first` and `read_first_missing` (entries that match nothing), and
  the `taskrail-autopilot` skill reads the governing documents from them (T061).
- **`autopilot approve-governing`.** Records a governing edit the human approved: each approved
  path is stored in the task's lane with the blob ID of its content (the worktree file, else the
  branch tip). `autopilot status` reports those files in `governing_approved` and raises
  `governing` only for governing files not approved, naming only them in `ESCALATE: governing …`;
  a later change to an approved file flags it again. The autopilot skill records approvals this
  way (T059).
- **A discard on an unmerged task branch closes the task.** A task whose row is `❌` at the tip of
  its task branch, and closed on neither mainline ref, is `discarded-branch`: `next` and
  `autopilot next` no longer offer it, `claim` refuses it (exit 5), `edit` refuses it without
  `--force`, and it frees its place in the run's count. `autopilot status` reports it
  `discarded-branch`, keeps a lane between `discard` and its commit `running`, and reports a task
  `❌` on the local or remote mainline `discarded`. Behaviour change: such a task used to read
  `pending` until merged and pulled (T062).
- **The autopilot text names `taskrail checks`.** The lane brief tells a lane to run its checks
  with `taskrail checks <ID>`, which passes its resource values itself, and the
  `taskrail-autopilot` skill's gate, rebase, hand-off and after-merge steps re-run a lane's checks
  with it (T063).
- **A branch whose task was discarded on it is handed off.** `autopilot status` queues a
  `discarded-branch` task with the `done-branch` ones, ordered by the author time of its discard
  commit, reports its `touched` files (so it joins `overlaps`) and its `governing_touched` without
  the `governing` escalation. `autopilot lane <ID> --state handed-off` accepts it; it keeps reading
  `discarded-branch`, and `handoff.in_review` names it until its `❌` reaches a mainline ref.
  `taskrail review` prepares and publishes a task discarded on its branch, with `chore` as the
  default title type (T065).

## 0.1.0

Published from the repository taskrail was extracted from, as `taskrail-v0.1.0`; this repository
has no `v0.1.0` tag.

First release.

- **Backlog format.** `TODO.md` with an `## Epics` table; each epic inline or in its own file;
  task tables with free column order, custom columns, and `⬜` / `✅` / `❌` statuses. Several
  backlogs per repository, each with its ID prefix, mainline and allowed dependency directions.
- **Validation and queries.** `validate` with file and line for every problem; `list`, `show`
  and `next` with computed `pending`, `claimed`, `blocked`, `done` and `discarded` states, and
  `--json` throughout.
- **Task kinds as data.** Core kinds `bug`, `chore`, `feature` and `spike`, each with stages,
  gates, an artifact and an executor skill; repositories add kinds under `.taskrail/types/` or
  override them under `.taskrail/overrides/`, including routing on a column.
- **Claims and IDs.** Exclusive claims shared by every worktree of a clone, optionally mirrored
  to a remote ref; IDs reserved under a lock across all branches.
- **Write commands.** `new` (with `--workspace` to start the task on its own branch), `done`,
  `discard`, `reopen`, `epic add` and `epic split` — one-cell or one-row diffs, validated before
  anything is written.
- **Review hand-off.** `review` fetches, picks the rebase base, pushes the task branch and
  prints a pull or merge request link with a Conventional Commits title for GitHub, GitLab,
  Gitea, Forgejo or a URL template.
- **Installation.** Idempotent `init` for Claude Code and OpenCode, a committed wrapper that
  runs the pinned version (falling back to `uvx`), `upgrade`, `self upgrade`, and optional
  GitHub workflow and pre-commit hook running `validate`.
