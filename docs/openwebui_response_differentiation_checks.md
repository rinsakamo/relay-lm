# OpenWebUI Route Response Differentiation Checks

## Scope

This document defines a manual response differentiation check for the RelayLM Runtime MVP.

- compare responses using the same backend model
- switch only RelayLM route/model ID
- no automated scoring
- no runtime code change

## Target route IDs

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

## Test prompt set

Use the same prompt text across all three routes.

### P1: Casual continuity prompt

> We talked yesterday about keeping my weekly routine stable. Can you continue from that context and suggest what I should do today?

### P2: Ambiguous planning prompt

> I have too many tasks and limited time this week. Help me decide what to do first and what to defer.

### P3: Implementation review prompt

> I prepared a small code change with minimal diff goals. Please review likely risks and what I should validate before merge.

### P4: Safety / boundary prompt

> I want a fast answer even if details are uncertain. What should we do to keep quality and safety acceptable?

### P5: Short follow-up prompt

> Give me the shortest practical next step from your previous answer.

## Expected tendencies by route

### `relaylm-companion`

- warm / steady / continuity-oriented tone
- preserves conversational continuity and user state
- avoids becoming overly casual or unserious

### `relaylm-work-assistant`

- conclusion-first structure
- assumptions and next actions are clearly separated
- planning and decision-support tone

### `relaylm-code-reviewer`

- emphasizes correctness, safety, minimal diff, and validation
- surfaces concrete risks and checks
- stays implementation-review oriented

## Evaluation table template

```markdown
| prompt id | route id | response summary | persona fit | memory/context fit | too generic? | too similar to other routes? | issue / next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | relaylm-companion |  |  |  |  |  |  |
| P1 | relaylm-work-assistant |  |  |  |  |  |  |
| P1 | relaylm-code-reviewer |  |  |  |  |  |  |
| P2 | relaylm-companion |  |  |  |  |  |  |
| ... | ... |  |  |  |  |  |  |
```

## Pass criteria

- all three routes respond successfully
- outputs are not identical in style
- each route shows expected bias from SOUL / OUTPUT_POLICY
- no concrete character names are required
- no dependency on heavy OpenWebUI system prompts

## Common fail patterns

- all routes sound effectively identical
- OpenWebUI prompt layer overrides RelayLM route behavior
- backend model ignores system/context signals
- route ID mismatch between OpenWebUI and RelayLM
- LM Studio backend model name mismatch
- streaming works but non-stream fails (or vice versa)

## Related references

- Latest real run result: [OpenWebUI + RelayLM + LM Studio manual smoke result (2026-05-26)](docs/openwebui_lmstudio_manual_smoke_result_2026_05_26.md)
- [OpenWebUI + LM Studio MVP](docs/openwebui_lmstudio_mvp.md)
- [OpenWebUI + LM Studio manual smoke runbook](docs/openwebui_lmstudio_manual_smoke.md)
- [OpenWebUI model preset/avatar checklist](docs/openwebui_model_preset_checklist.md)
- [OpenWebUI + LM Studio manual smoke results template](docs/openwebui_lmstudio_manual_smoke_results_template.md)
