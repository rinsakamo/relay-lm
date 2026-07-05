---
relaylm_doc_type: implementation_handoff
relaylm_authority: o2_supervised_scheduler_service_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_scheduler
relaylm_update_trigger:
  - O1E operational-controls behavior changes
  - scheduler service-loop public projection changes
  - cancellation or pacing handling changes
  - durable-memory E2 smoke dependency changes
relaylm_not_authoritative_for:
  - repository-wide current status
  - queue record mutation semantics
  - protected source body storage
  - durable Primary MEM finalization semantics
  - browser or FastAPI startup behavior
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - o3_always_on_local_scheduler.md
---
# O2 Supervised Scheduler Service

Last reviewed: 2026-07-05 JST

## Purpose

O2 adds an opt-in supervised local service loop around the existing O1E operational controls boundary. Its job is to repeatedly invoke `run_relaymem_slp_scheduler_operational_controls_once(...)`, carry the bounded O1D2 `SchedulerPolicyState` between rounds, and follow content-free pacing recommendations.

O2 exists so local operation can drain scheduler/worker work between a formation phase and a later fresh-session recall phase. It is a prerequisite capability for durable-memory E2 value smoke, but it does not implement that E2 scenario itself.

## Authority

O2 has no independent memory, queue, worker, stale-recovery, or finalization authority.

The only execution authority is:

```text
O2 service loop
  -> O1E run_relaymem_slp_scheduler_operational_controls_once
     -> O1D2 scheduler policy
        -> O1D1 one-round scheduler coordinator
           -> existing replay/queue lanes and worker/finalization gates
```

O2 reads only public, content-free fields from O1E/O1D2 results. It does not inspect queue paths, job ids, dispatch ids, lease tokens, protected source bodies, or memory content.

## Public projection

The O2 result projection is content-free and bounded. It contains only:

- schema/status/mode
- round counters
- idle and sleep counters
- last O1E/O1D2/O1D1 status strings
- cancellation/shutdown/unsafe booleans
- bounded reason ids

The result `repr(...)` also omits private nested results.

## Loop behavior

Each service iteration:

1. checks cancellation;
2. invokes O1E exactly once;
3. validates the returned object is exactly `SchedulerOperationalControlsResult`;
4. carries `policy_result.next_policy_state` into the next iteration when present;
5. stops on invalid input/config, unsafe result, unexpected failure, cancellation, shutdown, disabled mode, idle limit, or max rounds;
6. follows O1D2 pacing:
   - `run_next_round`: continue immediately;
   - `wait_before_next_round`: sleep a bounded policy delay;
   - `idle`: increment idle count and stop after the configured idle limit;
   - `stop`: complete.

Tests inject a fake sleeper, so validation does not real-sleep.

## Non-goals and boundaries

O2 does not:

- add memory mutation authority;
- directly mutate queue records;
- read or expose protected source bodies;
- expose job IDs, dispatch IDs, lease tokens, claim owners, queue paths, or memory content;
- start background threads;
- start from `create_app()`;
- turn scheduling on by default;
- implement durable-memory E2 value smoke.

## Operational usage

O2 is a Python service-loop API. O3 is the supported local process/CLI wrapper for running it from a shell.

For bounded validation, use O3 with `--max-rounds 1`. For local always-on operation, use O3 with `--always-on`.

## Validation

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_o2_supervised_scheduler_service_smoke.py
PYTHONPATH=. python scripts/relaylm_o1e_scheduler_operational_controls_smoke.py
```

## Relationship to durable-memory E2 smoke

Durable-memory E2 smoke should remain a separate slice. O2 only supplies the supervised draining capability needed before that E2 scenario can become meaningful evidence.
