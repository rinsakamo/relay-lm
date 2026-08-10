---
relaylm_doc_type: subsystem_architecture
relaylm_authority: subjective_mem_consolidate_runtime_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Subjective MEM Consolidate input, policy authorization, transition, persistence, or recovery changes
  - lifecycle predecessor authority changes for consolidated revisions
  - ordinary Retrieval changes Secondary Subjective MEM eligibility consumption
relaylm_not_authoritative_for:
  - current runtime implementation completion status
  - candidate discovery, usage thresholds, scheduling, or policy-model selection
  - ordinary Subjective MEM Retrieval, ranking, cache, or request-path selection
  - API, UI, background recovery, or Primary MEM consolidation
  - Correct, Forget, Pin/Unpin, Restore, relation, supersession, merge, or Purge behavior
relaylm_related_authority:
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - st1_subjective_mem_commit_runtime.md
  - lc1a_subjective_mem_correct.md
  - subjective-mem-forget-runtime.md
  - subjective-mem-pin-unpin-runtime.md
  - subjective-mem-restore-runtime.md
  - subjective-mem-lifecycle-publication-engine.md
  - project_execution_plan.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Subjective MEM runtime implementers
  - RelayMEM policy and lifecycle reviewers
  - retrieval and integrity reviewers
relaylm_authority_level: subsystem
---
# Subjective MEM Consolidate Runtime

Last reviewed: 2026-08-07 JST

## Scope

Consolidate owns one caller-invoked, default-off exact transformation of the
current active Primary revision into an immutable active Secondary successor on
the canonical Subjective MEM Markdown and content-free lifecycle boundaries.

```text
active Primary revision N / mutation none / retrieval eligible
  -> exact prepared Consolidate intent / retrieval fail-closed
  -> active Secondary revision N+1 / mutation none / retrieval eligible
```

Consolidate appends one immutable successor for the same logical memory. It does
not merge multiple memories, synthesize a summary, rewrite meaning, change
memory kind, or select a candidate by similarity, usage count, age, or recency.

Current implementation completion and feature posture remain owned by
`docs/PROJECT_STATUS.md`. Exact schema and transition requirements remain owned
by the Subjective MEM contracts.

## Normative state model

The Subjective MEM logical contract owns:

```text
consolidate: active Primary -> active Secondary
```

The predecessor is the exact active Primary revision selected by the singleton
`SubjectiveMemCurrentState`. Reservation fences that selector with
`mutation_state: prepared` and `retrieval_eligible: false`. Finalization advances
it to the exact active Secondary successor with `mutation_state: none` and
`retrieval_eligible: true`.

Consolidation changes only immutable revision metadata and `formation_stage` from
`primary` to `secondary`. It preserves grounded assessment reference and content,
subjective meaning, character, logical memory identity, memory kind, scope,
formation snapshot, lifecycle state, retrieval visibility, and every strength
dimension.

A Secondary predecessor cannot be consolidated again. Pinned, held, hidden,
superseded, purged, prepared, recovery-required, corrupt, missing-current,
duplicate-current, dangling-current, or non-current revisions fail closed.

## Responsibility and dependency boundary

Primary MEM and legacy consolidation behavior are characterization or historical
boundary evidence only. Subjective MEM Consolidate does not call or modify
Primary MEM code, queue, worker, scheduler, API, UI, ranking, cache, or storage
and does not establish dual-write or old/new precedence. Ordinary Subjective MEM
Retrieval remains the owner of candidate consumption, ranking, cache, durable
usage events, and request-path authority.

`relaylm/subjective_mem_consolidate_runtime.py` is the Consolidate operation
owner. It owns proposal application, exact predecessor validation, successor
construction, operation-specific finalization, replay mapping, and bounded
caller-invoked forward recovery while using the shared lifecycle publication
engine for operation-neutral mechanics.

