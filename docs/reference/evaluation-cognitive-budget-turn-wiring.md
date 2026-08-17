# Cognitive Budget turn wiring evaluation

`src/relaylm/evaluation_cognitive_budget_turn_wiring.py` provides the isolated deterministic `cognitive_budget_turn_wiring` evaluation component for the merged #1387 Turn/runtime Cognitive Budget wiring from PR #1412.

## Current component contract

`evaluate_cognitive_budget_turn_wiring()` calls the real buffered and streaming ordinary-turn APIs with explicit `CognitiveBudgetRuntimeConfig`. It does not reproduce Budget accounting, degradation, protected-floor enforcement, Context Compiler selection, or Retrieval ranking.

The deterministic fixture verifies that:

- a fitting buffered budget path performs protected/full counting before exactly one provider generation and commits the normal User/Assistant Event pair;
- pressure recompiles through the configured BudgetPlan degradation before exactly one provider generation, without mutating durable Canonical State merely because State was omitted from the final cognitive projection;
- protected-floor overflow and degradation exhaustion both fail before any provider generation while preserving the already-persisted User Event and durable State;
- explicit Cognitive Budget cannot be combined with legacy MEMORY/Event retrieval budgets, and that invalid configuration is rejected before User Event append;
- the streaming path performs exactly one streamed semantic generation only after serialized fit and commits the same ordinary-turn Event boundary.

## Non-goals

This component does not change Turn/runtime semantics, extend cognitive-budget support to diagnostic variants not owned by #1412, alter Budget accounting/degradation/guard semantics, modify provider serialization/token counting, redefine Context Compiler or Retrieval semantics, or choose numeric defaults/calibration.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for Serial Integration after component merge.
