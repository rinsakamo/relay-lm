---
name: relaylm-stable-implementation
description: Advance RelayLM repository work end to end from bare continuation commands such as 次に進めて, 進めて, 続けて, or 次へ. Use for implementation, documentation canonicalization, repository maintenance, debugging, PR convergence, review correction, and merge. Enforces architecture-first investigation, root-cause-only changes, No-Patch and Stable-Structure gates, invariant-first tests, thorough review, exact-head verification, and automatic P0-P8 convergence.
---

# RelayLM Stable Implementation

## Purpose

Run RelayLM work without requiring the user to restate the workflow. A bare continuation command means: inspect the live repository, select the next authorized action, perform it, and converge the owning PR as far as evidence permits.

This skill combines:

- design before implementation;
- root-cause-first debugging;
- invariant-first test design;
- structural refactoring after correctness;
- thorough complete-diff review;
- fresh verification before completion;
- RelayLM single-authority, forward-recovery, removal-gate, and Git-history-retirement rules.

## Trigger

Use this skill when the user says:

```text
次に進めて
進めて
続けて
次へ
```

Also use it for any RelayLM request to implement, fix, refactor, canonicalize, consolidate, retire, review, finalize, or merge repository work.

A narrower instruction such as `LC-1だけ進めて`, `ドキュメント整理だけ進めて`, `コード整理を進めて`, or `#672を進めて` limits lane selection but does not weaken this workflow.

## Mandatory repository refresh

At the start of every run:

1. read current `main` and open PRs;
2. inspect checks, reviews, unresolved threads, changed paths, exact heads, mergeability, and stacking;
3. read `docs/PROJECT_STATUS.md`;
4. read `docs/architecture/project_execution_plan.md`;
5. read `docs/planning/workstream-orchestration.md`;
6. read the owning ADRs, contracts, plans, code, tests, workflows, and registries;
7. identify each active PR's P0-P8 stage and available lane capacity.

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

- lane and ordered program stage;
- exact owned paths and authorities;
- current callers, consumers, entry points, workflows, generated registries, and operator paths;
- current state, writer, reader, selector, recovery, and canonical representation where applicable;
- behavioral and authority non-goals;
- compatibility, migration, rollback, retirement, and removal boundaries;
- validation matrix;
- path and authority parallel-safety.

An unclear or expanding scope returns to P0.

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
- structural stability.

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

Split work only at complete authority boundaries. Do not separate schema, runtime, recovery, or caller changes into independently misleading partial states.

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
12. a change whose root cause cannot be explained.

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

For documentation or repository-maintenance PRs, the same cycle means:

- define failing generic validation or explicit reviewed criteria;
- implement canonical authority, registry, generation, movement, or retirement;
- remove obsolete mechanisms and negative references within the accepted scope.

Do not stop at “tests pass” when the resulting structure remains patch-like.

## P4: Baseline validation and reviewable PR

Before thorough review:

- branch and PR match the declared atomic scope;
- obvious syntax, format, compile, schema, link, and focused-test failures are fixed;
- PR body records P0-P2 decisions, non-goals, rollback, removal gates, validation, and parallel-safety;
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
- deletion and Git recoverability where applicable.

CI success is not a thorough review.

## P6: Root-cause correction and final-review loop

For each finding:

1. classify it as a local implementation defect or an architectural assumption defect;
2. correct the underlying cause;
3. strengthen regression evidence when practical;
4. update contracts, docs, records, manifests, and PR body when the boundary changed;
5. run focused validation and required exact-head CI;
6. perform a fresh final review of the full exact head.

Loop:

```text
local defect
  -> correct -> exact-head validation -> fresh final review -> repeat if needed

architecture defect, authority duplication, repeated special cases,
or three failed correction attempts
  -> stop patching -> return to P1 -> redesign -> re-enter P2
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
- destructive and authority-changing effects remain authorized.

When the user gave a continuation command and did not say `レビューだけ` or `マージしないで`, merge without asking for repeated authorization. Use expected-head protection where available.

## P8: Post-merge convergence

After merge:

- verify the merge commit and resulting `main`;
- verify required post-merge or main-head checks;
- update shared status, sequencing, generated registries, or bookkeeping only through their owner;
- close or supersede replaced PRs and branches factually;
- release the lane slot;
- refresh the portfolio and select the next executable action.

Do not report completion when post-merge state is unknown.

## Portfolio selection

Default capacity:

```text
1 Lane C PR
+ up to 1 Lane D PR
+ up to 1 Lane R PR
```

Converge existing work first. Then advance the earliest executable Lane C item and one eligible path- and authority-disjoint parallel lane when meaningful work exists.

Pending CI alone is not a stop condition while another safe bounded action exists.

Do not open speculative work merely to fill capacity.

## Progress report

Report:

```text
Critical lane
  PR and P0-P8 stage
  action completed
  exact head
  strategy or gate decisions when changed
  validation, review, and merge state

Parallel lanes
  PR and P0-P8 stage
  action completed or exact reason no safe action existed

Portfolio
  active PR count
  path or authority conflicts
  next automatically selected action
```

Do not present a menu unless repository evidence cannot resolve a genuine policy decision.

## Stop conditions

Stop without changing work only when:

- all registered lanes are complete;
- every remaining action requires a genuine user policy decision or unavailable external authority;
- no safe bounded path- and authority-disjoint action exists;
- repository state cannot be read reliably enough to act safely.

Name the exact stop condition. Never promise hidden background work.
