# Calibration candidate sweep contract

Status: CAL2 candidate-derivation contract for RelayLM v1.

Owning Issue: #1388.

Parent contract: `docs/contracts/calibration-evidence.md` (`calibration-contract-v1`).

Related semantic owners: #1387 Cognitive Budget, #1386 Actual-model Evaluation, #1247 deterministic evaluation, #1267 Context Compiler / layer-local controls.

This contract defines how CAL2 may construct **experimental budget candidates** from measured runtime boundaries without turning those candidates into canonical runtime defaults.

It exists to prevent a circular dependency in which Actual-model Evaluation waits for a canonical default before producing pressure evidence while Calibration waits for pressure evidence before selecting that default.

## Candidate versus canonical default

A CAL2 candidate is an experiment input. It is not a runtime recommendation, profile, release default, or compatibility promise.

Calibration may freeze candidate values for a controlled experiment before CAL6 only when every value is traceable to one of:

- an exact observed provider/runtime capacity;
- an exact observed serialized-token count;
- an exact deterministic fit/failure boundary;
- an exact semantic-owner selection breakpoint;
- a mathematically derived adjacent integer boundary from one of those observations.

Calibration must not select an experimental value because it is a familiar round number, a vendor convention, a percentage that merely looks reasonable, or a desired future default.

Canonical runtime/profile selection remains prohibited until CAL6.

## Required freeze point

Before deriving or executing a CAL2 candidate matrix, freeze all evidence identity required by `calibration-contract-v1`, including:

- exact RelayLM commit;
- exact model artifact and serving-tokenizer identity;
- provider and adapter identity plus declared capabilities;
- effective model context window;
- decoding configuration and seed policy;
- scenario-set and Character fixture revisions;
- execution path and Continuity Runtime identity where applicable;
- exact serialized-input token-counter implementation and count mode;
- complete caller-supplied #1387 BudgetPlan and degradation policy.

No canonical sweep may begin while an open writer is changing Context Compiler selection semantics, Retrieval semantics, Cognitive Budget semantics, provider serialization/token counting, or Actual-model evidence carriage used by the run.

Historical runs remain citable historical evidence but do not automatically survive a changed freeze point.

## Fixed model-context identity

For one controlled target condition, `TotalBudgetConfig.model_context_window` must equal the effective context window recorded by the #1386 run manifest.

Calibration must not simulate pressure by lying about the provider/model context window while claiming an otherwise identical runtime identity.

Pressure is introduced through explicit output reservation and legal layer envelopes/degradation policy while the effective provider/model context identity remains fixed.

## Measurement probe

CAL2 begins with a measurement probe, not a quality comparison.

The probe must use the frozen target and exact serialized-input counter with:

- `model_context_window` equal to the observed effective provider context window `W`;
- `reserved_output_tokens = 0` as an explicit **diagnostic lower-bound sentinel**, never as a runtime recommendation or default;
- a source-justified initial BudgetPlan demonstrated not to truncate the selected scenario under the current semantic-owner controls;
- the exact degradation policy identity intended for the later controlled sweep.

The probe exists only to expose the unpressured serialized-input boundary under the exact target serialization.

Record at least:

- `W`, the effective model context window;
- `T0`, the final serialized input token count when the probe fits without degradation;
- required input-framing token count;
- final cognitive-input token count;
- count mode;
- whether any unexpected pressure/degradation occurred.

If the supposed measurement probe degrades or fails, the initial plan is not a valid non-pressure reference for that scenario and must not be used to derive quality candidates.

## Derived reserve breakpoints

When an exact or approved conservative serialized-input count `T0` is available and `T0 <= W`, CAL2 may derive reserve boundaries algebraically.

The first exact fit-boundary reserve is:

```text
R_fit = W - T0
```

At that reserve, effective serialized-input capacity equals the observed unpressured serialized-input size.

The immediately adjacent first-pressure probe is:

```text
R_first_pressure = R_fit + 1
```

when `R_first_pressure <= W`.

This `+1` is not a tuning heuristic. It is the adjacent integer boundary that makes the previously observed serialized input exceed capacity by exactly one token before legal degradation.

Both values are experiment candidates only. They are not output-reserve defaults.

If the counter mode is `conservative_estimate`, derived boundaries inherit that mode and conclusions must be labeled conservative rather than exact.

## Protected-floor boundary discovery

The protected-floor boundary must be discovered from #1387 enforcement, not guessed.

For the same frozen target, protected anchors, and serialized-input counter, search the integer output-reserve domain monotonically for the adjacent pair:

- `R_protected_pass_max`: the greatest reserve for which the protected serialized-input floor still fits;
- `R_protected_fail_min`: the least reserve for which #1387 reports `PROTECTED_FLOOR_EXCEEDS_CONTEXT`.

For an exact integer-token counter, the adjacent boundary must satisfy:

```text
R_protected_fail_min = R_protected_pass_max + 1
```

The search must use the existing #1387 protected-floor enforcement semantics. Calibration must not implement a second protected-floor equation or infer hidden anchor token counts.

The failing side is deterministic pre-generation evidence only. It must not be scored as model-quality evidence because no provider generation occurs.

A structurally guaranteed impossible-floor sentinel may use `reserved_output_tokens = W`, because it leaves zero serialized-input capacity. It is a diagnostic boundary case only and is never a runtime/default candidate.

## Near-protected-floor candidate

The canonical CAL2 `near_protected_floor` experiment point is derived from the discovered protected boundary, not from a percentage of the model context window.

