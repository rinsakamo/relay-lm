# RelayLM 2.0 — Cognitive IR calibration physical host

This document defines the fail-closed physical host package for the #2211 pre-S2 calibration.

It does not change the already-merged calibration matrix. It packages exactly one physical
execution of that matrix with fresh repository/provider authority and durable non-citable artifacts.

## Boundary

Environment authority and test inference use different interfaces:

```text
LM Studio native API
  GET /api/v1/models
  -> unique loaded model key
  -> unique loaded instance id
  -> loaded context length
  -> architecture / format / quantization / selected variant
  -> public reasoning capability/default when exposed

OpenAI-compatible API
  POST /v1/chat/completions
  -> all 72 calibration model calls
  -> response_format.type = json_schema
  -> strict JSON Schema structured output
```

The physical host never uses `/api/v1/chat` to answer calibration probes.

## Frozen transport

The default LM Studio calibration client remains:

```text
api               = openai-chat-completions-json-schema-v1
structured_output = true
temperature       = 0.0
max_tokens        = 128
seed              = null
timeout_seconds   = 300
```

No undocumented reasoning field is added to Chat Completions. The native model-listing response is
used to record the model's exposed reasoning capability/default as runtime identity. This is an
execution condition, not a scientific variable selected after results.

## Physical identity

Before the first model call, freeze:

```text
repository.commit
repository.tree
repository.clean_required = true

model
model_instance_id
context_length
runtime
transport

retry_policy.automatic_retry = false
retry_policy.semantic_retry  = false

live_binding_fields =
  model
  model_instance_id
  context_length
  runtime

call_plan = exact deterministic 72-call plan
```

Secret-bearing keys are rejected from persisted identity.

The artifact root must be fresh, empty, repository-external storage.

## Live binding

`probe_lmstudio_native_calibration_binding()` performs no model generation. It calls
`GET /api/v1/models`, requires one exact model-key match and exactly one loaded instance, then
returns the live model/instance/context/runtime binding.

The host performs this probe:

1. once at preflight;
2. immediately before every structured provider call.

Any drift terminates the transaction before the next model call.

## Call discipline

The call order is derived only from the merged calibration contract:

```text
for difficulty in CALIBRATION_DIFFICULTIES:
  for seed in CALIBRATION_SEEDS:
    C0_APPLICATION_ONLY
    C1_FORMATION_ONLY
    C2_END_TO_END
```

Total:

```text
4 * 6 * 3 = 72 provider calls
```

No early stop, provider retry, semantic retry, seed replacement, parser repair, prompt repair or
result-dependent difficulty change is allowed.

## Accounting

`provider_attempts` counts physical requests before dispatch.
`provider_completions` counts successful provider responses accepted by the client.

Therefore a first-request provider failure is:

```text
provider_attempts    = 1
provider_completions = 0
```

Binding drift before request dispatch does not count as a provider attempt.

## Durable artifacts

A fresh transaction writes:

```text
run-manifest.json
run-state.json
request-evidence.jsonl
calibration-result.json   # completed runs only
```

`request-evidence.jsonl` stores only bounded non-citable instrumentation for each completed
exchange: deterministic question id, response id, input/output tokens and structured content.

On a terminal provider/binding/protocol failure, `run-state.json` is rewritten to `INCOMPLETE` and
the detached artifact is preserved. No automatic retry occurs.

On success, `calibration-result.json` records the existing matrix result, plus run id, identity
fingerprint and truthful attempt/completion accounting.

## Claim boundary

Every result remains:

```text
claim_status = NON_CITABLE_S2_CALIBRATION
citable      = false
```

A selected difficulty only authorizes a separate fresh S2 preregistration transaction.
It does not compare P0-P6, open S3, prove Cognitive IR efficacy or change architecture.

## Intended LM Studio host procedure

For the current Gemma campaign, a host may use native model-management endpoints to establish the
requested model/context before freezing identity. Environment construction is outside the
calibration model-call budget.

After construction:

1. call `GET /api/v1/models`;
2. freeze the returned unique loaded binding;
3. build `OpenAICompatibleStructuredCalibrationClient`;
4. freeze its exact `transport_identity`;
5. create a fresh external artifact root;
6. call `run_calibration_host(...)` once;
7. reconcile the terminal result to #2211.

If environment construction changes the loaded instance, all live binding values are reacquired
after construction. Historical instance/config values are never reused as current authority.
