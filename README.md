# RelayLM

RelayLM is an OpenAI-compatible memory and context proxy for local LLM applications, agents, AI companions, and local inference runtimes.

It is not a language model. RelayLM sits in front of an LLM backend and repacks memory, RAG, recent turns, and spilled context into a budget-aware effective context.

Initial product target:

- Open-LLM-VTuber memory proxy
- URL-swap integration through an OpenAI-compatible `/v1/chat/completions` endpoint
- persona-stable and KV-reuse-aware context packing

## Core idea

RelayLM compiles memory, RAG, and chat history into a prefix-stable context layout so that engines such as vLLM and SGLang can reuse prefix/KV cache across turns and character threads.

The first practical value is simple:

> Make an AI VTuber or AI companion feel like it remembers unusually well, without requiring the frontend to manage long context directly.

## Architecture

RelayLM uses the RelayStack architecture as a product/control-plane layer:

- RelayMEM: memory candidates and long-term memory sources
- RelayCTX: effective context construction and compression
- RelayKV: runtime/cache research boundary, developed in `rinsakamo/relay-kv`
- RelayPLC: policy, fallback, routing, and budget control
- RelayTRC: trace and lineage, deferred for the MVP
- Relay Adapter: OpenAI-compatible proxy and backend adapters

## Initial docs

- [VTuber memory proxy design](docs/vtuber_memory_proxy_design.md)
- [Context packing design](docs/context_packing_design.md)
- [Open-LLM-VTuber integration](docs/open_llm_vtuber_integration.md)
- [Runtime architecture](docs/runtime_architecture.md)
- [Config schema](docs/config_schema.md)
- [Context compiler contract](docs/context_compiler_contract.md)
- [Product runtime hardening](docs/product_runtime_hardening.md)
- [MVP-0 pass-through proxy](docs/mvp0_pass_through_proxy.md)

## MVP direction

The first implementation is a thin OpenAI-compatible proxy:

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> vLLM / SGLang / other OpenAI-compatible backend
```

The default integration should be easy for existing Open-LLM-VTuber users:

1. Start an LLM backend.
2. Start RelayLM.
3. Change the OpenAI-compatible API URL in Open-LLM-VTuber to RelayLM.
4. Keep using the existing character configuration.

## MVP-0 quick start

Install locally:

```bash
pip install -e .
```

Create a config:

```bash
cp config.example.yaml config.yaml
```

Run RelayLM:

```bash
relaylm --config config.yaml
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

`relay-kv` remains the runtime/KV-cache research repository. RelayLM starts one layer above runtime APIs as a memory and context proxy. RelayLM should benefit from RelayKV's design lessons, especially working-set selection, anchor/recent/retrieved separation, and cache-aware layout, without mutating engine KV cache in the initial product.