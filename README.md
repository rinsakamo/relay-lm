# RelayLM

<p align="center">
  <strong>Memory- and persona-aware OpenAI-compatible conversation proxy for local LLMs</strong>
</p>

<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-blue">
  <img alt="OpenAI-compatible" src="https://img.shields.io/badge/API-OpenAI--compatible-6f42c1">
  <img alt="Status: active development" src="https://img.shields.io/badge/status-active%20development-orange">
  <a href="./LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"></a>
</p>

<p align="center">
  <a href="./README_ja.md">日本語 README</a> ・
  <a href="./docs/PROJECT_STATUS.md">Project Status</a> ・
  <a href="./docs/README.md">Documentation</a> ・
  <a href="./LICENSE">License</a>
</p>

> [!WARNING]
> RelayLM is under active MVP development. See [Project Status](docs/PROJECT_STATUS.md) for the current phase, implemented boundaries, gated or default-off behavior, and immediate next work.

## 🌉 What is RelayLM?

RelayLM is a persona-specialized conversation proxy for local LLM applications, AI companions, VTubers, agents, and local inference runtimes.

It sits between an OpenAI-compatible frontend and backend:

```text
Frontend
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible LLM backend
```

RelayLM is **not** a language model and **not** a memory database. It is designed to compile persona, approved memory, RAG, recent turns, scene state, and spilled context into a token-budgeted, persona-stable, KV-reuse-aware effective context.

> Make an AI VTuber or AI companion feel like it remembers unusually well, without requiring the frontend to manage long context directly.

## ✨ Why RelayLM?

- 🔌 **URL-swap integration** — connect through an OpenAI-compatible `/v1/chat/completions` endpoint.
- 🧠 **Persona-stable context** — keep identity and output policy above dynamic memory and retrieved evidence.
- 🧩 **Explicit pipeline boundaries** — separate scene, affect, intent, retrieval, context packing, output observation, orchestration, and deferred persistence.
- ⚡ **KV-reuse-aware layout** — prefer stable context ordering that can benefit prefix/KV cache reuse.
- 🛡️ **Safe-by-default behavior** — introduce request mutation and persistence behind explicit compatibility, policy, and apply gates.
- 💻 **Local-first posture** — keep storage local by default, expose backend URLs in configuration, and avoid hidden remote telemetry.

> [!NOTE]
> RelayLM is local-first, but when a hosted or remote backend is configured, the selected compiled context is sent to that backend as part of the request.

## 🧭 Runtime paths

### Standard MVP path

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

### Optional AI VTuber path

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

RelayLM owns conversation proxying and context/runtime boundaries. It does not own the frontend UI, ASR, TTS, or avatar runtime.

## 📍 Development status

For the current phase, implemented boundaries, dry-run/read-only/default-off behavior, and immediate next work, see [Project Status](docs/PROJECT_STATUS.md).

`docs/PROJECT_STATUS.md` is the maintained current-state view. This README intentionally does not duplicate phase numbers or short-lived implementation status.

## 🚀 Quick start

### 1. Clone and install

```bash
git clone https://github.com/rinsakamo/relay-lm.git
cd relay-lm

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

<details>
<summary>Windows PowerShell activation</summary>

```powershell
.venv\Scripts\Activate.ps1
```

</details>

If editable installation cannot access build dependencies, use the current environment's build tools:

```bash
pip install -e . --no-build-isolation
```

### 2. Create the configuration

For the standard OpenWebUI + LM Studio path:

```bash
cp examples/config/openwebui_lmstudio.yaml config.yaml
```

For a generic starting point instead:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` for your backend URL, backend model, and RelayLM route. The standard example expects LM Studio at `http://127.0.0.1:1234/v1` and RelayLM at `http://127.0.0.1:8090/v1`. See the [configuration schema](docs/config_schema.md) and the [OpenWebUI + LM Studio guide](docs/openwebui_lmstudio_mvp.md).

### 3. Start RelayLM

```bash
relaylm --config config.yaml
```

Fallback module command:

```bash
python -m relaylm.app --config config.yaml
```

Or start through Uvicorn:

```bash
RELAYLM_CONFIG=config.yaml \
  uvicorn relaylm.app:create_app --factory --host 127.0.0.1 --port 8090
```

### 4. Point the frontend to RelayLM

Set the OpenAI-compatible base URL in OpenWebUI, Open-LLM-VTuber, or another compatible frontend to:

```text
http://127.0.0.1:8090/v1
```

## 🏗️ Architecture

The canonical runtime order is:

```text
User input
  -> RelayRUN request shell
  -> PipelineContext
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> Main LLM / backend forward
  -> RelayCTX Unpack
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN
  -> RelayRUN final artifact / trace / checkpoint summary
  -> User output

Out-of-band after-turn path:
  governed evidence
  -> RelaySLP
  -> MEM update candidates / SOUL proposals
  -> persistence and approval gates
```

This is the canonical responsibility order, not a claim that every stage is already active. Consult [Project Status](docs/PROJECT_STATUS.md) for implementation status.

| Relay component | Responsibility |
|---|---|
| 🌬️ **RelaySCN** | Scene classification and scene/persistence policy |
| 🙂 **RelayEMO** | Affect estimation and scene-gated expression control |
| 🚦 **RelayINT** | Input-side intent, ambiguity, clarification, and proceed/block gate |
| 🧠 **RelayMEM** | Read-only retrieval in the normal response path |
| 📦 **RelayCTX** | Backend input construction through Repack and visible/internal separation through Unpack |
| 🔎 **RelayREF** | Lightweight output-side observation and diagnostics |
| 🎛️ **RelayRUN** | Runtime orchestration, fallback/recovery, checkpoints, trace, and node state |
| 🌙 **RelaySLP** | Out-of-band memory and SOUL compilation path |

Cross-cutting and transport boundaries:

- `PipelineContext`: request-local coordination, payload replacement history, runtime-private state, node results, and diagnostics handoff
- Runtime Compile Gate: request-local apply and compatibility decision phase; not a standalone `RelayPLC` component
- OpenAI-compatible adapter: frontend/backend protocol boundary; not a semantic pipeline stage

The short timing rule is:

```text
RelayINT = before action
RelayREF = after response
```

For authoritative ownership and order, see the [Pipeline Responsibility Design](docs/architecture/pipeline_responsibility_design.md).

## 📚 Documentation

- 📍 [Current project status](docs/PROJECT_STATUS.md)
- 🗺️ [Documentation index](docs/README.md)
- 🏗️ [Architecture documents](docs/architecture/README.md)
- 🧭 [Pipeline implementation plan](docs/architecture/pipeline_implementation_plan.md)
- 🚀 [OpenWebUI + LM Studio MVP guide](docs/openwebui_lmstudio_mvp.md)
- ⚙️ [Configuration schema](docs/config_schema.md)
- 📜 [Contracts](docs/contracts/README.md)
- 🧪 [Smoke tests and validation](docs/smoke/README.md)
- 🧬 [RelaySOUL design and gates](docs/relaysoul/README.md)
- 🗃️ [MVP summaries and milestone history](docs/mvp/README.md)

## 🔗 Relationship to RelayKV

[RelayKV](https://github.com/rinsakamo/relay-kv) is the adjacent runtime/KV-cache research repository. RelayLM operates one layer above runtime APIs as a conversation and context proxy.

RelayLM can benefit from RelayKV design lessons—working-set selection, anchor/recent/retrieved separation, Persona Anchor KV, and cache-aware layout—without directly mutating engine KV cache in the initial product.

## 📄 License

RelayLM is licensed under the [Apache License 2.0](LICENSE).
