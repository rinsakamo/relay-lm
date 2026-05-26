# OpenWebUI Model Preset / Avatar Checklist

## Scope

This document is a checklist for manual OpenWebUI preset/avatar setup verification in the RelayLM Runtime MVP flow.

- manual verification only
- no runtime code change
- no automatic real-backend integration test

## Target topology

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

## Preset checklist by route

Target route IDs:

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

For each route ID, verify the same checklist items below.

## OpenWebUI checklist

- OpenAI-compatible connection Base URL is set to `http://127.0.0.1:8090/v1`.
- API key is set (`relaylm` or a dummy value).
- Model preset and avatar can be created successfully.
- Base Model / Model ID exactly matches one RelayLM route ID.
- Display name / avatar / prompt suggestions can be customized.
- Heavy system prompt layering is avoided to prevent duplication with RelayLM persona-policy context.

## RelayLM checklist

Prepare config and run local smokes before manual UI checks:

```bash
cp examples/config/openwebui_lmstudio.yaml config.yaml
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

Verify route publication:

```bash
curl http://127.0.0.1:8090/v1/models
```

Expected route IDs:

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

## LM Studio checklist

- OpenAI-compatible server is running.
- Direct backend model listing works:

```bash
curl http://127.0.0.1:1234/v1/models
```

- If your loaded backend model name is not `local-model`, update config route/backend model mapping accordingly.

## Route-specific response differentiation check

- Use the same backend model in LM Studio.
- Switch only the route/model ID at RelayLM/OpenWebUI.
- Compare response tendencies between:
  - `relaylm-companion`
  - `relaylm-work-assistant`
  - `relaylm-code-reviewer`
- Verify behavior differences come from route/profile/memory configuration.
- Do not rely on concrete character names.

## Manual smoke result template

Use this template for real-environment verification records.

```markdown
- date:
- environment:
- LM Studio model name:
- RelayLM config used:
- OpenWebUI version (if known):
- route IDs tested:
  - relaylm-companion
  - relaylm-work-assistant
  - relaylm-code-reviewer
- /v1/models result:
- non-stream result:
- stream result:
- OpenWebUI preset/avatar result:
- response differentiation notes:
- failures / suspected cause / next action:
```

## Troubleshooting references

- [OpenWebUI + LM Studio manual smoke runbook](docs/openwebui_lmstudio_manual_smoke.md)