Use `R_protected_pass_max` with the same protected anchors and policy, then execute only if at least one legal degradable layer remains present in the scenario.

If no legal degradable content remains, record the family as not representable for that scenario rather than inventing another pressure source.

## Layer-selection breakpoint discovery

Retrieval, Working Context, and Canonical State pressure candidates must be tied to semantic-owner selection transitions.

For each legal owner control under test:

1. keep model/provider/serialization identity fixed;
2. vary only the selected layer cap while keeping its floor fixed for that sub-sweep;
3. execute the existing deterministic owner path without model generation where possible;
4. record only cap values at which the owner-visible selected item count or character occupancy changes;
5. use those exact transition values as candidate layer breakpoints.

Calibration must not manufacture a layer breakpoint by applying arbitrary percentages to a maximum cap.

When a layer exposes both item and character caps, vary one dimension at a time until its transition boundary is understood. A later two-dimensional condition may combine already-observed transition values, but the combined condition must identify both source observations.

## Floor exploration

Floors are independent experiment axes and must not be silently inferred from maxima.

A floor value under test is legal only when:

- the #1387 envelope accepts it;
- the semantic owner can represent the corresponding projection;
- the rationale is explicit in the matrix row.

A zero floor may be used only as a labeled diagnostic lower-bound condition where the owner contract permits zero. It does not mean that zero is an acceptable product default.

For product-quality candidate profiles, floor selection must be supported by preceding breakpoint evidence showing which retained authority is necessary for the scenario family. If that evidence does not yet exist, product-default floor selection remains blocked.

## Pressure-family construction

CAL2 constructs the required pressure families from observed boundaries as follows.

### `baseline_fit`

Use a non-pressure condition demonstrated to fit without degradation under the exact frozen target. It is the comparison reference, not necessarily a future runtime default.

### `retrieval_pressure`

Use an observed MEMORY or Event Evidence owner-selection breakpoint together with an output-reserve boundary that causes optional retrieval content to compete for total capacity.

The condition must not change Retrieval ranking semantics.

### `working_context_pressure`

Use an observed Working Context item/character selection breakpoint while holding unrelated layer controls constant.

The condition must not invent a new Working Context eviction rule.

### `current_authority_pressure`

Use an observed Canonical State selection breakpoint and an explicit floor under test while preserving Tier 0 framing, Identity, and Current Event.

The experiment may observe higher-protection degradation only after all lower-protection legal reductions required by #1387 are exhausted.

### `near_protected_floor`

Use `R_protected_pass_max` as defined above with legal degradable content present.

### `impossible_protected_floor`

Use `R_protected_fail_min` or the structurally impossible reserve sentinel `W` and preserve the bounded pre-generation failure as deterministic evidence.

No model-quality review is attached to a turn on which provider generation did not occur.

## Minimal quality execution set

CAL2 need not generate model output for every integer cap or reserve inspected while locating deterministic boundaries.

Model generation should be reserved for evidence-bearing candidate points:

- one valid `baseline_fit` reference;
- each distinct first-pressure / owner-selection breakpoint selected for comparison;
- the last legal point before a material protected-floor boundary where semantic generation still occurs;
- repeated runs required to evaluate stability.

Deterministic search points used only to locate boundaries remain deterministic calibration observations and must not be inflated into model-quality sample counts.

## Controlled comparison validity

A baseline/pressure pair is valid only when the non-budget identity required by `calibration-contract-v1` is unchanged.

For total-budget comparisons, changes are limited to the declared budget condition and condition identity. If model bytes, tokenizer/counting mode, provider serialization, scenario revision, Character fixture, decoding policy, Continuity Runtime, or semantic-owner behavior drifts between conditions, the pair is invalid for CAL3 breakpoint inference.

## Current implementation dependency

The repository-neutral #1386 bridge for explicit `CognitiveBudgetRuntimeConfig` evidence is implemented: it can preserve total-budget identity, final serialized-token diagnostics, degradation observations, and bounded pre-generation failures when supplied a truthful runtime and token counter.

The canonical LM Studio host runner currently does not construct a provider/model-specific serialized-input token counter or bind an explicit total `CognitiveBudgetRuntimeConfig` from its host condition. Normal foundation-v2 LM Studio evidence therefore does not by itself satisfy this CAL2 sweep contract.

That host-local execution dependency belongs to #1386 or an explicitly delegated evidence-execution owner. Calibration must not fork a second LM Studio/Actual-model runner.

Once the host path supplies the frozen token counter and total-budget runtime, the measurement probe and derived candidate rules above provide the experiment values; #1386 does **not** need a canonical runtime default from CAL6 in order to execute CAL2.

## CAL2 completion boundary

CAL2 is complete only when controlled actual-model evidence exists for all representable required pressure families under one frozen target/capability class, with:

- immutable #1386 execution identities;
- exact or explicitly conservative token-count mode;
- complete budget/policy identity;
- deterministic boundary evidence;
- product-quality reviews for generated turns;
- explicit not-representable records for any family blocked by an owner contract.

CAL2 completion does not select a canonical profile or runtime default. Its output is the evidence matrix consumed by CAL3 breakpoint analysis.

## Canonical-default prohibition

Nothing in this contract selects a canonical numeric output reserve, State/Working Context/MEMORY/Event envelope, degradation threshold, small/standard/large profile, or release runtime default.

Those decisions remain gated on CAL3 breakpoint analysis, CAL4 profile evidence where applicable, CAL5 deterministic regression validation, and CAL6 provenance-backed canonicalization.

Refs #1388 #1387 #1386 #1247 #1267
