# Event Retrieval Diagnostics

`select_event_evidence_with_diagnostics(...)` is the explicit retrieval-stage diagnostics surface for the current bounded Event-evidence selector.

The ordinary `select_event_evidence(...)` API preserves its existing return type and selection behavior. Both public entry points delegate to the same private selection owner, so diagnostics do not create a second retrieval implementation, Event authority, or ranking owner.

## Current observations

The diagnostics object contains only aggregate mechanics from the retrieval attempt:

- `mode`;
- observed input Event count;
- explicit Event-ID exclusion count;
- non-message Event count;
- blank/non-string message-content count;
- eligible message count;
- positive lexical candidate count;
- selected count;
- explicit Event-count limit;
- explicit character limit and used characters;
- positive candidates skipped because the remaining character budget could not fit the complete Event content;
- positive candidates left unadmitted after the Event-count limit was already full;
- separate Event-count and character-budget pressure booleans.

No Event ID, actor/content payload, timestamp, query term, lexical score, State value, or MEMORY content/location is emitted.

## Reason attribution

Reason attribution follows the existing selector order without changing selection semantics:

1. explicit Event-ID exclusions are applied first;
2. non-message Events and messages without non-empty string content are ineligible;
3. only positive exact lexical overlap enters the ranked candidate set;
4. relevance rank and newer source-order tie break remain unchanged;
5. while an Event slot remains, a positive candidate that cannot fit whole in the remaining character budget is counted as a character-budget skip and selection continues;
6. after the Event-count limit is full, later positive candidates are counted as unadmitted by that limit;
7. selected Events are still restored to source chronology before return.

A zero Event or character budget returns before consuming the Event iterable. Diagnostics therefore report zero observed Events, exclusions, candidates, and pressure rather than inventing facts about an iterable that was never inspected. A query without usable lexical terms likewise returns before Event iteration, matching the existing selector boundary.

These counters describe retrieval mechanics only. They do not establish Event truth beyond the existing persisted Event authority, semantic authority, confidence, relevance quality, telemetry requirements, or a default runtime budget.

## Deferred

Integrated ordinary-turn retrieval diagnostics, total cross-layer/token-aware cost, runtime default budgets, retrieval-scaled persistent/segmented discovery, semantic/vector retrieval, temporal interpretation, redundancy suppression, and stronger conflict authority remain separate #1267 work.

The wider Context Compiler authority remains `docs/architecture/context-compiler.md`; that compiler still does not infer upstream Event retrieval pressure when it receives already-selected Event evidence.