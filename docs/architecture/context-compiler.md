# Context Compiler

The Context Compiler constructs the smallest sufficient cognitive context for the current turn **as the character**.

## Inputs

- Identity Core;
- relevant Canonical State;
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
  Working Context     recent conversational continuity
  Retrieved Memory    optional long-term semantic context
  Event Evidence      targeted grounding / chronology
```

> **Persistence decides what RelayLM knows. Context selection decides what RelayLM thinks about now.**

## Authority and continuity rules

- Raw client transcript replay is not a trusted context mechanism.
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

### Content-free State selection diagnostics

Callers that explicitly need selection evidence may use `compile_cognitive_input_with_diagnostics`. It returns the same `CognitiveInput` produced by the ordinary compiler plus a diagnostics tuple. The ordinary `compile_cognitive_input` path does not generate or persist diagnostics.

The current diagnostics surface covers only the `canonical_state` layer and exposes aggregate, content-free fields:

- selection mode: `unbounded`, `within_budget`, `zero_budget`, or `lexical_ranked`;
- eligible / selected / evicted record counts;
- budget unit (`records`), explicit limit, used count, and whether budget pressure occurred;
- selected lexical-match count and selected deterministic-fallback count when lexical ranking is active;
- evicted-by-budget-limit count.

Diagnostics deliberately exclude State IDs, keys, values, source Event IDs, Current Event content/ID, and any other semantic payload. They are observations about selection mechanics, not a new truth source, persistence layer, ranking authority, or telemetry requirement.

This first diagnostics slice is record-count based because the current explicit State cap is record-count based. Cross-layer token cost, Working Context diagnostics, retrieved-memory/Event diagnostics, and total-budget degradation/fallback reporting remain later #1267 work.

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

`compile_cognitive_input(..., retrieved_memory=...)` accepts already-selected `MemoryChunk` values and projects them into a dedicated `CognitiveInput.memory` layer. Each projected item contains only:

```text
content
location
```

This separation is intentional:

```text
Working Context sources[]   RelayLM Event provenance
Retrieved Memory location   current Markdown document locator
```

A memory `location` is **not** an Event ID, is **not** eligible as StateCandidate provenance, and is **not yet** durable logical-memory identity across Markdown reorganization. #1260 still owns richer Markdown provenance conventions and stable logical memory identity.

The compiler consumes the supplied `retrieved_memory` exactly as already-selected evidence; it does not silently run broader retrieval or change its scope. Projection is read/select/project only and does not mutate `MEMORY.md`, State, Events, or indexes and does not call an LLM.

The OpenAI-compatible provider serializes this layer separately from `context` and instructs the model that crystallized memory is lower authority than active State. That instruction remains a defense-in-depth rule; RelayLM now also owns a conservative deterministic State-shadow filter before projection.

### Deterministic State-shadow filtering

Before retrieved chunks become `CognitiveInput.memory`, the Context Compiler compares only an explicitly State-addressing subset against the full eligible active Canonical State set.

Current filtering is intentionally narrow:

- authority eligibility uses every State record with `status == "active"` and `valid_to is None`, independently of any later `max_state_records` projection cap;
- a Memory chunk is State-addressing only when its heading path contains every normalized lexical term of a State key;
- when that State value has lexically comparable text, the chunk is retained if at least one current State value appears as an exact lexical token sequence in the chunk;
- if the heading addresses the key but none of the comparable current State values appears, the whole chunk is suppressed from `CognitiveInput.memory`;
- exact token sequences are used rather than substring matching, so for example `likes` is not treated as present inside `dislikes`;
- inactive or expired State records do not suppress memory;
- a chunk whose heading does not explicitly identify a State key is left untouched, even if its prose happens to mention an older or different value.

Whole-chunk suppression changes only current cognitive residency. It does not rewrite or delete `MEMORY.md`, mutate State or Events, create a second semantic owner, or add an LLM call.

This first filter deliberately does **not** infer arbitrary natural-language contradiction, distinguish historical from current prose when the heading is ambiguous, compare semantic degree envelopes, or decide conflicts for non-lexically-comparable State values. Those remain later #1267 work.

### Opt-in ordinary-turn retrieval

`run_user_turn` and `run_user_turn_streaming` now accept `memory_budget: MemoryRetrievalBudget | None`.

Current behavior is intentionally opt-in:

- `memory_budget=None` preserves the previous behavior and does not read `MEMORY.md` at all;
- a supplied `MemoryRetrievalBudget(max_chunks, max_chars)` uses the Current User Event text as the retrieval query and delegates selection to `select_memory_chunks`;
- buffered and streaming turns share the same retrieval/compilation helper and therefore the same selection semantics;
- selected chunks pass through the deterministic State-shadow filter and then enter only the dedicated `CognitiveInput.memory` layer;
- a zero budget is allowed and selects no memory; negative budget values fail explicitly;
- no default runtime MEMORY budget is implied by the existence of this opt-in path;
- the public OpenAI client boundary does not yet expose a MEMORY-budget control in this slice.

The Current User Event is persisted before optional retrieval, matching the existing ordinary-turn occurrence semantics. If reading `MEMORY.md` fails after that point, the turn fails closed before provider generation: the User Event remains recorded, no Assistant Event is created, and Canonical State is unchanged by the failed turn.

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

`compile_cognitive_input(..., event_evidence=...)` now accepts already-selected persisted Events and projects them into a distinct `CognitiveInput.event_evidence` layer. Each item preserves:

```text
event_id
event_type
actor
timestamp
content
```

Projection preserves supplied order and excludes the Current Event by ID because Current Input is already carried separately. A selected Event without non-empty string `payload.content` fails explicitly rather than being silently dropped or rewritten.

The layer remains distinct by authority and purpose:

```text
Working Context   recent dialogue continuity with Event sources
Retrieved Memory  crystallized synthesis with document location
Event Evidence    targeted persisted occurrence with real Event ID
Current Input     protected current governed Event
```

The OpenAI-compatible provider serializes Event Evidence separately. Real Event-evidence IDs may be used as StateCandidate provenance; MEMORY locations remain ineligible. User/assistant actor role and occurrence time remain visible, and retrieved occurrence evidence is not automatically current Canonical State.

Retrieval and projection remain read/select/project only and add no LLM call. The ordinary turn does **not yet** retrieve or supply Event evidence automatically. The file-backed `CharacterDirectory.iter_events()` path also still scans `events.jsonl`; runtime budget plumbing and retrieval-scaled journal reads/indexing remain separate work. Semantic/vector retrieval, temporal interpretation, conflict authority beyond current source roles, and cross-layer diagnostics are likewise deferred.

## Budget model

Context budgeting is role-aware rather than one flat relevance competition.

Conceptually:

```text
protected tier   Identity + Current Event
current tier     relevant active Canonical State
working tier     bounded recent conversational continuity
retrieved tier   MEMORY chunks + targeted Events
reserve tier     prompt / schema / provider overhead
```

Budgets should use floors/caps/residual allocation rather than fixed percentages that must always be consumed. Correct but irrelevant memory should remain out of Context; token availability alone is not a reason to inject it.

## Deferred selection work

#1267 remains the authority for later Context selection and retrieval work, including:

- evidence-backed runtime default State/MEMORY/Event budgeting and stronger semantic/multilingual relevance beyond the current explicit lexical primitives;
- `unresolved`, `referent`, and `active_task` retention beyond pure recency;
- semantic State-vs-memory conflict detection beyond explicit State-key headings, including historical/current interpretation, degree-level conflicts, and non-lexical values;
- durable logical memory identity/provenance and temporal-scope consumption as #1260 conventions become available;
- ordinary-turn targeted Event retrieval wiring and retrieval-scaled Event Journal reads/indexing;
- redundancy reduction across State / Working Context / Memory / Events;
- total token-aware tier budgeting and cross-layer diagnostics;
- embedding/index acceleration only after authority eligibility is preserved.

The governing principle is:

> **Retrieve by relevance, assemble by authority.**
