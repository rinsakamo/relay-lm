---
relaylm_doc_type: contract
relaylm_authority: current_relaymem_slp_supervised_scheduler_service_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_scheduler
relaylm_update_trigger:
  - O2 supervised-service result/projection schema or status changes
  - O2 service settings, hard bounds, cancellation, signal, pacing, sleep, or loop semantics change
  - O2 policy-state carry-forward or lower O1E invocation semantics change
  - O2 public projection or private-result retention boundary changes
  - O3 wrapper begins to change O2 service authority rather than only invoke it
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - O1A/O1D1 scheduler round and lane semantics
  - O1D2 fairness, retry-window, pacing recommendation, backoff, or jitter semantics
  - O1E cancellation checkpoints, stale-recovery orchestration, or queue mutation authority
  - O1F validation-only semantics
  - B3 queue lifecycle, C2 worker execution, or I1-GC/I1-GD durable-finalization semantics
  - O3 CLI/process lifecycle beyond its invocation of this O2 API
  - FastAPI or browser startup behavior
  - durable-memory E2 scenario semantics
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/scheduler.md
  - ../../architecture/o2_supervised_scheduler_service.md
  - ../../architecture/o3_always_on_local_scheduler.md
  - ../../architecture/o1e_scheduler_operational_controls.md
  - ../../architecture/o1f_operational_validation.md
relaylm_related_contracts:
  - scheduler-round.md
  - scheduler-policy.md
  - scheduler-operational-controls.md
  - scheduler-operational-validation.md
  - ../relayrun-checkpoint-and-recovery.md
relaylm_verified_by:
  - ../../../scripts/relaylm_o2_supervised_scheduler_service_smoke.py
  - ../../../scripts/relaylm_o1e_scheduler_operational_controls_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM SLP local scheduler service maintainers
  - O3 process/CLI wrapper maintainers
  - durable-memory evaluation and local-operation maintainers
  - runtime, recovery, security, privacy, and observability reviewers
relaylm_authority_level: exact_contract
---
# Supervised Scheduler Service Contract

## Authority summary

This contract owns the exact current **O2 supervised local scheduler service loop** implemented by:

```text
relaylm/relaymem_slp_supervised_scheduler_service.py
```

O2 repeatedly invokes the separately owned O1E operational-control boundary, carries the bounded O1D2 `SchedulerPolicyState` between iterations, and follows the bounded public pacing recommendation returned by O1D2 through O1E.

The authority chain remains:

```text
O2 service loop
  -> O1E operational controls
     -> O1D2 scheduler policy
        -> O1D1 one-round coordinator
           -> separately owned replay/queue/worker/finalization boundaries
```

O2 has no independent queue mutation, stale-recovery, worker, memory, durable-finalization, retrieval, or source-body authority.

## Current implementation anchor

The exact current service owner is:

```text
relaylm/relaymem_slp_supervised_scheduler_service.py
```

The current implementation handoff remains:

```text
docs/architecture/o2_supervised_scheduler_service.md
```

O3 remains a separate process/CLI wrapper above this API.

This transaction does not retire or move either source.

## Current schema identifiers

The exact current O2 schema identifiers are:

```text
O2_SUPERVISED_SERVICE_RESULT_SCHEMA
  = relaylm.o2_supervised_scheduler_service_result.v0

O2_SUPERVISED_SERVICE_PROJECTION_SCHEMA
  = relaylm.o2_supervised_scheduler_service_projection.v0
```

## Current hard bounds

The exact current O2 hard bounds are:

```text
MAX_O2_REASON_IDS       = 16
MAX_O2_ROUNDS           = 1_000_000
MAX_O2_SLEEP_MS         = 60_000
MAX_O2_SLEEP_COUNT      = 1_000_000
MAX_O2_TOTAL_SLEEP_MS   = 3_600_000_000
```

Every bounded O2 reason ID must match:

```regex
^[a-z][a-z0-9_]{0,63}$
```

## Current service status vocabulary

