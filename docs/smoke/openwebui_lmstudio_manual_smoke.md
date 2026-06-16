# OpenWebUI + LM Studio Manual Smoke Runbook

## Scope

This runbook verifies the real local connection path and current managed-history boundary.

Related docs:

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
- history-exclusion apply is disabled,
- no-instruction history-exclusion dry-run/apply is available only behind explicit gates,
- instruction-bearing managed apply is not implemented,
- explicit `pass_through` remains delegated client authority.

Do not use a remote backend unless this current message exposure is acceptable.

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

Record intentional changes from the copy-ready example.

## Step 3: local preflight smoke

```bash
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

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

Expected:

- non-stream returns a normal JSON completion,
- stream emits progressive SSE chunks,
- current stream path is primarily backend forwarding,
- no claim is made that Stream Unpack is active.

## Step 5: OpenWebUI connection

In OpenWebUI:

1. Open **Admin Settings**.
2. Go to **Connections -> OpenAI**.
3. Select **Add Connection**.
4. Choose **Standard / Compatible** when available.
5. Enter the RelayLM API URL.
6. Enter API key `relaylm` or a dummy value.
7. Save.

Do not choose Open Responses. Current RelayLM supports `/v1/models` and `/v1/chat/completions`, not `/v1/responses`.

### Reachable Base URL

- OpenWebUI runs directly on the same host: `http://127.0.0.1:8090/v1`
- OpenWebUI runs in Docker: try `http://host.docker.internal:8090/v1`
- Docker-to-WSL fallback: use `http://<WSL_IP>:8090/v1`

```bash
hostname -I
docker exec open-webui curl http://<WSL_IP>:8090/v1/models
```

RelayLM may need `listen.host: 0.0.0.0` for container access. Binding to all interfaces increases exposure; use firewall/network controls and do not expose RelayLM publicly by accident.

## Step 6: profile differentiation

Use the same LM Studio model and switch only RelayLM route/model IDs.

Expected:

- route-specific SOUL/OUTPUT_POLICY influence,
- route-specific configured memory-seed influence,
- no dependency on heavy OpenWebUI system prompts,
- no invented memory required for a pass.

Use the controlled prompts in [response differentiation checks](openwebui_response_differentiation_checks.md).

## Step 7: current history-exclusion matrix

Run this section only after recording the baseline config and using a test-only local backend or inspectable fake backend. Do not enable actual apply blindly against production traffic.

### Case A — default compatibility path

Config:

```yaml
client_message_canonicalization_dry_run_enabled: false
client_history_exclusion_preflight_enabled: false
client_history_exclusion_apply_enabled: false
client_history_exclusion_apply_dry_run_only: true
```

Send:

```json
{
  "model": "relaylm-companion",
  "messages": [
    {"role": "user", "content": "old turn"},
    {"role": "assistant", "content": "old reply"},
    {"role": "user", "content": "current turn"}
  ],
  "stream": false
}
```

Expected:

- request completes,
- no history-exclusion apply result is required,
- prior client history may remain in the backend-bound message list,
- this is compatibility behavior, not the target authority path.

### Case B — dry-run candidate

Config:

```yaml
client_message_canonicalization_dry_run_enabled: true
client_history_exclusion_preflight_enabled: true
client_history_exclusion_apply_enabled: true
client_history_exclusion_apply_dry_run_only: true
```

Use the same no-instruction message list.

Expected:

- backend request remains the compatibility payload,
- request-local history-exclusion candidate may be created,
- `payload_mutation_applied=false`,
- default persisted diagnostics remain content-free.

### Case C — actual no-instruction apply

Config:

```yaml
client_message_canonicalization_dry_run_enabled: true
client_history_exclusion_preflight_enabled: true
client_history_exclusion_apply_enabled: true
client_history_exclusion_apply_dry_run_only: false
```

Use a managed `memory_light` route with no client system/developer message.

Expected backend-bound message list:

1. one RelayLM-owned compiled system/prefix message,
2. the validated current user message.

Expected:

- prior user/assistant history is absent,
- status is `applied`,
- `payload_mutation_applied=true`,
- request completes normally.

### Case D — instruction-bearing unsupported actual apply

Keep Case C config and add a client `system` or `developer` message.

Expected:

- current v0 apply does not rebuild the unsupported request,
- backend forwarding is blocked fail-closed,
- raw prior history/instruction payload is not used as fallback,
- no fabricated successful assistant response.

### Case E — explicit pass-through exemption

Use an explicit `pass_through` route with actual-apply flags set.

Expected:

- route remains delegated client authority,
- compatible client messages are forwarded,
- managed history-exclusion forward gate does not block solely because no managed applied result exists.

## Step 8: RelayRUN recovery diagnostics

This section generalizes the historical MVP-38 checklist.

Recovery diagnostics are inspected through trace/diagnostic metadata, not through visible output.

Expected artifact order when present:

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

Expected boundaries:

- diagnostics-only,
- no direct user-visible recovery text,
- no backend-payload recovery artifact injection,
- no response-body mutation,
- no actual resume/retry/user-action apply,
- content-free persisted projections.

## Pass/fail criteria

PASS requires:

- direct LM Studio path works,
- RelayLM model list and non-stream/stream paths work,
- OpenWebUI uses Standard / Compatible and reaches RelayLM,
- route/profile behavior is plausible,
- each history-exclusion matrix case matches its documented authority behavior,
- recovery artifacts remain diagnostics-only and content-free,
- no internal marker or recovery artifact leaks into backend/user-visible content.

FAIL includes:

- OpenWebUI sends `/v1/responses`,
- managed actual apply restores raw prior history after a blocked result,
- instruction-bearing unsupported actual apply reaches the backend as raw fallback,
- pass-through is incorrectly blocked as a managed route,
- raw user/backend/snippet/prompt/final text appears in persisted diagnostics,
- visible recovery text appears from the diagnostics-only chain,
- backend or response body is mutated unexpectedly.

## Evidence collection

Collect only redacted, shareable evidence:

- RelayLM commit SHA,
- redacted config summary and intentional differences,
- OpenWebUI connection type and reachable URL class,
- LM Studio model ID,
- route ID and mode,
- history-exclusion flags and result status,
- backend message-role/count summary rather than message text,
- diagnostics artifact names and content-free assertion result,
- non-stream/stream/recovery pass/fail summary.
