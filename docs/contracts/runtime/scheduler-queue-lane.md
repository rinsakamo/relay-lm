---
relaylm_doc_type: contract
relaylm_authority: current_relaymem_slp_scheduler_queue_lane_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_update_trigger:
  - O1C queue-lane gate intersection, discovery, eligibility, selection, reread, scope, request-build, or C2 mapping changes
  - shared O0/O1C queue-candidate helper behavior or bounds change
  - queue filename or due-retry classification integration changes
  - queue-lane private future-retry hint or privacy boundary changes
  - C2 result vocabulary consumed by O1C changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - O1A SchedulerGates/LaneOutcome common schema or round aggregation
  - O1B durable-finalization replay-lane semantics
  - B2 enqueue or B3 claim/lease/retry/stale-recovery/terminal transition semantics
  - C1-5 protected-source persistence or C2 worker integration internals
  - Primary MEM formation or durable-finalization semantics
  - O1D1/O1D2/O1E/O1F/O2/O3 higher scheduling, policy, operational, validation, service, or process semantics
  - O0 CLI parsing, projection, exit-code, or operator-command semantics
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/scheduler.md
  - ../../architecture/o1c_eligible_b2_queue_lane.md
  - ../../architecture/o0_local_one_job_runner.md
  - ../../architecture/o1a_two_lane_scheduler_contract.md
  - ../../architecture/o1d1_production_scheduler_round.md
  - ../../architecture/phase6b3_relayslp_queue_state_helpers.md
  - ../../architecture/phase6c2_one_queued_primary_worker_integration.md
relaylm_related_contracts:
  - scheduler-round.md
  - scheduler-replay-lane.md
  - scheduler-policy.md
  - scheduler-operational-controls.md
  - scheduler-operational-validation.md
  - supervised-scheduler-service.md
  - local-scheduler-process.md
relaylm_verified_by:
  - ../../../scripts/relaylm_o1c_eligible_queue_lane_smoke.py
  - ../../../scripts/relaylm_o1c_eligible_queue_lane_security_smoke.py
  - ../../../scripts/relaylm_wave3_cross_slice_convergence_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM SLP queue-lane and scheduler maintainers
  - O0 local one-job runner maintainers consuming the shared queue-candidate helper
  - B3/C2/protected-source integration maintainers
  - runtime, recovery, security, filesystem-hardening, and observability reviewers
relaylm_authority_level: exact_contract
---
# Scheduler Queue Lane Contract

## Authority summary

This contract owns the exact current **O1C bounded eligible B2/B3 queue-lane adapter** and the shared **O0/O1C queue-candidate boundary** implemented by:

```text
relaylm/relaymem_slp_scheduler_queue_lane.py
relaylm/relaymem_slp_queue_candidate.py
```

One O1C invocation performs at most:

```text
exact scheduler/lower worker gate intersection
  -> server-owned root validation
  -> one bounded non-recursive queue discovery
  -> canonical B3 record read/eligibility classification
  -> lexicographically first due queued candidate
  -> one canonical selected-record reread
  -> server-owned character/store scope resolution
  -> fresh source registry + exact C2 request construction
  -> at most one existing C2 delegation
  -> exact O1A queue LaneOutcome
  -> return
```

O1C never polls, sleeps, performs stale recovery, starts another scheduler round, tries a second candidate, or mutates a queue record directly.

## Current implementation anchors

The O1C adapter is:

```text
relaylm/relaymem_slp_scheduler_queue_lane.py
```

The shared lower candidate helper is:

```text
relaylm/relaymem_slp_queue_candidate.py
```

The helper is shared with O0 and owns only:

- lower local-worker gate validation;
- configured-root validation;
- bounded queue discovery;
- future-retry observation;
- deterministic candidate selection;
- canonical reread;
- namespace-to-character/store resolution;
- fresh source-registry and exact C2 request construction.

It does **not** invoke C2 or mutate queue state.

The current O1C implementation handoff remains:

