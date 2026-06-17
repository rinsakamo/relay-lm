# Client History Exclusion Manual Smoke

## Purpose

Validate the current managed-route history authority boundary without confusing the default compatibility path with the target current-turn-only architecture.

## Deterministic source of truth

Run:

```bash
python scripts/relaylm_client_history_exclusion_apply_runtime_smoke.py
python scripts/relaylm_client_history_exclusion_apply_forward_gate_smoke.py
```

These scripts verify:

- default-off behavior,
- dry-run candidate generation without payload mutation,
- actual no-instruction apply,
- instruction-bearing fail-closed behavior,
- pass-through exemption,
- backend forward-gate enforcement.

`relaylm_openwebui_lmstudio_proxy_smoke.py` contains the repository-standard fake backend and payload capture implementation.

## Flag dependency

Minimal apply controls:

```yaml
client_history_exclusion_apply_enabled: true
client_history_exclusion_apply_dry_run_only: true
```

Set `client_history_exclusion_apply_dry_run_only: false` only for an intentional actual-apply test.

When apply is enabled, route resolution automatically enables the required preflight. These settings are optional diagnostics controls, not prerequisites for apply:

```yaml
client_message_canonicalization_dry_run_enabled: true
client_history_exclusion_preflight_enabled: true
```

## Test message chain

Use a managed `memory_light` route and a non-sensitive test payload:

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

## Matrix

### A. Default compatibility

```yaml
client_history_exclusion_apply_enabled: false
client_history_exclusion_apply_dry_run_only: true
```

Expected:

- request completes,
- no applied result is required,
- previous client turns may remain backend-bound,
- this is compatibility behavior.

### B. Dry-run candidate

```yaml
client_history_exclusion_apply_enabled: true
client_history_exclusion_apply_dry_run_only: true
```

Expected:

- result status is `ready`,
- a request-local payload candidate exists,
- `payload_mutation_applied=false`,
- backend receives the unchanged compatibility payload.

### C. Actual no-instruction apply

```yaml
client_history_exclusion_apply_enabled: true
client_history_exclusion_apply_dry_run_only: false
```

Expected backend-bound messages:

1. one RelayLM-owned compiled system/prefix message,
2. the validated current user message.

Expected result:

- status is `applied`,
- `payload_mutation_applied=true`,
- previous user/assistant history is absent,
- backend forwarding proceeds.

### D. Instruction-bearing unsupported apply

Keep Case C settings and add a client `system` or `developer` message.

Expected:

- apply result is blocked,
- backend forward gate blocks the request,
- previous history and raw instruction evidence are not restored as fallback,
- no successful assistant response is fabricated.

### E. Explicit pass-through exemption

Use a `pass_through` route with actual-apply settings.

Expected:

- result is skipped as exempt,
- compatible client messages remain delegated client authority,
- backend forwarding is not blocked by the managed apply requirement.

## Observation methods

Use one of these evidence levels:

- `script_verified`: deterministic repository smoke passed,
- `manually_captured`: exact backend payload captured with a local fake backend,
- `not_observable_in_environment`: exact role/count shape was not exposed by the selected backend UI.

A successful LM Studio response alone does not prove the exact backend-bound message list.

## Evidence

Record only content-free or redacted evidence:

- RelayLM commit SHA,
- route ID and applied mode,
- two apply settings,
- optional diagnostics settings,
- result status,
- payload mutation boolean,
- backend forwarding boolean,
- backend message role/count summary when captured,
- observation method,
- pass/fail.
