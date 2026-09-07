# RelayLM 2.0 — #2211 factorized calibration-v2 physical host

This document defines the fail-closed physical host for the preregistered factorized calibration v2 owned by #2211.

It does not alter the generator, seeds, regimes, operator wording, selection priority, or admission thresholds frozen by the calibration-v2 preregistration.

```text
claim_status = NON_CITABLE_S2_CALIBRATION_V2
citable      = false
```

## Execution boundary

One completed transaction is exactly:

```text
6 fresh seeds
× 4 frozen regimes
× 3 frozen probes
= 72 provider calls
```

No early stopping, semantic retry, automatic retry, prompt repair, seed replacement, threshold change, or result-dependent regime change is legal.

Any failed provider request counts as an attempt and terminates the transaction as `INCOMPLETE`.

## Repository and artifact authority

Before execution, the host binds:

- exact Git commit;
- exact Git tree;
- clean checkout requirement;
- one fresh repo-external artifact root.

The artifact root must be empty before the transaction. The host writes:

```text
run-manifest.json
run-state.json
request-evidence.jsonl
calibration-v2-result.json   # completed transaction only
```

Visible structured model responses are retained only as `instrumentation_only` evidence for later bounded forensic work. They are not P0–P6 evidence.

## Live LM Studio binding

The host reuses the existing native LM Studio model probe. It requires one unique loaded model instance and freezes at least:

```text
model
model_instance_id
context_length
runtime
```

The runtime record includes the observed architecture, format, quantization, selected variant, and reasoning capability metadata when exposed.

A fresh native binding probe is executed before every provider request. Any change to a frozen live-binding field terminates the transaction before the next provider request.

The native API is authority only. It does not generate calibration answers.

## Provider transport

Actual calibration inference remains on the OpenAI-compatible Chat Completions surface with strict JSON Schema structured output:

```text
api               = openai-chat-completions-json-schema-v1
structured_output = true
temperature       = 0
max_tokens        = 128
timeout_seconds   = 300
seed              = null
```

The host reuses the already-qualified reasoning-off client. No request-level reasoning extension is added.

Every successful completion must satisfy:

```text
finish_reason == stop
visible content is non-empty
message.reasoning is absent/null/empty
message.reasoning_content is absent/null/empty
usage.completion_tokens_details.reasoning_tokens == 0
```

The host rejects a transport identity that does not explicitly declare both:

```text
reasoning_mode = off
reasoning_verification = usage.completion_tokens_details.reasoning_tokens==0
```

Thus LM Studio native metadata such as `reasoning.default=on` is not used as the effective reasoning-state verdict; the completion-level accounting is authoritative for this transaction.

## Frozen call order

The host consumes the preregistered `calibration_v2_call_plan()` exactly. It may not add or omit calls.

Before each declared call:

1. reacquire live native binding;
2. fail on drift;
3. issue exactly one structured OpenAI-compatible request;
4. fail unless the reasoning-off completion contract passes;
5. persist the visible response and token accounting as instrumentation.

## Runtime scoring

The runtime scorer parses only the declared strict JSON objects and fails closed on malformed, duplicate, unexpected, out-of-range, or illegal rule fields.

For every seed × regime cell it records independently:

```text
C0 application exactness
C1 formation exactness
C2 rule exactness
C2 answer exactness
C2 joint exactness
input/output tokens
```

Regime summaries use the unchanged preregistered admission contract:

```text
C0 = 6/6
C1 = 3..5/6
C2 = 2..4/6
```

If multiple regimes pass, the preregistered task-coverage priority decides `selected_regime`. If none pass, `selected_regime=null`.

## Scientific boundary

A completed calibration-v2 transaction may only determine whether one frozen task regime is eligible for a new, separate S2 preregistration.

It does not:

- run P0–P6;
- select or rank representation arms;
- prove Memory, Structure, Crystallization, or Model Legibility;
- retune the completed calibration v1;
- authorize S3;
- mutate #2132 architecture authority.

```text
P0-P6                    = NOT RUN
S2                       = BLOCKED until calibration v2 completes and selects a regime
S3                       = BLOCKED
architecture consequence = NONE
```

Physical execution must occur on the local model host with fresh repository/model/runtime authority. Repository/CI work must not be represented as physical evidence.
