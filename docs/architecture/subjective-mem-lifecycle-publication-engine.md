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

This document owns the operation-neutral execution boundary required to publish
an immutable Subjective MEM lifecycle successor and finalize its content-free
durable state without duplicating the existing Correct runtime for every later
lifecycle operation.

The first implementation consumers are:

```text
current consumer:  Correct
next consumer:     Pin / Unpin
```

Correct remains the semantic owner of `active -> active` correction. Pin / Unpin
remains the semantic owner of `active -> pinned` and `pinned -> active`.
The shared engine owns neither transition choice nor operation-specific content.

## Current implementation problem

The current Correct runtime contains both Correct semantics and reusable
publication machinery in one large module. Forget reuses some Correct-private
validation helpers but owns a separate publication and recovery body because it
also finalizes anti-reformation state.

LC-1C cannot safely proceed by:

- copying the Correct publication state machine into a Pin / Unpin module;
- importing high-level Correct or Forget private helpers;
- adding a wrapper that delegates to Correct while leaving authority there;
- creating a second selector, receipt family, canonical page writer, replay
  model, or recovery model;
- converting every lifecycle operation in one unbounded refactor.

The root cause is missing operation-neutral ownership for the mechanics already
shared by the accepted lifecycle contracts.

## P1 decision

Introduce one function-oriented module:

```text
relaylm/subjective_mem_lifecycle_engine.py
```

It owns only the operation-neutral mechanics listed below. It must have at least
one exact current production consumer in the same extraction PR. Correct is that
consumer. The module is not an extension point for hypothetical operations.

The dependency direction is:

```text
Correct operation owner -------------------+
                                            |
Pin / Unpin operation owner ---------------+--> lifecycle publication engine
                                            |      -> canonical Markdown planner/I/O
future accepted lifecycle owner -----------+      -> Evidence store transaction
                                                   -> shared lifecycle record schemas
```

Operation owners construct and validate an exact immutable execution plan. The
engine validates that plan again at its authority boundary and executes it. The
engine never imports an operation owner.

## Engine-owned responsibility

The shared engine owns exactly these mechanics:

1. validate one bounded operation-neutral execution plan;
2. reserve the singleton current selector with `mutation_state: prepared` and
   `retrieval_eligible: false` under the Evidence-space transaction lock;
3. persist the operation claim and prepared intent supplied by the operation
   owner after exact schema and digest validation;
4. write and read one immutable rendered post-image artifact;
5. publish the canonical page through the secure POSIX page-domain lock and
   exact pre-image/post-image digests;
6. verify predecessor retention and exact successor installation through a
   caller-supplied bounded verifier;
7. invoke one bounded operation finalizer inside the publication boundary;
8. resolve exact finalized replay without appending another revision;
9. recover forward from exact pre-image or exact post-image states;
10. mark the selector `recovery_required` for a foreign or ambiguous page without
    overwriting it;
11. return bounded, content-free execution outcomes.

The engine does not decide or synthesize:

- operation kind;
- allowed from/to lifecycle states;
- successor semantic payload;
- authorization class or reason category;
- operation-specific durable records such as a Forget tombstone;
- operation-specific final-record equality beyond a bounded callback contract.

## Exact execution plan

The engine accepts one immutable plan whose fields are limited to the authority
needed by the shared mechanics:

```text
operation identity and input digest
exact evidence-space and character authority digests
exact logical memory and from/to revision
exact current selector pre-state and prepared state
exact current receipt lineage
exact canonical page identity, relative path, partition, and pre-image digest
exact predecessor and successor revision/block digests
exact immutable artifact ID and post-image digest
exact shared lifecycle claim and prepared intent
bounded verify-installed callback
bounded finalize-installed callback
bounded final-replay resolver
bounded recovery-required recorder
```

Callbacks are accepted only where operation-specific durable semantics cannot be
expressed by the engine without taking their authority. They must be explicit
current consumers, deterministic, repository-local, content-free at the engine
boundary, and covered by operation tests. Generic hooks, registries, factories,
plugin loading, ContextVar dispatch, monkeypatching, or fallback callbacks are
prohibited.

## Invariants

The implementation must preserve:

```text
one singleton selector
one canonical page writer
one exact pre-image/post-image publication path
one immutable artifact path
one claim and prepared-intent reservation model
one exact finalized-replay model
one forward-only recovery model
one Evidence-space transaction writer at each durable transition
no raw idempotency key, semantic content, path, or unrestricted exception text
  in execution results or shared records
no operation-specific lifecycle decision in the shared engine
```

