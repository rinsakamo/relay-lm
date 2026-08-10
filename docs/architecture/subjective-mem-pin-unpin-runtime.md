---
relaylm_doc_type: subsystem_architecture
relaylm_authority: subjective_mem_pin_unpin_runtime_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Subjective MEM Pin/Unpin input, transition, persistence, or recovery changes
  - ordinary Retrieval changes pinned lifecycle eligibility or priority consumption
  - Subjective MEM lifecycle state, selector, or publication authority changes
relaylm_not_authoritative_for:
  - current runtime implementation completion status
  - ordinary Subjective MEM Retrieval, ranking, cache, or request-path selection
  - API, UI, model-generated Pin/Unpin decisions, or background recovery
  - Primary MEM pin projection, migration, retirement, or precedence
  - Correct, Forget, Restore, Consolidate, or Purge behavior
relaylm_related_authority:
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - st1_subjective_mem_commit_runtime.md
  - lc1a_subjective_mem_correct.md
  - subjective-mem-forget-runtime.md
  - subjective-mem-lifecycle-publication-engine.md
  - phase_i5_pin_unpin_contract.md
  - phase_i5b_pin_unpin_apply.md
  - project_execution_plan.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Subjective MEM runtime implementers
  - lifecycle reviewers
  - retrieval migration and integrity reviewers
relaylm_authority_level: subsystem
---
# Subjective MEM Pin / Unpin Runtime

Last reviewed: 2026-08-07 JST

## Scope

Pin / Unpin owns one caller-invoked, default-off lifecycle runtime on the
canonical Subjective MEM Markdown and content-free operations boundaries.

```text
Pin:
  active revision N / mutation none / retrieval eligible
    -> exact prepared intent / retrieval fail-closed
    -> pinned revision N+1 / mutation none / retrieval eligible

Unpin:
  pinned revision N / mutation none / retrieval eligible
    -> exact prepared intent / retrieval fail-closed
    -> active revision N+1 / mutation none / retrieval eligible
```

Pin and Unpin append immutable lifecycle successors. They never mutate the
predecessor, rewrite semantic content, create a separate pin-state projection,
or make a hidden memory retrievable.

Current implementation completion and feature posture remain owned by
`docs/PROJECT_STATUS.md`. Exact schema and transition requirements remain owned
by the Subjective MEM contracts.

## Normative state model

The Subjective MEM logical contract owns Pin state as lifecycle state, not as an
orthogonal mutable flag:

```text
pin:   active -> pinned
unpin: pinned -> active
```

Both final states are logically Retrieval-eligible only when the singleton
selector is exact, names the latest persisted revision, has
`mutation_state: none`, and has exact canonical lineage and receipt authority.
During preparation and publication the selector is fenced with
`mutation_state: prepared` and `retrieval_eligible: false`. Finalization returns
the selector to `mutation_state: none` and `retrieval_eligible: true` for either
`active` or `pinned`.

## Primary MEM characterization boundary

The Primary MEM I-5A/I-5B implementation is characterization or historical
migration evidence only. Its durable pin receipt/state projection and ranking
hint are not Subjective MEM semantic authority.

Subjective MEM Pin / Unpin therefore does not:

- write `memory/mem/pins/v0/**` or any Primary MEM pin projection;
- call Primary MEM Pin/Unpin modules, API routes, UI panels, or ranking helpers;
- add an orthogonal `pin_state` field to `SubjectiveMemCurrentState`;
- wire pinned priority into ordinary Subjective MEM Retrieval;
- establish permanent old/new pin precedence or dual-write behavior.

Ordinary Subjective MEM Retrieval remains the owner of candidate consumption,
ranking, cache, usage events, and request-path authority. This architecture does
not grant Primary MEM any current Pin / Unpin authority.

## One semantic owner

`relaylm/subjective_mem_pin_runtime.py` is the Pin / Unpin operation owner. It
owns one shared operation body and exposes two bounded public entry points:

```text
pin_subjective_mem(...)
unpin_subjective_mem(...)
```

Both entry points delegate to the same operation body. The explicit operation
kind derives the only supported transition pair:

```text
pin   -> expected active, result pinned
unpin -> expected pinned, result active
```

Separate Pin and Unpin validator, publication, receipt, selector, replay, or
recovery bodies are prohibited. A second runtime, private duplicate core,
ContextVar dispatch, monkeypatch, fallback import, wrapper-only indirection, or
operation-specific precedence path is also prohibited.

The current dependency direction includes the operation-neutral lifecycle
publication engine:

