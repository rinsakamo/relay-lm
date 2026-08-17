# Serialized fit enforcement evaluation

`src/relaylm/evaluation_serialized_fit_enforcement.py` provides the isolated deterministic `serialized_fit_enforcement` evaluation component for the merged #1387 serialized-fit enforcement loop from PR #1408.

## Current component contract

`evaluate_serialized_fit_enforcement()` consumes the real `enforce_serialized_input_budget(...)` API. It supplies deterministic semantic-owner compiler callbacks and serialized-input count sequences, then observes the enforcement result or bounded pre-generation failure.

The deterministic fixture verifies that:

- an initially fitting serialized input returns with `fit`, zero degradation steps, and no pressure;
- an overflowing initial plan is recompiled with the next explicitly configured BudgetPlan and returns only after the final serialized input fits;
- exhausting all configured degradation steps raises `CognitiveBudgetExceeded` with `degradation_exhausted`, final plan/count metadata, and no semantic `CognitiveInput` payload on the exception;
- identical plan and token-count sequences produce identical enforcement sequences;
- untyped compiler or token-counter results fail closed.

## Non-goals

This component does not evaluate the later protected-anchor floor guard/wrapper from #1410, define semantic owner projections, change degradation policy, perform provider generation, add Continuity pressure semantics, or choose tokenizer/calibration defaults.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
