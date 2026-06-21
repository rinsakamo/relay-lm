---
relaylm_doc_type: implementation_contract
relaylm_authority: phase6b0_relayslp_durable_queue
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-B1 dispatch preflight lands
  - Phase 6-B2 durable enqueue lands
  - Phase 6-B3 claim lease or terminal-state helper lands
  - queue backend or recovery semantics change
relaylm_not_authoritative_for:
  - RelayMEM candidate meaning or safety scope
  - Primary or Secondary MEM formation
  - memory-write preflight or memory-write idempotency
  - worker RelaySLP execution
  - page index or log apply
  - RelaySOUL mutation
  - SOUL Lab TTS audio or avatar execution
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6a1_relayslp_job_admission_contract.md
  - phase6a2_relayslp_response_handoff_contract.md
  - relaymem_slp_current_target.md
  - relaymem_slp_execution_design.md
  - relayrun_runtime_checkpoint_design.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# Phase 6-B0 RelaySLP Durable Queue Contract

## Status

Phase 6-B0 is a design and contract boundary only.

It defines the durable deferred-job record, dispatch-idempotency ownership, queue state machine, atomic enqueue behavior, stale-lease and restart rules, corruption handling, retry-class boundary, and content-free public projection required before any queue implementation is added.

Phase 6-B0 does not create a queue implementation, generate a dispatch key, perform queue I/O, claim work, invoke a worker, invoke RelaySLP, write memory, mutate RelaySOUL, or change visible response delivery.

The next implementation boundary is Phase 6-B1: a default-off, dry-run-only job-record and dispatch-idempotency preflight helper with no queue I/O.

## Purpose

Phase 6-A2 may produce one runtime-private `relaymem.slp_enqueue_candidate.v0` after a finalized `turn_end` response. Phase 6-B consumes that protected candidate through a separately governed queue boundary.

```text
finalized visible response
  -> A1 admission result
  -> A2 runtime-private enqueue candidate
  -> B1 dispatch/job-record preflight
  -> B2 atomic durable enqueue
  -> B3 claim/lease/terminal-state helpers
  -> later Phase 6-C worker execution
```

The visible response is already final before this path begins. Queue persistence failure must never replace, delay, invalidate, or downgrade that response.

## Ownership

### Phase 6 / RelayRUN orchestration owns

- dispatch-idempotency identity,
- durable deferred-job correlation,
- enqueue duplicate prevention,
- queue state and record revision,
- claim ownership and lease fencing,
- retry-attempt orchestration metadata,
- terminal queue states,
- stale-lease recovery eligibility,
- content-free queue status projection.

### RelayMEM owns

- memory candidate meaning,
- source-lineage semantics,
- memory safety scope,
- Primary and Secondary MEM formation,
- memory-write preflight,
- memory-write idempotency,
- durable page/index/log apply.

### RelaySLP does not own orchestration persistence

RelaySLP may later execute a claimed job and consume RelayMEM-owned artifacts. It does not define queue identity, silently repair queue corruption, or directly mutate RelaySOUL.

## Idempotency domains

Dispatch idempotency and memory-write idempotency are distinct artifacts with distinct owners and lifetimes.

```text
dispatch idempotency
  prevents duplicate durable enqueue, duplicate active claim, and duplicate execution dispatch
  owned by Phase 6 / RelayRUN orchestration

memory-write idempotency
  prevents duplicate durable memory apply
  owned by RelayMEM persistence preflight and apply
```

A retried deferred job may encounter a memory update that was already applied. The dispatch key must not be reused as a memory-write key, and a memory-write key must not be accepted as a dispatch key.

## A2 candidate consumption

A Phase 6-B consumer must receive the runtime-private A2 result directly. It must not reconstruct a candidate from:

- `PipelineNodeResult`,
- public projection fields,
- trace or audit records,
- frontend metadata,
- visible response text,
- the original A1 public projection,
- caller-supplied dictionaries that merely resemble the candidate.

The consumer must validate the exact `relaymem.slp_enqueue_candidate.v0` field set and require:

- `candidate_kind = relayslp_deferred_job`,
- `trigger_mode = turn_end`,
- `processing_stage = primary_formation | primary_write_preflight`,
- `source_event_kind = turn`,
- `response_finalized = true`,
- `dry_run_only = true` at the A2 boundary,
- `enqueue_requested = false`,
- `queue_io_performed = false`,
- `enqueued = false`,
- `worker_invoked = false`,
- `invokes_slp = false`,
- `writes_memory = false`,
- `mutates_soul = false`,
- `changes_visible_response = false`,
- empty dispatch and memory-write idempotency keys,
- valid bounded correlation, namespace, source count, lineage fingerprint, terminal status, and persistence-policy metadata.

