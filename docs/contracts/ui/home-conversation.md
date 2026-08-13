---
relaylm_doc_type: contract
relaylm_authority: current_soul_lab_home_real_conversation_browser_transport_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - Home real/preview source-mode, request-state, failure-reason, message, session, or request-snapshot types change
  - Home browser defense bounds, route resolution, request shape, or same-origin fetch options change
  - non-stream or SSE parsing/validation semantics change
  - request/session/generation/character/route fencing, timeout, stop, retry, or New Conversation behavior changes
  - Home begins to add trusted scene evidence, system/developer authority, direct backend access, or durable transcript persistence
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - RelayLM Core Chat Completions request validation, routing, backend execution, streaming emission, or managed runtime semantics
  - trusted scene admission or persistence qualification
  - RelayMEM retrieval, formation, durable queue, worker, or memory mutation semantics
  - Phase I-2 used-memory observation or lifecycle evidence schemas
  - SOUL Lab settings/characters management projection schemas
  - browser visual styling, localization copy, or component hierarchy beyond authority-relevant state behavior
  - static bundle serving, TTS/audio/avatar execution, peer communication, or process lifecycle
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/ui/soul-lab.md
  - ../../architecture/runtime/request-response-pipeline.md
relaylm_related_contracts:
  - soul-lab-management.md
  - ../runtime/managed-route-fallback.md
relaylm_verified_by:
  - ../../../apps/soul-lab/scripts/homeConversationSmoke.mjs
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - SOUL Lab Home conversation maintainers
  - RelayLM browser/runtime integration maintainers
  - UI security, privacy, streaming, and request-fencing reviewers
relaylm_authority_level: exact_contract
---
# SOUL Lab Home Conversation Contract

## Authority summary

This contract owns the exact current **SOUL Lab Home browser-side real-conversation transport and session-fencing boundary**.

The current implementation anchors are:

```text
apps/soul-lab/src/features/home/homeConversationTypes.ts
apps/soul-lab/src/features/home/homeConversationState.ts
apps/soul-lab/src/features/home/homeConversationApi.ts
apps/soul-lab/src/features/home/HomeConversationPage.tsx
```

The focused exact-head browser contract evidence is:

```text
apps/soul-lab/scripts/homeConversationSmoke.mjs
```

The real path remains:

```text
server-owned LabCharacterProjection
  -> exactly one unambiguous route model
  -> browser-local real session snapshot
  -> same-origin POST /v1/chat/completions
  -> existing RelayLM Core route/runtime authority
  -> bounded JSON or SSE parse
  -> fenced browser-visible assistant result
```

Home does not become a second route resolver, backend client, scene authority, memory reader, persistence gate, transcript store, or runtime orchestrator.

## Relationship to SOUL Lab management

`docs/contracts/ui/soul-lab-management.md` owns the exact current read-only `/lab/api/characters` projection used to obtain route-model labels.

Home accepts only the route labels that arrived through the exact active character projection.

This contract does not redefine how the server constructs `LabCharacterProjection`; it owns only how Home consumes one exact projection to decide whether a real conversation target is usable.

## Relationship to RelayLM Core

The browser calls the existing Core route:

```text
POST /v1/chat/completions
```

The Core route remains authoritative for:

- model-route resolution;
- character and memory scope;
- managed/pass-through runtime selection;
- request validation beyond the browser's defense-in-depth checks;
- RelayMEM retrieval;
- RelayCTX construction;
- backend execution;
- output safety and streaming behavior;
- server-side persistence qualification.

A browser request that passes this contract has not thereby acquired server authority.

## Source-mode vocabulary

The exact current `ConversationSourceMode` vocabulary is:

```text
real
preview
```

Real and preview are distinct browser-local session domains.

Preview never enters the real request builder.

## Request-state vocabulary

The exact current `ConversationRequestState` vocabulary is:

```text
idle
submitting
streaming
completed
stopped
failed
```

`isRequestActive(...)` returns true exactly for:

```text
submitting
streaming
```

All other request states are non-active for the helper.

## Failure-reason vocabulary

The exact current `ConversationFailureReason` vocabulary is:

```text
unavailable
ambiguous_route
invalid_request
http_failure
timeout
response_invalid
response_too_large
stream_invalid
stream_truncated
body_unavailable
aborted
network_failure
```

These are bounded browser-visible reason classes.

Raw backend response bodies, raw thrown exception strings, credentials, prompt/context content, filesystem paths, and queue/worker identities are not substituted for these values.

## Message-status vocabulary

The exact current `ConversationMessageStatus` vocabulary is:

```text
complete
pending
streaming
stopped
failed
```

Only completed browser messages are eligible for the next real wire history.

## ConversationMessage shape

The current browser message interface has exactly these responsibility-level fields:

```text
messageId
role
content
status
occurredAtLabel
failureReason?
```

The role vocabulary is exactly:

```text
user
assistant
```

There is no browser Home `system` or `developer` message role.

## WireConversationMessage shape

The exact current wire-message interface contains only:

```text
role
content
```

with role exactly:

```text
user | assistant
```

No character ID, memory namespace, backend ID, source mode, request ID, session ID, generation, or internal authority field is part of a wire message.

## ConversationRequestSnapshot shape

Every exact real request snapshot carries:

```text
requestId
characterId
routeModel
sessionId
generation
sourceMode
stream
messages
assistantMessageId
```

`sourceMode` is statically/exactly:

```text
real
```

The snapshot stores the exact wire message list that belongs to that request.

It is a browser request fence and retry snapshot, not a server authorization object.

## ConversationSession shape

The exact current browser session contains:

```text
sessionId
generation
sourceMode
requestState
messages
draft
lastRequest
```

`lastRequest` is either null or an exact `ConversationRequestSnapshot`.

Sessions are browser-process state only and are not a durable transcript authority.

## Conversation target states

The exact current target result vocabulary is:

```text
available
unavailable
ambiguous_route
```

An available target contains:

```text
status = available
characterId
routeModel
```

An unavailable/ambiguous target contains only:

```text
status
characterId
```

## Server-projected route resolution

The current helper is:

```text
resolveConversationTarget(projection, characterId)
```

It first requires:

```text
projection exists
AND
projection.character_id == characterId
```

otherwise the result is `unavailable`.

It then filters projected `route_models` to non-empty-after-trim strings and removes duplicates.

The exact result rule is:

```text
0 distinct non-empty routes -> unavailable
1 distinct non-empty route  -> available
2+ distinct non-empty routes -> ambiguous_route
```

Home does not use list order as route priority and does not choose a backend ID/model directly.

## No browser route priority

When multiple server-projected route models exist, Home fails closed as:

```text
ambiguous_route
```

It does not:

- select the first array entry;
- sort and choose the first route;
- infer a preferred route from backend/model labels;
- reuse a previous route from another character;
- query a backend directly.

Any future preferred-route semantics require an explicit server-owned projection contract.

## Browser defense bounds

The exact current `HOME_CONVERSATION_BOUNDS` values are:

```text
maxMessages          = 40
maxUserMessageChars  = 8_000
maxTranscriptChars   = 64_000
maxResponseChars     = 32_000
maxResponseBytes     = 1_048_576
maxSseEvents         = 2_048
requestTimeoutMs     = 120_000
```

These are browser defense-in-depth bounds only.

They do not widen or replace server-side limits.

## Session key

The exact current session-key helper is:

```text
conversationSessionKey(characterId, sourceMode)
```

and returns the concatenation:

```text
<characterId> + U+0000 + <sourceMode>
```

Therefore real/preview sessions for one character have different keys, and two characters have different keys even in the same source mode.

The key is browser-local and is not transmitted as server identity.

## Session creation

`createConversationSession(sourceMode, sessionId)` initializes:

```text
generation = 0
requestState = idle
messages = []
draft = ""
lastRequest = null
```

When no explicit `sessionId` is supplied, the helper uses `crypto.randomUUID()`.

The session ID is not a server session ID.

## New Conversation/reset helper

`resetConversationSession(current, sessionId)` creates a fresh session in the same source mode and sets:

```text
generation = current.generation + 1
```

All current messages, draft, and retry snapshot are cleared through new-session initialization.

When no explicit new session ID is supplied, `crypto.randomUUID()` is used.

This resets browser-local conversation state only.

## Wire-history filtering

The exact current helper:

```text
toWireHistory(messages)
```

