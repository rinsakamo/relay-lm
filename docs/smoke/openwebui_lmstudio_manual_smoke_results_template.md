# OpenWebUI + LM Studio Manual Smoke Results Template

## Scope

Use this template for a real local OpenWebUI -> RelayLM -> LM Studio validation run.

Detailed procedures:

- [Client history exclusion manual smoke](client_history_exclusion_manual_smoke.md)
- [RelayRUN recovery diagnostics manual smoke](relayrun_recovery_diagnostics_manual_smoke.md)

Latest historical filled sample: [2026-05-26 result](openwebui_lmstudio_manual_smoke_result_2026_05_26.md).

## Environment

- date / JST date:
- OS / host:
- WSL networking mode if applicable: NAT / mirrored / unknown
- Python version:
- RelayLM commit SHA:
- LM Studio version:
- loaded backend model ID:
- OpenWebUI version:

## Config

- config file:
- copied from `examples/config/openwebui_lmstudio.yaml`? yes / no
- backend URL:
- RelayLM URL:
- route ID:
- route mode:
- backend model mapping changed from `local-model`? details:
- remote backend used? yes / no
- intentional differences reviewed? yes / no

### Managed history controls

Minimal apply controls:

- `client_history_exclusion_apply_enabled`:
- `client_history_exclusion_apply_dry_run_only`:

Optional diagnostics controls:

- `client_message_canonicalization_dry_run_enabled`:
- `client_history_exclusion_preflight_enabled`:

## Deterministic local smokes

```bash
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
python scripts/relaylm_client_history_exclusion_apply_runtime_smoke.py
python scripts/relaylm_client_history_exclusion_apply_forward_gate_smoke.py
python scripts/relaylm_profile_loading_smoke.py
python scripts/relaylm_config_room_scene_compat_smoke.py
```

- config coverage and copy-ready config:
- fake-backend proxy:
- history-exclusion runtime:
- history-exclusion forward gate:
- current profile ownership:
- optional room/scene compatibility:
- notes:

## LM Studio direct

- `/v1/models`:
- non-stream completion:
- stream completion:
- notes:

## RelayLM route

- `/healthz`:
- `/v1/models`:
- non-stream:
- stream:
- notes:

## OpenWebUI

- connection path: Admin Settings -> Connections -> OpenAI
- connection protocol: Standard / Compatible / other
- Open Responses selected? yes / no
- Base/API URL:
- API key type:
- model preset/avatar:
- route IDs configured:
- notes:

## Route response differentiation

| prompt ID | route ID | response summary | persona fit | memory/context fit | invented past fact? | too generic? | pass/fail |
|---|---|---|---|---|---|---|---|
| P1 | relaylm-companion | | | | | | |
| P1 | relaylm-work-assistant | | | | | | |
| P1 | relaylm-code-reviewer | | | | | | |

## History-exclusion matrix

Observation method: `script_verified`, `manually_captured`, or `not_observable_in_environment`.

| case | route mode | client instruction? | apply enabled | dry-run-only | result status | payload changed? | prior history backend-bound? | backend forwarded? | observation method | pass/fail |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| A default compatibility | memory_light | no | false | true | | | | | | |
| B dry-run candidate | memory_light | no | true | true | | | | | | |
| C actual no-instruction | memory_light | no | true | false | | | | | | |
| D unsupported instruction | memory_light | yes | true | false | | | | | | |
| E pass-through exemption | pass_through | any | true | false | | | | | | |

### Backend payload summary

- exact payload captured? yes / no / unavailable
- capture method:
- compiled system/prefix message count:
- preserved current user message count:
- prior user/assistant history count:
- client system/developer message count:
- notes:

### Content-free diagnostics

- user message bodies absent:
- backend response bodies absent:
- memory/snippet/page bodies absent:
- compiled prompt bodies absent:
- generated final text absent:
- local path or credential-bearing value absent:
- pass/fail:

## RelayRUN recovery diagnostics

### Normal conversation baseline

- prompt class:
- backend response returned normally? yes / no
- OpenWebUI error banner? yes / no
- visible recovery text appeared? yes / no
- pass/fail:

### Artifacts observed

- `runtime_checkpoint`:
- `recovery_transition_artifact`:
- `waiting_user_contract`:
- `recovery_apply_preflight`:
- `recovery_response_draft`:
- `visible_recovery_response_preflight`:
- `recovery_response_generator`:
- `output_relayscn_recovery_gate`:
- `visible_recovery_apply_preflight`:
- `user_action_contract`:

### Safety assertions

- `diagnostics_only=true` or equivalent:
- `user_visible_allowed=false` or equivalent:
- `final_text_generated=false`:
- `backend_payload_mutation_allowed=false` or equivalent:
- `response_body_mutation_allowed=false` or equivalent:
- `direct_user_output_allowed=false` or equivalent:
- `run_direct_text_finalization_allowed=false` or equivalent:
- recovery chain remained blocked/fail-closed where required:

### Mutation checks

- backend payload inspected? yes / no / unavailable
- recovery artifacts absent from backend payload? yes / no / unavailable
- backend response body returned unchanged? yes / no / unavailable
- visible recovery output appeared? yes / no
- pass/fail:

## Failure log

| symptom | suspected layer | next action |
|---|---|---|
| | LM Studio / RelayLM config / RelayLM proxy / OpenWebUI / history authority / recovery diagnostics / backend model | |

## Final verdict

- overall: pass / partial / fail
- blocking issue:
- safe to use current default compatibility path? yes / no / conditions:
- safe to enable no-instruction actual apply? yes / no / test-only:
- next docs follow-up:
- next code follow-up:
- next environment/config follow-up:
