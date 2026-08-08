---
relaylm_doc_type: contract
relaylm_authority: current_relaymem_slp_scheduler_round_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_update_trigger:
  - SchedulerGates, LaneOutcome, or SchedulerRoundResult exact fields change
  - one-round replay/queue invocation order or work-unit bounds change
  - scheduler configuration gates or accepted mode triples change
  - round projection schema, statuses, dispositions, or reason bounds change
  - one-round fault or projection-validation behavior changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - replay-lane discovery, I1-GC replay, or durable-finalization semantics
  - queue-lane discovery, B3 claim/retry, or C2 worker coordination semantics
  - O1D2 fairness, retry-time, backoff, jitter, or pacing policy
  - O1E cancellation, stale-recovery, or graceful-shutdown orchestration
  - O2/O3 service supervision, polling, loop, CLI-process, or always-on lifecycle
  - target Resource Provider or general compute scheduling
  - checkpoint/recovery, request routing, backend execution, or memory semantics
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/scheduler.md
  - ../../architecture/o1a_two_lane_scheduler_contract.md
  - ../../architecture/o1d1_production_scheduler_round.md
  - ../../architecture/o1d2_scheduler_policy.md
  - ../../architecture/o1e_scheduler_operational_controls.md
  - ../relayrun-checkpoint-and-recovery.md
relaylm_verified_by:
  - ../../../scripts/relaylm_o1a_two_lane_scheduler_contract_smoke.py
  - ../../../scripts/relaylm_o1d1_production_round_smoke.py
  - ../../../scripts/relaylm_o1d1_production_round_fault_smoke.py
  - ../../../scripts/relaylm_o1d1_production_round_concurrency_smoke.py
  - ../../../scripts/relaylm_o1d1_production_round_security_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM SLP scheduler and operations maintainers
  - replay-lane and queue-lane integration maintainers
  - runtime, service, recovery, security, and observability reviewers
relaylm_authority_level: exact_contract
---
# Runtime Scheduler Round Contract

## Authority summary

This contract owns the exact current **one-round** RelayMEM/SLP scheduler contract and O1D1 production coordinator boundary.

It combines two current layers without absorbing their lane internals:

```text
O1A pure contract
  -> validate already-bounded gates and lane outcomes
  -> aggregate one round
  -> derive content-free result/projection

O1D1 production coordinator
  -> build accepted gates from one exact server-owned RelayLMConfig
  -> invoke replay lane at most once
  -> invoke queue lane at most once
  -> aggregate through O1A
  -> validate the exact public projection
  -> return without sleep or another round
```

The exact current lane order is:

```text
replay -> queue
```

when both lanes are enabled.

This contract does **not** own recurring scheduling, fairness, backoff, shutdown orchestration, service supervision, or general compute-resource scheduling.

## Current implementation anchors

The exact current contract is implemented by:

```text
relaylm/relaymem_slp_scheduler_contract.py
relaylm/relaymem_slp_scheduler_round.py
```

The production round delegates to separately owned lane implementations:

```text
relaylm/relaymem_slp_scheduler_replay_lane.py
relaylm/relaymem_slp_scheduler_queue_lane.py
```

The current implementation handoffs remain transitional sources:

```text
docs/architecture/o1a_two_lane_scheduler_contract.md
docs/architecture/o1d1_production_scheduler_round.md
```

This transaction does not retire those sources.

## Current schema identifiers

The exact current scheduler schemas are:

```text
ROUND_RESULT_SCHEMA     = relaylm.local_scheduler_round_result.v0
ROUND_PROJECTION_SCHEMA = relaylm.local_scheduler_round_projection.v0
LANE_RESULT_SCHEMA      = relaylm.local_scheduler_lane_result.v0
```

The exact current reason bounds are:

```text
MAX_REASON_IDS_PER_LANE = 8
MAX_ROUND_REASON_IDS    = 16
```

Every bounded scheduler reason ID must match:

```regex
^[a-z][a-z0-9_]{0,63}$
```

Reason IDs must also be unique within the tuple/list being validated.

## Lane kinds

The exact current lane kinds are:

```text
replay
queue
```

