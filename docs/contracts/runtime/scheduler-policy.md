---
relaylm_doc_type: contract
relaylm_authority: current_relaymem_slp_scheduler_policy_fairness_retry_and_pacing_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_update_trigger:
  - SchedulerPolicyState or SchedulerPolicyRoundResult exact fields change
  - fairness, retry-window, pacing, backoff, or deterministic-jitter semantics change
  - scheduler-policy configuration gates or numeric bounds change
  - policy wrapper input/fault behavior or one-round invocation count changes
  - policy public projection schema or leakage boundary changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - O1A/O1D1 one-round scheduler gates, lane outcome schemas, or replay-before-queue order
  - replay-lane discovery, I1-GC replay, queue-lane discovery, B3 claim/retry, or C2 worker semantics
  - O1E cancellation, stale-recovery, graceful-shutdown, or signal-handling orchestration
  - O2/O3 polling loops, service supervision, daemonization, or always-on lifecycle
  - target RelayRUN resource-provider or general compute-job scheduling
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/scheduler.md
  - ../../architecture/o1d2_scheduler_policy.md
  - ../../architecture/o1d1_production_scheduler_round.md
  - ../../architecture/o1e_scheduler_operational_controls.md
relaylm_related_contracts:
  - scheduler-round.md
  - ../relayrun-checkpoint-and-recovery.md
relaylm_verified_by:
  - ../../../scripts/relaylm_o1d2_scheduler_policy_smoke.py
  - ../../../scripts/relaylm_o1d2_scheduler_policy_config_smoke.py
  - ../../../scripts/relaylm_o1d2_scheduler_policy_fault_smoke.py
  - ../../../scripts/relaylm_o1d2_scheduler_policy_security_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM SLP scheduler-policy and operations maintainers
  - external local scheduler caller/service maintainers
  - replay, queue, runtime, recovery, security, and observability reviewers
relaylm_authority_level: exact_contract
---
# Runtime Scheduler Policy Contract

## Authority summary

This contract owns the exact current **O1D2 deterministic scheduler-policy wrapper** around the separately owned one-round scheduler.

The current implementation anchor is:

```text
relaylm/relaymem_slp_scheduler_policy.py
```

The boundary is:

```text
external caller
  -> validate O1D2 policy input/config
  -> invoke O1D1 at most once
  -> advance bounded caller-carried policy counters
  -> classify fairness / retry window / pacing
  -> project content-free recommendation
  -> return immediately
```

O1D2 does not discover lane work, change the O1D1 replay-before-queue order, sleep, loop, poll, supervise a process, recover stale claims, or schedule another invocation itself.

## Relationship to the one-round contract

The separate [Runtime Scheduler Round Contract](scheduler-round.md) owns:

```text
SchedulerGates
LaneOutcome
SchedulerRoundResult
one exact O1D1 round
replay -> queue invocation order
```

This contract begins only after or around that one-round boundary.

O1D2 may inspect bounded public round/lane state and one queue-private retry-time hint for classification, but it does not replace lower replay/queue/worker authority.

## Current schema identifiers

The exact current policy schemas are:

```text
POLICY_RESULT_SCHEMA     = relaylm.local_scheduler_policy_round_result.v0
POLICY_PROJECTION_SCHEMA = relaylm.local_scheduler_policy_projection.v0
```

The exact current bounds are:

```text
MAX_POLICY_REASON_IDS = 16
MAX_POLICY_COUNTER    = 1_000_000
MAX_POLICY_DELAY_MS   = 60_000
```

Bounded policy reason IDs use:

```regex
^[a-z][a-z0-9_]{0,63}$
```

Invalid reason values normalize to:

```text
scheduler_policy_reason_invalid
```

Reason projection is de-duplicated in first-seen order and truncated at `MAX_POLICY_REASON_IDS`.

If no reason remains, the helper inserts:

```text
scheduler_policy_status
```

## Policy status vocabulary

The exact current `PolicyStatus` values are:

```text
policy_disabled
invalid_input
invalid_configuration
policy_evaluated
policy_blocked
round_unsafe
unexpected_failure
```

No polling, cancellation, service-loop, shutdown, or daemon status is implied by this vocabulary.

## Retry-window vocabulary

The exact current `RetryWindow` values are:

```text
none
immediate
short
later
unknown
```

