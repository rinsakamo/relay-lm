# OpenWebUI + LM Studio Manual Smoke Runbook

## Scope

This runbook verifies the real local connection path and the current managed-history and gated streaming boundaries.

Related docs:

- [Client history exclusion manual smoke](client_history_exclusion_manual_smoke.md)
- [RelayRUN recovery diagnostics manual smoke](relayrun_recovery_diagnostics_manual_smoke.md)
- [OpenWebUI model preset/avatar checklist](openwebui_model_preset_checklist.md)
- [OpenWebUI route response differentiation checks](openwebui_response_differentiation_checks.md)
- [Manual smoke results template](openwebui_lmstudio_manual_smoke_results_template.md)
- [Troubleshooting guide](openwebui_lmstudio_troubleshooting.md)
- [Latest filled result: 2026-05-26](openwebui_lmstudio_manual_smoke_result_2026_05_26.md)

This is manual validation only. It does not change runtime behavior.

## Topology

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

## Current authority limitation

The copy-ready `memory_light` routes do not imply current-turn-only backend context.

With default settings:

- prior frontend user/assistant history may remain in backend-bound messages,
- history-exclusion apply is disabled and dry-run-only by default,
- v0 actual apply supports bounded no-instruction requests,
- v1 actual apply supports bounded instruction-bearing requests only with exact `client_instruction_source.v1` provenance,
- missing or invalid v1 provenance fails closed,
- explicit `pass_through` remains delegated client authority.

A remote backend receives the backend-bound message list. Use one only when the current exposure is acceptable.

## Prerequisites

- LM Studio OpenAI-compatible server is running.
- RelayLM is installed and `config.yaml` is prepared.
- OpenWebUI uses an OpenAI **Standard / Compatible** connection.
- Open Responses is not selected for RelayLM.
- The loaded LM Studio model ID matches RelayLM config.

## Step 1: LM Studio direct check

```bash
curl http://127.0.0.1:1234/v1/models
```

```bash
curl http://127.0.0.1:1234/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "local-model",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": false
  }'
```

If this fails, troubleshoot LM Studio before RelayLM/OpenWebUI.

### WSL -> Windows LM Studio

First try `127.0.0.1`.

- WSL mirrored networking: Windows and WSL can use `127.0.0.1` for each other.
- Default WSL NAT networking: obtain the Windows host IP from WSL.

```bash
WIN_HOST=$(ip route show default | awk '{print $3}')
curl http://${WIN_HOST}:1234/v1/models
```

When using the host IP, LM Studio must accept local-network connections and Windows Firewall must allow the port.

## Step 2: RelayLM startup

```bash
cp examples/config/openwebui_lmstudio.yaml config.yaml
relaylm --config config.yaml
```

Fallback:

```bash
python -m relaylm.app --config config.yaml
```

Record intentional differences:

```bash
git diff --no-index examples/config/openwebui_lmstudio.yaml config.yaml
```

## Step 3: deterministic local smokes

```bash
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
python scripts/relaylm_client_history_exclusion_apply_contract_smoke.py
python scripts/relaylm_client_history_exclusion_apply_runtime_smoke.py
python scripts/relaylm_client_history_exclusion_apply_forward_gate_smoke.py
python scripts/relaylm_phase5c4a_runtime_smoke.py
python scripts/relaylm_profile_loading_smoke.py
python scripts/relaylm_config_room_scene_compat_smoke.py
```

These scripts validate the copy-ready config, fake-backend proxy path, current profile ownership, exhaustive config-field coverage, v0/v1 managed history-exclusion behavior, exact forward gating, and optional legacy `room_anchor` compatibility.

Check route publication:

```bash
curl http://127.0.0.1:8090/v1/models
```

Expected IDs:

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

## Step 4: RelayLM non-stream and stream checks

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

Expected with default settings:

- non-stream returns a normal JSON completion,
- stream emits progressive SSE chunks,
- stream bytes remain compatible backend forwarding,
- Phase 5.5 apply-like stream behavior remains inactive until explicitly enabled.

