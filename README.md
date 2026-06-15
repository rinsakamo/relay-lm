# RelayLM

<p align="center">
  <strong>Memory- and persona-aware OpenAI-compatible conversation proxy for local LLMs</strong>
</p>

<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-blue">
  <img alt="OpenAI-compatible" src="https://img.shields.io/badge/API-OpenAI--compatible-6f42c1">
  <img alt="Status: active development" src="https://img.shields.io/badge/status-active%20development-orange">
</p>

<p align="center">
  <a href="./README_ja.md">日本語 README</a> ・
  <a href="./docs/PROJECT_STATUS.md">Project Status</a> ・
  <a href="./docs/README.md">Documentation</a>
</p>

> [!WARNING]
> RelayLM is under active MVP development. The OpenAI-compatible proxy and pass-through path are usable, while several managed-context, output-processing, and persistence features remain gated, default-off, or planned. See [Project Status](docs/PROJECT_STATUS.md) for the exact current boundary.

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
- 🛡️ **Safe-by-default behavior** — new mutation and persistence paths are introduced behind explicit gates.
- 💻 **Local-first operation** — use local frontends, local backends, and repository-visible configuration.

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

## 📍 Current state

RelayLM is currently in **Phase 5-C**. The immediate next boundary is the managed-route apply path described in [Project Status](docs/PROJECT_STATUS.md).

### ✅ Available foundations

- OpenAI-compatible proxy and model-route handling
- `pass_through` compatibility baseline
- `PipelineContext` request-local coordination
- RelayCTX Repack boundaries
- gated RelayMEM retrieval and context injection
- RelayINT-facing reference-repair and diagnostics boundaries
- ordered `PipelineNodeResult` collection
- pure and gated non-stream RelayCTX Unpack
- request-level RelayRUN artifacts, checkpoints, and typed content-free diagnostics

### 🧪 Gated or diagnostic-only boundaries

- managed-route client-message canonicalization
- client-instruction identity and read-only cache lookup
- client-history exclusion preflight
- RelayINT Fast Path and quick-clarification planning
- non-stream RelayCTX Unpack apply
- short-term context injection

### 🛠️ Major planned boundaries

- managed-route client-message replacement
- cache-hit RelaySCN state injection and cache-miss instruction evidence
- typed instruction artifact parsing and cache writes
- streaming RelayCTX Unpack and TTS-safe output segmentation
- output-side RelayREF and RelaySCN stages
- cross-cutting per-node RelayRUN orchestration
- asynchronous RelaySLP persistence path

The concise, maintained source for what works now is [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

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

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` for your backend URL, backend model, and RelayLM route. See the [configuration schema](docs/config_schema.md) and the [OpenWebUI + LM Studio guide](docs/openwebui_lmstudio_mvp.md).

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
  -> RelayRUN artifact / trace / checkpoint summary
  -> User output

Out-of-band:
  governed evidence
  -> RelaySLP
  -> MEM update candidates / SOUL proposals
  -> persistence and approval gates
```

This is the canonical responsibility order, not a claim that every stage is already active. Consult [Project Status](docs/PROJECT_STATUS.md) for implementation status.

| Component | Responsibility |
|---|---|
| 🌬️ **RelaySCN** | Scene classification and scene/persistence policy |
| 🙂 **RelayEMO** | Affect estimation and scene-gated expression control |
| 🚦 **RelayINT** | Input-side intent, ambiguity, clarification, and proceed/block gate |
| 🧠 **RelayMEM** | Read-only retrieval in the normal response path |
| 📦 **RelayCTX** | Backend input construction through Repack and visible/internal separation through Unpack |
| 🔎 **RelayREF** | Lightweight output-side observation and diagnostics |
| 🎛️ **RelayRUN** | Runtime orchestration, fallback/recovery, checkpoints, trace, and node state |
| 🌙 **RelaySLP** | Out-of-band memory and SOUL compilation path |

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
