# OpenWebUI + RelayLM + LM Studio Troubleshooting

## Scope

- real local setup troubleshooting
- OpenWebUI -> RelayLM -> LM Studio
- Windows + WSL2 + Docker Desktop
- docs-only
- no runtime code change

## Quick topology

```text
OpenWebUI (Docker container)
  -> RelayLM (WSL)
  -> LM Studio (Windows host)
```

## 1) WSL -> Windows LM Studio

### Symptom

- `curl http://127.0.0.1:1234/v1/models` from WSL fails.
- curl to Windows host IP hangs or fails.

### Checks

- On Windows PowerShell:

```powershell
curl http://127.0.0.1:1234/v1/models
```

- On WSL (discover Windows host IP from default route):

```bash
WIN_HOST=$(ip route show default | awk '{print $3}')
echo "$WIN_HOST"
```

- On WSL (call LM Studio through Windows host IP):

```bash
curl http://${WIN_HOST}:1234/v1/models
```

### Fixes

- Enable LM Studio local network serving.
- Add/verify Windows Firewall inbound rule for TCP 1234.
- Note: Windows host IP as seen from WSL can change by restart/reconnect.

## 2) OpenWebUI container -> RelayLM

### Symptom

- OpenWebUI cannot connect to RelayLM.
- `host.docker.internal` hangs or fails for RelayLM path.

### Checks

- Verify RelayLM listen is `0.0.0.0:8090`.
- On WSL, get WSL-side IP:

```bash
hostname -I
```

- From container, test RelayLM model listing:

```bash
docker exec open-webui curl http://<WSL_IP>:8090/v1/models
```

### Fixes

- Use `http://<WSL_IP>:8090/v1` as OpenWebUI Base URL.
- Restart RelayLM after changing listen host.
- Note: WSL IP can change after restart.

## 3) OpenWebUI wrong configuration area

### Symptom

- RelayLM logs `OPTIONS /v1/openapi.json 404 Not Found`.
- OpenWebUI connection fails when configured under Tools/OpenAPI.

### Fix

- Configure RelayLM under OpenAI-compatible connection (OpenAI API connection), not Tools/OpenAPI.

## 4) Responses API vs Chat Completions

### Symptom

- RelayLM logs `POST /v1/responses 404 Not Found`.

### Fix

- Disable Responses API mode in OpenWebUI.
- Use Chat Completions / OpenAI-compatible chat completions.
- RelayLM currently supports `/v1/chat/completions`.
- `/v1/responses` compatibility shim is an optional future MVP topic and is not implemented now.

## 5) Working check commands

- LM Studio direct:

```bash
curl http://<WIN_HOST>:1234/v1/models
```

- RelayLM local:

```bash
curl http://127.0.0.1:8090/v1/models
```

- OpenWebUI container to RelayLM:

```bash
docker exec open-webui curl http://<WSL_IP>:8090/v1/models
```

- non-stream (`/v1/chat/completions`):

```bash
curl http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "relaylm-work-assistant",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": false
  }'
```

- stream (`/v1/chat/completions`):

```bash
curl -N http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "relaylm-work-assistant",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

## 6) Known-good observed values (2026-05-26)

- backend model: `qwen3.5-9b-ud-japanese-imatrix`
- LM Studio from WSL: `http://172.27.96.1:1234/v1`
- RelayLM from OpenWebUI container: `http://172.27.108.166:8090/v1`

These values are run-specific observations, not stable defaults. IPs can change after restart.

## 7) When to change code

Do not change RelayLM runtime code for firewall/IP/OpenWebUI configuration issues.

Consider runtime code changes only when:

- Chat Completions path works up to RelayLM but RelayLM outputs malformed responses.
- streaming response format mismatch is reproducibly observed.
- there is an explicit future MVP decision to support `/v1/responses`.