Raw retry timestamps are never part of the public policy projection.

## Pacing recommendation vocabulary

The exact current `PacingRecommendation` values are:

```text
stop
run_next_round
wait_before_next_round
idle
```

A recommendation is only a return value for an external caller.

`run_next_round` does not recursively execute another round, and `wait_before_next_round` does not sleep.

## Fairness preference vocabulary

The exact current `FairnessLanePreference` values are:

```text
replay
queue
balanced
none
```

This is a cross-invocation hint only. It does not reorder the replay and queue lane calls inside the current O1D1 round.

## SchedulerPolicyState

`SchedulerPolicyState` is immutable caller-carried content-free state with exactly these counters:

```text
replay_progress_streak
queue_progress_streak
replay_idle_streak
queue_idle_streak
consecutive_contention_count
consecutive_future_retry_count
consecutive_no_work_count
```

Every counter defaults to zero.

Every counter must have exact `int` type and satisfy:

```text
0 <= counter <= 1_000_000
```

Boolean values are rejected because `type(value) is int` is required.

An invalid counter raises:

```text
scheduler_policy_state_counter_invalid
```

## Policy-state privacy boundary

Policy state contains counters only.

It does not contain:

```text
candidate identity
job or dispatch identity
character / namespace / session / turn identity
filesystem path or root
claim or lease token
exact retry timestamp
protected source or memory text
digest
private delegate body
```

`projection()` returns only the seven named counters.

## Counter advancement

`SchedulerPolicyState.advance(result)` requires exact type:

```text
type(result) is SchedulerRoundResult
```

otherwise it raises:

```text
exact_scheduler_round_result_required
```

Each streak counter increments by one, capped at `MAX_POLICY_COUNTER`, when its current condition is true; otherwise it resets to zero.

## Lane progress classification

A lane is considered progressed only when:

```text
type(lane) is LaneOutcome
AND
(
  lane.mutation_may_have_occurred
  OR lane.status in current progress statuses
)
```

The policy module's exact progress statuses are:

```text
completed
already_complete
dry_run_ready
executed
retry_released
terminal
```

## Lane idle classification

A lane is considered idle only when:

```text
type(lane) is LaneOutcome
AND lane.attempted
AND not lane_progressed
AND (
  lane.no_immediate_work
  OR lane.status in current no-work statuses
)
```

The current no-work status set is:

```text
no_eligible_work
future_retry_only
busy
not_replayable
cleanup_required
dependency_unavailable
failed
unsafe_state
isolated
```

These classifications are policy counter inputs only and do not redefine the lane contracts themselves.

## Contention counter

`consecutive_contention_count` advances when either exact lane outcome satisfies:

```text
lane.contention_observed
OR lane.status == busy
```

Otherwise it resets to zero.

## Future-retry counter

`consecutive_future_retry_count` advances exactly when:

```text
round_result.future_work_hint_present == true
```

Otherwise it resets to zero.

It does not store the future retry timestamp.

## No-work counter

`consecutive_no_work_count` advances only when:

```text
at least one exact LaneOutcome exists
AND replay did not progress
AND queue did not progress
AND every existing lane satisfies:
  lane.no_immediate_work
  OR lane.status in the policy no-work set
```

Otherwise it resets to zero.

## SchedulerPolicyRoundResult shape

`SchedulerPolicyRoundResult` currently contains:

```text
status
round_result
policy_state
next_policy_state
pacing_recommendation
next_delay_ms
retry_window
fairness_lane_preference
unsafe
bounded_reason_ids
schema_version
```

`schema_version` is fixed to:

```text
relaylm.local_scheduler_policy_round_result.v0
```

`round_result` is excluded from repr/equality and from the public policy projection.

## Exact result validation

The current constructor requires:

- `status` in the exact current status vocabulary;
- `round_result` either null or exact `SchedulerRoundResult`;
- exact `SchedulerPolicyState` for current and next state;
- pacing, retry-window, and fairness values in their exact vocabularies;
- `unsafe` exact boolean;
- `next_delay_ms`, when present, exact integer in `[0, 60_000]`;
- bounded/sanitized reason IDs.

A delay may exist only when:

```text
pacing_recommendation == wait_before_next_round
```

Otherwise construction raises:

```text
scheduler_policy_delay_requires_wait
```

## Public policy projection

