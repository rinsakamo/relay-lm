---
relaylm_doc_type: adr
relaylm_authority: architecture_first_stable_implementation_and_no_patch_policy
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-24
relaylm_volatility: low
relaylm_owner: implementation
relaylm_update_trigger:
  - this decision is superseded
  - the universal PR lifecycle changes
  - the no-patch or stable-structure boundary changes
  - the continuation-command execution contract changes
relaylm_not_authoritative_for:
  - current implementation completion
  - exact runtime, storage, schema, contract, or API behavior
  - authorization for an unreviewed migration, deletion, or default-on change
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - 0006-repository-structure-and-maintenance-sequencing.md
  - ../planning/workstream-orchestration.md
  - ../../AGENTS.md
  - ../../skills/relaylm-stable-implementation/SKILL.md
relaylm_supersedes: []
relaylm_superseded_by: null
---
# ADR 0007: Architecture-first stable implementation and no-patch policy

## Decision summary

RelayLM adopts one mandatory architecture-first implementation discipline for Lane C implementation, Lane D documentation canonicalization, Lane R repository maintenance, debugging, review correction, and PR convergence.

A bare user command such as `次に進めて`, `進めて`, `続けて`, or `次へ` invokes this discipline automatically through the repository `AGENTS.md`, the `relaylm-stable-implementation` skill, and the workstream orchestration authority.

Substantive implementation does not begin immediately after scope selection. It first passes:

```text
current-system investigation
  -> invariant and negative-case definition
  -> implementation-alternative comparison
  -> failure / recovery / migration / rollback design
  -> validation design
  -> No-Patch Gate
  -> Stable-Structure Gate
```

The universal PR lifecycle remains P0-P8 but is redefined as:

```text
P0 scope and authority lock
  -> P1 implementation strategy and design review
  -> P2 architecture stability gate
  -> P3 invariant-first implementation and structural refactor
  -> P4 baseline validation and reviewable PR
  -> P5 thorough complete-PR review
  -> P6 root-cause correction, exact-head validation, and final-review loop
  -> P7 merge gate and expected-head-protected merge
  -> P8 post-merge convergence
```

A local implementation defect returns to P6. An architectural assumption defect, duplicate authority, repeated special-case growth, or three failed correction attempts returns to P1 instead of accumulating another patch.

## Context

RelayLM changes frequently cross durable state, lifecycle semantics, recovery, migration, authorization, documentation authority, generated registries, and transitional compatibility. A locally plausible patch can pass focused tests while creating:

- a second semantic authority;
- competing current selectors or write paths;
- fallback precedence that hides disagreement;
- recovery behavior inconsistent with durable state;
- compatibility surfaces without removal gates;
- test-specific production behavior;
- milestone-oriented permanent structure;
- debt deferred to a later cleanup that never becomes atomic.

Post-implementation review remains necessary but is too late to be the only structural control. The implementation method itself must be reviewed before code or destructive cleanup fixes the wrong model into place.

## Decisions

### 1. Current behavior is investigated before design

The implementation strategy identifies, where relevant:

```text
current authority
current callers and consumers
current read and write paths
current selector and canonical representation
current durable or generated state
current failure, recovery, and rollback paths
current tests, process smoke, workflows, and repository validators
```

Indirect, dynamic, subprocess, operator, migration, and documentation invocation are included when they can preserve a supported responsibility.

### 2. Invariants precede implementation details

The strategy states the domain invariants and negative cases before choosing code structure.

Representative RelayLM invariants include:

```text
one semantic authority
one exact current selector where selection exists
one authoritative write path
one canonical representation
fail-closed stale or tampered state
forward-only recovery after durable intent
no unauthorized retrieval or disclosure
no permanent fallback, dual-read, or dual-write
```

Tests and validation are designed against these invariants rather than against incidental implementation shape.

### 3. Meaningful alternatives are compared

When a real design choice exists, at least two materially different approaches are compared for authority clarity, failure and recovery, migration, rollback, atomic reviewability, testability, accepted future consumers, temporary compatibility, and structural stability.