No generic third lane or plugin lane is implied by the current contract.

## Round dispositions

The exact current round dispositions are:

```text
stop
run_next_round
idle
```

A disposition is a bounded recommendation/result of one round. O1D1 does not act on `run_next_round` by recursively starting another round.

## Round statuses

The exact current scheduler-round statuses are:

```text
disabled
invalid_input
invalid_configuration
round_completed
partial_progress
idle
blocked
unsafe_state
unexpected_failure
```

No additional service-loop, cancellation, shutdown, or timeout status is owned by this one-round contract.

## Replay-lane statuses accepted by O1A/O1D1

The exact current replay-lane statuses are:

```text
dependency_unavailable
no_eligible_work
busy
candidate_changed
delegated
completed
already_complete
not_replayable
isolated
unsafe_state
failed
```

These are scheduler adapter outcomes. They do not replace I1-G/I1-GC durable-finalization statuses.

## Queue-lane statuses accepted by O1A/O1D1

The exact current queue-lane statuses are:

```text
no_eligible_work
future_retry_only
busy
candidate_changed
dry_run_ready
delegated
executed
retry_released
terminal
cleanup_required
unsafe_state
failed
```

These are scheduler adapter outcomes. They do not replace B2/B3/C2 queue, claim, retry, or execution statuses.

## SchedulerGates shape

`SchedulerGates` is an immutable current object with exactly:

```text
enabled
dry_run_only
apply_enabled
replay_lane_enabled
queue_lane_enabled
required_dependency_available
supported_schema
```

The last two fields default to:

```text
required_dependency_available = true
supported_schema = true
```

Every field must be an exact `bool`; integer/string/null coercion is rejected.

## Current gate modes

The exact current mode mapping is:

```text
(enabled=false, dry_run_only=true,  apply_enabled=false) -> disabled
(enabled=true,  dry_run_only=true,  apply_enabled=false) -> dry_run
(enabled=true,  dry_run_only=false, apply_enabled=true)  -> apply
anything else                                           -> invalid
```

The scheduler gate is only an upper authority. `apply` does not elevate I1-GC, B3, C2, worker, or memory mutation gates owned below this round.

## Scheduler gate validation reasons

`SchedulerGates.validation_reason_ids()` currently returns the first applicable bounded condition in this order:

1. `unsupported_scheduler_schema` when `supported_schema` is false;
2. `invalid_scheduler_gate_combination` when the mode tuple is invalid;
3. `no_scheduler_lane_enabled` when scheduler is enabled and neither lane is enabled;
4. `required_dependency_unavailable` when scheduler is enabled and required enabled-lane dependencies are unavailable;
5. otherwise no reason IDs.

The method does not inspect queue roots, replay records, claims, or worker state.

## Production configuration fields

`build_relaymem_slp_scheduler_gates(config)` consumes these exact current `RelayLMConfig` fields:

```text
relaymem_local_scheduler_enabled
relaymem_local_scheduler_dry_run_only
relaymem_local_scheduler_apply_enabled
relaymem_local_scheduler_replay_lane_enabled
relaymem_local_scheduler_queue_lane_enabled
```

Current defaults recorded by the O1D1 implementation boundary are:

```yaml
relaymem_local_scheduler_enabled: false
relaymem_local_scheduler_dry_run_only: true
relaymem_local_scheduler_apply_enabled: false
relaymem_local_scheduler_replay_lane_enabled: true
relaymem_local_scheduler_queue_lane_enabled: true
```

The gate builder requires `type(config) is RelayLMConfig` and requires each configured gate value to be an exact boolean.

## Production dependency-availability gate

For each enabled lane, the production gate builder checks that its current lane delegate is callable.

The resulting `required_dependency_available` value is true exactly when:

```text
replay disabled OR replay delegate callable
AND
queue disabled OR queue delegate callable
```

The builder sets `supported_schema = true` under the current implementation.

Dependency availability at this layer is a callable-boundary check only. It is not proof that a lane has eligible work or that its deeper storage/worker dependencies will succeed.

## LaneOutcome shape

`LaneOutcome` is an immutable current object with exactly these public/internal fields:

```text
lane_kind
status
enabled
attempted
candidate_observed
candidate_selected
canonical_reread_performed
delegation_attempted
delegation_completed
mutation_may_have_occurred
no_immediate_work
future_work_hint_present
contention_observed
retryable
unsafe
terminal_for_candidate
bounded_reason_ids
private_delegate_result
schema_version
```

`schema_version` is fixed to `relaylm.local_scheduler_lane_result.v0`.

`private_delegate_result` is excluded from `repr` and equality and is never emitted by the scheduler projection.

## LaneOutcome boolean exactness

The following current lane fields must each have exact `bool` type:

```text
enabled
attempted
candidate_observed
candidate_selected
canonical_reread_performed
delegation_attempted
delegation_completed
mutation_may_have_occurred
no_immediate_work
future_work_hint_present
contention_observed
retryable
unsafe
terminal_for_candidate
```

Boolean coercion from integer/string values is not accepted by the pure contract.

## LaneOutcome structural invariants

The current constructor enforces:

- disabled lane cannot be attempted;
- delegation completion requires delegation attempt;
- delegation attempt requires lane attempt;
- selected candidate requires candidate observation;
- canonical reread requires candidate selection;
- delegation requires canonical reread;
- `no_eligible_work` and `future_retry_only` cannot attempt delegation;
- queue `busy` cannot follow delegation;
- progress statuses require completed delegation;
- `candidate_changed` requires a selected candidate;
- `future_retry_only` requires a future-work hint;
- `busy` requires contention observed;
- `unsafe_state` and replay `isolated` require `unsafe=true`;
- `no_immediate_work` cannot accompany a progress status.

The current replay lane is allowed to return `busy` after a delegation attempt because its lower replay boundary may encounter nonblocking contention during the delegated path. The queue lane does not allow that combination under this contract.

## Progress statuses

The exact current progress-status set used by pure round aggregation is:

```text
completed
already_complete
dry_run_ready
executed
retry_released
terminal
```

`delegated` itself is not in the progress-status set.

A lane may still cause round progress through `mutation_may_have_occurred=true` or through `candidate_changed`, as described below.

## Failure statuses

The exact current failure-status set used by aggregation is:

```text
dependency_unavailable
failed
unsafe_state
isolated
```

The same set is applied against the lane outcomes that can legally carry those status values.

## Immediate-retry status

The exact current immediate-retry status set is:

```text
candidate_changed
```

A `candidate_changed` outcome therefore contributes to the round's `progress` predicate even when no delegation completed.

## Idle-compatible statuses

The exact current idle-status set is:

```text
no_eligible_work
future_retry_only
busy
not_replayable
cleanup_required
failed
dependency_unavailable
unsafe_state
isolated
delegated
```

When no progress is detected, every present lane must either report `no_immediate_work=true` or have one of these statuses. Otherwise pure aggregation rejects the input with `lane_outcome_has_no_disposition`.

This set does not mean every listed status is semantically successful. It only participates in disposition derivation when no progress is present.

## SchedulerRoundResult shape

`SchedulerRoundResult` is an immutable current object with exactly:

```text
status
disposition
replay_lane
queue_lane
work_units_attempted
work_units_completed
idle_recommended
immediate_next_round_recommended
future_work_hint_present
retryable
unsafe
bounded_reason_ids
schema_version
```

`schema_version` is fixed to:

```text
relaylm.local_scheduler_round_result.v0
```

Nested replay/queue outcomes are excluded from the dataclass `repr`.

## Round-result work-unit bounds

The exact current result constraints are:

```text
0 <= work_units_attempted <= 2
0 <= work_units_completed <= work_units_attempted
```

Both values must be exact integers.

The pure aggregator defines a work unit here as a lane with `delegation_attempted=true`; completion counts lanes with `delegation_completed=true`.

## Round recommendation consistency

The current result requires exact booleans for:

```text
idle_recommended
immediate_next_round_recommended
future_work_hint_present
retryable
unsafe
```

and enforces:

```text
idle_recommended == (disposition == "idle")
immediate_next_round_recommended == (disposition == "run_next_round")
```

