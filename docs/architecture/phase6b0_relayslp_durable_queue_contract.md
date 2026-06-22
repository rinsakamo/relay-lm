---
relaylm_doc_type: implementation_contract
relaylm_authority: phase6b0_relayslp_durable_queue
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-B1 dispatch preflight changes
  - Phase 6-B2 durable enqueue changes
  - Phase 6-B3 claim lease retry or terminal-state helper changes
  - Phase 6-C worker execution lands
  - queue backend or recovery semantics change
relaylm_not_authoritative_for:
  - RelayMEM candidate meaning or safety scope
  - Primary or Secondary MEM formation
  - memory-write preflight or memory-write idempotency
  - worker RelaySLP execution details
  - page index or log apply
  - RelaySOUL mutation
  - SOUL Lab TTS audio or avatar execution
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6a1_relayslp_job_admission_contract.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - relaymem_slp_current_target.md
  - relaymem_slp_execution_design.md
  - relayrun_runtime_checkpoint_design.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# Phase 6-B0 RelaySLP Durable Queue Contract

## Status

Phase 6-B0 remains the authoritative durable-queue design and state-machine contract.

Implemented bounded consumers are:

- Phase 6-B1: exact dispatch/job-record preflight with no queue I/O,
- Phase 6-B2: atomic create-if-absent durable enqueue,
- Phase 6-B3: fenced claim, lease, retry-release, stale-recovery, and terminal-state helpers.

The next implementation boundary is Phase 6-C worker execution under an exact active B3 lease fence.

```text
finalized visible response
  -> A1 admission result
  -> A2 runtime-private enqueue candidate
  -> B1 deterministic dispatch/job identity and dry-run durable-job candidate: implemented
  -> B2 atomic durable enqueue: implemented
  -> B3 claim/lease/retry-release/stale-recovery/terminal helpers: implemented
  -> Phase 6-C worker execution: next
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

RelaySLP may execute a correctly claimed job in Phase 6-C and consume RelayMEM-owned artifacts. It does not define queue identity, repair queue corruption, or directly mutate RelaySOUL.

## Idempotency domains

Dispatch idempotency and memory-write idempotency remain distinct artifacts with distinct owners and lifetimes.

```text
Dispatch idempotency
  prevents duplicate durable enqueue, duplicate active claim, and duplicate execution dispatch
  owned by Phase 6 / RelayRUN orchestration

memory-write idempotency
  prevents duplicate durable memory apply
  owned by RelayMEM persistence preflight and apply
```

The dispatch key must not be reused as a memory-write key. A memory-write key must not be accepted as a dispatch key.

## Protected producer consumption

A Phase 6-B consumer must receive the exact preceding runtime-private typed result. It must not reconstruct a candidate or request from:

- `PipelineNodeResult`,
- public projection fields,
- trace or audit records,
- frontend metadata,
- visible response text,
- an earlier public projection,
- caller-supplied dictionaries that merely resemble a typed artifact.

Unknown fields, missing fields, wrong types, nested substitutions, prior side effects, pre-populated forbidden values, and lookalike classes fail closed.

B1 consumes the exact A2 result. B2 consumes the exact B1 result and durable candidate. B3 consumes an exact runtime-private transition request and independently revalidates the complete canonical B2 record from disk.

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

The A2 candidate does not contain a retry classification. B1 initializes:

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
queued -> dead_letter    only through a later bounded isolation policy
claimed -> queued        only through validated retry release or stale-lease recovery
claimed -> succeeded
claimed -> failed
claimed -> cancelled
claimed -> dead_letter   only through a later bounded isolation policy
```

B3 does not generate `dead_letter`.

Every mutation uses compare-and-swap semantics over at least job ID, dispatch key, record revision, state, original inode, and original canonical bytes. Claim, renewal, retry release, stale recovery, and claimed-terminal transitions additionally fence on `claim_generation` and `lease_token`; active-lease operations except stale recovery also fence on `claim_owner`.

## State invariants

### Queued

- claim owner and lease token are empty,
- lease timestamps are null,
- terminal reason is empty,
- `retry_not_before` may be null or a canonical bounded timestamp,
- attempt count and claim generation are preserved from the last claim.

### Claimed

- claim owner and unpredictable lease token are present,
- lease acquisition and expiry timestamps are present and ordered,
- retry-not-before and terminal reason are empty,
- only the current active lease holder may renew, retry-release, or commit a claimed terminal transition,
- expired leases require stale recovery and are not renewed or executed.

### Terminal

- claim and lease fields are cleared,
- retry-not-before is null,
- terminal reason is present,
- `failed` and `dead_letter` require a non-`none` failure class,
- `succeeded` and `cancelled` require `failure_class = none`,
- terminal-state immutability is absolute.

Across all states:

```text
attempt_count == claim_generation
record_revision >= claim_generation
updated_at >= created_at
```

## Atomic enqueue and duplicate handling

B2 uses create-if-absent under a uniqueness constraint on dispatch key. Result vocabulary:

