# Context Compiler

The Context Compiler constructs the smallest sufficient cognitive context for the current turn **as the character**.

## Inputs

- Identity Core;
- relevant Canonical State;
- already-accepted Continuity Context when supplied;
- RelayLM-owned recent message Events used as Working Context;
- retrieved crystallized memory and targeted Event evidence when those layers are enabled;
- the current governed Event;
- minimum protocol/tool state;
- applicable audience/privacy/capability narrowing.

## Output

A bounded `CognitiveInput` object.

The durable memory model and the per-turn cognitive working set are intentionally different:

```text
Durable semantic layer
  Event Journal       what occurred / provenance
  Canonical State     accepted current understanding
  MEMORY.md / notes   crystallized long-term semantic synthesis

          ↓ selection / compilation

Per-turn cognitive layer
  Identity            protected
  Current Event       protected
  Relevant State      current accepted understanding
  Accepted Continuity accepted temporary referent/unresolved/active-task continuity
  Working Context     recent conversational continuity
  Retrieved Memory    optional long-term semantic context
  Event Evidence      targeted grounding / chronology
```

> **Persistence decides what RelayLM knows. Context selection decides what RelayLM thinks about now.**

## Authority and continuity rules

- Raw client transcript replay is not a trusted context mechanism.
- Accepted Continuity Context is temporary, non-durable continuity authority owned upstream; Context compilation may consume it but never accepts candidates, advances its lifecycle, or infers missing continuity semantics from raw language.
- Projected Continuity preserves its accepted Event sources and epistemic role without pretending that the compiler-generated projection itself was authored by the user or assistant.
- Working Context is built only from RelayLM-owned persisted Events.
- Working Context may contain both user-authored and assistant-authored dialogue and must preserve actor/source provenance.
- Assistant-authored Working Context supports conversational continuity, reference resolution, and unfinished dialogue. It does **not** prove user facts, preferences, goals, experiences, or external events merely because the assistant said them before.
- User-authored Working Context is evidence of what the user said, with the temporal and semantic limits of that utterance; prompt residence does not make it timeless external truth.
- Relevant accepted State may influence the response without being recited.
- Current-state conflicts are resolved by authority/source role before relevance ranking. A stale memory or assistant assertion cannot override active Canonical State for a current-state claim.
- Event Journal remains occurrence/provenance authority for what happened even when current State has changed.
- Retrieval and Context compilation are read/select/project operations. They never mutate Canonical State or durable memory.

> **Continuity relevance does not imply factual authority.**

## Context residency lifecycle

Context residency is distinct from semantic memory lifecycle.

```text
Semantic lifecycle
  Event → State → Crystallization → MEMORY

Context residency lifecycle
  admit → retain → downrank → evict → retrieve again
```

Eviction from Working Context means only that the material is no longer in the current cognitive working set. It does not delete the source Event, Canonical State, or crystallized memory. Older material may later re-enter Context through retrieval.

This distinction prevents token-budget pressure from becoming accidental forgetting.

## Current Working Context implementation

The first bounded Working Context slice was implemented by #1278.

Current defaults:

```text
max message Events: 6
max content chars: 4000
```

The cap applies to Working Context only. Identity, active Canonical State, and the Current Event are not evicted by this cap.

Additional rules:

- the Current Event is excluded from Working Context because it is already carried separately as `input`;
- only RelayLM-persisted user/assistant message Events are eligible;
- selected prior material is returned in chronological order;
- a normal prior `user → assistant` exchange is admitted atomically so budget pressure does not leave an orphan assistant assertion in Context;
- an unmatched user Event may be admitted by itself;
- an unmatched assistant Event is not admitted by itself;
- zero Working Context budget leaves Identity, State, and Current Event intact.

These are deterministic residency rules, not semantic truth rules.

## Current accepted Continuity projection

`compile_cognitive_input(..., continuity_context=...)` accepts an already-validated `ContinuityContext` as an optional input. This is a consumer boundary only: candidate acceptance, replacement/resolution, revision advancement, expiry, and capacity eviction remain owned by the Continuity lifecycle authority.

The current bounded projection covers all three accepted initial Continuity kinds: `referent`, `unresolved`, and `active_task`.

