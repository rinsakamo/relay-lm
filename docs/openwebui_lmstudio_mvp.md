# OpenWebUI + LM Studio MVP

## MVP topology

RelayLM standard MVP UI/backend topology is:

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

## Positioning

- OpenWebUI is the standard MVP frontend.
- LM Studio is the standard MVP local OpenAI-compatible backend.
- RelayLM is the OpenAI-compatible persona/memory context proxy between them.
- Open-LLM-VTuber remains an optional frontend and example integration path.

## OpenWebUI usage policy

OpenWebUI model preset / avatar should be used as a character-card-like or use-case-card UI layer.

Recommended route-like model IDs (abstract names, no concrete character names):

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

OpenWebUI model selector/model preset should map these model IDs to RelayLM routes.

## RelayLM responsibilities

RelayLM owns context and routing control:

- route resolution
- `character_id` or persona profile id resolution
- `SOUL` / `OUTPUT_POLICY` persona anchors
- `memory_light` context insertion
- recent turns shaping
- token budget safety

## OpenWebUI responsibilities

OpenWebUI owns lightweight presentation and interaction scaffolding:

- model card / avatar / display name
- prompt suggestions and launch UX
- model selector and preset switching

To avoid duplication/conflict, heavy system prompt steering should stay thin in OpenWebUI and not duplicate RelayLM persona policy blocks.

## LM Studio responsibilities

LM Studio owns backend inference runtime:

- local OpenAI-compatible backend endpoint
- actual model inference execution

## Open-LLM-VTuber position

Open-LLM-VTuber is supported as an optional frontend / example integration.

It is not the default MVP standard UI in this positioning update.


## Quick setup (config-first)

- Manual smoke runbook: [OpenWebUI + LM Studio manual smoke](docs/openwebui_lmstudio_manual_smoke.md)
- Model preset/avatar checklist: [OpenWebUI model preset/avatar checklist](docs/openwebui_model_preset_checklist.md)

### 1) LM Studio

Start LM Studio OpenAI-compatible server and ensure the endpoint is reachable:

- `http://127.0.0.1:1234/v1`

### 2) RelayLM

Point RelayLM backend to LM Studio and expose RelayLM as OpenAI-compatible endpoint:

Copy-ready config example:

```bash
cp examples/config/openwebui_lmstudio.yaml config.yaml
```

Then start RelayLM with that config.


- RelayLM listen URL example: `http://127.0.0.1:8090/v1`
- LM Studio backend URL example: `http://127.0.0.1:1234/v1`

Minimal route mapping example:

```yaml
backends:
  lmstudio_backend:
    type: openai_compatible
    base_url: http://127.0.0.1:1234/v1
    api_key: relaylm
    default_model: local-model

model_routes:
  relaylm-companion:
    backend: lmstudio_backend
    backend_model: local-model
    character_id: companion
    mode: memory_light
    cache_namespace: character/companion
    memory_namespace: character/companion

  relaylm-work-assistant:
    backend: lmstudio_backend
    backend_model: local-model
    character_id: work_assistant
    mode: memory_light
    cache_namespace: character/work-assistant
    memory_namespace: character/work-assistant

  relaylm-code-reviewer:
    backend: lmstudio_backend
    backend_model: local-model
    character_id: code_reviewer
    mode: memory_light
    cache_namespace: character/code-reviewer
    memory_namespace: character/code-reviewer

characters:
  companion:
    soul: examples/profiles/companion/SOUL.md
    output_policy: examples/profiles/companion/OUTPUT_POLICY.md
    room_anchor: examples/profiles/default/ROOM_ANCHOR.md
    scene_state: examples/profiles/default/SCENE_STATE.md
    memory_seed_path: examples/memory/companion_memories.yaml

  work_assistant:
    soul: examples/profiles/work_assistant/SOUL.md
    output_policy: examples/profiles/work_assistant/OUTPUT_POLICY.md
    room_anchor: examples/profiles/default/ROOM_ANCHOR.md
    scene_state: examples/profiles/default/SCENE_STATE.md
    memory_seed_path: examples/memory/work_assistant_memories.yaml

  code_reviewer:
    soul: examples/profiles/code_reviewer/SOUL.md
    output_policy: examples/profiles/code_reviewer/OUTPUT_POLICY.md
    room_anchor: examples/profiles/default/ROOM_ANCHOR.md
    scene_state: examples/profiles/default/SCENE_STATE.md
    memory_seed_path: examples/memory/code_reviewer_memories.yaml
```

### 3) OpenWebUI

Configure OpenAI-compatible connection in OpenWebUI:

- Base URL: `http://127.0.0.1:8090/v1`
- API key: `relaylm` (dummy is acceptable)

Create model preset / avatar cards and set Base Model (Model ID) to one of:

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

### 4) Smoke checks

Check route publication:

```bash
curl http://127.0.0.1:8090/v1/models
```

Non-streaming completion:

```bash
curl http://127.0.0.1:8090/v1/chat/completions   -H 'content-type: application/json'   -d '{
    "model": "relaylm-companion",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": false
  }'
```

Streaming completion:

```bash
curl -N http://127.0.0.1:8090/v1/chat/completions   -H 'content-type: application/json'   -d '{
    "model": "relaylm-companion",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

Config-only local smoke command:

```bash
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

## Prompt layering notes

- OpenWebUI should focus on display name / avatar / prompt suggestions.
- Avoid heavy system prompt duplication in OpenWebUI when RelayLM already provides `SOUL`/`OUTPUT_POLICY`.
- RelayLM remains responsible for persona/memory/context/token-budget control.


## Example profiles and memory seeds

RelayLM repository includes abstract example profiles for the OpenWebUI route IDs:

- `examples/profiles/companion/SOUL.md`
- `examples/profiles/companion/OUTPUT_POLICY.md`
- `examples/profiles/work_assistant/SOUL.md`
- `examples/profiles/work_assistant/OUTPUT_POLICY.md`
- `examples/profiles/code_reviewer/SOUL.md`
- `examples/profiles/code_reviewer/OUTPUT_POLICY.md`

Optional memory seed examples:

- `examples/memory/companion_memories.yaml`
- `examples/memory/work_assistant_memories.yaml`
- `examples/memory/code_reviewer_memories.yaml`

When mapping OpenWebUI preset model IDs to RelayLM routes, bind each route to its matching abstract `character_id` profile and seed file.
