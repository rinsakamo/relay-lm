# OpenWebUI + RelayLM + LM Studio Troubleshooting

## Scope

Real local setup troubleshooting for:

```text
OpenWebUI
  -> RelayLM
  -> LM Studio
```

See [manual smoke runbook](openwebui_lmstudio_manual_smoke.md).

## 1. WSL -> Windows LM Studio

### Symptom

- WSL cannot reach LM Studio on Windows.

### Networking-mode-aware check

First try:

```bash
curl http://127.0.0.1:1234/v1/models
```

- In WSL mirrored networking mode, Windows and WSL can connect through `127.0.0.1`.
- In default NAT networking mode, WSL normally needs the Windows host IP.

```bash
WIN_HOST=$(ip route show default | awk '{print $3}')
echo "$WIN_HOST"
curl http://${WIN_HOST}:1234/v1/models
```

Fixes for host-IP access:

- enable LM Studio local-network serving,
- allow TCP 1234 in Windows Firewall,
- remember that the host IP may change.

## 2. OpenWebUI container -> RelayLM

### Symptom

- OpenWebUI cannot connect to RelayLM.

Checks:

```bash
curl http://127.0.0.1:8090/v1/models
```

From Docker, try:

```text
http://host.docker.internal:8090/v1
```

If RelayLM runs in WSL and that path fails:

```bash
hostname -I
docker exec open-webui curl http://<WSL_IP>:8090/v1/models
```

Possible fix:

```yaml
listen:
  host: 0.0.0.0
  port: 8090
```

Security note: `0.0.0.0` exposes RelayLM beyond loopback. Use firewall/network controls and do not expose an unauthenticated development proxy publicly.

## 3. Wrong OpenWebUI configuration area

### Symptom

```text
OPTIONS /v1/openapi.json 404 Not Found
```

Fix:

- use **Admin Settings -> Connections -> OpenAI**,
- do not configure RelayLM as a Tools/OpenAPI server.

## 4. Open Responses versus Chat Completions

### Symptom

```text
POST /v1/responses 404 Not Found
```

Fix:

- add an OpenAI connection,
- choose **Standard / Compatible** when available,
- do not choose Open Responses,
- use RelayLM's `/v1/models` and `/v1/chat/completions` endpoints.

`/v1/responses` is not currently implemented.

## 5. Route/model mismatch

### Symptoms

- route missing from OpenWebUI,
- backend reports unknown model,
- wrong profile responds.

Checks:

```bash
curl http://127.0.0.1:8090/v1/models
curl http://127.0.0.1:1234/v1/models
```

Verify:

- OpenWebUI Base Model equals a RelayLM `model_routes` key,
- route `backend` exists,
- `backend_model` matches the loaded LM Studio model ID,
- managed route `character_id` exists under `characters`.

## 6. Profile configuration error

### Symptoms

- `ProfileConfigurationError`,
- missing profile file,
- managed route fails before backend forward.

Current managed profiles require:

- `character_id`,
- matching `characters` entry,
- `soul`,
- `output_policy`,
- character-level or top-level `common_runtime_policy`.

Client system prompts are not fallback SOUL sources. Fix the configured profile rather than promoting frontend prompt text into durable persona authority.

## 7. Unexpected prior history reaches backend

### Cause

Current default `memory_light` compatibility compilation may preserve previous frontend user/assistant messages. History-exclusion apply is default-off.

Check:

```yaml
client_message_canonicalization_dry_run_enabled: false
client_history_exclusion_preflight_enabled: false
client_history_exclusion_apply_enabled: false
client_history_exclusion_apply_dry_run_only: true
```

This default is expected compatibility behavior, not a proof that current-turn-only reconstruction is active.

For test-only no-instruction apply validation, follow the manual smoke matrix. Do not enable actual apply for instruction-bearing requests; current v0 blocks them fail-closed.

## 8. Backend forward blocked after enabling history apply

Expected causes include:

- client system/developer message present,
- preflight not ready,
- unsupported request shape,
- no exact `applied` result,
- runtime preparation blocked.

This is intentional fail-closed behavior. Do not disable the gate by restoring raw prior history. Return to dry-run/default settings and inspect typed status/reason metadata.

Explicit `pass_through` routes are exempt from the managed apply requirement.

## 9. Streaming stalls

- test non-stream first,
- test LM Studio direct stream,
- verify proxy connectivity,
- remember current streaming is primarily backend SSE forwarding,
- do not expect Stream Unpack or TTS-safe segmentation yet.

## 10. Known-good historical values

The 2026-05-26 recorded result observed:

- backend model `qwen3.5-9b-ud-japanese-imatrix`,
- LM Studio from WSL at a run-specific `172.x.x.x:1234/v1`,
- RelayLM from Docker at a run-specific `172.x.x.x:8090/v1`.

These are historical run observations, not stable defaults. IP addresses and versions may change.

## 11. When to change code

Do not change runtime code for ordinary firewall, IP, wrong connection protocol, or model-ID problems.

Consider code changes only when:

- Chat Completions reaches RelayLM but RelayLM emits malformed responses,
- streaming format mismatch is reproducible,
- current authority gate behavior contradicts its typed contract,
- an explicit project decision adds `/v1/responses` support.
