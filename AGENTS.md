# RelayLM agent instructions

These instructions apply to the entire repository.

## Current repository authority overrides bootstrap prompts

Thread initial prompts, handoffs, conversation memory, PR bodies, and historical files are bootstrap orientation only. They never override the current `main` versions of:

1. `AGENTS.md`;
2. `skills/relaylm-stable-implementation/SKILL.md`;
3. `docs/adr/0007-architecture-first-stable-implementation.md`;
4. `docs/adr/0008-lane-local-continuation-safety.md`;
5. `docs/adr/0009-execution-epoch-and-rebootstrap.md`;
6. `docs/contracts/agent-execution-safety.md`;
7. `docs/planning/workstream-orchestration.md`.

A lane started before any of these authorities changed must not continue its old loop by partially applying new wording. Stop branch writes and perform the current execution-epoch re-bootstrap.

## Bare continuation commands are lane-local

Treat these as execution commands:

```text
次に進めて
進めて
続けて
次へ
```

They advance only the lane, PR, branch, or bounded work item already established by the current thread.

Resolve scope in this order:

1. explicit lane, PR, branch, or work item in the current instruction;
2. lane declared by the thread's initial prompt or handoff;
3. uniquely identified current PR or branch and its lane metadata;
4. one unambiguous work item already selected in the conversation.

If this does not identify exactly one lane or one bounded PR, fail closed. Do not modify, review, comment on, merge, retarget, or create work. Ask the user to name Lane C, Lane D, Lane R, or a PR.

Other lanes may be read only for conflicts and dependencies. Converge the selected lane's existing PR before opening a replacement. After P8, select only the next executable item in the same lane.

## Explicit portfolio commands

Cross-lane execution requires an explicit instruction such as:

```text
全レーンを進めて
ポートフォリオを進めて
Lane C・D・Rを並行で進めて
```

Only explicit portfolio mode authorizes advancing, reviewing, commenting on, merging, or creating work in more than one lane. Path and authority disjointness and lane-capacity rules still apply.

## Mandatory execution-epoch re-bootstrap

Before any repository write, review mutation, correction, merge, or ordinary PR metadata change:

1. refresh current `main`, the selected PR, exact head, checks, reviews, threads, mergeability, changed paths, labels, and active workflows;
2. run or reproduce `scripts/relaylm_agent_execution_guard.py` against the current PR body and `origin/main`;
3. verify exactly one current `relaylm-execution-receipt`;
4. verify `bootstrap_main_sha` equals the exact current `origin/main` commit and is an ancestor of the selected head;
5. verify one writer identity and no branch-pushing workflow or transfer PR;
6. verify no `relaylm:p6-stop` label;
7. verify no temporary construction artifact in the proposed final diff.

When the receipt is missing or stale, or the governance epoch changed after the lane began:

- stop every branch writer;
- do not add a corrective patch;
- do not create a temporary validation PR or transfer branch;
- remove or disable branch-pushing automation;
- refresh and incorporate current `main`;
- refresh current authority, callers, workflows, registries, and failure evidence;
- reclassify P0 and P1 and pass P2 again;
- record a new execution receipt before substantive work resumes.

Controlled exceptions while stopped:

- one branch change may only disable branch-writing automation or remove a temporary execution artifact;
- after read-only P0/P1/P2 re-bootstrap, one PR-body edit may add or replace only the execution receipt.

The receipt edit must contain no branch write, review disposition, merge action, title/base change, or unrelated body edit. Run the guard immediately afterward.

Correct implementation evidence may be preserved. Old process state is not grandfathered.

## Authoritative reading order

At every re-bootstrap and before substantive work, read or verify:

1. the current execution authorities listed above;
2. `docs/PROJECT_STATUS.md` for implemented state and caveats;
3. `docs/architecture/project_execution_plan.md` for repository-wide sequencing;
4. `docs/planning/workstream-orchestration.md` and the selected lane's owning plan;
5. the exact ADRs, contracts, code, tests, workflows, registries, review threads, generated surfaces, and operator entry points required by the selected action.

