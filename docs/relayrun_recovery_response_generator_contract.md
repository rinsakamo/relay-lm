# RelayRUN Recovery Response Generator Contract

## Purpose

This document defines the future RelayRUN recovery response generator contract that sits after `recovery_response_draft` and `visible_recovery_response_preflight`.

The contract describes how content-free recovery intent can be transformed into safe user-facing recovery text in a later phase. It is a design and contract document only for MVP-34 preparation: it does not execute a generator, does not produce visible output, and does not change runtime behavior.

The core purpose is to preserve the current boundary:

- RelayRUN may structure recovery intent, blocked state, and output-pipeline preflight diagnostics.
- RelayRUN must not directly finalize character-facing text.
- Any future visible recovery response must pass through the full output pipeline and output-side safety gates.

## Non-goals

- No runtime generator implementation.
- No user-visible recovery output.
- No RelayRUN direct final text.
- No backend payload mutation.
- No response body mutation.
- No actual resume.
- No retry execution.
- No recovery transition apply.
- No stream recovery.

## Position in artifact chain

The future generator contract is downstream of the existing recovery diagnostics chain:

1. `recovery_transition_artifact`
   - Proposes a future recovery transition such as context repair, ask-user confirmation, retry-safe node, or blocked-state explanation.
2. `waiting_user_contract`
   - Records whether user confirmation or clarification is required before recovery can continue.
3. `recovery_apply_preflight`
   - Records apply gates and blocked reasons without applying recovery.
4. `recovery_response_draft`
   - Records content-free recovery-output intent and draft instructions without generating final text.
5. `visible_recovery_response_preflight`
   - Records full output-pipeline requirements before any user-visible recovery text can be allowed.
6. `recovery_response_generator`
   - Defines whether a generator may be invoked and what content-free intent it may use.
7. `output_relayscn_recovery_gate`
   - Records projected source metadata for a future output-side scene/safety gate before any recovery text can become visible.
8. Future visible recovery response apply preflight
   - Performs the final pre-apply check before response mutation or visible recovery output is allowed.

## Required inputs

A future generator contract may use only metadata and content-free intent from approved upstream artifacts:

- `recovery_response_draft`.
- `visible_recovery_response_preflight`.
- Scene policy / output-side RelaySCN policy.
- Response mode, route, and `character_id` metadata only.
- Safety/content policy.
- Optional `user_action_confirmation` in a future phase.

## Forbidden inputs/content

The generator contract must not receive or embed raw content from runtime payloads, backend responses, memory bodies, or checkpoints.

Forbidden inputs include:

- Raw user message.
- Backend payload.
- Backend response text.
- Prompt text.
- Snippet/page body text.
- Final generated text from a prior attempt.
- Unapproved memory body.
- Full checkpoint payload body.
- Full source artifact payloads that contain draft prompt text or nested
  artifact trees.

Source artifacts in the generator artifact must be content-free projections only.
They may include schema versions, booleans, source kinds, blocked reason names,
pipeline preflight booleans, and required pipeline node names, but must not
include `draft_prompt_for_output_pipeline` or nested `source_artifacts`.

## Output contract

A future diagnostics-only generator contract artifact should use a shape like:

```yaml
recovery_response_generator_contract:
  schema_version: relayrun.recovery_response_generator_contract.v0
  diagnostics_only: true
  generator_allowed: false
  generator_attempted: false
  generated_text_present: false
  output_pipeline_required: true
  source_message_kind: none
  allowed_message_intent: none
  blocked_reasons:
    - recovery_response_generator_not_implemented
    - recovery_response_generator_disabled
    - recovery_response_generator_dry_run_only
  safety:
    contains_user_content: false
    contains_backend_payload: false
    contains_response_text: false
    contains_prompt_text: false
    contains_snippet_text: false
    contains_final_text: false
    direct_user_output_allowed: false
    run_direct_text_finalization_allowed: false
```

Required fields:

- `schema_version`:
  - Identifies the artifact schema.
