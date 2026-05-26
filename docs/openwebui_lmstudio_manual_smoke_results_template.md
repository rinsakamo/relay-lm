# OpenWebUI + LM Studio Manual Smoke Results Template

## Scope

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

- [OpenWebUI route response differentiation checks](docs/openwebui_response_differentiation_checks.md)

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
