# OpenWebUI Model Preset / Avatar Checklist

## Scope

Manual OpenWebUI preset/avatar setup verification for the RelayLM MVP path.

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

## Target route IDs

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

## OpenWebUI connection checklist

- Open **Admin Settings -> Connections -> OpenAI**.
- Add a connection.
- Select **Standard / Compatible** when available.
- Do not select Open Responses for current RelayLM.
- Set the reachable RelayLM API URL.
- Set API key `relaylm` or another dummy value.
- Confirm `/v1/models` loads the RelayLM route IDs.

Same-host example:

```text
http://127.0.0.1:8090/v1
```

Docker may require `host.docker.internal` or a reachable WSL address. Do not assume container-local `127.0.0.1` points to RelayLM.

## Preset/avatar checklist

For each route:

- Base Model/Model ID exactly matches the RelayLM route ID.
- Display name/avatar/prompt suggestions can be customized.
- Heavy system prompt layering is avoided.
- No client system prompt is treated as durable RelaySOUL authority.
- The user understands that current default `memory_light` may retain prior frontend history backend-bound.

## RelayLM checklist

```bash
cp examples/config/openwebui_lmstudio.yaml config.yaml
python scripts/relaylm_openwebui_lmstudio_config_smoke.py
python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
curl http://127.0.0.1:8090/v1/models
```

Verify:

- route IDs are published,
- exact LM Studio model ID is configured,
- each managed route has a valid character entry,
- `soul` and `output_policy` files exist,
- history-exclusion defaults remain understood:
  - apply disabled,
  - dry-run-only true,
  - no-instruction requests only when explicitly enabled.

## LM Studio checklist

- OpenAI-compatible server is running.
- Direct `/v1/models` works.
- Direct `/v1/chat/completions` works.
- If the loaded model ID differs from `local-model`, RelayLM config is updated.

## Response differentiation

- use the same backend model,
- switch only RelayLM route/model ID,
- use controlled prompts from [response differentiation checks](openwebui_response_differentiation_checks.md),
- verify route/profile differences,
- fail rather than reward fabricated prior memory.

## Manual record

Use [OpenWebUI + LM Studio manual smoke results template](openwebui_lmstudio_manual_smoke_results_template.md).

Record OpenWebUI version, connection protocol, route mode, history-exclusion flags, response differentiation, and any authority/fallback issue.