```text
docs/architecture/o1c_eligible_b2_queue_lane.md
```

This transaction does not retire it.

## Common scheduler boundary

O1C accepts exact `SchedulerGates` and returns common `LaneOutcome` with:

```text
lane_kind = queue
```

The common gate/result schemas and one-round aggregation remain owned by `scheduler-round.md`.

This contract owns only queue-lane-specific candidate discovery, lower-gate intersection, reread, scope/request preparation, C2 delegation, and queue-specific outcome mapping.

## Public O1C entry point

The exact current function is:

```text
run_relaymem_slp_scheduler_queue_lane_once(
    *,
    config,
    gates,
    now=None,
    fault_injector=None,
) -> LaneOutcome
```

It accepts no public `character_id` assertion, queue candidate, job ID, dispatch ID, root override, or C2 request.

## Queue-lane reason bound

O1C normalizes adapter-specific reasons to at most:

```text
8
```

with exact token grammar:

```regex
^[a-z][a-z0-9_]{0,63}$
```

Invalid values normalize to a bounded queue-lane invalid-reason token rather than raw exception or object text.

The common LaneOutcome contract remains authoritative for the final bounded reason field.

## QueueLanePrivateState

The current queue-lane private state is immutable and contains:

```text
delegate_result
earliest_retry_not_before
character_scope_resolved
```

`delegate_result` and `earliest_retry_not_before` are excluded from repr and equality.

Its repr is bounded to:

```text
QueueLanePrivateState(
  delegate_result_omitted=True,
  retry_timestamp_omitted=True,
  character_scope_resolved=<bool>
)
```

The private state is attached through `LaneOutcome.private_delegate_result` and is not a public scheduler projection.

## Exact SchedulerGates requirement

O1C first requires:

```text
type(gates) is SchedulerGates
```

Otherwise it returns:

```text
status = failed
enabled = false
attempted = false
no_immediate_work = true
reason = exact_scheduler_gates_required
```

No queue discovery occurs.

## Common gate validation

O1C obtains:

```text
gates.validation_reason_ids()
```

Any common validation reason returns queue-lane:

```text
status = failed
attempted = false
no_immediate_work = true
```

with those already-bounded gate reasons.

The lane `enabled` boolean reflects the intersection:

```text
gates.enabled AND gates.queue_lane_enabled
```

When the common reason includes `required_dependency_unavailable`, O1C marks the returned outcome unsafe.

O1C does not reinterpret or repair invalid common scheduler gates.

## Scheduler disabled behavior

When:

```text
gates.mode == disabled
```

O1C returns:

```text
status = failed
enabled = false
attempted = false
no_immediate_work = true
reason = scheduler_disabled
```

This queue-lane adapter deliberately represents a disabled scheduler as a failed lane adapter outcome rather than a discovered no-work result.

## Queue lane disabled behavior

When:

```text
gates.queue_lane_enabled == false
```

O1C returns:

```text
status = failed
enabled = false
attempted = false
no_immediate_work = true
reason = queue_lane_disabled
```

No lower-worker gate validation or queue discovery follows.

## Exact RelayLMConfig requirement

After scheduler-gate checks, O1C requires:

```text
type(config) is RelayLMConfig
```

Otherwise:

```text
status = failed
enabled = true
attempted = false
no_immediate_work = true
reason = exact_relaylm_config_required
```

## Lower local-worker gate triple

The shared helper validates this exact current lower triple:

```text
relaymem_local_worker_enabled
relaymem_local_worker_dry_run_only
relaymem_local_worker_apply_enabled
```

Each value must be exact `bool`.

The accepted modes are:

```text
(false, true,  false) -> disabled
(true,  true,  false) -> dry_run
(true,  false, true ) -> apply
anything else         -> invalid
```

Wrong gate type returns:

```text
local_worker_gate_type_invalid
```

Invalid triple returns:

```text
local_worker_gate_mode_invalid
```

## Additional lower-worker config validation

`validate_local_worker_mode(config)` also validates current bounded local-worker dependencies before discovery:

```text
relaymem_local_worker_claim_owner
relaymem_local_worker_lease_duration_seconds
relaymem_local_worker_discovery_max_entries
relaymem_slp_source_registry_max_entries
relaymem_slp_source_registry_ttl_seconds
relaymem_slp_protected_source_max_artifact_bytes
```

Current failure reasons include:

```text
local_worker_claim_owner_invalid
local_worker_lease_duration_invalid
local_worker_discovery_limit_invalid
local_worker_source_registry_limit_invalid
local_worker_source_registry_ttl_invalid
local_worker_protected_source_bound_invalid
```

The discovery maximum must be exact `int` in:

```text
1 .. 4096
```

The lease duration must remain within the existing B3 maximum lease bound.

The protected-source artifact limit must remain within the existing protected-source maximum bound.

O1C consumes these bounds; it does not redefine the lower queue/worker/protected-source semantic authority.

## Lower worker disabled behavior

If the lower worker mode is exactly disabled, O1C returns:

```text
status = failed
enabled = true
attempted = false
no_immediate_work = true
reason = local_worker_disabled
```

A disabled lower worker is not reported as an empty queue.

## Scheduler/lower gate intersection

For valid enabled scheduler and lower-worker modes, O1C derives the effective C2 request mode exactly as:

```text
scheduler apply AND lower worker apply
  -> apply

all other valid enabled intersections
  -> dry_run
```

Therefore:

```text
scheduler dry_run + lower apply -> C2 dry_run
scheduler apply   + lower dry_run -> C2 dry_run
scheduler apply   + lower apply -> C2 apply
```

No scheduler gate can elevate a lower dry-run authority to apply.

## Configured root validation

Before queue discovery, the shared helper validates exactly these server-owned configured root values:

```text
queue_root
  = config.relaymem_slp_queue_root

protected_source_root
  = config.relaymem_slp_protected_source_root

store_root
  = config.memory.root_path
```

Each must be exact nonempty `str`, equal to its stripped value, contain no NUL, and represent an absolute path.

Current bounded root reasons are:

```text
local_worker_queue_root_invalid
local_worker_protected_source_root_invalid
local_worker_store_root_invalid
```

O1C exposes no per-call root override.

Root validation failure returns:

```text
status = unsafe_state
attempted = true
unsafe = true
no_immediate_work = true
```

with the bounded root reasons and no discovery/delegation.

## Exact `now` handling

If `now` is null, O1C constructs:

```text
datetime.now(timezone.utc)
```

The effective value must have exact `datetime` type and timezone-aware offset.

Invalid `now` returns:

```text
status = failed
attempted = false
no_immediate_work = true
reason = queue_lane_now_invalid
```

The exact timestamp is not projected publicly.

## Shared queue filename grammar

The shared candidate helper recognizes queue candidates only when a filename matches the current B2/B3 filename prefix plus exactly 64 lowercase hex digits and `.json`:

```text
<FILENAME_PREFIX><64 lowercase hex>.json
```

Under the current queue-record authority this is the canonical dispatch record family:

```text
slp-dispatch-v0-<64 lowercase hex>.json
```

The queue-record module remains authoritative for the prefix and canonical record schema.

## Secure queue-root open and lock

Discovery opens the configured queue root through existing:

```text
open_queue_root(queue_root)
```

and acquires the existing queue lock with:

```text
exclusive = false
```

A lock result exactly `queue_lock_busy` produces discovery status `busy`.

Other lock errors produce discovery status `unsafe`.

The shared helper releases the queue lock and closes the root on owned exits.

It does not create a new scheduler-global lock or candidate reservation file.

## One bounded non-recursive discovery

One helper invocation performs one `os.scandir` over the queue root.

Every directory entry increments the scan count, including nonmatching names.

If scanning exceeds:

```text
max_entries
```

the helper returns:

```text
status = unsafe
reason = queue_discovery_limit_exceeded
```

Partial candidates are discarded for purposes of selection.

O1C does not continue scanning, recurse, or try a partial first candidate after overflow.

## Canonical queue record reading

Grammar-matching queue files are read only through the existing queue-storage authority:

```text
read_record_snapshot(root_fd, filename)
```

If a safe snapshot is not returned with status `ok`, discovery fails closed as `unsafe` using the lower bounded reasons or:

```text
queue_record_discovery_invalid
```

The shared helper does not repair, rewrite, rename, delete, quarantine, or isolate an invalid queue object.

## Queue discovery private objects

The shared helper uses private:

```text
QueueCandidate
QueueDiscoveryResult
```

`QueueCandidate` contains only the selected canonical filename and `RecordSnapshot` but omits both from repr.

`QueueDiscoveryResult` contains public-safe booleans/status plus private:

```text
candidate
earliest_retry_not_before
```

Those private fields are excluded from repr and equality.

The discovery repr explicitly reports candidate/retry timestamp omission rather than the values.

## Discovery status vocabulary

The exact shared discovery status vocabulary is:

```text
selected
no_work
future_retry_only
busy
unsafe
```

These are helper results, not public O1A queue LaneOutcome statuses.

## Eligibility classification

For each safe canonical queue record:

```text
state = queued
retry_not_before absent
  -> due candidate

state = queued
retry_not_before parseable and <= now
  -> due candidate

state = queued
retry_not_before parseable and > now
  -> future-work hint only

state = claimed
  -> claimed observed, not due candidate

other canonical state
  -> terminal observed, not due candidate
```

A queued record with malformed `retry_not_before` returns discovery unsafe:

```text
queue_retry_timestamp_invalid
```

O1C does not convert a future timestamp into a sleep/backoff delay. That remains O1D2 policy authority.

## Future-retry private hint

The helper retains the earliest future due timestamp privately as:

```text
earliest_retry_not_before
```

O1C copies that value only into `QueueLanePrivateState`.

It never appears in `LaneOutcome` repr or public scheduler projection.

The public indication is only:

```text
future_work_hint_present = true
```

when appropriate.

## Deterministic due-candidate selection

Due candidates are sorted by canonical filename in ascending lexicographic order.

The helper selects exactly the first candidate.

This ordering is a stable v0 deterministic rule only. It does not claim FIFO, fairness, age priority, semantic priority, starvation prevention, or retry priority.

O1D2 owns higher policy hints.

## Empty/future discovery outcomes

When due candidates exist:

```text
QueueDiscoveryResult.status = selected
candidate_selected = true
```

When no due candidate exists but a future queued record exists:

```text
status = future_retry_only
future_work_hint_present = true
```

When no due/future candidate exists:

```text
status = no_work
```

Claimed/terminal observations remain private/bounded helper booleans and do not create mutation authority.

## O1C mapping of discovery unsafe

When helper discovery returns `unsafe`, O1C returns:

```text
status = unsafe_state
enabled = true
attempted = true
unsafe = true
no_immediate_work = true
```

It preserves bounded helper reason IDs or uses:

```text
queue_inventory_unsafe
```

It also preserves `candidate_observed` and `future_work_hint_present` booleans.

## O1C mapping of discovery busy

When helper discovery returns `busy`, O1C returns:

```text
status = busy
enabled = true
attempted = true
no_immediate_work = true
contention_observed = true
```

with lower bounded reasons or:

```text
queue_lock_busy
```

O1C does not retry the lock internally.

## O1C mapping of future retry

When helper discovery returns `future_retry_only`, O1C returns:

```text
status = future_retry_only
enabled = true
attempted = true
no_immediate_work = true
future_work_hint_present = true
reason = future_retry_only
```

No C2 delegation occurs.

## O1C mapping of no work

When helper discovery returns `no_work`, O1C returns:

```text
status = no_eligible_work
enabled = true
attempted = true
no_immediate_work = true
reason = no_eligible_queue_work
```

## Selected candidate presence invariant

A helper result that reaches the selected path but has no private candidate is treated as unsafe by O1C:

```text
status = unsafe_state
candidate_observed = true
unsafe = true
no_immediate_work = true
reason = selected_candidate_missing
```

No scope resolution or C2 invocation follows.

## Canonical selected-record reread

After selection, the shared helper independently:

1. reopens the queue root;
2. reacquires the existing shared queue lock;
3. rereads exactly the selected canonical filename;
4. releases the lock and closes the root;
5. compares the current snapshot to the discovery snapshot;
6. revalidates that the record is still queued and due.

The lock is released before C2 delegation.

## Reread exact input requirement

`canonical_reread_relaymem_slp_queue_candidate(...)` requires:

```text
type(candidate) is QueueCandidate
AND
timezone-aware exact datetime now
```

Otherwise:

```text
status = unsafe
reason = queue_candidate_reread_input_invalid
```

## Reread lock behavior

A shared-lock result `queue_lock_busy` during reread is treated as a candidate change:

```text
status = changed
reason = queue_lock_busy_before_claim
```

Other lock errors are unsafe.

O1C does not wait for the lock.

## Reread snapshot identity

The current selected record must preserve all of:

```text
(device, inode)
raw canonical bytes
canonical record mapping
```

against the discovery snapshot.

Any difference returns:

```text
status = changed
reason = queue_candidate_changed_before_claim
```

This detects replacement, byte change, canonical mapping change, revision/generation/state change, and equivalent selected-record races.

## Reread due check

The shared helper re-evaluates queue eligibility through:

```text
queued_record_is_due(current.record, now)
```

A malformed retry timestamp is unsafe.

A safe record that is no longer queued/due returns:

```text
status = changed
reason = queue_candidate_no_longer_eligible
```

The discovery snapshot is never treated as C2 mutation authority.

## O1C mapping of reread failure

A reread exception returns queue lane:

```text
status = failed
candidate_observed = true
candidate_selected = true
no_immediate_work = true
reason = queue_lane_reread_failed
```

A helper reread `unsafe` returns:

```text
status = unsafe_state
canonical_reread_performed = true
unsafe = true
no_immediate_work = true
```

with bounded helper reasons or `queue_candidate_reread_unsafe`.

A safe reread change returns:

```text
status = candidate_changed
canonical_reread_performed = true
retryable = true
```

with bounded helper reasons or `queue_candidate_changed`.

No second candidate is selected.

## Character/namespace scope resolution

After a successful reread, O1C calls the shared server-owned resolver with:

```text
namespace = current.record.namespace
explicit_character_id = None
configured_store_root = config.memory.root_path
```

O1C therefore exposes no operator/browser character assertion.

The namespace must satisfy the existing token grammar or resolution returns:

```text
local_worker_namespace_invalid
```

## Server-owned route scope

The resolver derives candidate `(character_id, memory_namespace)` pairs only from server-owned `model_routes` whose:

```text
character_id is token
memory_namespace is token
character_id exists in config.characters
```

For O1C, the resolver considers only characters whose route namespace exactly matches the selected record namespace.

Zero matches return:

```text
local_worker_character_scope_not_found
```

Multiple distinct character matches return:

```text
local_worker_character_scope_ambiguous
```

Exactly one match becomes the server-resolved character ID.

The namespace itself is never used as a character ID.

## Character-partitioned store root

The shared helper passes the server-resolved character to the existing character-store root resolver together with the configured memory root.

A null/non-absolute result returns:

```text
local_worker_character_store_root_unavailable
```

This contract consumes that partitioning boundary but does not redefine the underlying memory-store path authority.

## O1C scope resolution failure

Any exception during scope resolution is normalized to:

```text
queue_character_scope_resolution_failed
```

A null character/store result returns queue-lane:

```text
status = failed
candidate_observed = true
candidate_selected = true
canonical_reread_performed = true
no_immediate_work = true
```

with the bounded scope reason or `queue_character_scope_unavailable`.

No C2 request is constructed.

## Fresh source registry per request

The shared request builder constructs a new exact:

```text
RelayMEMSLPPrimaryWorkerSourceRegistry
```

for every request with:

```text
max_entries = config.relaymem_slp_source_registry_max_entries
ttl_seconds = config.relaymem_slp_source_registry_ttl_seconds
```

The source registry is not shared between separate O1C delegations.

The O1C focused smoke verifies two separate delegations receive distinct registry objects.

## Exact C2 request construction

The shared helper constructs exactly one:

```text
RelayMEMSLPOneQueuedJobRunnerRequest
```

with current C2 request schema and these responsibility-level inputs:

```text
runtime_private = true
content_included = false
current existing primary-writer decision
queued_record = exact canonical reread record
fresh source_registry
server-resolved character_id
configured queue_root
configured protected_source_root
character-partitioned store_root
configured local-worker claim_owner
enabled = true
dry_run_only = effective mode is dry_run
apply_enabled = effective mode is apply
configured lease_duration_seconds
configured protected_source_max_artifact_bytes
```

O1C does not reconstruct protected-source content. C1-5 remains restart/rehydration authority below C2.

This contract does not own the primary-writer decision semantics consumed by the request builder.

## Request-build failure

Any failure during scope-complete C2 request construction or the pre-C2 focused fault seam returns:

```text
status = failed
candidate_observed = true
candidate_selected = true
canonical_reread_performed = true
no_immediate_work = true
reason = queue_c2_request_invalid
```

No C2 invocation occurs after that failure.

## Single C2 delegation

For a successfully built request, O1C calls at most once:

```text
execute_one_queued_relaymem_slp_primary_job(c2_request)
```

O1C never directly performs B3 claim, protected-source rehydration, worker execution, retry release, terminal transition, or cleanup as a substitute for C2.

## Delegation exception boundary

If the C2 invocation or immediate post-C2 fault seam raises, O1C returns conservatively:

```text
status = failed
delegation_attempted = true
mutation_may_have_occurred = true
no_immediate_work = true
retryable = true
reason = queue_c2_delegation_failed
```

This conservatively accounts for a lower effect that may already have occurred before an exception was observed.

No second candidate or second C2 call is attempted.

## C2 mutation indicator

For an exact current C2 result, O1C considers lower mutation as potentially having occurred when any are true:

```text
claim_performed
worker_invoked
queue_transition_performed
terminal
cleanup_required
```

The resulting boolean is copied into common `LaneOutcome.mutation_may_have_occurred` only.

O1C does not claim ownership of the lower mutation.

## C2 result private retention

After a normal C2 return, O1C stores the raw exact C2 result only in private `QueueLanePrivateState.delegate_result`.

That field is omitted from repr and equality and is never projected publicly.

## Common delegated queue fields

A normally mapped C2 result returns a queue LaneOutcome with:

```text
enabled = true
attempted = true
candidate_observed = true
candidate_selected = true
canonical_reread_performed = true
delegation_attempted = true
delegation_completed = true
mutation_may_have_occurred = lower-derived boolean
terminal_for_candidate = bool(result.terminal)
```

The status/retry/no-work/unsafe fields are then specialized by the exact mapping below.

## C2 `dry_run_ready` mapping

When:

```text
result.status = dry_run_ready
```

O1C returns:

```text
status = dry_run_ready
no_immediate_work = false
```

with lower bounded reasons or:

```text
queue_dry_run_ready
```

## Cleanup-required precedence

When either:

```text
result.cleanup_required == true
OR
result.status == cleanup_required
```

O1C returns:

```text
status = cleanup_required
no_immediate_work = true
retryable = true
```

with lower reasons or:

```text
queue_cleanup_required
```

This check precedes the generic terminal mapping.

O1C does not perform the cleanup itself.

## Terminal mapping

When:

```text
result.terminal == true
```

and cleanup-required precedence did not apply, O1C returns:

```text
status = terminal
no_immediate_work = false
terminal_for_candidate = true
```

with lower reasons or:

```text
queue_candidate_terminal
```