Unknown fields, missing fields, wrong types, nested substitutions, pre-existing side effects, or a pre-populated idempotency key must fail closed.

B1 must produce a separate runtime-private dry-run durable-record candidate. B2 must consume that validated B1 artifact rather than serializing the A2 dictionary directly.

## Planned durable record schema

The first durable record schema is reserved as:

```text
relaymem.slp_durable_job.v0
```

A durable record contains only bounded orchestration metadata and protected references. It must not contain raw user/model text, prompts, visible response text, memory values, snippets, page bodies, page patches, RelaySOUL bodies, API keys, or arbitrary caller metadata.

### Identity and source fields

```text
schema_version
job_id
dispatch_idempotency_key
dispatch_key_version
candidate_schema_version
candidate_kind
trigger_mode
processing_stage
source_event_kind
run_id
turn_index
session_id
namespace
source_count
source_lineage_fingerprint
source_admission_status
runtime_terminal_status
persistence_policy_status
```

### Queue-control fields

```text
state
record_revision
created_at
updated_at
attempt_count
claim_generation
claim_owner
lease_token
lease_acquired_at
lease_expires_at
retry_class
retry_not_before
failure_class
terminal_reason_id
```

The exact serialized representation and storage backend remain B2 implementation choices, but the semantic field set and state invariants are fixed by this contract.

`job_id`, `dispatch_idempotency_key`, correlation identifiers, namespace, lineage fingerprint, claim owner, lease token, and exact timestamps are runtime-private. They must not appear in the default public projection.

### Field provenance

B1 copies only validated A2 candidate fields into the source portion of the durable-record candidate. It generates or initializes only Phase 6-owned orchestration fields.

The A2 candidate does not contain a retry classification. Therefore B1 must initialize:

```text
retry_class = unclassified
failure_class = none
terminal_reason_id = ""
```

B1 must not recover `retry_class` from the A1 projection, infer it from memory meaning, or invent a retry policy from `processing_stage`. A later bounded worker/failure-classification contract may replace `unclassified` only through an explicit validated transition.

Initial queue-control values before durable enqueue are:

```text
state = queued
record_revision = 0
attempt_count = 0
claim_generation = 0
claim_owner = ""
lease_token = ""
lease_acquired_at = null
lease_expires_at = null
retry_not_before = null
```

B1 is dry-run-only and does not assign durable timestamps or persist these values. B2 assigns durable `created_at` and `updated_at` values during atomic enqueue.

## Dispatch-idempotency derivation

The dispatch-idempotency key is owned by Phase 6 / RelayRUN and is generated no earlier than B1.

The derivation input is the canonical ordered tuple:

```text
dispatch_key_version
candidate_schema_version
candidate_kind
trigger_mode
processing_stage
source_event_kind
run_id
turn_index
session_id presence marker and value
namespace
source_count
source_lineage_fingerprint
```

The canonical encoding must be versioned, length-delimited or canonical-JSON equivalent, deterministic across process restarts, and hashed with a stable cryptographic digest.

The derivation must not include:

- wall-clock timestamps,
- random UUIDs,
- queue paths,
- record revision,
- attempt count,
- claim or lease metadata,
- source admission status,
- runtime terminal status,
- persistence policy status,
- retry class or retry outcome,
- memory-write idempotency keys,
- raw content.

Operational status fields may change without creating a second logical dispatch identity. A collision between the same derived dispatch key and non-identical canonical key-input fields is corruption and must block rather than overwrite.

`job_id` is a separate record identifier. B1 must define whether it is deterministically derived from the dispatch identity or separately allocated, but `job_id` must never be an input to the dispatch key.

## Queue states

The bounded queue state vocabulary is:

```text
queued
claimed
succeeded
failed
cancelled
dead_letter
```

Terminal states are:

```text
succeeded
failed
cancelled
dead_letter
```

Once a terminal state is committed, that record cannot return to `queued` or `claimed`.

`failed` is used only when no further retry transition is allowed for the current record. A retryable execution failure must return the current `claimed` record to `queued` through a separately validated retry-release transition before a terminal state is committed.

