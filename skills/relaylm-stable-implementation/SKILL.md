---
name: relaylm-stable-implementation
description: Advance one explicitly bound RelayLM lane or pull request end to end from bare continuation commands such as 次に進めて, 進めて, 続けて, or 次へ. Cross-lane execution requires an explicit portfolio command. Use for implementation, documentation canonicalization, repository maintenance, debugging, PR convergence, review correction, and merge. Enforces architecture-first investigation, root-cause-only changes, No-Patch and Stable-Structure gates, invariant-first tests, thorough review, exact-head verification, and P0-P8 convergence.
---

# RelayLM Stable Implementation

## Purpose

Run RelayLM work without requiring the user to restate the implementation workflow, while preserving strict lane isolation.

A bare continuation command means:

1. resolve exactly one current lane, PR, branch, or bounded work item;
2. inspect live repository evidence;
3. perform the next authorized action only inside that scope;
4. converge that owning PR as far as evidence permits;
5. after merge, select the next item only in the same lane.

This skill combines:

- lane-local fail-closed execution;
- design before implementation;
- root-cause-first debugging;
- invariant-first test design;
- structural refactoring after correctness;
- thorough complete-diff review;
- fresh verification before completion;
- RelayLM single-authority, forward-recovery, removal-gate, and Git-history-retirement rules.

## Command modes

### Lane-local continuation mode

The following commands are lane-local by default:

```text
次に進めて
進めて
続けて
次へ
```

They do not authorize work in another lane merely because that work is unblocked, higher priority, or waiting for CI.

### Explicit portfolio mode

Cross-lane execution requires an explicit instruction such as:

```text
全レーンを進めて
ポートフォリオを進めて
Lane C・D・Rを並行で進めて
```

Equivalent language is valid only when it clearly authorizes more than one named lane or the whole portfolio.

A narrower instruction such as `LC-1だけ進めて`, `ドキュメント整理だけ進めて`, `コード整理を進めて`, or `#672を進めて` binds the run to that lane or PR and does not weaken this workflow.

## Resolve lane scope before acting

For lane-local mode, resolve scope in this order:

1. explicit lane, PR, branch, or work item in the current user instruction;
2. lane declared by the current thread's initial prompt or handoff;
3. uniquely identified current PR or branch and its lane metadata;
4. one unambiguous work item already selected in the current conversation.

The result must be exactly one of:

```text
Lane C
Lane D
Lane R
one explicitly named PR or bounded work item belonging to one lane
```

If the result is ambiguous, fail closed:

- do not modify repository files;
- do not create or retarget a PR;
- do not review, comment on, approve, or merge any PR;
- do not choose another lane from repository priority;
- ask the user to identify the lane or PR.

Never infer portfolio authorization from the existence of several open lane PRs.

## Cross-lane read-only boundary

A lane-local run may inspect other lanes only to detect:

- changed-path overlap;
- semantic-authority overlap;
- shared generated registries or status owners;
- stack or merge-order dependencies;
- a newer `main` change that invalidates the selected lane's evidence.

Without explicit portfolio authorization, other lanes are read-only. Do not:

- edit their branches or files;
- update their PR bodies;
- post comments or reviews;
- resolve their threads;
- merge, close, reopen, retarget, or supersede them;
- start their next work item.

When a cross-lane dependency blocks the selected lane, report the blocker and stop or continue with another safe action inside the same lane. Do not repair the dependency in the other lane.

## Mandatory repository refresh

At the start of every run:

1. resolve the lane-local or explicit portfolio mode;
2. read current `main` and open PRs;
3. inspect checks, reviews, unresolved threads, changed paths, exact heads, mergeability, and stacking;
4. read `AGENTS.md`;
5. read `docs/adr/0008-lane-local-continuation-safety.md`;
6. read `docs/PROJECT_STATUS.md`;
7. read `docs/architecture/project_execution_plan.md`;
8. read `docs/planning/workstream-orchestration.md`;
9. read the owning ADRs, contracts, plans, code, tests, workflows, and registries;
10. determine the selected PR's P0-P8 stage.

In lane-local mode, determine other PR stages only as much as necessary for conflict and dependency checks.

Conversation memory, old prompts, PR bodies, and historical files are orientation only.

## Universal P0-P8 lifecycle

```text
P0 scope and authority lock
  -> P1 implementation strategy and design review
  -> P2 architecture stability gate
  -> P3 invariant-first implementation and structural refactor
  -> P4 baseline validation and reviewable PR
  -> P5 thorough complete-PR review
  -> P6 root-cause correction, exact-head validation, and fresh final-review loop
       -> local defect: correct and repeat P6
       -> architecture defect: return to P1
       -> clean: proceed to P7
  -> P7 merge gate and expected-head-protected merge
  -> P8 post-merge convergence
```

