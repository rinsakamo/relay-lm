# Client History Exclusion Manual Smoke

## Purpose

Validate the current managed-route history-authority boundary without confusing default compatibility behavior with the gated v0/v1 current-turn reconstruction paths.

## Deterministic source of truth

Run:

```bash
python scripts/relaylm_client_history_exclusion_apply_contract_smoke.py
python scripts/relaylm_client_history_exclusion_apply_runtime_smoke.py
python scripts/relaylm_client_history_exclusion_apply_forward_gate_smoke.py
python scripts/relaylm_phase5c4a_runtime_smoke.py
```

These scripts verify:

- default-off behavior,
- dry-run candidate generation without payload mutation,
- v0 no-instruction actual apply,
- v1 instruction-bearing actual apply with explicit request-local provenance,
- missing or invalid v1 provenance failing closed,
- pass-through exemption,
- exact backend forward-gate enforcement,
- content-free diagnostics and errors.

`relaylm_openwebui_lmstudio_proxy_smoke.py` contains the repository-standard fake backend and payload-capture implementation.

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

## v0 no-instruction test chain

Use a managed `memory_light` route and a non-sensitive payload with no client `system` or `developer` message:

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

## v1 instruction-bearing test chain

Use an explicit request-local provenance envelope. The selected index must point to a current `system` or `developer` candidate before the latest user turn.

```json
{
  "model": "relaylm-companion",
  "messages": [
    {"role": "system", "content": "Answer as a concise technical reviewer."},
    {"role": "user", "content": "old turn"},
    {"role": "assistant", "content": "old reply"},
    {"role": "user", "content": "current turn"}
  ],
  "relaylm": {
    "instruction_evidence": {
      "schema_version": "client_instruction_source.v1",
      "message_indices": [0]
    }
  },
  "stream": false
}
```

Role, wording, and position alone do not establish provenance. The reserved `relaylm` control envelope is removed before managed backend forwarding.

## Matrix

### A. Default compatibility

```yaml
client_history_exclusion_apply_enabled: false
client_history_exclusion_apply_dry_run_only: true
```

Expected:

- request completes through the compatibility path,
- no applied result is required,
- previous client turns may remain backend-bound,
- this does not prove current-turn-only reconstruction.

### B. Dry-run candidate

```yaml
client_history_exclusion_apply_enabled: true
client_history_exclusion_apply_dry_run_only: true
```

Expected for a supported v0 or v1 request:

- result status is `ready`,
- a request-local payload candidate exists,
- `payload_mutation_applied=false`,
- backend receives the unchanged compatibility payload.

### C. Actual v0 no-instruction apply

```yaml
client_history_exclusion_apply_enabled: true
client_history_exclusion_apply_dry_run_only: false
```

Use the v0 test chain.

Expected backend-bound messages:

1. one RelayLM-owned compiled system/prefix message,
2. the exact validated current user message.

Expected result:

- schema is `client_history_exclusion_apply.v0`,
- status is `applied`,
- `payload_mutation_applied=true`,
- previous user/assistant history is absent,
- backend forwarding proceeds.

### D. Actual v1 instruction-bearing apply

Keep Case C settings and use the v1 test chain.

Expected backend-bound messages:

1. one RelayLM-owned compiled system message containing approved RelayLM blocks plus one bounded escaped low-trust instruction-evidence block,
2. the exact validated current user message.

Expected result:

- schema is `client_history_exclusion_apply.v1`,
- explicit `client_instruction_source.v1` selection is validated,
- status is `applied`,
- previous history, raw instruction objects, unselected instruction candidates, and the reserved control envelope are absent,
- backend forwarding proceeds only for the exact selected candidate.

### E. Missing or invalid v1 provenance

Keep actual-apply settings and add client `system` or `developer` messages without a valid provenance envelope. Also test duplicate, unordered, out-of-range, post-user, non-instruction, and identity-mismatched indices.

Expected:

- apply result is blocked,
- backend forward gate blocks the request,
- raw prior history and instruction messages are not restored as fallback,
- no successful assistant response is fabricated.

### F. Explicit pass-through exemption

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
- apply settings,
- request class: default, v0, valid-v1, invalid-v1, or pass-through,
- result schema and status,
- payload-mutation boolean,
- backend-forwarding boolean,
- backend message role/count summary when captured,
- observation method,
- pass/fail.
