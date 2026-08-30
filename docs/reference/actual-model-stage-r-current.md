# Current Stage R execution authority

Status: current bounded execution entrypoint for RelayLM 1.0 Stage R actual-model qualification.

Long-lived Issue history is evidence, not an execution prompt. #1386 owns the actual-model evaluation authority; the active bounded physical semantic transaction is routed separately by current #1386 authority.

## Current entrypoint

Use:

```text
python -m relaylm.actual_model_stage_r
```

The machine-readable current descriptor is:

```text
evaluation/actual_model/screenings/stage-r0-vllm-current-v1.json
```

It deliberately contains no numeric context window. It points to one current execution template and declares:

- `context_window_source = fresh_external_capacity_evidence`;
- `hardware_capability_source = fresh_vllm_profiler_auto_kv`.

The current template is:

```text
evaluation/actual_model/screenings/stage-r0-vllm-reference-v3.json
```

The v3 template binds its scenario set by repository-relative path and exact semantic revision. The current execution chain therefore has one derivation:

```text
stage-r0-vllm-current-v1
  -> stage-r0-vllm-reference-v3
  -> foundation-v3 path + revision
  -> exact v3 scenario IDs
```

Historical v2 plans remain loadable evidence/templates and are not rewritten as v3.

## Hardware capability bootstrap

Before capacity acquisition or semantic screening:

1. use the exact canonical vLLM source/runtime and frozen target;
2. start a fresh profiler probe with `--max-model-len auto`;
3. retain the runtime memory-profile facts and its recommended explicit `--kv-cache-memory-bytes=<bytes>`;
4. stop the probe;
5. restart the same target/runtime with that exact fresh KV byte recommendation plus `--max-model-len auto`;
6. attest the final live backend/model/root/runner/max-model-length identity;
7. keep this final runtime unchanged through capacity acquisition and screening.

Historical context-window or KV values are evidence for their original runs only. They are not current launch controls.

## Capacity

Run `actual_model_stage_r --operation capacity` first. The launcher delegates to the existing production capacity path and rejects caller-supplied prior capacity evidence. Capacity acquisition therefore observes the final live `max_model_len` directly.

The resulting external immutable capacity artifact must be complete for the selected current condition and exact current scenario-set revision.

## Screening

Run `actual_model_stage_r --operation screening` with the fresh external capacity evidence ID and root from the immediately preceding exact-head capacity run.

The launcher refuses screening without the complete ID/root pair and injects `--context-window-from-capacity-evidence`. The template's historical numeric `effective_context_window` is template data, not current physical capacity authority.

All target, checkout, model-runner, scenario, pass-request, capacity-coverage, live-runtime, exact-request-evidence and source-validation gates remain in force.

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
- `response-transcript-fidelity-v1`;
- `response-false-attribution-resistance-v1`;
- `continuity-lifecycle-v1`.

Proposal scoring is scenario-owned and explicit in foundation-v3. `scored + []` means exactly zero expected proposals; `unscored` preserves raw observations while excluding that channel from FP/FN/precision/recall.

## Exact request evidence

The #2029 request-evidence contract applies to the same canonical two-pass execution path used by current Stage R. Future semantic evidence must preserve citable per-turn Pass 1 and Pass 2 request records, including exact request body/messages, generation-affecting controls, request-body SHA and request evidence identity. Canonical execution fails closed when required request evidence is absent. Historical evidence is not retrofitted.

## Evidence boundaries

A capacity admission failure before screening is not semantic evidence. A deterministic-boundary PASS is not a semantic-quality PASS. Keep raw model output, request evidence, typed proposals, deterministic decisions, semantic review, capacity and timing evidence separately citable.

## Principle

> Current execution starts from a small current authority surface; historical plans and comments remain evidence, never implicit runtime defaults.
