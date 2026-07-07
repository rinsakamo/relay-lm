---
relaylm_doc_type: runbook
relaylm_authority: o1_manual_one_round_compatibility_validation
relaylm_status: compatibility
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/o0_local_one_job_runner.md
  - ../architecture/o1d1_production_scheduler_round.md
  - ../architecture/o2_supervised_scheduler_service.md
  - ../architecture/o3_always_on_local_scheduler.md
  - ../architecture/wave3_cross_slice_convergence_audit.md
relaylm_not_authoritative_for:
  - scheduler policy
  - service supervision
  - always-on operation
---
# O1 manual one-round operations runbook

## Status

This runbook remains a compatibility/manual-validation guide for explicitly invoking one O1D1-style scheduler round. It describes the pre-O2/O3 one-round boundary and remains useful when validating that lower-level O1D1 behavior returns without sleeping. For current opt-in local service/always-on wrapper operation, read [O2 Supervised Scheduler Service](../architecture/o2_supervised_scheduler_service.md) and [O3 Always-On Local Scheduler](../architecture/o3_always_on_local_scheduler.md).

## Purpose

Use this only for explicit local validation where one bounded scheduler round is desired:

```text
O1D1 one round
  -> O1B sealed I1-G replay opportunity at most once
  -> O1C queue opportunity at most once
  -> O1A content-free aggregation
  -> return without sleeping
```

## Preconditions

- Review [Project Status](../PROJECT_STATUS.md) before interpreting results.
- Use server-owned configuration values only.
- Keep durable-finalization, local worker, and scheduler gates explicit.
- Do not provide roots, locator identity, job identity, dispatch identity, claim identity, namespace, or memory paths from browser input.
- Treat this as one caller invocation, not a service loop.

## Expected result shape

A manual round may return replay status, queue status, work-unit counts, bounded reason IDs, and a disposition of `stop`, `idle`, or `run_next_round`.

`run_next_round` is only a recommendation. This runbook does not start another round.

## Interpretation boundaries

- Replay completion means durable-finalization convergence through exact C1-5/B2/completion only.
- Queue terminal means C2/B3 reached a terminal result for one candidate; it does not prove semantic quality.
- Primary MEM formation is proven only by worker/M3 and later observation/retrieval evidence.
- Hidden or prepared memory exclusion is governed by I-4D, not by the scheduler.
- O1D1 does not implement fairness, retry-time policy, backoff, jitter, shutdown, supervision, or recurring automatic processing.
- O2/O3 are separate opt-in local operation layers above O1E/O1D1 and do not make this manual runbook a service loop.

## Stop conditions

Stop and inspect the dedicated authority when any result reports unsafe state, unknown status, projection invariant failure, corrupt evidence, root validation failure, ambiguous character/scope resolution, or leaked private values.
