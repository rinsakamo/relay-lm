# Cognitive Budget turn diagnostics evaluation

`src/relaylm/evaluation_cognitive_budget_turn_diagnostics.py` provides the isolated deterministic `cognitive_budget_turn_diagnostics` evaluation component for the merged #1387 explicit Turn/runtime Cognitive Budget diagnostics capability from PR #1421.

## Current component contract

`evaluate_cognitive_budget_turn_diagnostics()` calls the real buffered and streaming Cognitive Budget diagnostic ordinary-turn APIs. It observes returned aggregate diagnostics and bounded diagnostic failures without reproducing Budget accounting, degradation, or Turn orchestration.

The deterministic fixture verifies that:

- a fitting buffered turn returns content-free fit diagnostics after exactly one semantic provider generation;
- a pressured buffered turn returns degraded-fit reduction counts after exactly one provider generation on the final fitting input;
- protected-floor overflow raises the diagnostic failure subtype while remaining catchable as `CognitiveBudgetExceeded`, performs no provider generation, and does not leak user content into diagnostics or failure text;
- degradation exhaustion exposes deterministic reduction counts before any provider generation;
- the streaming diagnostic API returns fit diagnostics after exactly one streamed semantic generation.

## Non-goals

This component does not change Turn/runtime or Budget diagnostics semantics, alter provider serialization/token counting, redefine Context Compiler or Retrieval semantics, add semantic payload diagnostics, or choose numeric defaults/calibration.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, shared navigation, and aggregate Issue status remain for Serial Integration after component merge.
