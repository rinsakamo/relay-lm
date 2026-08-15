---
relaylm_doc_type: contract
relaylm_authority: current_relayslp_durable_queue_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relayrun_orchestration
relaylm_update_trigger:
  - dispatch/job identity derivation changes
  - durable job schema or canonical-record validation changes
  - durable enqueue duplicate/collision/corruption semantics change
  - claim, lease, retry-release, stale-recovery, or terminal transitions change
  - queue storage locking/CAS/durability behavior changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - RelayMEM candidate meaning, formation, write preflight, or memory-write idempotency
  - worker RelaySLP execution
  - retry-budget, backoff, fairness, or scheduler-loop policy
  - RelaySOUL mutation or visible-response delivery
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - job-admission.md
  - response-handoff.md
  - ../../architecture/memory/formation.md
relaylm_verified_by:
  - ../../../scripts/relaylm_phase6b0_durable_queue_contract_smoke.py
  - ../../../scripts/relaylm_phase6b1_dispatch_preflight_smoke.py
  - ../../../scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py
  - ../../../scripts/relaylm_phase6b3_queue_state_smoke.py
  - ../../../scripts/relaylm_phase6b3_queue_state_security_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayRUN/RelaySLP dispatch, queue, recovery, and worker maintainers
  - RelayMEM formation/persistence maintainers consuming claimed work
  - security, durability, diagnostics, scheduler, and documentation reviewers
relaylm_authority_level: exact_contract
---
# RelaySLP Durable Queue Contract

## Authority summary

This contract owns the exact current Phase 6-B durable deferred-job orchestration boundary implemented across:

```text
relaylm/relaymem_slp_dispatch_preflight.py       # B1
relaylm/relaymem_slp_durable_enqueue.py          # B2
relaylm/relaymem_slp_queue_record.py              # shared canonical record
relaylm/relaymem_slp_queue_storage.py             # secure queue storage primitives
relaylm/relaymem_slp_queue_state.py               # B3
```

The current responsibility is:

```text
A2 runtime-private enqueue candidate
  -> B1 deterministic dispatch/job identity + queued record candidate
  -> B2 atomic create-if-absent durable enqueue
  -> B3 fenced claim/lease/retry/recovery/terminal transitions
  -> later worker execution under separately owned authority
```

The queue stores bounded orchestration metadata and protected references. It is not a memory store, not a RelaySLP execution engine, and not a synchronous visible-response path.

## Ownership split

Phase 6 / RelayRUN orchestration owns:

- dispatch idempotency;
- deterministic job identity;
- durable deferred-job correlation;
- duplicate enqueue prevention;
- queue state and record revision;
- claim generation, owner, and lease fencing;
- retry-release/stale-recovery queue metadata;
- terminal queue states;
- content-free queue status projection.

RelayMEM separately owns:

- candidate meaning and safety scope;
- Primary/Secondary formation;
- memory-write preflight;
- memory-write idempotency;
- page/index/log apply.

Worker/RelaySLP execution is downstream and separately owned.

## Idempotency domains remain separate

The permanent split is:

```text
dispatch idempotency
  -> queue/orchestration domain
  -> prevents duplicate logical durable dispatch

memory-write idempotency
  -> RelayMEM persistence domain
  -> prevents duplicate durable memory apply
```

A dispatch key must not be reused as a memory-write key. B1-B3 do not generate a memory-write idempotency key.

## Current durable job schema

The exact durable record schema is:

```text
relaymem.slp_durable_job.v0
```

The exact key set is:

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

Missing or extra record fields fail canonical validation.

## Current identity/version constants

The exact current identifiers are:

```text
DURABLE_JOB_SCHEMA    = relaymem.slp_durable_job.v0
DISPATCH_KEY_VERSION  = relaymem.slp_dispatch_key.v0
JOB_ID_VERSION        = relaymem.slp_job_id.v0
DISPATCH_KEY_PREFIX   = slp-dispatch-v0:
JOB_ID_PREFIX         = slp-job-v0:
FILENAME_PREFIX       = slp-dispatch-v0-
```

The queue filename is derived from the digest portion of the validated dispatch key and ends in `.json`.

No user content, namespace value, job ID, claim owner, lease token, retry class, or terminal reason is directly used as a path component.

## Current record bounds

Shared current limits are:

```text
MAX_RECORD_BYTES   = 32 * 1024
MAX_TOKEN          = 128
MAX_REASON_COUNT   = 32
MAX_COUNTER        = 2**63 - 1
MAX_LEASE_SECONDS  = 7 * 24 * 60 * 60
```

