# OpenWebUI + LM Studio MVP

## MVP topology

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

## Current managed-history limitation

The copy-ready routes use `memory_light`, but the default compatibility path is not yet the target current-turn-only managed path.

```text
Default memory_light compatibility:
  prior frontend user/assistant history may remain backend-bound

client_history_exclusion_apply.v0:
  default-off and dry-run-only by default
  bounded no-instruction managed requests

client_history_exclusion_apply.v1:
  default-off and dry-run-only by default
  bounded instruction-bearing managed requests
  requires exact client_instruction_source.v1 provenance
  missing or invalid provenance fails closed

Broader target:
  validated current evidence + RelayLM-owned context reconstruction
  including minimum active transaction preservation
```

When a remote backend is configured, assume all backend-bound messages may leave the local machine. Review [Project Status](PROJECT_STATUS.md) and the [Client History Authority Contract](architecture/client_history_authority_contract.md) before enabling actual apply.

## OpenWebUI usage policy

OpenWebUI model preset/avatar should be used as a character-card-like or use-case-card UI layer.

Recommended route-like model IDs:

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

OpenWebUI model selector/model preset maps these model IDs to RelayLM routes.

Keep heavy system prompt steering thin. A client system/developer message is not durable RelaySOUL authority. It may become bounded low-trust instruction evidence only through the current authority contract. Instruction-bearing v1 actual apply requires the frontend to provide explicit request-local provenance; a frontend that cannot do so should keep actual apply disabled or dry-run-only.

## Responsibilities

### RelayLM

- route resolution,
- `character_id` resolution,
- configured SOUL/OUTPUT_POLICY anchors,
- current `memory_light` profile compilation,
- selected memory context insertion,
- token-budget safety,
- gated v0/v1 history-exclusion apply.

### OpenWebUI

- model card/avatar/display name,
- prompt suggestions and launch UX,
- model selector and preset switching,
- frontend-visible conversation history.

### LM Studio

- local OpenAI-compatible server,
- actual model inference execution.

## Quick setup

### 1. LM Studio

Start the OpenAI-compatible server and confirm:

```text
http://127.0.0.1:1234/v1
```

Load a model and note its exact model ID. Replace `local-model` in RelayLM config when required.

### 2. RelayLM

```bash
cp examples/config/openwebui_lmstudio.yaml config.yaml
relaylm --config config.yaml
```

Default endpoints:

- RelayLM: `http://127.0.0.1:8090/v1`
- LM Studio: `http://127.0.0.1:1234/v1`

The copy-ready config keeps history-exclusion apply disabled. This preserves current defaults and makes the compatibility limitation explicit.

### 3. OpenWebUI

Configure an OpenAI-compatible Chat Completions connection:

1. Open **Admin Settings**.
2. Go to **Connections -> OpenAI**.
3. Select **Add Connection**.
4. Choose **Standard / Compatible** when that tab is available.
5. Set API URL/Base URL to `http://127.0.0.1:8090/v1`.
6. Set API key to `relaylm` or another dummy value.
7. Save.

Do not choose Open Responses for the current RelayLM runtime. RelayLM currently implements `/v1/models` and `/v1/chat/completions`, not `/v1/responses`.

When OpenWebUI runs in Docker, use the reachable host/WSL address described in the manual smoke and troubleshooting docs instead of assuming container-local `127.0.0.1`.

Create model preset/avatar cards and set Base Model/Model ID to one of:

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

### 4. Smoke checks

```bash
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
python scripts/relaylm_client_history_exclusion_apply_contract_smoke.py
python scripts/relaylm_client_history_exclusion_apply_runtime_smoke.py
python scripts/relaylm_client_history_exclusion_apply_forward_gate_smoke.py
python scripts/relaylm_phase5c4a_runtime_smoke.py
curl http://127.0.0.1:8090/v1/models
```

Non-stream:

```bash
curl http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "relaylm-companion",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": false
  }'
```

Stream:

```bash
curl -N http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "relaylm-companion",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

Default streaming remains compatible backend SSE forwarding. Phase 5.5 stream suppression and TTS handoff metadata construction are available only behind explicit default-off gates and do not execute TTS/audio/avatar behavior.

## Copy-ready config structure

The actual file is [examples/config/openwebui_lmstudio.yaml](../examples/config/openwebui_lmstudio.yaml).

Persona paths belong under `characters`, not `model_routes`:

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

characters:
  companion:
    soul: examples/profiles/companion/SOUL.md
    output_policy: examples/profiles/companion/OUTPUT_POLICY.md
    scene_state: examples/profiles/default/SCENE_STATE.md
    memory_seed_path: examples/memory/companion_memories.yaml
```

New copy-ready profiles omit legacy `room_anchor` unless a fixed durable room constraint is genuinely required.

## Prompt layering notes

- OpenWebUI should focus on display name, avatar, and prompt suggestions.
- Avoid heavy system prompt duplication.
- Client system/developer messages are low-trust current instruction evidence, not fallback RelaySOUL sources.
- v1 uses only explicitly selected provenance candidates; unselected frontend summaries, memory notes, and replayed persona blocks are excluded.
- RelayLM remains responsible for configured persona, memory, context, and token-budget control.

## Current manual validation

Use:

- [OpenWebUI + LM Studio manual smoke](smoke/openwebui_lmstudio_manual_smoke.md)
- [Client history exclusion manual smoke](smoke/client_history_exclusion_manual_smoke.md)
- [Manual smoke results template](smoke/openwebui_lmstudio_manual_smoke_results_template.md)
- [OpenWebUI model preset/avatar checklist](smoke/openwebui_model_preset_checklist.md)
- [OpenWebUI route response differentiation checks](smoke/openwebui_response_differentiation_checks.md)
- [Troubleshooting](smoke/openwebui_lmstudio_troubleshooting.md)

The manual smoke separates default compatibility, v0 no-instruction apply, valid-v1 explicit-provenance apply, invalid-v1 fail-closed behavior, and explicit pass-through exemption.