includes only messages whose:

```text
status == complete
```

and maps each retained message to only:

```text
role
content
```

Therefore pending, streaming, stopped, and failed assistant placeholders do not enter the next request.

## Transcript character count

The current helper:

```text
transcriptCharacterCount(messages)
```

sums the JavaScript string lengths of all browser message contents supplied to it.

The Home page uses this browser-local count when refusing a new submission that would exceed the transcript bound.

## Request snapshot fence

The exact current helper:

```text
requestSnapshotMatches(snapshot, current)
```

requires simultaneous equality of:

```text
characterId
sessionId
generation
routeModel
```

A mismatch in any one field returns false.

This is the central stale-update fence for completion, streaming delta, failure, and finalizer paths.

## Chat Completions body builder

The current builder is:

```text
buildChatCompletionsBody(snapshot)
```

It returns exactly:

```text
model
messages
stream
```

No other snapshot field is copied into the body.

## Exact body shape

The body is structurally:

```json
{
  "model": "<routeModel>",
  "messages": [
    {"role": "user|assistant", "content": "..."}
  ],
  "stream": true
}
```

with `stream` equal to the snapshot boolean.

The body does not include:

- `characterId`;
- `memory_namespace`;
- `backend_id`;
- browser request/session/generation IDs;
- `system` or `developer` messages;
- raw SOUL or memory content;
- compiled RelayCTX;
- trusted scene metadata;
- credentials;
- queue/claim/worker identity.

## Request-builder initial validation

The body builder rejects with:

```text
HomeConversationError(invalid_request)
```

when any of these are true:

```text
sourceMode != real
routeModel.trim() is empty
messages is empty
message count > 40
```

## Per-message request validation

Every snapshot message must have:

```text
role exactly user or assistant
content typeof string
content length > 0
```

Any violation returns `invalid_request`.

A user message may not exceed:

```text
8_000 chars
```

An assistant message may not exceed:

```text
32_000 chars
```

The running transcript character sum may not exceed:

```text
64_000 chars
```

## Final-message request invariant

After mapping/validation, the last wire message must:

```text
exist
have role == user
have content.trim().length > 0
```

Otherwise request construction fails with `invalid_request`.

This prevents a real request ending on a non-final assistant entry or a whitespace-only user turn.

## No trusted scene assertion

The exact current Home request body contains no `metadata.scene_state` or equivalent trusted persistence qualification.

The browser must not manufacture a high-confidence scene state or persistence permission.

This is an intentional fail-closed authority boundary, even though it means an ordinary Home-origin turn may not satisfy current persistence thresholds.

Trusted scene-admission authority remains server/route-owned and outside this contract.

## Real fetch target

Both non-stream and stream helpers ultimately call exactly:

```text
/v1/chat/completions
```

through browser `fetch`.

The browser does not construct a configured backend URL and does not call LM Studio or another backend directly.

## Fetch options

The current request uses:

```text
method = POST
credentials = same-origin
cache = no-store
signal = supplied AbortSignal
Content-Type = application/json
Accept = application/json | text/event-stream
```

No browser `Authorization` header is added by Home.

The exact `Accept` value is selected by the non-stream versus streaming helper.

## HTTP failure handling

If the fetch call returns a non-OK HTTP response, Home throws only:

```text
HomeConversationError(http_failure)
```

It does not read and display the raw backend/RelayLM failure body as user-facing error text.

## Fetch exception handling

A fetch exception maps to:

```text
aborted
```

when the supplied signal is aborted or the exception is a DOM `AbortError`.

Other fetch exceptions map to:

```text
network_failure
```

Raw exception text is not part of the `HomeConversationError` reason.

## HomeConversationError shape

`HomeConversationError` stores only the bounded `ConversationFailureReason` as its public reason and uses the same reason string as the Error message.

Its name is exactly:

```text
HomeConversationError
```

The implementation does not pass through a caught raw backend body/exception message into this error.

## Non-stream entry point

The current non-stream API is:

```text
requestHomeConversation(snapshot, signal, fetchImpl=fetch)
```

It:

1. performs the bounded request with `Accept: application/json`;
2. reads the response through the bounded streaming byte reader;
3. JSON-decodes the completed text;
4. validates the OpenAI-compatible first choice;
5. returns only bounded assistant text and optional finish reason.

