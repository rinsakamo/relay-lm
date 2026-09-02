# Actual-model vLLM functional acceptance

Status: launch/runtime capability is owned by completed #1959 authority; current Stage R execution/evidence is owned by #1386, with the current final Core semantic qualification transaction owned by #2092. Numeric Cognitive Budget selection remains #1388 authority.

Stage R exists first to answer a product question:

> Does the exact current two-pass RelayLM path work end-to-end with a real model?

Capacity, token usage, latency and KV observations support that question. Transient free VRAM must not redefine the semantic/evaluation window or force RelayLM to maximize whatever memory happens to be free at one instant.

## Functional acceptance identity

Functional acceptance uses:

- the current canonical Stage R semantic plan;
- one exact target/runtime/runner launch class;
- one explicitly selected execution token window from the applicable current evaluation/calibration authority;
- stable same-launch-class memory geometry sufficient to carry that window;
- fresh host free-memory evidence only as a final feasibility check.

Keep fixed:

- target: `gemma-4-12b-it-qat-w4a16-google-vllm-v1`;
- canonical vLLM source: `70b84f0bcbb6d0a35b74b1035673a1c934089dbb` / `0.26.1rc1.dev549+g70b84f0bc`;
- execution: buffered two-pass;
- `reference_baseline`: Pass 1 reasoning OFF / Pass 2 reasoning OFF;
- decoding: `temperature=0`, `top_p=1`, `seed=null`;
- current foundation-v3 scenarios selected by the current Stage R template;
- current prompt/wire and State/Continuity/Event semantics.

The canonical vLLM runtime is the runtime bound by the frozen target/runtime proof, not whichever vLLM package happens to be installed globally.

The execution token window is **not** selected from the current free-VRAM ratio and is **not** automatically the largest window the host can fit. #1388 owns release Cognitive Budget selection. A bounded comparison/evaluation owner may bind an explicit experiment window where current authority permits that use, but must not silently promote it to a release default.

If current authority supplies no legal target window, stop on that authority gap. Do not replace it with `--max-model-len auto` merely to consume available VRAM.

## Token-capacity-based physical admission

For an already-qualified launch class, ordinary Stage R launch admission is based on the memory required to carry the selected token window.

Fresh `free_bytes` is a feasibility observation only:

```text
fresh_free_bytes >= required_total_bytes
```

Changing free VRAM above that boundary must not change:

- selected `max_model_len`;
- explicit KV-cache bytes;
- requested runtime memory envelope;
- A/B comparison semantics.

### Stable launch-class geometry

Bind a citable successful launch-capability observation for the same target/runtime/runner/host capability class containing at least:

- startup free GPU bytes from the successful launch;
- explicit KV-cache bytes used by that successful launch;
- resulting GPU KV-cache token capacity;
- target/runtime/runner identity.

A conservative reusable non-KV envelope is:

```text
reference_non_kv_bytes =
    successful_startup_free_bytes
    - successful_explicit_kv_cache_bytes
```

This is deliberately an upper-bound carriage envelope, not a claim that every byte in the difference was consumed by the model.

For a selected `target_model_len`, derive a conservative KV requirement without extrapolating beyond the attested token capacity:

```text
kv_bytes_per_token_upper =
    ceil(reference_kv_cache_bytes / reference_kv_cache_capacity_tokens)

required_kv_cache_bytes =
    target_model_len * kv_bytes_per_token_upper

required_total_bytes =
    reference_non_kv_bytes + required_kv_cache_bytes
```

`target_model_len` must be positive and must not exceed the attested KV token capacity. A larger target requires fresh launch-capability evidence rather than extrapolation.

The repository helper `VLLMTokenCapacityReference` owns this deterministic conversion. `VLLMLaunchMemoryAdmission.for_token_window(...)` combines it with fresh `free_bytes` / `total_bytes`.

### Pinned-vLLM startup guard

The pinned vLLM runtime applies `gpu_memory_utilization` as an early startup guard even when explicit `kv_cache_memory_bytes` later owns KV allocation.

Therefore RelayLM still renders an explicit `--gpu-memory-utilization`, but it is derived from `required_total_bytes / total_bytes`, **not** from `free_bytes / total_bytes`.

Its only purpose in this path is to keep pinned-vLLM's startup guard at or below the already-proven required envelope. It does not size KV and it does not expand when more VRAM happens to be free.

The final launch uses:

```text
--gpu-memory-utilization <required-envelope-derived value>
--kv-cache-memory-bytes <required_kv_cache_memory_bytes>
--max-model-len <selected target_model_len>
```

No `auto` is used for the Stage R target window.

Explicit KV bytes remain the KV-sizing authority.

If fresh free memory is below `required_total_bytes`, fail closed before launch. Do not shrink the target silently, rerun Calibration, or reinterpret the failure as a semantic defect.

