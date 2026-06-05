# MVP-32: RelayRUN Recovery Apply Preflight and Response Draft Summary

## Date basis

- JST date: 2026-06-05.
- Based on main after PR #221 and #223 merged.
- Scope: docs-only summary of RelayRUN recovery apply preflight and recovery response draft diagnostics.

## Completed scope

- `recovery_apply_preflight` artifact:
  - RelayRUN emits a diagnostics-only preflight artifact that records whether a future recovery transition could be considered for apply.
- Default-off recovery apply preflight config:
  - Recovery apply preflight is guarded by explicit default-off and dry-run-only configuration.
- Recovery apply required gates:
  - The artifact records required gates such as explicit config enablement, dry-run disabled, recovery transition presence, waiting-user contract presence, scene-policy allowance, output-pipeline requirement, and user confirmation when required.
- `waiting_user_confirmation_required` blocking:
  - Recovery and unresolved-reference paths that require user confirmation remain blocked until a future user-action contract exists.
- No apply even when enabled non-dry-run:
  - Recovery apply remains blocked by the not-implemented gate even if config is enabled and dry-run-only is disabled.
- `recovery_response_draft` artifact:
  - RelayRUN emits a diagnostics-only draft artifact that records recovery-output intent for a future output pipeline.
- Default-off recovery response draft config:
  - Recovery response drafting is guarded by explicit default-off and dry-run-only configuration.
- `draft_only=true`:
  - The draft artifact is explicitly marked as draft-only and must not be treated as final response text.
- `final_text_generated=false`:
  - RelayRUN records that no final character-facing text was generated.
- `suggested_message_kind`:
  - The draft classifies output intent as `none`, `ask_clarification`, `confirm_recovery`, `explain_backend_error`, or `context_repair_prompt`.
- Content-free `draft_prompt_for_output_pipeline`:
  - Draft prompts are short internal instructions for a future output pipeline and do not include raw user, backend, response, snippet, or prompt content.

## Runtime safety

- Diagnostics-only:
  - MVP-32 artifacts describe recovery apply and recovery response intent without applying behavior.
- Default disabled:
  - Recovery apply preflight and recovery response draft diagnostics remain default-off and dry-run protected.
- No user-visible recovery output:
  - RelayRUN does not surface recovery text to users in this phase.
- No direct character-facing text:
  - The recovery response draft is not a final assistant message.
- No backend payload mutation:
  - RelayRUN recovery artifacts are not forwarded to backend providers.
- No response body mutation:
  - Success and error response bodies remain on the existing runtime path.
- No resume/retry/recovery apply:
  - RelayRUN does not resume checkpoints, retry failed nodes, or apply recovery transitions.
- RUN does not finalize final response text:
  - RelayRUN only prepares diagnostics and draft intent; it does not act as a response generator.
- Future visible recovery must pass through full output pipeline:
  - Any future user-visible recovery must go through the full RelayLM output path and safety gates.
- No raw user/backend/response/snippet/prompt content in artifacts:
  - Artifacts remain content-free and avoid raw messages, backend payloads, response text, snippet text, prompt text, and page bodies.

## Artifact chain

- `recovery_transition_artifact`:
  - Proposes a future transition type such as context repair, ask-user confirmation, retry-safe node, or blocked-state explanation.
- `waiting_user_contract`:
  - Structures whether user confirmation or clarification is required before future recovery can continue.
- `recovery_apply_preflight`:
  - Converts transition and waiting-user state into explicit apply gates and blocked reasons without applying recovery.
- `recovery_response_draft`:
  - Converts apply-preflight state into content-free draft intent for a future output pipeline without finalizing text.
- Relation to RelaySCN / RelayEMO / RelayCTX / Main LLM or recovery generator / Output-side SCN:
  - A future visible recovery response must pass through scene policy, emotion/context layers, the main LLM or a dedicated recovery generator, and output-side safety/scene gating before it reaches the user.

## Validation summary

- Recovery apply preflight smoke:
  - Validates normal, recovery-scene, unresolved-reference, backend-error, and enabled non-dry-run blocked cases.
- Recovery response draft smoke:
  - Validates draft kinds, content-free prompts, final-text blocking, response preservation, trace metadata, and backend payload immutability.
- Waiting-user contract smoke:
  - Revalidates waiting-user classification for normal, recovery, unresolved reference, and backend-error paths.
- Recovery transition dry-run smoke:
  - Revalidates recovery transition proposal diagnostics without apply.
- Checkpoint index smoke:
  - Revalidates bounded content-free checkpoint listing and unsafe root/file blocking.
- Checkpoint writer smoke:
  - Revalidates default-off content-free checkpoint writing.
- Resume preflight smoke:
  - Revalidates checkpoint readability diagnostics without resume.
- Runtime checkpoint dry-run smoke:
  - Revalidates RelayRUN runtime artifact and node-status summaries.
- Runtime diagnostics smoke:
  - Revalidates diagnostics/log payload structure.
- Trace success smoke:
  - Revalidates RelayRUN artifact propagation in trace metadata.
- RelaySCN / RelayREF / RelayMEM smokes:
  - Revalidates scene policy, reference handling, memory retrieval, runtime context, snippet injection, and payload-diff behavior alongside the RelayRUN chain.
- Token budget truncation smokes:
  - Revalidates truncation ordering and confirms RelayRUN diagnostics do not bypass token-budget safety.

## Key design result

RelayRUN can now prepare recovery-output intent and draft material without applying it, while preserving the rule that user-visible recovery must go through the full output pipeline.

## Remaining limitations

- No user-visible recovery response:
  - Recovery output remains internal diagnostics only.
- No recovery response generator:
  - There is no dedicated generator that turns draft intent into safe user-facing text.
- No full output pipeline apply:
  - Recovery drafts are not routed through the final output pipeline yet.
- No actual resume:
  - Checkpoints cannot be resumed.
- No retry execution:
  - Failed backend or runtime nodes are not retried.
- No stream recovery:
  - Streaming recovery behavior is not implemented.
- No user action API:
  - User confirmation and clarification actions are not accepted through a structured API.
- No checkpoint selection policy:
  - RelayRUN does not select checkpoints for recovery or resume.

## Next phase

- User-visible recovery response preflight through full output pipeline:
  - Define the gates for taking recovery draft intent into the complete output path.
- Recovery response generator contract:
  - Specify how a generator may produce safe recovery text from content-free intent.
- Output-side RelaySCN gating:
  - Add output-side scene and safety checks before recovery text can be shown.
- Waiting_user user action API / confirmation contract:
  - Define structured confirmation and clarification actions that unblock future recovery flows.
- Resume readiness policy:
  - Specify when checkpoint selection and recovery state make a run eligible for actual resume planning.