A caller cannot weaken engine validation by omitting a verifier or finalizer.
Malformed plans, duplicate or foreign selector state, changed receipts, stale
page authority, partial final records, unsupported platform, unsafe path, lock
contention, and foreign images fail closed.

## Migration order

### Extraction PR

The first code PR after this design must:

1. move only operation-neutral mechanics from the Correct runtime into the shared
   engine;
2. migrate Correct to consume the shared engine in the same PR;
3. preserve exact Correct behavior, record shapes, IDs, error classification,
   replay, crash recovery, and process smoke;
4. delete the moved Correct-private implementations rather than retain wrapper
   or fallback paths;
5. leave Forget behavior unchanged unless a required shared-helper move can be
   proven mechanically and without importing Forget tombstone semantics.

This PR does not implement Pin / Unpin. Its accepted current consumer is Correct,
so the engine is not speculative.

### Pin / Unpin PR

Only after the extraction PR is merged and exact Correct equivalence is green,
LC-1C may add `subjective_mem_pin_runtime.py` as the sole Pin / Unpin semantic
owner. It consumes the shared engine and supplies:

- exact Pin / Unpin transition validation;
- byte-equivalent successor preservation;
- operation-specific intent and final lifecycle records;
- exact replay and final-record equality for the Pin / Unpin operation family.

It must not copy the extracted engine, import Correct/Forget private helpers, or
add a second execution path.

### Forget boundary

Forget is not silently migrated by either PR. Its anti-reformation tombstone and
semantic-identity finalization are an additional authority. A later migration is
allowed only through a separate complete-diff review proving exact behavior and
removing the replaced body in the same PR. Until then, no new Pin / Unpin code
may depend on Forget internals.

## Alternatives considered

### Copy Correct into Pin / Unpin

Rejected because it creates a second publication, replay, and recovery authority
and adds another large lifecycle state machine.

### Import Correct private helpers directly

Rejected because private helper ownership remains with Correct and later changes
can silently break Pin / Unpin semantics.

### General registry or lifecycle plugin framework

Rejected because there are only two accepted immediate consumers and no current
need for dynamic registration. It would create speculative extension points.

### Extract the engine with Correct as current consumer

Accepted because it transfers real existing responsibility, removes the moved
Correct implementation, provides exact characterization evidence, and gives
Pin / Unpin one stable dependency without taking operation semantics.

## Change budget for the extraction PR

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

Expected new production files: one. Expected changed paths: two to four.
No workflow, changed-matrix, status, API, UI, Primary MEM, Retrieval, Forget
semantic, or documentation-wide cleanup path is expected.

The extraction should reduce the Correct module by moving responsibility, not
increase total production logic through duplication. Unexpected additional
paths, more than roughly 200 net new lines in an existing file, a new function
above roughly 80 lines, or a new module above roughly 700 lines returns the work
to P1. These are review triggers, not mechanical split targets.

## Validation

The extraction PR must prove:

- all existing Correct unit and process tests remain exact;
- default-off and dry-run behavior remains write-free;
- committed and duplicate-finalized results are unchanged;
- pre-page and post-page crash recovery remains forward-only;
- foreign image handling preserves the foreign page and marks recovery required;
- selector, receipt, page, and predecessor races remain fail closed;
- shared engine results and records remain content-free;
- the Correct module no longer contains the moved publication/replay/recovery
  implementation or a compatibility fallback;
- the engine has one current production consumer and no dynamic registry;
- Python 3.10/3.12 unit suites and the consolidated Subjective MEM lifecycle
  group pass on the exact head.

The later Pin / Unpin PR must additionally satisfy the validation matrix in
`subjective-mem-pin-unpin-runtime.md`.

## Rollback and removal

Before the extraction PR merges, rollback is branch deletion. After merge, the
shared engine is the publication owner for Correct and must not be bypassed by
restoring the removed body. A defect is corrected in the engine or the exact
Correct plan construction, with exact-head characterization evidence.

If Pin / Unpin is later abandoned, the engine remains justified by Correct as
its current consumer. No Pin-specific compatibility surface remains in the
engine.

## Non-goals

This design does not implement Pin / Unpin, change Correct or Forget semantics,
wire ordinary Retrieval, add API/UI routes, change Primary MEM, introduce
background recovery, support non-POSIX apply, migrate user data, or authorize
Restore, Consolidate, Merge, Supersession, or Purge.