A `stop` result therefore has both recommendation flags false.

## Pure aggregate_scheduler_round inputs

`aggregate_scheduler_round(...)` receives:

```text
gates
invocation_order
replay_lane
queue_lane
```

It invokes no lane, reads no filesystem, uses no clock, sleeps nowhere, and mutates no external state.

The explicit `invocation_order` lets the pure contract prove that a production caller did not invert or duplicate the fixed current lane order.

## Gate-failure aggregation

If gate validation yields reason IDs, pure aggregation requires:

```text
replay_lane is null
queue_lane is null
invocation_order is empty
```

Any lane activity supplied alongside a scheduler-level gate failure is rejected with:

```text
scheduler_level_failure_must_precede_lane_invocation
```

For accepted gate-failure input, current status selection is:

```text
first reason in {
  invalid_scheduler_gate_combination,
  no_scheduler_lane_enabled
}
  -> invalid_configuration

otherwise
  -> blocked
```

The result is always `disposition=stop`, with zero work units.

`unsafe` is false for `invalid_configuration` and true for other blocked gate failures.

## Disabled aggregation

When `gates.mode == "disabled"`, pure aggregation also requires no lane results and empty invocation order.

Otherwise it raises:

```text
disabled_scheduler_must_not_invoke_lanes
```

The exact disabled result is:

```text
status = disabled
disposition = stop
work_units_attempted = 0
work_units_completed = 0
idle_recommended = false
immediate_next_round_recommended = false
future_work_hint_present = false
retryable = false
unsafe = false
bounded_reason_ids = ("scheduler_disabled",)
```

## Exact current invocation order

For a non-disabled, gate-valid round, pure aggregation computes expected invocation order from enabled lanes in exactly this sequence:

```text
replay, then queue
```

Examples:

```text
replay=true, queue=true   -> ("replay", "queue")
replay=true, queue=false  -> ("replay",)
replay=false, queue=true  -> ("queue",)
```

The supplied order must equal the computed tuple exactly or aggregation raises:

```text
invalid_lane_invocation_order
```

## Lane presence consistency

Pure aggregation enforces:

```text
replay_lane_enabled == (replay_lane is present)
queue_lane_enabled  == (queue_lane is present)
```

A supplied replay outcome must have:

```text
lane_kind = replay
enabled = true
```

A supplied queue outcome must have:

```text
lane_kind = queue
enabled = true
```

Mismatches are rejected before result derivation.

## Round progress predicate

For each present lane, the current pure aggregator treats the round as having progress when **any** lane satisfies at least one of:

```text
lane.status is in current progress statuses
lane.mutation_may_have_occurred is true
lane.status == candidate_changed
```

If progress is true:

```text
disposition = run_next_round
```

The aggregator does not calculate when the next round should occur.

## Idle disposition

When no progress is detected, every present lane must be idle-compatible under the exact current rule.

Then:

```text
disposition = idle
```

`idle` means this bounded round recommends no immediate work. It does not prove permanent queue emptiness and does not start a sleep/timer itself.

## Round status derivation

After work counts, progress/failure/unsafe state, future hint, retryability, and disposition are derived, current status precedence is exactly:

```text
if any lane unsafe:
    unsafe_state
elif any delegation completed AND any failure-status lane exists:
    partial_progress
elif any delegation completed AND progress is true:
    round_completed
elif failure-status lane exists AND no lane is retryable:
    blocked
else:
    idle
```

This means the result status and disposition answer different questions.

For example, an unsafe lane can still coexist with a `run_next_round` disposition if the round's progress predicate was already true. Downstream O1D2/O1E policy/control layers decide what to do with the returned bounded result; O1A itself does not start another round.

## Combined round reason IDs

Pure aggregation combines lane reason IDs in lane tuple order:

```text
replay reasons first, then queue reasons
```

Each reason is appended only on its first occurrence.

The combined tuple is then revalidated against:

```text
MAX_ROUND_REASON_IDS = 16
unique IDs
^[a-z][a-z0-9_]{0,63}$
```

No nested delegate result or raw exception is copied into the round reason tuple.

## Round projection exact keys