Do not infer current behavior or sequencing from an initial prompt or PR body.

## Single-writer rule

One active PR branch has one logical writer. Test and validation workflows are repository-content read-only.

Prohibited:

- `contents: write` or `git push` in a PR-local construction or validation workflow;
- auto-correct and implementation agents writing the same branch;
- a second PR or branch created only to apply, validate, or transfer a correction;
- automatic retry, rebase, or force-push after a non-fast-forward rejection.

The failure-budget monitor may update only its hidden state comment, execution labels, and Draft state. It must never modify branch content or the PR body.

Immediately before any branch write, fetch the exact head. If it changed from the expected value, stop and re-bootstrap rather than rebasing or retrying.

## Mandatory stable-implementation discipline

All implementation, documentation, cleanup, migration, and correction work uses `relaylm-stable` and the P0-P8 lifecycle.

Do not begin substantive implementation before:

- current behavior, callers, authority, state, and recovery are understood;
- direct, indirect, subprocess, workflow, registry, operator, and documentation invocation roots are enumerated;
- invariants and negative cases are written down;
- meaningful alternatives are compared;
- failure points, migration, rollback, and removal gates are defined;
- the No-Patch Gate and Stable-Structure Gate pass;
- the atomic PR boundary and validation matrix are fixed.

## No-patch rule

A small root-cause correction is allowed. A symptom patch or workaround is not.

Prohibited by default:

- caller-, fixture-, test-, or platform-specific bypasses that do not express the domain rule;
- duplicate semantic authorities, current selectors, writers, or canonical representations;
- permanent fallback, precedence, dual-read, or dual-write;
- wrapper-only indirection that leaves ownership unchanged;
- swallowed errors or retries that hide durable-state disagreement;
- compatibility without owner, current consumer, removal gate, and replacement validation;
- weakening tests to fit implementation;
- editing generated output instead of source authority;
- permanent milestone-oriented production names;
- deferring known in-scope structural debt to later cleanup.

## Mechanical failure budget and P6-STOP

The failure-budget workflow owns consecutive-failure state in one hidden PR comment and mirrors it with exactly one of:

```text
relaylm:failure-1
relaylm:failure-2
relaylm:p6-stop
```

Normalize a signature as:

```text
workflow + failed job + first failed step + bounded conclusion category
```

A new head, renamed workflow, moved command, or prose-only adjustment does not reset materially identical failure state.

The third consecutive identical signature, architectural assumption error, duplicate authority or writer, branch-write collision, branch-writing validation, temporary-artifact recurrence, or temporary transfer PR triggers `P6-STOP`:

- add `relaylm:p6-stop` and make the PR Draft;
- no further branch writes or auto-correct;
- no temporary workflow or transfer PR;
- return to P1 only through current-epoch re-bootstrap;
- clear the stop label only after the new receipt and P2 evidence are reviewed.

Do not reset failure state by renaming a workflow, changing prose, or moving the same patch to another branch.

## Temporary artifact rule

Construction helpers belong outside the repository tree when possible. The final diff must not contain root-level hidden patch scripts, probe workflows, self-deleting refactor workflows, generated syntax-fix scripts, or temporary build/transfer workflows.

A permanent automation requires accepted authority, stable responsibility naming, tests, repository-content read-only operation unless separately governed, and rollback/removal analysis.

## Completion and merge

CI success does not replace thorough review or fresh final review. Correct findings at the root, validate the exact head, and repeat complete-diff review until clean.

Merge only with a current receipt, exact current-main bootstrap, no stop label, no temporary artifact, no branch-writing workflow, successful exact-head checks, clean fresh review, and the owning lane's P7 authorization. Use expected-head protection where available, verify resulting `main`, perform P8, and remain in the same lane.

Never claim completion without fresh evidence. Never promise hidden background work.
