---
relaylm_doc_type: subsystem_architecture
relaylm_authority: subjective_mem_consolidate_runtime_architecture
relaylm_status: target
relaylm_volatility: high
relaylm_owner: memory
relaylm_update_trigger:
  - LC-1E Consolidate input, policy authorization, transition, persistence, or recovery changes
  - a later lifecycle operation changes consolidated-predecessor authority
  - RT-1 begins consuming Secondary Subjective MEM eligibility
relaylm_not_authoritative_for:
  - current runtime implementation or completion status
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
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - Subjective MEM runtime implementers
  - RelayMEM policy and lifecycle reviewers
  - retrieval migration implementers
relaylm_authority_level: subsystem
---
# LC-1E Subjective MEM Consolidate Runtime

## Scope

LC-1E is the next bounded lifecycle slice after LC-1D. It defines one
caller-invoked, default-off Consolidate runtime on the canonical Markdown and
content-free operations boundaries established by ST-1 and the preceding
lifecycle slices.

```text
active Primary revision N / mutation none / retrieval eligible
  -> exact prepared Consolidate intent / retrieval fail-closed
  -> active Secondary revision N+1 / mutation none / retrieval eligible
```

Consolidate appends one immutable successor for the same logical memory. It does
not merge multiple memories, synthesize a summary, rewrite meaning, change
memory kind, or select a candidate by similarity, usage count, age, or recency.

## Normative state model

The accepted logical contract owns:

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

## Boundaries

Primary MEM and legacy consolidation behavior are characterization evidence only.
LC-1E does not call or modify Primary MEM code, queue, worker, scheduler, API, UI,
ranking, cache, or storage. It does not establish dual-write or old/new
precedence. RT-1 remains the future owner of ordinary readers, projection
consumption, ranking, cache, durable usage events, and hard cutover.

`relaylm/subjective_mem_consolidate_runtime.py` is the only Consolidate operation
owner. It owns proposal application, exact predecessor validation, successor
construction, publication, finalization, replay, and bounded caller-invoked
recovery.

```text
subjective_mem_consolidate_runtime
  -> subjective_mem_consolidate
  -> subjective_mem_lifecycle_authority
  -> subjective_mem_lifecycle_engine
  -> subjective_mem_markdown
  -> subjective_mem / evidence store / canonical commit I/O
```

The Consolidate owner must not import private Correct, Forget, Pin/Unpin, or
Restore runtime helpers and must not copy the shared lifecycle publication state
machine.

## Policy proposal authority

`relaylm/subjective_mem_consolidate.py` owns one bounded storage-neutral proposal
and deterministic identity shape. The first LC-1E slice accepts exactly one
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
ST-1 formation decision rather than a lifecycle transition. Consolidate therefore
binds the generic current authorization the shared predecessor authority already
selects, and never requires an unrelated prior lifecycle operation:

```text
expected_current_authorization_kind
expected_current_authorization_id
expected_current_authorization_digest
```

The accepted kinds are exactly the two the shared authority returns:

```text
revision 1                        subjective_mem_decision
later committed lifecycle revision subjective_mem_lifecycle_transition
```

The runtime compares all three to the exact loaded predecessor authority and to
the canonical digest of its exact authorization record. No transition-only alias,
compatibility fallback, dual field name, or precedence rule exists.

`authorization_id` on the proposal is a different value: it is the new Consolidate
operation's RelayMEM policy authorization ID. It is bound and persisted through
the existing lifecycle intent, transition, and receipt family together with the
authorization class, reason category, and exact policy revision. No new durable
policy-authorization record schema is introduced. The proposal must carry exactly
`CONSOLIDATE_POLICY_REVISION`; a well-formed but different policy revision fails
closed.

This architecture does not define how a policy discovers or prioritizes
candidates. No usage threshold, age threshold, retrieval count, embedding,
lexical similarity, LLM decision, queue, worker, or scheduler is authorized.
The caller must provide one exact proposal produced under a separately identified
RelayMEM policy revision. The runtime validates that authority but does not
re-create or infer the policy decision.

User-management and operator-management authorization are not included in the
first bounded runtime. Adding them later requires an explicit authority update;
they cannot be accepted through a permissive fallback.

## Exact predecessor and successor

The predecessor must be the one canonical revision named by the exact singleton
selector and current receipt. It must have:

- expected character and logical memory ID;
- exact revision, page, block, and digest bindings;
- `lifecycle_state: active` and `retrieval_visible: true`;
- `formation_stage: primary`;
- `mutation_state: none` and `retrieval_eligible: true`;
- one exact current authorization lineage accepted by the shared predecessor
  authority;
- no later canonical revision for the logical memory.

The successor preserves every semantic, scope, strength, and lifecycle value and
changes only:

- memory revision to `N+1`;
- predecessor reference to `N`;
- formation stage to `secondary`;
- immutable creation time;
- authorization to the exact Consolidate lifecycle transition.

The successor remains on the same canonical page. Current page partitioning is
owned by character and memory kind, not formation stage. LC-1E therefore appends
a block to the exact existing page and does not move, rename, split, or duplicate
the logical memory.

## Shared predecessor authority

