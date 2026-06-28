# E1-R3 Durable Replay Residual Follow-up

Generated: 2026-06-28 JST

This note records the remaining #436 review residual that still needs code work after the #354/#435 repair commits in this branch.

## Residual

Durable finalization replay must preserve the E1-R3 `formation_summary_artifact` across sealed-record replay.

Current code facts:

- `RelayMEMSLPFinalizedTurnSource` owns `formation_summary_artifact` and the live finalized-source builder populates it.
- The protected-source payload intentionally omits the formation summary for C1-5/C1-2 compatibility.
- The durable finalization seal mapping still needs to carry `formation_summary_artifact` as worker-internal replay evidence, while accepting legacy v0 sealed records that do not have it.

## Required code changes

- Add `formation_summary_artifact` to the durable finalized-source seal mapping.
- Keep a legacy accepted finalized-source field set so existing sealed v0 records without the field remain replayable.
- Validate `formation_summary_artifact` as a mapping when present.
- Pass it through `_reconstruct_source()` when rebuilding `RelayMEMSLPFinalizedTurnSource`, defaulting legacy records to `{}`.
- Add replay smoke coverage that compares the replayed source formation summary with the originally sealed source.

## Non-goals

- Do not add formation summary to the protected-source payload.
- Do not change B1/B2 queue identity.
- Do not invalidate existing durable-finalization records solely because they predate E1-R3 formation summaries.
