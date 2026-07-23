---
name: relaylm-stable
description: Advance one explicitly bound RelayLM lane or pull request from bare continuation commands such as 次に進めて, 進めて, 続けて, or 次へ. Cross-lane execution requires an explicit portfolio command. Enforces lane-local fail-closed execution, architecture-first design, No-Patch and Stable-Structure gates, invariant-first implementation, complete-diff review, exact-head verification, and P0-P8 convergence.
---

# RelayLM Stable

## Purpose

Advance RelayLM work end to end without requiring the user to repeat the implementation workflow, while preserving strict lane isolation.

This Skill is the portable execution entry point. Detailed repository authority remains in:

1. `AGENTS.md`;
2. `docs/adr/0007-architecture-first-stable-implementation.md`;
3. `docs/adr/0008-lane-local-continuation-safety.md`;
4. `docs/planning/workstream-orchestration.md`;
5. the selected lane's current plans, contracts, code, tests, workflows, records, and review state.

Read those authorities before substantive action. This Skill summarizes and executes them; it does not replace them.

## Command modes

### Lane-local mode

The following commands are lane-local by default:

```text
次に進めて
進めて
続けて
次へ
```

They advance only the lane, PR, branch, or bounded work item already established by the current thread.

Resolve scope in this order:

1. explicit lane, PR, branch, or work item in the current user instruction;
2. lane declared by the thread's initial prompt or handoff;
3. uniquely identified current PR or branch and its lane metadata;
4. one unambiguous work item already selected in the conversation.

The result must be exactly one lane or one bounded PR belonging to one lane.

If scope is ambiguous, fail closed:

- do not edit repository files;
- do not create or retarget a PR;
- do not review, comment on, approve, or merge a PR;
- do not select another lane from repository priority;
- ask the user to name Lane C, Lane D, Lane R, or a PR.

### Explicit portfolio mode

Cross-lane execution requires an explicit instruction such as:

```text
全レーンを進めて
ポートフォリオを進めて
Lane C・D・Rを並行で進めて
```

Never infer portfolio authorization from multiple open PRs, free capacity, priority, or pending CI.

## Cross-lane read-only boundary

In lane-local mode, inspect other lanes only for:

- changed-path or semantic-authority overlap;
- shared callers, workflows, records, registries, or status owners;
- stack and merge-order dependencies;
- newer `main` changes that invalidate selected-lane evidence.

Do not edit, review, comment on, merge, close, reopen, retarget, supersede, or advance another lane.

When a required correction belongs to another lane, record the blocker and stop or continue with another safe action inside the selected lane.

## Mandatory refresh

At the beginning of every run:

1. resolve lane-local or explicit portfolio mode;
2. refresh current `main` and open PRs;
3. inspect changed paths, checks, reviews, unresolved threads, exact heads, mergeability, and stacking;
4. read the authorities listed under Purpose;
5. determine the selected PR's P0-P8 stage;
6. verify path and authority safety before any write.

Conversation memory, handoffs, PR bodies, and historical files are orientation only.

## P0-P8 lifecycle

```text
P0 scope and authority lock
  -> P1 implementation strategy and design review
  -> P2 architecture stability gate
  -> P3 invariant-first implementation and structural refactor
  -> P4 baseline validation and reviewable PR
  -> P5 thorough complete-PR review
  -> P6 root-cause correction and exact-head final-review loop
       -> local defect: repeat P6
       -> architecture defect: return to P1
       -> cross-lane dependency: record blocker; do not edit other lane
       -> clean: proceed to P7
  -> P7 expected-head-protected merge
  -> P8 post-merge convergence inside the same lane
```

No stage is skipped merely for speed.

## P0: Scope and authority lock

Identify:

- one selected lane and ordered stage;
- owned paths and authorities;
- callers, consumers, entry points, workflows, and registries;
- state, writer, reader, selector, representation, recovery, and rollback where applicable;
- non-goals;
- compatibility, migration, retirement, and removal boundaries;
- validation matrix;
- cross-lane read-only conflicts.

## P1: Implementation strategy

Before substantive implementation:

- investigate the current system and all relevant invocation roots;
- define invariants and negative cases;
- compare meaningful alternatives;
- map failure, recovery, migration, and rollback points;
- define compatibility owners and removal gates;
- map invariants to validation evidence;
- confirm one complete atomic boundary owned by the selected lane.

Typical invariants:

```text
one semantic authority
one owner per responsibility
one exact current selector where applicable
one authoritative write path
one canonical representation
one recovery model
fail-closed stale or tampered state
forward-only recovery after durable intent
no permanent fallback or dual authority
no cross-lane ownership transfer
```

## P2: Stability gates

### No-Patch Gate

Reject:

- caller-, fixture-, test-, platform-, or environment-specific bypasses;
- duplicate authorities, selectors, writers, or representations;
- fallback or precedence that hides disagreement;
- wrapper-only indirection without ownership transfer;
- swallowed errors or retries that hide invalid state;
- compatibility without owner, consumer, removal gate, and replacement validation;
- current and target both treated as canonical;
- weakened tests;
- direct edits to generated output;
- permanent milestone-oriented production names;
- deferred known in-scope structural debt;
- changes whose root cause cannot be explained;
- changing another lane to unblock the selected lane.

A small root-cause correction is valid. Diff size is not the criterion.

### Stable-Structure Gate

Require:

```text
one semantic authority
one lane owner for the atomic change
one owner per responsibility
one selector and write path where applicable
one recovery model
one canonical representation
explicit dependency direction
bounded compatibility with removal gates
function-oriented permanent names
no speculative abstraction without an accepted consumer
```

Record the gate result in the PR body or owning design record.

## P3: Invariant-first implementation

Use:

```text
RED
  add failing evidence for the invariant

GREEN
  implement the smallest correct behavior

REFACTOR
  remove duplication, special cases, unstable ownership,
  unnecessary wrappers, and wrong dependency direction
```

Do not stop merely because tests pass if the final structure remains patch-like.

## P4-P6: Validation, review, and correction

Before P5, make the PR complete, atomic, documented, exact-head testable, and free of temporary construction artifacts.

P5 reviews the complete diff, every changed file, callers, authority, state, failure modes, recovery, compatibility, negative cases, documentation claims, deletion recoverability, and lane ownership.

CI success does not replace review.

P6 classifies every finding:

```text
local defect
  -> root-cause correction -> exact-head validation -> fresh complete review

architecture defect, duplicate authority, repeated special cases,
or three failed correction attempts
  -> stop patching -> return to P1 and redesign

cross-lane dependency
  -> do not edit the owner lane -> record the blocker
```

A finding remains open until the corrected exact head is reviewed.

## P7: Merge

Merge only when:

- P0-P6 are complete;
- the latest complete-diff review is clean;
- exact-head checks pass and skips are understood;
- review threads and requested changes are resolved;
- base and head are intended and mergeable;
- no newer repository change invalidated the evidence;
- the merge remains within the selected lane.

A lane-local continuation command authorizes merging only the selected lane's PR, unless the user says review-only or do not merge.

## P8: Same-lane convergence

After merge:

- verify the merge commit and resulting `main`;
- verify required post-merge checks;
- perform bookkeeping only through the selected lane's owner;
- release the selected lane slot;
- select the next executable item only in the same lane.

Do not switch lanes automatically.

## Stop conditions

In lane-local mode, stop without changing another lane when:

- lane binding is ambiguous;
- the selected lane is complete;
- the selected lane requires a genuine user decision or unavailable authority;
- another lane or pending evidence blocks it and no same-lane action exists;
- repository state cannot be read safely.

Name the exact blocker. Never promise hidden background work.