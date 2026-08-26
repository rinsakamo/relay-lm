# Current Stage R execution authority

Status: current bounded execution entrypoint for RelayLM 1.0 Stage R actual-model qualification.

Long-lived Issue history is evidence, not an execution prompt. #1386 is an umbrella/evidence index. The active transaction owner is #1921 until this authority cleanup converges.

## Current entrypoint

Use:

```text
python -m relaylm.actual_model_stage_r
```

Do not reconstruct the current procedure from old #1386 comments or invoke the historical v2 plan as though its numeric context window were a live hardware profile.

The machine-readable current descriptor is:

```text
evaluation/actual_model/screenings/stage-r0-vllm-current-v1.json
```

It deliberately contains no numeric context window. It declares:

- the existing v2 execution template used for topology/pass/scenario identity;
- `context_window_source = fresh_external_capacity_evidence`;
- `hardware_capability_source = fresh_vllm_profiler_auto_kv`.

## Hardware capability bootstrap

Before capacity acquisition or semantic screening:

1. use the exact canonical vLLM source/runtime and frozen target;
2. start a fresh profiler probe with `--max-model-len auto`;
3. retain the runtime memory-profile facts and its recommended explicit `--kv-cache-memory-bytes=<bytes>`;
4. stop the probe;
5. restart the same target/runtime with that exact fresh KV byte recommendation plus `--max-model-len auto`;
6. attest the final live backend/model/root/runner/max-model-length identity;
7. keep this final runtime unchanged through capacity acquisition and screening.

Historical values such as `1616`, `14208`, `15616`, or a prior KV-byte recommendation are evidence for their original runs only. They are not current launch controls.

## Capacity

Run `actual_model_stage_r --operation capacity` first. The launcher delegates to the existing production capacity path and rejects caller-supplied prior capacity evidence. Capacity acquisition therefore observes the final live `max_model_len` directly.

The resulting external immutable capacity artifact must be complete for the selected current condition.

## Screening

Run `actual_model_stage_r --operation screening` with the fresh external capacity evidence ID and root from the immediately preceding exact-head capacity run.

The current launcher refuses screening without the complete ID/root pair and always injects the existing host's `--context-window-from-capacity-evidence` control. The v2 template's historical numeric window is therefore not current screening authority.

All existing target, checkout, model-runner, scenario, pass-request, capacity coverage, live-runtime and source-validation gates remain in force.

## Current semantic reference

For the Stage R0 reference baseline:

- buffered two-pass;
- Pass 1 reasoning OFF;
- Pass 1 no structured-output control;
- Pass 2 reasoning OFF;
- Pass 2 explicit native structured output;
- temperature 0;
- top_p 1;
- seed null;
- canonical `response-persona-correction-v1` and `continuity-lifecycle-v1` scenarios.

Reasoning escalation is not a routine rescue path. #1915 owns its separate provider/runtime finding.

## Evidence boundaries

A capacity admission failure before screening is not semantic evidence. A deterministic-boundary PASS is not a semantic-quality PASS. Keep raw model output, typed proposals, deterministic decisions, semantic review, and capacity/timing evidence separately citable.

## Principle

> Current execution starts from a small current authority surface; historical plans and comments remain evidence, never implicit runtime defaults.