Counters are exact integers from zero through `MAX_COUNTER`; booleans are not integer substitutes.

## Canonical JSON

Durable records use deterministic JSON bytes with:

```text
ensure_ascii = true
sort_keys = true
separators = (",", ":")
allow_nan = false
UTF-8 encoding
```

On read, current canonical decoding rejects:

```text
queue_record_malformed_utf8
queue_record_malformed_json
queue_record_duplicate_json_key
queue_record_json_not_object
queue_record_noncanonical_json
```

A record that parses but whose bytes are not exactly the canonical representation is not normalized in place. It is rejected.

## Current queue states

The exact current state vocabulary is:

```text
queued
claimed
succeeded
failed
cancelled
dead_letter
```

The mutable states are:

```text
queued
claimed
```

The terminal states are:

```text
succeeded
failed
cancelled
dead_letter
```

Current B3 does not generate `dead_letter`; the canonical record validator recognizes it as a terminal state for durable compatibility.

## B1 responsibility

B1 consumes the exact successful A2 in-process result and exact A2 enqueue candidate.

Its result schema is:

```text
relaymem.slp_dispatch_preflight.v0
```

B1 is helper-only, diagnostics-only, read-only, and current `dry_run_only` only.

A valid B1 result is:

```text
status = dry_run_ready
source_candidate_valid = true
response_finalized = true
durable_job_count = 1
durable_job_created = true
queue_io_performed = false
enqueue_attempted = false
enqueue_applied = false
duplicate_detected = false
worker_invoked = false
invokes_slp = false
writes_memory = false
mutates_soul = false
changes_visible_response = false
```

B1 creates no queue file.

## B1 accepted source boundary

B1 requires one exact `RelayMEMSLPResponseHandoffResult` with one exact `RelayMEMSLPEnqueueCandidate` and validates the exact runtime shapes rather than accepting lookalike dictionaries or public diagnostics.

The source must represent a finalized valid A2 `dry_run_candidate` path. B1 rejects pre-existing queue/apply/worker/memory/SOUL/visible-response side effects.

The downstream job candidate remains runtime-private.

## B1 initial durable-job fields

B1 initializes queue-control state exactly as:

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

Timestamps are intentionally absent in B1 because no durable write has occurred.

## Dispatch-key derivation

The deterministic dispatch-key input is the ordered sequence of:

```text
dispatch_key_version
candidate_schema_version
candidate_kind
trigger_mode
processing_stage
source_event_kind
run_id
turn_index
session_id presence marker
session_id value or empty string
namespace
source_count
source_lineage_fingerprint
```

The compact JSON representation of that ordered input is SHA-256 hashed and prefixed with:

```text
slp-dispatch-v0:
```

The dispatch-key input deliberately excludes operationally mutable state such as:

- timestamps;
- queue path;
- record revision;
- attempt/claim generation;
- claim/lease metadata;
- source admission/runtime terminal/persistence-policy status;
- retry/failure state;
- memory-write identity;
- raw content.

The dispatch identity therefore describes the logical source dispatch rather than a retry attempt.

## Job-ID derivation

`job_id` is a separate deterministic domain:

```text
sha256(JOB_ID_VERSION + "\0" + dispatch_key)
```

with prefix:

```text
slp-job-v0:
```

The job ID is never an input to dispatch-key derivation.

## Derived identity validation

Canonical record validation requires:

- dispatch key to have the exact prefix plus lowercase SHA-256 digest;
- dispatch key to equal re-derivation from the current record identity fields;
- job ID to have the exact prefix plus lowercase SHA-256 digest;
- job ID to equal derivation from the dispatch key.

A record with mismatched derived identity fails closed.

## Canonical source-domain constraints

Current durable records require:

```text
candidate_schema_version = relaymem.slp_enqueue_candidate.v0
candidate_kind = relayslp_deferred_job
trigger_mode = turn_end
source_event_kind = turn
processing_stage in {primary_formation, primary_write_preflight}
source_admission_status in {admitted_dry_run, eligible_for_enqueue}
runtime_terminal_status in {completed, succeeded, idle}
persistence_policy_status in {allowed, free_to_update}
1 <= source_count <= 32
valid lowercase SHA-256 source_lineage_fingerprint
```

Required tokens are bounded ASCII-safe tokens under the shared grammar.

## Timestamp grammar

Durable queue timestamps use exact UTC strings matching:

```text
YYYY-MM-DDTHH:MM:SS.ffffffZ
```

