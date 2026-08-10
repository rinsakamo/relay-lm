---
relaylm_doc_type: subsystem_architecture
relaylm_authority: subjective_mem_lifecycle_publication_replay_and_recovery_engine
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - lifecycle publication, replay, recovery, or selector-fencing responsibility changes
  - a lifecycle operation starts or stops consuming the shared engine
  - durable lifecycle record or canonical page publication contracts change
relaylm_not_authoritative_for:
  - Correct, Forget, Pin, Unpin, Restore, Consolidate, or Purge transition semantics
  - operation-specific proposal validation, authorization, payload transformation, or tombstones
  - current implementation completion
  - ordinary Retrieval, ranking, cache, API, UI, queue, worker, or scheduler behavior
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../adr/0007-architecture-first-stable-implementation.md
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - st1_subjective_mem_commit_runtime.md
  - lc1a_subjective_mem_correct.md
  - subjective-mem-forget-runtime.md
  - subjective-mem-pin-unpin-runtime.md
  - subjective-mem-restore-runtime.md
  - subjective-mem-consolidate-runtime.md
  - project_execution_plan.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Subjective MEM lifecycle runtime implementers
  - lifecycle reviewers
  - recovery and integrity reviewers
relaylm_authority_level: subsystem
---
# Subjective MEM Lifecycle Publication Engine

Last reviewed: 2026-08-07 JST

## Purpose

This document owns the operation-neutral Subjective MEM execution boundary for
publishing an immutable lifecycle successor and finalizing its content-free
state. The stable implementation owner is:

```text
relaylm/subjective_mem/lifecycle_engine.py
```

The engine centralizes publication, selector fencing, exact replay, and
caller-invoked forward recovery without becoming a lifecycle-policy owner.
Operation owners remain responsible for deciding whether an operation is
allowed and for constructing the exact semantic successor and operation-owned
final records.

Current implementation completion and milestone posture remain owned by
`docs/PROJECT_STATUS.md`. Exact field and persistence requirements remain owned
by the Subjective MEM contracts.

## Responsibility boundary

The dependency direction is one-way:

```text
Correct operation owner -----------+
Pin / Unpin operation owner -------+
Restore operation owner -----------+--> lifecycle publication engine
Consolidate operation owner -------+      -> canonical Markdown I/O
                                           -> Evidence store transaction
                                           -> shared lifecycle schemas
```

The current tree uses the shared engine from the Correct, Pin / Unpin, Restore,
and Consolidate execution surfaces. Forget remains a separate operation body
because anti-reformation tombstone finalization is additional operation-specific
authority; it is not implicitly migrated into this engine.

The engine never imports a lifecycle operation owner. There is no operation
registry, plugin loader, dynamic dispatch framework, fallback owner, or second
selector authority.

## Engine-owned mechanics

The engine owns only operation-neutral mechanics shared by its production
consumers:

1. validate one bounded immutable publication plan;
2. write or verify one immutable rendered post-image artifact;
3. reserve the singleton current selector as Retrieval-ineligible while work is
   prepared;
4. persist the shared lifecycle claim and prepared intent under one Evidence
   store transaction boundary;
5. publish the canonical Markdown post-image with exact pre-image and post-image
   binding;
6. verify predecessor retention and successor installation;
7. invoke exactly one operation-owned deterministic finalizer;
8. commit shared lifecycle transition, receipt, result, projection, and final
   selector state together with bounded operation-owned final bindings;
9. resolve exact finalized replay without republishing or re-deciding semantics;
10. drive caller-invoked forward recovery from an exact recognized durable
    state; and
11. return bounded content-free execution outcomes.

The engine does **not** own:

- the operation kind or allowed lifecycle transition;
- semantic successor construction;
- user or operator authorization;
- operation-specific reason policy;
- Forget tombstone creation or release semantics;
- candidate discovery or policy-model selection;
- ordinary Retrieval, ranking, request routing, API, UI, or background work.

## Publication plan

Each operation owner supplies one immutable `LifecyclePublicationPlan` that
binds the complete operation-neutral execution authority. The plan carries the
exact Evidence space and character identity, operation identity, logical memory
and revision lineage, singleton selector reservation, canonical page identity,
pre-image and post-image digests, immutable artifact identity, prepared intent,
and bounded operation-owned final record or log bindings.

The engine revalidates the plan at its own boundary. A caller cannot bypass
publication verification, selector fencing, finalization, replay validation, or
recovery classification by omitting a field or selecting a weaker path.

Operation-owned atomic bindings are deliberately bounded. Shared record and log
kinds remain reserved to the engine so an operation cannot replace the shared
claim, intent, transition, receipt, result, recovery, current-state, or
projection authority through an additional binding.

## Finalization boundary

An operation owner supplies one deterministic finalizer. Given the exact final
selector state, that finalizer returns the shared final record set and, where
needed, bounded operation-owned records or logs.

This split preserves one responsibility per layer:

```text
operation owner
  -> validates operation semantics and authorization
  -> constructs exact successor and operation-specific records

shared engine
  -> publishes exact post-image
  -> advances and verifies shared selector state
  -> commits shared lifecycle records
  -> invokes the operation finalizer atomically
```

The engine does not interpret the semantic payload returned by an operation
owner and does not choose a different finalizer after reservation.

## Replay and idempotency

A repeated operation is successful only when durable identity and bindings are
exactly the same as the original finalized operation. Exact finalized replay
returns the existing bounded result and does not:

- create another successor;
- rewrite the canonical page;
- advance the selector again;
- choose a fallback operation owner; or
- weaken an identity mismatch into success.

Conflicting operation identity, selector state, durable record identity, page
image, or final bindings fail closed.

## Forward recovery

Recovery is caller-invoked; this subsystem starts no background recovery worker.
The engine recognizes only exact states that are part of the accepted
publication protocol. It may continue forward when durable intent and the
canonical pre-image or post-image establish one unambiguous next action.

Foreign, partial, stale, or ambiguous images are fenced as failure or
`recovery_required` rather than guessed through. Recovery never rolls semantic
state backward, silently discards durable intent, or creates a second current
selector.

Operation-specific recovery authority remains with the operation owner where
extra durable state is required. Restore, for example, retains dedicated plan
and replay helpers around the shared publication engine. Forget remains outside
the shared engine while its anti-reformation finalization requires its
specialized boundary.

## Stable invariants

```text
one singleton Subjective MEM current selector
one canonical page publication path
one immutable rendered post-image per exact operation identity
one shared claim and prepared-intent reservation model
one shared finalized-replay model
one caller-invoked forward-recovery model
one deterministic operation finalizer per reserved operation
no operation semantics in the shared engine
no fallback, dual writer, or second publication authority
```

Shared durable and execution outcomes remain content-free. Raw semantic content,
raw keys, unrestricted filesystem paths, and unrestricted exception text do not
become shared lifecycle records merely because an operation uses this engine.

## Failure boundary

Malformed plans, stale or duplicate selectors, changed receipts, unsafe page
identity, mismatched immutable artifacts, foreign durable records, unsupported
publication state, lock contention, invalid additional bindings, and ambiguous
recovery state fail closed.

A failure before durable reservation leaves no semantic successor authority. A
failure after durable reservation is resolved only through exact replay or
forward recovery. The engine never treats an incomplete prepared state as
ordinary Retrieval-eligible current memory.

## Current operation ownership

The shared publication engine does not collapse lifecycle operations into one
semantic implementation:

| Operation | Semantic owner | Shared engine posture |
|---|---|---|
| Correct | `subjective_mem/lifecycle_runtime.py` | direct consumer |
| Pin / Unpin | `subjective_mem/pin_runtime.py` | direct consumer |
| Forget | Forget runtime / recovery owners | specialized publication/finalization boundary |
| Restore | Restore plan/runtime/replay owners | direct consumer with operation-specific recovery |
| Consolidate | `subjective_mem_consolidate_runtime.py` | direct consumer |
| Purge | none; not authorized by this architecture | no engine authority |

This table describes responsibility placement, not milestone completion or
feature enablement. `docs/PROJECT_STATUS.md` remains the current implementation
status authority.

## Evolution rule

A new lifecycle consumer may use this engine only when its operation semantics
are already owned elsewhere and the complete atomic change proves that the
existing plan, finalization, replay, and recovery model is sufficient. The
engine must not grow operation-specific conditionals merely to absorb another
operation.

If a future operation needs materially different publication authority, the
architecture must be reviewed before code is changed. Duplicating the selector,
canonical writer, replay chain, or recovery authority is not an acceptable
compatibility strategy.

## Validation anchors

The stable responsibility boundary is represented in the current tree by:

```text
relaylm/subjective_mem/lifecycle_engine.py
relaylm/subjective_mem/lifecycle_runtime.py
relaylm/subjective_mem/pin_runtime.py
relaylm/subjective_mem/restore_plan.py
relaylm/subjective_mem_restore_runtime.py
relaylm/subjective_mem/restore_replay.py
relaylm/subjective_mem_consolidate_runtime.py
tests/test_subjective_mem_lifecycle_engine_finalization.py
tests/test_subjective_mem_lifecycle_runtime.py
tests/test_subjective_mem_restore_runtime.py
tests/test_subjective_mem_restore_finalization.py
```

These are implementation and regression anchors, not a new exact contract. The
storage, lifecycle, canonical-Markdown, and operation-specific contracts remain
the normative sources for exact schemas and transition rules.
