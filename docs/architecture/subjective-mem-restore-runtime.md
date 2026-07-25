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

LC-1D is the next bounded Subjective MEM lifecycle slice after LC-1C Pin/Unpin.
It defines one caller-invoked, default-off Restore runtime on the canonical
Markdown and content-free operations boundaries established by ST-1 and the
preceding lifecycle slices.

```text
hidden revision N / mutation none / retrieval ineligible
  / exact effective Forget tombstone
    -> exact prepared Restore intent / retrieval fail-closed
    -> active revision N+1 / mutation none / retrieval eligible
    -> exact immutable tombstone release effective
```

Restore appends an immutable active successor. It never mutates or deletes the
hidden predecessor, the original Forget transition, receipt, or tombstone. It
does not infer that a memory should be restored and does not authorize
re-formation of another logical memory.

## Normative state model

The accepted logical contract owns Restore as:

```text
restore: hidden -> active
```

The predecessor must be the exact hidden revision selected by the singleton
`SubjectiveMemCurrentState`. During reservation and publication the selector is
fenced with `mutation_state: prepared` and `retrieval_eligible: false`.
Finalization advances the selector to the exact active successor with
`mutation_state: none` and `retrieval_eligible: true`.

Restore changes only lifecycle visibility and immutable revision metadata. It
preserves grounded assessment reference and content, subjective meaning,
character, logical memory identity, memory kind, formation stage, scope,
formation snapshot, and every strength dimension.

## Primary MEM characterization boundary

Existing Primary MEM Forget or UI behavior is characterization evidence only.
LC-1D does not call or modify Primary MEM restore, Forget, API, UI, ranking,
cache, or storage code. It does not create old/new precedence, dual-write, or a
compatibility projection.

RT-1 remains the sole future owner of ordinary Subjective MEM readers,
projection consumption, ranking, cache, usage events, and one-authority hard
cutover.

## One Restore operation owner

`relaylm/subjective_mem_restore_runtime.py` is the only Restore operation owner.
It owns proposal application, exact predecessor and Forget-lineage validation,
successor construction, tombstone release finalization, replay, and bounded
caller-invoked recovery.

The dependency direction is:

```text
subjective_mem_restore_runtime
  -> subjective_mem_restore
  -> subjective_mem_lifecycle_authority
  -> subjective_mem_lifecycle_engine
  -> subjective_mem_reformation
  -> subjective_mem_markdown
  -> subjective_mem / evidence store / canonical commit I/O
```

The Restore owner must not import a private Correct, Forget, or Pin/Unpin runtime
helper and must not copy the shared lifecycle publication state machine.

## Shared predecessor-authority owner

Restore produces an active current revision that must remain a valid predecessor
for later Correct, Forget, and Pin operations. The current code has more than
one operation-local allowlist and receipt validator for lifecycle predecessors.
Adding `restore` independently to each list would create repeated semantic
authority.

LC-1D therefore transfers exact current lifecycle receipt and transition
validation to one storage-neutral owner:

```text
relaylm/subjective_mem_lifecycle_authority.py
```

Its concrete current consumers are Correct, Forget, Pin/Unpin, and Restore. It
owns:

- accepted committed lifecycle operation kinds;
- exact receipt self-digest and transition binding;
- exact memory, revision, selector, page, block, schema, and platform bindings;
- exact predecessor authorization linkage;
- operation-compatible predecessor lifecycle state;
- content-free record binding returned to the lifecycle publication engine.

Operation owners retain their own transition direction, proposal, reason,
authorization, payload, and successor rules. No wrapper-only import alias or
fallback to the former validators is allowed. The old duplicated operation
allowlists and private cross-runtime imports are removed in the implementation
PR after all current consumers use the shared owner.

## Storage-neutral proposal authority

`relaylm/subjective_mem_restore.py` owns one bounded proposal and deterministic
identity shape. The proposal binds:

- exact memory ID and current hidden revision;
- exact current selector ID and digest;
- exact Forget lifecycle receipt ID and digest;
- exact Forget transition ID and digest;
- exact Forget tombstone ID and digest;
- exact semantic-identity digest;
- exact page, relative path, current block, and page digest;
- exact memory kind and formation stage;
- exact scope-binding and formation-snapshot digests;
- exact revision, page, block, renderer, partition, and platform revisions;
- authorization class `user_management` or `operator_management`;
- one bounded authorization ID;
- reason category `user_requested_restore` or `operator_requested_restore`;
- the current lifecycle policy revision;
- fixed assertions that semantic payload, scope, formation snapshot, strength,
  memory kind, and formation stage are preserved;
- fixed assertions that no generation, correction, purge, consolidation, or
  Primary MEM mutation is requested.

