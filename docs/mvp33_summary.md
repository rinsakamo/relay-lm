# MVP-33: RelayRUN Visible Recovery Preflight Summary

## Date basis

- JST date: 2026-06-05.
- Based on main after PR #225 merged.
- Scope: docs-only summary of RelayRUN visible recovery response preflight diagnostics.

## Completed scope

- `visible_recovery_response_preflight` artifact:
  - RelayRUN emits a diagnostics-only preflight artifact for future user-visible recovery response handling.
- Default-off visible recovery preflight config:
  - Visible recovery preflight remains guarded by explicit default-off and dry-run-only configuration.
- Full output pipeline required:
  - The artifact records that future visible recovery must pass through the full RelayLM output pipeline before any text can reach the user.
- `required_pipeline_nodes`:
  - The preflight lists input-side RelaySCN, input-side RelayEMO, RelayCTX repack, main LLM or recovery generator, RelayCTX unpack, return-side RelayEMO, and output-side RelaySCN.
- `pipeline_preflight`:
  - The artifact records required pipeline gates for RelaySCN, RelayEMO, RelayCTX repack, RelayCTX unpack, main LLM or recovery generator, and output-side RelaySCN.
- `user_visible_allowed=false`:
  - User-visible recovery output remains blocked in this phase.
- `apply_allowed=false / apply_attempted=false / applied=false`:
  - RelayRUN records that visible recovery cannot be applied, has not been attempted, and has not been applied.
- `final_text_generated=false`:
  - RelayRUN records that it did not generate final character-facing text.
- `source_message_kind` from `recovery_response_draft`:
  - The visible recovery preflight preserves the draft intent source kind, such as `none`, `ask_clarification`, `context_repair_prompt`, or `explain_backend_error`.
- Enabled non-dry-run still preflight-only:
  - Even when visible recovery preflight is enabled and dry-run-only is disabled, the artifact remains blocked by not-implemented and output-pipeline-not-executed gates.

## Runtime safety

- Diagnostics-only:
  - MVP-33 describes visible recovery readiness and blocked reasons without applying behavior.
- Default disabled:
  - Visible recovery preflight remains default-off unless explicitly enabled.
- No user-visible recovery output:
  - RelayRUN does not show recovery text to the user in this phase.
- No RelayRUN direct final text:
  - RelayRUN does not directly finalize character-facing recovery responses.
- No backend payload mutation:
  - Visible recovery artifacts are not forwarded to backend providers.
- No response body mutation:
  - Existing response bodies remain unchanged by visible recovery diagnostics.
- No resume / retry / recovery transition apply:
  - RelayRUN does not resume checkpoints, retry failed nodes, or apply recovery transitions.
- No raw user/backend/response/snippet/prompt/final text in artifact:
  - The visible recovery artifact remains content-free and avoids raw messages, backend payloads, response text, snippet text, prompt text, page bodies, and final generated text.
- Future visible recovery must pass through full output pipeline:
  - Any future user-visible recovery path must run through the complete RelayLM output pipeline.
- Output-side RelaySCN gate required:
  - Output-side RelaySCN remains a required final gate before any future recovery response can become visible.

## Artifact chain

- `recovery_transition_artifact`:
  - Proposes a future recovery transition such as context repair, ask-user confirmation, retry-safe node, or blocked-state explanation.
- `waiting_user_contract`:
  - Structures whether recovery requires user confirmation, clarification, or another waiting-user action.
- `recovery_apply_preflight`:
  - Converts transition and waiting-user state into explicit apply gates and blocked reasons without applying recovery.
- `recovery_response_draft`:
  - Converts recovery apply preflight state into content-free draft intent for a future output pipeline without finalizing text.
- `visible_recovery_response_preflight`:
  - Converts recovery response draft intent into explicit full-output-pipeline requirements and keeps user-visible output blocked.
- Relation to RelaySCN / RelayEMO / RelayCTX / Main LLM or recovery generator / Output-side RelaySCN:
  - A future visible recovery response must enter input-side RelaySCN and RelayEMO, pass through RelayCTX repack, run the main LLM or a dedicated recovery generator, pass through RelayCTX unpack and return-side RelayEMO, and then be gated by output-side RelaySCN before reaching the user.

## Validation summary

- Visible recovery preflight smoke:
  - Validates normal, recovery scene, unresolved reference, backend error, enabled non-dry-run still-preflight-only behavior, required pipeline nodes, safety flags, trace metadata, and backend payload non-mutation.
- Recovery response draft smoke:
  - Revalidates draft-only recovery response intent, source message kinds, content-free prompts, and final-text blocking.
- Recovery apply preflight smoke:
  - Revalidates recovery apply blocked gates, waiting-user confirmation blocking, and non-apply behavior.
- Waiting-user contract smoke:
  - Revalidates waiting-user classification for recovery scene, unresolved reference, backend error, and normal paths.
- Recovery transition dry-run smoke:
  - Revalidates recovery transition proposals without apply.
- Checkpoint index smoke:
  - Revalidates bounded content-free checkpoint listing, traversal cap, symlink blocking, traversal blocking, and outside-root blocking.
- Checkpoint writer smoke:
  - Revalidates default-off content-free checkpoint writing.
- Resume preflight smoke:
  - Revalidates checkpoint readability diagnostics without resume.
- Runtime checkpoint dry-run smoke:
  - Revalidates RelayRUN runtime checkpoint artifact shape and node-status summaries.
- Runtime diagnostics smoke:
  - Revalidates runtime diagnostics payload structure.
- Trace success smoke:
  - Revalidates RelayRUN artifact propagation through trace metadata.
- RelaySCN / RelayREF / RelayMEM smokes:
  - Revalidates scene policy, reference handling, memory retrieval, runtime context injection, snippet injection, and payload-diff behavior alongside the RelayRUN chain.
- Token budget truncation smokes:
  - Revalidates token-budget truncation ordering and confirms RelayRUN diagnostics do not bypass truncation safety.

## Key design result

RelayRUN can now express that a recovery response could become visible only through the full output pipeline, while still not generating or applying any visible recovery output itself.

## Remaining limitations

- No user-visible recovery response:
  - Recovery output remains internal diagnostics only.
- No recovery response generator:
  - There is no generator contract or implementation that converts recovery intent into safe user-facing text.
- No output pipeline apply:
  - Visible recovery is not routed through the full output pipeline yet.
- No output-side RelaySCN recovery gate implementation:
  - Output-side RelaySCN is required by the preflight but not yet implemented as an apply gate.
- No user action API:
  - User confirmation and clarification actions are not accepted through a structured API.
- No actual resume:
  - Checkpoints cannot be resumed.
- No retry execution:
  - Failed backend or runtime nodes are not retried.
- No stream recovery:
  - Streaming recovery behavior is not implemented.
- No checkpoint selection policy:
  - RelayRUN does not select checkpoints for recovery or resume.

## Next phase

- Recovery response generator contract:
  - Define how content-free recovery intent can be converted into safe recovery text without bypassing RelayLM style, scene, and safety gates.
- Output-side RelaySCN visible recovery gate:
  - Define and implement the final scene/safety gate for future visible recovery output.
- User action / confirmation API:
  - Define structured user confirmation and clarification actions that can unblock waiting-user states.
- Visible recovery response apply preflight:
  - Add a preflight layer for moving visible recovery from draft intent toward full-pipeline execution while still blocking apply.
- Eventual gated visible recovery response through full output pipeline only:
  - Allow visible recovery output only after the complete pipeline executes and all gates pass.