`SchedulerPolicyRoundResult.projection()` returns exactly the public responsibility shape:

```text
schema_version
status
round_status
pacing_recommendation
next_delay_ms
retry_window
fairness_lane_preference
unsafe
bounded_reason_ids
policy_state
```

The projection schema is:

```text
relaylm.local_scheduler_policy_projection.v0
```

`round_status` is the lower `SchedulerRoundResult.status` when a round exists, otherwise:

```text
not_invoked
```

`policy_state` is the projection of **next_policy_state**, not the pre-round state.

The nested lower round/lane objects are not returned.

## Wrapper entry point

The current wrapper is:

```text
run_relaymem_slp_scheduler_round_once_with_policy(
    *,
    config,
    registry=None,
    now=None,
    policy_state=None,
    fault_injector=None,
)
```

It invokes O1D1 at most once and returns immediately.

## Wrapper exact input types

Current fail-closed checks are:

```text
type(config) is RelayLMConfig
registry is null OR type(registry) is RelayMEMSLPPrimaryWorkerSourceRegistry
now is null OR valid timezone-aware exact datetime
policy_state is null OR type(policy_state) is SchedulerPolicyState
fault_injector is null OR callable
```

Invalid inputs return `invalid_input` without entering the lower round.

Current bounded reasons include:

```text
exact_relaylm_config_required
exact_source_registry_required
scheduler_policy_now_invalid
exact_scheduler_policy_state_required
scheduler_policy_fault_injector_invalid
```

Invalid-input helper results are marked `unsafe=true`.

## Time input validity

A current `now` value is valid only when:

```text
type(now) is datetime
AND now.tzinfo is not None
AND now.utcoffset() is not None
```

Naive datetimes are rejected.

The same timezone-awareness rule is used before a private retry timestamp can contribute to retry-window classification.

## Policy config gate fields

The exact current policy gate fields are:

```text
relaymem_local_scheduler_policy_enabled
relaymem_local_scheduler_policy_dry_run_only
relaymem_local_scheduler_policy_apply_enabled
```

Each must be exact boolean.

If any is not exact `bool`, validation returns:

```text
scheduler_policy_gate_must_be_bool
```

## Accepted policy gate triples

The current accepted triples are exactly:

```text
(false, true,  false) -> disabled
(true,  true,  false) -> dry_run
(true,  false, true)  -> apply
```

Anything else returns:

```text
invalid_scheduler_policy_gate_combination
```

These gates wrap the lower scheduler gate. They do not elevate lower lane or mutation authority.

## Numeric policy fields and bounds

The exact current numeric fields and accepted inclusive bounds are:

```text
relaymem_local_scheduler_policy_fairness_streak_limit
  1 .. 100

relaymem_local_scheduler_pacing_base_delay_ms
  0 .. 60_000

relaymem_local_scheduler_pacing_max_delay_ms
  0 .. 60_000

relaymem_local_scheduler_pacing_jitter_ms
  0 .. 60_000

relaymem_local_scheduler_policy_short_retry_window_ms
  1 .. 3_600_000

relaymem_local_scheduler_policy_later_retry_window_ms
  1 .. 86_400_000
```

Each must have exact `int` type. A boolean is not accepted as an integer.

Any per-field bounds failure returns:

```text
scheduler_policy_numeric_bound_invalid
```

## Cross-field config constraints

Current validation also requires:

```text
base_delay_ms <= max_delay_ms
jitter_ms <= max_delay_ms
short_retry_window_ms <= later_retry_window_ms
```

Violations return respectively:

```text
scheduler_policy_base_delay_exceeds_max
scheduler_policy_jitter_exceeds_max
scheduler_policy_retry_windows_inverted
```

## Policy-disabled result

After successful validation, disabled policy mode returns without invoking O1D1:

```text
status = policy_disabled
pacing_recommendation = stop
retry_window = none
fairness_lane_preference = none
next_policy_state = current state
unsafe = false
bounded reason includes scheduler_policy_disabled
```

## One-round invocation invariant

For enabled dry-run or apply policy mode, the wrapper imports and invokes:

```text
run_relaymem_slp_scheduler_round_once(...)
```

at most once.

It passes through:

```text
config
registry
now
fault_injector
```

O1D2 does not invoke replay or queue lane functions directly.

