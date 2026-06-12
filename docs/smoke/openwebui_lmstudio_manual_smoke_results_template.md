# OpenWebUI + LM Studio Manual Smoke Results Template

## Scope

- Latest filled result sample: [OpenWebUI + RelayLM + LM Studio manual smoke result (2026-05-26)](openwebui_lmstudio_manual_smoke_result_2026_05_26.md)

This document is a manual result template for real-environment smoke reporting.

- manual result template only
- no real backend execution in Cloud Codex
- no runtime code change

## Environment

- date:
- OS / host:
- Python version:
- RelayLM commit SHA:
- LM Studio version (if known):
- loaded backend model name:
- OpenWebUI version (if known):

## Config

- config used:
- copied from `examples/config/openwebui_lmstudio.yaml`? (yes/no):
- backend URL:
- RelayLM URL:
- backend model mapping changed from `local-model`? (if yes, details):

## Preflight local smoke

Run before real manual smoke:

```bash
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

- config smoke result:
- proxy smoke result:
- notes:

## LM Studio direct check

- `/v1/models` result:
- non-stream direct completion result:
- stream direct completion result (if tested):
- notes:

## RelayLM route check

- `/v1/models` result:
- non-stream via RelayLM result:
- stream via RelayLM result:
- notes:

## OpenWebUI setup

- connection Base URL:
- API key type (`relaylm` or dummy):
- model preset/avatar setup status:
- route IDs configured:
  - `relaylm-companion`
  - `relaylm-work-assistant`
  - `relaylm-code-reviewer`
- notes:

## Response differentiation

Reference prompt IDs from:

- [OpenWebUI route response differentiation checks](openwebui_response_differentiation_checks.md)

### Route comparison table

```markdown
| prompt id | route id | response summary | persona fit | memory/context fit | too generic? | too similar to other routes? | pass/fail note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | relaylm-companion |  |  |  |  |  |  |
| P1 | relaylm-work-assistant |  |  |  |  |  |  |
| P1 | relaylm-code-reviewer |  |  |  |  |  |  |
| P2 | relaylm-companion |  |  |  |  |  |  |
| ... | ... |  |  |  |  |  |  |
```

## Failure log

```markdown
| symptom | suspected layer | next action |
| --- | --- | --- |
|  | LM Studio / RelayLM config / RelayLM proxy / OpenWebUI connection / OpenWebUI prompt layering / backend model behavior |  |
```

## Final verdict

- verdict: pass / partial / fail
- next docs follow-up:
- next code follow-up (if needed):

## MVP-38 RelayRUN recovery diagnostics manual smoke record

### Date

- date:
- JST date:

### Environment

- OS:
- Python version:
- RelayLM commit SHA:
- LM Studio version:
- LM Studio model:
- OpenWebUI version:

### Config summary

- route/model:
- diagnostics enabled/disabled:
- trace enabled/disabled:
- trace path if enabled:
- recovery configs default-off or overridden:
- config differences from `config.example.yaml` reviewed? (yes/no):
- notes:

### Normal conversation result

- prompt used:
- route/model used:
- OpenWebUI result summary:
- backend response body returned normally? (yes/no):
- OpenWebUI error banner? (yes/no):
- pass/fail:
- notes:

### Recovery diagnostics result

- `relayrun_artifact` observed in diagnostics/trace? (yes/no):
- recovery artifact names observed:
  - `recovery_transition_artifact`:
  - `waiting_user_contract`:
  - `recovery_apply_preflight`:
  - `recovery_response_draft`:
  - `visible_recovery_response_preflight`:
  - `recovery_response_generator`:
  - `output_relayscn_recovery_gate`:
  - `visible_recovery_apply_preflight`:
  - `user_action_contract`:
- recovery chain remained blocked/fail-closed? (yes/no):
- user-visible recovery output appeared? (yes/no):
- notes:

### Backend payload mutation result

- LM Studio backend payload inspected? (yes/no):
- recovery artifacts absent from backend payload? (yes/no):
- unexpected recovery/system payload content? (yes/no):
- pass/fail:
- notes:

### Response body mutation result

- OpenWebUI received backend response body unchanged? (yes/no):
- RelayRUN recovery diagnostics changed response body? (yes/no):
- pass/fail:
- notes:

### Content-free artifact result

- raw user text absent from recovery artifacts? (yes/no):
- backend response text absent from recovery artifacts? (yes/no):
- snippet/page text absent from recovery artifacts? (yes/no):
- prompt/final text absent from recovery artifacts? (yes/no):
- trace artifact names only collected for shared evidence? (yes/no):
- pass/fail:
- notes:

### Pass/fail

- overall result: pass / partial / fail
- blocking issue:
- safe to proceed beyond MVP-38? (yes/no):

### Notes / follow-up

- follow-up docs:
- follow-up code:
- follow-up environment/config:
