---
relaylm_doc_type: subsystem_architecture
relaylm_authority: subjective_mem_restore_runtime_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Subjective MEM Restore input, transition, tombstone release, persistence, or recovery changes
  - lifecycle predecessor authority changes for restored revisions
  - ordinary Retrieval changes restored lifecycle-eligibility consumption
relaylm_not_authoritative_for:
  - current runtime implementation completion status
  - ordinary Subjective MEM Retrieval, ranking, cache, or request-path selection
  - API, UI, model-generated Restore decisions, or background recovery
  - Primary MEM restore, migration, retirement, or precedence
  - Correct, Forget, Pin/Unpin, Consolidate, or Purge behavior
relaylm_related_authority:
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - st1_subjective_mem_commit_runtime.md
  - lc1a_subjective_mem_correct.md
  - subjective-mem-forget-runtime.md
  - subjective-mem-pin-unpin-runtime.md
  - subjective-mem-lifecycle-publication-engine.md
  - project_execution_plan.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Subjective MEM runtime implementers
  - lifecycle reviewers
  - retrieval and anti-reformation reviewers
relaylm_authority_level: subsystem
---
# Subjective MEM Restore Runtime

Last reviewed: 2026-08-07 JST

## Scope

Restore owns one caller-invoked, default-off exact `hidden -> active` Subjective
MEM lifecycle transition on the canonical Markdown and content-free operations
boundaries shared by the lifecycle system.

```text
hidden revision N / mutation none / retrieval ineligible
  / exact effective Forget tombstone
    -> exact prepared Restore intent / retrieval fail-closed
    -> active revision N+1 / mutation none / retrieval eligible
    -> exact immutable tombstone release effective
```

Restore appends an immutable active successor. It never mutates or deletes the
hidden predecessor, original Forget transition, receipt, or tombstone. It does
not infer that a memory should be restored and does not authorize formation of a
second logical memory.

Current implementation completion and feature posture remain owned by
`docs/PROJECT_STATUS.md`. Exact schema and transition requirements remain owned
by the Subjective MEM contracts.

## Normative state model

The Subjective MEM logical contract owns:

```text
restore: hidden -> active
```

The predecessor is the exact hidden revision selected by the singleton
`SubjectiveMemCurrentState`. Reservation fences that selector with
`mutation_state: prepared` and `retrieval_eligible: false`. Finalization advances
it to the exact active successor with `mutation_state: none` and
`retrieval_eligible: true`.

Restore changes only lifecycle visibility and immutable revision metadata. It
preserves grounded assessment reference and content, subjective meaning,
character, logical memory identity, memory kind, formation stage, scope,
formation snapshot, and every strength dimension.

## Responsibility and dependency boundary

Primary MEM Restore and Forget behavior is characterization or historical
boundary evidence only. Subjective MEM Restore does not call or modify Primary
MEM code, API, UI, ranking, cache, or storage and does not establish dual-write
or old/new precedence. Ordinary Subjective MEM Retrieval remains the owner of
candidate consumption, ranking, cache, usage events, and request-path authority.

`relaylm/subjective_mem_restore_runtime.py` is the Restore operation owner. It
owns proposal application, exact predecessor and Forget-lineage validation,
successor construction, tombstone-release finalization, exact replay, and
bounded caller-invoked recovery.

```text
subjective_mem_restore_runtime
  -> subjective_mem_restore
  -> subjective_mem_restore_plan
  -> subjective_mem_restore_replay
  -> subjective_mem_lifecycle_authority
  -> subjective_mem_lifecycle_engine
  -> subjective_mem_reformation
  -> subjective_mem_tombstone_release
  -> subjective_mem_markdown
  -> subjective_mem / evidence store / canonical commit I/O
```

The Restore owner does not import private Correct, Forget, or Pin/Unpin runtime
helpers and does not duplicate the shared lifecycle publication state machine.

## Shared predecessor authority

A restored active revision must remain a valid predecessor for later lifecycle
operations. Exact committed lifecycle receipt and transition validation therefore
belongs to the storage-neutral owner:

```text
relaylm/subjective_mem/lifecycle_authority.py
```

