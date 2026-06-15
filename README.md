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

RelayLM's canonical runtime vocabulary follows the [pipeline responsibility design](docs/architecture/pipeline_responsibility_design.md):

- RelaySCN: scene classification and scene/persistence policy
- RelayEMO: affect estimation and scene-gated expression control
- RelayINT: input-side intent, ambiguity, clarification, and proceed/block gate
- RelayMEM: read-only retrieval in the normal response path; writes are separated from retrieval
- RelayCTX: backend input construction through Repack and response/internal-candidate separation through Unpack
- RelayREF: lightweight output-side observation and diagnostics
- RelayRUN: runtime orchestration, fallback/recovery handling, checkpoints, trace artifacts, and node-state reporting
- RelaySLP: out-of-band memory and SOUL compilation path

Cross-cutting and adjacent boundaries:

- `PipelineContext`: request-local coordination, payload replacement history, node results, and diagnostics handoff
- OpenAI-compatible adapter / proxy transport: frontend and backend protocol boundary, not a semantic pipeline stage
- RelayKV: adjacent runtime/cache research boundary, developed in `rinsakamo/relay-kv`, not a RelayLM pipeline component

`RelayPLC` and `RelayTRC` are not standalone components in the current architecture. Responsibilities previously summarized under `RelayPLC` are owned by RelaySCN for scene and persistence policy, RelayINT for pre-action routing and clarification, RelayRUN for runtime fallback/recovery routing, and RelayCTX Repack for token-budget control. Trace and lineage are carried by RelayRUN artifacts, diagnostics, and typed audit projections rather than a separate RelayTRC stage.

## Documentation

- [Current project status](docs/PROJECT_STATUS.md)
- [Documentation index](docs/README.md)
- [Architecture docs](docs/architecture/README.md)
- [MVP summaries and milestone notes](docs/mvp/README.md)
- [Contract docs](docs/contracts/README.md)
- [Smoke and validation docs](docs/smoke/README.md)
- [RelaySOUL design and gate docs](docs/relaysoul/README.md)
- [OpenWebUI + LM Studio MVP](docs/openwebui_lmstudio_mvp.md)
- [Config schema](docs/config_schema.md)

For a one-page view of the current phase, implemented boundaries, default-off/preflight-only features, and immediate next work, start with [Project Status](docs/PROJECT_STATUS.md).

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
