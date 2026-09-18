# Autopilot decisions

| Task | Title | Document |
|------|-------|----------|
| T018 | Restrict the task kinds a repository allows | [T018-restrict-the-task-kinds-a-repository-all.md](T018-restrict-the-task-kinds-a-repository-all.md) |
| T023 | Report signs of prior work on a task in show | [T023-report-signs-of-prior-work-on-a-task-in.md](T023-report-signs-of-prior-work-on-a-task-in.md) |
| T022 | Use each mainline's own remote in review | [T022-use-each-mainline-s-own-remote-in-review.md](T022-use-each-mainline-s-own-remote-in-review.md) |
| T021 | Map a repository's column names onto taskrail's columns | [T021-map-a-repository-s-column-names-onto-tas.md](T021-map-a-repository-s-column-names-onto-tas.md) |
| T025 | Skip installing skills for kinds a repository does not allow | [T025-skip-installing-skills-for-kinds-a-repos.md](T025-skip-installing-skills-for-kinds-a-repos.md) |
| T026 | Refuse --column for core columns in new | [T026-refuse-column-for-core-columns-in-new.md](T026-refuse-column-for-core-columns-in-new.md) |
| T007 | Design taskrail's autopilot from existing orchestrators | [T007-design-taskrail-s-autopilot-from-existin.md](T007-design-taskrail-s-autopilot-from-existin.md) |
| T028 | Write the autopilot design into DESIGN.md | [T028-write-the-autopilot-design-into-design-m.md](T028-write-the-autopilot-design-into-design-m.md) |
| T027 | Stop init and upgrade on an unreadable installed.json | [T027-stop-init-and-upgrade-on-an-unreadable-i.md](T027-stop-init-and-upgrade-on-an-unreadable-i.md) |
| T017 | Branch a task from its single unmerged dependency | [T017-branch-a-task-from-its-single-unmerged-d.md](T017-branch-a-task-from-its-single-unmerged-d.md) |
| T020 | Run stages conditionally on a column or the executor's judgement | [T020-run-stages-conditionally-on-a-column-or.md](T020-run-stages-conditionally-on-a-column-or.md) |
| T019 | Let the executor name or rename a task branch | [T019-let-the-executor-name-or-rename-a-task-b.md](T019-let-the-executor-name-or-rename-a-task-b.md) |
| T029 | Add the autopilot configuration, runs, and the start, lane and status commands | [T029-add-the-autopilot-configuration-runs-and.md](T029-add-the-autopilot-configuration-runs-and.md) |
| T035 | Match routes through the shared column predicate | [T035-match-routes-through-the-shared-column-p.md](T035-match-routes-through-the-shared-column-p.md) |
| T034 | Clear done-branch for a task reopened on its mainline | [T034-clear-done-branch-for-a-task-reopened-on.md](T034-clear-done-branch-for-a-task-reopened-on.md) |
| T037 | Delete remote claims with a lease on their recorded commit | [T037-delete-remote-claims-with-a-lease-on-the.md](T037-delete-remote-claims-with-a-lease-on-the.md) |
| T036 | Mirror branch records to a remote ref | [T036-mirror-branch-records-to-a-remote-ref.md](T036-mirror-branch-records-to-a-remote-ref.md) |
| T030 | Dispatch autopilot lanes with autopilot next | [T030-dispatch-autopilot-lanes-with-autopilot.md](T030-dispatch-autopilot-lanes-with-autopilot.md) |
| T032 | Add autopilot notify and the escalation flags in autopilot status | [T032-add-autopilot-notify-and-the-escalation.md](T032-add-autopilot-notify-and-the-escalation.md) |
| T031 | Detect squash merges by content and follow through with autopilot merged | [T031-detect-squash-merges-by-content-and-foll.md](T031-detect-squash-merges-by-content-and-foll.md) |
| T005 | Import tasks from table-based backlogs without epics | [T005-import-tasks-from-table-based-backlogs-w.md](T005-import-tasks-from-table-based-backlogs-w.md) |
| T038 | Create task branches without tracking the mainline | [T038-create-task-branches-without-tracking-th.md](T038-create-task-branches-without-tracking-th.md) |
| T024 | Write the taskrail-autopilot skill with Claude Code and OpenCode notes | [T024-write-the-taskrail-autopilot-skill-with.md](T024-write-the-taskrail-autopilot-skill-with.md) |
| T012 | Flag reopened tasks committed without a Reopens trailer | [T012-flag-reopened-tasks-committed-without-a.md](T012-flag-reopened-tasks-committed-without-a.md) |
| T014 | Add an edit command for existing task rows | [T014-add-an-edit-command-for-existing-task-ro.md](T014-add-an-edit-command-for-existing-task-ro.md) |
| T004 | Add a git merge driver for status cells and appended rows | [T004-add-a-git-merge-driver-for-status-cells.md](T004-add-a-git-merge-driver-for-status-cells.md) |
| T040 | Merge appended changelog bullets without duplicating moved ones | [T040-merge-appended-changelog-bullets-without.md](T040-merge-appended-changelog-bullets-without.md) |
| T039 | Fetch full history in the generated GitHub workflow | [T039-fetch-full-history-in-the-generated-gith.md](T039-fetch-full-history-in-the-generated-gith.md) |
| T033 | Trial the autopilot on a real backlog with each supported agent | [T033-trial-the-autopilot-on-a-real-backlog-wi.md](T033-trial-the-autopilot-on-a-real-backlog-wi.md) |
| T050 | Accept --gate close for the stop after done | [T050-accept-gate-close-for-the-stop-after-don.md](T050-accept-gate-close-for-the-stop-after-don.md) |
| T049 | Stop flagging governing paths once a task is done on its branch | [T049-stop-flagging-governing-paths-once-a-tas.md](T049-stop-flagging-governing-paths-once-a-tas.md) |
| T060 | Remove DESIGN.md and CLAUDE.md from the autopilot's governing paths | [T060-remove-design-md-and-claude-md-from-the.md](T060-remove-design-md-and-claude-md-from-the.md) |
| T054 | Keep a closing lane from reading as pending between done and its commit | [T054-keep-a-closing-lane-from-reading-as-pend.md](T054-keep-a-closing-lane-from-reading-as-pend.md) |
| T055 | Fix the autopilot skill text found wrong in the T033 trial | [T055-fix-the-autopilot-skill-text-found-wrong.md](T055-fix-the-autopilot-skill-text-found-wrong.md) |
| T052 | Add taskrail checks for a task and a Claude Code note on command shape | [T052-add-taskrail-checks-for-a-task-and-a-cla.md](T052-add-taskrail-checks-for-a-task-and-a-cla.md) |
| T053 | Order the autopilot hand-off queue by completion, not branch tip time | [T053-order-the-autopilot-hand-off-queue-by-co.md](T053-order-the-autopilot-hand-off-queue-by-co.md) |
| T056 | Add an OpenCode note on escalations during blocking lane batches | [T056-add-an-opencode-note-on-escalations-duri.md](T056-add-an-opencode-note-on-escalations-duri.md) |
| T048 | Add autopilot close to abandon a run | [T048-add-autopilot-close-to-abandon-a-run.md](T048-add-autopilot-close-to-abandon-a-run.md) |
| T051 | Label overlaps in known conflict-class files | [T051-label-overlaps-in-known-conflict-class-f.md](T051-label-overlaps-in-known-conflict-class-f.md) |
| T047 | Keep a stacked task's fork point after done | [T047-keep-a-stacked-task-s-fork-point-after-d.md](T047-keep-a-stacked-task-s-fork-point-after-d.md) |
| T061 | Separate the documents the orchestrator reads first from the paths that escalate | [T061-separate-the-documents-the-orchestrator.md](T061-separate-the-documents-the-orchestrator.md) |
| T059 | Record an approved governing edit so autopilot status stops flagging it | [T059-record-an-approved-governing-edit-so-aut.md](T059-record-an-approved-governing-edit-so-aut.md) |
| T062 | Treat a task discarded on its unmerged branch as closed in status and next | [T062-treat-a-task-discarded-on-its-unmerged-b.md](T062-treat-a-task-discarded-on-its-unmerged-b.md) |
| T063 | Name taskrail checks in the lane brief and the autopilot skill's re-run steps | [T063-name-taskrail-checks-in-the-lane-brief-a.md](T063-name-taskrail-checks-in-the-lane-brief-a.md) |
| T064 | Skip a task merged on the remote mainline but not pulled in autopilot next | [T064-skip-a-task-merged-on-the-remote-mainlin.md](T064-skip-a-task-merged-on-the-remote-mainlin.md) |
| T065 | Hand off a branch whose task was discarded on it | [T065-hand-off-a-branch-whose-task-was-discard.md](T065-hand-off-a-branch-whose-task-was-discard.md) |
| T066 | Pass chosen resource values to taskrail checks for a lane whose values were released | [T066-pass-chosen-resource-values-to-taskrail.md](T066-pass-chosen-resource-values-to-taskrail.md) |
| T067 | Detect and clean up a merged branch whose task was discarded on it | [T067-detect-and-clean-up-a-merged-branch-whos.md](T067-detect-and-clean-up-a-merged-branch-whos.md) |
| T069 | Warn in the README that taskrail is experimental and AI-developed | [T069-warn-in-the-readme-that-taskrail-is-expe.md](T069-warn-in-the-readme-that-taskrail-is-expe.md) |
| T070 | Detect a task whose row is missing from its base and carry the row into its workspace | [T070-detect-a-task-whose-row-is-missing-from.md](T070-detect-a-task-whose-row-is-missing-from.md) |
| T071 | Run the autopilot on named tasks, including ones whose workspace new --workspace prepared | [T071-run-the-autopilot-on-named-tasks-includi.md](T071-run-the-autopilot-on-named-tasks-includi.md) |
| T072 | Report a task's worktree path in one form whichever checkout runs the command | [T072-report-a-task-s-worktree-path-in-one-for.md](T072-report-a-task-s-worktree-path-in-one-for.md) |
| T073 | Create a task worktree under the main checkout when new or workspace runs inside another worktree | [T073-create-a-task-worktree-under-the-main-ch.md](T073-create-a-task-worktree-under-the-main-ch.md) |
| T074 | Refuse merged --cleanup for a worktree that contains other registered worktrees | [T074-refuse-merged-cleanup-for-a-worktree-tha.md](T074-refuse-merged-cleanup-for-a-worktree-tha.md) |
| T075 | Report and create task worktrees outside the bare directory of a bare repository | [T075-report-and-create-task-worktrees-outside.md](T075-report-and-create-task-worktrees-outside.md) |
| T076 | Name wadsworthai/taskrail as the canonical repository in the CLI, skills and docs | [T076-name-wadsworthai-taskrail-as-the-canonic.md](T076-name-wadsworthai-taskrail-as-the-canonic.md) |
| T077 | Release v0.2.0 from the canonical repository | [T077-release-v0-2-0-from-the-canonical-reposi.md](T077-release-v0-2-0-from-the-canonical-reposi.md) |
| T078 | Bump main to 0.3.0.dev0 after the v0.2.0 tag | [T078-bump-main-to-0-3-0-dev0-after-the-v0-2-0.md](T078-bump-main-to-0-3-0-dev0-after-the-v0-2-0.md) |
| T079 | Write the current-branch workflow into DESIGN.md | [T079-write-the-current-branch-workflow-into-d.md](T079-write-the-current-branch-workflow-into-d.md) |
| T082 | Add a decisions gate that stops for each decision instead of each stage | [T082-add-a-decisions-gate-that-stops-for-each.md](T082-add-a-decisions-gate-that-stops-for-each.md) |
| T080 | Work a task on the checked-out branch with task_branch = current | [T080-work-a-task-on-the-checked-out-branch-wi.md](T080-work-a-task-on-the-checked-out-branch-wi.md) |
| T081 | Commit a task's changes only when it is done with commit = on-done | [T081-commit-a-task-s-changes-only-when-it-is.md](T081-commit-a-task-s-changes-only-when-it-is.md) |
| T083 | Close a current-branch task without fetch, rebase or publish | [T083-close-a-current-branch-task-without-fetc.md](T083-close-a-current-branch-task-without-fetc.md) |
| T084 | Teach the skills the current-branch workflow, on-done commits and decisions gates | [T084-teach-the-skills-the-current-branch-work.md](T084-teach-the-skills-the-current-branch-work.md) |
| T085 | Release v0.3.0 | [T085-release-v0-3-0.md](T085-release-v0-3-0.md) |
| T086 | Bump main to 0.4.0.dev0 after the v0.3.0 tag | [T086-bump-main-to-0-4-0-dev0-after-the-v0-3-0.md](T086-bump-main-to-0-4-0-dev0-after-the-v0-3-0.md) |
| T087 | Decide whether the design principles govern new work only or also what exists | [T087-decide-whether-the-design-principles-gov.md](T087-decide-whether-the-design-principles-gov.md) |
| T089 | Decide whether to split DESIGN.md by topic for what the orchestrator reads first | [T089-decide-whether-to-split-design-md-by-top.md](T089-decide-whether-to-split-design-md-by-top.md) |
| T088 | Measure the CLI and configuration surface against YAGNI and report what has no consumer | [T088-measure-the-cli-and-configuration-surfac.md](T088-measure-the-cli-and-configuration-surfac.md) |
| T090 | Record the scope, reach and refusal rules for the design principles in CLAUDE.md | [T090-record-the-scope-reach-and-refusal-rules.md](T090-record-the-scope-reach-and-refusal-rules.md) |
| T091 | Tell every executor to read the repository's agent instruction files before it plans | [T091-tell-every-executor-to-read-the-reposito.md](T091-tell-every-executor-to-read-the-reposito.md) |
