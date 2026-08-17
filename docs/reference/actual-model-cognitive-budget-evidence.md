# Actual-model total cognitive-budget evidence bridge

Status: #1386 actual-model evidence carriage for the already-owned #1387 total cognitive-budget runtime.

This reference defines how actual-model runs exercise and preserve evidence from `CognitiveBudgetRuntimeConfig`. It does not define budget semantics, choose numeric defaults, alter provider behavior, or perform calibration.

## Purpose

The #1387 runtime already enforces:

- hard model context capacity;
- reserved output capacity;
- protected Identity + Current Event + provider framing floor;
- explicit per-layer `BudgetPlan` envelopes/floors;
- deterministic tier-ordered degradation;
- final serialized-input token counting or approved conservative bounds;
- bounded fail-before-generation behavior;
- aggregate content-free diagnostics.

Before this bridge, #1386 actual-model runs recorded only legacy explicit MEMORY/Event retrieval limits and therefore could not produce calibration evidence for the real total-budget path.

The bridge makes the existing runtime observable without reimplementing it.

## Manifest identity

`ActualModelRunManifest.cognitive_budget` is optional. When present it is an `ExplicitCognitiveBudgetConfiguration` containing the existing #1387 owner values:

```text
TotalBudgetConfig
  model_context_window
  reserved_output_tokens

BudgetDegradationPolicy
  complete initial BudgetPlan
    Canonical State max/floor items
    Working Context max/floor items + chars
    Retrieved MEMORY max/floor items + chars
    Event Evidence max/floor items + chars
  ordered BudgetDegradationStep list
    layer
    tier
    target envelope/floor
```

No numeric value is invented by #1386. The manifest merely freezes caller-supplied #1387 policy identity for the evidence run.

`manifest.effective_context_window` must equal `cognitive_budget.model_context_window`.

The total cognitive-budget path and the older `ExplicitBudgetConfiguration` MEMORY/Event-only path are mutually exclusive. A run cannot combine them and ambiguously claim which controls were authoritative.

## Runtime binding

A manifest declaration does not reconstruct a runtime token counter.

The caller must supply a real `CognitiveBudgetRuntimeConfig` containing:

- the same `TotalBudgetConfig`;
- the same `BudgetDegradationPolicy`;
- the configured provider/model-specific `SerializedCognitiveInputTokenCounter`.

Declaration/runtime mismatch fails before semantic provider generation. Supplying an undeclared runtime also fails closed.

Tokenizer/provider identity remains represented by existing #1386 manifest fields. The actual exact-versus-conservative count mode is observed from runtime diagnostics rather than guessed from metadata.

## Real ordinary-turn execution

For a declared total cognitive-budget condition, #1386 uses the real ordinary-turn functions:

```text
buffered
  run_user_turn_with_cognitive_budget_diagnostics

streaming
  run_user_turn_streaming_with_cognitive_budget_diagnostics
```

These functions already own the #1387 execution boundary. The actual-model harness does not duplicate enforcement, compilation, degradation, or token-accounting logic.

Exactly one semantic generation remains possible after a successful fit. No evaluation-only provider call or second model call is introduced.

## Successful turn evidence

Every successfully generated turn may carry `cognitive_budget` diagnostics copied from the runtime's aggregate content-free diagnostics:

- model context window;
- effective serialized-input capacity;
- reserved output tokens;
- required input framing tokens;
- final serialized input tokens;
- final cognitive-input tokens;
- available cognitive capacity;
- pressure flag;
- applied degradation-step count;
- reduced layer/tier counts;
- per-tier reduction counts;
- outcome: `fit` or `degraded_fit`;
- count mode: `exact` or `conservative_estimate`.

The evidence copy contains no Identity text, State keys/values, Continuity values, MEMORY text/locations, Event content, prompt text, or secrets.

Raw model output and deterministic State/Continuity decisions remain separate from these budget diagnostics exactly as before.

## Bounded pre-generation failure evidence

A protected-floor overflow or degradation-exhaustion condition is valid calibration evidence even though no model response exists.

The harness therefore preserves a top-level `bounded_failure` observation containing:

- failed turn index and already-known semantic fixture input;
- `provider_generation_occurred: false`;
- the same content-free budget diagnostics;
- outcome `bounded_failure`;
- #1387 failure reason (`protected_floor_exceeds_context` or `degradation_exhausted`);
- final count mode and token counts;
- applied degradation count.

The failed turn does **not** receive fabricated `RawModelObservation` or deterministic candidate decisions. Prior successfully completed turns, if any, remain in `turns`.

## Controlled pressure comparisons

Existing controlled comparisons now accept either of two mutually exclusive budget-control modes:

1. legacy explicit MEMORY/Event retrieval budgets; or
2. explicit total cognitive-budget configurations.

Baseline and pressure must use the same mode. For total-budget comparisons, their `cognitive_budget` configurations must differ while unrelated manifest identity stays fixed.

Comparison summaries add a content-free `bounded_budget_failure_count`. Pressure-minus-baseline remains an unsigned observation; a positive delta is not automatically better or worse.

Scenario-bound pressure wrappers pass the explicit baseline and pressure `CognitiveBudgetRuntimeConfig` objects through to the ordinary-turn harness.

## Canonical scenario execution

`run_actual_model_scenario_definition()` accepts the same optional runtime and validates manifest/runtime identity before mutable workspace creation or provider generation.

Current restart-quality evidence is intentionally **not** extended by this ordinary-turn bridge. A restart scenario declaring total cognitive-budget evidence fails closed instead of silently ignoring the configuration. A future restart-specific budget evidence extension would require a separate bounded #1386 transaction.

## Artifact behavior

`ActualModelEvidence.to_mapping()` / immutable artifact persistence include:

- manifest total-budget identity;
- per-successful-turn aggregate budget diagnostics;
- optional bounded failure evidence.

Existing content-addressed run/execution/pressure identity naturally includes the declared cognitive-budget configuration through `manifest.to_mapping()`.

## Ownership boundaries

This bridge does not own or modify:

- total-budget arithmetic, protection tiers, degradation order, token-count semantics, or failure reasons — #1387;
- Retrieval or Context Compiler selection semantics — #1267;
- Continuity acceptance/lifecycle semantics — #1371;
- provider wire or decoding semantics — #1456 provider authority;
- runtime-config discovery/precedence/CLI semantics — #1446;
- calibration values/profile boundaries/default selection — #1388.

## Calibration gate consequence

After this bridge is merged, #1386 can produce machine-auditable total-budget evidence required by #1388 CAL2 **when a real target provider/model, exact manifest, explicit runtime configuration, and provider/model token counter are supplied**.

The bridge alone does not create real target-model executions or justify any numeric default. Canonical calibration remains blocked until reproducible real-model evidence is actually produced and the relevant moving semantic baselines are freshly frozen.
