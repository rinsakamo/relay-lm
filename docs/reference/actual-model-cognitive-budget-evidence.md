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

A persisted scenario-bound pressure comparison is citable only when its `pressure_comparison_id` matches the content-derived identity of the exact scenario-set version/revision and definition, baseline and pressure plan IDs, and underlying condition-comparison ID. The persistence boundary recomputes that identity and rejects a caller-supplied mismatch before writing the artifact.

## Replication and stopping rule

Authority identity: `actual-model-replication-rule-v1`.

This rule applies to a controlled actual-model comparison whose purpose is to
attribute a product-quality difference to one explicit condition boundary,
including a total cognitive-budget pressure comparison. It does not choose
budget values, profiles, or defaults; define #1387 degradation semantics;
change scenario labels or the #1386 review rubric; create a weighted score;
estimate population-level statistical significance; or generalize one
scenario/model result to another target.

### Valid replicate pair

A pair is a valid replicate only when the existing #1386 controlled
comparison contract is satisfied. The following non-budget identity remains
fixed, as applicable:

- RelayLM freeze commit;
- exact model artifact;
- tokenizer;
- provider/adapter;
- provider capabilities;
- effective context window;
- decoding and seed policy;
- scenario definition and revision;
- Character fixture revision;
- structured-output schema;
- execution path;
- Continuity Runtime identity; and
- serialized-input counter identity and count mode.

Only the declared comparison condition/budget and the required
condition/replicate evidence identity may differ. An invalid pair contributes
no evidence for directional stability and must not be reinterpreted as an
adverse model result.

### Unit of stability

Evaluate stability independently for:

```text
scenario × exact comparison boundary × supported quality dimension
```

Do not collapse dimensions into a weighted score. Supported dimensions are
limited to what the scenario, provider, and review actually cover, such as:

- response correctness/coherence;
- persona/self-identity;
- required StateCandidate behavior;
- required Continuity behavior;
- unsupported recalled-detail behavior; and
- scenario-owned no-op, stale, or unnecessary proposal behavior.

Unsupported dimensions remain `not covered`. The deterministic RelayLM
boundary PASS/FAIL remains separate from product-quality direction.

### Pair-level directional classification

For each supported quality dimension, classify each valid pair using the
existing scenario-owned and review criteria:

- `pressure_worse`;
- `no_material_delta`; or
- `pressure_better`.

Do not invent a universal numeric epsilon. A difference is material only when
the existing scenario/review semantics support that interpretation, such as a
required categorical pass/fail outcome changing, a required labeled proposal
being present versus absent, or a supported forbidden/unsupported behavior
appearing versus not appearing. Raw precision, recall, and count differences
remain descriptive unless existing scenario/review authority makes them
materially meaningful.

If the same product failure occurs on both sides of a pair, record it as a
repeated model/scenario quality observation, not as a boundary-attributed
budget delta.

### Minimal sequential replication gate

Use this fixed sequence for each scenario/boundary/dimension unit:

```text
valid pair 1  = initial observation
valid pair 2  = independent replication check
```

If pair 1 and pair 2 disagree in directional classification, stop and classify
the unit as `unstable_no_boundary_attribution`. Do not add replicates merely to
manufacture a majority; disagreement is itself evidence of instability.

If pair 1 and pair 2 agree, execute at most one additional valid pair when
confirmation is required:

```text
valid pair 3  = confirmation
```

If all three valid pairs agree on the same material direction, classify the
unit as `replicated_directional_signal`. If all three agree that there is no
material delta, classify it as `no_material_delta_observed`. If pair 3
disagrees with the first two, classify the unit as
`unstable_no_boundary_attribution`.

Three valid pairs are the maximum evidence tranche for this minimal v1
reproducibility gate:

- pair 1 is the observation;
- pair 2 is the replication;
- pair 3 is the confirmation; and
- the protocol must not keep sampling until a preferred result appears.

This is an engineering reproducibility gate, not a statistical significance or
confidence-interval claim.

### Claim scope and calibration consequence

`replicated_directional_signal` means only that the observed directional effect
reproduced under the exact frozen scenario, target, and comparison boundary
represented by those runs. It does not establish a universal model property,
cross-scenario or cross-model generality, a canonical profile, or a runtime
default.

`no_material_delta_observed` means only that no material delta was observed in
the three valid paired executions under that exact freeze.

`unstable_no_boundary_attribution` means that the evidence does not support
attributing the observed product-quality difference to that exact comparison
boundary.

For #1388, an `unstable_no_boundary_attribution` boundary must not be used as
evidence that one adjacent condition is the smallest sufficient region or as
justification for selecting one side as a profile/default. Calibration may
preserve the instability, investigate a different meaningfully separated
evidence-derived region in a later explicitly governed transaction, or retain
no-default/evidence-insufficient status. It must not repeat the same disputed
adjacent pair until a preferred direction wins. A
`replicated_directional_signal` is usable evidence for Calibration, but does
not itself select a default.

### Current CAL3-GAP-1 reconciliation

Under `actual-model-replication-rule-v1`, the already-executed
`cognitive-pressure-shared-semantics-v1` boundary is reconciled as follows:

```text
R_fit           = 6345
R_first_pressure = 6346
```

The two existing valid pairs classify the supported correctness dimension as:

```text
pair 1: fit-side correctness pass;   pressure-side correctness fail
         → pressure_worse

pair 2: fit-side correctness fail;    pressure-side correctness fail
         → no_material_delta
```

Their classifications disagree, so the stopping condition is already met
after two valid pairs:

```text
unstable_no_boundary_attribution
```

No third pair is required for this exact boundary. The repeated unresolved
Continuity loss on both sides remains a repeated product-quality observation,
but is not attributable to the `6345 → 6346` boundary. No profile or default
follows from this reconciliation, and no new evidence IDs are created.

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
