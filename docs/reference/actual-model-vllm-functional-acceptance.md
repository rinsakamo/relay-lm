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
- canonical vLLM source: `70b84f0bcbb6d0a35b74b1035673a1c934089dbb` / `0.26.1rc1.dev549+g70b84f0bc`;
- execution: buffered two-pass;
- `reference_baseline`: Pass 1 reasoning OFF / Pass 2 reasoning OFF;
- decoding: `temperature=0`, `top_p=1`, `seed=null`;
- scenarios: existing `response-persona-correction-v1` and `continuity-lifecycle-v1` only;
- current prompt/wire and State/Continuity/Event semantics.

The canonical vLLM runtime is the runtime bound by the current frozen reasoning proof, not whichever vLLM package happens to be installed globally. The local `0.27.1` runtime is not an interchangeable substitute for the frozen Google W4A16 target: prior provider evidence found that target fails to start on that runtime, while the exact `70b84f0bc...` source runtime has already reproduced model-load/server readiness with runner v2 on the current host.

The execution window is bound from fresh external capacity evidence whose `observed_max_model_len` is the exact live value for the same checkout/canonical runtime.

## Hardware capability discovery

Do not treat a guessed `gpu_memory_utilization` fraction or a repository-chosen context size as hardware capability.

Use the exact canonical vLLM runtime's own memory profiler in two bounded steps:

1. **Probe.** Start the exact target on source `70b84f0bc...` with normal profiling enabled and `--max-model-len auto`. This probe exists only to obtain runtime memory facts; its configured `gpu_memory_utilization` is not the capability result.
2. **Resolve KV capacity from free VRAM.** Retain the profiler output for startup free GPU memory, weights/model memory, peak activation memory, non-Torch memory and CUDA-graph memory. The pinned runtime may present the recommendation in surrounding log prose or Markdown-like backticks and may spell the evidence token as either `--kv-cache-memory=<bytes>` or `--kv-cache-memory-bytes=<bytes>`. Treat the positive integer byte value as the evidence, not the quoting or presentation spelling. Parse the raw profiler log with `python -m relaylm.actual_model_vllm_profiler --log <profiler-log>`; the command prints the exact integer only when the log contains one unambiguous recommendation and fails closed when no recommendation or conflicting recommendations are present. Do not hand-parse this value with whitespace-sensitive `rg`/shell extraction. The canonical source contract defines explicit KV bytes as overriding `gpu_memory_utilization` for KV sizing.
3. **Final capability run.** Restart the exact same target/runtime with that parsed integer supplied through the supported final-launch `--kv-cache-memory-bytes=<bytes>` control and `--max-model-len auto`. Auto-fit then resolves the maximum model length supported by the profiled KV capacity.
4. Attest the final live `/version` and `/v1/models` identity, `max_model_len`, runner v2, model root and GPU KV-cache token capacity, and retain the exact final launch arguments/startup log.

Do not invent a fallback fraction such as 0.9 or 0.92. If the canonical runtime does not expose enough memory-profile evidence to derive or report a defensible explicit KV byte budget, stop and report the backend-capability gap instead of substituting a guessed fixed context window.

If unrelated GPU processes or display load materially change between probe and final launch, repeat the probe rather than reusing a stale byte recommendation.

The discovered maximum is a hardware/backend capability fact for this exact machine/runtime state. It is not a release/default recommendation.

## Primary acceptance question

Run the current product path and review, in this order:

1. Pass 1 conversation is coherent, Character-consistent and language-appropriate.
2. Pass 2 completes the current protocol and produces meaningful direct State/Continuity proposals.
3. State/Continuity proposals are grounded, correctly attributed and restrained.
4. correction, negation, uncertainty and no-op behavior are handled without authority corruption.
5. accepted State/Continuity affects later turns as intended.
6. assistant-authored material does not self-certify user facts or fabricated history.
7. deterministic validation, failure and stale-result behavior preserve canonical authority.

A provider-capacity failure can prevent these questions from being observed, but minimizing context capacity is not itself a functional acceptance goal.

## Focused State durability regression

`evaluation/actual_model/scenario_sets/preference-epistemic-strength-v1.json` is a focused State-proposal regression fixture for #1903. It does not replace the primary Stage R scenario plan or by itself qualify a release.

The fixture holds the ordinary State ontology and direct-candidate Pass 2 path fixed while checking two complementary surfaces:

- an English sequential contrast: tentative preference -> resolved durable preference -> temporary mood;
- the original Japanese S5 surface `たぶん紅茶のほうが好きかも。` as a black-box multilingual regression.

The Japanese sentence belongs to evaluation evidence only. It must not be copied into the model-facing State grammar, provider prompt, deterministic Validator, or language-specific phrase rules. The purpose is to test whether the language-independent State durability gate generalizes by meaning rather than by memorizing one wording.

Expected outcomes are:

```text
tentative meaning
  -> no durable State proposal

resolved durable meaning
  -> ordinary State set remains available

temporary variation with durable meaning unchanged
  -> no durable remove/replace solely from the temporary variation
```

The first #1906 real-model iteration is an explicit negative baseline for this gate: its English sequential contrast passed on both base and candidate heads, while the Japanese S5 created durable `user.preference/preferred_beverage=紅茶` on both heads in all 3 replicates. Therefore English-only success is not sufficient evidence for #1903. A candidate semantic fix must pass the Japanese black-box case without adding that Japanese wording to the prompt.

This fixture exists to detect durability/epistemic-strength regression after model-facing State grammar changes. It must be run against the exact current prompt/wire identity when claiming that tentative overcommit is improved. A repository GREEN only proves that the fixture and semantic contract are wired correctly; actual-model evidence is still required for product-quality qualification.

## Execution

Use one clean exact RelayLM checkout throughout final capability attestation, capacity acquisition and functional screening. Use an isolated environment for the canonical vLLM source runtime; do not downgrade or otherwise mutate the user's global vLLM installation merely to satisfy the evidence identity.

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
- Pass 2 protocol success and direct State/Continuity proposal quality;
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

This acceptance contract does not change:

- Pass 1 / Pass 2 responsibilities;
- State / Continuity / Event-source structural semantics;
- provider parsing or `finish_reason != stop` rejection;
- primary Stage R scenario selection;
- reasoning escalation policy;
- release/runtime defaults.

The current Pass 2 wire projects directly to `state_candidates` / `continuity_candidates`; functional acceptance must bind and review that exact current prompt/wire identity rather than reusing evidence from the retired six-field scaffold.

The focused durability fixture extends regression coverage for model-facing State projection semantics only. It does not introduce a language-specific deterministic parser, confidence field, fixed intermediate cognition axes, or new State lifecycle rule.

The capacity correction remains: **use the canonical frozen-proof vLLM runtime, profile its actual free VRAM and non-KV footprint, let that runtime resolve explicit KV bytes and maximum model length, use that live capacity for functional acceptance, then calibrate later**.

## Principle

> First establish the exact citable backend/runtime, then discover that runtime's usable GPU capacity and prove the exact current RelayLM path works there. Calibrate the product profile only after that.