The proposal digest includes every expected authority binding. Changing the
revision, selector, Forget lineage, authorization, reason, page, schema, or
policy changes the input digest.

## Exact predecessor and successor

The predecessor must be the one canonical revision named by the exact singleton
selector and current Forget receipt. It must have:

- the expected character and logical memory ID;
- exact expected revision, page, block, and digest bindings;
- `lifecycle_state: hidden`;
- `mutation_state: none` and `retrieval_eligible: false`;
- `retrieval_visible: false`;
- authorization by the exact current Forget transition;
- one exact, currently effective Forget tombstone for the same semantic identity
  and hidden revision;
- no later canonical revision for the logical memory.

The successor preserves every semantic and scope value and changes only:

- revision number to exactly `N+1`;
- predecessor reference to exactly `N`;
- lifecycle state to `active`;
- `retrieval_visible` to true;
- immutable creation time;
- authorization to the exact Restore lifecycle transition.

Restore cannot operate on active, pinned, held, superseded, purged, prepared,
recovery-required, corrupt, missing-current, duplicate-current, or dangling
state.

## Immutable Forget-tombstone release

The original Forget tombstone remains immutable historical authority. Restore
never edits it and never reuses its `effective` field as mutable state.

LC-1D adds one immutable, content-free release record:

```text
schema: relaylm.subjective_mem_forget_tombstone_release.v1
record kind: subjective_mem_forget_tombstone_release
```

The release record binds exactly:

- release ID and self-digest;
- evidence space and character;
- semantic-identity digest;
- logical memory ID;
- hidden revision and restored active revision;
- original tombstone ID and digest;
- original Forget transition ID and digest;
- original Forget receipt ID and digest;
- Restore transition ID and digest;
- Restore receipt ID and digest;
- Restore authorization class, ID, reason, and policy revision;
- release time equal to Restore finalization time;
- `content_free: true`.

A singleton release-state log keyed by tombstone ID contains exactly one event
that binds the same release record and Restore lineage. The log is a rebuildable
current-state projection; the immutable release record and exact lifecycle
records are its authority.

`relaylm/subjective_mem_reformation.py` remains the only anti-reformation
semantic evaluator. For each exact valid Forget tombstone it must resolve one of
two states:

```text
no release record or release-state event
  -> blocked

one exact release record + release-state event + Restore transition/receipt
  -> that tombstone no longer blocks
```

A missing, duplicate, malformed, dangling, cross-linked, digest-mismatched, or
non-monotonic release fails closed. The evaluator returns `allowed` only when
every exact tombstone for the semantic identity is valid and every one has an
exact valid release. A later Forget creates a new immutable tombstone and blocks
again until that new tombstone is independently restored.

This is composition of immutable Forget and Restore authority, not fallback or
precedence between competing representations.

## Shared mutation fence

LC-1D reuses:

- one Evidence-space transaction lock;
- one logical current selector per character and memory;
- exact current revision, selector, receipt, page, block, and digest binding;
- one Character Workspace canonical Markdown page;
- one secure POSIX page-domain lock and atomic replacement path;
- one immutable post-image artifact;
- the shared lifecycle claim, intent, transition, receipt, result, and
  finalization record family;
- one projection state marked `rebuild_required` after finalization;
- deterministic idempotency and caller-invoked forward recovery.

Read-only proposals may coexist, but the first valid lifecycle reservation wins.
A stale Restore loses to any Correct, Forget, Pin/Unpin, Restore, or later
lifecycle mutation that changes the singleton selector, receipt, revision, page,
or tombstone authority.

## Deterministic identity and conflict

The idempotency slot derives from:

```text
evidence space
character authority digest
logical memory ID
operation family: restore
caller idempotency-key digest
```

The operation, transition, intent, receipt, release, and result IDs derive from
the slot plus the exact proposal input and operation time. Raw idempotency keys
are never persisted.

An exact retry resolves the same finalized result. The same key with changed
proposal data is an integrity conflict. A released tombstone cannot be released
a second time by a different Restore identity.

## Atomic finalization

Before page replacement, Restore writes one content-free claim and prepared
intent and fences the singleton selector.

After exact active post-image verification, one Evidence-space transaction
inserts or exactly verifies:

- one Restore lifecycle transition;
- one Restore lifecycle receipt;
- one Forget-tombstone release record;
- one release-state log event;
- one lifecycle idempotency result;
- one intent finalization;
- the final active singleton selector;
- one `rebuild_required` projection-state log.

The transaction revalidates the exact prepared selector, original Forget
receipt, transition, tombstone, tombstone state, and absence of another release.
A page can never become successfully active while anti-reformation still treats
the exact tombstone as effective, and a release can never become effective
without the exact active canonical successor.

