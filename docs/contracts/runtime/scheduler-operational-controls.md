---
relaylm_doc_type: contract
relaylm_authority: current_relaymem_slp_scheduler_operational_controls_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_update_trigger:
  - scheduler operational-control result/projection schema or status changes
  - cancellation checkpoints or signal-adapter semantics change
  - stale-claim discovery/recovery orchestration or scan bounds change
  - operational/stale-recovery config gates or lower-apply compatibility changes
  - O1E fault seams or one-invocation scheduler-call bound changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - O1A/O1D1 one-round lane/result semantics
  - O1D2 fairness, retry-window, pacing, backoff, or jitter semantics
  - B3 queue transition semantics beyond O1E's exact stale-recovery delegation boundary
  - I1-GC replay or C2 worker execution semantics
  - O2/O3 polling, service supervision, daemon, or always-on lifecycle
  - general RelayRUN resource scheduling
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/scheduler.md
  - ../../architecture/o1e_scheduler_operational_controls.md
  - ../../architecture/o1f_operational_validation.md
  - ../../architecture/o2_supervised_scheduler_service.md
  - ../../architecture/o3_always_on_local_scheduler.md
relaylm_related_contracts:
  - scheduler-round.md
  - scheduler-policy.md
  - ../relayrun-checkpoint-and-recovery.md
relaylm_verified_by:
  - ../../../scripts/relaylm_o1e_scheduler_operational_controls_smoke.py
  - ../../../scripts/relaylm_o1e_scheduler_operational_controls_config_smoke.py
  - ../../../scripts/relaylm_o1e_scheduler_operational_controls_fault_smoke.py
  - ../../../scripts/relaylm_o1e_scheduler_operational_controls_security_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM SLP scheduler operations maintainers
  - local scheduler service and shutdown integration maintainers
  - queue lifecycle, recovery, security, observability, and documentation reviewers
relaylm_authority_level: exact_contract
---
# Runtime Scheduler Operational Controls Contract

## Authority summary

This contract owns the exact current **O1E bounded caller-invoked operational-control layer** implemented by:

```text
relaylm/relaymem_slp_scheduler_operations.py
```

One invocation is bounded to:

```text
caller invocation
  -> exact input/config validation
  -> cancellation checkpoint
  -> optional bounded stale-claim discovery
  -> at most one B3 stale_recovery transition
  -> cancellation checkpoint
  -> at most one O1D2/O1D1 scheduler round
  -> cancellation checkpoint
  -> content-free projection
  -> return
```

O1E does not poll, sleep, loop, retry internally, supervise a service, daemonize, create a background worker, change lane discovery, or replace B3/I1-GC/C2 authority.

## Current schema identifiers

The exact current schemas are:

```text
OPERATIONS_RESULT_SCHEMA     = relaylm.local_scheduler_operational_controls_result.v0
OPERATIONS_PROJECTION_SCHEMA = relaylm.local_scheduler_operational_controls_projection.v0
```

The current hard bounds are:

```text
MAX_OPERATION_REASON_IDS = 16
MAX_STALE_SCAN_ENTRIES   = 4096
```

Bounded reason IDs use:

```regex
^[a-z][a-z0-9_]{0,63}$
```

Invalid reason inputs normalize to `scheduler_operational_reason_invalid`, duplicate values are removed in first-seen order, and projection stops at sixteen reasons. If no reason remains, `scheduler_operational_status` is inserted.

## Operational modes

The current operational mode vocabulary is:

```text
disabled
dry_run
apply
```

Internal/result validation may additionally carry `invalid` for fail-closed input/config results.

The standard gate triples are exactly:

```text
(false, true,  false) -> disabled
(true,  true,  false) -> dry_run
(true,  false, true)  -> apply
```

Any other triple is invalid.

## Operational status vocabulary

The exact current operational statuses are:

```text
disabled
dry_run_ready
invalid_input
invalid_config
cancelled_before_start
cancelled_before_stale_recovery
cancelled_before_scheduler_round
cancelled_after_scheduler_round
shutdown_requested
scheduler_round_completed
completed
unexpected_failure
```

Not every vocabulary member must be emitted by every current wrapper path. The vocabulary is the constructor-accepted current result contract.

## Stale-recovery status vocabulary

The exact current stale-recovery statuses are:

```text
not_invoked
stale_recovery_disabled
stale_recovery_dry_run_ready
stale_recovery_attempted
stale_recovery_no_candidate
stale_recovery_failed
```

These are O1E orchestration statuses. They do not replace the exact B3 queue-transition result/status contract.

## SchedulerCancellationToken

`SchedulerCancellationToken` wraps one caller-provided cancellation probe:

```text
is_cancelled: Callable[[], bool]
```

Construction requires a callable or raises:

```text
scheduler_cancellation_probe_required
```

`requested()` returns `bool(probe())`.

If the probe raises, `requested()` returns `true` rather than propagating the exception. Cancellation-probe failure therefore closes toward cancellation.

The token repr is content-free and reports only that the probe was omitted from representation.

## Signal cancellation adapter

`SchedulerSignalCancellationAdapter` is an opt-in synchronous adapter that maps process signals to the same cancellation token.

Current behavior is:

```text
initial requested = false
request_shutdown(...)
  -> requested = true
```

Its `installed(...)` context manager defaults to:

```text
SIGINT
SIGTERM
```

It saves the prior handlers, installs `request_shutdown`, yields the adapter, then restores every prior handler in `finally`.

The adapter starts no thread, timer, polling loop, daemon, or service.

Signal handling requests cancellation; it does not asynchronously interrupt a lower B3/I1-GC/C2 critical section.

## SchedulerOperationalControlsResult shape

The current result contains:

```text
status
mode
stale_recovery_status
stale_recovery_enabled
stale_recovery_attempted
stale_recovery_applied
scheduler_round_invoked
scheduler_policy_result
stale_recovery_result
cancelled
shutdown_requested
unsafe
bounded_reason_ids
schema_version
```

The schema version is fixed to `relaylm.local_scheduler_operational_controls_result.v0`.

`scheduler_policy_result` and `stale_recovery_result` are private nested results: they are excluded from repr/equality and are not projected directly.

## Exact result validation

The constructor requires:

- status in the current operational vocabulary;
- mode in `disabled`, `dry_run`, `apply`, or `invalid`;
- stale-recovery status in the current stale vocabulary;
- exact booleans for all public boolean flags;
- scheduler policy result null or exact `SchedulerPolicyRoundResult`;
- stale-recovery result null or exact `RelayMEMSLPQueueStateTransitionResult`;
- bounded/sanitized reason IDs.

Boolean coercion from integers or strings is rejected.

## Public projection

The current public projection contains exactly the responsibility-level fields:

```text
schema_version
status
mode
stale_recovery_status
stale_recovery_enabled
stale_recovery_attempted
stale_recovery_applied
scheduler_round_invoked
scheduler_policy_status
scheduler_round_status
cancelled
shutdown_requested
unsafe
bounded_reason_ids
```

The projection schema is `relaylm.local_scheduler_operational_controls_projection.v0`.

When no scheduler policy result exists:

```text
scheduler_policy_status = not_invoked
scheduler_round_status  = not_invoked
```

When it exists, only its bounded status and projected lower round status are copied. Nested policy, lane, queue, claim, or transition bodies are omitted.

## Wrapper entry point

The current entry point is:

```text
run_relaymem_slp_scheduler_operational_controls_once(
    *,
    config,
    registry=None,
    now=None,
    policy_state=None,
    cancellation=None,
    fault_injector=None,
)
```

It returns after one bounded invocation.

## Exact wrapper input checks

Current checks require:

```text
type(config) is RelayLMConfig
registry is null OR type(registry) is RelayMEMSLPPrimaryWorkerSourceRegistry
now is null OR exact timezone-aware datetime
policy_state is null OR type(policy_state) is SchedulerPolicyState
fault_injector is null OR callable
cancellation is null, exact SchedulerCancellationToken, or callable probe
```

Invalid input returns `invalid_input`, mode `invalid`, and `unsafe=true` with a bounded reason.

Current input reasons include:

```text
exact_relaylm_config_required
exact_source_registry_required
scheduler_operational_now_invalid
exact_scheduler_policy_state_required
scheduler_operational_fault_injector_invalid
scheduler_cancellation_probe_required
```

## Current config fields

O1E owns these exact operational gate fields:

```text
relaymem_local_scheduler_operational_controls_enabled
relaymem_local_scheduler_operational_controls_dry_run_only
relaymem_local_scheduler_operational_controls_apply_enabled
```

and these exact stale-recovery fields:

```text
relaymem_local_scheduler_stale_recovery_enabled
relaymem_local_scheduler_stale_recovery_dry_run_only
relaymem_local_scheduler_stale_recovery_apply_enabled
relaymem_local_scheduler_stale_recovery_max_scan_entries
```

The architecture handoff records current defaults as:

```yaml
relaymem_local_scheduler_operational_controls_enabled: false
relaymem_local_scheduler_operational_controls_dry_run_only: true
relaymem_local_scheduler_operational_controls_apply_enabled: false
relaymem_local_scheduler_stale_recovery_enabled: false
relaymem_local_scheduler_stale_recovery_dry_run_only: true
relaymem_local_scheduler_stale_recovery_apply_enabled: false
relaymem_local_scheduler_stale_recovery_max_scan_entries: 256
```

## Gate validation

All six operational/stale gate values must be exact booleans.

Failure returns:

```text
scheduler_operational_gate_must_be_bool
```

The operational triple and stale-recovery triple are normalized independently through the standard disabled/dry-run/apply mapping.

Invalid operational triple:

```text
invalid_scheduler_operational_gate_combination
```

Invalid stale triple:

```text
invalid_scheduler_stale_recovery_gate_combination
```

## Cross-gate authority constraints

Current O1E config rules require:

```text
operational mode disabled
  -> stale-recovery mode must also be disabled
```

otherwise:

```text
stale_recovery_requires_operational_controls
```

Current stale-recovery apply also requires operational apply:

```text
stale_recovery apply AND operational != apply
  -> stale_recovery_apply_requires_operational_apply
```

These are upper orchestration constraints; they do not weaken lower B3 transition gates.

## Stale scan bound

`relaymem_local_scheduler_stale_recovery_max_scan_entries` must have exact `int` type and satisfy:

```text
1 <= value <= 4096
```

Invalid values return:

```text
scheduler_stale_recovery_scan_limit_invalid
```

A boolean does not satisfy the exact-int requirement.

## Operational dry-run lower-apply fence

When O1E mode is `dry_run`, these lower apply flags must all be false:

```text
relaymem_local_scheduler_policy_apply_enabled
relaymem_local_scheduler_apply_enabled
relaymem_local_worker_apply_enabled
relaymem_slp_durable_finalization_apply_enabled
```

If any is enabled, configuration fails closed with:

```text
operational_dry_run_lower_apply_enabled
```

O1E dry-run therefore cannot wrap a known lower mutation-capable apply configuration.

## Cancellation checkpoints

Current cancellation is checked at bounded points:

```text
after input/config validation, before disabled handling
before stale recovery
before scheduler round
after scheduler round
```

The final projection is protected by a separate fault seam rather than another cancellation read in the current implementation.

A cancellation present before the first operational work returns:

```text
cancelled_before_start
```

Cancellation before stale recovery returns:

```text
cancelled_before_stale_recovery
```

Cancellation after any stale-recovery work but before the scheduler call returns:

```text
cancelled_before_scheduler_round
```

Cancellation immediately after the scheduler call returns:

```text
cancelled_after_scheduler_round
```

A checkpoint prevents **starting later work**. It does not roll back already-applied stale recovery and does not interrupt lower work already completed or in its critical section.

## Disabled mode ordering

Current ordering checks cancellation before returning the disabled result.

Therefore a caller whose cancellation token is already requested receives `cancelled_before_start` rather than `disabled`.

With no cancellation, disabled mode returns:

```text
status = disabled
reason = scheduler_operational_controls_disabled
scheduler_round_invoked = false
```

## Time input

If `now` is omitted after successful gate handling, current O1E uses:

```text
datetime.now(timezone.utc)
```

If supplied, `now` must be an exact timezone-aware `datetime`.

The stale scanner and lower scheduler policy receive the same exact current time for the invocation.

## Stale-recovery orchestration

O1E owns only orchestration of one possible stale claim.

It does not rewrite a queue record directly.

The path is:

```text
bounded queue-root scan
  -> choose at most one expired claimed record
  -> construct exact RelayMEMSLPQueueTransitionRequest(kind=stale_recovery)
  -> call transition_relaymem_slp_queue_state(...)
```