`dead_letter` is an alternative terminal orchestration state for retry-exhausted, non-retryable, corrupt-but-preserved, or administratively isolated work. It is not a memory semantic classification.

## State machine

Allowed transitions:

```text
create -> queued
queued -> claimed
queued -> cancelled
queued -> dead_letter    only through later bounded isolation policy
claimed -> queued        only through validated retry release or stale-lease recovery
claimed -> succeeded
claimed -> failed
claimed -> cancelled
claimed -> dead_letter   only through later bounded terminal policy
```

No transition is allowed out of `succeeded`, `failed`, `cancelled`, or `dead_letter`.

Every mutation must use compare-and-swap semantics over at least:

```text
job_id
dispatch_idempotency_key
record_revision
state
```

Claim, lease renewal, retry release, stale-lease recovery, and claimed-terminal mutations must additionally fence on `claim_generation` and `lease_token`.

## State-dependent invariants

### `queued`

- claim owner and lease token are empty,
- lease timestamps are null,
- terminal reason is empty,
- `retry_not_before` may be null or a future bounded timestamp,
- the record is not executable before `retry_not_before`.

### `claimed`

- claim owner and lease token are present,
- lease acquisition and expiry timestamps are present and ordered,
- terminal reason is empty,
- only the current lease holder may renew or commit a claimed transition.

### terminal states

- claim owner and lease token are empty,
- lease timestamps are null,
- `terminal_reason_id` is present,
- `failed` and `dead_letter` require a non-`none` bounded `failure_class`,
- terminal states cannot be claimed or renewed.

## Atomic enqueue and duplicate handling

B2 durable enqueue must be create-if-absent under a uniqueness constraint on the dispatch-idempotency key.

Equivalent safe implementations include:

- a database transaction with a unique key,
- an atomic no-replace filesystem publication after durable temporary-file write,
- another backend with equivalent create-if-absent and crash-consistency guarantees.

The enqueue result vocabulary must distinguish:

```text
enqueued_new
duplicate_existing
blocked_collision
blocked_corrupt
write_failed
```

A duplicate is accepted only when the existing record has the same canonical dispatch key-input fields. Same key plus different key-input fields is not a duplicate; it is a collision/corruption condition.

Fields intentionally excluded from dispatch identity, such as admission status, runtime terminal status, persistence-policy status, timestamps, or retry metadata, must not cause a second record and must not overwrite the existing record during duplicate handling.

No implementation may overwrite an existing job record merely because the same dispatch key is presented again.

## Claim and lease invariants

A successful claim must atomically:

- require `state = queued`,
- require that `retry_not_before` is absent or no longer in the future,
- increment `record_revision`,
- increment `attempt_count`,
- increment `claim_generation`,
- set one claim owner,
- set one unpredictable lease token,
- set lease acquisition and expiry timestamps,
- transition to `claimed`.

Only the holder of the current lease token and claim generation may renew the lease or commit `succeeded`, `failed`, `cancelled`, `dead_letter`, or retry-release transitions from `claimed`.

Lease renewal must compare-and-swap the current record revision and preserve the same claim generation and lease token while advancing only bounded lease metadata.

Lease expiry does not itself execute work, classify memory, or mutate the record. It only makes the record eligible for a separately validated stale-lease recovery transition.

## Retry release

A retry-release transition is structurally distinct from terminal failure.

It may transition `claimed -> queued` only when a later bounded failure-classification/retry policy explicitly permits another attempt. The transition must:

- fence on the current record revision, claim generation, and lease token,
- increment the record revision,
- preserve the dispatch identity and attempt count,
- clear claim owner, lease token, and lease timestamps,
- store only bounded failure-class and retry-class metadata,
- set a bounded `retry_not_before` value when backoff applies,
- leave memory-write idempotency to RelayMEM.

Phase 6-B0 does not define retry budgets, backoff values, or worker error mapping.

## Stale lease and restart behavior

On restart:

- `queued` records remain eligible for future claim after any `retry_not_before`,
- unexpired `claimed` records remain claimed,
- expired `claimed` records are not automatically executed,
- terminal records remain terminal,
- malformed records are blocked from claim.

Stale-lease recovery may transition an expired `claimed` record back to `queued` only when:

- the stored schema is supported,
- the record is otherwise valid,
- the observed `record_revision`, `claim_generation`, and `lease_token` still match,
- the retry boundary permits another attempt,
- no terminal result has already been committed.

