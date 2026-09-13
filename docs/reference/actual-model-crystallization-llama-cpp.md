# Actual-model off-turn Crystallization on llama.cpp

This is the v1 physical carriage for the existing off-turn Crystallization
contract. It is an evaluation-only path and does not change `CrystallizationInput`,
the crystallization prompt or structured schema, `MemoryUnit`, `StateCandidate`,
the deterministic Validator, State, MEMORY projection, ordinary turns, Stage R,
or calibration semantics.

## Public physical target

The registered target is:

```text
target: v1:crystallization
engine: llama.cpp
resource: llama-cpp:local-gpu
module: tools.v1_crystallization_llama_cpp_wsl
required distribution: httpx
```

It is intentionally distinct from `v1:stage-r`. The operator-facing command is
owned by the common physical runner:

```bash
python -m tools.relay_physical_run --target v1:crystallization
```

This command is a future physical Phase-B entrypoint. It is documented here for
the later scientific owner and is not run by the #2811 repository transaction.
The operator does not assemble a server command, model path, port, workspace,
HTTP request, or queue primitive.

## Layering

```text
common physical runner / shared queue
        |
        v
fresh WSL wrapper roots and exact checkout-only Python path
        |
        v
one transaction-owned llama-server lifetime
        |
        v
llama.cpp runtime/artifact/model/context/slot/context-shift attestation
        |
        v
llama.cpp off-turn host
        |
        +--> existing run_actual_model_crystallization(...)
        |       |
        |       +--> raw MemoryUnit[] / StateCandidate[]
        |       +--> deterministic Validator, State, and MEMORY evidence
        |       +--> immutable CRY2-compatible evidence artifact
        |
        +--> current native-schema request with reasoning_effort=none
        +--> same final request body to exact /input_tokens accounting
```

The transaction reuses the existing llama.cpp lifecycle helpers for the
single-slot `llama-server`, readiness, non-generative `/health`, `/v1/models`,
`/props`, and `/slots` checks, owned-process teardown, and per-launch log. The
host performs no capability-generation smoke. Native JSON Schema is required on
the canonical request; HTTP/schema/parse failures have no plain-text fallback,
repair generation, retry, or second generation.

The provider adapter subclasses the existing OpenAI-compatible crystallizer only
to bind the current llama.cpp `reasoning_effort=none` realization and
`LlamaCppThinkingChatInputCounter`. It constructs one request body, counts that
body with the current llama.cpp framing method, and sends the same controls to
`/chat/completions`. The raw model proposal remains separate from deterministic
materialization through the existing actual-model evidence contract. The host
does not produce a product-quality PASS; current CRY2 review remains a separate
review step over retained evidence.

## Current physical bindings

At each future invocation, the host binds fresh live runtime facts to the
repository target rather than trusting historical issue text: the exact current
llama.cpp revision/build, canonical GGUF target and SHA-256, request model alias,
embedded tokenizer identity, context `8192`, one slot, disabled context shift,
`-ngl 999`, localhost `127.0.0.1:1234`, and the native llama.cpp input-token
counter. The repository authority currently realizes reasoning OFF as the
explicit OpenAI-compatible `reasoning_effort=none` field; the counter and
generation body both carry it, along with `stream=false`.

The canonical frozen quality fixture is copied into a fresh run workspace and
its source revision is checked before and after the operation. Evidence records
the exact input, raw structured proposals, deterministic decisions, resulting
State, and resulting MEMORY representation under the existing immutable
Crystallization evidence format. A later CRY2 reviewer can consume that artifact
without another model generation.

No target, wrapper, transaction, provider, server, model, GPU, LM Studio, or
scientific execution is performed as part of #2811.
