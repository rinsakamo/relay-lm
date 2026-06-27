---
relaylm_doc_type: runbook
relaylm_authority: o1_manual_one_round_pre_o2_o3_operations
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/o0_local_one_job_runner.md
  - ../architecture/o1d1_production_scheduler_round.md
  - ../architecture/wave3_cross_slice_convergence_audit.md
relaylm_not_authoritative_for:
  - scheduler policy
  - service supervision
  - always-on operation
---
# O1 manual one-round operations runbook

## Status

This runbook is for the post-Wave-3 / pre-O2-O3 boundary. O1D1 can execute one accepted-gate production round and return without sleep. No polling loop, daemon, service supervision, fairness/backoff policy, or always-on operation is complete.

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

## Stop conditions

Stop and inspect the dedicated authority when any result reports unsafe state, unknown status, projection invariant failure, corrupt evidence, root validation failure, ambiguous character/scope resolution, or leaked private values.