No required stage is skipped merely for speed.

## P0: Scope and authority lock

Before substantive changes, identify:

- the single selected lane and ordered program stage;
- exact owned paths and authorities;
- current callers, consumers, entry points, workflows, generated registries, and operator paths;
- current state, writer, reader, selector, recovery, and canonical representation where applicable;
- behavioral and authority non-goals;
- compatibility, migration, rollback, retirement, and removal boundaries;
- validation matrix;
- path and authority safety against other lanes.

The PR body must state that the lane is exclusive for the run unless portfolio mode was explicitly invoked.

An unclear, expanding, or cross-lane scope returns to P0.

## P1: Implementation strategy and design review

Do not write production code or perform destructive cleanup before the strategy is reviewable.

### Investigate the current system

Record:

```text
current authority
current callers and consumers
current write and read paths
current durable or generated state
current recovery and rollback paths
current tests, process smoke, and repository validation
```

Inspect indirect, dynamic, subprocess, workflow, operator, migration, and documentation invocation where relevant.

### Define invariants and negative cases

State what must remain true before choosing implementation details.

Typical RelayLM invariants include:

```text
one semantic authority
one exact current selector
one authoritative write path
one canonical representation
fail-closed stale or tampered state
forward-only recovery after durable intent
no unauthorized retrieval or disclosure
no permanent fallback or dual authority
no cross-lane ownership transfer
```

### Compare meaningful alternatives

Compare at least two materially different approaches when a real design choice exists. Evaluate:

- authority clarity;
- failure and recovery behavior;
- migration and rollback;
- reviewability and atomicity;
- testability;
- future ordered consumers already accepted by repository authorities;
- temporary compatibility and removal cost;
- structural stability;
- whether the approach remains owned entirely by the selected lane.

Do not invent alternatives when only one valid path exists; explain why the alternatives are invalid.

### Map failure points

For stateful work, map every durable transition boundary and define:

```text
observable state
retry behavior
conflict classification
forward recovery
operator action
```

### Fix the validation design

Define which evidence proves each invariant:

```text
unit or component tests
integration tests
process smoke
old/new characterization
negative validation
exact-head CI
post-merge verification
```

### Confirm the atomic PR boundary

Split work only at complete authority boundaries. Do not separate schema, runtime, recovery, or caller changes into independently misleading partial states. Do not absorb another lane's responsibility to keep the selected PR moving.

## P2: Architecture stability gate

Implementation may begin only when both gates pass.

### No-Patch Gate

Reject an approach that relies on any of the following unless an accepted contract explicitly requires it:

1. caller-, fixture-, test-, OS-, or environment-specific bypass;
2. new authority beside an existing authority;
3. fallback or precedence that hides disagreement;
4. wrapper-only indirection without ownership transfer;
5. swallowed exceptions or retries that conceal invalid state;
6. compatibility without owner, live consumer, removal gate, and replacement validation;
7. current and target both treated as canonical;
8. weakening a failing test to match the implementation;
9. direct modification of generated output rather than its source;
10. permanent milestone-oriented production names;
11. known in-scope debt deferred to later cleanup;
12. a change whose root cause cannot be explained;
13. changing another lane to unblock the selected lane without explicit portfolio authorization.

A small change is allowed when it corrects the root cause and preserves the stable model.

### Stable-Structure Gate

The chosen approach must establish or preserve:

```text
one semantic authority
one owner per responsibility
one current selector where selection exists
one write path per authority
one recovery model
one canonical representation
explicit dependency direction
bounded compatibility with removal gates
function-oriented permanent names
no speculative abstraction without a concrete accepted consumer
one lane owner for the complete atomic change
```

Record the gate result in the PR body or owning design record.

## P3: Invariant-first implementation and structural refactor

Implement the smallest complete atomic boundary.

Preferred cycle:

```text
RED
  add a failing test or validation that expresses the invariant

GREEN
  implement the smallest correct domain behavior

REFACTOR
  remove duplication, special cases, unstable names, wrong ownership,
  unnecessary wrappers, and inverted dependencies while tests stay green
```

For documentation or repository-maintenance PRs, the equivalent cycle is:

- define failing generic validation or explicit reviewed criteria;
- implement canonical authority, registry, generation, movement, or retirement;
- remove obsolete mechanisms and negative references within the selected lane's scope.

Do not stop at “tests pass” when the resulting structure remains patch-like.

## P4: Baseline validation and reviewable PR

Before thorough review:

- branch and PR match the declared atomic and lane-local scope;
- obvious syntax, format, compile, schema, link, and focused-test failures are fixed;
- PR body records P0-P2 decisions, non-goals, rollback, removal gates, validation, and cross-lane read-only checks;
- current exact head is recorded;
- temporary construction artifacts are removed or explicitly bounded;
- the PR can be reviewed without hidden or uncommitted work.

## P5: Thorough complete-PR review

Review the entire resulting PR, not only the last commit.

Inspect:

- contracts, ADRs, plans, and current-status boundaries;
- every changed file and complete diff;
- direct and indirect callers and entry points;
- authority, state, failure, crash, race, security, privacy, migration, rollback, and recovery;
- tests for missing negative cases, false positives, false negatives, and tautologies;
- compatibility surfaces and removal gates;
- fallback, duplicate authority, stale paths, dead wrappers, and scope drift;
- documentation claims against behavior;
- deletion and Git recoverability where applicable;
- accidental changes, comments, reviews, or ownership assumptions involving another lane.

CI success is not a thorough review.

## P6: Root-cause correction and final-review loop

For each finding:

1. classify it as a local implementation defect or an architectural assumption defect;
2. correct the underlying cause inside the selected lane;
3. strengthen regression evidence when practical;
4. update contracts, docs, records, manifests, and PR body when the selected boundary changed;
5. run focused validation and required exact-head CI;
6. perform a fresh final review of the full exact head.

Loop:

```text
local defect
  -> correct -> exact-head validation -> fresh final review -> repeat if needed

architecture defect, authority duplication, repeated special cases,
or three failed correction attempts
  -> stop patching -> return to P1 -> redesign -> re-enter P2

required correction belongs to another lane
  -> do not edit that lane -> record blocker -> stop selected-lane convergence
```

A review comment is not resolved by explanation alone when code, tests, docs, or evidence remain wrong.

## P7: Merge gate and merge

Merge only when:

- P0-P6 are complete;
- the latest complete-diff final review has no unresolved finding;
- exact-head checks are successful and skips are understood;
- review threads and requested changes are resolved or factually dispositioned;
- base and head are intended and mergeable;
- conflict resolution has been reviewed;
- no newer repository change invalidated the design or evidence;
- destructive and authority-changing effects remain authorized;
- the merge changes only the selected lane's authorized boundary.

When the user gave a lane-local continuation command and did not say `レビューだけ` or `マージしないで`, merge the selected lane's PR without asking for repeated authorization. Use expected-head protection where available.

Do not merge another lane's PR in the same interaction unless explicit portfolio mode was invoked.

## P8: Post-merge convergence

After merge:

- verify the merge commit and resulting `main`;
- verify required post-merge or main-head checks;
- update shared status, sequencing, generated registries, or bookkeeping only through the selected lane's authorized owner;
- close or supersede replaced PRs and branches in the selected lane factually;
- release the selected lane slot;
- select the next executable action only in the same lane.

Do not report completion when post-merge state is unknown.

## Lane-local action selection

In lane-local mode:

1. converge the selected lane's existing PR;
2. if no PR exists, choose the earliest executable item in that same lane;
3. if that PR is blocked by CI, inspect or improve only safe work in the same lane;
4. if no same-lane action is safe, report the exact blocker and stop;
5. never fill time by advancing another lane.

Pending CI is allowed to be a lane-local stop condition when no other safe action exists in the selected lane.

## Explicit portfolio action selection

Only in explicit portfolio mode:

```text
1 Lane C PR
+ up to 1 Lane D PR
+ up to 1 Lane R PR
```

Converge existing work first, then advance additional path- and authority-disjoint lanes as explicitly authorized. Three open lane PRs are a ceiling, not a target.

Do not open speculative work merely to fill capacity.

## Progress report

### Lane-local mode

Report:

```text
Selected lane
  PR and P0-P8 stage
  action completed
  exact head
  strategy or gate decisions when changed
  validation, review, and merge state

Cross-lane safety
  read-only conflicts or dependencies discovered
  confirmation that no other lane was modified

Next
  next action in the same lane, or exact blocker
```

### Explicit portfolio mode

Report each authorized lane separately, followed by portfolio conflicts and the next authorized portfolio action.

Do not present a menu unless lane scope or a genuine policy decision cannot be resolved safely.

## Stop conditions

In lane-local mode, stop without changing other lanes when:

- the selected lane is complete;
- the selected lane requires a genuine user decision or unavailable authority;
- the selected lane is blocked by another lane or pending evidence and no same-lane action exists;
- lane binding is ambiguous;
- repository state cannot be read reliably enough to act safely.

Name the exact stop condition. Never promise hidden background work.