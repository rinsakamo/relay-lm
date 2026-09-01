# Cognitive Turn Contract

Ordinary-turn execution topology is owned by `docs/contracts/cognition-execution-policy.md`. This contract owns the semantic input/output/commit boundary shared by the supported execution policies.

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

The snapshot supplied to cognition is the pre-turn accepted context.

For `single_pass`, the Continuity runtime revision advances only after the one complete provider result reaches deterministic Continuity validation at the common commit boundary. Streaming deltas do not mutate accepted Continuity while generation is in progress.

For `two_pass`, successful ordinary-turn completion is the complete accepted Pass 1 response after its Assistant Event is committed. The same accepted pre-turn snapshot still enters the originating `CognitiveInput`; after that response commit, an explicitly configured Continuity runtime advances its lifecycle exactly once and performs due expiry in conversation order. Pass 2 may apply Continuity candidates at that already-advanced revision without advancing the lifecycle a second time. A failed or stale Pass 2 applies no proposal-driven Continuity mutation, while the successful turn's already-completed lifecycle advance remains. The post-conversation Continuity lifecycle snapshot is the origin snapshot used by the Pass 2 stale guard; if Continuity advances again before that extraction commits, the extraction is stale and applies no candidates.

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
- projection does not mutate Events, State, MEMORY, or indexes and does not itself add a model generation.

Event evidence has different semantics from both Working Context and MEMORY:

```text
Working Context   recent conversational continuity backed by Event sources
MEMORY            crystallized synthesis, document locator only
Event Evidence    targeted persisted occurrence with real Event ID
```

Authority remains source-role-aware. A user-authored Event proves what the user said at that occurrence, subject to temporal and semantic scope. An assistant-authored Event remains assistant-authored and cannot self-certify user facts or external truth. An Event occurrence is not automatically accepted current Canonical State merely because it was retrieved.

The OpenAI-compatible provider serializes Event evidence separately and permits its real Event IDs as StateCandidate `sources`. MEMORY `location` values remain ineligible as sources.

The ordinary turn APIs also accept an optional `EventRetrievalBudget(max_events, max_chars)`:

- `event_budget=None` supplies no targeted Event evidence;
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

## Execution-policy ordering

Both implemented execution paths share the same preparation owner:

```text
load config / Identity / Canonical State
        ↓
persist Current User Event
        ↓
if explicit ContinuityRuntime exists:
  snapshot accepted ContinuityContext
        ↓
perform configured MEMORY / Event retrieval
and/or total Cognitive Budget enforcement
        ↓
compile one originating CognitiveInput
```

Persisting the User Event before retrieval/provider execution is intentional: the Event Journal records that the user input occurred even if optional retrieval or cognition later fails.

### `single_pass` ordering

```text
originating CognitiveInput
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

Buffered and streamed single-pass delivery share this semantic ordering. A streaming adapter may expose safely decoded response characters while the provider is still producing its structured wire object, but early display is not a semantic `CognitiveOutput` acceptance point. Assistant Event creation, StateCandidate validation, and Continuity validation wait for the complete valid result.

### `two_pass` ordering

The explicit two-pass APIs use the same prepared origin but separate the visible-response and proposal phases:

```text
reserve process-local execution revision
        ↓
prepare + bind originating User Event / CognitiveInput
        ↓
if explicit two-pass cognitive budget exists:
  count exact Pass 1 conversation serialization with resolved Pass 1 request
  apply existing deterministic #1387 degradation until fit or bounded failure
        ↓
Pass 1 conversation generation
        ↓
accept complete non-empty response
        ↓
persist Assistant Event
        ↓
if ContinuityRuntime exists:
  advance Continuity lifecycle exactly once / expire due items
        ↓
return response-first TwoPassTurnResult
        └──────── background ────────┐
                                     ↓
                          construct exact CognitionExtractionInput
                                     ↓
                     if explicit two-pass cognitive budget exists:
                       count exact Pass 2 extraction serialization
                       with resolved Pass 2 request before provider delegation
                                     ↓
                          Pass 2 structured extraction
                                     ↓
                         StateCandidate[] / ContinuityCandidate[]
                                     ↓
                  short guarded stale-check / validation boundary
                                     ↓
                  State validation + Continuity candidate application
                  at the already-advanced revision; no second lifecycle advance
