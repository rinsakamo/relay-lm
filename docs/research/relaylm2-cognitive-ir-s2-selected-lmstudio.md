# RelayLM 2.0 Cognitive IR S2 — selected-regime LM Studio physical entrypoint

Status: **PHYSICAL PACKAGE ONLY / NO S2 MODEL CALLS IN THIS TRANSACTION**. Owner: #2211.

This surface adapts the already-preregistered selected S2 family to the currently qualified LM Studio/OpenAI-compatible physical path. It does not change the selected task family, P0-P6 representation semantics, the ten-call order, admission thresholds, S3, or architecture authority.

## Scientific input is unchanged

The owning preregistration remains `relaylm2-cognitive-ir-s2-selected-regime.md`:

```text
selected task regime = V2_IDENTITY_OFFSET_NO_WRAP
seed                 = 1399709667
step_index           = 0
examples_visible     = 0
query                = [6, 5, 6, 8]
expected             = [9, 7, 7, 9]
physical call count  = 10
```

The current entrypoint calls `generate_selected_s2_family()` rather than reconstructing or retuning that family locally.

## Physical condition matched to the completed calibration-v2

The selected-regime admission was established on this model/runtime class, so the S2 entrypoint fail-closes unless fresh Native authority reports:

```text
model            = google/gemma-4-12b
context_length   = 8192
architecture     = gemma4
format           = gguf
quantization     = Q4_K_M
selected_variant = google/gemma-4-12b@q4_k_m
```

These strings intentionally preserve the exact case/shape observed from the Native API in the completed calibration-v2 transaction. Historical receipts are not current physical authority: repository state and the loaded LM Studio binding are reacquired at execution time, then the complete live binding is rechecked before every provider call.

Native `reasoning.default` metadata is **not** treated as the effective reasoning verdict. The completed calibration path already established that this metadata can remain `on` while effective completion behavior is independently verifiable.

## Transport

Actual S2 inference uses OpenAI-compatible:

```text
POST /v1/chat/completions
stream         = false
temperature    = 0
max_tokens     = 512
timeout         = 300 s
request seed    = omitted
reasoning field = omitted
```

LM Studio Native API is used only to establish and recheck the loaded-model/runtime binding.

No undocumented `reasoning`, `reasoning_effort`, or provider-specific thinking override is added to the OpenAI-compatible request.

### Structured Output boundary

Structured Output is applied only where the S2 semantic contract is machine-readable:

```text
form-p2 ordinary summary   -> plain text
form-p3 semantic gist      -> plain text
form-p4 reusable rule      -> strict JSON Schema object
probe-p0 .. probe-p6       -> strict JSON Schema integer array
```

P4 schema freezes exactly:

```text
permutation: 4 unique integers in 0..3
offsets:     4 integers in 0..9
modulus:     const 10
additional properties: forbidden
```

Each target probe schema freezes exactly one four-integer array with values in `0..9`.

This keeps formatting/prose nuisance from dominating the machine-readable parts of the cognitive comparison without silently turning P2/P3 into typed IR controls.

## Effective reasoning-off gate

Every successful completion, including P2/P3, must satisfy all of:

```text
HTTP success
exactly one choice
finish_reason = stop
visible content = non-empty
reasoning / reasoning_content = absent, null, or empty
usage.completion_tokens_details.reasoning_tokens = 0
```

Any nonzero reasoning token count, non-empty reasoning payload, missing reasoning accounting, non-stop finish reason, empty visible content, provider failure, or malformed response is terminal. There is no hidden-reasoning rescue.

## Attempt accounting and no retry

The existing S2 host-v2 remains authoritative for provider work accounting:

```text
provider_attempt != provider_completion
```

A failed dispatched request still counts as physical work. Automatic retry and semantic retry remain disabled. The exact call order remains:

```text
form-p2
form-p3
form-p4
probe-p0
probe-p1
probe-p2
probe-p3
probe-p4
probe-p5
probe-p6
```

P4/P5/P6 still share one P4 formation completion; P6 remains deterministic equal-information neutralization rather than an independently generated extraction.

## Fail-closed execution boundary

`run_lmstudio_selected_s2_transaction()` requires:

- clean exact repository checkout;
- one exact loaded model instance;
- the frozen model/context/runtime class above;
- Native model identity equal to the OpenAI-compatible request model;
- a fresh repository-external empty artifact root;
- stable live model instance/context/runtime across all ten calls.

The entrypoint contains no model load, unload, reload, swap, download, context mutation, or LM Studio UI mutation.

## Current claim boundary

Merging this package establishes only:

```text
selected S2 family        = PREREGISTERED
selected LM Studio host   = PACKAGE_READY
physical S2 result        = NONE
P0-P6 physical execution  = NOT RUN
S3                         = BLOCKED
architecture consequence  = NONE
```

A later fresh physical transaction remains `NON_CITABLE_S2_SMOKE`. Even a completed mechanically discriminating smoke can only make a separate S3 preregistration eligible; it cannot itself establish Memory/Structure ontology, Cognitive IR superiority, or production architecture authority.
