# Free-form current State-shadow evaluation

`src/relaylm/evaluation_freeform_current_state_shadow.py` provides the isolated deterministic `freeform_current_state_shadow` evaluation component for the merged #1267 Context Compiler C4 capability from PR #1385.

## Current component contract

`evaluate_freeform_current_state_shadow()` calls the real `compile_cognitive_input(...)` API and observes only the resulting MEMORY residency. It does not reproduce the Context Compiler's current-claim grammar.

The deterministic fixture verifies that:

- a line-leading `Current <canonical key> is <value>` scalar conflict is suppressed by active Canonical State;
- an explicit current scalar claim matching active State is retained;
- `<canonical key> is now <value>` is also an explicit-current claim;
- a prefixed phrase such as `Previous current ...` remains outside the C4 grammar;
- historical or temporally ambiguous free-form key prose remains resident for later interpretation;
- free-form prose that omits the canonical key is not semantically mapped by C4;
- free-form boolean claims are not added to the scalar C4 rule.

All checks are attributed to the `context_compiler` boundary. The component deliberately preserves C4's bounded negative space rather than widening contradiction semantics.

## Non-goals

This component does not add historical/current interpretation, alias or synonym inference, omitted-key mapping, negation handling, free-form boolean/degree semantics, retrieval ranking changes, State mutation, MEMORY mutation, or any LLM contradiction classifier.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