A consolidated Secondary revision must remain a valid predecessor for later
Correct, Forget, Pin/Unpin, and any later governed operation that accepts an
active Secondary current revision.

The existing storage-neutral predecessor authority remains the only owner of
committed lifecycle receipt and transition validation. LC-1E extends that owner
to accept a valid committed `consolidate` predecessor exactly once and removes
any operation-local allowlist that would otherwise duplicate the semantic. No
fallback, compatibility wrapper, or second receipt validator is added.

That owner replaces its lifecycle-direction table with one bounded operation
specification per accepted operation:

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

## Mutation, identity, and finalization

LC-1E reuses one Evidence-space transaction lock, one logical current selector,
exact selector/receipt/page authority, one canonical Markdown page, one secure
POSIX page lock and atomic replacement path, one immutable post-image artifact,
the shared lifecycle claim/intent/transition/receipt/result/finalization family,
`rebuild_required` projection state, deterministic idempotency, and
caller-invoked forward recovery.

The idempotency slot derives from evidence space, character authority digest,
logical memory ID, operation family `consolidate`, and caller key digest.
Operation, transition, intent, receipt, and result IDs derive from that slot plus
the exact proposal and operation time. Raw keys are never persisted.

After exact Secondary post-image verification, one Evidence-space transaction
inserts or exactly verifies:

- Consolidate lifecycle transition and receipt;
- lifecycle idempotency result and intent finalization;
- final active Secondary singleton selector;
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

## Failure model and posture

Stale revision, non-active lifecycle, non-Primary formation stage, missing or
duplicate selector, changed receipt, invalid predecessor lineage, foreign page or
block, payload, scope, strength, or memory-kind drift, unsupported policy
authorization or reason, schema drift, idempotency conflict, partial
finalization, unsupported platform, unsafe path, lock contention, non-monotonic
time, and foreign image fail closed.

No failure path may expose a prepared selector, modify semantic content, create a
second logical memory, consult Primary MEM, accept a merely similar memory, or
leave two current states.

LC-1E uses the existing lifecycle gate and remains default-off, dry-run-capable,
apply-enabled only with ST-1 secure apply, single-host, POSIX-apply-only,
caller-invoked, and unwired from ordinary Retrieval, API, UI, queue, worker, and
scheduler paths.

A closed `subjective_mem_lifecycle_enabled` gate returns a bounded `disabled`
outcome, and a caller that does not request apply returns content-free `dry-run`
readiness. Neither path writes an artifact, claim, intent, record, selector
event, or canonical page byte.

## Implementation budget

The later implementation is bounded to:

```text
relaylm/subjective_mem_consolidate.py                    new
relaylm/subjective_mem_consolidate_runtime.py            new
relaylm/subjective_mem_lifecycle_authority.py            accepted-operation extension
focused tests and one process smoke
existing consolidated smoke and registration surfaces only
```

The shared lifecycle engine, canonical renderer, generic lifecycle gate, config,
API, UI, Primary MEM, ordinary Retrieval, workflows, changed-matrix, generated
registries, and unrelated documentation are excluded unless P1 proves a concrete
missing generic invariant. Return to P1 if path count or diff grows materially,
an existing file gains roughly 200 lines, a file exceeds roughly 700 lines, a
function exceeds roughly 80 lines, tests copy production logic, or a new shared
abstraction duplicates the lifecycle engine.

Because the runtime and negative-test surface are expected to be materially
larger than this one-file architecture change, implementation must use the
ChatGPT-first backend only while connected writes remain atomic and reviewable.
If it would require long-file Base64 splitting, partial assembly, temporary files,
or unsafe full-file replacement, stop connected writes and hand the bounded
implementation plan to Claude Code as the single branch writer.

## Validation matrix

The implementation must prove:

- default-off and dry-run no-write behavior;
- exact `active Primary N -> active Secondary N+1`;
- lifecycle, semantic, scope, memory-kind, formation-snapshot, and strength
  preservation;
- prepared exclusion and final eligibility;
- exact RelayMEM policy authorization and policy-revision binding;
- rejection of user/operator fallback in the first slice;
- same-page append with no move or duplicate current memory;
- exact replay and idempotency conflict;
- stale, Secondary, pinned, hidden, held, superseded, purged, and wrong-state
  rejection;
- first-writer behavior and selector fencing;
- pre/post-page forward recovery and foreign-image preservation;
- later Correct, Forget, and Pin acceptance of a Consolidate predecessor through
  one shared authority;
- absence of relation, merge, supersession, tombstone, usage-event, ordinary
  Retrieval, Primary MEM, API/UI, background recovery, temporary artifacts, and
  branch-writing validation.

The existing `runtime/subjective_mem_lifecycle` consolidated group remains the CI
owner. LC-1E extends it rather than creating a workflow or changing Lane R
changed-matrix authority.

## Non-goals

LC-1E excludes policy candidate discovery, automatic scheduling, usage-based
selection, summarization, semantic merge, duplicate collapse, relation creation,
supersession, strength change, lifecycle visibility change, Primary MEM
consolidation or migration, ordinary Retrieval cutover, API/UI, background
recovery, Purge, multi-host coordination, and non-POSIX publication.