```text
subjective_mem_pin_runtime
  -> subjective_mem_pin
  -> subjective_mem_lifecycle_authority
  -> subjective_mem_lifecycle_engine
  -> subjective_mem_lifecycle / subjective_mem_markdown
  -> subjective_mem / evidence store / canonical commit I/O
```

The operation owner must not import Primary MEM Pin/Unpin runtime code or a
high-level Correct/Forget private helper.

## Storage-neutral proposal authority

`relaylm/subjective_mem/pin.py` owns one proposal and boundary shape for both
operations. The proposal binds:

- `operation_kind: pin | unpin`;
- exact memory ID and current revision;
- exact expected lifecycle and mutation state;
- exact page, relative path, current block, and page digest;
- exact singleton selector ID and digest;
- exact current commit/lifecycle receipt ID and digest;
- exact memory kind and formation stage;
- exact scope-binding and formation-snapshot digests;
- exact revision, page, block, renderer, partition, and platform revisions;
- authorization class `user_management` or `operator_management` and a bounded
  authorization ID;
- one operation-compatible reason category:
  - Pin: `user_requested_pin` or `operator_requested_pin`;
  - Unpin: `user_requested_unpin` or `operator_requested_unpin`;
- the current lifecycle policy revision;
- fixed assertions that semantic payload, scope, formation snapshot, strength,
  memory kind, and formation stage are preserved;
- fixed assertions that no model generation, purge, restore, or content rewrite
  is requested.

The proposal digest includes the operation kind and every expected authority
binding. Changing direction, revision, authorization, reason, expected state,
or policy changes the input digest.

## Exact predecessor and successor

The predecessor must be the one canonical revision named by the exact singleton
selector and current receipt. It must have:

- the expected character and logical memory ID;
- exact expected revision, page, block, and digest bindings;
- `mutation_state: none` and `retrieval_eligible: true`;
- lifecycle `active` for Pin or `pinned` for Unpin;
- one resolvable formation-decision or lifecycle-transition authority;
- no later canonical revision for the same logical memory.

The successor preserves byte-equivalent logical values for grounded assessment
reference and content, subjective meaning, memory kind, formation stage, scope
binding, formation snapshot, all strength dimensions, character, and logical
memory identity. It changes only:

- revision number to exactly `N+1`;
- predecessor reference to exactly `N`;
- lifecycle state to `pinned` or `active`;
- immutable creation time;
- authorization to the exact lifecycle transition.

`retrieval_visible` remains true. Pin/Unpin cannot conceal Correct, Forget,
Restore, Consolidate, or any other payload/state mutation.

## Shared mutation and publication fence

Pin / Unpin uses the shared Subjective MEM lifecycle boundaries:

- one Evidence-space transaction lock;
- one logical `SubjectiveMemCurrentState` selector per character and memory;
- exact current revision, selector, receipt, page, block, and digest binding;
- one Character Workspace canonical Markdown page;
- one secure POSIX page-domain lock and atomic replacement path;
- one immutable post-image artifact;
- the shared lifecycle claim/intent/transition/receipt/result record family;
- the operation-neutral lifecycle publication, replay, and recovery engine;
- one projection state marked `rebuild_required` after finalization;
- deterministic idempotency and caller-invoked forward recovery.

Correct, Forget, Pin, and Unpin may have read-only proposals concurrently, but
the first valid apply reserves the singleton selector and wins. A later apply
from a stale revision, selector, receipt, page, or unsupported lifecycle state
fails closed.

## Deterministic identity and conflict

The idempotency slot is independent of proposal input and is derived from:

```text
evidence space
character authority digest
logical memory ID
operation family: pin_unpin
caller idempotency-key digest
```

The operation ID, transition ID, intent ID, and receipt ID then derive from the
slot plus an input digest containing the exact proposal, operation kind, and
operation time. The result ID derives from the slot.

Consequences:

- an exact retry resolves the same finalized result;
- the same key with changed proposal data is an integrity conflict;
- the same key reused for the inverse direction is an integrity conflict;
- Pin and Unpin cannot occupy independent slots under one raw key;
- raw idempotency keys are never persisted.

## Content-free durable records

Before canonical page replacement, Pin / Unpin stores one lifecycle operation
claim, one prepared lifecycle intent, and the singleton selector with
`mutation_state: prepared`.

After exact post-image verification, the shared publication engine and
operation-owned finalizer commit the exact lifecycle final state, including:

