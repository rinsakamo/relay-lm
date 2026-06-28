# E1-R3 Durable Replay Residual Follow-up

Generated: 2026-06-28 JST

This note records the #436 review residual and the repair applied in this branch.

## Residual

Durable finalization replay must preserve the E1-R3 `formation_summary_artifact` across sealed-record replay.

## Repair in this branch

- Added `relaylm/relaymem_durable_finalization_formation_replay_patch.py` to preserve formation summaries inside durable-finalization seal/replay authorities without adding them to the protected-source payload.
- `finalized_source_to_mapping()` now emits `formation_summary_artifact` as worker-internal replay evidence.
- `validate_finalized_source_mapping()` accepts both the new shape and legacy v0 sealed records that predate the field.
- Replay reconstruction passes `formation_summary_artifact` into `RelayMEMSLPFinalizedTurnSource`, using `{}` for legacy records.
- Added `scripts/relaylm_i1gc_durable_finalization_formation_replay_smoke.py` and wired it into the I1-GC durable-finalization replay workflow.

## CI follow-up

The first PR run exposed failures in the M3h recovery-audit lane and the Phase 6-C1 integrated worker fault lane. The shared repair was to avoid over-rejecting legitimate uncertain M3g receipts while still rejecting forged dry-run/state-uncertain receipts and cleanup-incomplete receipts without reconciliation progress.

## Non-goals preserved

- The protected-source payload remains unchanged.
- B1/B2 queue identity remains unchanged.
- Existing durable-finalization records are not invalidated solely because they predate E1-R3 formation summaries.