Parsing requires a canonical round trip. `created_at` and `updated_at` must both be valid after persistence and:

```text
updated_at >= created_at
```

Exact timestamps are runtime-private and not part of the public queue projection.

## Cross-state counter invariants

For every valid durable record:

```text
attempt_count == claim_generation
record_revision >= claim_generation
```

These monotonic counters are part of the claim/retry fence.

## Queued-state invariants

For `state=queued`:

```text
claim_owner = ""
lease_token = ""
lease_acquired_at = null
lease_expires_at = null
terminal_reason_id = ""
```

`retry_not_before` may be null or a valid canonical timestamp.

Attempt count and claim generation may be greater than zero after retry release or stale recovery.

## Claimed-state invariants

For `state=claimed`:

```text
claim_owner = valid bounded token
lease_token = valid bounded token
lease_acquired_at = valid timestamp
lease_expires_at = valid timestamp greater than acquisition
retry_not_before = null
terminal_reason_id = ""
attempt_count >= 1
```

The record remains claimed until a fenced transition succeeds.

## Terminal-state invariants

For all terminal states:

```text
claim_owner = ""
lease_token = ""
lease_acquired_at = null
lease_expires_at = null
retry_not_before = null
terminal_reason_id = non-empty bounded token
```

Additionally:

```text
failed / dead_letter -> failure_class != none
succeeded / cancelled -> failure_class == none
```

Terminal records are immutable under B3.

## B2 responsibility

B2 consumes an exact successful B1 result and exact B1 durable-job candidate.

Its result schema is:

```text
relaymem.slp_durable_enqueue.v0
```

The public queue projection schema is:

```text
relaymem.slp_queue_status_projection.v0
```

B2 may inspect or atomically create one durable queue record. It still never invokes a worker, RelaySLP, memory apply, RelaySOUL, or visible-response mutation.

## B2 gate behavior

B2 controls are exact booleans:

```text
enabled
dry_run_only
apply_enabled
```

When disabled, no queue root is opened.

A true apply request exists only when:

```text
dry_run_only == false
apply_enabled == true
```

Other accepted combinations remain inspection/dry-run behavior or block under the owning helper logic.

## Queue root boundary

B2/B3 use one caller/server-supplied queue root only after bounded path validation.

Queue storage does not derive a root from a durable job, namespace, memory page, user text, or record metadata.

The queue root must be opened through the secure queue-storage boundary. Unsafe, missing, unsupported, or symlinked root structures fail closed.

## B2 create-if-absent outcomes

The exact current B2 outcome vocabulary is:

```text
enqueued_new
duplicate_existing
blocked_collision
blocked_corrupt
write_failed
```

The wider B2 status vocabulary additionally includes:

```text
disabled
invalid_input
blocked
dry_run_ready
```

The distinction among duplicate, collision, corruption, and write failure is semantic and must not be collapsed into success.

## Duplicate identity rule

An existing record is an accepted duplicate only when its canonical dispatch-key input fields match the new candidate's identity fields.

Same dispatch key plus different canonical identity input is:

```text
blocked_collision
```

A malformed/noncanonical existing record is:

```text
blocked_corrupt
```

B2 never overwrites a different or corrupt existing record merely because a deterministic filename already exists.

## B2 durable initialization

When B2 applies a new record, it fills the B1-null durable timestamps with current canonical UTC timestamps and persists the exact queued-state record under the deterministic dispatch filename.

The successful durable record remains:

```text
state = queued
attempt_count = 0
claim_generation = 0
record_revision = 0
```

until a B3 claim transition occurs.

## B2 public projection

The public queue projection may report bounded operational fields such as:

```text
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

It omits runtime-private identities, queue paths, timestamps, claim owner/token, lineage fingerprint, and durable record body.

## B3 request schema

The exact current transition request schema is:

```text
relaymem.slp_queue_transition_request.v0
```

`RelayMEMSLPQueueTransitionRequest` contains:

```text
transition_kind
job_id
dispatch_idempotency_key
expected_record_revision
expected_state
claim_owner
claim_generation
lease_token
lease_duration_seconds
retry_class
retry_not_before
failure_class
terminal_state
terminal_reason_id
```

B3 requires the exact request type rather than a lookalike mapping.

## B3 transition kinds

The exact current transition-kind vocabulary is:

```text
claim
renew_lease
retry_release
stale_recovery
commit_terminal
```

No generic arbitrary state setter exists.

## B3 result statuses

The exact current transition result status vocabulary is:

```text
disabled
invalid_input
blocked
not_ready
dry_run_ready
applied
conflict
corrupt
write_failed
```

The exact result schema is:

```text
relaymem.slp_queue_state_transition.v0
```

## B3 gate behavior

B3 controls are exact booleans:

```text
enabled
dry_run_only
apply_enabled
```

When disabled, B3 performs no queue I/O.

When:

```text
dry_run_only = false
apply_enabled = false
```

B3 blocks with:

```text
apply_gate_incomplete
```

An apply mutation occurs only when non-dry-run and apply-enabled.

Dry-run inspection uses a shared/non-exclusive queue lock; apply uses an exclusive queue lock under the storage authority.

## Claim request invariants

A current `claim` request requires:

```text
expected_state = queued
claim_owner present
lease_token empty
lease_duration_seconds > 0
retry_class = unclassified
retry_not_before = null
failure_class = none
terminal fields empty
```

The lease duration must not exceed `MAX_LEASE_SECONDS`.

A successful claim:

- revalidates the exact canonical record and expected revision/state;
- requires retry readiness when `retry_not_before` exists;
- increments `record_revision`;
- increments `attempt_count`;
- increments `claim_generation`;
- creates a new unpredictable lease token;
- records owner/acquisition/expiry;
- clears retry/terminal fields as required;
- transitions to `claimed`.

## Lease renewal invariants

A current `renew_lease` request requires:

```text
expected_state = claimed
claim_owner present
lease_token present
lease_duration_seconds > 0
unused retry/failure/terminal fields at defaults
```

Renewal fences on the current revision, state, claim owner, claim generation, and lease token.

It preserves attempt count, claim generation, owner, token, and original acquisition time while extending the expiry and incrementing record revision.

An expired lease is not renewed as active work.

## Retry-release invariants

A current `retry_release` request requires:

```text
expected_state = claimed
claim_owner present
lease_token present
lease_duration_seconds = 0
retry_class != unclassified
failure_class != none
terminal fields empty
```

The transition requires the active claim fence and converts:

```text
claimed -> queued
```

It increments record revision, preserves attempt count/claim generation and dispatch identity, clears active claim/lease fields, and stores bounded retry/failure classification plus optional canonical `retry_not_before`.

A retry release is not a terminal failure.

## Stale-recovery invariants

A current `stale_recovery` request requires:

```text
expected_state = claimed
lease_token present
lease_duration_seconds = 0
retry/failure/terminal fields at default values
```

Stale recovery is permitted only at or after lease expiry.

It fences on revision/state/claim generation/lease token and intentionally does not require claim-owner equality.

Successful stale recovery converts:

```text
claimed -> queued
```

while preserving attempt count and generation, clearing the active claim fields, and recording the implementation's fixed stale-recovery classification.

## Terminal request invariants

`commit_terminal` supports current terminal targets:

```text
succeeded
failed
cancelled
```

`dead_letter` is not generated by B3.

A terminal request requires a non-empty terminal reason, zero lease-duration request, no retry scheduling fields, and failure-class consistency:

```text
failed     -> failure_class != none
succeeded  -> failure_class == none
cancelled  -> failure_class == none
```

A `claimed` terminal transition requires the active owner/generation/token fence.

A `queued` record may transition only to `cancelled` under the current queued-terminal rule with no active claim fence.

No transition is allowed out of a terminal record.

## Compare-and-swap authority

Every B3 mutation is fenced against canonical durable state rather than trusting the request's expected values alone.

The storage/CAS boundary revalidates at least:

- deterministic filename/dispatch identity;
- exact canonical record;
- expected job ID and dispatch key;
- expected record revision and state;
- original record snapshot/bytes/inode;
- claim generation and lease token for claimed operations;
- claim owner where current active-lease semantics require it.

A concurrent change becomes a bounded conflict rather than being silently overwritten.

## Secure storage and mutation

The queue storage layer uses directory file descriptors and fail-closed filesystem checks where supported.

It rejects unsafe conditions including symlink traversal, unexpected file types, changed root/record identity, hard-link anomalies, oversized records, malformed/noncanonical JSON, and unsafe platform support.

An applied record replacement follows the bounded durability pattern:

```text
exclusive queue lock
  -> read/revalidate canonical snapshot
  -> same-directory exclusive temporary file
  -> write exact canonical bytes
  -> fsync temporary file
  -> re-open/revalidate original target against snapshot
  -> atomic replace
  -> fsync directory
  -> strict committed-record re-read