When intentionally testing Phase 5.5 gates, use the dedicated deterministic smokes. B2 may suppress internal sentinels and C0 through C4 may emit content-free handoff metadata, but they must not execute TTS, generate audio, control an avatar, or replay already emitted visible chunks.

## Step 5: OpenWebUI connection

In OpenWebUI:

1. Open **Admin Settings**.
2. Go to **Connections -> OpenAI**.
3. Select **Add Connection**.
4. Choose **Standard / Compatible** when available.
5. Enter the RelayLM API URL.
6. Enter API key `relaylm` or a dummy value.
7. Save.

Current RelayLM supports `/v1/models` and `/v1/chat/completions`, not `/v1/responses`.

### Reachable Base URL

- same host: `http://127.0.0.1:8090/v1`
- OpenWebUI in Docker: try `http://host.docker.internal:8090/v1`
- Docker-to-WSL fallback: `http://<WSL_IP>:8090/v1`

```bash
hostname -I
docker exec open-webui curl http://<WSL_IP>:8090/v1/models
```

RelayLM may need `listen.host: 0.0.0.0` for container access. Use firewall/network controls and avoid accidental public exposure. UI-A7 `/lab/api/*` management reads remain loopback-only even when Core routes are exposed for a local container topology.

## Step 6: profile differentiation

Use the same LM Studio model and switch only RelayLM route/model IDs.

Expected:

- route-specific SOUL/OUTPUT_POLICY influence,
- route-specific configured memory-seed influence,
- no dependency on heavy OpenWebUI system prompts,
- no invented memory required for a pass.

Use the controlled prompts in [response differentiation checks](openwebui_response_differentiation_checks.md).

## Step 7: managed history authority

Run and record the dedicated [client history exclusion smoke](client_history_exclusion_manual_smoke.md).

It separates:

- default compatibility from dry-run and actual apply,
- v0 no-instruction from v1 explicit-provenance instruction-bearing apply,
- invalid or missing v1 provenance from valid v1 operation,
- managed routes from pass-through,
- deterministic script evidence from optional manual payload capture.

A successful LM Studio response alone does not establish the exact backend-bound message role/count list.

## Step 8: RelayRUN recovery diagnostics

Run and record the dedicated [RelayRUN recovery diagnostics smoke](relayrun_recovery_diagnostics_manual_smoke.md).

It preserves:

- config comparison and normal-chat baseline,
- expected recovery artifact order,
- explicit safety-field checks,
- backend-payload and response-body mutation checks,
- content-free evidence requirements.

## Overall pass/fail criteria

PASS requires:

- deterministic local smokes pass,
- direct LM Studio path works,
- RelayLM model list and non-stream/stream paths work,
- OpenWebUI uses Standard / Compatible and reaches RelayLM,
- route/profile behavior is plausible,
- managed history authority matches the dedicated v0/v1 matrix,
- recovery artifacts remain diagnostics-only and content-free,
- no internal marker or recovery artifact leaks into backend/user-visible content.

FAIL includes:

- OpenWebUI sends `/v1/responses`,
- managed actual apply restores previous history after a blocked result,
- valid v1 explicit-provenance apply is rejected contrary to the current contract,
- missing or invalid v1 provenance reaches the backend,
- pass-through is blocked as a managed route,
- content-bearing request/response/prompt data appears in persisted diagnostics,
- visible recovery text appears from the diagnostics-only chain,
- backend or response body changes unexpectedly,
- gated stream suppression replays or duplicates already emitted visible output.

## Evidence collection

Collect only redacted, shareable evidence:

- RelayLM commit SHA,
- deterministic smoke results,
- redacted config summary and intentional differences,
- OpenWebUI connection type and reachable URL class,
- LM Studio model ID,
- route ID and mode,
- managed-history request class and result,
- backend message role/count summary when captured,
- recovery artifact names and safety assertions,
- non-stream/stream/recovery pass/fail summary.