- accepted item order is preserved across all projected kinds;
- accepted `referent`, `unresolved`, and `active_task` items are projected before recent Event-derived Working Context;
- each item becomes a `ContextItem` whose `sources` are the accepted source Event IDs;
- `content` is a compact deterministic JSON object carrying `kind`, `key`, semantic `value`, and `epistemic_role` under a `continuity` field;
- the projection leaves `ContextItem.actor` unset because accepted Continuity is a compiler-generated typed projection, not replayed user- or assistant-authored dialogue;
- immutable Mapping/tuple semantic values are converted only to their JSON projection shape; accepted Continuity itself is not mutated;
- the Working Context Event-count and character budgets do not evict accepted Continuity items, so zero recent-message budget does not erase already-accepted referent, unresolved, or active-task continuity;
- `continuity_context=None`, or an accepted context containing no projected items, preserves the previous cognitive projection.

The compiler does not resolve references from raw language, synthesize unresolved questions, infer active tasks from dialogue, accept Continuity candidates, create a second Continuity lifecycle owner, or infer semantic redundancy with recent dialogue or Event Evidence.

The ordinary-turn runtime now owns process-local Continuity acceptance/lifecycle orchestration, but the current runtime compilation call does not yet supply its `ContinuityRuntime.context` to this compiler input. That cross-lane orchestration wiring remains outside the Context Compiler semantic owner and must consume this capability only after it exists on `v1`.

## Current active-State selection primitive

`compile_cognitive_input` supports an optional explicit `max_state_records` cap for large active-State sets.

Eligibility is applied before ranking: only records with `status == "active"` and no `valid_to` are candidates. The selector never changes State records or provenance.

Current behavior is deliberately conservative:

- `max_state_records=None` preserves the previous behavior and projects every eligible active State record;
- if the eligible set already fits the explicit cap, order and contents are unchanged;
- only under explicit cap pressure, deterministic lexical relevance against the Current Event is used;
- specific State-key matches receive the strongest lexical weight, followed by matching semantic value text and then State-class text;
- positive lexical matches are ranked before zero-match fallback records;
- ties and fallback are deterministic by existing State order;
- after selection, records are projected in their original Canonical State order rather than score order;
- `max_state_records=0` removes only the State projection; Identity, Current Event, and Working Context remain independent;
- negative caps fail explicitly.

The current lexical selector is candidate selection, not authority. It does not mutate State, call an LLM, resolve contradictions, or infer truth from similarity.

The ordinary runtime does **not** yet impose a default State cap, so existing turns continue to receive all eligible active State unless a caller explicitly requests bounded State selection. Runtime budget policy and stronger semantic/multilingual discovery remain #1267 work.

### Content-free selection diagnostics

Callers that explicitly need selection evidence may use `compile_cognitive_input_with_diagnostics`. It returns the same `CognitiveInput` produced by the ordinary compiler plus a diagnostics tuple. The ordinary `compile_cognitive_input` path does not generate or persist diagnostics.

The diagnostics surface currently covers four compiler-owned layers:

- `canonical_state` — active-State eligibility, selection mode, selected/evicted counts, explicit record budget, lexical-match/fallback counts, and budget-limit eviction count;
- `working_context` — eligible prior message count after Current Event exclusion, selected count, explicit Event-window and character budgets, selected character usage, Current Event exclusion count, Event-window eviction count, unmatched-assistant drop count, and character-budget eviction count;
- `retrieved_memory` — number of already-retrieved MEMORY chunks supplied to the compiler, number projected after the active-State authority filter, and deterministic State-shadow suppression count;
- `event_evidence` — number of already-selected Event candidates supplied to the compiler, number projected after Current Event and exact Working Context Event-ID de-duplication, Current Event exclusion count, and the count of supplied non-current Event IDs that were already resident in selected Working Context.

Accepted Continuity projection does not add a fifth diagnostics authority in this slice. `working_context` diagnostics continue to describe only recent Event-derived Working Context, and Event-Evidence exact-ID overlap diagnostics continue to compare against that selected Working Context rather than treating Continuity source provenance as duplicate dialogue residency.

Shared diagnostic fields include layer/mode, aggregate eligible/selected/evicted counts, budget unit/limit/used/pressure, plus bounded reason counters. Working Context additionally reports `character_budget_limit`, `character_budget_used`, `evicted_event_window_count`, `evicted_character_budget_count`, and `evicted_orphan_assistant_count`. Cross-layer additions remain `authority_suppressed_count`, `current_event_excluded_count`, and `redundancy_overlap_count`.

Working Context reason attribution follows the existing selector order without changing it: the Event window is applied first, unmatched assistant Events inside that window are not independently admitted, then complete exchanges are admitted newest-first under the character budget. A zero Event budget is therefore observed as Event-window eviction; with a nonzero Event budget and zero character budget, the remaining eligible window is observed as character-budget eviction. These counters describe residency mechanics only.

