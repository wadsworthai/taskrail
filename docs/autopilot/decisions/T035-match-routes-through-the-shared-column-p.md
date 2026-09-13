# T035 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T035-match-routes-through-the-shared-column-p.md` (commit
`ed0ee55`), its eleven acceptance criteria, and the lane's evidence of how existing routes would
re-route (`API`/`api`/`Api`, padded values, a lower-case column key, a core column alias, an
undeclared but present column, and a list value rejected today).

Context for every behaviour change below: no consumer project has adopted taskrail yet (T003 is
pending), and the only shipped routes, in `examples/spec-kit`, use `—` and `*`, which keep their
meaning. Changing route semantics now costs nothing outside this repository.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| D1 | Shape of `when` | keep the table, each entry a column predicate with a string or list · `column`/`match` keys · strings only | **keep the table; values may be lists** | One syntax that still expresses several columns, with the same value semantics as stages. |
| D2 | Letter case and trimming of route values and column keys | case-insensitive and trimmed · exact · per-kind setting | **case-insensitive and trimmed**, flagged "Behaviour change" in the CHANGELOG with the re-routing effects | Removes the trap T020's decision 6 opened this task for; a setting would only preserve it. |
| D3 | `""`, blank or empty-list route values | `kind-invalid` · accept `""` as empty | **`kind-invalid`, as for stage `match`** | `""` was never documented for routes; `—` and `-` are. One parser, one set of errors. |
| D4 | Route on an undeclared column | `route-column-unknown` error, kind stays loaded · error for core/alias only · warning | **`route-column-unknown` error, kind stays loaded; remove `route-column-undeclared`** | Aligns with `stage-column-unknown`; a route on an undeclared column is a configuration mistake, and the backlog's own `column-undeclared` warning already asks for the declaration. |
| D5 | `routes` JSON | one value as a string, several as a list, declared column spelling · always a list | **as recommended** | Existing consumers of the single-value form keep working. |
| D6 | Ordering and dead routes | first match wins plus a `route-unreachable` warning · CHANGELOG only | **first match wins, plus `route-unreachable`** | `validate` is where a consumer sees a route that case-insensitivity made dead. It must never report a route that some task could still reach: when unsure, do not warn, and cover `*` versus `—` in tests. |

Not marked breaking: taskrail is 0.x and earlier behaviour changes (T026, T027) were released the
same way, each flagged in the CHANGELOG. Plan approved. The lane must remove its scratch
repositories under a temporary directory when it no longer needs them.

## implement gate

Reviewed: commit `fd0511c` (`predicates.py` `parse_match` and `covers`, `kinds.py` routes,
`project.py`, DESIGN.md §5.1, §5.4, §5.5, README, CHANGELOG, `tests/test_routes.py`). Re-ran
`uv run pytest -q` in the lane's worktree: 392 passed. Against the
unchanged source the new tests gave 42 failed, 17 passed, and the 17 are the behaviour meant to
stay. `covers` is exact for these values — a `*` is covered only by `*`, and an earlier route with
a column the later one does not constrain never covers it — and an exhaustive pairwise test over
483 routes and 50 tasks checks that no reachable route is reported.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Follows D1–D6 and the eleven criteria; `parse_column_predicate` keeps its signature and messages. |
| 2 | New DESIGN.md §5.5 *Routes* | keep · fold into §5.1 | **keep** | Routes now have their own rules and three issue codes; §5.4 stays about stages. |

## rebase after T019 and T029

T019 (`1543057`) and T029 (`45eb96f`) were squash-merged into `main`. The branch was rebased onto
`origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `docs/features/README.md`, `docs/autopilot/decisions/README.md`, `CHANGELOG.md` | keep both · stop | **keep both** | Rows and bullets added on both sides. |
| 2 | Conflict in `TODO.md` | union by ID, `✅` wins · stop | **union by ID** | T019, T029 and T035 `✅` on their sides; no `Reopens:` commit for any. |

After the rebase: no conflict markers, `pytest -q` 469 passed, `taskrail validate` 0 errors,
`upgrade` reports nothing to create or update.