## Replay and recovery

Exact replay requires the canonical active successor, final selector, Restore
transition and receipt, release record and state, result, finalization, and all
original Forget lineage to match exactly. Replay never appends another revision
or release.

Recovery is caller-invoked and forward-only:

1. **Exact hidden pre-image plus valid prepared state**: publish the original
   immutable active post-image after revalidating Forget and tombstone authority.
2. **Exact active post-image plus missing final records**: atomically finalize
   the original Restore receipt, selector, release, result, and projection.
3. **Neither exact image**: mark the selector `recovery_required` and fail closed
   without overwriting the foreign page.
4. **Final Restore or release records without the exact active post-image**: fail
   closed and never return success.

A durable active successor is never rolled back to the hidden predecessor because
receipt delivery or finalization failed. No background worker, scanner, polling
loop, scheduler, or automatic repair is introduced.

## Failure model

LC-1D fails closed for stale revision, non-hidden state, missing or duplicate
selector, changed receipt, invalid Forget transition or tombstone, already
released tombstone, semantic-identity mismatch, foreign page or block, payload or
scope drift, unsupported authorization or reason, schema drift, idempotency
conflict, partial finalization, unsupported platform, unsafe path, lock
contention, non-monotonic time, and foreign image.

No failure path may silently expose the hidden predecessor, ignore an effective
tombstone, create another logical memory, consult Primary MEM, or leave both
hidden and active current states authoritative.

## Feature posture and rollback

LC-1D uses the existing Subjective MEM lifecycle gate. It remains default-off,
dry-run-capable, apply-enabled only when ST-1 secure apply is enabled,
single-host, POSIX-apply-only, caller-invoked, and unwired from ordinary
Retrieval, API, UI, queue, worker, and scheduler paths.

Rollback before apply is configuration disablement. After a committed Restore,
rollback is a new governed Forget successor with a new tombstone, never deletion
or in-place mutation of the Restore revision or release record.

## Implementation boundary and change budget

The implementation PR is expected to own at most these bounded paths:

```text
relaylm/subjective_mem_restore.py                         new
relaylm/subjective_mem_restore_runtime.py                 new
relaylm/subjective_mem_lifecycle_authority.py             new
relaylm/subjective_mem_lifecycle_runtime.py               shared-authority migration
relaylm/subjective_mem_forget_runtime.py                  shared-authority migration
relaylm/subjective_mem_pin_runtime.py                     shared-authority migration
relaylm/subjective_mem_reformation.py                     exact release evaluation
Tests and one process smoke for the same boundary
Existing consolidated smoke and registration surfaces only
```

No config, API, UI, Primary MEM, ordinary Retrieval, workflow, changed-matrix,
generated registry, or unrelated documentation path belongs in LC-1D.

The implementation must return to P1 before continuing if the expected path count
or diff grows materially, an existing file gains roughly more than 200 lines, a
file grows beyond roughly 700 lines, a function grows beyond roughly 80 lines,
tests begin reproducing production logic, or the proposed shared authority does
not remove the duplicated current consumers in the same atomic PR.

## Validation matrix

The implementation suite must prove:

- default-off and dry-run no-write behavior;
- exact `hidden N -> active N+1` publication;
- semantic payload, scope, snapshot, strength, kind, and stage preservation;
- final eligibility and prepared-selector exclusion;
- exact Forget receipt, transition, tombstone, and semantic-identity binding;
- immutable release record and content-free state shape;
- anti-reformation blocked before Restore and allowed only after exact Restore;
- a later Forget blocks again independently;
- malformed, duplicate, dangling, cross-linked, or missing release fail-closed;
- exact replay without another revision or release;
- changed-input idempotency conflict;
- stale selector, receipt, page, tombstone, and wrong-state rejection;
- concurrent lifecycle first-writer behavior;
- pre-page and post-page crash recovery and foreign-image preservation;
- Correct, Forget, and Pin accept an exact committed Restore predecessor through
  the one shared authority owner;
- no ordinary Retrieval, Primary MEM, API/UI, background recovery, branch-writing
  validation, or temporary artifact.

The existing `runtime/subjective_mem_lifecycle` consolidated group remains the CI
owner. LC-1D extends that group rather than creating a workflow or changing Lane
R changed-matrix authority.

## Non-goals

LC-1D does not implement:

- heuristic resurrection or restoration of a merely similar memory;
- Restore of held, superseded, or purged state;
- physical purge or deletion of historical revisions and tombstones;
- Consolidate or RT-1;
- API or SOUL Lab UI;
- ordinary Retrieval or prior-reader retirement;
- Primary MEM migration or compatibility;
- background recovery;
- multi-host or non-POSIX canonical publication.