O1D1 remains the same-round lane owner.

## Lower-round failure handling

If O1D1 raises, O1D2 returns:

```text
status = unexpected_failure
reason = scheduler_policy_round_failed
unsafe = true
```

If O1D1 returns a non-exact `SchedulerRoundResult`, O1D2 returns:

```text
status = unexpected_failure
reason = scheduler_policy_round_result_invalid
unsafe = true
```

No second round or alternate lane path is attempted.

## Policy fault seams

The current wrapper exposes these bounded fault-injection seams:

```text
after_policy_validation_before_round
after_round_before_policy
after_policy_before_return
```

An exception at those seams is converted into bounded failure reasons:

```text
after_policy_validation_before_round
  -> scheduler_policy_fault_before_round

after_round_before_policy
  -> scheduler_policy_fault_before_projection

after_policy_before_return
  -> scheduler_policy_fault_before_return
```

Each maps to `unexpected_failure` and `unsafe=true`.

Fault injection is test/validation behavior, not a runtime retry mechanism.

## Policy application status mapping

`apply_scheduler_round_policy(...)` advances state, classifies retry/fairness/pacing, then maps the lower round to policy status:

```text
round_result.unsafe == true
  -> round_unsafe

round status in:
  disabled
  invalid_configuration
  invalid_input
  blocked
  -> policy_blocked

otherwise
  -> policy_evaluated
```

The result `unsafe` field mirrors `bool(round_result.unsafe)` in the normal policy-application path.

## Retry-window classification

Retry-window classification first checks:

```text
round_result.future_work_hint_present
```

If false:

```text
retry_window = none
```

If true but the queue lane is missing or its status is not `future_retry_only`:

```text
retry_window = unknown
```

## Private retry-time inspection

For queue `future_retry_only`, O1D2 reads only this private delegate attribute:

```text
earliest_retry_not_before
```

The value contributes only if it is an exact timezone-aware `datetime` and the caller supplied a valid timezone-aware `now`.

Otherwise:

```text
retry_window = unknown
```

The timestamp itself is never projected.

## Retry-window thresholds

Current delta classification is:

```text
delta_ms <= 0
  -> immediate

0 < delta_ms <= relaymem_local_scheduler_policy_short_retry_window_ms
  -> short

delta_ms > short_retry_window_ms
  -> later
```

The configured `later_retry_window_ms` participates in config validation and ordering but the current classifier does **not** introduce another public class or upper cutoff beyond `later`.

This is the exact current behavior and must not be documented as if retries beyond the configured later window become a separate state.

## Fairness rule

Fairness is computed from the **next** advanced state.

Let:

```text
limit = relaymem_local_scheduler_policy_fairness_streak_limit
```

Current priority order is:

```text
replay_progress_streak >= limit
AND queue_progress_streak < limit
  -> queue

queue_progress_streak >= limit
AND replay_progress_streak < limit
  -> replay

replay_idle_streak >= limit
AND queue_idle_streak < limit
  -> queue

queue_idle_streak >= limit
AND replay_idle_streak < limit
  -> replay

any policy-state counter nonzero
  -> balanced

otherwise
  -> none
```

The output does not cause O1D2 to call the preferred lane or to change O1D1 order.

## Pacing priority

Current pacing uses this exact priority order:

```text
lower round disabled / invalid_input / invalid_configuration
  -> stop
  -> reason round_not_runnable

lower round unsafe
  -> stop
  -> reason round_unsafe

round_result.immediate_next_round_recommended
  -> run_next_round
  -> reason round_progress

retry_window == immediate
  -> run_next_round
  -> reason retry_window_immediate

consecutive_contention_count > 0
  -> wait_before_next_round
  -> bounded contention delay
  -> reason contention_pacing

retry_window in {short, later, unknown}
  -> wait_before_next_round
  -> bounded future-retry delay
  -> reason future_retry_pacing

round_result.retryable
  -> wait_before_next_round
  -> one-streak bounded delay
  -> reason retryable_idle_pacing

consecutive_no_work_count >= 2
  -> wait_before_next_round
  -> bounded no-work delay
  -> reason no_work_pacing

otherwise
  -> idle
  -> no delay
  -> reason no_immediate_work
```

A lower round status `blocked` affects policy status mapping but is not in the first pacing stop-status set; pacing therefore remains determined by the later predicates for that exact round. The public result still carries `status=policy_blocked`.