`SchedulerRoundResult.projection()` emits exactly:

```text
schema_version
status
disposition
replay_lane_enabled
replay_lane_attempted
replay_lane_status
replay_candidate_selected
replay_delegated
replay_completed
queue_lane_enabled
queue_lane_attempted
queue_lane_status
queue_candidate_selected
queue_delegated
queue_completed
work_units_attempted
work_units_completed
idle_recommended
immediate_next_round_recommended
future_work_hint_present
retryable
unsafe
bounded_reason_ids
```

When a lane result is absent, its projection status is:

```text
not_invoked
```

and its projected booleans are false.

## Projection content boundary

The current round projection is intentionally content-free.

It does not expose:

- user/assistant/source content;
- protected-source bodies;
- memory title/summary/body;
- namespace or character values;
- run/session/turn/job/dispatch/locator identities;
- queue/finalization filenames or roots;
- relative or absolute paths;
- claim owner, lease token, generation, or revision;
- exact retry/completion timestamps;
- digests or fingerprints;
- raw exceptions;
- nested I1-GC/C2/private delegate results.

The scheduler can report bounded operational disposition without becoming another memory or queue-record inspection surface.

## Production round entry point

The exact current O1D1 entry is:

```text
run_relaymem_slp_scheduler_round_once(
    *,
    config: RelayLMConfig,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None = None,
    now: datetime | None = None,
    fault_injector: Callable[[str], None] | None = None,
) -> SchedulerRoundResult
```

`fault_injector` is an internal test seam, not a config/CLI/browser/API authority.

## Production input exactness

The current one-round entry validates inputs before lane work:

- `config` must have exact type `RelayLMConfig`, otherwise `invalid_input` / `exact_relaylm_config_required`;
- supplied `registry` must have exact type `RelayMEMSLPPrimaryWorkerSourceRegistry`, otherwise `invalid_input` / `exact_source_registry_required`;
- supplied `now` must have exact type `datetime`, non-null `tzinfo`, and non-null `utcoffset()`, otherwise `invalid_input` / `scheduler_now_invalid`;
- supplied `fault_injector` must be callable, otherwise `invalid_input` / `scheduler_fault_injector_invalid`.

These failures return a bounded result; they do not invoke either lane.

## Invalid-input result

Current `_invalid_input_result(reason_id)` returns:

```text
status = invalid_input
disposition = stop
replay_lane = null
queue_lane = null
work_units_attempted = 0
work_units_completed = 0
idle_recommended = false
immediate_next_round_recommended = false
future_work_hint_present = false
retryable = false
unsafe = true
bounded_reason_ids = (reason_id,)
```

The one-round coordinator does not include the rejected raw input value in this result.

## Invalid-configuration result

When current gate construction raises `AttributeError`, `TypeError`, or `ValueError`, O1D1 returns:

```text
status = invalid_configuration
disposition = stop
work_units_attempted = 0
work_units_completed = 0
retryable = false
unsafe = false
bounded_reason_ids = ("scheduler_config_schema_invalid",)
```

No lane is invoked.

## Gate result before lane invocation

After production gates are built, O1D1 obtains `gates.validation_reason_ids()`.

If reasons are present, or `gates.mode == "disabled"`, it delegates result construction to the pure aggregator with:

```text
invocation_order = ()
replay_lane = null
queue_lane = null
```

It then validates the projection before returning the result.

This preserves one pure status/disposition authority rather than duplicating disabled/gate-failure aggregation in the production coordinator.

## Replay lane invocation

For a valid enabled round with `replay_lane_enabled=true`, O1D1 calls exactly one:

```text
run_relaymem_slp_scheduler_replay_lane_once(
    config=config,
    gates=gates,
    registry=registry,
    fault_injector=fault_injector,
)
```

The coordinator does not loop or choose a second replay candidate.

If the delegate raises unexpectedly, O1D1 returns an `unexpected_failure` result with:

```text
replay_lane_unexpected_failure
```

If the returned object is not exact `LaneOutcome`, has the wrong `lane_kind`, or has a status outside current replay statuses, the round returns:

```text
replay_lane_result_invalid
```