## Non-stream body presence

A successful HTTP response whose body is null fails with:

```text
body_unavailable
```

No fallback response is synthesized.

## Non-stream byte bound

The response reader counts every received byte chunk.

If cumulative bytes exceed:

```text
1_048_576
```

it fails with:

```text
response_too_large
```

## Fatal UTF-8 decoding

Non-stream response bytes are decoded with:

```text
TextDecoder("utf-8", {fatal: true})
```

Malformed UTF-8 during the bounded body read maps to:

```text
response_invalid
```

## Additional decoded-body bound

After bounded byte decoding, the implementation rejects the decoded body when:

```text
result.length > maxResponseChars * 4
```

with `response_too_large`.

Under current constants the decoded JSON-text bound is therefore:

```text
128_000 JavaScript characters
```

before OpenAI-compatible structural parsing.

## Non-stream JSON parse

Malformed JSON maps to:

```text
response_invalid
```

Raw malformed text is not retained as a visible assistant response.

## Non-stream completion shape

A valid payload must be an object with:

```text
choices = non-empty array
```

The first element must be an object containing:

```text
message = object
message.content = string
```

Optional extension fields elsewhere are ignored by this bounded parser.

## Non-stream visible response bound

`choices[0].message.content` must not exceed the current dynamic response character limit.

The dynamic limit is:

```text
min(
  32_000,
  max(0, 64_000 - requestCharacters)
)
```

where `requestCharacters` is the sum of snapshot wire-message content lengths.

Overflow returns `response_too_large`.

## Non-stream finish reason

`choices[0].finish_reason` may be:

```text
undefined
null
string
```

Any other type returns `response_invalid`.

The returned completion normalizes undefined/null to:

```text
finishReason = null
```

and returns only:

```text
text
finishReason
```

## Streaming entry point

The current streaming API is:

```text
streamHomeConversation(
  snapshot,
  signal,
  onDelta,
  fetchImpl=fetch,
)
```

It requests with:

```text
Accept: text/event-stream
```

and requires a response body.

## Streaming parser state

The current parser tracks bounded local state:

```text
buffer
byteCount
visibleCount
eventCount
doneSeen
finishReason
responseId
```

None of these values creates server/runtime authority.

## Streaming byte bound

Every received chunk increments `byteCount`.

If:

```text
byteCount > 1_048_576
```

streaming fails with:

```text
response_too_large
```

## Streaming UTF-8 behavior

Streaming uses a fatal UTF-8 decoder with incremental decode mode.

UTF-8 code points may be split across byte chunks and remain valid.

Invalid UTF-8 maps to:

```text
stream_invalid
```

The decoder is flushed once at stream end.

## SSE event boundaries

The current parser recognizes either:

```text
LF LF
```

or:

```text
CRLF CRLF
```

as one SSE event boundary.

The earliest complete boundary in the current buffer wins.

Boundaries may themselves be split across network chunks because parsing operates on the accumulated decoded buffer.

## Empty events

An event whose raw text trims to empty is skipped and does not increment the bounded event count.

Non-empty events increment:

```text
eventCount
```

before data extraction.

## SSE event-count bound

If:

```text
eventCount > 2_048
```

streaming fails with:

```text
response_too_large
```

Comments therefore still consume the bounded event count when their raw event is non-empty, even when they yield no data payload.

## SSE data-line parsing

Within one raw event:

- lines beginning with `:` are comments and ignored as data;
- a line exactly `data` contributes an empty data line;
- a line beginning `data:` contributes the value after `data:` with at most one immediately following space removed;
- multiple data lines are joined with `\n`;
- an event with no data lines yields no payload and is otherwise ignored.

Other SSE fields are not interpreted by this parser.

## `[DONE]`

The exact sentinel:

```text
[DONE]
```

sets:

```text
doneSeen = true
```

and produces no visible delta.

Any subsequent non-`[DONE]` data event after `doneSeen` causes:

```text
stream_invalid
```

## Streaming JSON validation

Every non-sentinel data payload must parse as JSON.

Malformed JSON returns:

```text
stream_invalid
```

## Streaming event object

A parsed stream event must be an object with:

```text
choices = array
```