## Exponential delay bound

Current delay construction uses:

```text
base = relaymem_local_scheduler_pacing_base_delay_ms
max_delay = relaymem_local_scheduler_pacing_max_delay_ms
jitter_max = relaymem_local_scheduler_pacing_jitter_ms
bounded_streak = min(max(1, streak), 7)
raw = min(max_delay, base * 2 ** (bounded_streak - 1))
delay = min(max_delay, raw + deterministic_jitter)
```

The exponent never uses a streak greater than seven.

The returned delay can therefore never exceed the configured max delay or the module hard bound of 60,000 ms.

## Deterministic jitter

If configured max jitter is zero or negative, current jitter is zero.

Otherwise:

```text
seed = streak * 131 + sum(ord(char) for char in reason)
jitter = seed % (max_jitter_ms + 1)
```

Current jitter inputs are only the bounded streak and one internal abstract reason class such as:

```text
contention
future_retry
retryable_idle
no_work
```

No candidate ID, job ID, token, path, digest, raw timestamp, secret, or content participates in jitter.

The deterministic arithmetic is pacing repeatability, not cryptographic randomness.

## No-sleep / no-loop invariant

The policy module does not own or perform:

```text
time.sleep
async sleep
timer scheduling
polling loop
recurring automatic invocation
background thread/task
daemonization
service supervision
signal handling
global scheduler lock
durable scheduler journal
```

`next_delay_ms` is only a caller recommendation.

An external service may consume it under a separate O1E/O2/O3 operational contract.

## Leakage boundary

The public policy projection must not include:

```text
memory or protected-source content
character / namespace / session / turn identifiers
job / dispatch / candidate / locator identifiers
filenames, roots, or paths
claim / lease / token details
exact retry timestamps
digests
raw exceptions
nested I1-GC, B3, C2, or lane private results
```

It may include only bounded scheduler status, abstract reasons, delay integer/null, retry class, fairness class, unsafe boolean, lower round status, and bounded counters.

## Failure direction

Current failures close toward no additional scheduling action:

```text
invalid input
  -> invalid_input
  -> stop
  -> no lower round

invalid config
  -> invalid_configuration
  -> stop
  -> no lower round

policy disabled
  -> policy_disabled
  -> stop
  -> no lower round

fault before round
  -> unexpected_failure
  -> stop
  -> no lower round

round exception / invalid result
  -> unexpected_failure
  -> stop
  -> no retry round

unsafe lower round
  -> round_unsafe
  -> stop
```

O1D2 never repairs a failed round by discovering alternate work itself.

## Stable invariants

- O1D2 wraps at most one O1D1 round per caller invocation.
- O1D2 never changes O1D1 replay-before-queue order.
- Policy state is seven bounded content-free counters only.
- All state counters are exact integers and saturate at 1,000,000.
- Policy gate booleans and numeric config fields are strict exact types.
- Only disabled, dry-run, and apply policy gate triples are accepted.
- Fairness output is a hint and never a same-round lane reorder.
- Retry timestamps are classified but never projected.
- `later_retry_window_ms` validates configuration ordering; current retry classification uses `later` for every positive delta above the short threshold.
- Backoff is bounded exponential with streak capped at seven.
- Jitter is deterministic from abstract policy inputs only.
- `next_delay_ms` exists only with `wait_before_next_round`.
- O1D2 never sleeps, loops, polls, or supervises.
- Public policy output is content-free and omits nested/private lower results.
- O1E/O2/O3 remain separate operational lifecycle owners.

## Non-goals

This contract does not define:

- replay or queue candidate discovery;
- I1-GC replay semantics;
- B3 claim/retry or C2 worker semantics;
- one-round scheduler lane-result schemas already owned by `scheduler-round.md`;
- cancellation, stale recovery, shutdown, or signal orchestration;
- a polling or daemon loop;
- service supervision;
- general RelayRUN resource-provider scheduling;
- source retirement or redirect creation;
- repository-level implementation sequencing.

## Related authority

- [Runtime Scheduler Round Contract](scheduler-round.md)
- [Runtime Scheduler Architecture](../../architecture/runtime/scheduler.md)
- [O1D2 Scheduler Policy Handoff](../../architecture/o1d2_scheduler_policy.md)