Recovery must clear claim/lease fields, increment the record revision, preserve the original dispatch identity and attempt count, and retain bounded failure/recovery metadata. It must not invoke the worker automatically.

## Corruption behavior

Queue readers and writers must fail closed on:

- unsupported schema versions,
- unknown or missing fields,
- invalid state-dependent fields,
- duplicate records for one dispatch key,
- identity/key mismatch,
- malformed timestamps or counters,
- impossible state transitions,
- lease data on non-claimed records,
- missing lease data on claimed records,
- path traversal, symlink, unsafe-root, partial-write, or torn-record evidence for file-backed storage.

Corrupt records must not be silently repaired, overwritten, claimed, or passed to a worker. A backend may quarantine them or create a separately governed dead-letter projection, but preservation and isolation must not expose protected values through default diagnostics.

## Retry-class boundary

The queue stores bounded `retry_class`, `attempt_count`, `retry_not_before`, and `failure_class` metadata, but Phase 6-B does not decide memory meaning or execute retry policy.

B3 may validate the structural legality of claim, lease, retry-release, stale-recovery, and terminal transitions. Retry budgets, backoff selection, worker error classification, checkpoint/recovery integration, and terminal-failure policy remain Phase 6-E or another separately bounded contract.

A retry must never bypass RelayMEM memory-write idempotency.

## Public status projection

The planned public schema is:

```text
relaymem.slp_queue_status_projection.v0
```

The default projection may include only allowlisted content-free fields:

```text
schema_version
status
state
trigger_mode
processing_stage
source_event_kind
source_count
attempt_count
retry_class
response_finalized
enqueue_attempted
enqueue_applied
duplicate_detected
claim_active
lease_present
terminal
failure_class
blocked_reason_ids
```

It must exclude:

- the durable record body,
- the A2 or B1 runtime-private candidate,
- job and dispatch identifiers,
- run, turn, session, and namespace values,
- lineage fingerprints,
- claim owner and lease token,
- exact timestamps including `retry_not_before`,
- queue paths,
- memory-write idempotency keys,
- raw content of any kind.

## Visible-response independence

Any later request-runtime wiring must treat queue persistence as detached post-finalization work.

```text
visible response finalized
  -> response success is fixed
  -> queue attempt may succeed, duplicate, block, or fail
  -> only content-free deferred status may be recorded
```

Queue failure must not:

- change the HTTP success already selected for the response,
- rewrite or append visible text,
- delay stream completion while waiting for persistence,
- trigger TTS/audio/avatar behavior,
- create a synchronous memory-write fallback.

## Phase split

```text
Phase 6-B0
  durable queue contract, ownership, state machine, and safety invariants

Phase 6-B1
  default-off dry-run job-record and dispatch-idempotency preflight helper
  no queue I/O

Phase 6-B2
  gated atomic durable enqueue
  duplicate/collision/corruption handling
  no worker invocation

Phase 6-B3
  claim, lease, retry-release, stale-lease recovery, and terminal-state helpers
  no worker execution

Phase 6-C
  worker execution through RelayMEM-owned bounded artifacts
```

## B0 non-goals

Phase 6-B0 does not implement:

- Python queue helpers,
- dispatch-key generation,
- queue configuration,
- filesystem or database I/O,
- durable enqueue,
- duplicate lookup,
- claim or lease mutation,
- retry execution,
- worker or scheduler execution,
- RelaySLP invocation,
- Primary or Secondary MEM formation,
- memory-write preflight or apply,
- page/index/log mutation,
- RelaySOUL mutation,
- request-runtime wiring,
- visible response mutation or delay,
- TTS, audio, Live2D, avatar, or lip-sync processing.

## Required validation for later slices

B1, B2, and B3 must each add dedicated smoke coverage and GitHub Actions triggers. At minimum, later validation must prove:

- exact A2 candidate validation,
- deterministic dispatch identity,
- fixed B1 initialization of retry metadata not present in A2,
- strict separation from memory-write idempotency,
- default-off and dry-run-only B1 behavior,
- atomic create-if-absent B2 behavior,
- duplicate/collision distinction,
- fail-closed corruption handling,
- fenced claim, lease-renewal, retry-release, and terminal transitions,
- attempt-count and claim-generation monotonicity,
- stale-lease restart behavior,
- terminal-state immutability,
- content-free public projection,
- no worker, memory, SOUL, visible-response, TTS, audio, or avatar side effect inside Phase 6-B.
