---
relaylm_doc_type: implementation_handoff
relaylm_authority: o1d2_scheduler_policy
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_related_authority:
  - docs/architecture/o1a_two_lane_scheduler_contract.md
  - docs/architecture/o1b_sealed_i1g_replay_lane.md
  - docs/architecture/o1c_eligible_b2_queue_lane.md
  - docs/architecture/o1d1_production_scheduler_round.md
  - docs/architecture/wave3_cross_slice_convergence_audit.md
---
# O1D2 Deterministic Scheduler Policy

## Status and scope

O1D2 implements a content-free policy boundary around the existing O1D1 one-round scheduler coordinator. It adds deterministic policy state, fairness/starvation hints, retry-window rounding, bounded backoff/jitter, and pacing recommendations for an external caller.

O1D2 does not implement a polling loop, sleep, recurring automatic scheduling, stale-claim recovery, cancellation, graceful shutdown, signal handling, daemonization, service supervision, global scheduler lock, durable scheduler journal, lane discovery, I1-GC replay semantics, C2/B3 worker semantics, or always-on local operation.

```text
one caller invocation
  -> O1D2 policy gates
  -> exactly one O1D1 round
  -> O1B replay lane and/or O1C queue lane remain sole discovery/delegation owners
  -> O1A aggregation remains pure
  -> content-free policy projection
  -> return immediately without sleep
```

## Relation to O1D1

The existing O1D1 public entry point remains unchanged:

```python
run_relaymem_slp_scheduler_round_once(...)
```

O1D2 adds a wrapper entry point in `relaylm/relaymem_slp_scheduler_policy.py`:

```python
run_relaymem_slp_scheduler_round_once_with_policy(
    *,
    config: RelayLMConfig,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None = None,
    now: datetime | None = None,
    policy_state: SchedulerPolicyState | None = None,
    fault_injector: Callable[[str], None] | None = None,
) -> SchedulerPolicyRoundResult
```

The wrapper validates policy gates before lane invocation, calls O1D1 at most once, applies policy to the O1D1 result, and returns. It does not change O1D1's fixed replay-before-queue invocation order inside a round.

## Policy state model

`SchedulerPolicyState` is caller-carried and content-free. It contains only bounded counters:

```text
replay_progress_streak
queue_progress_streak
replay_idle_streak
queue_idle_streak
consecutive_contention_count
consecutive_future_retry_count
consecutive_no_work_count
```

Each counter is an exact integer from 0 through 1000000. The policy state does not include candidate identity, path, root, locator, job ID, dispatch ID, claim token, retry timestamp, character scope, protected source, memory text, or nested delegate result.

## Fairness and starvation rules

O1D2 computes `fairness_lane_preference` as a hint only:

```text
replay | queue | balanced | none
```

The hint is deterministic and based on bounded counters plus lane-kind/status classes only. It does not invert O1D1's same-round replay-before-queue order, does not call a lane more than once, and does not pass replay-private identity into the queue lane or queue-private identity into the replay lane.

Rules:

- when replay progress or queue idle exceeds the configured fairness streak limit, prefer `queue`;
- when queue progress or replay idle exceeds the configured fairness streak limit, prefer `replay`;
- when counters are active but no one lane is preferred, return `balanced`;
- with no prior state, return `none`.

## Retry-window rounding

O1C may retain a private `earliest_retry_not_before` timestamp inside its private lane state. O1D2 may inspect that private value only to round it into a public class:

```text
none | immediate | short | later | unknown
```

Raw timestamps are never returned. If no exact timezone-aware `now` and private retry timestamp are available, O1D2 returns `unknown` rather than projecting a timestamp.

## Bounded backoff, jitter, and pacing

O1D2 returns:

```text
pacing_recommendation: stop | run_next_round | wait_before_next_round | idle
next_delay_ms: int | null
```

The recommendation is a caller hint only. RelayLM does not sleep or schedule the next call.

Pacing rules:

- unsafe, invalid, or disabled state returns `stop`;
- completed work, mutation possibility, candidate-change retry, or immediate retry returns `run_next_round`;
- contention, future retry, retryable idle, or repeated no-work returns `wait_before_next_round` with bounded `next_delay_ms`;
- initial no-work returns `idle`.

Delay is bounded by `relaymem_local_scheduler_pacing_max_delay_ms`. Jitter is deterministic and uses only public abstract reason/streak inputs, never cryptographic material, private identity, timestamps, paths, or content.

## Config fields

O1D2 adds these `RelayLMConfig` fields:

```yaml
relaymem_local_scheduler_policy_enabled: false
relaymem_local_scheduler_policy_dry_run_only: true
relaymem_local_scheduler_policy_apply_enabled: false
relaymem_local_scheduler_policy_fairness_streak_limit: 3
relaymem_local_scheduler_pacing_base_delay_ms: 250
relaymem_local_scheduler_pacing_max_delay_ms: 5000
relaymem_local_scheduler_pacing_jitter_ms: 0
relaymem_local_scheduler_policy_short_retry_window_ms: 30000
relaymem_local_scheduler_policy_later_retry_window_ms: 300000
```

The policy gate triple accepts exactly disabled, dry-run, and apply mode:

```text
disabled: enabled=false, dry_run_only=true,  apply_enabled=false
dry-run:  enabled=true,  dry_run_only=true,  apply_enabled=false
apply:    enabled=true,  dry_run_only=false, apply_enabled=true
```

All policy gates are strict booleans. Numeric fields are strict bounded integers. Invalid config fails closed before O1D1/O1B/O1C lane invocation.

The existing five O1D1 scheduler booleans retain their prior meaning.

## No-sleep / no-loop / no-supervision guarantee

O1D2 contains no `time.sleep`, async sleep, timer, thread, polling loop, recurring scheduling, background task, daemon, supervisor, signal handler, or service lifecycle. The returned delay is only a recommendation to an external caller.

## Leakage boundary

O1D2 projection uses:

```text
relaylm.local_scheduler_policy_round_result.v0
relaylm.local_scheduler_policy_projection.v0
```

Public projection includes only:

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

It must not include content, protected source, namespace/character values, run/session/turn/job/dispatch/locator identity, filenames, roots/paths, claim/lease details, exact timestamps, digests, raw exceptions, or nested I1-GC/C2 results.

## Permanent evidence

O1D2 adds:

```text
relaylm/relaymem_slp_scheduler_policy.py
scripts/relaylm_o1d2_scheduler_policy_smoke.py
scripts/relaylm_o1d2_scheduler_policy_config_smoke.py
scripts/relaylm_o1d2_scheduler_policy_fault_smoke.py
scripts/relaylm_o1d2_scheduler_policy_security_smoke.py
.github/workflows/o1d2-scheduler-policy.yml
docs/mvp/wave4/o1d2_completion_report.md
```

The O1D2 workflow also runs O1D1 and O1A/O1B/O1C regressions to preserve lower boundaries.

## O1E handoff

O1E starts after O1D2 policy is stable. O1E may consume O1D2 pacing/fairness/retry-window hints but owns stale-claim operational recovery orchestration, cancellation checkpoints, graceful shutdown, and signal handling. O1E must not reinterpret O1D2 delay hints as authorization to poll, sleep, supervise, or mutate lane discovery semantics inside O1D2.