The exact constructor-accepted O2 service statuses are:

```text
disabled
completed
idle
cancelled
shutdown_requested
unsafe_state
invalid_input
invalid_config
unexpected_failure
```

These are O2 service-loop outcomes. They do not replace O1E operational statuses, O1D2 policy statuses, O1D1 round statuses, B3 queue statuses, or worker/finalization statuses.

## Service settings object

`RelayMEMSLPSupervisedSchedulerServiceSettings` is an immutable current settings object with exactly:

```text
max_rounds
stop_after_idle_rounds
idle_sleep_ms
max_sleep_ms
install_signal_handlers
```

Current defaults are:

```text
max_rounds                 = 1
stop_after_idle_rounds     = 1
idle_sleep_ms              = 1000
max_sleep_ms               = 60000
install_signal_handlers    = false
```

`max_rounds = None` is accepted and represents no O2 round-count stop. It does not disable cancellation, idle stopping, lower stop conditions, or bounded sleep counters.

## Settings validation

When `max_rounds` is not null it must be exact `int` and satisfy:

```text
1 <= max_rounds <= 1_000_000
```

Otherwise construction raises:

```text
o2_service_max_rounds_invalid
```

The following fields must each be exact `int`:

```text
stop_after_idle_rounds
idle_sleep_ms
max_sleep_ms
```

Wrong type raises:

```text
o2_service_setting_int_required
```

The exact bounds are:

```text
1 <= stop_after_idle_rounds <= 1_000_000
0 <= idle_sleep_ms <= 60_000
0 <= max_sleep_ms <= 60_000
```

Bound violations raise respectively:

```text
o2_service_stop_after_idle_rounds_invalid
o2_service_idle_sleep_ms_invalid
o2_service_max_sleep_ms_invalid
```

`install_signal_handlers` must be exact `bool` or construction raises:

```text
o2_service_install_signal_handlers_bool_required
```

Boolean values do not satisfy the exact-int settings requirements.

## Service result shape

`RelayMEMSLPSupervisedSchedulerServiceResult` is immutable and content-free. It currently contains exactly:

```text
status
mode
rounds_attempted
rounds_completed
idle_rounds
slept_count
total_sleep_ms
last_operational_status
last_policy_status
last_round_status
last_pacing_recommendation
cancelled
shutdown_requested
unsafe
bounded_reason_ids
schema_version
```

The result deliberately retains no nested O1E, O1D2, O1D1, queue, worker, or durable-finalization result object.

Its schema version is fixed to:

```text
relaylm.o2_supervised_scheduler_service_result.v0
```

## Result constructor exactness

The constructor requires `status` to belong to the exact O2 service status vocabulary.

These fields must be exact `str`:

```text
mode
last_operational_status
last_policy_status
last_round_status
last_pacing_recommendation
```

Wrong type raises:

```text
o2_service_string_field_invalid
```

These fields must be exact nonnegative `int`:

```text
rounds_attempted
rounds_completed
idle_rounds
slept_count
total_sleep_ms
```

Wrong type or negative values raise:

```text
o2_service_counter_invalid
```

These fields must be exact `bool`:

```text
cancelled
shutdown_requested
unsafe
```

Wrong type raises:

```text
o2_service_bool_invalid
```

An unrecognized service status raises:

```text
o2_service_status_invalid
```

## Result repr boundary

The current repr exposes only:

```text
status
mode
rounds_attempted
rounds_completed
private_results_omitted=True
```

O2 never retains lower private results, so repr cannot expose nested queue, worker, memory, lease, protected-source, or backend state through a stored delegate result.

## Public projection

The exact current O2 public projection contains:

```text
schema_version
status
mode
rounds_attempted
rounds_completed
idle_rounds
slept_count
total_sleep_ms
last_operational_status
last_policy_status
last_round_status
last_pacing_recommendation
cancelled
shutdown_requested
unsafe
bounded_reason_ids
```

The projection schema is:

```text
relaylm.o2_supervised_scheduler_service_projection.v0
```

The projection does not include:

- queue roots or filesystem paths;
- job IDs or dispatch keys;
- claim owners or lease tokens;
- protected source bodies;
- memory content;
- exact queue or memory records;
- backend text;
- nested O1E/O1D2/O1D1 objects.

## Main service entry point

The current API is:

```text
run_relaymem_slp_supervised_scheduler_service(
    *,
    config,
    registry=None,
    settings=None,
    now=None,
    cancellation=None,
    sleeper=None,
    runner=run_relaymem_slp_scheduler_operational_controls_once,
)
```

When `settings` is null, O2 constructs the exact default settings object.

When `sleeper` is null, O2 uses `time.sleep`.

The default runner is the exact current O1E operational-control entry point.

## Direct input validation

O2 directly requires:

```text
type(config) is RelayLMConfig
registry is null OR type(registry) is RelayMEMSLPPrimaryWorkerSourceRegistry
type(exact_settings) is RelayMEMSLPSupervisedSchedulerServiceSettings
sleeper is null OR callable
runner is callable
```

Fail-closed reasons are:

```text
exact_relaylm_config_required
exact_source_registry_required
exact_o2_service_settings_required
o2_service_sleeper_invalid
o2_service_runner_invalid
```

These direct failures return:

```text
status = invalid_input
mode = invalid
unsafe = true
```

O2 does not independently validate the exact `now` shape. It passes `now` through to the O1E runner, whose exact input contract remains authoritative.

## Cancellation coercion

The current cancellation input may be:

```text
null
exact SchedulerCancellationToken
callable probe
```

A callable probe is wrapped as `SchedulerCancellationToken`.

Other non-null values fail closed with:

```text
scheduler_cancellation_probe_required
```

and return `invalid_input`, mode `invalid`, `unsafe=true`.

Cancellation probe exception behavior remains owned by `SchedulerCancellationToken` in the O1E operational-control contract.

## Optional signal-handler installation

When:

```text
settings.install_signal_handlers == true
```

O2 creates the existing O1E `SchedulerSignalCancellationAdapter`.

Its token is combined with any caller token using logical OR:

```text
caller requested OR signal adapter requested
```

O2 then creates an otherwise-identical settings object with:

```text
install_signal_handlers = false
```

and runs the loop inside:

```text
with adapter.installed():
```

O2 does not create a second signal mechanism, thread, timer, daemon, or asynchronous interrupt path.

## Service-loop state

At loop start, current internal counters are:

```text
policy_state      = None
rounds_attempted  = 0
rounds_completed  = 0
idle_rounds       = 0
slept_count       = 0
total_sleep_ms    = 0
```

Current last-status defaults are:

```text
last_mode                   = unknown
last_operational_status     = not_invoked
last_policy_status          = not_invoked
last_round_status           = not_invoked
last_pacing_recommendation  = stop
```

These are content-free local service state only.

## Pre-round cancellation

At the top of every iteration O2 checks the cancellation token before max-round handling and before invoking O1E.

If requested, O2 returns:

```text
status = cancelled
cancelled = true
reason = service_cancelled
```

The runner is not invoked after that checkpoint.

The focused O2 smoke verifies this behavior with a runner that would fail the test if called.

## Max-round stop

When `max_rounds` is not null and:

```text
rounds_attempted >= max_rounds
```

O2 returns:

```text
status = completed
reason = service_max_rounds_reached
```

No additional O1E invocation occurs.

This is an O2 service bound, not a lower queue or worker completion claim.

## One lower invocation per iteration

When not cancelled or max-round stopped, O2 increments:

```text
rounds_attempted += 1
```

then calls the configured runner exactly once with:

```text
config
registry
now
policy_state
cancellation = token
```

The default runner is O1E.

O2 does not call replay, queue, worker, stale-recovery, or durable-finalization APIs directly.

## Runner exception handling

If the runner raises, O2 returns:

```text
status = unexpected_failure
unsafe = true
last_operational_status = unexpected_failure
reason = service_runner_failed
```

O2 does not retry the runner internally after the exception.

## Exact lower-result requirement

The runner must return exact:

```text
SchedulerOperationalControlsResult
```

A wrong result type returns:

```text
status = unexpected_failure
unsafe = true
last_operational_status = unexpected_failure
reason = exact_scheduler_operational_result_required
```

The focused smoke explicitly covers a runner returning a generic object.

## Completed lower invocation bookkeeping

After an exact O1E result, O2 increments:

```text
rounds_completed += 1
```

and records:

```text
last_mode = operational.mode
last_operational_status = operational.status
```

The counter means a structurally valid O1E result returned. It does not mean memory or queue mutation occurred.

## O1D2 policy-state carry-forward

When O1E contains a non-null scheduler policy result, O2 reads only its bounded public/status-level values and next state:

```text
policy.status
policy.projection().round_status
policy.pacing_recommendation
policy.next_policy_state
```

O2 then sets:

```text
policy_state = policy.next_policy_state
```

for the next O1E invocation.

When there is no policy result, O2 resets the public summary to:

```text
last_policy_status = not_invoked
last_round_status = not_invoked
last_pacing_recommendation = stop
```

O2 does not reinterpret the internals of `SchedulerPolicyState`.

The focused smoke verifies that a next policy state returned from one round is supplied to the next runner invocation.

## Unsafe lower result

If:

```text
operational.unsafe == true
```

O2 stops immediately with:

```text
status = unsafe_state
unsafe = true
```

Reasons merge the lower O1E bounded reasons with:

```text
service_operational_unsafe
```

O2 does not continue, sleep, or attempt another round after a lower unsafe result.

## Disabled lower result

If:

```text
operational.status == disabled
```

O2 returns:

```text
status = disabled
reason includes service_disabled
```

The lower O1E reasons are preserved only through bounded reason merging.

Default-off RelayLM configuration therefore keeps the O2 service non-operational unless lower scheduler gates are explicitly enabled.

## Lower invalid-input result

If:

```text
operational.status == invalid_input
```

O2 returns:

```text
status = invalid_input
unsafe = true
reason includes service_invalid_input
```

No further round is attempted.

## Lower invalid-config result

If:

```text
operational.status == invalid_config
```

O2 returns:

```text
status = invalid_config
reason includes service_invalid_config
```

No further round is attempted.

The current O2 result does not forcibly set `unsafe=true` for this branch unless lower behavior already required it; invalid configuration is a terminal service outcome rather than permission to continue.

## Lower unexpected failure

If:

```text
operational.status == unexpected_failure
```

O2 returns:

```text
status = unexpected_failure
unsafe = true
reason includes service_unexpected_failure
```

No retry is attempted by O2.

## Lower shutdown propagation

If either:

```text
operational.shutdown_requested == true
operational.status == shutdown_requested
```

O2 returns:

```text
status = shutdown_requested
shutdown_requested = true
reason includes service_shutdown_requested
```

O2 does not begin another round.

## Lower cancellation propagation

If either:

```text
operational.cancelled == true
operational.status starts with cancelled_
```

O2 returns:

```text
status = cancelled
cancelled = true
reason includes service_cancelled
```

The specific lower O1E cancellation checkpoint remains visible only through `last_operational_status` and the bounded lower reasons.

## Post-round cancellation checkpoint

After lower status handling and before pacing action, O2 checks its cancellation token again.

If cancellation is then requested, O2 returns:

```text
status = cancelled
cancelled = true
reason = service_cancelled_after_round
```

The focused smoke verifies a token becoming true after exactly one runner invocation.

## `run_next_round` pacing

When the current O1D2 pacing recommendation is:

```text
run_next_round
```

O2 sets:

```text
idle_rounds = 0
```

and immediately begins the next service iteration without sleeping.

This does not create additional same-round lane calls. Each new iteration still delegates through a fresh O1E invocation.