Terminal queue transition semantics remain C2/B3 authority.

## Claim-conflict mapping

For lower statuses:

```text
claim_not_applied
claim_lost_before_rehydrate
```

O1C returns:

```text
status = candidate_changed
no_immediate_work = false
retryable = true
```

with lower reasons or:

```text
queue_claim_conflict
```

This is the expected convergence path when O0/O1C or two O1C calls race on the same B3 candidate.

## Blocked protected-source mapping

For:

```text
result.status = source_blocked
```

O1C returns:

```text
status = unsafe_state
no_immediate_work = true
unsafe = true
```

with lower reasons or:

```text
queue_source_blocked
```

O1C does not bypass or reconstruct the protected source.

## Retryable protected-source mapping

For:

```text
result.status = source_retryable
```

O1C returns:

```text
status = failed
no_immediate_work = true
retryable = true
```

with lower reasons or:

```text
queue_source_retryable
```

## Worker retry-release mapping

When:

```text
result.status = worker_completed
AND
(result.retryable == true OR result.worker_status == retry_released)
```

O1C returns:

```text
status = retry_released
no_immediate_work = false
retryable = true
```

with lower reasons or:

```text
queue_retry_released
```

Retry timing itself remains lower B3/O1D2 authority.

## Worker executed mapping

When:

```text
result.status = worker_completed
AND
result.worker_invoked == true
```

and retry-release precedence did not apply, O1C returns:

```text
status = executed
no_immediate_work = false
```

with lower reasons or:

```text
queue_worker_executed
```

## C2 fallback failure mapping

Any C2 result not matched above returns queue-lane:

```text
status = failed
no_immediate_work = true
retryable = bool(result.retryable)
```

with lower bounded reasons or:

```text
queue_delegate_failed
```

O1C does not reinterpret unknown lower statuses into success.

## Same-round replay independence

O1D1 invokes replay before queue when both lanes are enabled, but O1B private output is never passed directly to O1C.

If replay convergence creates queue-visible work, O1C may see it only through its independent normal queue-root discovery/reread path.

It receives no replay locator, candidate, source registry, C2 request, or private delegate result.

Same-round observation is possible but not privileged or guaranteed.

## O0 shared-helper boundary

O0 consumes the same `relaymem_slp_queue_candidate.py` helper for safe lower gate/root/discovery/reread/scope/request behavior.

O0 retains separate authority for:

- explicit operator command invocation;
- its request/CLI contract;
- optional explicit character assertion where its own interface allows it;
- CLI projection and exit behavior;
- one-process command semantics.

The shared helper does not inherit O0 CLI authority merely because both O0 and O1C consume it.

## Queue lock release before C2

Discovery and reread use the existing shared queue lock only while reading canonical candidate state.

The lock is released before C2.

The authoritative claim race is therefore resolved by the existing B3 claim CAS inside C2, not by an O1C reservation.

## Concurrency boundary

Two O1C calls, or O0 and O1C, may independently select the same queued record.

Canonical reread may close some pre-delegation races, but a later race remains possible and is resolved by C2/B3.

O1C maps claim conflict to `candidate_changed` rather than adding a second global lock, owner marker, retry loop, or candidate reservation.

## Future retry and higher policy boundary

O1C only reports:

```text
future_retry_only
future_work_hint_present = true
```

and privately retains the earliest future timestamp.

It does not:

- sleep until the timestamp;
- calculate delay;
- implement backoff or jitter;
- reorder due candidates by retry time;
- provide fairness/starvation prevention.

O1D2 owns bounded future scheduling policy above the lane.

## No stale-recovery authority

A `claimed` record is observed only as unavailable immediate queue work.

O1C does not inspect lease expiry to perform stale recovery and never constructs a B3 `stale_recovery` transition.

O1E remains the scheduler-stack stale-recovery orchestration owner.

## Public privacy boundary

Public queue LaneOutcome and scheduler projections must not expose:

- namespace;
- character ID or character store path;
- job or dispatch identity;
- record revision or claim generation;
- claim owner or lease token;
- retry timestamp;
- canonical filename;
- queue/protected-source/memory roots or paths;
- protected-source body or digest;
- memory content;
- run/session/turn identity;
- raw C2 request/result;
- raw exception text;
- server config values.

The only public future-work information is a bounded boolean/status, never the timestamp.

## One-candidate invariant

One O1C call performs at most:

```text
one bounded queue inventory
one deterministic due-candidate selection
one canonical reread
one scope resolution
one C2 request build
one C2 call
```

There is no second-candidate fallback after:

- candidate change;
- C2 claim conflict;
- C2 retryable result;
- blocked source;
- cleanup required;
- C2 failure;
- focused fault seam.

Higher rounds/services may call O1C again only under their separately owned semantics.

## Fail-closed invariants

The exact current O1C/shared-helper rules include:

1. wrong SchedulerGates type prevents discovery;
2. invalid/disabled scheduler or queue lane prevents discovery;
3. wrong RelayLMConfig type prevents discovery;
4. invalid/disabled lower worker gates prevent discovery;
5. scheduler authority never elevates lower dry-run to apply;
6. invalid server-owned roots fail before queue scan;
7. queue discovery is non-recursive, shared-lock protected, and bounded;
8. malformed grammar-matching queue records fail the inventory closed;
9. invalid retry timestamps fail closed;
10. deterministic selection never falls through to a second candidate;
11. selected record is reread under the existing lock and must remain byte/record/identity/due equivalent;
12. character scope comes only from server-owned route configuration for O1C;
13. exactly one character scope is required;
14. a fresh source registry is built for every C2 request;
15. O1C never reconstructs protected-source content;
16. C2 is called at most once;
17. C2/claim races converge through lower B3 authority rather than new O1C locks;
18. delegation exceptions conservatively set mutation-may-have-occurred;
19. future timestamps and raw C2 state remain private;
20. O1C adds no poll/sleep/stale-recovery/service/daemon behavior.

## Current focused evidence

The exact queue-lane contract is guarded by:

```text
scripts/relaylm_o1c_eligible_queue_lane_smoke.py
scripts/relaylm_o1c_eligible_queue_lane_security_smoke.py
scripts/relaylm_wave3_cross_slice_convergence_smoke.py
```

The functional smoke verifies, among other things:

- disabled/invalid common gates do not scan;
- lower disabled worker does not scan;
- empty queue maps to `no_eligible_work`;
- future retry remains a private timestamp + public hint;
- scheduler dry-run cannot elevate lower apply;
- lower dry-run cannot be elevated by scheduler apply;
- apply mode builds apply-enabled C2 requests only when both authorities allow it;
- fresh source registry is built per delegation;
- exact canonical reread record is passed into the C2 request;
- claim conflict, retry release, cleanup required, source retry/block, and generic failure mappings are bounded;
- a pre-C2 fault prevents C2 invocation and does not leak raw exception text;
- public O1C signature has no character assertion;
- real apply convergence can reach terminal queue state and lower protected-source cleanup through existing C2/B3 authority.

## Relationship to scheduler-round contract

`scheduler-round.md` owns common queue `LaneOutcome` field validation, accepted queue status vocabulary, one-round aggregation, and O1D1 replay-before-queue ordering.

This contract owns the behavior **inside the queue lane** before that common LaneOutcome is returned.

## Relationship to replay lane

`scheduler-replay-lane.md` owns the separate O1B durable-finalization replay opportunity.

O1B and O1C share only the common SchedulerGates/LaneOutcome framework. They do not share candidate roots, identity, selection state, private delegate results, or lower mutation authority.

## Source-retirement boundary

This transaction does not retire:

```text
docs/architecture/o1c_eligible_b2_queue_lane.md
```

It also does not retire the shared O0/O1C candidate helper, O0 handoff, B2/B3/C2 handoffs, implementation modules, smokes, or completion evidence. Retirement requires a separate bounded provenance/consumer/migration transaction.