- one `SubjectiveMemLifecycleTransition`;
- one lifecycle receipt;
- one idempotency result;
- one intent finalization;
- the final singleton selector, whose `current_receipt_id` names the new
  lifecycle receipt;
- one `rebuild_required` projection-state log.

These artifacts contain bounded identifiers, digests, schemas, lifecycle
states, authorization class/ID, reason category, policy revision, times, and
receipt lineage only. They never contain grounded content, subjective meaning,
prompts, raw user reasons, filesystem paths, idempotency keys, or unrestricted
exception text.

No Pin/Unpin-specific durable current-state authority or second selector is
allowed. Lifecycle transition plus final selector state are the canonical Pin
authority.

## Exact replay

Replay success requires exact claim, intent, transition, receipt, idempotency
result, intent finalization, final selector, selector uniqueness, page digest,
predecessor block, successor block, operation direction, and lifecycle states.
An exact finalized retry returns the same transition, receipt, result, and final
selector without appending another revision. Partial, malformed, duplicate, or
cross-linked final records fail closed.

## Publication and recovery

Recovery is caller-invoked and forward-only:

1. **Exact pre-image plus valid prepared state**: publish the immutable original
   post-image after revalidating claim, intent, selector, receipt, and
   predecessor authority.
2. **Exact post-image plus missing final records**: finalize the original
   transition, receipt, result, selector, and projection state.
3. **Neither exact image**: mark the selector `recovery_required` and fail
   closed without overwriting the foreign page.
4. **Final records without the exact post-image**: fail closed and do not return
   success.

A durable pinned or active successor is never rolled back because receipt
delivery or finalization failed. No background worker, scanner, polling loop,
scheduler, or automatic repair is introduced.

## Failure model

Pin / Unpin fails closed for stale or non-current revision, wrong direction,
already-target state, hidden/held/superseded/purged/prepared/recovery/corrupt
state, missing or duplicate selector, changed receipt, foreign page/block,
payload or scope drift, unsupported authorization/reason, schema drift,
idempotency conflict, partial finalization, unsupported platform, unsafe path,
lock contention, and foreign image.

No failure path may silently treat Pin as active, Unpin as pinned, consult a
Primary MEM fallback, or leave both lifecycle states authoritative.

## Feature posture and rollback

Pin / Unpin uses the Subjective MEM lifecycle gate and remains default-off,
dry-run-capable, apply-enabled only with the secure canonical Subjective MEM
apply boundary, single-host, POSIX-apply-only, caller-invoked, and unwired from
ordinary Retrieval, API, UI, queue, worker, and scheduler paths unless a
separate current authority explicitly wires those surfaces.

Rollback before apply is configuration disablement. After a committed Pin or
Unpin, rollback is a new governed inverse lifecycle successor, never deletion
or in-place mutation of the committed revision.

## Validation anchors

The stable responsibility boundary is represented by current runtime and
focused validation surfaces including:

```text
relaylm/subjective_mem/pin.py
relaylm/subjective_mem_pin_runtime.py
relaylm/subjective_mem/lifecycle_engine.py
tests/test_subjective_mem_pin_runtime.py
scripts/relaylm_subjective_mem_pin_unpin_smoke.py
```

Generic lifecycle and consolidated smoke surfaces may also exercise this
boundary. Historical slice identifiers in test, smoke, or compatibility names
are validation anchors only; they are not semantic or architectural authority.

Validation must preserve:

- default-off and dry-run no-write behavior;
- exact Pin `active N -> pinned N+1` and Unpin `pinned N -> active N+1`;
- semantic payload, scope, stage, snapshot, strength, and kind preservation;
- final Retrieval eligibility and prepared-selector exclusion;
- exact replay without an extra revision;
- changed-input and cross-direction idempotency conflict;
- stale selector/receipt/page and wrong-direction rejection;
- hidden/held/superseded/purged/recovery/corrupt rejection;
- concurrent lifecycle first-writer behavior;
- pre-page and post-page crash recovery and foreign-image preservation;
- content-free records and projection;
- one shared evaluator and no second pin-state authority;
- no Primary MEM, API, UI, Retrieval, queue, worker, or scheduler invocation.

## Non-goals

Pin / Unpin does not own or authorize ordinary Subjective MEM
Retrieval/ranking/cache, API/UI, Correct, Forget, Restore, Consolidate, Merge,
Supersession, Purge, Primary MEM migration/dual-write/retirement,
model-generated Pin/Unpin, background recovery, multi-host publication,
non-POSIX apply, or user-data migration.
