# Total budget accounting evaluation

`src/relaylm/evaluation_total_budget_accounting.py` provides the isolated deterministic `total_budget_accounting` evaluation component for the merged #1387 Cognitive Budget B1 capability from PR #1390.

## Current component contract

`evaluate_total_budget_accounting()` consumes the real `TotalBudgetConfig`, `ProtectedAnchorTokenCounts`, and `TotalBudgetAccounting` types. It does not reproduce the accounting arithmetic in an independent evaluator implementation; checks observe only the public B1 properties and constructor validation behavior.

The deterministic fixture verifies that:

- the hard context equation accounts separately for model context, reserved output capacity, required input framing, Identity, Current Event, and remaining degradable cognitive-input capacity;
- an impossible protected floor remains explicitly observable through negative remaining capacity, a false fit predicate, and exact overflow count;
- an output reservation larger than the context window clamps usable capacities to zero while preserving the negative arithmetic and exact overflow;
- invalid explicit token counts fail closed, including booleans masquerading as integers;
- required B1 token-count inputs have no numeric defaults and must be supplied explicitly.

## Non-goals

This component does not define degradation order, per-layer envelopes/floors, Continuity pressure semantics, runtime fail-before-generation behavior, provider serialization/tokenization, numeric calibration/defaults, or semantic content selection.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
