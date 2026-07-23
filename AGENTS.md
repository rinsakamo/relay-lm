# RelayLM agent instructions

These instructions apply to the entire repository.

## Bare continuation commands are lane-local

When the user says only one of the following, treat it as an execution command rather than a request for advice:

```text
次に進めて
進めて
続けて
次へ
```

A bare continuation command is **lane-local by default**. It advances only the lane, pull request, or bounded work item already established by the current conversation or repository working context.

Resolve the execution scope in this order:

1. an explicit lane, PR, branch, or work item in the current user instruction;
2. the lane declared by the current thread's initial prompt or handoff;
3. the uniquely identified current PR or branch and its lane metadata;
4. a single unambiguous work item already selected in the current conversation.

If these signals do not identify exactly one lane or one bounded PR, fail closed: do not modify, review, comment on, merge, retarget, or create work in any lane. Ask the user to name Lane C, Lane D, Lane R, or a PR.

Before acting, read and follow:

1. `skills/relaylm-stable-implementation/SKILL.md`;
2. `docs/planning/workstream-orchestration.md`;
3. `docs/adr/0008-lane-local-continuation-safety.md`;
4. `docs/PROJECT_STATUS.md`;
5. `docs/architecture/project_execution_plan.md`;
6. the owning ADRs, contracts, plans, code, tests, workflows, review threads, and registries for the selected work.

Refresh current `main`, open PRs, checks, reviews, exact heads, mergeability, and conflicts. Cross-lane state may be read to detect conflicts and dependencies, but a lane-local command does not authorize cross-lane writes or convergence.

Converge the selected lane's existing PR before opening a replacement. After P8, select only the next executable item in the same lane.

## Explicit portfolio commands

Cross-lane execution requires an explicit portfolio instruction such as:

```text
全レーンを進めて
ポートフォリオを進めて
Lane C・D・Rを並行で進めて
```

Only an explicit portfolio command authorizes advancing, reviewing, commenting on, merging, or creating work in more than one lane during the interaction. Portfolio mode still requires path and authority disjointness and the repository's lane-capacity rules.

## Mandatory stable-implementation discipline

All implementation, documentation, cleanup, migration, and correction work must use the repository skill and the P0-P8 lifecycle.

Do not begin substantive implementation before:

- current behavior, callers, authority, state, and recovery are understood;
- invariants and negative cases are written down;
- meaningful implementation alternatives are compared;
- failure points, migration, rollback, and removal gates are defined;
- the No-Patch Gate and Stable-Structure Gate pass;
- the atomic PR boundary and validation matrix are fixed.

## No-patch rule

A small root-cause correction is allowed. A symptom patch or workaround is not.

Prohibited by default:

- caller-, fixture-, test-, or platform-specific bypasses that do not represent the domain rule;
- duplicate semantic authorities, current selectors, write paths, or canonical representations;
- permanent fallback, precedence, dual-read, or dual-write;
- wrapper-only indirection that leaves ownership unchanged;
- swallowed errors or retry loops that hide durable-state disagreement;
- compatibility surfaces without an owner, current consumer, removal gate, and replacement validation;
- weakening tests to fit the implementation;
- direct edits to generated outputs instead of their source authority;
- permanent milestone-oriented production names;
- deferring known in-scope structural debt with “later cleanup”.

When a review exposes an architectural assumption error, repeated special cases, authority duplication, or three failed correction attempts, stop local patching and return to implementation-strategy design.

## Completion and merge

CI success does not replace thorough review or fresh final review. Correct findings at the root, validate the exact head, and repeat final review until clean.

When the merge gate passes and the user has not said `レビューだけ` or `マージしないで`, merge the selected lane's PR using expected-head protection where available, verify the resulting `main`, perform post-merge convergence, release that lane slot, and select the next executable action in the same lane.

Never claim completion without fresh evidence. Never promise hidden background work.