```text
subjective_mem_consolidate_runtime
  -> subjective_mem_consolidate
  -> subjective_mem_lifecycle_authority
  -> subjective_mem_lifecycle_engine
  -> subjective_mem_markdown
  -> subjective_mem / evidence store / canonical commit I/O
```

The Consolidate owner does not import private Correct, Forget, Pin/Unpin, or
Restore runtime helpers and does not duplicate the shared lifecycle publication
state machine.

## Policy proposal authority

`relaylm/subjective_mem_consolidate.py` owns one bounded storage-neutral proposal
and deterministic identity shape. The current bounded runtime accepts exactly one
authorization class:

```text
relaymem_policy
```

The proposal binds:

- exact memory ID and current active Primary revision;
- exact singleton selector ID and digest;
- exact current lifecycle receipt ID and digest;
- exact current predecessor authorization kind, ID, and digest;
- exact page, relative path, current block, and page digest;
- exact memory kind and `formation_stage: primary`;
- exact scope-binding, formation-snapshot, and strength digests;
- exact revision, page, block, renderer, partition, and platform revisions;
- one bounded RelayMEM policy authorization ID and exact policy revision;
- one bounded reason category `policy_authorized_consolidation`;
- fixed preservation assertions and explicit exclusion of generation, correction,
  relation, supersession, merge, lifecycle visibility changes, and Primary MEM
  mutation.

Changing any expected authority binding changes the proposal input digest.

An active Primary revision may still be revision 1, whose exact authority is the
formation decision rather than a lifecycle transition. Consolidate therefore
binds the generic current authorization selected by the shared predecessor
authority and never requires an unrelated prior lifecycle operation:

```text
expected_current_authorization_kind
expected_current_authorization_id
expected_current_authorization_digest
```

The accepted kinds are exactly the two returned by the shared authority:

```text
revision 1                          subjective_mem_decision
later committed lifecycle revision subjective_mem_lifecycle_transition
```

The runtime compares all three values to the exact loaded predecessor authority
and the canonical digest of its exact authorization record. No transition-only
alias, compatibility fallback, dual field name, or precedence rule exists.

`authorization_id` on the proposal is a different value: it is the new
Consolidate operation's RelayMEM policy authorization ID. It is bound and
persisted through the shared lifecycle intent, transition, and receipt family
together with the authorization class, reason category, and exact policy
revision. No separate durable policy-authorization record schema is introduced.
The proposal must carry exactly `CONSOLIDATE_POLICY_REVISION`; a well-formed but
different policy revision fails closed.

This architecture does not define how policy discovers or prioritizes
candidates. No usage threshold, age threshold, retrieval count, embedding,
lexical similarity, LLM decision, queue, worker, or scheduler is authorized. The
caller supplies one exact proposal produced under a separately identified
RelayMEM policy revision; the runtime validates that authority but does not
re-create or infer the policy decision.

User-management and operator-management authorization are not accepted by this
bounded Consolidate authority. Adding another authorization class requires an
explicit authority change and cannot occur through a permissive fallback.

## Exact predecessor and successor

The predecessor must be the one canonical revision named by the exact singleton
selector and current receipt. It must have:

- expected character and logical memory ID;
- exact revision, page, block, and digest bindings;
- `lifecycle_state: active` and `retrieval_visible: true`;
- `formation_stage: primary`;
- `mutation_state: none` and `retrieval_eligible: true`;
- one exact current authorization lineage accepted by the shared predecessor
  authority; and
- no later canonical revision for the logical memory.

The successor preserves every semantic, scope, strength, and lifecycle value and
changes only:

- memory revision to `N+1`;
- predecessor reference to `N`;
- formation stage to `secondary`;
- immutable creation time; and
- authorization to the exact Consolidate lifecycle transition.

The successor remains on the same canonical page. Current page partitioning is
owned by character and memory kind, not formation stage. Consolidate appends a
block to the exact existing page and does not move, rename, split, or duplicate
the logical memory.

## Shared predecessor authority