### Relationship to capability profiling

The existing profiler parser remains valid for **launch-capability acquisition** when the launch-significant target/runtime/runner class changes and new memory geometry must be attested.

`python -m relaylm.actual_model_vllm_profiler --log <profiler-log>` still parses the pinned runtime's unambiguous “fully utilize GPU memory” KV recommendation for that capability transaction.

Ordinary Stage R does not repeat that maximize-free-VRAM profiler merely because desktop/WSL/driver VRAM occupancy changed.

Historical #1959 evidence remains immutable under its historical launch contract. #2033 changes how later Stage R consumes a qualified launch class; it does not rewrite the historical PASS.

## Matched comparison rule

For matched A/B execution on one host:

- use the same launch-class geometry reference;
- use the same selected target token window;
- use the same resulting explicit KV bytes;
- use the same target/runtime/runner/decoding/reasoning controls.

If fresh free VRAM differs between A and B but remains at or above the same `required_total_bytes`, the launch memory arguments remain identical.

If either side falls below the requirement, the comparison is physically inadmissible. Do not reinterpret the free-memory difference as a prompt-quality result.

## Primary acceptance question

Run the current product path and review, in this order:

1. Pass 1 conversation is coherent, Character-consistent and language-appropriate.
2. Pass 2 completes the current protocol and produces meaningful direct State/Continuity proposals.
3. State/Continuity proposals are grounded, correctly attributed and restrained.
4. correction, negation, uncertainty and no-op behavior are handled without authority corruption.
5. accepted State/Continuity affects later turns as intended.
6. assistant-authored material does not self-certify user facts or fabricated history.
7. deterministic validation, failure and stale-result behavior preserve canonical authority.

A provider-capacity failure can prevent these questions from being observed, but maximizing context capacity is not itself a functional acceptance goal.

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

Use one clean exact RelayLM checkout and an isolated environment for the canonical vLLM source runtime. Do not downgrade or otherwise mutate the user's global vLLM installation merely to satisfy the evidence identity.

Before launch:

1. bind the current legal target token window;
2. bind citable same-launch-class token/KV geometry;
3. acquire fresh host `free_bytes` / `total_bytes`;
4. build `VLLMLaunchMemoryAdmission.for_token_window(...)`;
5. fail closed if the required envelope does not fit;
6. launch the final runtime with `final_memory_args()`.

After that runtime is serving, acquire current external capacity evidence with the canonical Stage R plan:

```text
python -m relaylm.actual_model_host \
  --backend vllm \
  --operation capacity \
  --condition reference_baseline \
  ... \
  --artifact-root "$EVIDENCE_ROOT"
```

The capacity artifact records the live `observed_max_model_len`, which on this fixed-window path must reflect the explicitly selected runtime window.

Then run functional screening and bind it to that exact external evidence:

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

The normal target/runtime/counter/scenario/coverage checks still apply. The capacity artifact proves execution admission for the selected window; it does not select a release default and does not qualify product behavior by itself.

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

- fresh startup free GPU memory as environment evidence;
- launch-class non-KV reference envelope and its evidence identity;
- selected target token window;
- derived explicit KV-cache byte requirement;
- production serialized-input token count;
- provider `prompt_tokens`, `completion_tokens`, `total_tokens` and `finish_reason`;
- counter/provider delta;
- explicit reasoning-token metadata when provided;
- Pass 1 / Pass 2 / settle timing.

These measurements are useful to #1388 when their model-facing identity is eligible. Transient free-memory changes are not themselves recalibration triggers.

## Calibration handoff

#1388 selects Cognitive Budget/output-reserve/reasoning/default values from eligible token-demand and quality evidence.

The runtime/admission layer consumes a supplied selected token window and determines only whether the current host can carry it. A larger amount of free VRAM does not increase that token window. A smaller amount of free VRAM does not change Calibration identity; it is a host-carriage failure only if it falls below the required envelope.

## Deliberate boundaries

This acceptance contract does not change:

- Pass 1 / Pass 2 responsibilities;
- State / Continuity / Event-source structural semantics;
- provider parsing or `finish_reason != stop` rejection;
- primary Stage R scenario selection;
- reasoning escalation policy;
- release/runtime numeric selection ownership.

The current Pass 2 wire projects directly to `state_candidates` / `continuity_candidates`; functional acceptance must bind and review that exact current prompt/wire identity rather than reusing evidence from the retired six-field scaffold.

The focused durability fixture extends regression coverage for model-facing State projection semantics only. It does not introduce a language-specific deterministic parser, confidence field, fixed intermediate cognition axes, or new State lifecycle rule.

## Principle

> Select token demand by cognitive/evaluation authority, convert that demand to a stable physical memory requirement, and use fresh free VRAM only to answer whether the host can carry it.
