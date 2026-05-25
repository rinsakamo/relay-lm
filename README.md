# RelayLM

RelayLM is a persona-specialized OpenAI-compatible conversation proxy for local LLM applications, AI companions, VTubers, agents, and local inference runtimes.

It is not a language model or a memory database. RelayLM sits in front of an LLM backend and repacks persona, memory, RAG, recent turns, room/scene state, and spilled context into a token-budgeted, persona-stable, KV-reuse-aware effective context.

Initial product target:

- Open-LLM-VTuber memory proxy
- URL-swap integration through an OpenAI-compatible `/v1/chat/completions` endpoint
- persona-stable and KV-reuse-aware context packing

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

## Initial docs

- [VTuber memory proxy design](docs/vtuber_memory_proxy_design.md)
- [Context packing design](docs/context_packing_design.md)
- [Persona-specialized proxy design](docs/persona_specialized_proxy_design.md)
- [RelaySOUL persona source calibration design](docs/relaysoul_design.md)
- [RelaySOUL patch candidate contract](docs/relaysoul_patch_candidate_contract.md)
- [RelaySOUL revision contract](docs/relaysoul_revision_contract.md)
- [RelaySOUL approval contract](docs/relaysoul_approval_contract.md)
- [RelaySOUL persistence contract](docs/relaysoul_persistence_contract.md)
- [Open-LLM-VTuber integration](docs/open_llm_vtuber_integration.md)
- [Runtime architecture](docs/runtime_architecture.md)
- [Config schema](docs/config_schema.md)
- [Token policy profile settings](docs/token_policy_profiles.md)
- [Context compiler contract](docs/context_compiler_contract.md)
- [Product runtime hardening](docs/product_runtime_hardening.md)
- [MVP-0 pass-through proxy](docs/mvp0_pass_through_proxy.md)
- [MVP-1 config and routing smoke](docs/mvp1_config_routing_smoke.md)
- [MVP-1 runtime diagnostics smoke](docs/mvp1_runtime_diagnostics_smoke.md)
- [MVP-1 API diagnostics smoke](docs/mvp1_api_diagnostics_smoke.md)
- [MVP-1 summary](docs/mvp1_summary.md)
- [MVP-2 context compiler contract](docs/mvp2_context_compiler_contract.md)
- [MVP-2 profile file loading](docs/mvp2_profile_file_loading.md)
- [MVP-2 config profile resolution](docs/mvp2_config_profile_resolution.md)
- [MVP-2 compiled system message](docs/mvp2_compiled_system_message.md)
- [MVP-2 incoming system fallback](docs/mvp2_incoming_system_fallback.md)
- [MVP-2 profile compile dry-run](docs/mvp2_profile_compile_dry_run.md)
- [MVP-2 dry-run diagnostics headers](docs/mvp2_dry_run_diagnostics_headers.md)
- [MVP-2 gated compile decision](docs/mvp2_gated_compile_decision.md)
- [MVP-2 memory-light apply helper](docs/mvp2_memory_light_apply.md)
- [MVP-2 runtime memory-light apply](docs/mvp2_runtime_memory_light_apply.md)
- [MVP-2 memory-light API smoke](docs/mvp2_memory_light_api_smoke.md)
- [MVP-2 summary](docs/mvp2_summary.md)
- [MVP-3 summary](docs/mvp3_summary.md)
- [MVP-4 summary](docs/mvp4_summary.md)
- [MVP-5 summary](docs/mvp5_summary.md)
- [MVP-6 summary](docs/mvp6_summary.md)
- [MVP-7 summary](docs/mvp7_summary.md)
- [MVP-8 summary](docs/mvp8_summary.md)
- [MVP-9 summary](docs/mvp9_summary.md)
- [MVP-10 summary](docs/mvp10_summary.md)
- [MVP-11 summary](docs/mvp11_summary.md)
- [MVP-12 summary](docs/mvp12_summary.md)
- [MVP-13 summary](docs/mvp13_summary.md)
- [MVP-14 summary](docs/mvp14_summary.md)

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