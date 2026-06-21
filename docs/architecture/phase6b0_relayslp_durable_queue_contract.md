---
relaylm_doc_type: implementation_contract
relaylm_authority: phase6b0_relayslp_durable_queue
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-B1 dispatch preflight changes
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
  - phase6b1_relayslp_dispatch_preflight.md
  - relaymem_slp_current_target.md
  - relaymem_slp_execution_design.md
  - relayrun_runtime_checkpoint_design.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# Phase 6-B0 RelaySLP Durable Queue Contract

## Status

Phase 6-B0 remains the authoritative durable-queue design and state-machine contract.

Phase 6-B1 now implements the first bounded consumer of this contract: a default-off, read-only, dry-run-only dispatch/job-record preflight. B1 generates deterministic dispatch and job identities plus one runtime-private initial `relaymem.slp_durable_job.v0` candidate, but performs no queue I/O.

The next implementation boundary is Phase 6-B2: gated atomic create-if-absent durable enqueue, duplicate/collision/corruption classification, and durable timestamp assignment without worker invocation.

```text
finalized visible response
  -> A1 admission result
  -> A2 runtime-private enqueue candidate
  -> B1 deterministic dispatch/job identity and dry-run durable-job candidate: implemented
  -> B2 atomic durable enqueue: next
  -> B3 claim/lease/retry-release/terminal helpers: later
  -> Phase 6-C worker execution: later
```

Queue work is detached post-finalization work. Queue failure must never replace, delay, invalidate, or downgrade the already-finalized visible response.

## Ownership

### Phase 6 / RelayRUN orchestration owns

- dispatch idempotency,
- durable deferred-job correlation,
- duplicate enqueue prevention,
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

RelaySLP may later execute a claimed job and consume RelayMEM-owned artifacts. It does not define queue identity, repair queue corruption, or directly mutate RelaySOUL.

## Idempotency domains

Dispatch idempotency and memory-write idempotency remain distinct artifacts with distinct owners and lifetimes.

```text
dispatch idempotency
  prevents duplicate durable enqueue, duplicate active claim, and duplicate execution dispatch
  owned by Phase 6 / RelayRUN orchestration

memory-write idempotency
  prevents duplicate durable memory apply
  owned by RelayMEM persistence preflight and apply
```

The dispatch key must not be reused as a memory-write key. A memory-write key must not be accepted as a dispatch key.

## Protected A2 consumption

A Phase 6-B consumer must receive the runtime-private A2 result directly. It must not reconstruct a candidate from:

- `PipelineNodeResult`,
- public projection fields,
- trace or audit records,
- frontend metadata,
- visible response text,
- the original A1 public projection,
- caller-supplied dictionaries that merely resemble the candidate.

The exact `relaymem.slp_enqueue_candidate.v0` field set must be validated. Required invariants include:

- `candidate_kind = relayslp_deferred_job`,
- `trigger_mode = turn_end`,
- `processing_stage = primary_formation | primary_write_preflight`,
- `source_event_kind = turn`,
- `response_finalized = true`,
- `dry_run_only = true`,
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

Unknown fields, missing fields, wrong types, nested substitutions, prior side effects, or pre-populated idempotency keys fail closed.

B1 produces a separate runtime-private dry-run durable-record candidate. B2 must consume that validated B1 artifact rather than serializing an A2 dictionary directly.

## Durable record schema

The queue record schema is:

```text
relaymem.slp_durable_job.v0
```

Identity and source fields:

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

Queue-control fields:

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

The record contains only bounded orchestration metadata and protected references. It must not contain raw user/model text, prompts, visible response text, memory values, snippets, page bodies, page patches, RelaySOUL bodies, credentials, or arbitrary caller metadata.

`job_id`, dispatch key, correlation values, namespace, lineage fingerprint, claim owner, lease token, and exact timestamps remain runtime-private.

## B1 initialization

B1 copies only validated A2 source fields and initializes only Phase 6-owned fields.

The A2 candidate does not contain a retry classification. Therefore B1 initializes:

```text
state = queued
record_revision = 0
created_at = null
updated_at = null
attempt_count = 0
claim_generation = 0
claim_owner = ""
lease_token = ""
lease_acquired_at = null
lease_expires_at = null
retry_class = unclassified
retry_not_before = null
failure_class = none
terminal_reason_id = ""
```

B1 must not recover `retry_class` from the A1 projection or infer retry policy from memory meaning or processing stage. B1 assigns no durable timestamps and performs no persistence.

## Dispatch-idempotency derivation

B1 uses version `relaymem.slp_dispatch_key.v0` and the canonical ordered tuple:

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

The encoding is deterministic compact canonical JSON and the UTF-8 bytes are hashed with SHA-256.

The derivation must not include:

- wall-clock timestamps,
- random UUIDs,
- queue paths,
- record revision,
- attempt count,
- claim or lease metadata,
- source admission status,
- runtime terminal status,
- persistence-policy status,
- retry class or retry outcome,
- memory-write idempotency keys,
- raw content.

Operational status fields may change without creating a second logical dispatch identity. Same derived key with different canonical key-input fields is collision/corruption and must block.

