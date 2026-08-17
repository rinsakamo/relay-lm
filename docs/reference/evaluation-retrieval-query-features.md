# Retrieval query feature evaluation

`src/relaylm/evaluation_retrieval_query_features.py` provides the isolated deterministic evaluation component `retrieval_query_features` for the merged #1267 Retrieval semantics from PRs #1363 and #1366.

## Current component contract

`evaluate_retrieval_query_features()` calls the real MEMORY selector, Event selector, and `EventDiscoveryIndex` APIs. It does not reproduce lexical normalization or ranking implementation.

The deterministic fixture verifies that:

- repeated normalized query feature `coffee` does not outweigh two distinct features `fukuoka` and `trip` in MEMORY selection;
- the same distinct-feature rule selects the two-feature Event rather than the repeated single-feature Event;
- generic iterable Event selection and `EventDiscoveryIndex` selection converge on the same Event;
- direct `EventDiscoveryIndex.candidate_scores(...)` counts each supplied query feature at most once, including when a caller passes repeated features.

The component preserves source-specific ranking policy: MEMORY heading/body weights remain MEMORY-owned, while Event overlap scoring and tie-break behavior remain Event-owned. The shared contract being evaluated is only that query multiplicity is not additional relevance evidence.

## Non-goals

This component does not change lexical features, CJK behavior, ranking weights, budgets, Event Journal authority, Context authority, turn orchestration, or any provider/storage semantics. It does not claim semantic/vector/temporal relevance or actual-model quality.

## Integration status

This component is intentionally not registered in the native evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and #1247 aggregate status remain pending for serial integration.
