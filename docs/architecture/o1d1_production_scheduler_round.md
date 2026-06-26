---
relaylm_doc_type: implementation_handoff
relaylm_authority: o1d1_production_scheduler_round
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_related_authority:
  - docs/architecture/o1a_two_lane_scheduler_contract.md
  - docs/architecture/o1b_sealed_i1g_replay_lane.md
  - docs/architecture/o1c_eligible_b2_queue_lane.md
  - docs/architecture/o0_local_one_job_runner.md
  - docs/architecture/wave2_cross_slice_convergence_audit.md
---
# O1D1 Accepted Scheduler Gates and One Production Round

## Status

O1D1 implements one accepted, server-configured, single-threaded production scheduler round. It does not implement a scheduler loop, polling, sleep, fairness, retry delay, stale recovery, shutdown, daemonization, or service supervision.

```text
one exact RelayLMConfig
  -> accepted SchedulerGates
  -> reject disabled / invalid / unsupported state before lane invocation
  -> at most one O1B replay-lane call
  -> at most one O1C queue-lane call
  -> O1A aggregate_scheduler_round(...)
  -> content-free projection validation
  -> return without sleep
```

The production entry point is:

```python
run_relaymem_slp_scheduler_round_once(
    *,
    config: RelayLMConfig,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None = None,
    now: datetime | None = None,
    fault_injector: Callable[[str], None] | None = None,
) -> SchedulerRoundResult
```

`fault_injector` is an internal test seam. It is not accepted from config, CLI, browser, or API input.

## Accepted configuration

O1D1 adds these exact `StrictBool` fields to `RelayLMConfig`:

```yaml
relaymem_local_scheduler_enabled: false
relaymem_local_scheduler_dry_run_only: true
relaymem_local_scheduler_apply_enabled: false
relaymem_local_scheduler_replay_lane_enabled: true
relaymem_local_scheduler_queue_lane_enabled: true
```

Only three mode triples are accepted:

```text
disabled: enabled=false, dry_run_only=true,  apply_enabled=false
dry-run:  enabled=true,  dry_run_only=true,  apply_enabled=false
apply:    enabled=true,  dry_run_only=false, apply_enabled=true
```

When the scheduler is enabled, at least one lane must be enabled. Integer, string, and null coercion are rejected. Defaults remain disabled and dry-run-first.

The scheduler gate is only an upper authority. Scheduler apply does not elevate I1-G durable-finalization gates or O0/C2/B3 local-worker gates. O1B and O1C continue to intersect scheduler mode with their existing lower authorities.

## Fixed invocation order and bounds

The v0 order is exact and sequential:

```text
replay returns
  -> queue starts
  -> aggregate
  -> validate projection
  -> return
```

A valid enabled round invokes each enabled lane at most once. Therefore:

```text
I1-GC delegation <= 1
C2 delegation    <= 1
total work units <= 2
```

The coordinator does not recurse, rescan in a loop, retry internally, or start a second round. `run_next_round` is only a returned disposition for an external future caller.

## Preserved authorities

O1A remains pure. `relaymem_slp_scheduler_contract.py` gains no config, filesystem, clock, sleep, or lane invocation dependency.

O1B remains sole owner of bounded I1-G inventory, deterministic sealed-pending selection, canonical reread, and at most one I1-GC delegation. The coordinator does not inspect locators, completion markers, or nested replay results.

O1C remains sole owner of bounded queue inventory, eligibility, deterministic selection, canonical reread, server-owned character/store resolution, and at most one C2 delegation. The coordinator does not construct C2 requests or inspect job, dispatch, claim, locator, root, or character identity.

B3/C2/I1-GC/C1-5 retain mutation, claim, lease, replay-fence, source, and convergence authority. O1D1 adds no global scheduler lock, cross-root lock, durable round journal, or leader election.

## Same-round replay-to-queue rule

A completed replay may publish a new B2 record that the same round's queue lane can observe. The only supported path is:

```text
O1B -> I1-GC convergence
  -> O1C independently opens and inventories the configured queue root
  -> O1C canonical selected-record reread
  -> existing C2
```

The coordinator passes no replay result, locator, job/dispatch identity, candidate object, or priority hint into O1C. Selection remains normal O1C lexicographic/current eligibility authority, so same-round selection of a newly published record is possible but not guaranteed.

## Failure and fault behavior

Classified `LaneOutcome` values remain lane-local and are aggregated by O1A. A replay `busy`, `candidate_changed`, `isolated`, or bounded failure does not suppress the independent queue opportunity. A later queue failure does not roll back completed replay work.

An unexpected exception, wrong lane result type, unknown lane status, aggregation failure, or projection invariant failure is round-fatal. The coordinator returns one fixed content-free `unexpected_failure` result, stops the round, and does not include raw exception text or private delegate state.

Internal fault seams are:

```text
after_gate_validation_before_replay
after_replay_before_queue
after_queue_before_aggregation
after_aggregation_before_projection
after_projection_before_return
```

A fault after replay preserves the bounded replay outcome. A fault before queue records no queue invocation. O1D1 performs no rollback and creates no durable scheduler-round identity; restart safety remains delegated to I1-GC, B3, and C2 idempotency/current-claim checks.

## Time handling

`now` is optional and, when supplied, must be one exact timezone-aware `datetime`. It is passed only to O1C for one bounded eligibility snapshot.

O1D1 does not expose exact retry timestamps, convert hints to delay, calculate backoff or jitter, or sleep. `future_work_hint_present` remains the only public bounded indication that later work may exist.

## Projection and leakage boundary

O1D1 returns the existing schemas:

```text
relaylm.local_scheduler_round_result.v0
relaylm.local_scheduler_round_projection.v0
relaylm.local_scheduler_lane_result.v0
```

Before return, the coordinator validates exact projection keys, schema, enums, booleans, work-unit bounds, reason-ID count/format, and equality with the bounded `SchedulerRoundResult` fields.

The projection and result representation exclude content, protected source, namespace/character values, run/session/turn/job/dispatch/locator identity, filenames, roots/paths, claim/lease details, exact timestamps, digests, raw exceptions, and nested I1-GC/C2 results.

## Concurrency

O1D1 is single-threaded within one round. Multiple processes or threads may invoke separate rounds concurrently. Safety remains delegated to existing nonblocking replay fences, secure reread, queue advisory locking, B3 claim/CAS, and C2 exact current-claim validation.

O0 remains the explicit one-job CLI authority. O1D1 adds no polling CLI and does not change `relaylm-worker --once` semantics.

## Permanent evidence

O1D1 adds:

```text
scripts/relaylm_o1d1_config_smoke.py
scripts/relaylm_o1d1_production_round_smoke.py
scripts/relaylm_o1d1_production_round_fault_smoke.py
scripts/relaylm_o1d1_production_round_concurrency_smoke.py
scripts/relaylm_o1d1_production_round_security_smoke.py
.github/workflows/o1d1-production-scheduler-round.yml
```

The workflow also runs O1A/O1B/O1C, Wave 2, O0, I1-GC/I1-GD, B2/B3, C2, config loading, completion-report, compile, and documentation-link regressions.

## Deferred scope

The following remain unimplemented and owned by later phases:

```text
O1D2: fairness, retry-time policy, backoff, jitter, pacing
O1E: stale recovery, cancellation, graceful shutdown, signal handling
O1F: operational/soak validation
O2/O3: supervised and broader automatic operation
```

O1D1 completion must not be described as an always-on scheduler, polling service, fairness completion, or automatic production operation completion.