A consolidated Secondary revision must remain a valid predecessor for later
Correct, Forget, Pin/Unpin, and any governed operation that accepts an active
Secondary current revision.

The storage-neutral predecessor authority remains the owner of committed
lifecycle receipt and transition validation. Its bounded operation
specification includes Consolidate's exact lifecycle and formation-stage change
without creating an operation-local fallback or second receipt validator:

```text
correct      active -> active     stage preserved   lifecycle policy revision
forget       active -> hidden     stage preserved   lifecycle policy revision
pin          active -> pinned     stage preserved   lifecycle policy revision
unpin        pinned -> active     stage preserved   lifecycle policy revision
restore      hidden -> active     stage preserved   lifecycle policy revision
consolidate  active -> active     primary -> secondary
             relaymem_policy / policy_authorized_consolidation
             consolidation policy revision
```

An operation that does not name a formation-stage change still requires both ends
of its committed transition to equal the exact predecessor stage, so no other
operation can widen the stage boundary. A named change is compared against both
the specification and the exact committed revision, so only Consolidate may have
produced a Secondary revision. Authorization class and reason category are bound
here only for Consolidate; every other operation keeps its owner-bounded
authority unchanged.

Operation owners retain their transition direction, proposal, reason,
authorization, payload, and successor rules. Consolidate never broadens another
operation's accepted lifecycle or formation-stage boundary.

## Mutation, identity, publication, and finalization

Consolidate uses one Evidence-space transaction lock, one logical current
selector, exact selector/receipt/page authority, one canonical Markdown page,
one secure POSIX page lock and atomic replacement path, one immutable post-image
artifact, the shared lifecycle claim/intent/transition/receipt/result/finalization
family, `rebuild_required` projection state, deterministic idempotency, and
caller-invoked forward recovery.

The operation-neutral lifecycle engine owns reservation, canonical publication,
shared finalized replay, and recovery classification. Consolidate supplies the
exact operation-owned finalizer and predecessor bindings needed to atomically
commit the Primary-to-Secondary successor.

The idempotency slot derives from evidence space, character authority digest,
logical memory ID, operation family `consolidate`, and caller key digest.
Operation, transition, intent, receipt, and result IDs derive from that slot plus
the exact proposal and operation time. Raw keys are never persisted.

After exact Secondary post-image verification, one Evidence-space transaction
inserts or exactly verifies:

- Consolidate lifecycle transition and receipt;
- lifecycle idempotency result and intent finalization;
- final active Secondary singleton selector; and
- `rebuild_required` projection state.

The transition records:

```text
operation: consolidate
from_lifecycle_state: active
to_lifecycle_state: active
from_formation_stage: primary
to_formation_stage: secondary
authorized_by: relaymem_policy
```

The transaction revalidates the prepared selector, current receipt, predecessor
authority, proposal policy binding, and exact page state. It creates no
tombstone, release, relation, merge record, supersession record, usage event, or
second memory body.

## Replay and recovery

Exact replay requires the Secondary successor, final selector, Consolidate
transition and receipt, result, intent finalization, and predecessor authority to
match. Replay appends no revision.

Recovery is caller-invoked and forward-only:

1. Exact active Primary pre-image plus valid prepared state publishes the original
   Secondary post-image after authority revalidation.
2. Exact active Secondary post-image plus missing final records atomically
   finalizes the original receipt, selector, result, and projection state.
3. Neither exact image marks the selector `recovery_required` and preserves the
   foreign page.
4. Final Consolidate records without the exact Secondary post-image never return
   success.

No background worker, scanner, scheduler, polling, automatic repair, or semantic
regeneration is added. A durable Secondary successor is never rolled back to its
Primary predecessor because receipt delivery or finalization failed.

## Failure model and feature posture