Diagnostics deliberately exclude State IDs, keys, values, Event IDs, MEMORY locations/content, Current Event content/ID, and other semantic payload. The Event-overlap counter compares real Event IDs internally but emits only an aggregate count and is computed from supplied Event-evidence candidates before exact overlap residency suppression. Diagnostics are observations about selection/projection mechanics, not a new truth source, persistence layer, ranking authority, or telemetry requirement.

For MEMORY and Event Evidence, `budget_limit=None` and `budget_pressure=False` mean only that the Context Compiler itself did not own the upstream retrieval budget. The compiler does **not** infer MEMORY/Event candidate populations, retrieval-stage ranking pressure, or token costs that were never provided to it. Retrieval-stage diagnostics, total cross-layer token cost, degradation/fallback reporting, and runtime default-budget evidence remain later #1267 work.

## Current MEMORY.md retrieval and projection primitives

`select_memory_chunks` provides bounded read/select behavior over crystallized `memory/MEMORY.md` content.

Current retrieval behavior:

- parse ATX Markdown heading sections into locally complete chunks that include the section heading and direct body;
- ignore heading-looking lines inside fenced code blocks;
- retain the current heading path and expose a deterministic current-location reference such as `memory/MEMORY.md#memory/coffee`;
- disambiguate duplicate current heading locations deterministically within the document;
- use simple normalized lexical token matching, with heading matches weighted above body matches;
- select only chunks with a positive lexical match; optional crystallized memory has no zero-match fallback merely because budget remains;
- require explicit caller-supplied chunk-count and character budgets;
- never truncate a chunk to make it fit; an oversized relevant chunk is skipped and a later relevant complete chunk may still fit;
- return selected chunks in original document order after ranking/selection;
- zero budgets return no chunks and negative budgets fail explicitly.

`compile_cognitive_input(..., retrieved_memory=...)` accepts already-selected `MemoryChunk` values and projects them into a dedicated `CognitiveInput.memory` layer. The canonical `MemoryChunk` now also carries #1260/#1409-owned typed `temporal_authority`; the current `RetrievedMemoryItem` provider projection still contains only:

```text
content
location
```

This separation is intentional:

```text
Working Context sources[]      RelayLM Event provenance
MemoryChunk temporal_authority typed MEMORY temporal/provenance authority
Retrieved Memory location      current Markdown document locator
```

A memory `location` is **not** an Event ID and is **not** eligible as StateCandidate provenance. When governed MEMORY metadata is present, stable logical `memory_id`, `derivation_id`, typed Event/State source references, and `current | historical | unknown` temporal scope are carried separately on `MemoryChunk.temporal_authority`; unannotated MEMORY remains typed `unknown`.

The compiler consumes the supplied `retrieved_memory` exactly as already-selected evidence; it does not silently run broader retrieval or change its scope. Projection is read/select/project only and does not mutate `MEMORY.md`, State, Events, or indexes and does not call an LLM.

The OpenAI-compatible provider serializes this layer separately from `context` and instructs the model that crystallized memory is lower authority than active State. That instruction remains a defense-in-depth rule; RelayLM also owns a conservative deterministic State-shadow filter before projection.

### Deterministic State-shadow filtering

Before retrieved chunks become `CognitiveInput.memory`, the Context Compiler compares a bounded set of deterministic **structural State-addressing forms** against the full eligible active Canonical State set.

Current filtering is intentionally narrow:

- authority eligibility uses every State record with `status == "active"` and `valid_to is None`, independently of any later `max_state_records` projection cap;
- a Memory chunk is State-addressing when its heading path contains every normalized lexical term of a State key, or when its body contains the canonical State key as an explicit `key:` / `key=` field assignment;
- inline field detection requires the exact normalized canonical key token and a field delimiter;
- ordinary free-form prose does **not** become State-addressing or temporally classified merely because it contains `current`, `currently`, `now`, a year/date literal, `previous`, `formerly`, grammatical tense, or other temporal wording;
- therefore an unannotated non-structural sentence such as `Current residence location is Hokkaido.` remains temporally `unknown` input and is not suppressed by a lexical-current grammar;
- boolean and reserved `{semantic, degree_hint}` State values continue to use only the existing explicitly State-addressing structural rules;
- for State values handled by the structural heading/field rule, the chunk is retained if at least one current State value appears as an exact lexical token sequence in the chunk;
- if the chunk explicitly addresses the key through those heading/field forms but none of the comparable current State values appears, the whole chunk is suppressed from `CognitiveInput.memory`;
- for a boolean State value, an explicitly State-addressing chunk is suppressed only when it contains the exact opposite `true` / `false` token and does not also contain the current boolean token;
- a boolean chunk containing the current token remains compatible; a chunk containing neither boolean token, or both tokens, is left untouched rather than being semantically or temporally reclassified;
- for the reserved structured State value `{semantic, degree_hint}`, the current `semantic` must appear as an exact lexical token sequence; a matching numeric degree alone cannot make conflicting semantic text compatible;
- when the State key is identified by the chunk heading, an explicit numeric `degree_hint:` / `degree_hint=` assignment in that section must equal the active State degree or the whole chunk is suppressed;
- when State addressing exists only through an inline canonical `key:` / `key=` assignment, a degree claim is associated with that key only when `degree_hint:` / `degree_hint=` occurs on the same assignment line; degree fields on another key's line are not borrowed;
- absence of an associated explicit degree assignment is not inferred as a conflict, and arbitrary prose numbers are not interpreted as degree claims;
- exact token sequences are used rather than substring matching, so for example `likes` is not treated as present inside `dislikes`;
- inactive or expired State records do not suppress memory;
- a chunk that uses none of the accepted structural State-addressing forms is left untouched even if its prose happens to mention an older, newer, current-sounding, or different value.

