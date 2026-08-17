# Degree State/MEMORY authority evaluation

`src/relaylm/evaluation_degree_state_memory_authority.py` provides the isolated deterministic evaluation component `degree_state_memory_authority` for the merged #1267 degree-level Context Compiler authority slice from PR #1364.

## Current component contract

`evaluate_degree_state_memory_authority()` returns the existing `EvaluationScenarioResult` shape and calls the real `compile_cognitive_input(...)` Context Compiler API. It does not reproduce or replace State/MEMORY authority logic.

The deterministic fixture uses active `user.preference / tea = {semantic: likes, degree_hint: 0.85}` and verifies seven bounded cases:

- heading-addressed `likes` with explicit stale `degree_hint: 0.65` is suppressed;
- heading-addressed `likes` with matching `degree_hint: 0.85` remains resident;
- matching semantic text with no explicit degree remains resident rather than inferring a conflict;
- conflicting `dislikes` is suppressed even when the numeric degree matches, so degree cannot rescue semantic conflict;
- inline-only `tea: likes; degree_hint: 0.65` is suppressed by the same-line degree claim;
- inline `tea: likes` does not borrow `degree_hint` from a separate `coffee` assignment line;
- unaddressed historical prose containing a degree field remains resident.

All checks are attributed to the `context_compiler` boundary. Metrics are bounded fixture counts only.

## Non-goals

This component does not infer adjective/free-form intensity, degree ordering or tolerance, cross-key degree comparison, arbitrary natural-language contradiction, historical/current intent, or actual-model quality. It changes no Context Compiler, State, retrieval, turn/runtime, persistence, provider, or storage semantics.

## Integration status

This component is intentionally not registered in the native evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and #1247 aggregate status remain for the serial integration lane after component merge.