Current lifecycle consumers use that owner to resolve accepted committed
lifecycle operations, exact receipt self-digest and transition binding, memory,
revision, selector, page, block, schema, and platform bindings, predecessor
authorization linkage, lifecycle-state compatibility, and content-free record
bindings required for publication.

Operation owners retain their own transition direction, proposal, reason,
authorization, payload, and successor rules. There is no fallback private
allowlist or wrapper-only alternate predecessor authority.

## Proposal authority

`relaylm/subjective_mem_restore.py` owns one bounded proposal and deterministic
identity shape. The proposal binds:

- exact memory ID and current hidden revision;
- exact singleton selector ID and digest;
- exact Forget receipt, transition, and tombstone IDs and digests;
- exact semantic-identity digest;
- exact page, relative path, current block, and page digest;
- exact memory kind and formation stage;
- exact scope-binding and formation-snapshot digests;
- exact revision, page, block, renderer, partition, and platform revisions;
- authorization class `user_management` or `operator_management` and a bounded ID;
- reason `user_requested_restore` or `operator_requested_restore`;
- current lifecycle policy revision;
- fixed preservation assertions and explicit exclusion of generation, correction,
  purge, consolidation, and Primary MEM mutation.

Changing any expected authority binding changes the proposal input digest.

## Exact predecessor and successor

The predecessor must be the one canonical revision named by the exact singleton
selector and current Forget receipt. It must have:

- expected character and logical memory ID;
- exact revision, page, block, and digest bindings;
- `lifecycle_state: hidden` and `retrieval_visible: false`;
- `mutation_state: none` and `retrieval_eligible: false`;
- authorization by the exact current Forget transition;
- one exact effective Forget tombstone for the same semantic identity and hidden
  revision; and
- no later canonical revision for the logical memory.

The successor preserves every semantic and scope value and changes only revision
to `N+1`, predecessor reference to `N`, lifecycle to `active`,
`retrieval_visible` to true, immutable creation time, and authorization to the
exact Restore transition.

Active, pinned, held, superseded, purged, prepared, recovery-required, corrupt,
missing-current, duplicate-current, and dangling state fail closed.

## Immutable tombstone release

The Forget tombstone remains immutable historical authority. Restore never edits
it or treats its original `effective` field as mutable state.

Restore uses one immutable content-free release record:

```text
schema: relaylm.subjective_mem_forget_tombstone_release.v1
record kind: subjective_mem_forget_tombstone_release
```

It binds release ID and self-digest; evidence space and character;
semantic-identity digest; logical memory; hidden and restored revisions; original
tombstone, Forget transition, and Forget receipt IDs and digests; Restore
transition and receipt IDs and digests; Restore authorization, reason, policy,
and finalization time; and `content_free: true`.

A singleton release-state log keyed by tombstone ID contains exactly one event
binding the same release and Restore lineage. It is a rebuildable projection; the
immutable release and exact lifecycle records are authority.

`relaylm/subjective_mem_reformation.py` remains the anti-reformation semantic
evaluator:

```text
valid Forget tombstone without an exact release -> blocked
valid Forget tombstone with one exact release    -> no longer blocks
```

A missing, duplicate, malformed, dangling, cross-linked, digest-mismatched, or
non-monotonic release fails closed. Re-formation is allowed only when every exact
Forget tombstone for the semantic identity is valid and every one has an exact
release. A later Forget creates a new tombstone and blocks again independently.

## Mutation, identity, publication, and finalization

Restore uses one Evidence-space transaction lock, one logical current selector,
exact selector/receipt/page authority, one canonical Markdown page, one secure
POSIX page lock and atomic replacement path, one immutable post-image artifact,
the shared lifecycle claim/intent/transition/receipt/result/finalization family,
`rebuild_required` projection state, deterministic idempotency, and
caller-invoked forward recovery.

The operation-neutral lifecycle engine owns reservation, canonical publication,
shared finalized replay, and recovery classification. Restore-specific plan and
replay owners bind the extra Forget lineage and tombstone-release authority that
must finalize atomically with the lifecycle successor.

