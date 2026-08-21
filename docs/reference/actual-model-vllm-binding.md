# Actual-model vLLM execution binding

This reference defines the #1386-owned binding between the frozen vLLM repository-snapshot target, live vLLM/model capability authority, the canonical OpenAI-compatible provider, and one citable actual-model run manifest.

It does not define cognition policy, reasoning defaults, a new evaluation runner, or a second provider mapping. Provider semantics remain owned by #1545/#1533; this binding only proves that the already-resolved execution condition is the one actually being used by #1386.

## Canonical target

The current vLLM execution target is:

- target: `gemma-4-12b-it-qat-w4a16-vllm-v1`;
- repository artifact: `unsloth/gemma-4-12B-it-qat-w4a16@626f3b2f8a3799cb2b64ca5fc09443c90fe2cbb2`;
- target format: repository snapshot with exact required file sizes/SHA-256 values;
- serving tokenizer and chat-template roles are part of the frozen target identity.

Before a run may be cited, `verify_actual_model_repository_snapshot(...)` must verify the local snapshot and the resulting verification must bind to the exact target revision and full frozen file count.

## Runtime/capability authority

The binding consumes `VLLMReasoningCapabilityAttestation` rather than inferring capability from model names or request acceptance.

That attestation already binds:

- backend `vllm` and exact version;
- request/served model identity from `/version` and `/v1/models`;
- live `model_root` and `max_model_len` when reported;
- exact frozen target/repository revision;
- reasoning parser and template thinking control;
- separately classified OFF and numeric bounded reasoning controls;
- protocol acceptance, semantic effect, repeatability, and ambiguity facts.

For the current canonical path, both OFF and bounded capability must be `semantically_attested`. `low`/`medium`/`high` effort labels are not numeric bounded substitutes and are not a COGP5 product-quality axis.

## Fail-before-generation binding

`bind_vllm_execution_condition(...)` rejects the run before scenario generation unless all of the following agree:

1. repository-snapshot verification target ID/revision and verified file count match the frozen target;
2. reasoning capability target ID/revision, model artifact identity, and repository revision match the same target;
3. the live vLLM `model_root` resolves to the verified snapshot root;
4. live `max_model_len`, the configured context window, and the manifest effective context window agree;
5. the provider carries the exact same `VLLMReasoningCapabilityAttestation` that the binding cites;
6. provider model and attested request model agree;
7. manifest provider/adapter/model/tokenizer/decoding/capability/seed identity agrees with the constructed provider and target;
8. the manifest contains explicit #1562 cognition pass-request identity;
9. current COGP5 request evidence uses the buffered execution path.

The manifest `provider_identity` is a deterministic secret-free serialization of the exact vLLM reasoning capability attestation. The binding sidecar also keeps that capability separately visible; a requested reasoning value is never promoted to applied capability by the evidence layer.

## Execution reuse

`run_vllm_actual_model_scenario_definition(...)` does not create a parallel evaluation architecture. After binding succeeds it calls the existing `run_actual_model_scenario_definition(...)` path unchanged.

The canonical OpenAI-compatible provider remains responsible for turning the #1562 `CognitionPassRequest` into the #1558 vLLM wire realization. Therefore:

```text
#1386 scenario + explicit pass request identity
        -> existing actual-model scenario harness
        -> existing Turn single-pass/two-pass path
        -> canonical OpenAI-compatible provider
        -> #1558 vLLM reasoning realizer
        -> exact vLLM request
```

A completed condition-bound result can be persisted as immutable `<execution_id>.vllm.json`. Same-ID/different-evidence replacement is rejected and requires a distinct replicate identity.

## COGP5 screening boundary

The intended first vLLM product-quality screening remains serial and hypothesis-driven:

```text
A: single_pass
   reasoning = off

B: two_pass
   Pass 1 = off
   Pass 2 = off

C: two_pass
   Pass 1 = off
   Pass 2 = bounded(16)
```

`bounded(64)` is eligible only if the first bounded comparison shows a meaningful product/budget difference that justifies deeper screening. Do not add `low`/`medium`/`high`, invalid-wire probes, streaming permutations, parser permutations, or template-conflict permutations to the product-quality matrix; those are provider capability/conformance evidence rather than product conditions.

The machine-readable `evaluation/actual_model/screenings/cogp5-vllm-screening-v1.json` is now historical pre-capacity-calibration evidence. It retains A/B/C, two representative foundation-v2 scenarios, and its historical diagnostic `effective_context_window=1024`, but it has no `capacity_evidence_id` and therefore cannot pass canonical host preparation.

A future revised screening plan may preserve the same A/B/C hypotheses only after it cites explicit capacity evidence. If it preserves the same two scenarios, one full A/B/C tranche would still consist of two scenario executions per condition and six total scenario executions. That count is a plan shape, not evidence that those executions have occurred.

