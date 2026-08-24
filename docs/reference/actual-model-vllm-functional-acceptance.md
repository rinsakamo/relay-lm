# Actual-model vLLM functional acceptance

Status: current #1865 correction under #1386 actual-model product-quality authority.

Stage R exists first to answer a product question:

> Does the exact current two-pass RelayLM path work end-to-end with a real model?

Capacity, token usage, latency, KV reuse and numeric profile selection are supporting observations. They must not become prerequisites that delay or replace the functional-quality question. Numeric/default selection remains downstream #1388 work.

## Functional acceptance identity

The repository-owned roomy functional-acceptance plan is:

`evaluation/actual_model/screenings/stage-r0-vllm-functional-acceptance-v1.json`

It preserves the current Stage R two-pass semantics while giving generation enough room to complete:

- target: `gemma-4-12b-it-qat-w4a16-google-vllm-v1`;
- effective context window: `4096` tokens;
- execution: buffered two-pass;
- `reference_baseline`: Pass 1 reasoning OFF / Pass 2 reasoning OFF;
- decoding: `temperature=0`, `top_p=1`, `seed=null`;
- scenarios: existing `response-persona-correction-v1` and `continuity-lifecycle-v1` only;
- no committed capacity citation: fresh external capacity evidence is used only to prove this selected execution can run without truncation.

The `4096` value is a roomy test condition, not a release/default proposal and not the Stage R success criterion.

## Primary acceptance question

Run the current product path and review, in this order:

1. Pass 1 conversation is coherent, Character-consistent and language-appropriate.
2. Pass 2 completes the current protocol and produces meaningful subjective interpretation/proposals.
3. State/Continuity proposals are grounded, correctly attributed and restrained.
4. correction, negation, uncertainty and no-op behavior are handled without authority corruption.
5. accepted State/Continuity affects later turns as intended.
6. assistant-authored material does not self-certify user facts or fabricated history.
7. deterministic validation, failure and stale-result behavior preserve canonical authority.

A provider-capacity failure can prevent these questions from being observed, but minimizing context capacity is not itself a functional acceptance goal.

## Execution

The common vLLM host defaults to the canonical Stage R reference plan when `--screening-plan` is omitted. Functional acceptance explicitly selects the roomy plan:

```text
--screening-plan evaluation/actual_model/screenings/stage-r0-vllm-functional-acceptance-v1.json
```

Run the exact attested vLLM/model trajectory with `max_model_len=4096` on one clean exact RelayLM checkout.

Acquire fresh external capacity evidence only as the preflight needed to execute the same selected plan without truncation:

```text
python -m relaylm.actual_model_host \
  --backend vllm \
  --operation capacity \
  --condition reference_baseline \
  --screening-plan evaluation/actual_model/screenings/stage-r0-vllm-functional-acceptance-v1.json \
  ... \
  --artifact-root "$EVIDENCE_ROOT"
```

Without changing the checkout, use that exact evidence for the functional screening:

```text
python -m relaylm.actual_model_host \
  --backend vllm \
  --operation screening \
  --condition reference_baseline \
  --screening-plan evaluation/actual_model/screenings/stage-r0-vllm-functional-acceptance-v1.json \
  ... \
  --capacity-evidence-id "$CAPACITY_EVIDENCE_ID" \
  --capacity-evidence-root "$EVIDENCE_ROOT"
```

The capacity artifact is an execution admission artifact. Passing it does not qualify product behavior; the completed semantic/functional run does.

## Functional evidence first

The first completed OFF/OFF run should primarily report:

- Pass 1 response quality and unsupported/fabricated-history defects;
- Pass 2 protocol success and six-field cognition/proposal quality;
- StateCandidate / ContinuityCandidate grounding and source correctness;
- deterministic accept/reject/materialization results;
- resulting State/Continuity and next-turn effects;
- no-op, correction, unresolved and continuity lifecycle behavior.

Pass 2 reasoning escalation remains conditional on completed OFF/OFF semantic evidence demonstrating a real quality need. It is not triggered by capacity, latency or the availability of a reasoning control.

## Incidental measurements

During the same run, retain token/timing observations when already available:

- production serialized-input token count;
- provider `prompt_tokens`, `completion_tokens`, `total_tokens` and `finish_reason`;
- counter/provider delta;
- explicit reasoning-token metadata when provided;
- Pass 1 / Pass 2 / settle timing;
- exact live `max_model_len` and model-runner identity.

These measurements are useful inputs to #1388 after the product path is functionally acceptable. They are not the reason to run Stage R.

## Calibration handoff

Only after functional qualification should #1388 decide the release capacity/output reserve, reasoning policy and other numeric defaults from successful evidence.

A successful 4096 run does not imply a 4096 default. Conversely, Stage R should not repeatedly squeeze the prompt into the historical 1616 pilot window merely to perform calibration before product behavior is known.

## Deliberate boundaries

This correction does not change:

- Pass 1 / Pass 2 responsibilities;
- the six-field Pass 2 cognition scaffold;
- State / Continuity / Event-source semantics;
- provider parsing or `finish_reason != stop` rejection;
- semantic scenarios or expected labels;
- reasoning escalation policy;
- runtime defaults or operator configuration.

It changes the critical-path priority only: **functional product behavior first, calibration second**.

## Principle

> First prove that RelayLM works as a product under a roomy valid execution condition. Then calibrate how small and fast that qualified path can be.
