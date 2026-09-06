# RelayLM 2.0 — Cognitive IR calibration reasoning-off contract

This document narrows the #2211 pre-S2 physical calibration after the first structured-output
transaction terminated on its first provider request before any calibration result was admitted.

The failed transaction remains terminal historical evidence:

```text
status       = INCOMPLETE
attempts     = 1
completions  = 0
S2           = BLOCKED
S3           = BLOCKED
claim_status = NON_CITABLE_S2_CALIBRATION
```

It is not retroactively repaired or resumed.

## Decision

For the Gemma 4 campaign, the next fresh calibration requires effective reasoning to be **off**.

LM Studio exposes Gemma 4's model-specific `Enable Thinking` custom field. That field controls the
chat-template `enable_thinking` variable. The documented OpenAI-compatible
`POST /v1/chat/completions` payload does not expose a reasoning-mode request parameter, so the
calibration does **not** invent one.

The division remains:

```text
LM Studio environment/model configuration
  -> establish Gemma 4 with Enable Thinking = false
  -> keep context_length = 8192

LM Studio native API
  GET /api/v1/models
  -> fresh model / loaded-instance / context / runtime authority
  -> verify that `off` is among the model's allowed reasoning options

OpenAI-compatible API
  POST /v1/chat/completions
  -> all actual calibration inference
  -> strict JSON Schema structured output
  -> no undocumented reasoning request field
```

The currently documented native model-load REST surface does not expose Gemma's model-specific
`Enable Thinking` custom field. Therefore the physical host must not claim that `POST
/api/v1/models/load` alone establishes reasoning-off. The model-specific setting must already be
configured in LM Studio before the fresh transaction is frozen.

## Effective execution verification

Reasoning-off is not accepted merely because the operator says it is off.

Use `ReasoningOffOpenAICompatibleStructuredCalibrationClient` for every calibration call. An
accepted provider completion requires all of the following:

```text
finish_reason == "stop"
visible message.content is non-empty
message.reasoning / message.reasoning_content are absent, null, or empty
usage.completion_tokens_details exists
usage.completion_tokens_details.reasoning_tokens == 0
```

If explicit reasoning-token accounting is absent, the client fails closed rather than assuming zero.
If any reasoning tokens are reported, the transaction terminates immediately as `INCOMPLETE`.

This makes `reasoning=off` an observed execution property of the OpenAI-compatible test path, not a
claim inferred from model metadata.

## Frozen OpenAI-compatible transport

The next fresh calibration keeps the original bounded output budget:

```text
api                    = openai-chat-completions-json-schema-v1
structured_output      = true
temperature            = 0.0
max_tokens             = 128
seed                   = null
timeout_seconds        = 300
reasoning_mode          = off
reasoning_verification = usage.completion_tokens_details.reasoning_tokens==0
```

The wire request contains no `reasoning` field. `reasoning_mode=off` is frozen transport identity
metadata whose truth is verified from each returned completion.

The earlier 6144-token transport-diagnostic idea is not part of this contract. It addressed the
reasoning-on failure mode and is unnecessary once reasoning-off is the declared execution
condition. Raising `max_tokens` after observing calibration outcomes remains prohibited.

## Exact failure reporting

A provider choice must finish with `stop`. Any other `finish_reason` is terminal, and the
reasoning-off client includes the exact observed value in the error rather than collapsing all
non-stop cases into an opaque message.

A response rejected for reasoning, finish reason, structured content, usage accounting, or any
other provider-contract violation increments `provider_attempts` but not `provider_completions`.
No retry occurs in the same transaction.

## Matrix is unchanged

No calibration science changes here:

```text
6 independent seeds
* 4 frozen difficulty cells
* C0 / C1 / C2
= 72 calibration calls
```

The prompts, generated cases, JSON Schemas, admission thresholds and selected-difficulty rule remain
exactly those merged before this repair. No P0-P6 result was used to define this reasoning-off
condition.

## Physical procedure

For the next transaction:

1. configure `google/gemma-4-12b` in LM Studio with `Enable Thinking = false`;
2. ensure the intended loaded instance uses context length 8192;
3. reacquire exact repository and native loaded-model authority;
4. confirm the model advertises `off` among allowed reasoning settings;
5. build `ReasoningOffOpenAICompatibleStructuredCalibrationClient`;
6. freeze its exact `transport_identity` in the calibration identity;
7. use a fresh empty repository-external artifact root;
8. call the existing `run_calibration_host(...)` exactly once with that client;
9. accept completions only when every response verifies zero reasoning tokens;
10. reconcile the terminal result to #2211.

No native `/api/v1/chat` response is used as a calibration answer. No model output from a diagnostic
or prior failed transaction is reused.

## Claim boundary

Every result remains:

```text
claim_status = NON_CITABLE_S2_CALIBRATION
citable      = false
architecture consequence = NONE
```

A completed calibration may select a difficulty for a separate fresh S2 preregistration. It does
not compare P0-P6 and it cannot open S3 by itself.
