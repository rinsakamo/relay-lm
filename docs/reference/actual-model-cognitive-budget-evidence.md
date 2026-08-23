# Actual-model total cognitive-budget evidence bridge

Status: #1386 actual-model evidence carriage for the already-owned #1387 total cognitive-budget runtime and the #1718/#1533 Core 1.0 two-pass per-generation budget boundary.

This reference defines how actual-model runs exercise and preserve evidence from `CognitiveBudgetRuntimeConfig` and `TwoPassCognitiveBudgetRuntimeConfig`. It does not define budget semantics, choose numeric defaults, alter provider behavior, or perform calibration.

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

For Core 1.0 two-pass execution, #1718 additionally requires each real model generation to be admitted against its own exact serialized request and explicit output reserve. Pass 1 keeps the #1387 degradation loop; Pass 2 checks the exact extraction request after the visible response exists and does not run a second semantic degradation policy.

Before this bridge, #1386 actual-model runs could cite the historical single-pass total-budget path but could not bind the same per-pass capacity identity used by the real two-pass runtime. The bridge makes the existing runtime observable without reimplementing it.

## Manifest identity

`ActualModelRunManifest.cognitive_budget` is optional. When present it is an `ExplicitCognitiveBudgetConfiguration` that freezes caller-supplied #1387 runtime identity.

Historical single-pass evidence retains its existing mapping exactly:

```text
TotalBudgetConfig
  model_context_window
  reserved_output_tokens

BudgetDegradationPolicy
  complete initial BudgetPlan
  ordered BudgetDegradationStep list

optional serialized-input counter identity
```

Core 1.0 two-pass evidence uses the same field with an explicit two-pass shape:

```text
mode: two_pass
pass1
  model_context_window
  reserved_output_tokens
pass2
  model_context_window
  reserved_output_tokens
BudgetDegradationPolicy
  complete initial BudgetPlan
  ordered BudgetDegradationStep list
optional serialized-input counter identity
```

The two-pass shape records the two real total-capacity equations. It does not collapse them into one synthetic reserve and does not invent a Pass 2 degradation policy.

No numeric value is invented by #1386. In particular, #1388 owns calibration and selection of release-profile Pass 1 / Pass 2 reserves. This bridge only makes explicit caller-supplied values citable.

`manifest.effective_context_window` must equal the model context window used by every total-capacity equation in the declared configuration. A two-pass identity therefore requires both Pass 1 and Pass 2 totals to bind the same effective model context window while allowing different output reserves.

The total cognitive-budget path and the older `ExplicitBudgetConfiguration` MEMORY/Event-only path remain mutually exclusive. A run cannot combine them and ambiguously claim which controls were authoritative.

A declared two-pass cognitive-budget identity requires `cognition_execution.mode == two_pass`. Conversely, a two-pass execution that declares cognitive-budget evidence cannot masquerade a historical single-pass total-budget identity as its capacity contract.

## Runtime binding

A manifest declaration does not reconstruct a runtime token counter.

The caller must supply the matching real runtime object:

```text
single_pass
  CognitiveBudgetRuntimeConfig

two_pass
  TwoPassCognitiveBudgetRuntimeConfig
    pass1_total
    pass2_total
    shared #1387 degradation policy
    exact/conservative pass-aware serialized-input counter
```

Declaration/runtime mismatch fails before semantic provider generation. Supplying an undeclared runtime also fails closed.

For two-pass execution, the runtime object supplied to #1386 is the same runtime type consumed by `run_user_turn_two_pass` / `run_user_turn_two_pass_streaming`; the evaluation harness does not translate it into a separate evaluation-only budget mechanism.

The fully resolved `CognitionPassRequest` used for Pass 1 counting is the same request passed to Pass 1 generation. The same identity rule holds for Pass 2 counting and extraction generation. This keeps reasoning/decoding/output controls inside both request serialization and provider execution rather than counting a proxy request.

Tokenizer/provider identity remains represented by existing #1386 manifest fields and, when supplied by the runtime counter, the content-free serialized-input counter identity. Exact-versus-conservative semantics remain counter-owned rather than guessed from unrelated metadata.

## Real ordinary-turn execution

Historical single-pass declared total-budget conditions continue to use the existing diagnostic-returning ordinary-turn functions:

```text
buffered
  run_user_turn_with_cognitive_budget_diagnostics

streaming
  run_user_turn_streaming_with_cognitive_budget_diagnostics
```

Core 1.0 two-pass declared conditions use the real #1533/#1718 functions:

```text
buffered
  run_user_turn_two_pass

streaming
  run_user_turn_two_pass_streaming
```

The actual-model harness does not duplicate enforcement, compilation, degradation, or token-accounting logic.

For two-pass execution:

1. Pass 1 counts the exact conversation request with the resolved Pass 1 request, applies the existing deterministic #1387 degradation/fail-before-generation semantics, then delegates at most once;
2. after a valid visible response exists, Pass 2 constructs the real `CognitionExtractionInput`, counts the exact extraction request with the resolved Pass 2 request, and checks its own total-capacity equation before delegation;
3. Pass 2 does not silently rewrite the originating governed cognitive input or run a second degradation loop;
4. Pass 2 overflow is represented by the existing content-free `pass2_budget_exceeded` extraction failure, with no extraction-provider call and no Pass 2 State/Continuity proposals;
5. buffered and streaming paths carry the same per-pass requests and budget identity.

The historical single-pass path remains one semantic generation. Core 1.0 two-pass intentionally contains the two sequential generations owned by #1533; this bridge does not add any evaluation-only model call beyond that topology.

## Successful turn evidence

Historical single-pass successfully generated turns may carry `cognitive_budget` diagnostics copied from the runtime's aggregate content-free diagnostics:

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

For Core 1.0 two-pass evidence, the citable per-pass capacity configuration lives in `manifest.cognitive_budget`, while the turn's existing `cognition_execution` observation records the Pass 2 terminal disposition. A local Pass 2 capacity rejection is therefore observable as:

```text
cognition_execution.mode = two_pass
cognition_execution.pass2_status = failed
cognition_execution.pass2_failure_reason = pass2_budget_exceeded
```

No fake Pass 2 raw output is created when the provider was not called. A successful Pass 2 continues to expose its normal committed/stale/failed execution observation and raw proposal evidence according to the existing cognition-execution contract.

Raw model output and deterministic State/Continuity decisions remain separate from budget identity exactly as before.

## Bounded pre-generation failure evidence

For the historical single-pass diagnostic path, a protected-floor overflow or degradation-exhaustion condition remains valid calibration evidence even though no model response exists.

The harness preserves a top-level `bounded_failure` observation containing:

- failed turn index and already-known semantic fixture input;
- `provider_generation_occurred: false`;
- the same content-free budget diagnostics;
- outcome `bounded_failure`;
- #1387 failure reason (`protected_floor_exceeds_context` or `degradation_exhausted`);
- final count mode and token counts;
- applied degradation count.

The failed turn does **not** receive fabricated `RawModelObservation` or deterministic candidate decisions. Prior successfully completed turns, if any, remain in `turns`.

For two-pass execution, Pass 2 overflow occurs after the valid visible response and is therefore not a top-level pre-generation failure for the whole turn. It is preserved through the cognition-execution failure observation described above. The visible response remains evidence; no extraction output is fabricated.

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

- manifest total-budget identity, including explicit Pass 1 / Pass 2 totals when the run uses the Core 1.0 two-pass budget shape;
- historical single-pass per-successful-turn aggregate budget diagnostics;
- two-pass cognition-execution disposition, including bounded `pass2_budget_exceeded` when applicable;
- optional historical single-pass top-level bounded failure evidence.

Existing content-addressed run/execution/pressure identity naturally includes the declared cognitive-budget configuration through `manifest.to_mapping()`.

## Ownership boundaries

This bridge does not own or modify:

- total-budget arithmetic, protection tiers, degradation order, token-count semantics, or failure reasons — #1387;
- Pass 1 / Pass 2 cognition responsibilities, response-first ordering, or stale semantics — #1533;
- Retrieval or Context Compiler selection semantics — #1267;
- Continuity acceptance/lifecycle semantics — #1371;
- provider wire or decoding semantics — #1456 provider authority;
- runtime-config discovery/precedence/CLI semantics — #1446;
- calibration values/profile boundaries/default selection — #1388.

## Calibration gate consequence

After this bridge is merged, #1386 can represent and execute machine-auditable per-pass total-budget evidence using the same Core 1.0 two-pass runtime mechanics **when an actual-model host supplies an explicit matching `TwoPassCognitiveBudgetRuntimeConfig` and provider/model pass-aware token counter**.

This generic bridge does not itself choose Pass 1 / Pass 2 reserves and does not make the current vLLM Stage R0 plan budget-calibrated. The citable host/screening layer must still carry an explicit per-pass runtime identity before #1718 can close. #1388 remains the owner of evidence-backed numeric profile/default selection.
