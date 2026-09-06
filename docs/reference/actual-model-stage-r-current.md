# Current Stage R execution authority

Status: current bounded execution entrypoint for RelayLM 1.0 Stage R actual-model evaluation.

Long-lived Issue history is evidence, not an execution prompt. #1386 owns actual-model evaluation authority. Backend-specific physical transactions remain separately owned.

## Current entrypoint

Use:

```text
python -m relaylm.actual_model_stage_r
```

Select the physical provider explicitly:

```text
--backend lm_studio
--backend vllm
```

The current **provider-neutral semantic descriptor** is:

```text
evaluation/actual_model/screenings/stage-r-current-v1.json
```

It freezes only the Stage R distinctions that should remain invariant across supported providers:

- foundation-v3 scenario path and exact semantic revision;
- exact current scenario IDs;
- buffered two-pass execution;
- Continuity Runtime identity;
- temperature 0 / top_p 1 / seed null;
- reasoning preference OFF;
- ordinary Pass 1 output;
- native structured Pass 2 output.

Backend-specific launch, model-file provenance and capacity machinery do not belong in this descriptor.

## Current semantic reference

The current scenario set is:

```text
evaluation/actual_model/scenario_sets/foundation-v3.json
```

with:

- `response-transcript-fidelity-v1`;
- `response-false-attribution-resistance-v1`;
- `continuity-lifecycle-v1`.

The fixture is executed exactly once per qualification transaction. Each declared ordinary turn gets at most one Pass 1 and one Pass 2 model generation; semantic retry is not part of Stage R.

Proposal scoring is scenario-owned and explicit in foundation-v3. `scored + []` means exactly zero expected proposals; `unscored` preserves raw observations while excluding that channel from FP/FN/precision/recall.

## LM Studio admission

For LM Studio, current Stage R consumes the externally managed serving condition directly rather than manufacturing a vLLM-style capacity prerequisite.

Invoke the current entrypoint with at least:

```text
--backend lm_studio
--operation screening
--condition reference_baseline
--provider-base-url http://<host>:<port>/v1
--request-model <LM Studio model key>
--repo-root <exact checkout>
--workspace-root <fresh workspace>
--artifact-root <fresh artifact root>
```

Use `--loaded-instance-id` when one request model has more than one loaded instance and an exact instance must be selected.

The LM Studio Stage R runner:

1. reads current native `/api/v1/models` metadata from the same server origin;
2. binds the requested model to one loaded instance;
3. accepts the current #2255 product-class condition, presently Gemma-4 12B with Q4-class quantization;
4. records the strongest live observable model condition, including model key, instance ID, display/parameter identity, quantization, size, effective context and exposed load/reasoning metadata;
5. uses that observed condition as run evidence rather than equality-checking one historical artifact SHA/filename/source revision;
6. executes the provider-neutral Stage R fixture through the production OpenAI-compatible two-pass provider;
7. writes generic execution evidence plus deterministic-boundary sidecars.

A compatible already-loaded model is valid input. Stage R does not require unload/reload merely to match one historical repository artifact.

Unknown optional artifact provenance is recorded as unknown rather than converted into `INCONCLUSIVE`. Routing ambiguity, incompatible model class, provider unavailability or inability to execute the actual semantic path still fail closed.

### Context

LM Studio's observed effective context is part of run identity. There is no vLLM token-capacity-reference prerequisite. If the provider cannot carry an actual Stage R request within that context, the semantic transaction fails at that real provider boundary; Stage R does not sweep context sizes after seeing results.

### Reasoning / Thinking

OFF remains the preferred reference condition.

Current LM Studio native model metadata may expose the loaded model's reasoning options/default. The Stage R run records those facts.

If the production Chat Completions path truthfully carries an explicit OFF override in future #1545 authority, that exact applied control may be used and recorded. Until then, the LM Studio Stage R runner does not invent a per-request reasoning wire. It omits the reasoning field and records the observed model/runtime default condition truthfully, for example `omitted_default_off`, `omitted_default_on`, or unknown.

A run using default ON must not be described as OFF evidence. The absence of an explicit OFF wire is not, by itself, a reason to prevent the performance experiment from executing; matched reasoning comparisons belong to separate provider/evaluation work.

### Structured output

Pass 1 remains ordinary conversation. Pass 2 still uses the exact current native JSON-schema structured-output contract. Failure of that real production path is execution evidence; there is no plain-text retry or parser-relaxation rescue.

## vLLM admission remains backend-specific

The existing descriptor:

```text
evaluation/actual_model/screenings/stage-r0-vllm-current-v1.json
```

remains the vLLM physical-admission authority. It still binds:

- fresh external capacity evidence;
- qualified `VLLMTokenCapacityReference` evidence;
- fixed-window vLLM launch/admission semantics;
- the existing vLLM execution template.

`--backend vllm` therefore preserves the previous capacity acquisition and screening contract. This work does not weaken or alias vLLM physical evidence into LM Studio.

The key separation is:

```text
Stage R semantics
  -> provider-neutral current descriptor

LM Studio physical condition
  -> observed loaded model/context + production provider path

vLLM physical condition
  -> vLLM token-capacity / launch authority
```

## Exact request and review evidence

The #2029 exact-request evidence contract continues to apply to the canonical two-pass execution path. Preserve per-turn Pass 1 / Pass 2 request records, raw model output, typed proposals and deterministic decisions where current generic execution authority requires them.

A deterministic-boundary PASS is not by itself a semantic-quality PASS. Product-quality review remains the provider-neutral `actual_model_review` / current Stage R review protocol; provider migration does not change those review dimensions.

Token/timing facts should be recorded when the provider exposes them authoritatively. Missing optional performance metadata is unknown, not a semantic failure.

## Evidence boundaries

Keep distinct:

```text
model/runtime observation
actual semantic execution
protocol/deterministic-boundary verdict
proposal scoring
human/product-quality review
timing/token observations
```

Do not transform imperfect reproducibility metadata into a substitute for running the semantic questions.

## Principle

> Freeze the semantic test and record the machine. Backend-specific admission belongs to the backend; Stage R semantics belong to RelayLM.
