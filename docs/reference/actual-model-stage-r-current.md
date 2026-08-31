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
- `hardware_capability_source = qualified_vllm_token_capacity_reference`.

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

## Physical admission bootstrap

Before capacity acquisition or semantic screening:

1. use the exact canonical vLLM source/runtime and frozen target;
2. bind one legal target token window from the current bounded evaluation/calibration owner; if no owner has selected a legal window, stop;
3. bind citable compatible `VLLMTokenCapacityReference` evidence from a successful launch of the same target/runtime/runner/host capability class;
4. acquire fresh GPU `free_bytes` and `total_bytes`;
5. construct `VLLMLaunchMemoryAdmission.for_token_window(...)` from the fixed target window, the qualified token-capacity reference, and the fresh GPU bytes;
6. fail closed before launch if fresh free memory is below the token-derived required envelope;
7. launch the final runtime with `final_memory_args()`, which renders an envelope-derived `--gpu-memory-utilization`, explicit `--kv-cache-memory-bytes`, and explicit `--max-model-len`;
8. attest the final live backend/model/root/runner/max-model-length identity;
9. keep this final runtime unchanged through capacity acquisition and screening.

Ordinary Stage R does not choose its token window by maximizing transient free VRAM and does not use `--max-model-len auto` as a substitute for a missing evaluation/calibration-owned target.

The existing vLLM profiler/parser remains available only for a separate launch-capability acquisition transaction when launch-significant target/runtime/runner/host identity changes or compatible token-capacity geometry is otherwise unavailable. Historical profiler values are evidence for their original runs only and are not ordinary Stage R launch controls.

The physical-admission contract is defined in `docs/reference/actual-model-vllm-functional-acceptance.md`. A bounded comparison may use an explicitly authorized experiment-only token window without making that value a #1388 release default.

## Capacity

After the fixed-window final runtime is serving, run `actual_model_stage_r --operation capacity` first. The launcher delegates to the existing production capacity path and rejects caller-supplied prior capacity evidence. Capacity acquisition therefore observes the live explicit `max_model_len` directly.

The resulting external immutable capacity artifact must be complete for the selected current condition and exact current scenario-set revision. On this path it attests the already-selected physical window; it does not choose that window.

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

A physical admission failure before screening is not semantic evidence. A deterministic-boundary PASS is not a semantic-quality PASS. Keep raw model output, request evidence, typed proposals, deterministic decisions, semantic review, capacity and timing evidence separately citable.

## Principle

> Current execution starts from a small current authority surface; token demand comes from cognitive/evaluation authority, qualified launch geometry carries it physically, and transient free VRAM answers only whether the host can carry it.