```

A mutation of the target bytes/inode during this sequence is a conflict, not an invitation to overwrite.

## Restart semantics

Durable queue state survives process restart under these rules:

```text
queued
  -> remains queued; eligible at/after retry_not_before

claimed with unexpired lease
  -> remains claimed

claimed with expired lease
  -> not automatically executed
  -> eligible only for separately fenced stale recovery

terminal
  -> remains immutable terminal

corrupt/noncanonical
  -> blocked from claim/recovery/terminal mutation
```

Restart does not infer worker success from absence of a process.

## Worker boundary

B0-B3 do not execute RelaySLP work.

The next worker boundary must consume an exact active claimed record/fence and must not treat a public queue projection as execution authority.

The queue does not itself decide memory candidate meaning or perform memory persistence.

## Retry-policy boundary

B3 stores bounded caller-classified retry/failure metadata, but B0-B3 do not own:

- retry budget;
- exponential backoff;
- jitter;
- fairness;
- scheduler polling interval;
- worker error taxonomy beyond bounded accepted queue fields;
- dead-letter isolation policy.

Those policies belong to their owning scheduler/worker/recovery layers.

## Visible-response independence

The durable queue is detached post-finalization work.

Queue failure must not:

- replace or downgrade an already selected HTTP success;
- rewrite visible response text;
- hold stream completion open while waiting for memory persistence;
- trigger synchronous memory-write fallback;
- trigger TTS/audio/avatar execution;
- cause a second backend generation.

## Content-free public boundary

Public/default queue status diagnostics are intentionally content-free.

They may expose only bounded state such as:

- status/transition kind;
- queue state;
- source stage/kind and source count where applicable;
- attempt count;
- retry/failure class;
- claim/lease/terminal booleans;
- attempted/applied/duplicate booleans;
- bounded reason IDs.

They exclude:

- durable record bodies;
- A2/B1/B3 private objects;
- job and dispatch identifiers;
- run/turn/session/namespace values;
- lineage fingerprint;
- claim owner and lease token;
- exact timestamps;
- queue paths;
- memory-write idempotency keys;
- raw user/model/response/memory/SOUL content.

## Canonical corruption rule

A corrupt queue record is not repaired as part of enqueue, claim, retry, stale recovery, or terminal transition.

The stable rule is:

```text
malformed / noncanonical / identity-mismatched / unsafe record
  -> block
  -> preserve evidence
  -> no worker execution
  -> no silent normalization or overwrite
```

Repair/isolation, if introduced, is a separately governed authority.

## Stable invariants

- The current durable schema is `relaymem.slp_durable_job.v0`.
- Dispatch idempotency and memory-write idempotency remain separate domains.
- Dispatch key and job ID are deterministic and independently validated.
- The queue filename is derived only from the validated dispatch digest.
- Durable JSON must already be canonical; readers do not normalize in place.
- Current states are queued, claimed, succeeded, failed, cancelled, and dead_letter.
- Current B3 generates only claimed/queued/succeeded/failed/cancelled transitions; it does not generate dead_letter.
- Terminal states are immutable.
- Attempt count equals claim generation and record revision never trails generation.
- Queued records carry no active claim; claimed records carry a bounded active lease; terminal records carry no active claim/retry-ready timestamp.
- B1 performs no queue I/O.
- B2 uses create-if-absent and distinguishes duplicate, collision, corruption, and write failure.
- Existing corrupt/colliding queue records are never silently overwritten.
- B3 mutations require exact request types and canonical durable-state revalidation.
- Active claimed operations are fenced by revision/state/generation/token and, where required, owner.
- Stale recovery requires expiry and intentionally does not require owner equality.
- Queue storage uses bounded locks, CAS-style snapshot checks, atomic replacement, fsync, and committed-record revalidation.
- Queue diagnostics remain content-free.
- Queue failure never becomes visible-response or synchronous memory-write authority.
- B0-B3 do not execute workers or RelaySLP and do not write memory/SOUL.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- A1 admission or A2 response-handoff semantics beyond their required exact source contracts;
- worker execution details;
- Primary/Secondary memory formation;
- memory-write preflight/idempotency/apply;
- scheduler loop/fairness/backoff policy;
- dead-letter generation policy;
- queue repair or migration tooling;
- RelaySOUL mutation;
- visible response, TTS, audio, or avatar execution;
- source retirement;
- repository-level sequencing.

## Related architecture and contracts

- [RelaySLP Job Admission](job-admission.md)
- [RelaySLP Response Handoff](response-handoff.md)
