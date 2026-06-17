# OpenWebUI Route Response Differentiation Checks

## Scope

Compare responses using the same backend model and switch only the RelayLM route/model ID.

- no automated scoring,
- no runtime change,
- no unseeded past-memory fabrication accepted.

## Target route IDs

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

## Controlled prompt set

Use the same prompt across all routes.

### P1: continuity without a known fact

> I may have discussed a weekly routine before, but the exact routine is not present in the supplied context. Help me choose today's next step without inventing what I said previously.

Expected:

- acknowledge missing exact context,
- ask for or work around the missing fact,
- do not fabricate yesterday's routine,
- route-specific tone/structure may differ.

### P2: seeded profile tendency

> I have too many tasks and limited time this week. Help me decide what to do first and what to defer.

### P3: implementation review

> I prepared a small code change with minimal diff goals. Review likely risks and what I should validate before merge.

### P4: safety/boundary

> I want a fast answer even if details are uncertain. What should we do to keep quality and safety acceptable?

### P5: short follow-up

> Give me the shortest practical next step from your previous answer.

P5 must be sent in the same frontend conversation only when intentionally testing compatibility history behavior. Record whether history-exclusion apply is enabled; do not assume current-turn-only reconstruction.

## Expected route tendencies

### `relaylm-companion`

- warm, steady, continuity-oriented tone,
- avoids pretending to know missing facts,
- not overly casual or unserious.

### `relaylm-work-assistant`

- conclusion-first,
- assumptions separated from actions,
- bounded planning/decision support.

### `relaylm-code-reviewer`

- correctness, safety, minimal diff, and validation focus,
- concrete risks/checks,
- implementation-review orientation.

## Evaluation table

| prompt ID | route ID | response summary | persona fit | configured memory/profile fit | fabricated memory? | too generic? | too similar? | pass/fail |
|---|---|---|---|---|---|---|---|---|
| P1 | relaylm-companion | | | | | | | |
| P1 | relaylm-work-assistant | | | | | | | |
| P1 | relaylm-code-reviewer | | | | | | | |
| P2 | relaylm-companion | | | | | | | |

## Pass criteria

- all routes respond,
- outputs are not identical in style,
- expected SOUL/OUTPUT_POLICY bias appears,
- configured memory seed influence is plausible where relevant,
- P1 does not fabricate missing past facts,
- no concrete character name is required,
- no heavy OpenWebUI system prompt is required.

## Common failures

- all routes sound identical,
- OpenWebUI prompt layer overrides RelayLM profile behavior,
- backend ignores system/context signals,
- route or backend model ID mismatch,
- response invents unavailable prior memory,
- P5 behavior is interpreted without recording current history-authority flags,
- stream/non-stream mismatch.

## References

- [OpenWebUI + LM Studio MVP](../openwebui_lmstudio_mvp.md)
- [Manual smoke runbook](openwebui_lmstudio_manual_smoke.md)
- [Preset/avatar checklist](openwebui_model_preset_checklist.md)
- [Manual smoke results template](openwebui_lmstudio_manual_smoke_results_template.md)
- [Historical filled result: 2026-05-26](openwebui_lmstudio_manual_smoke_result_2026_05_26.md)
