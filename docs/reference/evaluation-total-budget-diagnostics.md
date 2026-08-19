# Total Budget diagnostics evaluation

`src/relaylm/evaluation_total_budget_diagnostics.py` provides the isolated deterministic `total_budget_diagnostics` evaluation component for the merged #1387 aggregate total-budget diagnostics capability from PR #1417.

## Current component contract

`evaluate_total_budget_diagnostics()` consumes the real `diagnostics_for_budget_result(...)` and `diagnostics_for_budget_failure(...)` APIs. It observes only aggregate diagnostic values and schema; it does not reproduce Budget enforcement or retain semantic payload.

The deterministic fixture verifies that:

- fit diagnostics expose configured/effective capacities, framing/final/cognitive token counts, zero pressure/reductions, and exact count mode;
- degraded-fit diagnostics aggregate applied reductions by distinct layer and protection tier while preserving conservative-estimate count mode;
- protected-floor and degradation-exhaustion failures retain bounded failure reason and deterministic reduction counts;
- diagnostics fields and repr remain content-free even when the originating successful enforcement result contains a deliberately identifiable semantic payload;
- available cognitive capacity clamps to zero when required framing exceeds effective serialized-input capacity;
- failure diagnostics reject a mismatched total-budget config and result diagnostics reject degradation-step counts outside the configured policy.

## Current-authority note

PR #1421 extends the same `budget_diagnostics.py` owner with failure-attached diagnostics and explicit Turn/runtime APIs. This component was reconstructed onto that merged authority and intentionally evaluates only the preserved #1417 aggregate result/failure diagnostic primitives.

## Non-goals

This component does not change Budget diagnostics/enforcement semantics, evaluate #1421 Turn/runtime diagnostics exposure, expose semantic payload, alter provider serialization/token counting, or choose numeric calibration/defaults.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, shared navigation, and aggregate Issue status remain for Serial Integration after component merge.
