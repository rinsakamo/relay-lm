# Continuity turn evaluation

`src/relaylm/evaluation_continuity_turn.py` provides the isolated deterministic `continuity_turn` evaluation component for the merged #1371 K3 ordinary-turn Continuity orchestration from PR #1376.

## Current component contract

`evaluate_continuity_turn()` calls the real buffered and streaming ordinary-turn APIs with an explicitly supplied `ContinuityRuntime`. It does not reproduce Continuity lifecycle or Turn orchestration semantics.

The deterministic fixture verifies:

- buffered execution commits accepted Continuity from exactly one `provider.generate()` call;
- streaming execution uses one `stream_generate()` call and leaves Continuity Context unchanged while response deltas are emitted, committing only after structured completion;
- an explicitly configured runtime advances its revision even when the completed cognitive output contains no continuity candidates;
- non-empty continuity output without an explicit runtime is rejected after the single provider generation but before Assistant Event, State, or Continuity commit.

Checks are attributed to the `provider` or `turn_runtime` boundary. Metrics contain only provider-call and emitted-delta counts from the deterministic fixture.

## Non-goals

This component does not redefine K1/K2 Continuity semantics, choose runtime capacity/lifetime defaults, expand provider-specific structured grammar, exercise Context Compiler C2/C3 retention, persist Continuity Context, or change State/MEMORY/Event authority.

## Integration status

PR #1389 registers this already-merged component in the native evaluation registry and shared evaluation/navigation surfaces without changing its semantics.
