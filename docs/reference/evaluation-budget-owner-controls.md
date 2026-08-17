# Budget owner-control translation evaluation

`src/relaylm/evaluation_budget_owner_controls.py` provides the isolated deterministic `budget_owner_controls` evaluation component for the merged #1387 Cognitive Budget owner-control translation from PR #1399.

## Current component contract

`evaluate_budget_owner_controls()` consumes the real `owner_controls_for_budget_plan(...)` API. It observes the translated owner-control values rather than independently applying BudgetPlan caps to Context Compiler or Retrieval selectors.

The deterministic fixture verifies that:

- current BudgetPlan caps translate exactly to existing Context Compiler controls for Canonical State and Working Context;
- current Retrieved Memory and Event Evidence caps translate exactly to existing Retrieval selector parameter units;
- policy floors remain Budget/degradation-policy inputs and do not change translated current caps;
- no accepted-Continuity pressure or selection control is introduced by the translation surface.

## Non-goals

This component does not execute selectors, redefine Context Compiler or Retrieval semantics, add Continuity pressure semantics, validate B3 serialized-token accounting, enforce total budget at runtime, or choose numeric defaults/calibration.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
