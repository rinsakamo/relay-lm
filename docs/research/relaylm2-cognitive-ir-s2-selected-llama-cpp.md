# RelayLM 2.0 Cognitive IR — selected S2 on WSL llama.cpp

This document is the current repository contract for carrying the already-preregistered #2211 selected S2 smoke through a locally managed WSL2 `llama-server` runtime.

It is an execution adapter for the existing experiment. It does not redefine the P0-P6 scientific treatment, the selected family, or the S2/S3 interpretation boundary.

The historical LM Studio selected-S2 adapter remains historical evidence/support for its completed transactions. New WSL work uses this adapter instead of contacting or falling back to LM Studio.

## Ownership and procedure

Scientific owner: #2211.

Cross-experiment physical procedure: #2363.

The procedure invariant remains:

> **Controller observes and assembles. Host validates and freezes.**

The controller may collect fresh read-only serving, process, artifact, hardware, and capacity observations. It does not authorize the scientific run. `run_llama_cpp_selected_s2_transaction(...)` revalidates the material binding and then enters the existing S2 host, whose final binding/freeze remains authoritative before provider entry.

## Endpoint boundary

The selected WSL adapter accepts only:

```text
http://127.0.0.1:1234/v1
```

There is no network-host rewrite, LM Studio endpoint, alternate port, provider fallback, model fallback, or quant fallback in this path.

The OpenAI-compatible request `model` value is a provider/runtime alias observed freshly from `/v1/models`. It is not a RelayLM public Profile identity and is not inferred from the GGUF filename. The filesystem artifact path remains a runtime/artifact identity only.

## Explicit Thinking-OFF control

Every selected-S2 Chat Completions request carries the top-level OpenAI-compatible field:

```json
{
  "reasoning_effort": "none"
}
```

For a physical transaction, the exact llama.cpp revision is part of the frozen runtime identity and its upstream implementation semantics must be verified before execution. The admitted llama.cpp implementation contract is that top-level `reasoning_effort="none"` disables reasoning by setting the effective template input to Thinking-OFF.

This is a pinned llama.cpp runtime contract for this adapter, not a universal OpenAI/provider guarantee.

`reasoning_format="none"` is not an admissible substitute because output/reasoning formatting is distinct from the control that disables Thinking.

Omission of `reasoning_effort`, or any value other than `"none"`, is a pre-provider contract failure for selected-S2 exact accounting.

Response-side `reasoning` / `reasoning_content` must be empty when exposed. If the response exposes `completion_tokens_details.reasoning_tokens`, that value must be zero. These response checks are supplementary; the primary control is the explicit request plus the pinned llama.cpp implementation/runtime identity.

## Exact serialized-input accounting

Before each of the ten semantic Chat Completions requests, the adapter asks llama.cpp's own

```text
/v1/chat/completions/input_tokens
```

surface to count:

1. the exact generation body; and
2. the same body with only message `content` values replaced by empty strings.

Both counting bodies preserve `reasoning_effort="none"`, `model`, `stream=false`, decoding fields, and any `response_format`. The first counting body must therefore equal the generation body byte-for-structure at the JSON-object level. No reasoning field is stripped for counting.

The returned exact total must equal the generation response's `usage.prompt_tokens`; disagreement fails closed instead of silently changing cost accounting.

These input-token requests are non-generative instrumentation. The experiment's preregistered provider/model-call count remains exactly ten semantic Chat Completions calls. Instrumentation does not authorize an extra semantic call or a retry.

## Selected physical condition

This adapter preserves the selected S2 context condition of 8192 tokens. That number is experiment-specific here; it is **not** a generic #2363 constant.

The host fresh-reads `/health`, `/v1/models`, `/props`, and `/slots`, hashes the controller-declared llama-server binary and GGUF artifact again, and uses the repository llama.cpp runtime attester to bind:

- exact upstream revision/build info;
- fresh request model alias;
- exact model path and artifact SHA-256;
- model ftype;
- chat-template digest;
- context limit;
- slot count and each slot context;
- context-shift-disabled state.

The controller identity additionally freezes non-secret launch, hardware, and capacity evidence gathered under #2363. A live context other than 8192, changed binary/artifact hash, request-alias mismatch, changed `/props`/`/slots` binding, or context-shift-enabled declaration stops before semantic execution.

The generic #2363 procedure still requires fresh observations on every physical transaction. Historical values from a prior WSL or LM Studio run are never current execution authority.

## Transport policy

The selected llama.cpp transport freezes:

```text
temperature       = 0.0
seed              = null
max_output_tokens = 512
timeout_seconds   = 1800
stream             = false
reasoning_effort   = "none"
```

P2 and P3 remain plain-text formation calls. P4 and P0-P6 remain the existing strict JSON Schema machine-readable surfaces. The transport cannot make an eleventh provider call.

## Scientific invariants preserved

This adapter does not change:

- P0 `RAW_HISTORY`;
- P1 `RETRIEVAL_ONLY`;
- P2 `ORDINARY_SUMMARY`;
- P3 `SEMANTIC_CACHE`;
- P4 `MEMORY_PLUS_STRUCTURE`;
- P5 `STRUCTURE_ONLY_RECONSTRUCTABLE`;
- P6 `GENERIC_EQUAL_INFORMATION`;
- P5/P6 deterministic derivation from the one P4 formation;
- P4/P6 semantic equality;
- P4/P5/P6 one-formation lineage;
- the selected family/seed/regime;
- execution order `form-p2 -> form-p3 -> form-p4 -> probe-p0..p6`;
- exactly ten semantic provider calls;
- no automatic retry and no semantic retry;
- S2 mechanical terminal classifications;
- claim `NON_CITABLE_S2_SMOKE` with `citable=false`;
- S3 remaining a separately preregistered future transaction only after its current gate is satisfied.

A mechanically discriminating S2 is not an IR winner, ontology result, or architecture authorization.

## Historical preservation

Nothing in this adapter rewrites, reruns, or reinterprets completed LM Studio calibration/S2 evidence. In particular, a prior `EXECUTION_BLOCKED` transaction with zero provider/model calls remains exactly that historical result.

Repository preparation itself performs no model/GPU execution. A physical S2 transaction starts only from a fresh exact checkout, fresh external artifact root, fresh #2211/#2363 authority, and fresh WSL controller observations.
