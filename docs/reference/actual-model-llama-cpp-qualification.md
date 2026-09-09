# llama.cpp / llama-server actual-model qualification

Status: current RelayLM 1.0 physical-qualification carriage for the operator-selected local llama.cpp condition. Owner: #2409. The provider-neutral Stage R semantics remain owned by #1386 and `docs/reference/actual-model-stage-r-current.md`.

## Scope

This surface exists to run RelayLM's current actual-model Stage R on one explicitly attested external `llama-server` condition. It is an evaluation/laboratory boundary, not a new production Cognitive Profile routing key and not a replacement for the generic OpenAI-compatible provider architecture.

The current physical transaction uses the OpenAI-compatible loopback API:

```text
http://127.0.0.1:1234/v1
```

The qualification host accepts only that endpoint. It does not discover another provider by URL, contact a managed desktop runtime, or fall back to another server when llama-server is unavailable.

LM Studio support and historical evidence remain in the repository under their existing owners. They are not current physical fallback authority for this transaction.

## Artifact boundary

The current operator condition supplies a canonical WSL-local GGUF path as physical execution input. The qualification verifies the bytes against the repository's immutable exact-artifact target before semantic work.

The repository target may retain the historical source repository/provenance from which the identical GGUF bytes were frozen. That provenance does not make the old cache location or its serving runtime current physical authority. The live local path, verified content hash, live llama-server model path, and repository target identity are recorded separately.

A filesystem path is never used as RelayLM's external Cognitive Profile/model routing identity merely because it is the physical artifact path.

## Backend-specific request realization

The semantic prompts, State/Continuity proposal schema, source checks, validators, lifecycle, oracle and scorer are reused unchanged from the canonical OpenAI-compatible two-pass path.

For the qualified Gemma/llama-server condition, provider-neutral reasoning `off` is realized explicitly on every semantic request as:

```json
{
  "chat_template_kwargs": {
    "enable_thinking": false
  }
}
```

No model-family inference or hidden default authorizes this field. The qualification host binds an explicit llama.cpp capability record before using it. Bounded reasoning/token-budget modes are not qualified by this path.

Pass 1 remains ordinary conversation. Pass 2 remains the current native `response_format.type=json_schema` structured-output transport.

## Exact serialized-input accounting

Every real Stage R request is counted through llama-server's exact Chat Completions input-token surface before generation. The counted body is the same body that will be sent for generation, including:

- model and messages;
- temperature / top_p / max_tokens when present;
- native response_format on Pass 2;
- `stream=false`;
- `chat_template_kwargs.enable_thinking=false`.

Unknown or unattested request fields fail closed. There is no tokenizer estimate fallback.

## Bounded transaction order

One citable qualification uses a fresh clean RelayLM checkout and fresh artifact/evidence roots, then performs:

```text
repository / Core identity
-> exact local endpoint validation
-> GET /health
-> GET /v1/models
-> GET /props
-> GET /slots
-> exact GGUF verification
-> llama.cpp runtime / model / context / slot attestation
-> exact-input-counter binding
-> one tiny explicit-Thinking-OFF capability request
-> one native JSON-Schema capability request
-> current Stage R scenarios exactly once
-> durable summary and evidence
```

The two capability requests establish that the exact live physical condition can carry the required request controls. They are infrastructure/capability evidence, not Stage R semantic observations and do not change the semantic oracle.

There is no semantic retry, provider fallback, model substitution, prompt repair, parser relaxation, reasoning escalation, or parameter sweep inside the transaction.

## Context safety

Existing llama.cpp actual-model authority requires context shift to be disabled for citable qualification so context exhaustion cannot silently replace earlier context. The physical transaction must prove that condition truthfully before invoking the qualification host.

If the currently running server was launched without an attested context-shift-disabled condition, fixing/relaunching the runtime is mechanical setup/rehearsal. It is not retroactively part of a citable run. After the runtime condition is corrected, the citable transaction reacquires fresh repository and host authority.

## Classification

The host distinguishes:

- `PASS`: the physical/capability condition is valid and all automated current Stage R deterministic/scored semantic gates pass;
- `SEMANTIC_FAIL`: usable physical inference completed but current RelayLM Stage R semantic/deterministic/scored expectations failed;
- `INFRA_INVALID`: endpoint, artifact, runtime, context/slot identity, exact accounting, required request capability, transport, or other physical admission failure prevents a valid semantic verdict.

Infrastructure invalidity is never reported as RelayLM semantic failure. Semantic failure is not retried.

An automated `PASS` does not fabricate a human/product-quality review. The current #1386 review protocol remains a separate evidence boundary where that review is required for a release claim.

## Reproducibility evidence

The host preserves, as available under current evidence conventions:

- RelayLM exact HEAD/tree and frozen Core fingerprint;
- loopback endpoint;
- exact llama.cpp upstream revision, version/build information;
- live model alias/path, quantization/ftype, chat-template hash;
- exact GGUF local path, target identity, size/hash verification;
- effective context, slots and context-shift declaration;
- operator-supplied launch/offload and GPU identity declarations;
- exact Thinking OFF wire;
- Stage R decoding controls and native schema identity;
- exact input counts and content-free completion observations;
- provider `system_fingerprint` when returned;
- request counts, zero semantic retries/fallbacks, execution/boundary artifacts and final classification.

Manual local smoke is useful mechanical evidence, but it is not relabeled as repository-controlled qualification evidence.

## Invocation

After fresh physical authority is established, use the repository-owned entrypoint:

```text
python -m relaylm.actual_model_stage_r_llama_cpp \
  --repo-root <clean-exact-v1-checkout> \
  --provider-base-url http://127.0.0.1:1234/v1 \
  --request-model <exact-/v1/models-id> \
  --artifact-path <canonical-local-gguf> \
  --llama-upstream-revision <exact-40-hex-revision> \
  --llama-version <exact-live-version> \
  --expected-build-number <exact-live-build-number> \
  --expected-context-window 4352 \
  --context-shift-disabled \
  --workspace-root <fresh-workspace> \
  --artifact-root <fresh-artifact-root>
```

`--expected-slots` may be supplied when the transaction independently attests a fixed slot count. Volatile runtime facts are execution inputs/evidence, not committed current-state constants.

> Freeze RelayLM's semantic test, attest llama-server's exact physical condition, and never turn infrastructure failure into a cognition verdict.