- `diagnostics_only`:
  - Must remain `true` while generator behavior is not implemented.
- `generator_allowed=false`:
  - The generator must not be allowed until all gates pass in a future apply phase.
- `generator_attempted=false`:
  - No runtime generator invocation occurs in the docs-only or diagnostics-only phase.
- `generated_text_present=false`:
  - The artifact must not contain generated final text.
- `output_pipeline_required=true`:
  - Any visible output must go through the full output pipeline.
- `source_message_kind`:
  - Mirrors the content-free kind from `recovery_response_draft` or `visible_recovery_response_preflight`.
- `allowed_message_intent`:
  - Records the allowed intent class without containing final text.
- `blocked_reasons`:
  - Records why generator execution remains blocked.
- `safety`:
  - Records content and output-surface invariants.

## Message intent mapping

The generator contract maps source message kinds to content-free message intents:

- `none` -> no recovery message.
- `ask_clarification` -> ask user to clarify unresolved reference.
- `context_repair_prompt` -> ask user to confirm/restate current context.
- `explain_backend_error` -> explain failure at high level and ask whether to retry.
- `confirm_recovery` -> ask user how to proceed from blocked state.

All wording must stay content-free and scene-gated. The contract may describe intent, but it must not store final user-facing wording until the output-side scene and safety gates are implemented.

## Required gates

A future implementation must fail closed unless all required gates pass:

- Explicit config enabled.
- `dry_run_only=false` in a future non-diagnostics phase.
- `visible_recovery_response_preflight` present.
- Output-pipeline preflight passed.
- Output-side RelaySCN allows recovery output.
- User confirmation when `waiting_user_required=true`.
- Content-free contract passed.
- Backend payload mutation blocked.
- Response body mutation blocked until apply phase.

## Failure / blocked reasons

Recommended blocked reasons:

- `recovery_response_generator_not_implemented`.
- `recovery_response_generator_disabled`.
- `recovery_response_generator_dry_run_only`.
- `visible_recovery_preflight_missing`.
- `output_pipeline_not_executed`.
- `output_side_relayscn_gate_missing`.
- `waiting_user_confirmation_required`.
- `content_policy_not_verified`.

## Future implementation notes

The next implementation should add a diagnostics-only artifact first. That artifact should prove the generator contract can be built from existing recovery draft and visible recovery preflight artifacts without exposing raw content or mutating runtime behavior.

After that, add smoke tests for:

- Normal request.
- Recovery scene.
- Unresolved reference.
- Backend error.

No visible recovery output should be introduced until both the output-side RelaySCN gate and visible recovery response apply preflight exist. Runtime implementation must continue to preserve backend forwarding payloads, response bodies, RelayMEM ordering, and token truncation ordering.

## MVP implementation note

A diagnostics-only `recovery_response_generator` artifact now implements the first runtime form of this contract. The artifact is still fail-closed: `generator_allowed=false`, `generator_attempted=false`, and `generated_text_present=false` remain fixed while generator execution is not implemented.

The implementation does not generate user-visible text, does not execute a recovery response generator, does not mutate backend payloads, and does not mutate response bodies. It only maps content-free `source_message_kind` values from `recovery_response_draft` to content-free `allowed_message_intent` values and records blocked reasons for future output-pipeline work. The runtime artifact stores source projections only and intentionally omits draft prompt text plus nested source artifact trees.

## Next downstream gate

The next downstream runtime artifact is `output_relayscn_recovery_gate`. It is
also diagnostics-only and fail-closed. It receives only projected source
metadata from `recovery_response_generator` and
`visible_recovery_response_preflight`; it must not embed full source artifacts,
nested `source_artifacts`, draft prompts, raw user/backend/response/snippet
content, prompt text, or final generated text.

This gate still does not execute the generator, does not generate user-visible
text, does not run output-side RelaySCN, does not apply visible output, does not
mutate backend payloads, and does not mutate response bodies. It exists only to
record that future visible recovery must pass output-side RelaySCN and a later
visible recovery apply preflight before any final user-visible response can be
considered.
