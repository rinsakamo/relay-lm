# O1E Scheduler Operational Controls

Status: implemented in this slice.

O1E is a bounded caller-invoked operational-control layer around the existing O1D2/O1D1 scheduler stack. One invocation performs only this shape:

```text
explicit caller invocation
  -> O1E config gates
  -> cancellation checkpoint
  -> optional one stale-claim recovery orchestration through B3
  -> cancellation checkpoint
  -> at most one O1D2/O1D1 scheduler round
  -> cancellation checkpoint
  -> bounded content-free projection
  -> return
```

O1E does not poll, sleep, loop, retry internally, daemonize, supervise a service, create background workers, start timers, change O1B/O1C discovery, change I1-GC replay semantics, or change C2/B3 worker semantics outside existing B3 transition helpers.

## Authorities preserved

- O1A remains the pure scheduler contract/result/disposition authority.
- O1B remains the sealed I1-G replay-lane discovery and I1-GC delegation authority.
- O1C remains the eligible B2/B3 queue-lane discovery and C2 delegation authority.
- O1D1 remains the one-round replay-before-queue coordinator.
- O1D2 remains the deterministic fairness/retry-window/backoff/pacing policy wrapper.
- B3 remains the queue claim/lease/retry/stale-recovery/terminal lifecycle authority.

## Config gates

O1E adds one upper operational gate and one subordinate stale-recovery gate:

```yaml
relaymem_local_scheduler_operational_controls_enabled: false
relaymem_local_scheduler_operational_controls_dry_run_only: true
relaymem_local_scheduler_operational_controls_apply_enabled: false
relaymem_local_scheduler_stale_recovery_enabled: false
relaymem_local_scheduler_stale_recovery_dry_run_only: true
relaymem_local_scheduler_stale_recovery_apply_enabled: false
relaymem_local_scheduler_stale_recovery_max_scan_entries: 256
```

Accepted triples are the standard disabled / dry-run / apply shape:

| Mode | enabled | dry_run_only | apply_enabled |
|---|---:|---:|---:|
| disabled | false | true | false |
| dry-run | true | true | false |
| apply | true | false | true |

Every other combination fails closed. Stale recovery cannot be enabled while O1E is disabled, and stale-recovery apply requires O1E apply. O1E dry-run cannot wrap lower mutation-capable apply gates.

## Cancellation and shutdown boundary

O1E accepts an explicit cancellation token or probe. Cancellation is checked before start, before stale recovery, before the scheduler round, after the scheduler round, and before the final projection. Cancellation prevents starting new mutation-capable delegated work after that checkpoint. It does not try to interrupt B3/I1-GC/C2 once those authorities are already in a critical section.

`SchedulerSignalCancellationAdapter` is an opt-in adapter that maps SIGINT/SIGTERM into the same cancellation token without threads, timers, loops, or service supervision.

## Stale recovery

O1E scans at most one bounded queue root pass, selects at most one expired claimed record, and constructs an exact B3 `stale_recovery` transition request. It never rewrites queue records directly. The public O1E projection exposes only bounded statuses and booleans, not job IDs, dispatch IDs, lease tokens, owners, paths, exact timestamps, raw records, or nested delegate results.

## Remaining work

O1F remains responsible for full corruption, concurrency, saturation, restart, leakage, and operational validation. O2/O3 remain unimplemented unless a later MVP gate requires supervised or always-on operation.
