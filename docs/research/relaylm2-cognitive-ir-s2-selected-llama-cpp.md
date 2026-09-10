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

## One-command physical transaction

The current WSL Local execution surface is repository-owned and uses the interpreter name that is present on the target Ubuntu/WSL laboratory:

```text
python3 -m tools.v2_cognitive_ir_s2_selected_llama_cpp_wsl
```

Do not assume a `python` compatibility alias exists. #2436 established that the current target shell exposes `/usr/bin/python3` while `python` is absent; that pre-harness launcher block is historical infrastructure evidence and does not spend S2.

#2440 then established a separate LocalCodex sandbox fact: the operator home may be readable but not writable. The inner transaction historically used `Path.home()` for its lifecycle lock and one-lifetime server log, so the WSL launcher now creates a fresh repo-external writable runtime home and passes the real llama.cpp/GGUF paths explicitly. It also routes the shared lifecycle lock to:

```text
/tmp/relaylm/locks/llama-server-127.0.0.1-1234.lock
```

The launcher invokes the existing inner transaction module exactly once:

```text
tools.v2_cognitive_ir_s2_selected_llama_cpp_transaction
```

Changing the child `HOME` is therefore only a writable-state envelope for transaction-owned cache/log paths. It does not change the llama.cpp source root, GGUF artifact identity, provider endpoint, model alias, GPU/runtime identity, selected S2 treatment, or #2363 host boundary.

#2452 established another pre-host launcher fact: a clean `src/`-layout checkout is not importable by the inner transaction merely because the outer `tools...wsl` wrapper itself is importable. The current launcher therefore executes its one child with the exact checkout as `cwd` and prepends the exact checkout's `<repo>/src` directory to child `PYTHONPATH`, preserving any inherited `PYTHONPATH` after it. This binds `relaylm.*` imports to the selected clean checkout rather than an incidental installed copy while leaving the writable child `HOME` and real operator llama.cpp/GGUF paths unchanged.

The inner transaction owns only the mechanical laboratory lifecycle around the existing scientific host:

```text
fresh clean exact v2 checkout
-> acquire one kernel-backed local laboratory lock
-> fail closed if 127.0.0.1:1234 is already occupied
-> attest exact local llama.cpp source/binary/GGUF/GPU identity
-> verify the exact binary accepts the declared launch flags
-> verify the exact source revision maps reasoning_effort=none to Thinking OFF
-> create one unique server log
-> launch one fresh llama-server process
-> bounded non-generative readiness and /health + /v1/models + /props + /slots probes
-> assemble the existing selected-S2 controller identity
-> invoke run_llama_cpp_selected_s2_transaction(...) at most once
-> terminate only the transaction-owned server PID
-> wait for process exit/log flush
-> hash the one-process-lifetime server log
-> emit s2-selected-llama-cpp-transaction-summary.json
```

The transaction-owned launch class is:

```text
-m <canonical GGUF>
--host 127.0.0.1
--port 1234
-ngl 999
-c 8192
-np 1
--no-context-shift
-lv 4
--log-prefix
--log-timestamps
--log-file <unique one-lifetime path>
```

One WSL launcher invocation spawns at most one inner transaction. One inner transaction owns at most one server launch and at most one scientific host invocation. Neither layer reuses, restarts, replaces, or kills a pre-existing listener. Cleanup signals only the exact process handle created by that invocation. A local kernel-backed lock spans the whole server lifetime so independently launched Local agents serialize on the shared port/GPU rather than racing one another.

A launcher-environment, server startup/readiness, or runtime-identity failure before host invocation is an `EXECUTION_BLOCKED` mechanical result with zero semantic provider/model calls. Once the selected-S2 host has been invoked, a failure is terminal for that host transaction; the wrapper does not restart the server, retry the host, replay a request, reseed, or fall back to another provider.

The writable WSL launcher and lifecycle wrapper are not scientific hosts. They do not call host-owned freeze/durability primitives and do not alter the #2363 boundary. The existing `run_llama_cpp_selected_s2_transaction(...)` remains the only selected-S2 host entrypoint.

The transaction summary records the exact RelayLM repository identity, server PID/source/binary/hash/argv, GGUF hash, GPU identity, fresh request alias/runtime probes, controller identity, host result when reached, artifact references, unique server-log path/hash/size, cleanup disposition, and explicit zero retry/replay/fallback/LM-Studio/repository-mutation counters. Local execution/reconciliation should adopt this summary and its referenced artifacts rather than manually replaying internal requests.

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

Nothing in this adapter rewrites, reruns, or reinterprets completed LM Studio calibration/S2 evidence. In particular, prior `EXECUTION_BLOCKED` transactions with zero provider/model calls remain exactly those historical results. #2436 stopped before Python harness entry; #2440 entered the transaction wrapper but stopped on a read-only home-directory lifecycle lock before server launch or selected-S2 host entry; #2445 passed the writable lock and then stopped on LocalCodex localhost-binding permission before server launch; #2452 passed the Full Access permission gate and invoked the wrapper once, but its child stopped on the clean-checkout `src/` import-path boundary before transaction `main()`. None spent S2.

Repository preparation itself performs no model/GPU execution. A physical S2 transaction starts only from a fresh exact checkout, fresh external artifact root, fresh #2211/#2363 authority, and fresh WSL controller observations.