```

When two-pass cognitive budget enforcement is configured, RelayLM must count the exact Pass 1 conversation serialization with the same resolved Pass 1 request that is supplied to conversation generation. Pass 1 retains the existing #1387 deterministic degradation and fail-before-generation semantics; it does not substitute the historical combined single-pass serialization.

After the accepted Pass 1 response exists, RelayLM constructs the real `CognitionExtractionInput` and must count the exact Pass 2 extraction serialization with the same resolved Pass 2 request before provider delegation. Pass 2 does not run a second degradation policy or silently rewrite the originating cognitive input. If the exact extraction request does not fit its explicit total-context/output-reserve equation, the extraction ends locally as `failed` with bounded reason `pass2_budget_exceeded` and the extraction provider is not called.

The same provider object is reused sequentially. Pass 2 receives the originating `CognitiveInput` plus the Pass 1 response as interpretive context only. The assistant response is not a source Event and cannot self-certify user or external facts.

Pass 2 inference does not hold the conversation lock. A later Pass 1 may therefore begin while prior extraction is pending. A new two-pass turn advances the process-local execution revision before its preparation; the final extraction commit checks that revision, originating Event identity, origin State snapshot, and the post-conversation Continuity lifecycle snapshot under a short authority lock. A mismatch returns `stale` and performs no proposal-driven mutation or second lifecycle advance.

The same occurrence may currently qualify for recent Working Context and targeted Event evidence when both selectors admit it. Cross-layer redundancy suppression remains intentionally deferred rather than silently changing either selector's semantics.

## Fixed transcript turn replay

RelayLM may replay one already-completed conversational turn when the caller
supplies the original user and assistant message Events. Replay is a governed
post-turn cognition path, not a conversation generation path:

```text
validate supplied user + assistant message Events
        ↓
persist the supplied User Event unchanged
        ↓
prepare the ordinary originating CognitiveInput
from the pre-response State / Continuity snapshot
        ↓
persist the supplied Assistant Event unchanged
        ↓
advance the ordinary successful-conversation Continuity lifecycle once
        ↓
run the ordinary Pass 2 extraction, stale guards,
State validation, and Continuity validation
        ↓
return only after that turn's Pass 2 disposition is known
```

The replay boundary accepts complete RelayLM-owned `Event` values so the
caller-provided Event ID, type, actor, timestamp, payload content, and payload
provenance are not reconstructed. The pair is closed to a non-empty `message`
Event authored by `user`, followed by a distinct non-empty `message` Event
authored by `assistant`. Both Events are validated before either is persisted.
Their journal order is always the supplied user Event followed by the supplied
assistant Event; their timestamps and payloads are preserved exactly.

Replay performs zero Pass 1 provider calls and never regenerates, repairs, or
falls back from the supplied assistant response. It still performs the same
pre-response preparation that ordinary two-pass execution would have performed,
including explicit retrieval, cognitive-budget degradation, and resolved Pass 1
request identity when those controls are supplied. This preserves the exact
originating cognitive snapshot even though provider conversation generation is
skipped. Pass 2 receives that snapshot plus the supplied assistant content and
uses the ordinary Pass 2 request, capacity check, provider extraction, origin
binding, stale guards, and deterministic validators without a replay-specific
proposal grammar or materializer.

One replay call completes its bounded Pass 2 disposition before returning.
Sequential replay therefore prepares turn N+1 only after accepted State and
Continuity from turn N are current. The ordinary response-first failure contract
still applies: a failed, rejected, or stale Pass 2 does not remove either
transcript Event, does not commit invalid State or proposal-driven Continuity,
does not retry extraction, and does not invoke Pass 1 as a fallback. The
successful-conversation Continuity lifecycle advance remains exactly as it does
for an ordinary two-pass turn.

Replay reads crystallized MEMORY only when the ordinary explicit retrieval
controls request it. It never creates or rewrites `MEMORY.md`; crystallization
remains a separate explicitly invoked authority.

For the same starting package and controls, if an ordinary Pass 1 returns the
exact supplied assistant string and Pass 2 returns equivalent proposals, the
ordinary and replay paths converge to the same accepted State and Continuity
semantics. Caller-supplied import Event identity and timestamp metadata may
differ from live-created Event metadata without changing that semantic
equivalence.

## Semantic outputs

### Single-pass CognitiveOutput

```json
{
  "response": "...",
  "state_candidates": [],
  "continuity_candidates": []
}
```

`response` is user-visible natural language. `state_candidates` are non-authoritative proposals. `continuity_candidates` are proposals for bounded non-durable Continuity and require deterministic Continuity validation before becoming accepted temporary authority.

### Two-pass outputs

Pass 1:

```text
CognitionConversationOutput
  response
```

Pass 2:

```text
CognitionExtractionOutput
  state_candidates
  continuity_candidates
