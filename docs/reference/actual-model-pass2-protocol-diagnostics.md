# Actual-model Pass 2 Protocol Diagnostics

Status: current #1386 diagnostic path for investigating a failed two-pass provider/parser attempt without changing qualification semantics.

## Purpose

A normal actual-model run records stable two-pass status such as `pass2_failed`, but that runtime status intentionally does not carry raw provider response bodies or exception chains. When Stage R cannot distinguish output truncation, malformed model JSON, wrong wire shape, or a RelayLM parser rejection, use this explicit diagnostic path before changing prompt, window, or reasoning.

The diagnostic observes the existing OpenAI-compatible request/response path. It does not alter the request.

## Sidecar

`relaylm.actual_model_pass2_protocol_diagnostics` records only failed Pass 2 attempts and can bind them to an immutable `amp2d-*` sidecar. Each failure contains, when available:

```text
turn_index
http_status
response_text
message_content
finish_reason
usage
exception_chain
```

The standard `ActualModelEvidence`, `TwoPassExtractionResult`, State/Continuity proposals, and deterministic decisions remain unchanged.

Raw response content is written only to the explicitly supplied external artifact root. It is not emitted into generic runtime logs.

## Current vLLM runner

Run one existing Stage R scenario under the already-qualified `reference_baseline` request identity:

```text
python -m relaylm.actual_model_pass2_protocol_diagnostic_runner \
  --repo-root <clean-current-v1-checkout> \
  --snapshot-root <verified-model-snapshot> \
  --provider-base-url <live-vllm-base-url> \
  --workspace-root <external-workspace-root> \
  --artifact-root <external-artifact-root> \
  --model-runner v2 \
  --scenario-id <existing-stage-r-scenario-id> \
  --capacity-evidence-id <current-wire-capacity-evidence-id> \
  --capacity-evidence-root <external-capacity-evidence-root> \
  --replicate-id <new-diagnostic-replicate-id> \
  [--cognitive-budget <same-current-screening-budget-declaration>]
```

The runner deliberately fixes the condition role to `reference_baseline`. It reuses canonical vLLM target verification, live reasoning attestation, capacity admission, pass-request identity, Character fixture, and existing scenario definitions. `--scenario-id` must already be in the current Stage R plan.

The runner executes the existing scenario trajectory so the selected evidence remains comparable to normal screening. It does not create a new semantic fixture. The sidecar records only Pass 2 attempts that actually failed.

## Interpretation order

Use the sidecar only to localize the protocol failure. Typical next branches are:

```text
finish_reason = length + truncated message content
  -> generation-headroom / capacity-contract question

finish_reason = stop + malformed or wrong-shape content
  -> model protocol-following / prompt-wire question

valid expected JSON content + RelayLM rejection
  -> parser/contract implementation question
```

Do not classify scaffold semantic quality from a Pass 2 that never produced an admitted structured cognition output. Do not run Pass 2 reasoning escalation until the provider/parser failure has been localized and the reference baseline can be semantically evaluated.

## Authority

#1386 owns this diagnostic evidence path. #1533 owns the stable runtime failure semantics and provider/parser acceptance boundary. See `docs/contracts/cognition-pass2-protocol-failure.md`.