B3 remains the queue transition authority.

## Stale-recovery discovery input

The private scanner requires:

```text
valid timezone-aware now
exact int max_entries in 1..4096
```

Invalid discovery input returns private scanner status `unsafe` with:

```text
stale_recovery_discovery_input_invalid
```

## Queue-root opening and locking

The scanner uses the existing queue-storage authority to:

```text
open_queue_root(...)
acquire_queue_lock(root_fd, exclusive=false)
read_record_snapshot(...)
release_queue_lock(...)
```

A busy shared queue lock returns `no_candidate` with bounded reason `queue_lock_busy`.

Other root/lock/read failures close toward `unsafe` and then `stale_recovery_failed` at the O1E boundary.

The file descriptor is closed in `finally`.

## Queue filename bound

Only queue filenames matching the current queue filename prefix plus exactly 64 lowercase hexadecimal characters and `.json` are considered candidates.

Other directory entries are ignored.

O1E does not follow arbitrary filenames as queue records.

## Scan-count behavior

The scanner increments the `scanned` count for every directory entry encountered, before queue-filename filtering.

If:

```text
scanned > max_entries
```

it returns unsafe with:

```text
stale_recovery_scan_limit_exceeded
```

This means unrelated directory entries still consume the bounded scan budget.

## Record validation

For every queue-shaped filename encountered, O1E requires `read_record_snapshot` to return:

```text
snapshot != null
status == ok
```

Otherwise discovery fails closed using lower bounded reasons or:

```text
stale_recovery_record_invalid
```

O1E does not skip malformed queue-shaped records and continue opportunistically.

## Claimed-record eligibility

Only records whose exact current state is:

```text
claimed
```

are stale-recovery candidates.

Other states are ignored.

For a claimed record, `lease_expires_at` must parse successfully. Invalid lease expiry fails the scan closed with:

```text
stale_recovery_lease_expiry_invalid
```

A record is stale only when:

```text
lease_expires_at <= now
```

## Deterministic stale candidate selection

Every expired claimed candidate is collected as `(filename, snapshot)`.

After the bounded scan, candidates are sorted lexicographically by filename and the first candidate is selected.

O1E therefore selects at most one stale claim per invocation and does so deterministically under an unchanged queue snapshot.

## B3 stale-recovery request

For the selected record, O1E constructs an exact `RelayMEMSLPQueueTransitionRequest` with:

```text
transition_kind = stale_recovery
job_id = record.job_id
dispatch_idempotency_key = record.dispatch_idempotency_key
expected_record_revision = record.record_revision
expected_state = claimed
claim_generation = record.claim_generation
lease_token = record.lease_token
```

Those private values are passed only to the lower B3 transition authority and are not copied into the O1E public projection.

## B3 execution gates

The lower transition call uses:

```text
enabled = true
dry_run_only = stale_mode == dry_run
apply_enabled = stale_mode == apply
```

A B3 `dry_run_ready` result maps to:

```text
stale_recovery_dry_run_ready
```

A B3 `applied` result maps to:

```text
stale_recovery_attempted
```

Any other lower transition status maps to:

```text
stale_recovery_failed
```

The public `stale_recovery_applied` flag is true only when the lower exact result has `transition_applied=true`.

## No-candidate behavior

A successful bounded scan with no expired claimed candidate returns:

```text
stale_recovery_no_candidate
```

No B3 transition is invoked.

Stale-recovery absence does not prevent the later scheduler round from running when the rest of the O1E invocation remains valid.

## Stale-recovery failure behavior

A discovery exception, unsafe discovery result, transition-construction exception, transition-call exception, or lower nonaccepted transition status results in:

```text
stale_recovery_failed
```

The outer O1E wrapper then returns:

```text
status = unexpected_failure
reason = scheduler_stale_recovery_failed
unsafe = true
```

and does not start the scheduler round.

## Scheduler delegation

After stale-recovery orchestration and its cancellation checkpoint, O1E calls exactly the separately owned policy wrapper:

```text
run_relaymem_slp_scheduler_round_once_with_policy(...)
```

with:

```text
config
registry
exact_now
policy_state
fault_injector
```

O1E does not call replay or queue lanes directly.

## Scheduler result validation

If the policy wrapper raises:

```text
status = unexpected_failure
reason = scheduler_operational_round_failed
unsafe = true
```

If it returns anything other than exact `SchedulerPolicyRoundResult`:

```text
status = unexpected_failure
reason = scheduler_operational_round_result_invalid
unsafe = true
```

No second scheduler round is attempted.

## Successful completion

When the scheduler call returns an exact policy result and cancellation is not requested afterward, current completion is:

```text
mode == dry_run
  -> status = dry_run_ready

mode == apply
  -> status = completed
```

The result carries:

```text
scheduler_round_invoked = true
reason = scheduler_operational_controls_completed
unsafe = scheduler_policy_result.unsafe
```

O1E does not reinterpret lower scheduler unsafe state into a new mutation authority.

## Fault seams

The current bounded fault seams are:

```text
before_stale_recovery
during_stale_recovery_scan
before_b3_stale_recovery_transition
after_stale_recovery_before_scheduler_round
before_operational_projection_return
```

The outer wrapper maps failures at its outer seams to bounded reasons including:

```text
scheduler_operational_fault_before_stale_recovery
scheduler_operational_fault_before_scheduler_round
scheduler_operational_fault_before_return
```

A scanner/transition exception maps through stale-recovery failure handling.

Fault injection is validation support, not runtime retry authority.

## Shutdown semantics

The current signal adapter only flips the cancellation token. The core wrapper reacts through the cancellation checkpoints described above.

`shutdown_requested` and the `shutdown_requested` status remain accepted current result vocabulary/fields, but the normal `SchedulerSignalCancellationAdapter` path does not independently mint them in `run_relaymem_slp_scheduler_operational_controls_once`.

Documentation must therefore not equate signal receipt with a separate shutdown state transition beyond cancellation unless the implementation changes.

## Leakage boundary

O1E public projection must not expose:

```text
queue job ID
dispatch idempotency key
record revision
claim generation
lease token
lease owner
queue root/path
queue filename
exact lease expiry or retry timestamp
record body
memory/protected-source content
nested B3 transition result
nested scheduler policy or lane result
raw exception
```

Only bounded status/mode values, booleans, abstract reason IDs, and lower status summaries may cross the public projection.

## No-loop / no-supervision invariant

The core O1E module does not own:

```text
polling
sleep
repeated retry loop
background task/thread
timer
daemonization
service supervision
process restart policy
health endpoint
long-lived scheduler ownership
```

Those concerns belong to later O2/O3 layers or external process supervision.

## Stable invariants

- One O1E invocation starts at most one stale-recovery B3 transition and at most one O1D2/O1D1 scheduler round.
- Cancellation probe exceptions fail toward cancellation.
- Signal handling is opt-in and restored after the context manager exits.
- Operational and stale-recovery gates use exact disabled/dry-run/apply triples.
- Stale recovery cannot run when O1E is disabled, and stale apply requires O1E apply.
- O1E dry-run cannot wrap the known lower scheduler/worker/finalization apply gates.
- Stale scan is bounded to 1..4096 entries and at most one selected candidate.
- Queue-shaped malformed records fail the stale scan closed rather than being skipped.
- Only expired `claimed` records are eligible.
- Deterministic stale selection is lexicographic by queue filename.
- O1E delegates the actual state transition to B3 and never rewrites queue records directly.
- Private queue identity and lease data never enter the public O1E projection.
- O1E calls the scheduler policy wrapper at most once and never calls replay/queue lanes directly.
- O1E never sleeps, loops, polls, or supervises.
- O2/O3 remain separate operational lifecycle owners.

## Non-goals

This contract does not define:

- B3's complete queue transition state machine;
- replay-lane or queue-lane discovery semantics;
- I1-GC replay or C2 worker execution;
- O1D2 fairness/backoff/pacing already owned by `scheduler-policy.md`;
- service polling or supervision;
- always-on local scheduler process lifecycle;
- general RelayRUN compute scheduling;
- source retirement or redirect creation;
- repository-level implementation sequencing.

## Related authority

- [Runtime Scheduler Policy Contract](scheduler-policy.md)
- [Runtime Scheduler Round Contract](scheduler-round.md)
- [O1E Scheduler Operational Controls](../../architecture/o1e_scheduler_operational_controls.md)
- [Runtime Scheduler Architecture](../../architecture/runtime/scheduler.md)
