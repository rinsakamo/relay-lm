# Continuity lifecycle evaluation

`src/relaylm/evaluation_continuity_lifecycle.py` provides the isolated deterministic `continuity_lifecycle` evaluation component for the merged #1371 K1/K2 Continuity foundation from PRs #1374 and #1375.

## Current component contract

`evaluate_continuity_lifecycle()` calls the real `apply_continuity_candidates(...)` validation API. It does not reproduce Continuity acceptance or lifecycle rules.

The deterministic fixture verifies:

- a provenance-backed `user_assertion` is admitted into bounded Continuity Context;
- accepted nested semantic values are detached and deeply immutable from proposal-side mutation;
- an exact duplicate is a noop, advances the context revision, and does not refresh item lifetime;
- a changed valid proposal on the same lifecycle key supersedes the accepted item;
- unknown Event provenance is rejected without changing accepted membership;
- a same-kind keyed `resolve` removes the accepted item;
- reached lifetime expiry is applied at the next revision before candidate processing;
- capacity pressure deterministically evicts the oldest accepted item.

All checks are attributed to the `continuity_validation` boundary. Metrics report only bounded transition counts from the deterministic fixture.

## Non-goals

This component does not choose default capacity or lifetime, infer continuity from raw language, persist Continuity Context, change Event/State/MEMORY authority, exercise Context Compiler C2/C3 retention, or redefine ordinary-turn K3 orchestration.

## Integration status

This component is intentionally not registered in the native evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
