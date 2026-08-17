# Continuity Context retention evaluation

`src/relaylm/evaluation_continuity_context_retention.py` provides the isolated deterministic `continuity_context_retention` evaluation component for the merged #1267 Context Compiler C2 capability from PR #1378.

## Current component contract

`evaluate_continuity_context_retention()` calls the real `compile_cognitive_input(...)` and `compile_cognitive_input_with_diagnostics(...)` APIs. It does not reproduce Context Compiler projection logic or Continuity lifecycle semantics.

The deterministic fixture verifies that:

- already-accepted `referent` and `unresolved` Continuity items remain in current cognition when recent Event-derived Working Context Event and character budgets are both zero;
- accepted Event source IDs and epistemic role survive projection while the compiler-generated `ContextItem.actor` remains unset;
- accepted Continuity precedes recent Working Context without reordering the recent user/assistant Event projection;
- the diagnostic compiler produces the same Continuity projection while retaining the existing four compiler-owned diagnostic layers only;
- an empty accepted Continuity Context preserves an empty context when recent Working Context budgets are zero.

The component deliberately asserts only C2 positive semantics that remain valid after later accepted-kind extensions. It does not assert the temporary C2 exclusion of `active_task`; PR #1381 has since merged C3 and extended the same accepted Continuity projection while preserving these C2 invariants.

## Non-goals

This component does not accept or classify Continuity candidates, advance Continuity lifecycle, infer referents/questions/tasks from raw language, change Context Compiler selection policy, wire `ContinuityRuntime.context` through ordinary turns, add a diagnostics layer, or choose runtime/default budgets.

## Integration status

This component is intentionally not registered in the native evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