Whole-chunk suppression changes only current cognitive residency. It does not rewrite or delete `MEMORY.md`, mutate State or Events, create a second semantic owner, or add an LLM call.

The former C4 line-leading lexical-current grammar from #1385 is retired after #1409 established typed MEMORY temporal authority. Context Compiler must not recreate temporal/currentness authority from prose. C5 remains a separate bounded transaction that may consume `MemoryChunk.temporal_authority` directly when deciding historical/current ambiguity; it must not derive that metadata from raw language.

### Opt-in ordinary-turn MEMORY retrieval

`run_user_turn` and `run_user_turn_streaming` accept `memory_budget: MemoryRetrievalBudget | None`.

Current behavior is intentionally opt-in:

- `memory_budget=None` preserves the previous behavior and does not read `MEMORY.md` at all;
- a supplied `MemoryRetrievalBudget(max_chunks, max_chars)` uses the Current User Event text as the retrieval query and delegates selection to `select_memory_chunks`;
- buffered and streaming turns share the same retrieval/compilation helper and therefore the same selection semantics;
- selected chunks pass through the deterministic State-shadow filter and then enter only the dedicated `CognitiveInput.memory` layer;
- a zero budget is allowed and selects no memory; negative budget values fail explicitly;
- no default runtime MEMORY budget is implied by the existence of this opt-in path;
- the public OpenAI client boundary does not expose a MEMORY-budget control.

The Current User Event is persisted before optional retrieval. If reading `MEMORY.md` fails after that point, the turn fails closed before provider generation: the User Event remains recorded, no Assistant Event is created, and Canonical State is unchanged by the failed turn.

## Current targeted Event evidence retrieval and projection primitives

`select_event_evidence(...)` provides deterministic bounded selection over caller-supplied persisted Events without replaying the whole supplied sequence into cognitive context.

Current retrieval behavior:

- input Event order is treated as Event Journal chronology;
- only `message` Events with non-empty string `payload.content` are eligible;
- explicit `exclude_event_ids` can remove the Current Event or any other occurrence from eligibility;
- query and Event content use NFKC/casefold normalized exact lexical tokens;
- only positive token overlap is eligible; there is no zero-match fallback;
- higher lexical overlap wins admission;
- equal relevance prefers the newer occurrence by source order;
- explicit `max_events` and `max_chars` bound admission;
- Events are admitted whole; an oversized relevant Event is skipped rather than truncated, and a later fitting relevant Event may still be admitted;
- selected Events are returned in original source chronology after ranking/admission;
- the original `Event` objects are returned unchanged; retrieval does not mutate Events, State, MEMORY, indexes, or call an LLM.

`compile_cognitive_input(..., event_evidence=...)` accepts already-selected persisted Events and projects them into a distinct `CognitiveInput.event_evidence` layer. Each item preserves:

```text
event_id
event_type
actor
timestamp
content
```

Projection preserves supplied order among retained evidence. It excludes the Current Event by ID because Current Input is already carried separately, and it excludes an Event whose exact ID is already resident in selected Working Context. The retained Working Context item keeps that Event ID in `sources`, so occurrence provenance is not lost. This is exact occurrence residency de-duplication only: equal or similar content with a different Event ID remains separate evidence. A selected Event without non-empty string `payload.content` fails explicitly rather than being silently dropped or rewritten.

The layer remains distinct by authority and purpose:

```text
Working Context   recent dialogue continuity with Event sources
Retrieved Memory  crystallized synthesis with document location
Event Evidence    targeted persisted occurrence with real Event ID
Current Input     protected current governed Event
```

