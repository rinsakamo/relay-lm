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
  "input": {
    "event_id": "019c...",
    "actor": "user",
    "content": "..."
  }
}
```

- `identity` is authoritative stable character identity.
- `state` contains selected accepted Canonical State.
- `context` contains RelayLM-prepared Event-backed cognitive material, not authority-equivalent raw transcript replay.
- `memory` contains selected crystallized synthesis. It is a distinct optional layer and is not Canonical State or Event provenance.
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
if explicit MEMORY budget exists:
  read MEMORY.md → bounded retrieval
        ↓
compile CognitiveInput
  └─ filter explicit State-shadowed MEMORY before projection
        ↓
exactly one provider generation
        ↓
accept complete valid CognitiveOutput
        ↓
persist Assistant Event from response
        ↓
validate StateCandidate[]
        ↓
persist Canonical State only if validation changed it
```

Persisting the User Event before retrieval/provider execution is intentional: the Event Journal records that the user input occurred even if optional retrieval or cognition later fails.

Buffered and streamed delivery share this semantic ordering and the same optional-memory preparation path. A streaming adapter may expose safely decoded response characters while the single provider generation is still producing its structured wire object, but this early display is not a semantic `CognitiveOutput` acceptance point. Assistant Event creation and StateCandidate validation wait for the complete valid cognitive result.

## CognitiveOutput

```json
{
  "response": "...",
  "state_candidates": []
}
```

`response` is user-visible natural language. `state_candidates` are non-authoritative proposals.

The return path is deliberately symmetric with the input path:

```text
CognitiveOutput
  ├─ response
  │    ↓
  │  Assistant Event
  │    ↓
  │  possible future Working Context
  │
  └─ StateCandidate[]
       ↓
     Validator
       ↓
     Canonical State
```

An assistant response therefore remains useful for future conversational continuity without becoming self-certified factual authority.

Streaming does not create a second semantic output form. Provider wire `utterance` deltas are delivery fragments only; the final complete structured provider result is normalized into the same `CognitiveOutput(response, state_candidates)` used by buffered turns.

## Failure semantics

If optional MEMORY retrieval fails after the Current User Event is persisted but before provider generation:

```text
Current User Event    persisted
Provider generation   not called
Assistant Event       not created
Canonical State       unchanged by that failed turn
```

If the cognitive provider fails before producing a valid `CognitiveOutput`:

```text
Current User Event    persisted
Assistant Event       not created
Canonical State       unchanged by that failed turn
```

The persisted unmatched User Event may later participate in bounded Working Context, because it is real user-origin conversational evidence even though retrieval or the attempted assistant response failed.

For a streamed turn, the same provider-failure rule applies even if a safe prefix of the provider `utterance` was already delivered to the client. A truncated or malformed structured stream does not retroactively turn that visible prefix into an accepted Assistant Event, does not make incomplete candidates authoritative, and does not trigger semantic regeneration. Successful Assistant/State persistence occurs only after complete structured provider output.

If a valid response is produced but one or more StateCandidates are rejected, the valid response still becomes an Assistant Event while rejected candidates do not mutate Canonical State. Response validity and State acceptance are deliberately separate channels.

Adapter-level malformed provider output is fail-closed before a semantic `CognitiveOutput` is accepted.

An ordinary turn targets exactly one cognitive generation. Working Context selection, deterministic State-shadow filtering, deterministic validation, persistence, Context compilation, optional retrieved-memory selection/projection, and streamed delivery do not add a second ordinary cognitive LLM call.
