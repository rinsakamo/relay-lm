# Protected serialized-floor evaluation

`src/relaylm/evaluation_protected_serialized_floor.py` provides the isolated deterministic `protected_serialized_floor` evaluation component for the merged #1387 protected serialized-floor guard and total-enforcement wrapper from PR #1410.

## Current component contract

`evaluate_protected_serialized_floor()` consumes the real `enforce_protected_serialized_input_floor(...)` and `enforce_total_cognitive_budget(...)` APIs. It supplies explicit owner-side protected/full `CognitiveInput` projections and one serialized-input counter, then observes only enforcement ordering, counts, results, and bounded failure metadata.

The deterministic fixture verifies that:

- a protected framing/Identity/Current Event projection that cannot fit with reserved output fails before any full BudgetPlan compilation or degradation;
- a fitting protected projection is counted first, after which the same serialized-input counter is used for full enforcement;
- the direct protected-floor guard returns its authoritative serialized token count when the floor fits;
- protected-floor overflow reports `protected_floor_exceeds_context`, `final_plan=None`, zero degradation steps, exact final count/overflow, and no semantic `CognitiveInput` payload;
- invalid protected projections, untyped counter results, and untyped protected compiler results fail closed.

## Non-goals

This component does not define how Context/Turn semantic owners construct the protected projection, wire total-budget enforcement into ordinary generation, change provider serialization/token counting, add Continuity pressure selection, or choose tokenizer/calibration defaults.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