The invalid private result is not projected.

## Queue lane invocation

For a valid enabled round with `queue_lane_enabled=true`, O1D1 calls exactly one:

```text
run_relaymem_slp_scheduler_queue_lane_once(
    config=config,
    gates=gates,
    now=now,
    fault_injector=fault_injector,
)
```

If both lanes are enabled, this call happens only after the replay-lane call has returned.

If the delegate raises unexpectedly, O1D1 returns an `unexpected_failure` result with:

```text
queue_lane_unexpected_failure
```

If the returned object is not exact `LaneOutcome`, has the wrong `lane_kind`, or has a status outside current queue statuses, the round returns:

```text
queue_lane_result_invalid
```

## Same-round replay-to-queue boundary

Because replay runs before queue, replay convergence may publish a queue record that the queue lane can independently discover in the same round.

The scheduler coordinator does not pass replay-private authority into the queue lane.

It does not transfer:

- replay locator;
- job/dispatch identity;
- selected replay candidate object;
- completion marker;
- private delegate result;
- special priority hint.

The queue lane performs its own bounded discovery and canonical reread under its own current authority.

A newly published record can therefore become eligible in the same round, but the scheduler does not guarantee that it will be selected.

## At-most-once-per-lane round bound

Within one O1D1 invocation:

```text
replay-lane delegate calls <= 1
queue-lane delegate calls  <= 1
total delegated work units <= 2
```

The one-round coordinator does not recurse, poll, sleep, internally retry a lane, rescan in a loop, or begin a second scheduler round.

`run_next_round` remains a returned disposition for an outer policy/service caller.

## Optional `now`

When supplied, `now` must be one exact timezone-aware `datetime`.

O1D1 passes it only to the current queue-lane call.

The one-round coordinator does not:

- expose exact retry timestamps in its public projection;
- calculate next-delay seconds;
- calculate backoff or jitter;
- sleep until a retry time.

Those policy concerns are outside this contract.

## Internal production fault seams

The exact current O1D1 fault seam labels are:

```text
after_gate_validation_before_replay
after_replay_before_queue
after_queue_before_aggregation
after_aggregation_before_projection
after_projection_before_return
```

A configured test `fault_injector` is called only at those bounded internal points.

Any exception raised by the fault seam is converted to a content-free `unexpected_failure` result using the corresponding bounded reason described below.

## Fault reason mapping

Current fault-seam reason mapping is:

```text
after_gate_validation_before_replay -> scheduler_fault_before_replay
after_replay_before_queue           -> scheduler_fault_before_queue
after_queue_before_aggregation      -> scheduler_fault_before_aggregation
after_aggregation_before_projection -> scheduler_fault_before_projection
after_projection_before_return      -> scheduler_fault_before_return
```

A fault after replay preserves a valid replay outcome in the returned internal round result where current code passes it to `_unexpected_failure_result`.

A fault before queue records no queue invocation.

No completed lower-layer mutation is rolled back by O1D1.

## Aggregation failure

After enabled lanes return, O1D1 calls the pure aggregator with the exact recorded invocation order and lane outcomes.

An unexpected exception from that aggregation boundary becomes:

```text
status = unexpected_failure
disposition = stop
bounded_reason_ids = ("scheduler_aggregation_failed",)
```

Any valid lane outcomes already available are passed into the bounded failure-result constructor.

## Unexpected-failure result

`_unexpected_failure_result(...)` constructs:

```text
status = unexpected_failure
disposition = stop
idle_recommended = false
immediate_next_round_recommended = false
retryable = false
unsafe = true
```

It preserves an input lane only when `type(lane) is LaneOutcome`.

It counts `work_units_attempted` from preserved lanes with `delegation_attempted=true`, and `work_units_completed` from preserved lanes with `delegation_completed=true`.

`future_work_hint_present` is true when any preserved lane reports a future-work hint.

The bounded reason tuple contains only the supplied fixed failure reason.

The helper does not serialize a raw exception.

## Production projection validation

Before normal production return, O1D1 validates the exact projection shape and equality against the current `SchedulerRoundResult`.

The current validator requires:

- projection exact type `dict`;
- exact projection key set;
- exact projection schema version;
- status in the current round-status set;
- disposition in `stop | run_next_round | idle`;
- lane status in the appropriate current status set or `not_invoked`;
- every projected boolean key exact `bool`;
- `work_units_attempted` exact int from 0 through 2;
- `work_units_completed` exact int from 0 through attempted;
- `bounded_reason_ids` exact list with at most 16 entries;
- unique reason IDs matching the current regex;
- complete mapping equality to the projection derived from the internal result.

## Projection failure

Any failure while building or validating the production projection becomes an `unexpected_failure` result with:

```text
scheduler_projection_invalid
```

The coordinator does not return the malformed projection as a successful scheduler result.

The disabled/gate-failure helper `_return_validated(...)` applies the same projection-validation boundary before returning.

## Production invocation-order recording

The coordinator appends `"replay"` to its internal invocation-order list only after a valid replay-lane result is returned.

It appends `"queue"` only after a valid queue-lane result is returned.

That tuple is passed to pure aggregation.

The production coordinator therefore does not fabricate a successful lane invocation in the aggregate contract when the delegate raised or returned an invalid result.

## Concurrency boundary

O1D1 itself is sequential and single-threaded inside one call.

The current contract does not establish a global scheduler mutex, leader election, durable scheduler-round journal, or one-process-only correctness rule.

Multiple callers may invoke separate rounds concurrently.

Correctness under such overlap remains delegated to lower owning boundaries such as replay record locking/fences, queue discovery/advisory locking, B3 claim/CAS/lease behavior, and C2 exact current-claim validation.

Service-level single-instance or process supervision policy is not O1D1 authority.

## No durable round identity

The one-round scheduler does not persist a scheduler-round record or durable scheduler-round ID.

Restart safety remains delegated to the durable lower layers that own replay completion, queue claims, and worker idempotency/current-state checks.

The current public projection also omits run/session/turn/job/dispatch/locator identities.

## No sleep or polling

Neither the pure O1A contract nor O1D1 production round:

- polls continuously;
- sleeps;
- registers a recurring timer;
- watches roots for changes;
- computes a backoff schedule;
- runs a daemon/service loop;
- supervises a worker process.

Those effects belong to later policy/control/service layers where implemented.

## O1D2 remains separate

O1D2 owns scheduler policy around one-round results, including the current bounded responsibilities described by its own authority such as:

- fairness/starvation prevention;
- retry-time interpretation;
- bounded backoff;
- bounded jitter;
- saturation pacing;
- deterministic later-round timing/policy hints.

This scheduler-round contract does not import those values into O1A/O1D1 and does not infer them from `idle` or `run_next_round` alone.

## O1E remains separate

O1E owns caller-invoked operational controls such as current stale-claim recovery orchestration, cancellation checkpoints, and graceful shutdown behavior.

O1D1 has internal fault seams, but those test seams are not a cancellation API and do not make O1D1 the shutdown owner.

A later outer control may decide not to invoke or continue another round; that does not change the exact semantics of one completed O1D1 result.

## O2/O3 remain separate

O2/O3 own opt-in local service/process wrapping above the bounded O1 stack.

Their existence does not make `run_relaymem_slp_scheduler_round_once` itself recurring or always-on.

This contract must not be cited as proof that O1D1:

- owns a polling loop;
- owns worker-process supervision;
- guarantees single-process service ownership;
- sleeps between rounds;
- keeps running after return.

## Target Resource Provider is separate

The target scheduler architecture may describe broader `RelayRUN` or Resource Provider responsibilities for asynchronous work and resource allocation.

This current contract does not claim that the O1D1 RelayMEM/SLP scheduler round is that full target scheduler.

O1D1 coordinates two current bounded RelayMEM/SLP work opportunities only.

## Lane semantic non-authority

The one-round scheduler does not own:

- I1-G record schema, seal, replay, completion, isolation, retention, or cleanup;
- protected-source persistence/rehydration;
- B2 queue publication;
- B3 claim, lease, retry, stale recovery, terminal lifecycle;
- C2 queued-record request construction/coordination;
- worker execution;
- Subjective MEM formation, retrieval, correction, forget, restore, or lifecycle;
- queue/finalization repair.

