# RelayLM agent instructions

These instructions apply to the entire repository.

## Bare continuation commands

When the user says only one of the following, treat it as an execution command rather than a request for advice:

```text
次に進めて
進めて
続けて
次へ
```

Before acting, read and follow:

1. `skills/relaylm-stable-implementation/SKILL.md`;
2. `docs/planning/workstream-orchestration.md`;
3. `docs/PROJECT_STATUS.md`;
4. `docs/architecture/project_execution_plan.md`;
5. the owning ADRs, contracts, plans, code, tests, workflows, review threads, and registries for the selected work.

Refresh current `main`, open PRs, checks, reviews, exact heads, mergeability, and lane capacity. Do not rely only on conversation memory or an old handoff.

Converge existing PRs before opening overlapping replacements. Advance the earliest executable Lane C item and eligible path- and authority-disjoint Lane D or Lane R work. Do not ask the user to choose when repository authorities resolve the choice.

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

When the merge gate passes and the user has not said `レビューだけ` or `マージしないで`, merge using expected-head protection where available, verify the resulting `main`, perform post-merge convergence, release the lane slot, and select the next executable action.

Never claim completion without fresh evidence. Never promise hidden background work.
