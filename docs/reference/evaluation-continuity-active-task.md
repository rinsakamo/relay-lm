# Continuity active-task evaluation

`src/relaylm/evaluation_continuity_active_task.py` provides the isolated deterministic `continuity_active_task_retention` evaluation component for the merged #1267 Context Compiler C3 capability from PR #1381.

## Current component contract

`evaluate_continuity_active_task_retention()` calls the real `compile_cognitive_input(...)` and `compile_cognitive_input_with_diagnostics(...)` APIs. It does not reproduce Context Compiler projection logic or Continuity lifecycle semantics.

The deterministic fixture verifies that:

- an already-accepted `active_task` remains in current cognition when recent Event-derived Working Context Event and character budgets are both zero;
- accepted Event source IDs and `assistant_commitment` survive projection while the compiler-generated `ContextItem.actor` remains unset;
- accepted tuple order is preserved across `referent`, `active_task`, and `unresolved`;
- the diagnostic compiler projects the same accepted task while retaining only the existing four compiler-owned diagnostic layers.

## Non-goals

This component does not infer or classify tasks from raw language, decide whether a task should be active, accept or advance Continuity candidates, change referent/unresolved semantics, wire ordinary-turn runtime continuity into compilation, add a diagnostic layer, persist Continuity, or choose runtime/default budgets.

## Integration status

PR #1389 registers this already-merged component in the native evaluation registry and shared evaluation/navigation surfaces without changing its semantics.
