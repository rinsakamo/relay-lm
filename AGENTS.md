# RelayLM agent instructions

These instructions apply to the entire repository.

## Current repository authority overrides bootstrap prompts

Thread initial prompts, handoffs, conversation memory, PR bodies, and historical files are bootstrap orientation only. They never override the current `main` versions of:

1. `AGENTS.md`;
2. `skills/relaylm-stable-implementation/SKILL.md`;
3. `skills/relaylm-github-operations/SKILL.md`;
4. `docs/adr/0007-architecture-first-stable-implementation.md`;
5. `docs/adr/0008-lane-local-continuation-safety.md`;
6. `docs/adr/0009-execution-epoch-and-rebootstrap.md`;
7. `docs/contracts/agent-execution-safety.md`;
8. `docs/planning/workstream-orchestration.md`.

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
- refresh current authority, callers, workflows, registries, and failure evidence;
- perform the controlled exact-main integration described below;
- reclassify P0 and P1 and pass P2 again;
- record a new execution receipt before substantive work resumes.

Controlled exceptions while stopped, in this order:

1. one containment branch change may only disable branch-writing automation or remove temporary execution machinery;
2. after containment and a read-only comparison with current `main`, one exact-main integration or reconstruction may update the branch;
3. after the resulting head receives read-only P0/P1/P2 review, one PR-body edit may add or replace only the execution receipt.

The exact-main integration or reconstruction:

- captures and checks the expected branch head immediately before writing;
- uses the exact current `origin/main` commit as its integration parent or reconstruction base;
- preserves the already reviewed domain intent and introduces no new feature, workaround, fallback, or scope expansion;
- records and reviews any mechanical conflict resolution in the complete diff;
- stops without writing when a conflict requires a policy, authority, lifecycle, migration, or semantic decision;
- is not retried, rebased, or force-pushed automatically after a head mismatch.

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
- a bounded change budget identifies expected paths, new files, and likely growth hotspots;
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

## Minimal-change and structural-growth rule

Implement only the minimum code and documentation required by the selected authority, invariants, and acceptance criteria.

Prohibited by default:

- speculative abstractions or future-facing extension points without a concrete accepted current consumer;
- unrelated refactors, opportunistic cleanup, or adjacent feature work;
- unused configuration, hooks, interfaces, registries, factories, adapters, or compatibility surfaces;
- duplicate production logic in tests, migration helpers, or alternate execution paths;
- splitting files only to satisfy a line-count target;
- thin wrapper layers that do not transfer authority, ownership, validation, or responsibility.

The P1 change budget is a review baseline, not a mechanical LOC limit. Unexpected path count, substantial diff growth, or any of the following default review triggers requires stopping substantive implementation and returning to P1 before continuing:

- roughly more than 200 added lines in one existing file;
- a file growing beyond roughly 700 lines or a function beyond roughly 80 lines;
- multiple semantic authorities or unrelated reasons to change accumulating in one file;
- a new wrapper, adapter, registry, factory, or interface without an accepted current consumer;
- tests beginning to reimplement production behavior instead of validating invariants.

A trigger is not an automatic rejection. P1 must either reduce or split the design along authority and responsibility boundaries, or record why the current structure is simpler and safer. Do not add repository-wide hard LOC caps that encourage meaningless fragmentation.

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

## Mandatory P8 authority-sync transaction

For an implementation-boundary PR, P8 is a required second PR transaction after the implementation merge whenever the merged change advances or changes any current implementation status, caveat, authority boundary, next ordered slice, or accepted implementation budget.

The implementation PR and its P8 authority-sync PR are separate by default:

```text
implementation PR exact-head validation
  -> P7 expected-head-protected merge
  -> verify resulting main
  -> create one same-lane P8 authority-sync PR from that exact main
  -> validate and merge the P8 authority-sync PR
  -> verify resulting main
  -> release the lane slot
  -> begin the next implementation slice
```

The P8 authority-sync PR:

- is a required post-merge convergence PR, not a corrective, validation-transfer, or replacement PR;
- changes only the current-state, sequencing, direct implementation-budget authority, generated registry, or generic current-boundary validator paths required by the merged boundary;
- contains no runtime, feature, migration, fallback, or unrelated cleanup change;
- has its own exact-main branch, current execution receipt, P0-P7 review, exact-head checks, and expected-head-protected merge;
- preserves the merged implementation PR as immutable evidence rather than reopening or amending it.

Do not open, write, review for merge, or merge the next implementation PR until the required P8 authority-sync PR is merged and the resulting `main` is verified. The lane slot remains occupied while P8 is pending.

When the merged PR does not change current status, sequencing, authority, or implementation budget, record the exact evidence that no P8 authority-sync PR is required before releasing the lane slot.

Start the P8 authority-sync transaction in the same continuation interaction as the implementation merge whenever connected capabilities and required checks permit. If CI, permissions, a newer `main`, or another authority owner blocks completion, leave the lane explicitly at P8, name the blocker, and stop without starting the next slice. Never defer it as untracked background work.

## Completion and merge

CI success does not replace thorough review or fresh final review. Correct findings at the root, validate the exact head, and repeat complete-diff review until clean.

Merge only with a current receipt, exact current-main bootstrap, no stop label, no temporary artifact, no branch-writing workflow, successful exact-head checks, clean fresh review, and the owning lane's P7 authorization. Use expected-head protection where available, verify resulting `main`, complete the mandatory P8 authority-sync transaction when required, and remain in the same lane.

Never claim completion without fresh evidence. Never promise hidden background work.
