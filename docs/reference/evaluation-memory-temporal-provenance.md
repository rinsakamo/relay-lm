# MEMORY temporal provenance evaluation

`src/relaylm/evaluation_memory_temporal_provenance.py` provides the isolated deterministic `memory_temporal_provenance` evaluation component for the merged #1409/#1260 MEMORY temporal/provenance MP1 capability from PR #1422.

## Current component contract

`evaluate_memory_temporal_provenance()` consumes the real `MemoryTemporalScope`, `MemoryProvenanceSourceKind`, `MemoryProvenanceSource`, `MemoryProvenance`, and `MemoryTemporalAuthority` types. It observes only the typed authority model and constructor validation behavior; it does not derive temporal meaning from MEMORY prose.

The deterministic fixture verifies that:

- the temporal domain is closed to `current`, `historical`, and first-class `unknown`;
- provenance source roots are typed `event` or `state` references only;
- classified `current` and `historical` authority requires explicit typed provenance;
- provenance requires stable logical `memory_id`, `derivation_id`, and at least one typed source;
- `unknown` may preserve known provenance without being promoted to current or historical authority;
- prose-like temporal/source values, empty identities or sources, and untyped provenance inputs fail closed.

## Non-goals

This component does not implement or evaluate governed MEMORY Markdown metadata carriage/parsing (MP2), Context Compiler C5 temporal consumption, Retrieval relevance/ranking, raw-language/year/tense/heading inference, MEMORY mutation, or Canonical State promotion.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for Serial Integration after component merge.
