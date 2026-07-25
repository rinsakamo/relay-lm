---
relaylm_doc_type: subsystem_architecture
relaylm_authority: subjective_mem_restore_runtime_architecture
relaylm_status: target
relaylm_volatility: high
relaylm_owner: memory
relaylm_update_trigger:
  - LC-1D Restore input, transition, tombstone release, persistence, or recovery changes
  - a later lifecycle operation changes restored-predecessor authority
  - RT-1 begins consuming restored lifecycle eligibility
relaylm_not_authoritative_for:
  - current runtime implementation or completion status
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
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - Subjective MEM runtime implementers
  - lifecycle reviewers
  - retrieval migration implementers
relaylm_authority_level: subsystem
---
# LC-1D Subjective MEM Restore Runtime

## Scope

LC-1D is the next bounded lifecycle slice after LC-1C. It defines one
caller-invoked, default-off Restore runtime on the canonical Markdown and
content-free operations boundaries established by ST-1 and the preceding
lifecycle slices.

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

## Normative state model

The accepted logical contract owns:

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

## Boundaries

Primary MEM Restore and Forget behavior is characterization evidence only.
LC-1D does not call or modify Primary MEM code, API, UI, ranking, cache, or
storage. It does not establish dual-write or old/new precedence. RT-1 remains the
future owner of ordinary readers, projection consumption, ranking, cache, usage
events, and hard cutover.

`relaylm/subjective_mem_restore_runtime.py` is the only Restore operation owner.
It owns proposal application, exact predecessor and Forget-lineage validation,
successor construction, tombstone release finalization, replay, and bounded
caller-invoked recovery.

```text
subjective_mem_restore_runtime
  -> subjective_mem_restore
  -> subjective_mem_lifecycle_authority
  -> subjective_mem_lifecycle_engine
  -> subjective_mem_reformation
  -> subjective_mem_markdown
  -> subjective_mem / evidence store / canonical commit I/O
```

The Restore owner must not import private Correct, Forget, or Pin/Unpin runtime
helpers and must not copy the shared lifecycle publication state machine.

## Shared predecessor authority

A restored active revision must be a valid predecessor for later Correct,
Forget, and Pin. Current code has more than one operation-local lifecycle
receipt validator and allowed-operation set. Adding `restore` independently to
each would create repeated semantic authority.

LC-1D therefore transfers exact current lifecycle receipt and transition
validation to one storage-neutral owner:

```text
relaylm/subjective_mem_lifecycle_authority.py
```

Its concrete current consumers are Correct, Forget, Pin/Unpin, and Restore. It
owns accepted committed lifecycle operations; exact receipt self-digest and
transition binding; memory, revision, selector, page, block, schema, and platform
bindings; predecessor authorization linkage; lifecycle-state compatibility; and
content-free record bindings for publication.

Operation owners retain their transition direction, proposal, reason,
authorization, payload, and successor rules. The implementation removes old
duplicated allowlists and private cross-runtime validation imports after all
current consumers use the shared owner. No fallback or wrapper-only alias remains.

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
  revision;
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

LC-1D adds one immutable content-free release record:

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

`relaylm/subjective_mem_reformation.py` remains the only anti-reformation
semantic evaluator:

```text
valid Forget tombstone without an exact release -> blocked
valid Forget tombstone with one exact release    -> no longer blocks
```

A missing, duplicate, malformed, dangling, cross-linked, digest-mismatched, or
non-monotonic release fails closed. Re-formation is allowed only when every exact
Forget tombstone for the semantic identity is valid and every one has an exact
release. A later Forget creates a new tombstone and blocks again independently.

## Mutation, identity, and finalization

LC-1D reuses one Evidence-space transaction lock, one logical current selector,
exact selector/receipt/page authority, one canonical Markdown page, one secure
POSIX page lock and atomic replacement path, one immutable post-image artifact,
the shared lifecycle claim/intent/transition/receipt/result/finalization family,
`rebuild_required` projection state, deterministic idempotency, and
caller-invoked forward recovery.

The idempotency slot derives from evidence space, character authority digest,
logical memory ID, operation family `restore`, and caller key digest. Operation,
transition, intent, receipt, release, and result IDs derive from that slot plus
the exact proposal and operation time. Raw keys are never persisted.

After exact active post-image verification, one Evidence-space transaction
inserts or exactly verifies:

- Restore lifecycle transition and receipt;
- Forget-tombstone release record and release-state event;
- lifecycle idempotency result and intent finalization;
- final active singleton selector;
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

## Failure model and posture

Stale revision, non-hidden state, missing or duplicate selector, changed receipt,
invalid Forget lineage, released tombstone, semantic mismatch, foreign page or
block, payload or scope drift, unsupported authorization or reason, schema drift,
idempotency conflict, partial finalization, unsupported platform, unsafe path,
lock contention, non-monotonic time, and foreign image fail closed.

No failure path may expose the hidden predecessor, ignore an effective tombstone,
create another logical memory, consult Primary MEM, or leave two current states.

LC-1D uses the existing lifecycle gate and remains default-off, dry-run-capable,
apply-enabled only with ST-1 secure apply, single-host, POSIX-apply-only,
caller-invoked, and unwired from ordinary Retrieval, API, UI, queue, worker, and
scheduler paths. After a committed Restore, reversal is a new governed Forget
successor with a new tombstone, never mutation or deletion.

## Implementation budget

The later implementation PR is bounded to:

```text
relaylm/subjective_mem_restore.py                         new
relaylm/subjective_mem_restore_runtime.py                 new
relaylm/subjective_mem_lifecycle_authority.py             new
relaylm/subjective_mem_lifecycle_runtime.py               shared-owner migration
relaylm/subjective_mem_forget_runtime.py                  shared-owner migration
relaylm/subjective_mem_pin_runtime.py                     shared-owner migration
relaylm/subjective_mem_reformation.py                     release evaluation
focused tests and one process smoke
existing consolidated smoke and registration surfaces only
```

Config, API, UI, Primary MEM, ordinary Retrieval, workflows, changed-matrix,
generated registries, and unrelated documentation are excluded. Return to P1 if
path count or diff grows materially, an existing file gains roughly 200 lines, a
file exceeds roughly 700 lines, a function exceeds roughly 80 lines, tests copy
production logic, or shared authority does not remove its current duplicates.

## Validation matrix

The implementation must prove default-off and dry-run no-write behavior; exact
`hidden N -> active N+1`; semantic preservation; prepared exclusion and final
eligibility; exact Forget/tombstone binding; content-free release authority;
blocked-before and released-after classification; later Forget re-blocking;
malformed and dangling release fail-closed; replay and idempotency conflict;
stale/wrong-state rejection; first-writer behavior; pre/post-page recovery;
foreign-image preservation; later Correct, Forget, and Pin acceptance of a
Restore predecessor through one shared owner; and absence of ordinary Retrieval,
Primary MEM, API/UI, background recovery, temporary artifacts, and branch-writing
validation.

The existing `runtime/subjective_mem_lifecycle` consolidated group remains the CI
owner. LC-1D extends it rather than creating a workflow or changing Lane R
changed-matrix authority.

## Non-goals

LC-1D excludes heuristic resurrection, merely-similar memory restoration, held or
purged restoration, physical deletion, Consolidate, RT-1, API/UI, ordinary
Retrieval cutover, Primary MEM migration, background recovery, and multi-host or
non-POSIX publication.