otherwise it is `stream_invalid`.

## Optional response ID

The top-level `id`, when present, must be a string.

The first present string response ID becomes the expected response ID.

If a later event contains another present ID that differs from the expected ID, streaming fails with:

```text
stream_invalid
```

Events may omit `id` without clearing the remembered response ID.

## Usage-only empty-choice event

When:

```text
choices.length == 0
```

the top-level payload must contain an object-valued:

```text
usage
```

otherwise the event is invalid.

A valid usage-only event produces no delta and no finish reason.

## Streaming first choice

When choices are non-empty, the first choice must be an object containing:

```text
delta = object
```

otherwise `stream_invalid` is returned.

## Delta role

`choice.delta.role` may be absent or exactly:

```text
assistant
```

Any other present role returns:

```text
stream_invalid
```

Role-only assistant deltas are valid and produce empty visible content.

## Delta content

`choice.delta.content` may be:

```text
undefined
null
string
```

Other types are invalid.

Undefined/null map to an empty delta.

A string delta is appended to the existing single assistant placeholder only after all current fences remain valid at the Home page layer.

## Streaming finish reason

`choice.finish_reason` may be:

```text
undefined
null
string
```

Other types are invalid.

The most recent non-null finish-reason string becomes the streaming result's `finishReason`.

## Streaming visible-character bound

Every non-empty accepted delta increments a local visible character count.

If the count exceeds the same dynamic response-character limit used by non-stream parsing, streaming fails with:

```text
response_too_large
```

The overflowing delta is not accepted as a successful completion.

## Stream completion requirements

At transport EOF, after decoder flush:

```text
buffer.trim().length must equal 0
AND
doneSeen must be true
```

Remaining non-whitespace text produces:

```text
stream_truncated
```

Missing `[DONE]` also produces:

```text
stream_truncated
```

A finish reason alone does not replace the `[DONE]` requirement.

## Streaming abort/failure closure

During stream processing, an aborted signal becomes:

```text
aborted
```

A known `HomeConversationError` is preserved.

Other reader/network exceptions become:

```text
network_failure
```

The reader lock is released in `finally`.

## Streaming result shape

A successful stream returns only:

```text
finishReason
eventCount
```

The visible assistant text is delivered incrementally through `onDelta` and is owned by the fenced Home session state.

## One assistant placeholder per request

The Home page creates one user message and one empty/pending assistant message before real request execution.

Streaming deltas update the same `assistantMessageId`; they do not append a new assistant message for every chunk.

## Submission preconditions

Home refuses a new submit when:

- the trimmed draft is empty;
- the current request state is active;
- the user message exceeds 8,000 chars;
- adding user+assistant entries would exceed 40 messages;
- current transcript characters plus the new user body would exceed 64,000;
- real mode has no exact available target.

Preview mode follows a separate local path and does not require a real route target.

## Real request snapshot creation

For a valid real submit, Home increments session generation and creates:

```text
user message status = complete
assistant message status = pending
```

The request snapshot stores:

```text
new request UUID
active character ID
exact resolved route model
current session ID
new generation
sourceMode = real
current stream mode
completed prior wire history + current user message
assistant placeholder ID
```

The snapshot becomes `lastRequest` for bounded retry behavior.

## Current-request predicate

Before applying a delta or result, Home requires:

```text
activeCharacterId == snapshot.characterId
AND
current real session exists
AND
requestSnapshotMatches(snapshot, current fence tuple)
```

The fence tuple includes the snapshot route model rather than independently re-resolving a browser route during each callback.

## Character change invalidation

When the active character changes, the page invalidates the current active request.

Invalidation:

- aborts the controller;
- clears its timeout;
- removes the active-request reference;
- increments the old real session generation when the exact old session still exists;
- may mark the existing assistant placeholder `stopped` for user-visible invalidation.

A delayed old-character completion/delta can no longer pass the generation/character fence.

## Component unmount invalidation

The page cleanup invalidates any active request on component unmount.

This prevents an unmounted Home component from accepting a later completion into stale browser state.

## Timeout boundary

Every real execution creates a timer of exactly:

```text
120_000 ms
```

When it fires, the active request marks:

```text
timedOut = true
```

and aborts the request controller.

