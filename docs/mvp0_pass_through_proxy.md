# MVP-0 Pass-through Proxy

MVP-0 adds the first runtime skeleton for RelayLM.

The goal is URL-swap compatibility:

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

MVP-0 does not implement memory, RAG, SOUL loading, OUTPUT_POLICY loading, or context compilation.

## Install

```bash
pip install -e .
```

## Configure

Copy the example config and edit the backend URL/model.

```bash
cp config.example.yaml config.yaml
```

Example:

```yaml
mode: pass_through

listen:
  host: 127.0.0.1
  port: 8090

backends:
  local_backend:
    type: openai_compatible
    base_url: http://127.0.0.1:8000/v1
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
    character_id: default
    mode: pass_through
    cache_namespace: character/default
    memory_namespace: character/default
```

## Run

```bash
relaylm --config config.yaml
```

or:

```bash
RELAYLM_CONFIG=config.yaml uvicorn relaylm.app:create_app --factory --host 127.0.0.1 --port 8090
```

## Check models

```bash
curl http://127.0.0.1:8090/v1/models
```

Expected model IDs are taken from `model_routes`.

## Check non-streaming chat

```bash
curl http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "relaylm-default",
    "messages": [
      {"role": "user", "content": "hello"}
    ],
    "stream": false
  }'
```

## Check streaming chat

```bash
curl -N http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "relaylm-default",
    "messages": [
      {"role": "user", "content": "hello"}
    ],
    "stream": true
  }'
```

## Open-LLM-VTuber config

Point the OpenAI-compatible provider at RelayLM:

```yaml
base_url: 'http://localhost:8090/v1'
llm_api_key: 'relaylm'
model: 'relaylm-default'
```

## MVP-0 behavior

- `/v1/models` returns route model names.
- `/v1/chat/completions` resolves the incoming `model` through `model_routes`.
- The request is forwarded to the configured backend.
- `backend_model` replaces the incoming model before forwarding.
- `stream: true` is forwarded as SSE bytes.
- `stream: false` is forwarded as JSON.
- route-not-found is returned as an OpenAI-style JSON error.

## Preserved seams

MVP-0 intentionally keeps these seams for later phases:

- config loader
- route resolver
- backend adapter
- request diagnostics
- mode field
- character ID field
- cache namespace field
- memory namespace field

The pass-through endpoint should not grow memory or context compiler logic directly. Later phases should add those behind the existing route/config/compiler seams.
