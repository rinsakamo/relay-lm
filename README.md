# RelayLM

<p align="center">
  <img
    src="docs/assets/readme/relaylm-hero-wide.webp"
    alt="RelayLM characters in a soft home lab workspace"
    width="100%"
  />
</p>

<p align="center">
  <strong>File-first character workspace and memory/persona-aware OpenAI-compatible conversation proxy for local LLMs</strong>
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

RelayLM is a file-first character workspace and persona-specialized conversation proxy for local LLM applications, AI companions, VTubers, agents, and local inference runtimes.

It sits between an OpenAI-compatible frontend and backend:

```text
Frontend
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible LLM backend
```

RelayLM is **not** a language model and **not** a memory database. Its product target is an editable Markdown character workspace whose approved sources are compiled into relationship-, scene-, emotion-, memory-, and context-aware runtime projections. It is designed to compile persona, approved memory, RAG, recent turns, scene state, and spilled context into a token-budgeted, persona-stable, KV-reuse-aware effective context.

> Make an AI VTuber or AI companion feel like it remembers unusually well, without requiring the frontend to manage long context directly.

## ✨ Why RelayLM?

- 🔌 **URL-swap integration** — connect through an OpenAI-compatible `/v1/chat/completions` endpoint.
- 🧬 **File-first character workspace** — target editable Markdown sources such as `SOUL.md`, `STYLE.md`, `EMOTION.md`, `SCENE.md`, `RELATIONSHIP.md`, `MEMORY.md`, and `BOUNDARY.md`.
- 🧠 **Persona-stable context** — keep identity and output policy above dynamic memory and retrieved evidence.
- 🧩 **Explicit pipeline boundaries** — separate relationship, scene, affect, intent, retrieval, context packing, output observation, orchestration, and deferred persistence.
- ⚡ **KV-reuse-aware layout** — prefer stable context ordering that can benefit prefix/KV cache reuse.
- 🛡️ **Safe-by-default behavior** — introduce request mutation and persistence behind explicit compatibility, policy, and apply gates.
- 💻 **Local-first posture** — keep storage local by default, expose backend URLs in configuration, and avoid hidden remote telemetry.

> [!NOTE]
> RelayLM is local-first, but when a hosted or remote backend is configured, the selected compiled context is sent to that backend as part of the request.

## 🛠️ What you can build

- a local AI companion with more stable persona and conversation context
- a memory-aware work assistant used through OpenWebUI
- an AI VTuber context layer between Open-LLM-VTuber and a local LLM backend

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

> [!IMPORTANT]
> On the default `memory_light` compatibility path, prior frontend-supplied user/assistant history may still remain in the backend-bound message list. History-exclusion apply remains default-off and dry-run-only by default. The implemented v0 path supports bounded no-instruction managed requests; the v1 path supports bounded instruction-bearing managed requests only with exact `client_instruction_source.v1` provenance. Missing or invalid v1 provenance fails closed. Broader current-turn-only reconstruction, including active tool-chain preservation, is not complete. See [Project Status](docs/PROJECT_STATUS.md), the [Client History Authority Contract](docs/architecture/client_history_authority_contract.md), and the [OpenWebUI + LM Studio guide](docs/openwebui_lmstudio_mvp.md).

## ✅ Requirements

| Item | Requirement |
|---|---|
| Python | 3.10 or later |
| Backend | OpenAI-compatible Chat Completions backend |
| Standard setup | OpenWebUI + RelayLM + LM Studio |
| OpenWebUI | Use an OpenAI-compatible Standard / Compatible connection; do not select Open Responses for the current RelayLM runtime |
| RelayLM endpoints | `/healthz`, `/v1/models`, `/v1/chat/completions` |

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

In OpenWebUI, go to **Admin Settings -> Connections -> OpenAI -> Add Connection**, choose **Standard / Compatible** when that tab is available, and set the API URL to:

```text
http://127.0.0.1:8090/v1
```

Do not choose Open Responses for the current RelayLM runtime; `/v1/responses` is not implemented.

For Open-LLM-VTuber or another compatible frontend, configure its OpenAI-compatible Chat Completions base URL to the same endpoint.

### 5. Verify the installation

With the backend model loaded, check health, routes, and one non-stream response:

```bash
curl http://127.0.0.1:8090/healthz
curl http://127.0.0.1:8090/v1/models
curl http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"relaylm-work-assistant","messages":[{"role":"user","content":"hello"}],"stream":false}'
```

## 🧰 Troubleshooting

Connection problem? See the [OpenWebUI + RelayLM + LM Studio troubleshooting guide](docs/smoke/openwebui_lmstudio_troubleshooting.md).

## 🏗️ Architecture

The canonical target runtime order is:

```text
User input
  -> RelayRUN request shell
  -> PipelineContext
  -> RelayREL target relationship selection
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
  -> MEM update candidates / SCENE update candidates / REL update candidates / SOUL proposals
  -> persistence and approval gates
```

This is the canonical responsibility order, not a claim that every stage is already active. Consult [Project Status](docs/PROJECT_STATUS.md) and the [Current / Target / Migration Guide](docs/architecture/current_target_migration_guide.md) for implementation status.

| When | Relay component | What it does |
|---|---|---|
| Throughout the request | 🎛️ **RelayRUN** | Manages stage order, recovery, checkpoints, and trace |
| Target input architecture | 🤝 **RelayREL** | Selects relationship-specific interaction policy before scene resolution |
| Input | 🌬️ **RelaySCN** | Classifies the scene and resolves memory, expression, and persistence policy |
| Input and output | 🙂 **RelayEMO** | Interprets affect cues and adjusts scene-appropriate expression |
| Input | 🚦 **RelayINT** | Detects intent and ambiguity, then decides whether to continue, ask, or stop |
| Input | 🧠 **RelayMEM** | Reads long-term memory relevant to the current response |
| Before and after the LLM | 📦 **RelayCTX** | Packs LLM input and separates visible output from internal data |
| Output | 🔎 **RelayREF** | Observes the generated response and records diagnostics |
| After the response | 🌙 **RelaySLP** | Organizes memory and SOUL update candidates outside the response path |

For authoritative ownership and order, see the [Pipeline Responsibility Design](docs/architecture/pipeline_responsibility_design.md).

## 📚 Documentation

- 📍 [Current project status](docs/PROJECT_STATUS.md)
- 🗺️ [Documentation index](docs/README.md)
- 🧬 [File-first Character Workspace design](docs/architecture/file_first_character_workspace_design.md)
- 🧭 [Character template creation flow](docs/architecture/character_template_creation_flow.md)
- 🏗️ [Architecture documents](docs/architecture/README.md)
- 🧭 [Project execution plan](docs/architecture/project_execution_plan.md)
- 🚀 [OpenWebUI + LM Studio MVP guide](docs/openwebui_lmstudio_mvp.md)
- ⚙️ [Configuration schema](docs/config_schema.md)
- 📜 [Contracts](docs/contracts/README.md)
- 🧪 [Smoke tests and validation](docs/smoke/README.md)
- 🧬 [RelaySOUL design and gates](docs/relaysoul/README.md)
- 🗃️ [MVP summaries and milestone history](docs/mvp/README.md)

## 🔗 Backend cache boundary

RelayLM does not materialize, persist, offload, transfer, or directly mutate backend KV cache. Optional cache infrastructure belongs to the inference backend or an external runtime layer behind the backend adapter.

RelayLM remains responsible only for compiling approved context into a stable, cache-friendly prompt layout where practical; it does not require a particular cache implementation.

## 📄 License

RelayLM is licensed under the [Apache License 2.0](LICENSE).