At catch time, a timed-out request maps to browser reason:

```text
timeout
```

rather than ordinary `aborted`.

The timer is cleared in finalization and explicit invalidation paths.

## Soft Stop boundary

A user Stop action marks the active request:

```text
stoppedByUser = true
```

and aborts its controller.

It does not stop RelayLM server, backend generation authority, queue workers, or memory processes through a privileged control API.

If the request remains current when the abort is observed, the browser result state becomes:

```text
requestState = stopped
assistant message status = stopped
failureReason = aborted
```

Previously received streaming text remains browser-visible in the same assistant entry.

## Failure-state priority

When a current request throws, Home selects the bounded failure reason in this priority:

```text
active.timedOut
  -> timeout

else active.stoppedByUser
  -> aborted

else HomeConversationError
  -> error.reason

else
  -> network_failure
```

A user-stop request state is `stopped`; other failures use `failed`.

## Finalizer fence

Finalization clears the request timeout.

The global active-request reference is cleared only if its current request ID still equals the finalized snapshot request ID.

This prevents an older finalizer from clearing a newer request's active state.

## Retry boundary

Retry uses the browser session's exact `lastRequest` snapshot and does not append the user message again.

Retry is refused when:

- there is no previous snapshot;
- another request is active;
- current real target is unavailable/ambiguous;
- the current exact route model differs from the prior snapshot route;
- the current session ID differs from the prior snapshot session.

The retry path advances generation and creates a new request ID while preserving the original exact wire-message list for the failed/stopped request.

It clears/reuses the existing assistant placeholder rather than duplicating the user turn.

## Retry is not route migration

A retry cannot silently move a failed request to another projected route or another browser session.

If server projection changes the route or the user starts a New Conversation, the old snapshot is no longer retry-eligible.

## New Conversation authority

New Conversation resets only the current:

```text
character ID × source mode
```

session.

It invalidates any relevant active request, replaces the browser-local session ID, increments generation, and clears messages/draft/retry state.

It does not:

- erase durable memory;
- clear another character's browser session;
- clear the other source mode's session;
- issue a server transcript-delete call;
- change server route or character configuration.

## Real/preview separation

The default source mode for a character is:

```text
real
```

Local Preview must be explicitly selected.

Preview submission creates only browser-local complete user/assistant entries and does not call RelayLM.

The preview assistant text explicitly identifies itself as local preview behavior in current UI copy.

Preview history cannot enter `buildChatCompletionsBody` because request snapshots require `sourceMode=real` and real/preview sessions use distinct keys.

## No automatic preview fallback

A real network/HTTP/parse/stream failure remains a real failure.

Home does not automatically switch to Local Preview and present mock output as successful runtime output.

This source distinction is part of the authority boundary, not merely UI labeling.

## Management projection and runtime status

Home may display real-runtime readiness/status using the existing content-free SOUL Lab management projection.

It does not perform a separate browser-side backend probe and does not receive credentials.

TTS/avatar component configuration is not an eligibility gate for text conversation.

## No raw HTML rendering escape

Current focused smoke inspects `HomeConversationPage.tsx` and requires that it not use:

```text
dangerouslySetInnerHTML
```

for this Home conversation path.

Visible text remains ordinary React text content rather than raw backend-supplied HTML injection.

## Browser transcript persistence boundary

Current focused smoke requires no Home session persistence through a `localStorage` session pattern.

Real/preview conversation sessions remain browser-process/local React state rather than durable browser transcript storage.

This contract does not forbid separately governed future persistence; it records that the current exact B0 path is non-durable.

## Persistence qualification boundary

A successful Home conversation is not proof that a new Primary MEM formation job was admitted or published.

Current Home requests do not add trusted scene admission.

Server-side RelaySCN/persistence gates may therefore fail closed for ordinary Home-origin formation while the text conversation itself succeeds.

Home must not fabricate a persistence-success indicator from visible assistant text.

## Memory retrieval boundary

Home does not call RelayMEM retrieval directly.

If durable memory influences the request, it does so through the existing managed server pipeline.

Actual used-memory/backend-bound evidence remains the responsibility of separately versioned observation contracts.

The browser does not infer actual memory use merely because the model's answer appears to remember something.

## No direct backend authority

