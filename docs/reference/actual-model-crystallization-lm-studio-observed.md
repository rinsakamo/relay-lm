# Observed-condition LM Studio crystallization qualification

This entrypoint exists for the RelayLM 1.0 final-Core qualification path where LM Studio is an externally managed reference backend and the physical model is treated as an **observed experimental condition** rather than a frozen repository artifact that must be re-proven before every semantic generation.

It does not replace the exact-provenance `actual_model_crystallization_host_runner`. That runner remains available when a transaction explicitly requires local artifact-byte and serving-proof attestation.

## Entrypoint

```bash
python -m relaylm.actual_model_crystallization_lm_studio_observed \
  --repo-root /path/to/clean/relay-lm \
  --provider-base-url http://192.168.50.26:1234/v1 \
  --request-model google/gemma-4-12b \
  --workspace-root /fresh/workspace \
  --artifact-root /fresh/evidence
```

When one request model has multiple loaded instances, add:

```text
--loaded-instance-id <exact instance id>
```

For #2255 Phase B, pass the `model_observed_identity` emitted by Phase A Stage R:

```text
--expected-model-observed-identity <lmstudio-observed:sha256:...>
```

A mismatch fails closed before Crystallization generation. This is the Phase A -> Phase B same-model-condition gate.

## What is fixed

The semantic/product test remains the canonical current crystallization quality fixture:

```text
fixture: evaluation/actual_model/characters/crystallization-quality-v1
case_id: crystallization-consolidation-quality-v1
case_version: 1
max_events: 7
```

The runner verifies the repository fixture bytes against the repository-owned revision file before execution. It uses the current production `OpenAICompatibleCrystallizer`, current structured-output schema, current `CrystallizationInput`, `MemoryUnit[]`, `StateCandidate[]`, deterministic Validator, State authority and MEMORY projection.

One invocation performs exactly one crystallizer generation. There is no semantic retry, parser relaxation, prompt repair, model substitution or decoding sweep.

## What is observed and recorded

The runner reads the live LM Studio native model inventory and binds the requested model to one unambiguous loaded instance. Current #2255 admission accepts Gemma-4 12B with Q4-class quantization.

Evidence records the observed condition, including available:

- request-model key;
- loaded instance ID;
- display / parameter identity;
- quantization;
- model size;
- effective context length;
- flash-attention / KV-offload load configuration;
- reasoning allowed options and default;
- a content-addressed `model_observed_identity` over those observations.

Historical model artifact SHA, filename, repository revision and separately manufactured LM Studio serving-proof files are **not** required by this observed-condition path.

## Reasoning

No request-time reasoning field is invented. The current crystallizer Chat Completions request omits such a control.

If LM Studio exposes a reasoning default, the evidence records that default as the effective omitted-wire condition. If native reasoning metadata is unavailable, the evidence records `unknown` rather than fabricating OFF or ON.

OFF may remain the preferred comparison condition elsewhere, but a missing request-time OFF carriage does not by itself consume the Crystallization quality experiment before generation.

## Evidence boundary

The runner writes:

- `lm-studio-crystallization-model-observation.json`;
- the existing immutable CRY2 `<run_id>.json` semantic evidence;
- `crystallization-lm-studio-observed-summary.json`.

A successful invocation is still not a seven-axis product-quality PASS. Review the raw output and deterministic results under the existing crystallization review contract.

## Principle

> Freeze the semantic case. Observe and record the model condition. Do not spend the semantic test proving a filename.
