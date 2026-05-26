# OpenWebUI + LM Studio Manual Smoke Runbook

## Scope

This document is a manual smoke runbook for connection/path verification.

Related checklist: [OpenWebUI model preset/avatar checklist](docs/openwebui_model_preset_checklist.md).

- manual smoke only
- no automated real backend integration test in this doc
- no runtime behavior change

## Topology

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

## Prerequisites

- LM Studio OpenAI-compatible server is running.
- RelayLM is installed and a config file is prepared.
- OpenWebUI OpenAI-compatible connection is configured.

## Step 1: LM Studio direct check

Check models directly on LM Studio:

```bash
curl http://127.0.0.1:1234/v1/models
```

Check non-streaming completion directly on LM Studio:

```bash
curl http://127.0.0.1:1234/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "local-model",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": false
  }'
```

If this fails, troubleshoot LM Studio first before RelayLM/OpenWebUI.

## Step 2: RelayLM startup


Recommended quick start config:

```bash
cp examples/config/openwebui_lmstudio.yaml config.yaml
```

Start RelayLM with your config:

```bash
python -m relaylm.app --config config.yaml
```

or:

```bash
relaylm --config config.yaml
```

## Step 3: RelayLM route check


Config-only local smoke (no real backend connection):

```bash
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

Proxy-path local smoke (fake backend, no LM Studio connection):

```bash
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

Check route model IDs exposed by RelayLM:

```bash
curl http://127.0.0.1:8090/v1/models
```

Expected route IDs (OpenWebUI preset side):

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

## Step 4: RelayLM non-stream check

```bash
curl http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "relaylm-companion",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": false
  }'
```

Expect a normal JSON completion response.

## Step 5: RelayLM streaming check

```bash
curl -N http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "relaylm-companion",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

Expect SSE chunks to stream progressively.

## Step 6: OpenWebUI connection check

In OpenWebUI OpenAI-compatible connection settings:

- Base URL: `http://127.0.0.1:8090/v1`
- API key: `relaylm` (dummy is acceptable)

Create model preset / avatar entries and bind model IDs to:

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

## Step 7: Character/profile differentiation check

Use the same LM Studio backend model and switch only RelayLM route/model IDs.

Expected behavior:

- route-specific `SOUL` and `OUTPUT_POLICY` influence appears in responses
- route-specific memory seed influence appears when memory path is configured
- no dependency on concrete character names

## Troubleshooting

- LM Studio not reachable:
  - verify LM Studio server is running
  - verify host/port/path (`/v1`) exactly
- model ID mismatch:
  - OpenWebUI preset model ID must match RelayLM `model_routes` key
- missing characters block / `ProfileConfigurationError`:
  - ensure each route `character_id` exists under `characters:`
  - ensure `soul` and `output_policy` file paths exist
- OpenWebUI system prompt duplication:
  - keep OpenWebUI prompt layer thin to avoid conflict with RelayLM persona blocks
- streaming stalls:
  - test non-stream first
  - test LM Studio direct stream to isolate backend vs proxy path
- CORS/network/localhost issues:
  - verify OpenWebUI process can access `127.0.0.1:8090`
- wrong backend model name:
  - verify `backend_model` or backend default model is valid on LM Studio

## Safety boundaries

This runbook does not add or require:

- actual persistence
- RelaySOUL apply execution
- persona file mutation
- backend forwarding payload changes beyond configured compile behavior