The historical plan's `continuity_runtime = {max_items: 8, lifetime_revisions: 4}` remains an explicit evidence condition only. It is not a #1388 default and must not be promoted into release configuration by this lane.

## Capacity-evidence gate

`VLLMScreeningPlan.capacity_evidence_id` is optional for loading historical evidence but mandatory for canonical preparation. A non-empty string alone is not sufficient. The ID must resolve to a strict immutable `VLLMRuntimeCapacityEvidence` artifact before repository verification, snapshot verification, live backend/model acquisition, provider construction, or generation can proceed.

Reviewed repository capacity artifacts use the convention:

```text
evaluation/actual_model/capacity/<amcap-evidence-id>.json
```

Host tests or acquisition tooling may supply another explicit artifact root, but the evidence file still uses the same content-addressed identity and strict loader.

A capacity evidence record contains only content-free facts:

- RelayLM measurement commit as provenance;
- exact target ID/revision;
- frozen serving-tokenizer and chat-template identities;
- vLLM backend version and request-model identity;
- observed live `max_model_len`;
- exact scenario-set revision used for measurement;
- the exact `SerializedInputCounterIdentity` used for measurement;
- one or more footprint observations identified by canonical screening-condition ID, topology, pass, scenario, turn index, and content-free exact pass-request identity;
- total serialized-input tokens, framing tokens, and count mode for each footprint;
- optionally, an independently observed input-context-overflow condition with configured capacity, observed input tokens, HTTP status, and failure classification.

The exact pass-request identity is `amcpr-<sha256>` over the canonical resolved `CognitionPassRequest` fields (`reasoning_mode`, `reasoning_budget`, `temperature`, `top_p`, and `max_output_tokens`). It contains no prompt or message text. This keeps otherwise similar footprints distinct when their actual per-pass request semantics differ, including B Pass 2 OFF versus C Pass 2 bounded(16).

It does not persist prompt text, message content, State/Continuity values, MEMORY/Event text, API keys, provider URLs, or model output.

The evidence ID is `amcap-<sha256>` over canonical artifact contents excluding the ID field itself. The writer is immutable: identical re-writes are idempotent, while same-ID/different-bytes replacement is rejected. The loader reconstructs the typed record and recomputes the ID before the artifact can be cited. Duplicate footprint coverage identities are rejected rather than collapsed.

Before screening preparation proceeds, the cited artifact must additionally satisfy all of these checks:

1. the plan's `capacity_evidence_id` exactly equals the artifact's recomputed ID;
2. the selected `effective_context_window` is strictly greater than the largest cited serialized-input footprint;
3. that window does not exceed the evidence's attested runtime capacity;
4. target ID/revision, tokenizer identity, and chat-template identity match the current frozen repository target;
5. backend version, request model, and observed runtime capacity match fresh live vLLM re-attestation;
6. reconstructing the current `VLLMServingTokenizerCounter` from the fresh target/runtime produces the exact counter identity cited by the artifact;
7. the artifact's scenario-set revision exactly matches the canonical scenario set used by the selected screening plan;
8. the artifact contains every required scenario/turn/pass footprint for the selected condition, with the exact canonical condition ID and exact resolved pass-request identity.

Coverage is reconstructed deterministically from the selected `VLLMScreeningCondition` and the frozen scenario set. A, B Pass 1, B Pass 2, C Pass 1, and C Pass 2 remain distinct coverage coordinates even when two resolved requests are otherwise equal. Missing, stale, duplicate, or mismatched coverage fails before provider construction and therefore before generation.

The measurement commit is retained as provenance, not required to equal the later screening commit. A reviewed evidence artifact may therefore be committed and referenced by a later screening plan without pretending the measurement occurred at that later commit. Semantic staleness is instead rejected through the frozen target, serving-tokenizer/chat-template, backend/model, runtime-capacity, counter-identity, scenario-set revision, and exact pass-request coverage checks above.

The capacity artifact does not select a numeric value. `validate_capacity_window(...)` only proves whether a caller-selected window resolves the cited serialized-input floor and remains inside the attested live capacity. #1388 remains the owner of choosing any evidence-resolving candidate/profile/default.

The historical 1024 value is therefore neither deleted nor promoted: it remains the identity of the failed diagnostic condition that motivated capacity-first calibration.

## Exact serving-tokenizer footprint counting

`src/relaylm/actual_model_vllm_counter.py` provides a host-only `VLLMServingTokenizerCounter` for current Pass 1/Pass 2 footprint evidence. It plugs directly into the existing `OpenAICompatibleTwoPassSerializedInputCounter`; it does not rebuild RelayLM prompts or introduce a second provider serializer.

The count path is:

```text
current production Pass request
  -> canonical OpenAI-compatible request builder
  -> model-input mapping (transport-only stream already removed)
  -> VLLMServingTokenizerCounter
  -> live vLLM /tokenize chat renderer + frozen serving tokenizer
  -> exact SerializedInputTokenCount
```

The counter accepts only the current plain role/content message shape and the current provider fields needed for the frozen product path. Generation-only controls such as `temperature`, `top_p`, `seed`, structured-output `response_format`, and `thinking_token_budget` are recognized as production request controls but are not copied into the `/tokenize` request because they do not define the rendered chat prompt.

Chat-template controls are preserved according to the live vLLM chat-serving semantics used by the frozen path:

- an explicit `chat_template_kwargs` mapping is passed to `/tokenize`;
- current RelayLM OFF wire `reasoning_effort = none` is represented in effective chat-template kwargs and supplies `enable_thinking = false` when the request did not explicitly override it;
- current bounded reasoning requires the already-resolved explicit `enable_thinking = true` template control;
- unsupported effort values, conflicting OFF/enable controls, missing bounded activation, unknown top-level model-input fields, non-plain message shapes, target/model drift, and `max_model_len` drift fail closed.

Both total prompt count and required framing attribution come from the same live renderer. Framing uses the same ordered message roles and template controls with every message content replaced by the empty string. This is a content-free accounting baseline only; it does not redefine Identity, State, Context, or Event semantics.

`SerializedInputCounterIdentity` records the exact target/tokenizer/chat-template identities, vLLM backend version, request model, renderer/framing methods, and observed context limit without persisting the base URL, API key, message text, or other secrets.

This counter produces footprint evidence only. A token count does not itself prove a usable runtime capacity, choose an output reserve, or authorize COGP5 execution.

## Frozen R3B proof and live re-attestation

The provider-owned R3B capability probe is not repeated as a product-quality prelude. Its effective facts are frozen in `evaluation/actual_model/attestations/gemma-4-12b-it-qat-w4a16-vllm-reasoning-v1.json`, with provenance back to #1545 comment `5357159619`.

The proof retains only controls needed by the first screening:

- OFF: `reasoning_effort = none`, semantically effective and repeatable;
- bounded: `thinking_token_budget = 16` with `enable_thinking = true`, semantically effective and repeatable.

It deliberately does not turn `low|medium|high`, invalid effort, budget-without-activation, or OFF/template conflict into product conditions. It also does not freeze `bounded(64)` into the first-stage plan.

At each real host execution, `acquire_vllm_reasoning_capability(...)` reacquires only the live backend/model identity from `/version` and `/v1/models`, then combines that current identity with the frozen R3B probe facts through the existing provider-owned attestation constructor. A vLLM version mismatch, served-model ambiguity, target mismatch, snapshot mismatch, `model_root` mismatch, or `max_model_len` mismatch fails before generation. This is runtime identity re-attestation, not a new reasoning-parameter sweep.

## Host orchestration and serial execution

`src/relaylm/actual_model_vllm_host.py` owns the vLLM host preparation adapter. It first resolves and validates the cited capacity artifact, then verifies the exact repository snapshot, reacquires live backend identity, reconstructs the current serving-tokenizer counter identity, validates exact scenario/pass-request coverage for the selected condition, constructs the canonical single-pass or two-pass OpenAI-compatible provider with the same typed vLLM reasoning capability, creates the #1562 run manifest, and obtains the #1563 binding before any scenario generation.

The public host entry point is the thin common facade `python -m relaylm.actual_model_host`. It only selects the backend adapter:

```text
actual_model_host
  --backend lm_studio -> existing actual_model_host_runner unchanged
  --backend vllm      -> actual_model_vllm_host preparation/execution
```

The facade does not reinterpret the historical LM Studio condition format. It strips only the backend selector and delegates the remaining LM Studio arguments to the existing runner.

For a future capacity-evidence-bound vLLM plan, one invocation executes exactly one of `A | B | C` over that plan's frozen scenarios. A, B, and C must therefore be invoked serially. The facade does not accept an `all` condition and does not generate a parameter Cartesian product.

A successful vLLM invocation reports the selected condition, exact RelayLM commit, target ID, replicate ID, and immutable result/boundary artifact paths. Raw provider API-key material is never emitted in the summary or evidence identity.

## Deliberate boundary

The host orchestration consumes already-obtained reasoning probe facts; it does not itself repeat the R3B parameter experiment. It reacquires current backend/model identity only so stale capability evidence cannot be cited against a different live vLLM runtime.

The serving-tokenizer counter and capacity artifact contract likewise perform no generation and select no runtime capacity. No actual-model A/B/C execution, quality conclusion, calibration decision, or runtime default is created merely by these contracts. Product evidence begins only after real current-footprint evidence exists, #1388 selects an evidence-resolving runtime condition, and a revised plan is explicitly authorized for the exact live vLLM server and verified snapshot.