## `wait_before_next_round` pacing

When the recommendation is:

```text
wait_before_next_round
```

O2 resets:

```text
idle_rounds = 0
```

and chooses a delay.

The current delay is:

```text
0
```

unless the policy exists and `type(policy.next_delay_ms) is int`.

When an exact integer delay exists:

```text
delay_ms = min(policy.next_delay_ms, settings.max_sleep_ms)
```

The delay then passes through the O2 `_sleep(...)` hard bound before the next iteration.

The focused smoke verifies a 250 ms policy delay becomes one injected sleeper call with `0.25` seconds and updates O2 sleep counters.

## `idle` pacing

When the recommendation is:

```text
idle
```

O2 increments:

```text
idle_rounds = min(idle_rounds + 1, 1_000_000)
```

If:

```text
idle_rounds >= settings.stop_after_idle_rounds
```

O2 returns:

```text
status = idle
reason = service_idle_limit_reached
```

without sleeping again.

Otherwise it sleeps for:

```text
min(settings.idle_sleep_ms, settings.max_sleep_ms)
```

then continues.

The focused smoke verifies a two-idle-round setting sleeps exactly once between the two rounds.

## `stop` and other pacing values

Any pacing path not handled as:

```text
run_next_round
wait_before_next_round
idle
```

falls through to:

```text
status = completed
reason = service_completed
```

Under the exact current O1D2 contract the remaining normal pacing recommendation is `stop`.

O2 does not reinterpret why O1D2 returned stop.

## Sleep helper

The O2 `_sleep(...)` helper clamps each requested delay to:

```text
0 <= bounded_delay_ms <= 60_000
```

and invokes the sleeper with seconds:

```text
bounded_delay_ms / 1000.0
```

It then updates:

```text
slept_count
  <= 1_000_000

total_sleep_ms
  <= 3_600_000_000
```

Counters saturate at their hard bounds.

The injected sleeper is the validation seam used by smoke tests to avoid real wall-clock delay.

## Sleep authority boundary

O2 is the first layer in this local scheduler stack that intentionally performs sleep as part of a service loop.

O1D2 only produces a delay recommendation. O1E remains one-invocation and no-sleep. O1F remains validation-only.

O2 sleep does not grant queue, worker, stale-recovery, or memory authority.

## Cancellation combination

When both a caller token and signal-adapter token exist, O2 combines them as:

```text
first.requested() OR second.requested()
```

If no caller token exists, the adapter token is used directly.

This combined token is the token supplied to every O1E invocation.

## Counter clamping on result construction

The internal O2 result factory clamps service counters before constructing the exact result:

```text
rounds_attempted <= 1_000_000
rounds_completed <= 1_000_000
idle_rounds <= 1_000_000
slept_count <= 1_000_000
total_sleep_ms <= 3_600_000_000
```

Negative values are not generated by normal O2 flow and would still fail the result constructor if supplied directly.

## Reason normalization

O2 merges lower and local reasons through one bounded normalizer.

The normalizer:

- preserves first-seen order;
- removes duplicate reason IDs;
- limits output to sixteen reasons;
- replaces invalid values with `o2_service_reason_invalid`;
- inserts `o2_service_status` when normalization would otherwise yield no output.

## CLI pre-service projection helper

The current helper:

```text
make_relaymem_slp_supervised_scheduler_service_projection(
    *,
    status,
    reason_id,
)
```

returns an O2-shaped content-free projection without starting the service loop.

It sets:

```text
mode = invalid
```

and marks `unsafe=true` exactly for these helper statuses:

```text
invalid_input
unsafe_state
unexpected_failure
```

This helper exists for O3/pre-service failure projection and does not add CLI or process authority to O2.

## Private-data non-retention invariant

O2 records only bounded statuses, booleans, counters, reason IDs, and the bounded next policy state needed for subsequent scheduling.

It does not retain or project:

```text
job_id
dispatch_idempotency_key
claim_owner
lease_token
queue_root
queue filename
protected source body
memory content
backend text
nested lower result
```

The focused smoke checks both projection and repr against private canaries and identity/path tokens.

## No direct queue or memory access

The O2 implementation does not inspect queue directories, queue records, durable-finalization records, protected-source bodies, subjective-memory pages, or retrieval artifacts.

All operational work enters through the configured O1E runner.

A test-injected runner may simulate lower outcomes, but the service contract still requires the returned object to be exact `SchedulerOperationalControlsResult`.

## Thread and startup boundary

O2 does not:

- spawn background threads;
- register itself with FastAPI `create_app()`;
- start automatically on import;
- turn lower scheduling gates on by default;
- own daemon/process supervision.

O3 remains the supported local process/CLI wrapper.

## Durable-memory E2 boundary

O2 supplies supervised draining capability that may be used by a durable-memory E2 scenario.

O2 does not own or prove the E2 scenario itself, fresh-session recall semantics, memory-value evaluation, or memory-content correctness.

## Authority preservation

O2 preserves the exact lower ownership chain:

```text
O1A/O1D1
  one scheduler round and lane/result semantics

O1D2
  fairness, retry-window, pacing recommendation, backoff, jitter

O1E
  cancellation checkpoints, stale-recovery orchestration, one operational invocation

O1F
  validation-only hardening

B3
  queue claim/lease/retry/stale-recovery/terminal transitions

C2
  queued worker execution

I1-GC / I1-GD
  durable-finalization replay/completion/retention/cleanup
```

O2 decides only whether and when to invoke the lower O1E boundary again.

## Fail-closed invariants

The exact current O2 fail-closed rules include:

1. malformed direct inputs fail before service-loop execution;
2. malformed cancellation input fails before the runner;
3. runner exceptions stop the service as `unexpected_failure`;
4. wrong runner result type stops the service as `unexpected_failure`;
5. lower `unsafe` stops immediately;
6. lower disabled/invalid/cancelled/shutdown/unexpected-failure states stop rather than loop;
7. cancellation before a round prevents the lower invocation;
8. cancellation after a round prevents another lower invocation;
9. sleep is bounded per call and cumulatively counted with saturation;
10. O2 never reaches around O1E to mutate queue or memory state;
11. lower private results are not retained in the O2 result;
12. default-off lower scheduler configuration produces a disabled O2 result rather than silently enabling work.

## Current focused evidence

The exact O2 contract is guarded by:

```text
scripts/relaylm_o2_supervised_scheduler_service_smoke.py
```

Current focused evidence verifies:

- default lower configuration yields O2 `disabled`;
- projection schema is exact;
- policy-state carry-forward across two rounds;
- `run_next_round` causes immediate next invocation;
- `wait_before_next_round` uses the bounded policy delay;
- idle-round stopping and injected idle sleep;
- pre-start cancellation prevents runner invocation;
- post-round cancellation stops after exactly one attempt;
- lower unsafe state maps to O2 `unsafe_state`;
- wrong runner result type maps to `unexpected_failure`;
- projection and repr omit private canaries and lower identity/path fields.

## Relationship to O3

O3 is the supported local process/CLI wrapper above O2.

O3 may construct settings, cancellation adapters, process controls, and CLI-level projections, but it must not reinterpret O2's lower scheduling authority or bypass the O2/O1E chain.

O3 exact contract remains a separate transaction.

## Relationship to permanent runtime architecture

`docs/architecture/runtime/scheduler.md` owns the stable target runtime/resource scheduling separation.

This contract owns the exact current supervised local scheduler service behavior only. The phase label O2 is historical implementation provenance, not the permanent architecture responsibility name.

## Source-retirement boundary

This contract does not retire:

```text
docs/architecture/o2_supervised_scheduler_service.md
```

It also does not retire the O2 implementation, smoke, O1A-O1F sources, or O3 source. Retirement requires a separate bounded provenance-and-consumer migration transaction.