```

The originating turn binds both pass outputs. `CognitionExtractionInput.originating_event_id` is derived from the RelayLM-owned current User Event; the model does not author that binding.

Across both policies the semantic return graph remains:

```text
response
  ↓
Assistant Event
  ↓
possible future Working Context

StateCandidate[]
  ↓
Validator
  ↓
Canonical State

ContinuityCandidate[]
  ↓
deterministic Continuity validation
  ↓
process-local Continuity Context
  ↓
later-turn Context Compiler consumption
```

An assistant response therefore remains useful for future conversational continuity without becoming self-certified factual authority. A Continuity proposal likewise does not become accepted temporary authority merely because the model emitted it.

## Streaming semantics

Single-pass streaming does not create a second semantic output form. Provider wire `utterance` deltas are delivery fragments only; the final complete structured result normalizes into one `CognitiveOutput`.

Two-pass streaming exposes only Pass 1 conversation deltas. A complete valid `CognitionConversationOutput` is required before the Assistant Event is persisted, the configured Continuity lifecycle advances once, and Pass 2 is scheduled. Pass 2 does not create a second visible response. When a two-pass cognitive budget is configured, buffered and streaming paths use the same resolved Pass 1 / Pass 2 requests for both exact counting and provider delegation.

## Failure semantics

### Preparation failure

If optional retrieval or budget enforcement fails after the Current User Event is persisted but before model generation:

```text
Current User Event    persisted
Assistant Event       not created
Canonical State       unchanged by that failed turn
Continuity Context    unchanged by that failed turn
```

The persisted unmatched User Event may later participate in bounded Working Context because it is real user-origin conversational evidence even though cognition did not complete.

### Single-pass provider / output failure

If the single-pass provider fails before producing a valid `CognitiveOutput`:

```text
Current User Event    persisted
Assistant Event       not created
Canonical State       unchanged
Continuity Context    unchanged
```

For a streamed single-pass turn, the same rule applies even if a safe prefix of `utterance` was already delivered. A truncated or malformed structured stream does not retroactively turn that visible prefix into an accepted Assistant Event, does not make incomplete candidates authoritative, and does not trigger semantic regeneration.

If a valid single-pass response is produced but one or more StateCandidates are rejected, the valid response still becomes an Assistant Event while rejected candidates do not mutate Canonical State. StateCandidate acceptance and ContinuityCandidate acceptance remain separate deterministic channels.

If a completed single-pass output contains non-empty ContinuityCandidates without an explicit Continuity runtime, the turn fails before Assistant Event, State, or Continuity commit rather than silently dropping those proposals.

### Two-pass Pass 1 failure

A two-pass Pass 1 failure follows the same response-acceptance rule as the corresponding buffered or streaming conversation path: the User Event may already exist, but no Assistant Event, no successful-turn Continuity lifecycle advance, and no Pass 2 extraction is created unless the complete Pass 1 conversation output is valid. A Pass 1 cognitive-budget overflow follows #1387 fail-before-generation semantics, so the conversation provider is not called.

### Two-pass Pass 2 failure

Once Pass 1 has succeeded:

```text
Current User Event    persisted
Assistant Event       persisted
visible response      valid
Pass 2 failure        bounded extraction status
Canonical State       unchanged by failed Pass 2
Pass 2 Continuity proposals             not applied
successful-turn Continuity lifecycle revision / expiry remains
```

A failed or stale Pass 2 applies no proposal-driven Continuity mutation. A provider exception, malformed extraction output, or other Pass 2 execution failure becomes `failed` with bounded reason `pass2_failed`; semantic exception text is not returned as authority or diagnostics payload. A local exact-capacity failure before Pass 2 provider delegation becomes `failed` with bounded reason `pass2_budget_exceeded`. In either failure case, the successfully completed conversation's already-owned Continuity lifecycle revision and any due expiry are not rolled back.

If Pass 2 emits Continuity proposals without an explicit Continuity runtime, the extraction becomes `failed` with `continuity_runtime_required` before State mutation. The State and Continuity proposal channels therefore cannot partially commit across that failure.

If a newer two-pass turn has arrived, or the origin State / post-conversation Continuity snapshot has changed before commit, the old extraction becomes `stale`; it applies no proposals and does not advance the Continuity lifecycle again.

A successful Pass 2 still routes each proposal channel through its existing deterministic validator. Rejected candidates remain rejected model proposals rather than a failure of the already-valid response.

Adapter-level malformed provider output remains fail-closed before the corresponding pass output is accepted.
