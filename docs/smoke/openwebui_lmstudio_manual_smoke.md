# OpenWebUI + LM Studio Manual Smoke Runbook

## Scope

This document is a manual smoke runbook for connection/path verification.

Related checklist: [OpenWebUI model preset/avatar checklist](openwebui_model_preset_checklist.md).
Related differentiation checks: [OpenWebUI route response differentiation checks](openwebui_response_differentiation_checks.md).
Results template: [OpenWebUI + LM Studio manual smoke results template](openwebui_lmstudio_manual_smoke_results_template.md).
Troubleshooting guide: [OpenWebUI + RelayLM + LM Studio troubleshooting](openwebui_lmstudio_troubleshooting.md).
- Latest real run result: [OpenWebUI + RelayLM + LM Studio manual smoke result (2026-05-26)](openwebui_lmstudio_manual_smoke_result_2026_05_26.md)

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

If RelayLM runs on WSL and LM Studio runs on Windows host, note:

- `127.0.0.1` inside WSL points to WSL itself, not Windows host.
- discover Windows host IP from WSL:

```bash
WIN_HOST=$(ip route show default | awk '{print $3}')
```

- check LM Studio from WSL:

```bash
curl http://${WIN_HOST}:1234/v1/models
```

For Windows Firewall and LM Studio local network serving checks, see the troubleshooting guide.

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

In OpenWebUI OpenAI-compatible connection settings, use the Base URL that matches your runtime placement.

- API key: `relaylm` (dummy is acceptable)

Decision tree:

- OpenWebUI runs directly on host:
  - Base URL: `http://127.0.0.1:8090/v1`

- OpenWebUI runs in Docker container:
  1. try `host.docker.internal` first
  2. if it fails, use WSL IP

WSL IP check:

```bash
hostname -I
```

Container-side connectivity check:

```bash
docker exec open-webui curl http://<WSL_IP>:8090/v1/models
```

Docker/WSL fallback Base URL:

- `http://<WSL_IP>:8090/v1`

Note:

- RelayLM may need `listen.host: 0.0.0.0` so the container can reach it.
- WSL IP values are environment-dependent and may change after restart.

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

## MVP-38 preparation: RelayRUN recovery diagnostics manual smoke checklist

### Scope

This checklist prepares the MVP-38 real-environment smoke run. It is not an
MVP-37 execution record.

Use it to prepare checks that:

- verify the normal OpenWebUI -> RelayLM -> LM Studio conversation path is still
  working;
- verify RelayRUN recovery-chain artifacts are visible only through diagnostics
  and trace metadata;
- verify recovery diagnostics remain preflight-only and fail-closed;
- avoid testing or expecting actual user-visible recovery output.

### Non-goals

Do not use MVP-38 preparation to validate or enable:

- visible recovery response apply;
- response body mutation by RelayRUN recovery diagnostics;
- backend payload mutation by RelayRUN recovery diagnostics;
- actual resume;
- retry execution;
- user action parse or apply;
- stream recovery.

### Pre-test setup

Before running MVP-38 manual smoke:

1. Start LM Studio and confirm the OpenAI-compatible server is enabled.
2. Start RelayLM with a local `config.yaml` that prioritizes the normal
   conversation path.
3. Point OpenWebUI's OpenAI-compatible Base URL at RelayLM, not directly at LM
   Studio.
4. Keep recovery-related config flags default-off unless a specific diagnostics
   check explicitly requires enabling trace or diagnostics collection.
5. If diagnostics or trace are enabled, confirm where outputs are written and
   ensure no secrets are captured in shared evidence.
6. Before execution, compare `config.example.yaml` with local `config.yaml` and
   record intentional differences only.

Suggested config review before testing:

```bash
git diff --no-index config.example.yaml config.yaml
```

Review these items before the run:

- route/model mapping used by OpenWebUI;
- RelayLM listen host and port;
- LM Studio backend URL and model name;
- diagnostics enabled/disabled state;
- trace enabled/disabled state and trace path;
- recovery config flags remain default-off unless intentionally overridden for
  diagnostics visibility.

### Normal conversation smoke

Run normal chat first. Use a simple Japanese message such as:

```text
こんにちは。今日の作業を短く整理して。
```

Check at least one persona/profile route, for example `relaylm-companion`. If a
memory-light route is available in the local config, also check that route.

Expected normal-path result:

- OpenWebUI completes the request without an error banner.
- RelayLM returns the backend response body normally.
- LM Studio receives the expected normal chat request.
- RelayLM logs, diagnostics headers, and trace writing do not break the request.
- Route/persona behavior is plausible for the selected preset.
- No recovery text is injected into the user-visible response.

### Recovery diagnostics smoke preparation

Recovery diagnostics are checked through RelayLM diagnostics or trace metadata,
not through visible output.

For MVP-38, prepare to inspect that:

- recovery-chain artifact names appear in diagnostics/trace when the request path
  emits `relayrun_artifact`;
- backend payloads sent to LM Studio do not contain recovery artifacts;
- response bodies returned to OpenWebUI remain the backend response bodies;
- user-visible recovery text is not produced;
- `final_text_generated` remains `false` in recovery diagnostics artifacts;
- diagnostics remain content-free.

### Recovery chain expected artifact order

When `relayrun_artifact` is present, the recovery diagnostics chain should be
understood in this order:

1. `runtime_checkpoint`
2. `recovery_transition_artifact`
3. `waiting_user_contract`
4. `recovery_apply_preflight`
5. `recovery_response_draft`
6. `visible_recovery_response_preflight`
7. `recovery_response_generator`
8. `output_relayscn_recovery_gate`
9. `visible_recovery_apply_preflight`
10. `user_action_contract`

### Expected safety flags

For recovery diagnostics artifacts, expect fail-closed safety metadata such as:

- `diagnostics_only=true`
- `user_visible_allowed=false`
- `final_text_generated=false`
- `backend_payload_mutation_allowed=false`
- `response_body_mutation_allowed=false`
- `direct_user_output_allowed=false`
- `run_direct_text_finalization_allowed=false`

Some upstream artifacts may use older field names, but the expected operational
boundary is the same: no direct user-visible recovery output and no payload or
response mutation.

### Manual pass/fail criteria

PASS criteria:

- normal chat works through OpenWebUI -> RelayLM -> LM Studio;
- OpenWebUI receives a normal backend response;
- no recovery artifact appears in the backend payload sent to LM Studio;
- response body is not mutated by RelayRUN recovery diagnostics;
- trace/diagnostics artifacts are content-free;
- recovery chain remains blocked and fail-closed;
- no user-visible recovery output appears.

FAIL criteria:

- visible recovery text appears;
- response body changes unexpectedly;
- backend payload contains recovery artifact data;
- raw user/backend/snippet/prompt/final text appears inside a recovery artifact;
- OpenWebUI cannot complete normal chat;
- LM Studio receives unexpected recovery/system payload content.

### Evidence to collect in MVP-38

Collect only redacted, shareable evidence:

- redacted `config.yaml` summary;
- RelayLM startup command;
- OpenWebUI Base URL setting;
- LM Studio model name;
- normal chat prompt and result summary;
- diagnostics header summary;
- trace artifact names only;
- backend payload mutation check result;
- response body mutation check result;
- optional screenshots, with secrets and local tokens hidden.
