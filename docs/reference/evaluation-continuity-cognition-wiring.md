# Continuity cognition wiring evaluation

`src/relaylm/evaluation_continuity_cognition_wiring.py` provides the isolated deterministic `continuity_cognition_wiring` evaluation component for the merged #1267 Turn/Runtime capability from PR #1383.

## Current component contract

`evaluate_continuity_cognition_wiring()` calls the four real ordinary-turn public APIs: buffered, buffered with retrieval diagnostics, streaming, and streaming with retrieval diagnostics. It does not reproduce Turn orchestration, Context Compiler projection, or Continuity lifecycle rules.

The deterministic fixture verifies that:

- each public ordinary-turn variant performs exactly one semantic provider generation;
- an explicit `ContinuityRuntime` supplies its current accepted pre-generation `ContinuityContext` to the provider-facing `CognitiveInput` through the real Context Compiler path;
- the projected accepted referent preserves its Event sources and epistemic role while the compiler-generated `ContextItem.actor` remains unset;
- buffered generation observes the pre-turn runtime revision and the runtime advances only after successful generation;
- streamed generation keeps the accepted revision unchanged while response deltas are emitted and advances only after structured completion;
- retrieval-diagnostics variants use the same Continuity input path without adding a Continuity diagnostics authority.

## Non-goals

This component does not redefine accepted Continuity projection, infer Continuity from raw language, change Continuity acceptance/lifecycle, alter retrieval selection or diagnostics semantics, persist Continuity, or choose runtime/default capacity and lifetime policy.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
