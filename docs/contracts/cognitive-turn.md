# Cognitive Turn Contract

## CognitiveInput

Minimal semantic shape:

```json
{
  "identity": {"content": "..."},
  "state_classes": {
    "user.preference": "the user's likes, dislikes, and preferences",
    "relationship.state": "current qualities of the relationship"
  },
  "state": [],
  "context": [
    {
      "content": "...",
      "sources": ["event-id"],
      "actor": "user"
    }
  ],
  "memory": [
    {
      "content": "## Coffee\n\n...",
      "location": "memory/MEMORY.md#memory/coffee"
    }
  ],
  "event_evidence": [
    {
      "event_id": "019b...",
      "type": "message",
      "actor": "user",
      "timestamp": "2026-08-17T00:00:00+00:00",
      "content": "..."
    }
  ],
  "input": {
    "event_id": "019c...",
    "actor": "user",
    "content": "..."
  }
}
```

- `identity` is authoritative stable character identity.
- `state` contains selected accepted Canonical State.
- `context` contains RelayLM-prepared cognitive material. Current compiler-owned material may include already-accepted Continuity Context followed by bounded Event-backed Working Context; inclusion never upgrades source authority.
- `memory` contains selected crystallized synthesis. It is a distinct optional layer and is not Canonical State or Event provenance.
- `event_evidence` contains selected persisted Event occurrences with real Event provenance. Occurrence evidence is not automatically current State.
- `input` is the current governed Event.
- `state_classes` provides bounded semantic definitions and may be rendered through provider/schema metadata without changing semantics.

## ContextItem provenance

A Context item carries:

```text
content
sources[]
actor? = user | assistant | other future source role
```

For current Working Context, `sources` identifies the RelayLM-owned source Event and `actor` preserves who authored that Event.

The actor/source metadata is semantically important:

- user-authored Context can support what the user actually said, subject to temporal and semantic scope;
- assistant-authored Context may support dialogue continuity, reference resolution, and unfinished conversational structure;
- assistant-authored Context does not independently establish user facts, preferences, goals, experiences, or external truth;
- inclusion in Context never upgrades the authority of the underlying source.

Context compilation is read/select/project only. `ContextItem` is not a memory mutation or State acceptance mechanism.

## Accepted Continuity Context

`ContinuityRuntime` is an explicit process-local orchestration holder over an accepted immutable `ContinuityContext`. When a runtime is configured for an ordinary turn, Turn snapshots its current pre-generation context and supplies that accepted context to `compile_cognitive_input(...)`.

Turn does not inspect Continuity kinds or reproduce Context Compiler retention semantics. The compiler owns whether and how already-accepted Continuity enters `CognitiveInput.context`; current compiler authority includes accepted `referent`, `unresolved`, and `active_task` projection while preserving their accepted Event sources and epistemic role.

The snapshot supplied to cognition is the pre-turn accepted context. The runtime revision is advanced only after the single provider generation completes and deterministic Continuity validation runs at the common commit boundary. Streaming deltas do not mutate accepted Continuity while generation is in progress.

No runtime means no accepted Continuity Context is supplied to compilation. Runtime capacity and lifetime remain explicit caller-provided policy, and Continuity Context remains non-durable.

## Retrieved crystallized memory

A retrieved memory item carries:

```text
content
location
```

`content` is selected readable crystallized synthesis. `location` is only the deterministic location of that selection in the current Markdown document, such as `memory/MEMORY.md#memory/coffee`.

The current contract deliberately keeps this separate from Event-backed `ContextItem.sources`:

- a memory `location` is **not** an Event ID;
- a memory `location` is **not** a StateCandidate source;
- a memory `location` is **not yet** durable logical-memory identity across Markdown reorganization;
- retrieved crystallized prose is lower authority than active Canonical State for current understanding;
- including memory in CognitiveInput does not mutate `MEMORY.md`, State, or Events.

`compile_cognitive_input(..., retrieved_memory=...)` accepts already-selected `MemoryChunk` values without widening retrieval scope. Before projection, it applies a conservative deterministic State-shadow filter using the full eligible active Canonical State set, independently of any later State projection cap.

The current State-shadow contract is intentionally explicit rather than semantic:

- a retrieved chunk is State-addressing only when its heading path contains every normalized lexical term of a State key;
- if the corresponding active State value has comparable lexical text and at least one current value appears as an exact lexical token sequence in the chunk, the chunk is retained;
- if the heading addresses the key but none of the comparable current values appears, the whole chunk is excluded from `CognitiveInput.memory`;
- exact lexical tokens prevent substring equivalence such as treating `likes` as present inside `dislikes`;
- inactive or expired State does not suppress memory;
- headings that do not identify a State key remain untouched rather than being reclassified from arbitrary prose.

