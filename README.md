# RelayLM

RelayLM is a persona-specialized OpenAI-compatible conversation proxy for local LLM applications, AI companions, VTubers, agents, and local inference runtimes.

It is not a language model or a memory database. RelayLM sits in front of an LLM backend and repacks persona, memory, RAG, recent turns, room/scene state, and spilled context into a token-budgeted, persona-stable, KV-reuse-aware effective context.

Initial product target:

- OpenWebUI model preset / avatar -> RelayLM -> LM Studio as the standard MVP UI/backend path
- URL-swap integration through an OpenAI-compatible `/v1/chat/completions` endpoint
- persona-stable and KV-reuse-aware context packing
- Open-LLM-VTuber as an optional frontend / example integration

## Core idea

RelayLM compiles memory, RAG, and chat history into a prefix-stable context layout so that engines such as vLLM and SGLang can reuse prefix/KV cache across turns and character threads.

The first practical value is simple:

> Make an AI VTuber or AI companion feel like it remembers unusually well, without requiring the frontend to manage long context directly.

RelayLM's longer-term product axis is conversation quality: preserve persona consistency, relationship continuity, memory warmth, and token-budget stability so the user wants to keep talking.

## Architecture

RelayLM uses the RelayStack architecture as a product/control-plane layer:

- RelayMEM: memory candidates and long-term memory sources
- RelayCTX: effective context construction and compression
- RelayKV: runtime/cache research boundary, developed in `rinsakamo/relay-kv`
- RelayPLC: policy, fallback, routing, and budget control
- RelayTRC: trace and lineage, deferred for the MVP
- Relay Adapter: OpenAI-compatible proxy and backend adapters

## Documentation

- [Documentation index](docs/README.md)
- [Architecture docs](docs/architecture/README.md)
- [MVP summaries and milestone notes](docs/mvp/README.md)
- [Contract docs](docs/contracts/README.md)
- [Smoke and validation docs](docs/smoke/README.md)
- [RelaySOUL design and gate docs](docs/relaysoul/README.md)
- [OpenWebUI + LM Studio MVP](docs/openwebui_lmstudio_mvp.md)
- [Config schema](docs/config_schema.md)

## MVP direction

The first implementation is a thin OpenAI-compatible proxy with this standard MVP path:

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

Optional integration path:

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

For step-by-step OpenWebUI + LM Studio setup and route-model mapping, see [OpenWebUI + LM Studio MVP](docs/openwebui_lmstudio_mvp.md).

## MVP-0 quick start

Install locally:

```bash
pip install -e .
```

If the environment blocks package index access during editable install, use the current environment's build tools instead:

```bash
pip install -e . --no-build-isolation
```

Create a config:

```bash
cp config.example.yaml config.yaml
```

Run RelayLM through the installed console script:

```bash
relaylm --config config.yaml
```

If editable install failed before installing the console script, run the module directly from the repository root:

```bash
python -m relaylm.app --config config.yaml
```

Or run with uvicorn:

```bash
RELAYLM_CONFIG=config.yaml uvicorn relaylm.app:create_app --factory --host 127.0.0.1 --port 8090
```

Then point Open-LLM-VTuber's OpenAI-compatible base URL at:

```text
http://localhost:8090/v1
```

## Relationship to relay-kv

`relay-kv` remains the runtime/KV-cache research repository. RelayLM starts one layer above runtime APIs as a memory and context proxy. RelayLM should benefit from RelayKV's design lessons, especially working-set selection, anchor/recent/retrieved separation, Persona Anchor KV, and cache-aware layout, without mutating engine KV cache in the initial product.