`job_id` is separately and deterministically derived in the `relaymem.slp_job_id.v0` domain from the completed dispatch key. It is never an input to the dispatch key.

## Queue states

The bounded vocabulary is:

```text
queued
claimed
succeeded
failed
cancelled
dead_letter
```

Terminal states are `succeeded`, `failed`, `cancelled`, and `dead_letter`. No transition is allowed out of `succeeded`, `failed`, `cancelled`, or `dead_letter`.

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

Every mutation uses compare-and-swap semantics over at least job ID, dispatch key, record revision, and state. Claim, renewal, retry release, stale recovery, and claimed-terminal transitions additionally fence on `claim_generation` and `lease_token`.

## State invariants

### Queued

- claim owner and lease token are empty,
- lease timestamps are null,
- terminal reason is empty,
- `retry_not_before` may be null or a future bounded timestamp.

### Claimed

- claim owner and unpredictable lease token are present,
- lease acquisition and expiry timestamps are present and ordered,
- terminal reason is empty,
- only the current lease holder may renew or commit a claimed transition.

### Terminal

- claim and lease fields are cleared,
- terminal reason is present,
- `failed` and `dead_letter` require a non-`none` failure class,
- terminal-state immutability is absolute.

## Atomic enqueue and duplicate handling

B2 must use create-if-absent under a uniqueness constraint on dispatch key. Result vocabulary:

```text
enqueued_new
duplicate_existing
blocked_collision
blocked_corrupt
write_failed
```

A duplicate is accepted only when the existing record has identical canonical dispatch key-input fields. Same key plus different key-input fields is not a duplicate. Existing records must never be overwritten merely because the same key is presented again.

Fields excluded from dispatch identity must not create a second record and must not overwrite an existing record during duplicate handling.

## Claim and lease invariants

A successful future claim atomically requires `state=queued`, respects `retry_not_before`, increments `record_revision`, increments `attempt_count`, increments `claim_generation`, sets claim owner and lease token/timestamps, and transitions to `claimed`.

Lease renewal must compare-and-swap the current revision while preserving claim generation and lease token. Lease expiry does not execute work or mutate state; it only permits a separately validated stale-recovery attempt.

## Retry release

A retry-release transition is structurally distinct from terminal failure. A future `claimed -> queued` release must fence on revision, claim generation, and lease token; increment revision; preserve the dispatch identity and attempt count; clear claim/lease fields; store bounded failure/retry metadata; and optionally set `retry_not_before`.

Retry budgets, backoff values, worker error classification, and terminal policy are not defined by B0/B1.

## Restart and corruption

On restart:

- queued records remain eligible after `retry_not_before`,
- unexpired claimed records remain claimed,
- expired `claimed` records are not automatically executed,
- terminal records remain terminal,
- malformed records are blocked from claim.

Queue readers and writers fail closed on unsupported schemas, unknown/missing fields, impossible state combinations, identity/key mismatch, duplicate records, malformed counters/timestamps, lease data on non-claimed records, missing lease data on claimed records, and unsafe or torn file-backed storage evidence.

Corrupt records must not be silently repaired, overwritten, claimed, or passed to a worker.

## Public status projection

The public/default schema is:

```text
relaymem.slp_queue_status_projection.v0
```

It is content-free and may include only allowlisted state/status/count/boolean fields. It excludes:

- the durable record body,
- the A2 or B1 runtime-private candidate,
- job and dispatch identifiers,
- run, turn, session, and namespace values,
- lineage fingerprints,
- claim owner and lease token,
- exact timestamps,
- queue paths,
- memory-write idempotency keys,
- raw content of any kind.

## Visible-response independence

Queue persistence failure must not:

- change the HTTP success already selected,
- rewrite or append visible text,
- delay stream completion while waiting for persistence,
- trigger TTS/audio/avatar behavior,
- create a synchronous memory-write fallback.

## Phase split

```text
Phase 6-B0
  durable queue contract, ownership, state machine, and safety invariants

Phase 6-B1: implemented
  default-off dry-run job-record and dispatch-idempotency preflight helper
  no queue I/O

Phase 6-B2: next
  gated atomic durable enqueue
  duplicate/collision/corruption handling
  no worker invocation

Phase 6-B3
  claim, lease, retry-release, stale recovery, terminal-state helpers
  no worker execution

Phase 6-C
  worker execution through RelayMEM-owned bounded artifacts
```

## Current non-goals

B0/B1 do not implement:

- queue configuration or filesystem/database I/O,
- durable enqueue or duplicate lookup,
- claim/lease/state mutation,
- retry execution,
- worker or scheduler execution,
- RelaySLP invocation,
- memory-write preflight or apply,
- page/index/log mutation,
- RelaySOUL mutation,
- request-runtime wiring,
- visible-response mutation or delay,
- TTS, audio, Live2D, avatar, or lip-sync processing.

## Validation

B1 provides dedicated behavior and security smokes. Later B2/B3 validation must prove atomic create-if-absent semantics, duplicate/collision distinction, fail-closed corruption handling, fenced transitions, attempt/claim monotonicity, stale-lease behavior, and terminal-state immutability without leaking private identities or content.
