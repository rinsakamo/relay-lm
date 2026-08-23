# Actual-model vLLM cognitive-budget facade carriage

Status: #1718 Integration bridge from the canonical vLLM host invocation surface to the already-owned #1387 two-pass budget runtime and #1386 actual-model evidence path.

This reference does not choose context-window values, Pass 1 or Pass 2 output reserves, degradation targets, a release profile, or defaults. #1387 owns budget mechanics; #1388 owns calibrated release values; #1386 owns actual-model qualification.

## Canonical invocation

The shared actual-model facade may carry an explicit two-pass budget declaration only for vLLM screening:

```text
python -m relaylm.actual_model_host \
  --backend vllm \
  --operation screening \
  --condition B \
  ... \
  --cognitive-budget /outside/repo/two-pass-budget.json
```

`--cognitive-budget` is not a capacity-acquisition input. Supplying it with `--operation capacity` fails before capacity preparation.

The declaration is strict JSON. Unknown, missing and duplicate members fail closed. Its shape is:

```text
{
  "format_version": 1,
  "mode": "two_pass",
  "pass1": {
    "model_context_window": <explicit positive integer>,
    "reserved_output_tokens": <explicit non-negative integer>
  },
  "pass2": {
    "model_context_window": <explicit positive integer>,
    "reserved_output_tokens": <explicit non-negative integer>
  },
  "initial_plan": <complete existing #1387 BudgetPlan>,
  "degradation_steps": <ordered existing #1387 BudgetDegradationStep list>
}
```

The declaration intentionally has no `token_counter` field. A caller cannot claim a tokenizer implementation, live counter callable, counter mode or evidence identity through this surface.

## Ownership and resolution

The external declaration carries only caller-selected Pass 1 / Pass 2 totals and the existing #1387 degradation policy. It is converted to `TwoPassCognitiveBudgetRuntimeConfig` only after the vLLM host reconstructs current live counting capability from the frozen target, frozen reasoning proof and fresh backend/model attestation.

The facade helper uses the canonical vLLM target/proof/counter implementations rather than accepting a caller counter. The existing vLLM host preparation boundary then independently re-attests live backend identity, validates cited capacity evidence and selected-condition coverage, checks both declared context windows against the screening effective context window, and rebinds the runtime to its own fresh `VLLMServingTokenizerCounter` before provider generation.

Therefore an external declaration can choose budget values but cannot substitute counting behavior while presenting a plausible counter identity.

## Execution identity

When the declaration is accepted for a two-pass condition, the resulting host-owned `TwoPassCognitiveBudgetRuntimeConfig` is the same runtime type consumed by the real buffered two-pass ordinary-turn path. Its resolved identity is persisted through `ActualModelRunManifest.cognitive_budget` and forwarded to each selected scenario execution.

A declaration supplied to a single-pass screening condition fails closed at the existing vLLM host preparation boundary. Historical unbudgeted invocations remain mechanically possible when `--cognitive-budget` is omitted; their existence does not qualify the #1718 budgeted reference path or authorize #1388 defaults.

## Evidence boundary

This carriage surface proves only that explicit per-pass budget inputs can reach the citable vLLM screening runtime without inventing numeric policy or caller-owned counter facts. A release/profile decision still requires #1386 actual-model evidence and #1388 calibration. Installed `relaylm serve` integration remains owned by #1446 and is not implied by this host-only facade.
