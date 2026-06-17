# RelayRUN Recovery Diagnostics Manual Smoke

## Purpose

Validate the current diagnostics-only RelayRUN recovery chain without treating it as visible recovery execution.

This document generalizes the historical MVP-38 checklist while preserving its operational safety contract.

## Pre-test setup

1. Start LM Studio and confirm its OpenAI-compatible endpoint.
2. Start RelayLM with a local `config.yaml`.
3. Point OpenWebUI at RelayLM, not directly at LM Studio.
4. Record redacted differences from the copy-ready config.
5. Keep recovery settings default-off unless a specific diagnostics check requires them.
6. Record whether diagnostics and trace are enabled and where trace is written.

Suggested config comparison:

```bash
git diff --no-index examples/config/openwebui_lmstudio.yaml config.yaml
```

Review:

- route/model mapping,
- RelayLM listen address,
- LM Studio backend URL and model ID,
- diagnostics/trace settings,
- recovery-related overrides.

## Normal conversation baseline

Run normal chat first. Example:

```text
こんにちは。今日の作業を短く整理して。
```

Expected:

- OpenWebUI completes the request,
- RelayLM returns the backend response normally,
- LM Studio receives a normal chat request,
- route/profile behavior is plausible,
- recovery text does not appear in the visible response.

## Diagnostics inspection boundary

Recovery artifacts are inspected through RelayLM diagnostics or trace metadata, not through visible output.

Expected artifact order when present:

1. `runtime_checkpoint`
2. `recovery_transition_artifact`
3. `waiting_user_contract`
4. `recovery_apply_preflight`
5. `recovery_response_draft`
6. `visible_recovery_response_preflight`
7. `recovery_response_generator`
8. `output_relayscn_recovery_gate`
9. `visible_recovery_apply_preflight`
10. `user_action_contract`

## Expected safety metadata

Confirm these fields when the artifact version exposes them, or confirm the equivalent operational boundary:

- `diagnostics_only=true`
- `user_visible_allowed=false`
- `final_text_generated=false`
- `backend_payload_mutation_allowed=false`
- `response_body_mutation_allowed=false`
- `direct_user_output_allowed=false`
- `run_direct_text_finalization_allowed=false`

The invariant is:

- recovery diagnostics do not create direct visible text,
- recovery artifacts are absent from backend payloads,
- backend responses are not rewritten by the recovery chain,
- resume/retry/user-action apply does not execute,
- persisted recovery projections remain content-free.

## Backend payload check

Use a local inspectable backend or repository fake-backend pattern when exact payload inspection is required.

Record:

- whether the backend payload was captured,
- whether recovery artifacts were absent,
- whether an unexpected system/recovery message appeared,
- pass/fail.

## Response body check

Record:

- whether OpenWebUI received the normal backend response,
- whether recovery diagnostics changed the response body,
- whether visible recovery text appeared,
- pass/fail.

## Content-free check

Shared or persisted evidence must exclude:

- raw user text,
- backend response text,
- memory/snippet/page text,
- prompt or compiled block bodies,
- generated final text,
- secrets and local tokens.

Record artifact names, booleans, counts, status classes, and reason IDs instead.

## PASS criteria

- normal OpenWebUI -> RelayLM -> LM Studio chat works,
- recovery artifact names appear only in diagnostics/trace when emitted,
- `final_text_generated` remains false,
- backend payload contains no recovery artifacts,
- response body remains the backend response body,
- recovery chain stays blocked/fail-closed where required,
- persisted diagnostics remain content-free,
- no visible recovery output appears.

## FAIL criteria

- visible recovery text appears,
- response body changes unexpectedly,
- backend payload contains recovery artifact data,
- content-bearing request/response/prompt data appears in persisted artifacts,
- actual resume/retry/user-action apply occurs,
- normal chat breaks.

## Evidence

Collect only redacted, shareable evidence:

- RelayLM commit SHA,
- redacted config summary,
- startup command,
- OpenWebUI connection URL class,
- LM Studio model ID,
- normal conversation result summary,
- diagnostics artifact names,
- safety-field assertions,
- backend payload mutation result,
- response-body mutation result,
- overall pass/fail.
