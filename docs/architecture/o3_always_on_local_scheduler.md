---
relaylm_doc_type: implementation_handoff
relaylm_authority: o3_always_on_local_scheduler_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_scheduler
relaylm_update_trigger:
  - local scheduler CLI options change
  - O2 service-loop settings or projection changes
  - signal cancellation behavior changes
  - app startup behavior changes
relaylm_not_authoritative_for:
  - repository-wide current status
  - queue record mutation semantics
  - protected source body storage
  - durable Primary MEM finalization semantics
  - SOUL Lab or browser authority
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - o2_supervised_scheduler_service.md
---
# O3 Always-On Local Scheduler

Last reviewed: 2026-07-05 JST

## Purpose

O3 adds an opt-in local process wrapper for O2. It provides a CLI that loads RelayLM config, installs SIGINT/SIGTERM cancellation through the existing `SchedulerSignalCancellationAdapter`, runs the O2 supervised service loop, prints one JSON projection, and exits with a bounded status code.

O3 is local operation support. It is not app-embedded and is not browser authority.

## Authority

O3 delegates all scheduling work to O2, and O2 delegates each round to O1E. O3 does not add worker, queue, stale-recovery, memory formation, or durable finalization authority.

Existing gates remain authoritative, including:

```text
relaymem_local_scheduler_operational_controls_enabled
relaymem_local_scheduler_operational_controls_dry_run_only
relaymem_local_scheduler_operational_controls_apply_enabled
relaymem_local_scheduler_stale_recovery_enabled
relaymem_local_scheduler_stale_recovery_dry_run_only
relaymem_local_scheduler_stale_recovery_apply_enabled
```

Lower-level scheduler, worker, and durable-finalization gates continue to decide whether actual work may run.

## CLI usage

Bounded validation:

```bash
PYTHONPATH=. python scripts/relaylm_o3_always_on_local_scheduler.py --config config.yaml --max-rounds 1
```

Always-on local operation:

```bash
PYTHONPATH=. python scripts/relaylm_o3_always_on_local_scheduler.py --config config.yaml --always-on
```

The CLI defaults to bounded validation with `--max-rounds 1`. `--always-on` removes the max-rounds cap but still stops on O2 cancellation, shutdown, unsafe state, invalid config, disabled O1E mode, or configured idle limit.

## Output and exit codes

O3 prints JSON only: `result.projection()` for successful O2 execution, or an O2-shaped content-free projection for config/settings load failures.

Exit behavior:

- `0`: disabled, completed, idle, cancelled, or shutdown-requested;
- non-zero: invalid input/config, unsafe state, or unexpected failure.

No job ids, dispatch ids, lease tokens, claim owners, queue paths, protected source bodies, memory content, or raw config paths are printed.

## Non-goals and boundaries

O3 does not:

- start automatically from FastAPI `create_app()`;
- run in the browser or SOUL Lab UI;
- turn scheduler gates on by default;
- directly mutate queue records;
- read protected source bodies;
- implement durable-memory E2 value smoke;
- replace O1E/O1D2/O1D1 authority.

## Validation

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_o3_always_on_local_scheduler_smoke.py
PYTHONPATH=. python scripts/relaylm_o2_supervised_scheduler_service_smoke.py
```

## Relationship to durable-memory E2 smoke

O3 gives local operators an always-on process wrapper capable of draining eligible work after O1E gates allow it. The later durable-memory E2 scenario should consume this capability, but should be implemented and validated in a separate PR.