Stale revision, non-active lifecycle, non-Primary formation stage, missing or
duplicate selector, changed receipt, invalid predecessor lineage, foreign page or
block, payload, scope, strength, or memory-kind drift, unsupported policy
authorization or reason, schema drift, idempotency conflict, partial
finalization, unsupported platform, unsafe path, lock contention, non-monotonic
time, and foreign image fail closed.

No failure path may expose a prepared selector, modify semantic content, create a
second logical memory, consult Primary MEM, accept a merely similar memory, or
leave two current states.

Consolidate uses the existing Subjective MEM lifecycle gate and remains
default-off, dry-run-capable, apply-enabled only with secure canonical apply,
single-host, POSIX-apply-only, caller-invoked, and unwired from ordinary
Retrieval, API, UI, queue, worker, and scheduler paths unless a separate current
authority explicitly wires those surfaces.

The gate is the exact existing configuration triple, not a single boolean. Both
the lifecycle gate and the lower Subjective MEM commit gate are read as
`(enabled, dry_run_only, apply_enabled)` and must be one of exactly:

```text
disabled  (False, True,  False)
dry-run   (True,  True,  False)
apply     (True,  False, True)
```

Enforcement is bounded and operation-local; Consolidate introduces no
configuration field and no general-purpose gate resolver:

- lifecycle `disabled` returns a bounded `disabled` outcome for any caller mode,
  distinct from dry-run;
- lifecycle `dry-run` with a caller that does not request apply returns
  content-free dry-run readiness;
- lifecycle `dry-run` with a caller that requests apply fails closed, so a caller
  cannot escalate a configured dry-run mode;
- canonical publication requires the lifecycle triple to be exactly `apply`, the
  lower commit triple to be exactly `apply`, and the caller to request apply;
- lifecycle `apply` with the lower commit gate `disabled` or `dry-run` fails
  closed because lower commit apply authority is mandatory;
- lifecycle `apply` with a caller that does not request apply stays content-free
  dry-run; and
- non-boolean values, unsupported triples, and lifecycle/commit dependency
  mismatches fail closed before the first durable read.

Every rejected and every non-apply path writes no post-image artifact, lifecycle
claim, intent, transition, receipt, idempotency result, selector event, or
canonical page byte.

## Validation anchors

The stable responsibility boundary is represented by current runtime and focused
validation surfaces including:

```text
relaylm/subjective_mem_consolidate.py
relaylm/subjective_mem_consolidate_runtime.py
relaylm/subjective_mem/lifecycle_authority.py
relaylm/subjective_mem/lifecycle_engine.py
tests/test_subjective_mem_consolidate_runtime.py
```

Generic lifecycle and consolidated smoke surfaces also exercise this boundary.
Historical slice identifiers in test, smoke, or compatibility names are
validation anchors only; they are not semantic or architectural authority.

Validation must preserve:

- default-off and dry-run no-write behavior;
- exact `active Primary N -> active Secondary N+1`;
- lifecycle, semantic, scope, memory-kind, formation-snapshot, and strength
  preservation;
- prepared exclusion and final eligibility;
- exact RelayMEM policy authorization and policy-revision binding;
- rejection of user/operator fallback under the current authority;
- same-page append with no move or duplicate current memory;
- exact replay and idempotency conflict;
- stale, Secondary, pinned, hidden, held, superseded, purged, and wrong-state
  rejection;
- first-writer behavior and selector fencing;
- pre/post-page forward recovery and foreign-image preservation;
- later lifecycle acceptance of a Consolidate predecessor through one shared
  predecessor authority; and
- absence of relation, merge, supersession, tombstone, usage-event, ordinary
  Retrieval, Primary MEM, API/UI, background recovery, or a second semantic
  authority.

## Non-goals

Consolidate does not own or authorize policy candidate discovery, automatic
scheduling, usage-based selection, summarization, semantic merge, duplicate
collapse, relation creation, supersession, strength change, lifecycle visibility
change, Primary MEM consolidation or migration, ordinary Retrieval cutover,
API/UI, background recovery, Purge, multi-host coordination, or non-POSIX
publication.
