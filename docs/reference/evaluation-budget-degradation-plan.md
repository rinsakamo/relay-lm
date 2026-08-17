# Budget degradation plan evaluation

`src/relaylm/evaluation_budget_degradation_plan.py` provides the isolated deterministic `budget_degradation_plan` evaluation component for the merged #1387 Cognitive Budget B2 capability from PR #1397.

## Current component contract

`evaluate_budget_degradation_plan()` consumes the real `BudgetPlan`, envelope, `BudgetLayer`, `BudgetDegradationStep`, and `BudgetDegradationPolicy` APIs. It does not independently choose layer reductions or inspect semantic payload.

The deterministic fixture verifies that:

- B2 manages only layers whose semantic owners already expose deterministic pressure controls: Canonical State, Working Context, Retrieved Memory, and Event Evidence;
- accepted Continuity is absent from the B2 plan because no owner-defined pressure/subset contract exists yet;
- explicit degradation reaches Tier 3 floors before Tier 2, and Tier 2 before Tier 1;
- caller order within Tier 3 remains explicit and deterministic rather than being replaced with cross-layer relevance ranking;
- attempts to reduce Tier 2 or Tier 1 too early, or to return to a lower-protection tier, are rejected;
- layer envelopes must reduce monotonically and preserve configured floors;
- envelope bounds and partial-plan step counts are explicit validated inputs and do not acquire numeric defaults.

## Non-goals

This component does not define Continuity pressure semantics, cross-layer semantic relevance, degradation target amounts, runtime fail-before-generation behavior, provider serialization/tokenization, numeric calibration/defaults, or semantic-layer selection itself.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
