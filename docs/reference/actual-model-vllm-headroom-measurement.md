# Actual-model vLLM headroom measurement

Status: current #1863 bounded measurement contract under #1386 actual-model evidence authority.

This contract exists to measure a successful current-wire two-pass trajectory with enough generation room to avoid the former Stage R pilot-window truncation. It does **not** define a Core 1.0 runtime default or release profile; numeric selection remains #1388 authority.

## Measurement identity

The repository-owned measurement plan is:

`evaluation/actual_model/screenings/stage-r0-vllm-headroom-measurement-v1.json`

It preserves the canonical Stage R reference semantics and differs intentionally in measurement identity and effective context capacity:

- target: `gemma-4-12b-it-qat-w4a16-google-vllm-v1`;
- effective context window: `4096` tokens;
- execution: buffered two-pass;
- `reference_baseline`: Pass 1 reasoning OFF / Pass 2 reasoning OFF;
- decoding: `temperature=0`, `top_p=1`, `seed=null`;
- scenarios: `response-persona-correction-v1` and `continuity-lifecycle-v1`;
- no committed capacity citation: fresh external capacity evidence is required before screening.

The `4096` window is a roomy measurement workbench chosen to observe complete provider output. It is not a proposed default and must not be copied into release configuration merely because the run succeeds.

## Host selection

The common vLLM host defaults to the canonical Stage R reference plan when `--screening-plan` is omitted.

A bounded repository-owned measurement plan may be selected explicitly with a repository-relative path:

```text
--screening-plan evaluation/actual_model/screenings/stage-r0-vllm-headroom-measurement-v1.json
```

The selector rejects absolute paths and paths that resolve outside `repo_root`. Selecting a plan does not mutate the committed canonical plan.

## Required execution order

Run the exact attested vLLM/model trajectory with `max_model_len=4096`, then on one clean exact RelayLM checkout:

```text
python -m relaylm.actual_model_host \
  --backend vllm \
  --operation capacity \
  --condition reference_baseline \
  --screening-plan evaluation/actual_model/screenings/stage-r0-vllm-headroom-measurement-v1.json \
  ... \
  --artifact-root "$EVIDENCE_ROOT"
```

Acquire the content-addressed capacity evidence ID from that result. Without changing the checkout, consume that exact external evidence for screening:

```text
python -m relaylm.actual_model_host \
  --backend vllm \
  --operation screening \
  --condition reference_baseline \
  --screening-plan evaluation/actual_model/screenings/stage-r0-vllm-headroom-measurement-v1.json \
  ... \
  --capacity-evidence-id "$CAPACITY_EVIDENCE_ID" \
  --capacity-evidence-root "$EVIDENCE_ROOT"
```

External capacity evidence keeps exact measurement-commit binding. Do not acquire on one commit and screen another.

## What to measure

The fresh capacity artifact already supports content-free provider completion observations where available. For every reached pass/turn retain:

- production serialized-input token count;
- provider `prompt_tokens`;
- provider `completion_tokens`;
- provider `total_tokens`;
- `finish_reason`;
- explicitly reported reasoning tokens, preserving null as unknown;
- selected layer occupancy and any deterministic degradation evidence;
- exact live `max_model_len` and model-runner identity.

Screening then supplies the existing semantic and timing evidence. Pass 2 semantic quality is rateable only after complete protocol-successful output; `finish_reason=length` remains a capacity failure, not a semantic score.

## Calibration handoff

After a successful measurement, #1388 derives candidate capacity/output-reserve values from the observed successful trajectory, including:

```text
max successful prompt requirement
+ max successful completion requirement
+ explicit safety margin
```

Any stable difference between the production serialized-input counter and provider `usage.prompt_tokens` must be accounted for near a capacity boundary.

Do not preserve 4096 by default merely because it completed. Conversely, do not force the current wire back into the historical 1616 pilot window if doing so would conflate prompt optimization with capacity calibration.

## Deliberate boundaries

This measurement does not change:

- the canonical `stage-r0-vllm-reference-v2` plan or default host selection;
- Pass 1 / Pass 2 responsibilities;
- the six-field Pass 2 cognition scaffold;
- State / Continuity / Event-source semantics;
- provider parser or `finish_reason != stop` rejection;
- reasoning policy;
- semantic scenarios or expected labels;
- runtime defaults or operator configuration.

Pass-2 reasoning escalation remains conditional on completed OFF/OFF semantic evidence demonstrating a need.

## Principle

> First observe the complete successful trajectory with ample room; then calibrate the smallest sensible release profile from that evidence.