Home never receives configured backend credentials from this contract and never sends the request directly to the backend endpoint.

The browser-facing target remains:

```text
/v1/chat/completions
```

Server-managed route/backend authority remains behind that same-origin boundary.

## No hidden instruction authority

The exact current request body does not insert:

- hidden system text;
- developer messages;
- browser-generated SOUL instructions;
- memory summaries;
- scene or relationship assertions;
- backend credentials;
- internal diagnostics.

Only completed user/assistant conversation messages are sent.

## Extension-field tolerance boundary

The non-stream parser and stream parser allow safe unrelated OpenAI-compatible extension fields because they inspect only their required structural fields.

Tolerance of an extension field does not mean the browser trusts that field as route, memory, scene, safety, or persistence authority.

## Fail-closed invariants

The exact current Home browser invariants include:

1. real requests require an exact active server character projection with exactly one distinct non-empty route model;
2. ambiguous route projection never becomes a browser-selected route;
3. preview sessions never enter real requests;
4. request bodies contain only `model`, `messages`, and `stream`;
5. Home never emits system/developer messages or trusted scene assertions;
6. message/transcript/response/byte/event bounds reject overflow rather than silently truncating and reporting success;
7. HTTP failure never renders raw failure bodies;
8. malformed UTF-8/JSON/SSE becomes bounded failure;
9. mixed stream response IDs fail closed;
10. successful streaming requires `[DONE]` and no residual non-whitespace tail;
11. only completed browser messages enter the next wire history;
12. every asynchronous update is fenced by character/session/generation/route state;
13. character change/unmount/New Conversation invalidate stale request authority;
14. timeout and user Stop abort only the browser request path;
15. retry preserves the exact failed/stopped request wire snapshot and cannot silently move routes/sessions;
16. real failure never becomes automatic preview success;
17. browser Home sessions are non-durable current process state;
18. visible response text is not proof of persistence or actual memory-use evidence;
19. Home never contacts configured backends directly;
20. raw backend HTML is not injected through `dangerouslySetInnerHTML`.

## Current focused evidence

The exact current browser contract is guarded by:

```text
apps/soul-lab/scripts/homeConversationSmoke.mjs
```

The smoke transpiles and exercises the exact TypeScript state/API modules and statically inspects the Home page.

Current evidence covers:

- exact request body and absence of character/memory/backend/system fields;
- invalid real snapshots and browser bounds;
- same-origin/no-store fetch options and absent Authorization header;
- valid non-stream parsing with tolerated extensions;
- malformed/HTTP/body-missing/oversize/abort failure classes;
- UTF-8 code points split across SSE byte chunks;
- role-only/empty/string deltas;
- finish reason and usage extensions;
- `[DONE]` handling;
- missing-body, malformed, truncated, mixed-ID, oversize, event-count, and abort stream failures;
- route target unavailable/available/ambiguous behavior;
- real/preview and character session-key separation;
- New Conversation/reset semantics;
- request snapshot fence mismatches;
- active-state classification;
- stopped/failed history exclusion;
- presence of request-invalidation/fencing implementation hooks;
- absence of raw-HTML rendering and browser transcript persistence patterns.

## Relationship to A7 management read contract

A7 provides the server-owned route-model source.

B0 provides the browser conversation transport.

Neither authority subsumes the other:

```text
soul-lab-management.md
  -> what server configuration metadata may be read

home-conversation.md
  -> how one accepted route model is used by the browser for bounded conversation
```

## Relationship to request/response pipeline

`docs/architecture/runtime/request-response-pipeline.md` owns the stable runtime pipeline after the request reaches RelayLM.

This exact Home contract ends at safe browser request construction/transport and begins again at safe browser response parsing/render-state admission.

It does not duplicate server runtime internals.

## Source-retirement boundary

The UI-B0 real Home conversation implementation handoff was retired by a separate bounded documentation transaction that recorded its exact provenance in the central retirement manifest and repaired every live consumer. This contract owns the continuing exact Home browser transport and session-fencing responsibility; its rollout chronology is recoverable from Git history plus that manifest.

This contract does not retire the TypeScript implementation, smoke, or evaluation evidence. Any further source retirement remains a separate bounded transaction with exact provenance, consumer repair, and migration disposition.