This filter affects cognitive residency only. It does not rewrite `MEMORY.md`, mutate State or Events, or create another truth owner. Arbitrary natural-language contradiction inference, historical/current interpretation under ambiguous headings, degree-level conflicts, and non-lexically-comparable values remain deferred.

The ordinary turn APIs accept an optional `MemoryRetrievalBudget(max_chunks, max_chars)`:

- with no budget, the runtime does not read `MEMORY.md` and the memory layer remains empty;
- with a budget, the Current User Event text is used as the query for the existing bounded `select_memory_chunks` primitive;
- buffered and streamed turns use the same retrieval/compilation path;
- retrieved chunks pass through the State-shadow filter before entering the memory layer;
- no default MEMORY budget is chosen by this contract;
- the OpenAI client boundary does not yet expose this budget as a request parameter.

The provider remains instructed to treat active State as current understanding. That instruction is defense in depth for cases beyond the current narrow deterministic filter, not a substitute for RelayLM authority.

## Targeted Event evidence

An Event evidence item carries:

```text
event_id
event_type
actor
timestamp
content
```

`compile_cognitive_input(..., event_evidence=...)` accepts already-selected persisted Events and projects them into the dedicated `event_evidence` layer without widening retrieval scope.

The current projection contract is:

- the real persisted Event ID is preserved and may be cited as StateCandidate provenance;
- Event type, actor, timestamp, and content are preserved so occurrence role and chronology remain visible to cognition;
- supplied order is preserved;
- the Current Event is excluded if accidentally supplied because it is already carried separately as protected `input`;
- a selected Event without non-empty string `payload.content` fails explicitly rather than being silently rewritten or dropped;
- projection does not mutate Events, State, MEMORY, or indexes and does not add an LLM call.

Event evidence has different semantics from both Working Context and MEMORY:

```text
Working Context   recent conversational continuity backed by Event sources
MEMORY            crystallized synthesis, document locator only
Event Evidence    targeted persisted occurrence with real Event ID
```

Authority remains source-role-aware. A user-authored Event proves what the user said at that occurrence, subject to temporal and semantic scope. An assistant-authored Event remains assistant-authored and cannot self-certify user facts or external truth. An Event occurrence is not automatically accepted current Canonical State merely because it was retrieved.

The OpenAI-compatible provider serializes Event evidence separately and permits its real Event IDs as StateCandidate `sources`. MEMORY `location` values remain ineligible as sources.

The ordinary turn APIs now also accept an optional `EventRetrievalBudget(max_events, max_chars)`:

- `event_budget=None` preserves the previous behavior and supplies no targeted Event evidence;
- with an explicit budget, the Current User Event text is the retrieval query and the Current User Event ID is excluded from evidence;
- buffered and streamed turns use the same retrieval/compilation helper;
- ordinary-turn Working Context reads `CharacterDirectory.iter_events()` while targeted retrieval consumes `CharacterDirectory.event_retrieval_source()`; both are tied to the same validated process-local Event Journal snapshot, so the turn layer does not create an independent Event authority or reparse the unchanged journal solely for targeted retrieval;
- selected Events enter only the dedicated `event_evidence` layer through the existing projection owner;
- zero Event budgets are allowed and select no evidence; negative budgets fail explicitly;
- no default Event budget is chosen and the OpenAI client boundary does not expose Event-budget controls in this slice.

`CharacterDirectory` owns validation, snapshot-cache, and discovery-index lifecycle. `event_retrieval_source()` exposes the derived `EventDiscoveryIndex` for targeted discovery, while `iter_events()` exposes source chronology for Working Context. The turn layer consumes those APIs without inspecting postings or redefining retrieval semantics; initial/reopen/external-mutation validation and rebuild remain storage/retrieval-owner work.

## Working Context

The current runtime may include bounded RelayLM-owned recent dialogue in `context`.

This Working Context is intentionally different from durable memory:

```text
Event / State / MEMORY
    durable semantic sources

Working Context
    temporary cognitive residency for conversational continuity
```

Material can leave Working Context under budget pressure while remaining durably available in its source layer. Later retrieval may re-admit it.

The current implementation preserves normal prior `user → assistant` exchanges atomically so budget pressure cannot retain an assistant assertion while dropping the user Event that gave the exchange its conversational basis.

## Ordinary turn ordering

The current ordinary-turn runtime uses this semantic order:

```text
load config / Identity / Canonical State
        ↓
persist Current User Event
        ↓
if explicit ContinuityRuntime exists:
  snapshot its current accepted ContinuityContext
        ↓
if explicit MEMORY budget exists:
  read MEMORY.md → bounded retrieval
        ↓
obtain validated Event chronology for Working Context
        ↓
if explicit Event budget exists:
  obtain the derived Event retrieval source tied to that validated snapshot
  → bounded Event retrieval excluding Current User Event
        ↓
compile CognitiveInput
  ├─ consume the accepted pre-turn ContinuityContext through compiler-owned projection
  ├─ filter explicit State-shadowed MEMORY before projection
  └─ project selected targeted Events into Event Evidence
        ↓
exactly one provider generation
        ↓
accept complete valid CognitiveOutput
        ↓
reject non-empty ContinuityCandidate[] if no explicit runtime exists
        ↓
persist Assistant Event from response
        ↓
validate StateCandidate[]
        ↓
if ContinuityRuntime exists:
  validate/apply ContinuityCandidate[] exactly once
        ↓
persist Canonical State only if validation changed it
        ↓
replace ContinuityRuntime.context with the validated immutable result
```

Persisting the User Event before retrieval/provider execution is intentional: the Event Journal records that the user input occurred even if optional retrieval or cognition later fails.

Buffered and streamed delivery share this semantic ordering and the same optional-memory/Event/Continuity preparation owner. A streaming adapter may expose safely decoded response characters while the single provider generation is still producing its structured wire object, but this early display is not a semantic `CognitiveOutput` acceptance point. Assistant Event creation, StateCandidate validation, and Continuity validation wait for the complete valid cognitive result.

The same occurrence may currently qualify for recent Working Context and targeted Event evidence when both selectors admit it. Cross-layer redundancy suppression is intentionally deferred rather than silently changing either selector's semantics.

## CognitiveOutput

```json
{
  "response": "...",
  "state_candidates": [],
  "continuity_candidates": []
}
```

`response` is user-visible natural language. `state_candidates` are non-authoritative proposals. `continuity_candidates` are proposals for bounded non-durable Continuity and require deterministic Continuity validation before becoming accepted temporary authority.

The return path is deliberately symmetric with the input path:

```text
CognitiveOutput
  ├─ response
  │    ↓
  │  Assistant Event
  │    ↓
  │  possible future Working Context
  │
  ├─ StateCandidate[]
  │    ↓
  │  Validator
  │    ↓
  │  Canonical State
  │
  └─ ContinuityCandidate[]
       ↓
     deterministic Continuity validation
       ↓
     process-local Continuity Context
       ↓
     later-turn Context Compiler consumption
```

An assistant response therefore remains useful for future conversational continuity without becoming self-certified factual authority. A Continuity proposal likewise does not become accepted temporary authority merely because the model emitted it.

Streaming does not create a second semantic output form. Provider wire `utterance` deltas are delivery fragments only; the final complete structured provider result is normalized into the same `CognitiveOutput(response, state_candidates, continuity_candidates)` used by buffered turns.

## Failure semantics

If optional MEMORY retrieval fails after the Current User Event is persisted but before provider generation:

```text
Current User Event    persisted
Provider generation   not called
Assistant Event       not created
Canonical State       unchanged by that failed turn
Continuity Context    unchanged by that failed turn
```

If the cognitive provider fails before producing a valid `CognitiveOutput`:

```text
Current User Event    persisted
Assistant Event       not created
Canonical State       unchanged by that failed turn
Continuity Context    unchanged by that failed turn
```

The persisted unmatched User Event may later participate in bounded Working Context, because it is real user-origin conversational evidence even though retrieval or the attempted assistant response failed.

For a streamed turn, the same provider-failure rule applies even if a safe prefix of the provider `utterance` was already delivered to the client. A truncated or malformed structured stream does not retroactively turn that visible prefix into an accepted Assistant Event, does not make incomplete candidates authoritative, and does not trigger semantic regeneration. Successful Assistant/State/Continuity commit occurs only after complete structured provider output.

If a valid response is produced but one or more StateCandidates are rejected, the valid response still becomes an Assistant Event while rejected candidates do not mutate Canonical State. StateCandidate acceptance and ContinuityCandidate acceptance remain separate deterministic channels.

If a completed output contains non-empty ContinuityCandidates without an explicit Continuity runtime, the turn fails before Assistant Event, State, or Continuity commit instead of silently dropping those proposals.

Adapter-level malformed provider output is fail-closed before a semantic `CognitiveOutput` is accepted.

An ordinary turn targets exactly one cognitive generation. Working Context selection, accepted Continuity projection, deterministic State-shadow filtering, deterministic State/Continuity validation, persistence, Context compilation, optional retrieved-memory selection/projection, optional targeted Event retrieval/projection, and streamed delivery do not add a second ordinary cognitive LLM call.
