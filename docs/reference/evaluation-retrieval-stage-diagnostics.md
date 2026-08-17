# Retrieval-stage diagnostics evaluation component

`src/relaylm/evaluation_retrieval_diagnostics.py` provides the isolated deterministic evaluation component `retrieval_stage_diagnostics`.

## Current component contract

`evaluate_retrieval_stage_diagnostics()` returns the existing `EvaluationScenarioResult` shape and calls the real public selector APIs:

- `select_memory_chunks(...)`;
- `select_memory_chunks_with_diagnostics(...)`;
- `select_event_evidence(...)`;
- `select_event_evidence_with_diagnostics(...)`.

The component does not reproduce MEMORY or Event ranking, eligibility, admission, or budget logic. Selector implementation remains owned by `memory_retrieval.py` and `event_retrieval.py`.

### MEMORY fixture

The deterministic MEMORY fixture contains four positive lexical candidates. Under the component budgets it verifies:

- diagnostic selection equals the ordinary selector result;
- four positive candidates are observed;
- two complete chunks are admitted;
- one oversized positive chunk is skipped by the character budget;
- one later positive candidate remains unadmitted after the chunk-count limit is full;
- character-budget and chunk-count pressure remain distinct.

### Event fixture

The deterministic Event fixture contains eight observed Events: one explicitly excluded message, one non-message Event, one blank message, one irrelevant eligible message, and four positive lexical candidates. Under the component budgets it verifies:

- diagnostic selection equals the ordinary selector result;
- explicit exclusion and non-message/blank ineligibility are counted separately;
- four positive candidates are observed and two Events are admitted;
- one oversized positive Event is skipped by the character budget;
- one later positive candidate remains unadmitted after the Event-count limit is full;
- character-budget and Event-count pressure remain distinct.

### Zero-budget and semantic non-leakage

The component also verifies that:

- zero-budget MEMORY retrieval reports no parsed chunks, positive candidates, admissions, skips, or inferred pressure;
- zero-budget Event retrieval does not consume the supplied iterable and reports no unseen population, exclusions, eligibility, candidates, admissions, skips, or inferred pressure;
- serialized selector diagnostics do not contain seeded Event IDs/content, MEMORY content/locations, or query semantic payload.

## Metrics and claims

The returned metrics are bounded raw counts from the deterministic fixture. The component defines no weighted composite score.

This is a selector-contract evaluation only. It does not evaluate actual-model response quality, choose runtime/default budgets, alter retrieval semantics, or establish any new runtime authority.

## Registration status

This component is **not registered in the native evaluation scenario registry by this transaction**. `src/relaylm/evaluation.py`, shared scenario counts/lists, `docs/authority-map.yaml`, and Issue current-status summaries are intentionally unchanged.

Registration and shared aggregate reconciliation are deferred to a serial integration transaction after the isolated component is merged.