```text
enqueued_new
duplicate_existing
blocked_collision
blocked_corrupt
write_failed
```

A duplicate is accepted only when the existing record has identical canonical dispatch key-input fields. Same key plus different key-input fields is not a duplicate. Existing records must never be overwritten merely because the same key is presented again.

## Claim and lease invariants

A successful claim atomically requires `state=queued`, respects `retry_not_before`, increments `record_revision`, increments `attempt_count`, increments `claim_generation`, sets claim owner and a newly generated opaque lease token, records acquisition/expiry timestamps, and transitions to `claimed`.

Lease renewal compares the current revision, state, owner, claim generation, and lease token. It increments revision while preserving attempt count, generation, owner, token, and acquisition time. Lease expiry does not execute work or mutate state; it only permits a separately validated stale-recovery attempt.

At `retry_not_before`, a queued record is ready. At `lease_expires_at`, a claimed record is expired.

## Retry release and stale recovery

A retry-release transition is structurally distinct from terminal failure. `claimed -> queued` release fences on revision, owner, claim generation, and lease token; requires an active lease; increments revision; preserves dispatch identity, attempt count, and generation; clears claim/lease fields; and stores bounded caller-classified retry/failure metadata.

Stale recovery fences on revision, state, claim generation, and lease token but intentionally does not require owner equality. It is allowed only at or after expiry, increments revision, preserves attempts/generation, clears claim/lease fields, and stores fixed stale-lease classifications.

Retry budgets, backoff values, worker error classification, and terminal policy are not defined by B0/B1/B2/B3.

## Terminal commit

An active claimed record may commit `succeeded`, `failed`, or `cancelled` under the exact lease fence. A queued record may commit only `cancelled` with empty claim fence fields.

B3 clears claim/lease and retry-ready metadata, records the terminal reason, and never creates `dead_letter`. Terminal-state immutability applies before all other transition logic.

## Filesystem, locking, and CAS

B2 and B3 use the deterministic dispatch-digest filename under one absolute, pre-existing queue root. No job ID, owner, token, retry value, terminal reason, or content value forms a path.

B3 securely walks each queue-root component with directory file descriptors and rejects symlinks, non-directories, missing components, changed inodes, unsafe final types, hard-link counts other than one, oversized records, malformed or noncanonical JSON, and unsupported secure-dirfd platforms.

B3 takes a nonblocking shared queue-root lock for dry-run inspection and a nonblocking exclusive queue-root lock for apply.

A mutation writes and `fsync`s an exclusive same-directory temporary file, immediately reopens and revalidates the target, requires the original inode and exact bytes to match, atomically renames the temporary file over the target, `fsync`s the directory, and strictly re-reads the committed record. Same-inode byte mutation is a conflict.

Corrupt records must not be silently repaired, normalized, overwritten, claimed, recovered, terminated, or passed to a worker.

## Restart behavior

On restart:

- queued records remain eligible at or after `retry_not_before`,
- unexpired claimed records remain claimed,
- expired claimed records are not automatically executed,
- stale recovery is a separate fenced mutation,
- terminal records remain terminal,
- malformed records are blocked from all transitions.

## Public status projection

The public/default schema is:

```text
relaymem.slp_queue_status_projection.v0
```

It is content-free and may include only allowlisted status, transition kind, queue state, attempt count, claim/lease/terminal booleans, retry/failure classifications, applied/attempted flags, and bounded reason IDs.

It excludes:

- the durable record body,
- runtime-private transition requests and results,
- job and dispatch identifiers,
- run, turn, session, and namespace values,
- lineage fingerprints,
- claim owner and lease token,
- exact timestamps,
- queue paths,
- memory-write idempotency keys,
- raw content of any kind.

## Visible-response independence

Queue persistence or transition failure must not:

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

Phase 6-B2: implemented
  gated atomic durable enqueue
  duplicate/collision/corruption handling
  no worker invocation

Phase 6-B3: implemented
  claim, lease, retry-release, stale-recovery, terminal-state helpers
  no worker execution

Phase 6-C worker execution: next
  exact active B3 lease fence
  existing RelayMEM-owned M3a-M3h boundaries
```

## Current non-goals

B0-B3 do not implement:

- scheduler loops or queue scanning,
- worker execution,
- RelaySLP invocation,
- retry budget or backoff policy,
- request-runtime wiring,
- memory-write preflight or apply from a worker,
- Primary or Secondary MEM formation from queue work,
- page/index/log mutation from queue work,
- RelaySOUL mutation,
- visible-response mutation or delay,
- TTS, audio, Live2D, avatar, or lip-sync processing.

## Validation

Dedicated B1, B2, and B3 behavior, security, and contract smokes prove exact typed boundaries, canonical records, duplicate/collision distinction, fail-closed corruption handling, fenced transitions, attempt/claim monotonicity, stale-lease behavior, terminal-state immutability, lock/CAS behavior, and content-free public diagnostics.
