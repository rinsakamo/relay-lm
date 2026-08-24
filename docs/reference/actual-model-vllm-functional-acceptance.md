# Actual-model vLLM functional acceptance

Status: current #1863 transaction under #1386 actual-model product-quality authority.

Stage R exists first to answer a product question:

> Does the exact current two-pass RelayLM path work end-to-end with a real model?

Capacity, token usage, latency, KV reuse and numeric profile selection are supporting observations. They must not become prerequisites that delay or replace the functional-quality question. Numeric/default selection remains downstream #1388 work.

## Functional acceptance identity

Functional acceptance uses the current canonical Stage R semantic plan and the exact live vLLM capacity discovered for the test machine.

There is no repository-owned fixed functional-test context window.

Keep fixed:

- target: `gemma-4-12b-it-qat-w4a16-google-vllm-v1`;
- execution: buffered two-pass;
- `reference_baseline`: Pass 1 reasoning OFF / Pass 2 reasoning OFF;
- decoding: `temperature=0`, `top_p=1`, `seed=null`;
- scenarios: existing `response-persona-correction-v1` and `continuity-lifecycle-v1` only;
- current prompt/wire and State/Continuity/Event semantics.

The execution window is bound from fresh external capacity evidence whose `observed_max_model_len` is the exact live vLLM value for the same checkout/runtime.

## Hardware capability discovery

Do not treat a guessed `gpu_memory_utilization` fraction or a repository-chosen context size as hardware capability.

Use the exact installed vLLM build's own memory profiler in two bounded steps:

1. **Probe.** Start the exact target once with normal profiling enabled and `--max-model-len auto`. This probe exists only to obtain the runtime memory facts; its configured `gpu_memory_utilization` is not the capability result.
2. **Resolve KV capacity from free VRAM.** Retain the profiler output for startup free GPU memory, weights/model memory, peak activation memory, non-Torch memory and CUDA-graph memory. When the installed build emits its recommended `--kv-cache-memory=<bytes>` value for fully utilizing GPU memory, use that exact recommendation. That recommendation is derived from the observed startup free memory minus profiled non-KV consumption and vLLM's own redundancy buffer, rather than from a RelayLM-owned percentage.
3. **Final capability run.** Restart the exact same target with that explicit `--kv-cache-memory=<bytes>` and `--max-model-len auto`. The explicit KV byte budget makes `gpu_memory_utilization` irrelevant to KV-cache sizing; auto-fit then resolves the maximum model length supported by that profiled KV capacity.
4. Attest the final live `/v1/models` `max_model_len` and retain the final GPU KV-cache token capacity/startup log. That resolved `max_model_len` is the functional-test execution capability.

Do not invent a fallback fraction such as 0.9 or 0.92. If the exact installed vLLM build does not expose enough memory-profile evidence to derive or report the full-GPU KV byte budget, stop and report the backend-capability gap instead of substituting a guessed fixed context window.

If unrelated GPU processes or display load materially change between probe and final launch, repeat the probe rather than reusing a stale byte recommendation.

The discovered maximum is a hardware/backend capability fact for this exact machine/runtime state. It is not a release/default recommendation.

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

Use one clean exact RelayLM checkout throughout final capability attestation, capacity acquisition and functional screening.

After the final capability run is serving, acquire fresh external capacity evidence with the canonical Stage R plan. Capacity acquisition already binds to the live attested `max_model_len`; the canonical plan's historical pilot window does not select the acquisition runtime.

```text
python -m relaylm.actual_model_host \
  --backend vllm \
  --operation capacity \
  --condition reference_baseline \
  ... \
  --artifact-root "$EVIDENCE_ROOT"
```

The resulting capacity artifact records the exact live `observed_max_model_len`.

Without changing the checkout or final vLLM runtime, run functional screening and explicitly bind the screening context window to that same external evidence:

```text
python -m relaylm.actual_model_host \
  --backend vllm \
  --operation screening \
  --condition reference_baseline \
  --context-window-from-capacity-evidence \
  ... \
  --capacity-evidence-id "$CAPACITY_EVIDENCE_ID" \
  --capacity-evidence-root "$EVIDENCE_ROOT"
```

The normal target/runtime/counter/scenario/coverage checks still apply. The flag does not weaken capacity validation; it only replaces the canonical pilot window with the exact `observed_max_model_len` from the supplied fresh evidence before the normal screening preflight runs.

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

- startup free GPU memory and profiled non-KV memory components;
- the resolved explicit KV-cache byte budget used for the final capability run;
- final GPU KV-cache token capacity and live `max_model_len`;
- production serialized-input token count;
- provider `prompt_tokens`, `completion_tokens`, `total_tokens` and `finish_reason`;
- counter/provider delta;
- explicit reasoning-token metadata when provided;
- Pass 1 / Pass 2 / settle timing.

These measurements are useful inputs to #1388 after the product path is functionally acceptable. They are not the reason to run Stage R.

## Calibration handoff

Only after functional qualification should #1388 decide the release capacity/output reserve, reasoning policy and other numeric defaults from successful evidence.

A large discovered hardware capability does not imply a large release default. Conversely, Stage R should not repeatedly squeeze the prompt into the historical 1616 pilot window merely to perform calibration before product behavior is known.

## Deliberate boundaries

This correction does not change:

- Pass 1 / Pass 2 responsibilities;
- the six-field Pass 2 cognition scaffold;
- State / Continuity / Event-source semantics;
- provider parsing or `finish_reason != stop` rejection;
- semantic scenarios or expected labels;
- reasoning escalation policy;
- release/runtime defaults.

It changes only how the functional-test execution window is selected: **profile the actual free VRAM and non-KV footprint, let vLLM resolve an explicit KV byte budget and maximum model length, use that live capacity for functional acceptance, then calibrate later**.

## Principle

> First discover the machine's usable vLLM capacity from its actual memory profile, then prove RelayLM works there. Calibrate the product profile only after that.
