# O1F Operational Validation

Status: implemented in this slice.

O1F is a validation-only hardening phase for the caller-invoked local scheduler stack completed through [O1E Scheduler Operational Controls](o1e_scheduler_operational_controls.md). It validates the dangerous operational edges before any O2/O3 supervised or always-on operation is considered.

O1F does not add a scheduler loop, polling, sleep, daemon behavior, service supervision, a worker pool, an always-on process, a new queue lifecycle authority, or Primary MEM mutation.

## Validated boundary

The validated operational shape remains:

```text
explicit caller invocation
  -> existing O1E cancellation checkpoint
  -> optional at-most-one stale-claim recovery through B3
  -> existing O1D2/O1D1 at-most-one scheduler round
  -> bounded content-free projection
  -> return without sleep or polling
```

O1F adds validation helpers and smokes around that shape. It does not become a scheduler, worker, service, or queue owner.

## Helper

`relaylm/relaymem_slp_scheduler_operational_validation.py` provides bounded validation-only helpers:

- `validate_scheduler_operational_boundary_once(...)` wraps exactly one existing O1E invocation and validates only the public result/projection boundary.
- `validate_queue_root_inventory(...)` performs one read-only bounded queue-root inventory through existing B3 queue-storage helpers.
- `validate_durable_finalization_locator(...)` reads one sealed I1-G locator through the existing durable-finalization store reader.
- `validate_source_queue_correlation(...)` validates source/queue dispatch correlation equality without projecting IDs.
- `validate_content_free_projection(...)` and `validate_bounded_public_projection(...)` enforce content-free and bounded public output.

## Validation matrix

| Category | Evidence |
|---|---|
| Corruption | malformed queue JSON, duplicate-key JSON, noncanonical JSON, unsupported state, missing claim/lease fields, symlink, hardlink, oversized queue record, malformed sealed I1-G base, source/queue mismatch |
| Concurrency | concurrent O1E stale recovery over one expired claimed record; concurrent B3 claim attempts over one queued record |
| Saturation / boundedness | bounded scan limit, bounded reason count, repeated no-work dry-run calls that return without loop/sleep |
| Restart reread | missing sealed locator, queued record, claimed record, stale-recovered record, terminal record, malformed record all re-evaluated from disk |
| Cancellation / shutdown | explicit cancellation checkpoints and signal-adapter cancellation path remain O1E-owned and are validated through O1F public projection checks |
| Leakage | public O1F/O1E projections, smoke output, repr paths, and bounded failure reasons are checked against private canaries, IDs, claim tokens, paths, raw exceptions, protected source bodies, memory content, backend text, and nested delegate results |

## Preserved authorities

- O1A remains the pure scheduler result/disposition authority.
- O1B remains the sealed I1-G replay-lane discovery/reread and I1-GC delegation authority.
- O1C remains the eligible B2/B3 queue-lane discovery/reread and C2 delegation authority.
- O1D1 remains the one caller-invoked replay-before-queue coordinator.
- O1D2 remains the fairness, retry-window, backoff, jitter, and pacing-hint authority.
- O1E remains the stale-recovery, cancellation, and shutdown orchestration boundary.
- B3 remains the queue claim, lease, retry, stale-recovery, and terminal transition authority.
- I1-GC/I1-GD remain the durable-finalization replay, completion, retention, and cleanup authorities.
- C2 remains the one queued-job worker integration authority.

## Public projection contract

O1F public projections include only:

```text
schema_version
status
operation_status
stale_recovery_status
scheduler_policy_status
scheduler_round_invoked
unsafe
scanned_entry_count
checked_candidate_count
categories
bounded_reason_ids
```

They must not expose job IDs, dispatch IDs, claim tokens, lease owners, filesystem roots/paths, exact timestamps, raw records, raw exceptions, protected source bodies, memory content, backend text, or nested delegate results.

## Non-goals

O1F does not implement:

- scheduler polling loop;
- sleep, timer, or recurring schedule;
- daemon or service supervision;
- worker pool;
- always-on local operation;
- O2 supervised worker service;
- O3 always-on operation;
- new queue lifecycle authority;
- B3 transition direct rewrite;
- C2 worker semantic changes;
- I1-G replay semantic changes;
- Primary MEM mutation;
- SOUL Lab UI;
- Pin/Unpin apply;
- Held Apply/Discard runtime.

## Validation commands

```bash
python -m compileall relaylm scripts

PYTHONPATH=.:scripts python scripts/relaylm_o1a_scheduler_contract_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1b_sealed_replay_lane_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1c_eligible_queue_lane_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1d1_production_round_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1d2_scheduler_policy_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1e_scheduler_operational_controls_smoke.py

PYTHONPATH=.:scripts python scripts/relaylm_o1f_operational_validation_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1f_operational_validation_corruption_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1f_operational_validation_concurrency_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1f_operational_validation_saturation_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1f_operational_validation_restart_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1f_operational_validation_security_smoke.py

PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/o1f_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
```

## Completion report

The implementation evidence for this slice is recorded in [O1F completion report](../mvp/wave6/o1f_completion_report.md).