The OpenAI-compatible provider serializes Event Evidence separately. Real Event-evidence IDs may be used as StateCandidate provenance; MEMORY locations remain ineligible. User/assistant actor role and occurrence time remain visible, and retrieved occurrence evidence is not automatically current Canonical State.

### Opt-in ordinary-turn Event retrieval

`run_user_turn` and `run_user_turn_streaming` now also accept `event_budget: EventRetrievalBudget | None`.

Current runtime behavior is deliberately opt-in:

- `event_budget=None` preserves the previous ordinary-turn behavior and supplies an empty Event-evidence layer;
- a supplied `EventRetrievalBudget(max_events, max_chars)` uses the Current User Event content as the lexical query and explicitly excludes the Current User Event ID;
- buffered and streaming paths share `_compile_turn_cognitive_input` and therefore the same retrieval/projection semantics;
- when Event retrieval is enabled, the current Event Journal sequence is materialized once before provider generation and reused by both Working Context selection and `select_event_evidence`;
- selected Events enter only `CognitiveInput.event_evidence` through the existing projection owner;
- zero budgets are valid and select no evidence; negative budgets fail explicitly;
- no default Event budget and no OpenAI/client-facing Event-budget request field are introduced.

The Current User Event is persisted before the snapshot/retrieval step. Ordinary turns still make exactly one cognitive provider generation. If the same exact Event occurrence is selected both for Working Context and targeted Event Evidence, the Context Compiler keeps the Working Context residency and suppresses only the duplicate Event Evidence projection. Working Context user→assistant exchange admission remains unchanged, and the opt-in diagnostics report the supplied exact Event-ID overlap as a content-free count. Similarity-based or semantic cross-layer deduplication remains deferred.

`CharacterDirectory` now keeps a process-local validated Event snapshot. An unchanged `events.jsonl` is not reopened and reparsed for every later `iter_events()` call in the same directory instance; a successful RelayLM-owned append incrementally extends an already-valid snapshot. File signature changes invalidate the snapshot and force authoritative JSONL revalidation, so malformed external edits are not hidden by cached Events.

This snapshot optimization does **not** make Event retrieval independent of Event count. The first read after process start/reopen or external invalidation still parses the authoritative JSONL, and the current lexical targeted selector still evaluates the supplied Event snapshot. Persistent/segmented indexing, retrieval-scaled targeted discovery beyond O(N) candidate inspection, semantic/vector retrieval, temporal interpretation, and stronger conflict authority remain deferred.

## Budget model

Context budgeting is role-aware rather than one flat relevance competition.

Conceptually:

```text
protected tier    Identity + Current Event
current tier      relevant active Canonical State
continuity tier   accepted referent/unresolved/active-task continuity, bounded upstream
working tier      bounded recent conversational continuity
retrieved tier    MEMORY chunks + targeted Events
reserve tier      prompt / schema / provider overhead
```

Budgets should use floors/caps/residual allocation rather than fixed percentages that must always be consumed. Correct but irrelevant memory should remain out of Context; token availability alone is not a reason to inject it. The accepted Continuity projection does not establish a new runtime/default token budget; it consumes an already capacity/lifecycle-bounded Continuity Context.

## Deferred selection work

#1267 remains the authority for later Context selection and retrieval work, including:

- evidence-backed runtime default State/MEMORY/Event budgeting and stronger semantic/multilingual relevance beyond the current explicit lexical primitives;
- any later Continuity-specific selection/degradation policy beyond the current projection of all accepted initial Continuity kinds;
- C5 consumption of merged #1260/#1409 typed MEMORY temporal authority for historical/current ambiguity, without year/date/`previous`/`formerly`/tense/free-form temporal inference;
- State-vs-memory authority beyond the current deterministic structural addressing forms, including omitted-key alias/synonym/negation semantics, free-form degree/intensity interpretation, free-form boolean handling, and other non-lexically-comparable values;
- richer durable logical memory identity/provenance behavior beyond the current governed `MemoryChunk.temporal_authority` carriage when #1260 work justifies it;
- persistent/segmented Event Journal indexing and retrieval-scaled targeted discovery beyond the current process-local validated snapshot reuse;
- redundancy reduction across State / Working Context / Continuity / Memory / Events beyond the current exact Working Context/Event Evidence Event-ID residency rule;
- retrieval-stage MEMORY/Event diagnostics, total token-aware tier budgeting, and explicit cross-layer degradation/fallback evidence;
- embedding/index acceleration only after authority eligibility is preserved.

The governing principle is:

> **Retrieve by relevance, assemble by authority.**