A scheduler lane status is an adapter summary and cannot replace those lower state machines.

## Root and identity non-authority

The scheduler result/projection does not create or expose durable record identity.

O1D1 does not create queue/finalization roots from lane records and does not accept browser/CLI supplied locators, job IDs, dispatch IDs, claims, or roots as part of this one-round entry contract.

Server-owned configuration and lower adapters retain their own path/root validation boundaries.

## Content-free public boundary

The exact scheduler projection consists only of:

- schema/status/disposition;
- enabled/attempted/selected/delegated/completed booleans;
- bounded work counts;
- idle/immediate-next-round/future-hint/retryable/unsafe booleans;
- bounded reason IDs.

It intentionally excludes content and sensitive operational identity.

Any future projection expansion requires explicit contract review; lower private delegate results do not become public by default.

## Stable invariants

- The scheduler round has exactly two current lane kinds: replay and queue.
- The current fixed lane order is replay before queue when both are enabled.
- Each enabled lane is invoked at most once per O1D1 call.
- Delegated work units per round are bounded at two.
- The pure O1A aggregator invokes no lanes and performs no I/O or sleep.
- `SchedulerGates` and lane/result boolean fields require exact booleans.
- Only disabled, dry-run, and apply gate triples are valid.
- An enabled scheduler requires at least one enabled lane and available enabled-lane delegates.
- Scheduler apply is only an upper authority and never elevates lower replay/queue/worker mutation gates.
- Disabled/invalid scheduler-level state invokes no lane.
- Replay and queue lane outcomes retain distinct allowed status sets.
- Lane delegation requires observation -> selection -> canonical reread -> delegation consistency under current invariants.
- `future_retry_only` requires a future-work hint; `busy` requires contention.
- Progress is derived from current progress statuses, possible mutation, or candidate change.
- Progress yields `run_next_round`; a no-progress idle-compatible round yields `idle`.
- O1A derives round status with unsafe before partial-progress before completed-progress before blocked-failure precedence.
- Lane reason IDs combine replay-first then queue, de-duplicated and bounded to 16.
- Public projection has an exact current key set and is content-free.
- O1D1 converts unexpected delegate/aggregation/projection/fault failures to fixed bounded `unexpected_failure` results without raw exception text.
- A completed replay result is not rolled back when a later queue/fault failure occurs.
- Same-round queue discovery remains independent; replay output is not queue selection authority.
- `now` is optional, exact timezone-aware when supplied, and is passed only to the queue lane.
- O1D1 returns without polling, sleeping, recursion, or starting another round.
- O1D2 policy, O1E controls, O2/O3 supervision, target Resource Provider scheduling, and checkpoint/recovery remain separate authorities.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- replay-lane inventory/selection or I1-GC exact semantics;
- queue-lane inventory/selection or C2 exact semantics;
- B2/B3 record/claim/retry schemas;
- memory formation/retrieval/mutation semantics;
- O1D2 fairness, retry delay, backoff, jitter, or pacing fields;
- O1E cancellation, stale recovery, or shutdown fields;
- O2/O3 recurring service/process behavior;
- general asynchronous Resource Provider scheduling;
- thread/process leader election or a global scheduler lock;
- durable scheduler-round persistence;
- checkpoint/recovery schema;
- exact service interval or sleep duration;
- source retirement, redirects, or router migration;
- repository-level project sequencing.

## Related architecture and transitional sources

- [Runtime Scheduler Architecture](../../architecture/runtime/scheduler.md)
- [O1A Two-Lane Scheduler Contract Handoff](../../architecture/o1a_two_lane_scheduler_contract.md)
- [O1D1 Production Scheduler Round Handoff](../../architecture/o1d1_production_scheduler_round.md)
- [O1D2 Scheduler Policy](../../architecture/o1d2_scheduler_policy.md)
- [O1E Scheduler Operational Controls](../../architecture/o1e_scheduler_operational_controls.md)
- [RelayRUN Checkpoint and Recovery Contract](../relayrun-checkpoint-and-recovery.md)
