# OpenWebUI + LM Studio Manual Smoke Results Template

## Scope

Use this template for a real local OpenWebUI -> RelayLM -> LM Studio validation run.

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

### Current history-authority flags

- `client_message_canonicalization_dry_run_enabled`:
- `client_history_exclusion_preflight_enabled`:
- `client_history_exclusion_apply_enabled`:
- `client_history_exclusion_apply_dry_run_only`:

## Local preflight

```bash
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

- config smoke:
- proxy smoke:
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

| prompt ID | route ID | response summary | persona fit | memory/context fit | fabricated memory? | too generic? | pass/fail |
|---|---|---|---|---|---|---|---|
| P1 | relaylm-companion | | | | | | |
| P1 | relaylm-work-assistant | | | | | | |
| P1 | relaylm-code-reviewer | | | | | | |

## History-exclusion matrix

Record backend role/count summaries only; do not paste sensitive message content into shared evidence.

| case | route mode | client instruction present? | apply enabled | dry-run-only | result status | payload mutation applied? | prior history backend-bound? | backend forwarded? | pass/fail |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| A default compatibility | memory_light | no | false | true | | | | | |
| B dry-run candidate | memory_light | no | true | true | | | | | |
| C actual no-instruction | memory_light | no | true | false | | | | | |
| D unsupported instruction | memory_light | yes | true | false | | | | | |
| E pass-through exemption | pass_through | any | true | false | | | | | |

### Backend payload summary

- inspected with fake/local test backend? yes / no
- compiled system/prefix message count:
- preserved current user message count:
- prior user/assistant history count:
- raw system/developer message count:
- notes:

### Content-free diagnostics

- raw user text absent:
- backend response text absent:
- memory/snippet/page text absent:
- prompt/compiled block body absent:
- local path/secret-bearing URL absent:
- pass/fail:

## RelayRUN recovery diagnostics

- `relayrun_artifact` observed? yes / no
- artifacts observed:
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
- diagnostics remained blocked/fail-closed where required? yes / no
- visible recovery output appeared? yes / no
- backend payload changed by recovery diagnostics? yes / no
- response body changed by recovery diagnostics? yes / no
- pass/fail:

## Failure log

| symptom | suspected layer | next action |
|---|---|---|
| | LM Studio / RelayLM config / RelayLM proxy / OpenWebUI / history authority / backend model | |

## Final verdict

- overall: pass / partial / fail
- blocking issue:
- safe to use current default compatibility path? yes / no / conditions:
- safe to enable no-instruction actual apply? yes / no / test-only:
- next docs follow-up:
- next code follow-up:
- next environment/config follow-up:
