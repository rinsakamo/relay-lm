---
relaylm_doc_type: subsystem_architecture
relaylm_authority: subjective_mem_lifecycle_publication_replay_and_recovery_engine
relaylm_status: target
relaylm_volatility: high
relaylm_owner: memory
relaylm_update_trigger:
  - lifecycle publication, replay, recovery, or selector-fencing responsibility changes
  - another lifecycle operation begins consuming the shared engine
  - durable lifecycle record or canonical page publication contracts change
relaylm_not_authoritative_for:
  - Correct, Forget, Pin, Unpin, Restore, Consolidate, or Purge transition semantics
  - operation-specific proposal validation, authorization, payload transformation, or tombstones
  - current implementation completion
  - ordinary Retrieval, ranking, cache, API, UI, queue, worker, or scheduler behavior
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../adr/0007-architecture-first-stable-implementation.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - st1_subjective_mem_commit_runtime.md
  - lc1a_subjective_mem_correct.md
  - subjective-mem-forget-runtime.md
  - subjective-mem-pin-unpin-runtime.md
  - project_execution_plan.md
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - Subjective MEM lifecycle runtime implementers
  - lifecycle reviewers
relaylm_authority_level: subsystem
---
# Subjective MEM Lifecycle Publication Engine

## Purpose

This document owns the operation-neutral execution boundary needed to publish an
immutable Subjective MEM lifecycle successor and finalize its content-free state
without copying the existing Correct runtime for each later lifecycle operation.

The accepted first implementation consumer is Correct. Pin / Unpin is the next
consumer after exact Correct equivalence is proven. This document does not claim
that the shared engine is already implemented.

Correct remains the semantic owner of `active -> active`. Pin / Unpin remains the
semantic owner of `active -> pinned` and `pinned -> active`. The shared engine
does not choose transitions or create semantic payloads.

## Current problem

The current Correct runtime contains both Correct semantics and reusable page
publication, selector fencing, replay, and recovery mechanics. Forget imports
some Correct-private validation helpers and owns a separate specialized body
because it also finalizes anti-reformation state.

LC-1C must not proceed by:

- copying the Correct publication state machine;
- importing Correct or Forget private operation helpers;
- wrapping Correct while leaving authority there;
- adding another selector, page writer, replay model, or recovery model;
- converting every lifecycle operation in one unbounded refactor.

The missing boundary is one operation-neutral owner for mechanics already shared
by the accepted lifecycle contracts.

## Decision

Introduce one function-oriented module:

```text
relaylm/subjective_mem_lifecycle_engine.py
```

The first code PR must move real operation-neutral responsibility from Correct
into this module and migrate Correct as a production consumer in the same PR.
The moved Correct implementation is deleted; no compatibility wrapper or
fallback remains.

Dependency direction:

```text
Correct operation owner ---------+
                                  +--> lifecycle publication engine
Pin / Unpin operation owner -----+      -> canonical Markdown I/O
                                         -> Evidence store transaction
                                         -> shared lifecycle schemas
```

The engine never imports an operation owner. Operation owners provide one exact,
immutable execution plan and one directly called deterministic finalization
function for their operation-specific durable records. There is no registry,
factory, plugin loading, ContextVar dispatch, monkeypatch, fallback, or dynamic
operation discovery.

## Engine-owned responsibility

The engine owns only:

1. validation of one bounded operation-neutral plan;
2. singleton selector reservation as `prepared` and Retrieval-ineligible;
3. shared lifecycle claim and prepared-intent persistence;
4. immutable rendered post-image artifact I/O;
5. secure POSIX canonical-page publication with exact pre/post digests;
6. exact predecessor retention and successor installation verification;
7. invocation of the operation-owned deterministic finalizer;
8. exact finalized replay;
9. caller-invoked forward recovery from exact pre-image or post-image states;
10. `recovery_required` fencing for foreign or ambiguous images;
11. bounded, content-free execution outcomes.

The engine does not own:

- operation kind or allowed transition;
- semantic successor construction;
- authorization or reason policy;
- operation-specific records such as a Forget tombstone;
- ordinary Retrieval, ranking, cache, API, UI, or background recovery.

## Operation-neutral plan

The plan binds only the shared execution authority:

```text
operation identity and input digest
exact evidence-space and character authority
exact logical memory and from/to revision
exact selector pre-state and prepared state
exact current receipt lineage
exact page identity, path, partition, and pre-image digest
exact predecessor and successor revision/block digests
exact immutable artifact and post-image digest
exact shared claim and prepared intent
```

The engine revalidates the plan at its boundary. A caller cannot omit publication
verification, finalization, replay validation, or recovery fencing.

## Invariants

```text
one singleton selector
one canonical page writer
one exact pre-image/post-image publication path
one immutable artifact path
one shared claim and prepared-intent reservation model
one exact finalized-replay model
one forward-only recovery model
no operation semantics in the shared engine
no raw key, semantic content, filesystem path, or unrestricted exception text
  in shared records or execution results
```

Malformed plans, stale or duplicate selectors, changed receipts, stale page
authority, partial final records, unsupported platforms, unsafe paths, lock
contention, and foreign images fail closed.

## Migration order

### Shared-engine extraction

The next code PR must:

1. move only operation-neutral mechanics from Correct;
2. migrate Correct to the shared engine in the same PR;
3. preserve Correct record shapes, IDs, statuses, replay, and crash recovery;
4. delete the moved Correct-private bodies;
5. leave Forget semantics unchanged.

This PR does not implement Pin / Unpin. Correct is the concrete accepted current
consumer, so the extraction is not speculative.

### Pin / Unpin runtime

After the extraction merges and exact Correct equivalence is green,
`subjective_mem_pin_runtime.py` becomes the sole Pin / Unpin semantic owner and
uses the shared engine. It supplies exact transition validation, byte-equivalent
successor preservation, and Pin / Unpin final records.

Pin / Unpin must not copy the engine or import Correct/Forget private helpers.

### Forget boundary

Forget is not silently migrated. Its anti-reformation finalization is an
additional authority. A later migration requires a separate complete-diff review
and removal of the replaced body in the same PR.

## Alternatives

**Copy Correct into Pin / Unpin:** rejected because it creates duplicate
publication, replay, and recovery authorities.

**Import Correct private helpers:** rejected because ownership remains unstable
and operation coupling becomes implicit.

**General lifecycle registry/framework:** rejected because no dynamic consumer
exists and it would add speculative extension points.

**Extract with Correct as the first consumer:** accepted because it transfers a
real current responsibility and gives Pin / Unpin one stable dependency.

## Extraction change budget

Expected production paths:

```text
new:      relaylm/subjective_mem_lifecycle_engine.py
modified: relaylm/subjective_mem_lifecycle_runtime.py
```

Expected validation paths:

```text
modified: tests/test_subjective_mem_lifecycle_runtime.py
modified: scripts/relaylm_lc1a_subjective_mem_correct_smoke.py only if required
```

Expected changed paths: two to four. No workflow, changed-matrix, status, API,
UI, Primary MEM, Retrieval, Forget semantic, or documentation-wide cleanup path
is expected.

The extraction must reduce the Correct module by moving responsibility, not add
a duplicate implementation. Unexpected paths, roughly more than 200 net new
lines in an existing file, a function above roughly 80 lines, or a new module
above roughly 700 lines returns the work to P1. These are review triggers, not
mechanical split targets.

## Validation

The extraction PR must prove:

- all existing Correct unit and process behavior remains exact;
- default-off and dry-run behavior remains write-free;
- committed and duplicate-finalized outcomes remain exact;
- pre-page and post-page recovery remains forward-only;
- foreign images are preserved and fenced;
- selector, receipt, page, and predecessor races fail closed;
- shared records and outcomes remain content-free;
- the moved Correct implementation and fallback paths are absent;
- the engine has one production consumer and no dynamic registry;
- Python 3.10/3.12 tests and the consolidated lifecycle group pass on the exact
  head.

The later Pin / Unpin PR must also satisfy
`subjective-mem-pin-unpin-runtime.md`.

## Rollback and non-goals

Before merge, rollback is branch deletion. After merge, Correct uses the shared
engine as its publication owner; rollback is a reviewed correction, not revival
of the deleted body.

This design does not implement Pin / Unpin, change Correct or Forget semantics,
wire Retrieval, add API/UI, change Primary MEM, add background recovery, support
non-POSIX apply, migrate user data, or authorize Restore, Consolidate, Merge,
Supersession, or Purge.
