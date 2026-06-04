# MVP-30: RelayRUN Checkpoint and Recovery Dry-Run Summary

## Date basis

- JST date: 2026-06-04.
- Based on main after PR #211 through #216 merged.
- Scope: docs-only summary of the RelayRUN checkpoint, resume preflight, and recovery transition dry-run chain.

## Completed scope

- Runtime checkpoint artifact:
  - RelayRUN emits a runtime artifact that records run identity, request phase, node progress, and blocked reasons without changing backend behavior.
- `node_status` summaries:
  - Runtime nodes summarize whether major execution steps are pending, completed, skipped, failed, or blocked.
- `checkpoint_persistence_plan`:
  - RelayRUN reports whether checkpoint persistence is configured, allowed, blocked, or dry-run-only before any write path is considered.
- `checkpoint_writer_preflight`:
  - RelayRUN reports writer readiness, target preview, directory/write gating, and blocked reasons before any checkpoint file write.
- Default-off checkpoint writer:
  - File-backed checkpoint writing exists behind explicit configuration and remains disabled by default.
- Content-free checkpoint envelope:
  - The checkpoint writer persists only safe runtime state metadata and diagnostics, not raw prompt, backend, response, or snippet content.
- `resume_preflight`:
  - RelayRUN can validate checkpoint readability and resume eligibility as diagnostics while keeping actual resume disabled.
- `recovery_transition_artifact`:
  - RelayRUN can propose a recovery transition from observed node state without applying recovery, retry, or user-visible behavior.

## Runtime safety

- Default disabled where applicable:
  - Checkpoint file writes and resume-oriented behavior require explicit opt-in gates where applicable.
- Diagnostics-only where applicable:
  - Persistence planning, resume preflight, and recovery transition proposal are observable diagnostics before runtime application.
- No backend payload mutation:
  - RelayRUN checkpoint/recovery artifacts are not injected into the backend request payload.
- No raw user/backend/response/snippet content in checkpoint:
  - Checkpoint envelopes are content-free and avoid storing raw user messages, backend responses, generated response text, or RelayMEM snippet text.
- No resume/retry/recovery apply yet:
  - RelayRUN does not resume execution, retry failed work, or apply recovery transitions in this phase.
- Recovery transition not user-visible:
  - The recovery transition artifact remains internal diagnostics and does not produce a user-facing recovery response.
- Output pipeline not bypassed:
  - Future recovery output must continue through the normal RelayLM output pipeline; MVP-30 does not introduce a bypass.

## Artifact chain

- `relayrun_artifact`:
  - Top-level runtime diagnostic artifact for a RelayRUN execution.
- `checkpoint_persistence_plan`:
  - Persistence intent, gate, target preview, and blocked-reason summary.
- `checkpoint_writer_preflight`:
  - Writer readiness and safety preflight for file-backed checkpoint persistence.
- Checkpoint envelope:
  - Content-free file-backed envelope containing safe RelayRUN state metadata and diagnostics when the writer is explicitly enabled and allowed.
- `resume_preflight`:
  - Checkpoint readability and resume-readiness diagnostic result.
- `recovery_transition_artifact`:
  - Dry-run proposal for a recovery transition based on current RelayRUN node state.

## Validation summary

- RelayRUN checkpoint dry-run smoke:
  - Validates runtime checkpoint artifact creation and diagnostics exposure.
- Checkpoint writer smoke:
  - Validates default-off writer behavior, preflight gating, and safe content-free checkpoint writing when explicitly enabled.
- Resume preflight smoke:
  - Validates resume diagnostics, blocked reasons, and checkpoint envelope readability without applying resume.
- Recovery transition dry-run smoke:
  - Validates recovery transition proposal diagnostics without applying recovery or surfacing it to the user.
- Runtime diagnostics smoke:
  - Validates RelayRUN artifacts stay in diagnostics/trace metadata rather than backend payloads.
- Trace success smoke:
  - Validates RelayRUN checkpoint/recovery diagnostics are carried through trace metadata on successful requests.
- RelaySCN / RelayREF / RelayMEM smokes:
  - Revalidates existing scene, reference, and memory diagnostics alongside the RelayRUN chain.
- Token budget truncation smokes:
  - Revalidates the existing token-budget pipeline and confirms RelayRUN diagnostics do not bypass output/payload safety paths.

## Key design result

RelayRUN now records where execution is, can persist a safe checkpoint envelope, can validate checkpoint readability, and can propose a recovery transition without applying it.

## Remaining limitations

- No actual resume:
  - RelayRUN can inspect readiness only; it does not resume execution from a checkpoint.
- No retry execution:
  - Failed or blocked nodes are not retried.
- No user-visible recovery response:
  - Recovery proposal remains diagnostics-only.
- No stream recovery:
  - Streaming recovery behavior is not implemented.
- No checkpoint pruning/index:
  - Checkpoint retention, pruning, and index maintenance are still future work.
- No multi-run lookup:
  - RelayRUN does not yet list, search, or select checkpoints across multiple runs.

## Next phase

- Resume readiness / `waiting_user` contract:
  - Define when a run is safe to pause, resume, or wait for user input.
- Checkpoint index / listing:
  - Add safe checkpoint discovery without exposing raw request/response content.
- Recovery transition apply preflight:
  - Add an explicit preflight layer before any recovery transition can be applied.
- Eventually user-visible recovery through full output pipeline only:
  - If recovery becomes user-visible, it must pass through the normal RelayLM output pipeline and must not bypass runtime safety gates.