Alternatives are not invented mechanically. When only one path preserves accepted authorities, the strategy records why competing approaches are invalid.

### 4. Symptom patches are prohibited

A patch is defined by its function, not its diff size. A small root-cause correction is valid. A workaround that hides the model error is not.

Prohibited by default:

- caller-, fixture-, test-, platform-, or environment-specific bypasses that do not express the domain rule;
- duplicate authorities, selectors, write paths, or canonical representations;
- permanent fallback or precedence behavior;
- wrapper-only indirection without ownership transfer;
- swallowed errors or retry loops that conceal invalid durable state;
- compatibility without owner, current consumer, removal gate, and replacement validation;
- treating current and target as simultaneously canonical;
- weakening tests to fit the implementation;
- direct editing of generated output instead of its source authority;
- permanent milestone-oriented production names;
- known in-scope structural debt deferred to later cleanup;
- changes whose root cause cannot be explained.

An exception requires an explicit accepted contract or ADR and a bounded exit condition.

### 5. Stable structure is a pre-implementation gate

The chosen design establishes or preserves:

```text
one semantic authority
one owner per responsibility
one current selector where applicable
one authoritative write path
one recovery model
one canonical representation
explicit dependency direction
bounded compatibility with removal gates
function-oriented permanent names
no speculative abstraction without a concrete accepted consumer
```

The gate result is recorded in the PR body or owning design record.

### 6. Implementation is invariant-first and includes refactoring

The preferred execution cycle is:

```text
RED
  add failing evidence for the invariant

GREEN
  implement the smallest correct behavior

REFACTOR
  remove duplication, special cases, unstable ownership, unnecessary wrappers,
  wrong dependency direction, and temporary structure while evidence remains green
```

Documentation and maintenance PRs use the equivalent sequence: define failing generic validation or explicit reviewed criteria, establish canonical authority or registry, then remove superseded mechanisms and negative references within scope.

Passing tests does not end P3 if the resulting structure remains patch-like.

### 7. Review corrections distinguish local and architectural defects

P6 classifies findings before editing.

```text
local defect
  -> root-cause correction -> exact-head validation -> fresh final review

architecture defect
  duplicate authority
  repeated special cases
  three failed correction attempts
  -> stop local patching -> return to P1 -> redesign -> pass P2 again
```

This rule prevents a correction loop from stabilizing the wrong architecture through accumulated exceptions.

### 8. Continuation commands authorize end-to-end convergence

A bare continuation command directs ChatGPT or Codex to:

1. refresh repository and PR state;
2. read the repository skill and current authorities;
3. determine each active PR's P0-P8 stage;
4. perform the next executable action rather than return a menu;
5. converge existing PRs before opening overlapping replacements;
6. merge when P7 passes unless the user limited the turn to review-only;
7. verify P8 and automatically select the next safe action.

The command does not authorize hidden background execution or claims without fresh evidence.

## Consequences

- Implementation strategy becomes a reviewable artifact rather than private intuition.
- Patch accumulation is interrupted before it becomes architecture.
- Root-cause corrections may remain small, but every change must fit one stable authority model.
- Some apparently simple tasks return to design when they expose authority or recovery ambiguity.
- PRs may take longer before first code, but correction and rollback cost should decrease.
- The repository `AGENTS.md` provides Codex-compatible automatic instructions, while the Agent Skills-standard `SKILL.md` provides a portable ChatGPT/Codex workflow.
- Existing active PRs adopt the revised lifecycle at their next review or correction boundary; completed, evidence-backed earlier stages are not mechanically repeated.

## Rejected alternatives

### Keep design investigation inside ordinary implementation

Rejected because the investigation can be silently skipped and cannot be reviewed as a separate gate.

### Ban all small changes

Rejected because size does not distinguish a root-cause correction from a workaround.

### Allow temporary fallbacks and clean them up later

Rejected because temporary precedence and dual authority commonly become durable behavior unless an explicit consumer and removal gate exist.

### Apply the discipline only to runtime code

Rejected because documentation authority, generated registries, migration tools, smoke consolidation, and repository cleanup can create equally durable structural errors.