The idempotency slot derives from evidence space, character authority digest,
logical memory ID, operation family `restore`, and caller key digest. Operation,
transition, intent, receipt, release, and result IDs derive from that slot plus
the exact proposal and operation time. Raw keys are never persisted.

After exact active post-image verification, one Evidence-space transaction
inserts or exactly verifies:

- Restore lifecycle transition and receipt;
- Forget-tombstone release record and release-state event;
- lifecycle idempotency result and intent finalization;
- final active singleton selector; and
- `rebuild_required` projection state.

The transaction revalidates the prepared selector, original Forget receipt,
transition, tombstone and state, and absence of another release. The page cannot
be successfully active while the exact tombstone still blocks, and a release
cannot become effective without the exact active canonical successor.

## Replay and recovery

Exact replay requires the active successor, final selector, Restore transition
and receipt, release record and state, result, finalization, and original Forget
lineage to match. Replay appends no revision or release.

Recovery is caller-invoked and forward-only:

1. Exact hidden pre-image plus valid prepared state publishes the original active
   post-image after revalidation.
2. Exact active post-image plus missing final records atomically finalizes the
   original receipt, selector, release, result, and projection.
3. Neither exact image marks the selector `recovery_required` and preserves the
   foreign page.
4. Final Restore or release records without the exact active post-image never
   return success.

No background worker, scanner, scheduler, polling, or automatic repair is added.
A durable active successor is never rolled back to its hidden predecessor because
receipt delivery or finalization failed.

## Failure model and feature posture

Stale revision, non-hidden state, missing or duplicate selector, changed receipt,
invalid Forget lineage, released tombstone, semantic mismatch, foreign page or
block, payload or scope drift, unsupported authorization or reason, schema drift,
idempotency conflict, partial finalization, unsupported platform, unsafe path,
lock contention, non-monotonic time, and foreign image fail closed.

No failure path may expose the hidden predecessor, ignore an effective tombstone,
create another logical memory, consult Primary MEM, or leave two current states.

Restore uses the Subjective MEM lifecycle apply boundary and remains default-off,
dry-run-capable, apply-enabled only with secure canonical apply, single-host,
POSIX-apply-only, caller-invoked, and unwired from ordinary Retrieval, API, UI,
queue, worker, and scheduler paths unless a separate current authority explicitly
wires those surfaces. After a committed Restore, reversal is a new governed
Forget successor with a new tombstone, never mutation or deletion.

## Validation anchors

The stable responsibility boundary is represented by current runtime and focused
validation surfaces including:

```text
relaylm/subjective_mem_restore.py
relaylm/subjective_mem_restore_plan.py
relaylm/subjective_mem_restore_runtime.py
relaylm/subjective_mem_restore_replay.py
relaylm/subjective_mem/lifecycle_authority.py
relaylm/subjective_mem_lifecycle_engine.py
relaylm/subjective_mem_reformation.py
relaylm/subjective_mem_tombstone_release.py
tests/test_subjective_mem_restore_runtime.py
tests/test_subjective_mem_restore_finalization.py
```

Generic lifecycle and consolidated smoke surfaces may also exercise this
boundary. Historical slice identifiers in test, smoke, or compatibility names
are validation anchors only; they are not semantic or architectural authority.

Validation must preserve default-off and dry-run no-write behavior; exact
`hidden N -> active N+1`; semantic preservation; prepared exclusion and final
eligibility; exact Forget/tombstone binding; content-free release authority;
blocked-before and released-after classification; later Forget re-blocking;
malformed and dangling release fail-closed; exact replay and idempotency conflict;
stale/wrong-state rejection; first-writer behavior; pre/post-page recovery;
foreign-image preservation; later lifecycle acceptance of a restored predecessor
through one shared predecessor owner; and absence of ordinary Retrieval, Primary
MEM, API/UI, background recovery, or a second lifecycle authority.

## Non-goals

Restore does not own or authorize heuristic resurrection, merely-similar memory
restoration, held or purged restoration, physical deletion, Consolidate, API/UI,
ordinary Retrieval cutover, Primary MEM migration, background recovery, or
multi-host or non-POSIX publication.
