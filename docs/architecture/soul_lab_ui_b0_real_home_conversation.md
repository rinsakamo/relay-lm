---
relaylm_doc_type: implementation_handoff
relaylm_authority: bounded_ui_integration
relaylm_status: in_review
relaylm_volatility: medium
relaylm_owner: soul_lab_ui_b0
relaylm_update_trigger:
  - Home conversation transport changes
  - server-owned route projection changes
  - browser request/session fencing changes
  - UI-B0 validation or known limitations change
relaylm_related_authority:
  - docs/PROJECT_STATUS.md
  - docs/architecture/pipeline_implementation_plan.md
  - docs/architecture/post_i3_evaluation_work_roadmap.md
  - docs/architecture/soul_lab_ui_mvp.md
  - docs/architecture/soul_lab_ui_a7_management_projection_handoff.md
  - docs/architecture/integration_i1_primary_mem_two_turn_recall.md
  - docs/architecture/phase_i2_real_soul_lab_observation.md
  - docs/architecture/phase_i3_auditable_primary_mem_correct.md
---
# SOUL Lab UI-B0 Real Home Conversation

## Scope

UI-B0 replaces the fixed Home mock-only submit path with a bounded text-first connection to the existing RelayLM OpenAI-compatible Chat Completions route. It does not create a new conversation, character, memory, SOUL, routing, or backend authority.

```text
SOUL Lab Home
  -> exact active-character server projection
  -> one unambiguous projected route model
  -> same-origin POST /v1/chat/completions
  -> existing RelayLM route and character resolution
  -> existing M2 retrieval
  -> existing RelayCTX injection
  -> existing backend forwarding
  -> bounded non-stream JSON or SSE rendering
```

## Implemented request path

`RootApp` remains the single owner of active character, route, language, and theme. It now retains the exact `LabCharacterProjection` records returned by `/lab/api/characters`, in addition to display-only `CharacterSummary` values, and passes the exact active projection to Home.

Home accepts a real conversation target only when the active projection contains exactly one distinct non-empty `route_models` value:

- zero routes -> `unavailable`
- more than one distinct route -> `ambiguous_route`
- exactly one route -> available

The browser does not select a backend model ID and does not reconstruct a route from display fields. UI-B0 intentionally fails closed instead of assigning new preferred-route semantics to the existing management projection.

The request body is limited to the standard shape:

```json
{
  "model": "<server-projected route model>",
  "messages": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "stream": true
}
```

Only completed messages from the current real browser-local session are eligible for the next request. The browser never adds `system` or `developer` messages.

## Same-origin and credential boundary

The browser sends requests only to `/v1/chat/completions` with:

- `credentials: "same-origin"`
- `cache: "no-store"`
- `Content-Type: application/json`
- `Accept: application/json` or `text/event-stream`
- an `AbortSignal`

The Vite development server proxies `/v1` to `http://127.0.0.1:8090` with `changeOrigin: false`. The browser does not connect to LM Studio directly, does not receive backend credentials, and does not add a permissive CORS policy.

The request excludes character IDs, memory namespaces, backend IDs, SOUL, OUTPUT_POLICY, raw MEM, compiled RelayCTX, credentials, filesystem paths, queue/lease identities, and hidden instructions. Existing RelayLM resolution remains the authority for all of them.

## Non-stream contract

The non-stream client:

- requires a successful HTTP response,
- reads the body through a byte-bounded `ReadableStream`,
- decodes UTF-8 with fatal validation,
- accepts OpenAI-compatible optional extension fields,
- requires a non-empty `choices` array and a string `choices[0].message.content`,
- validates an optional string/null `finish_reason`,
- rejects malformed JSON, missing bodies, invalid structures, and oversized responses,
- maps failures to bounded reason codes without exposing response bodies or exceptions.

## Stream contract

The streaming client handles:

- `ReadableStream` byte chunks,
- UTF-8 code points split across chunks,
- LF or CRLF SSE event boundaries split across chunks,
- comments and non-data events,
- one or more `data:` lines,
- role-only assistant deltas,
- absent, null, or empty content deltas,
- string content deltas,
- optional finish reasons and usage/extensions,
- `[DONE]`,
- abort,
- malformed JSON/events,
- mixed response IDs,
- unavailable bodies,
- truncated streams,
- byte, visible-text, and event-count upper bounds.

One assistant entry is created per request. Every accepted content delta appends to that entry; deltas never create additional messages.

## Stop, failure, and retry state machine

Browser request states are:

```text
idle
  -> submitting
  -> streaming (stream requests)
  -> completed | stopped | failed
```

Soft Stop aborts only the active browser fetch. It does not stop RelayLM, a queue, worker, or backend process. Received assistant text remains visible and the message becomes `stopped`.

Failures retain the user message and the bounded assistant failure state. Raw exceptions, backend bodies, raw JSON, and raw SSE are not rendered or logged by the transport.

Retry is available only for the current real session after `failed` or `stopped`. It reuses the exact stored request snapshot and assistant placeholder, assigns a new request ID and generation, and does not append a duplicate user message. Retry is refused when the current server-projected route no longer matches the snapshot.

## Character, session, and generation fencing

Every real request snapshot captures:

- request ID,
- character ID,
- route model,
- browser-local session ID,
- monotonically advanced generation,
- stream mode,
- exact wire message snapshot,
- assistant placeholder ID.

A completion, SSE delta, error, or finalizer may update state only when the active character, session ID, generation, and route snapshot still match. Character switching, source-mode switching, New Conversation, and unmount abort or invalidate the active request. The character selector being enabled or disabled is not used as the safety fence.

## Real Runtime and Local Preview separation

Real Runtime is the default source mode. Local Preview requires an explicit user action.

Sessions are keyed by `character ID × source mode`. Therefore:

- character sessions do not mix,
- real and preview messages do not mix,
- preview messages cannot enter a real request,
- runtime failures do not trigger automatic preview fallback,
- switching modes preserves separate browser-local histories.

The source mode and request state remain visible as labels such as `REAL RUNTIME · STREAMING` and `LOCAL PREVIEW · COMPLETED`.

Real runtime status uses only the existing content-free `/lab/api/settings` projection and performs no browser-side network probe. Preview mode alone uses the existing mock runtime/events. TTS and avatar configuration are displayed as projected status but are not text-conversation completion gates.

## New Conversation semantics

New Conversation applies only to the current character and current source mode. It:

- aborts and invalidates an in-flight request,
- creates a new browser-local session ID,
- advances the generation fence,
- clears the current message list,
- clears the current draft,
- clears the retry snapshot for that session.

It does not affect another character or source mode, persisted transcripts, Primary MEM, correction receipts, SOUL, or server state.

This separation permits an evaluation in which browser history is cleared while durable M2-selected memory may still affect the next response through existing RelayCTX injection.

## Browser defense bounds

UI-B0 centralizes conservative browser-only limits:

- 40 wire/session messages,
- 8,000 characters per user message,
- 64,000 accumulated visible transcript characters,
- 32,000 response characters,
- 1 MiB response bytes,
- 2,048 SSE events,
- 120-second request timeout.

These are browser safeguards, not replacements for server authority. Oversized input or output is rejected; it is not silently truncated and treated as successful.

## Memory-use validation

UI-B0 does not perform retrieval or prompt injection. The evidence chain remains:

```text
Home real request
  -> existing M2 selection
  -> existing RelayCTX backend-bound injection
  -> response
  -> Phase I-2 used-memory observation evidence
```

The Home UI does not expose raw prompts, compiled context, SOUL, MEM pages, or traces. Phase I-2 remains the evidence surface for memory actually included in backend-bound context. Phase I-3 remains the correction authority.

A fresh browser conversation proves only that frontend history was reset. Durable-memory influence must be confirmed separately through the existing used-memory observation.

## Validation

Frontend:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run smoke:home-conversation
npm run build
```

Repository regressions:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i2_lab_observation_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i3_primary_mem_correct_ci_runner.py
PYTHONPATH=. python scripts/relaylm_openwebui_lmstudio_config_smoke.py
PYTHONPATH=. python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

The strict Node smoke covers request shape and same-origin options, valid and invalid non-stream responses, HTTP/malformed/oversized/abort handling, multi-chunk UTF-8 and SSE parsing, role-only and empty deltas, finish reasons, `[DONE]`, malformed/truncated/oversized/aborted streams, route ambiguity, session separation, reset semantics, stale-generation rejection, failed/stopped history filtering, preview rejection, and source-code guards against unsafe rendering or session persistence.

## Manual smoke

```text
SOUL Lab Vite :5173
  -> RelayLM :8090
  -> LM Studio :1234
```

1. Start an OpenAI-compatible LM Studio server at `http://127.0.0.1:1234/v1` with a model loaded.
2. Start RelayLM with `relaylm --config config.yaml`.
3. Run `npm run dev` in `apps/soul-lab` and open `http://127.0.0.1:5173/lab/`.
4. Confirm the server-configured character appears and Real Runtime is selected.
5. Exercise non-stream and streaming conversation.
6. Stop a stream and confirm partial text remains.
7. Retry and confirm the user message is not duplicated.
8. Switch character during streaming and confirm no old chunk appears under the new character.
9. Start New Conversation and confirm only current browser-local history and draft reset.
10. Select Local Preview explicitly and confirm its messages never appear in Real Runtime.
11. Stop RelayLM or make it unavailable and confirm no automatic mock fallback occurs.
12. Confirm no raw prompt, SOUL, MEM, trace, credential, path, or queue identity is displayed.

For the memory evaluation, use the existing explicit one-job C2 execution method until O0 exists:

```text
real Home conversation
  -> explicit one-job C2 execution
  -> formed Primary MEM
  -> Phase I-2 observation
  -> Phase I-3 Correct
  -> Home New Conversation
  -> question affected by corrected memory
  -> Phase I-2 used-memory evidence
```

UI-B0 does not claim that the complete E1 flow is automated.

## Known limitations and separate slices

- More than one projected route model is fail-closed as `ambiguous_route`; preferred-route semantics are not introduced here.
- Browser transcripts are process-local and non-durable.
- Static SOUL Lab bundle serving is not included.
- O0 local one-job runner remains a separate parallel slice.
- I1-G pre-enqueue durability remains separate.
- I-4 Forget/Hide and later memory governance remain separate.
- Queue scanning, scheduling, supervised worker service, and always-on operation remain separate.
- Secondary MEM consolidation and RelaySOUL proposal/intervention/rollback remain separate.
- TTS, audio, avatar, Live2D, ASR, and peer communication transport remain separate.

## E1 proof boundary

UI-B0 proves that a user can exercise the existing real text request path from SOUL Lab Home and safely observe non-stream or stream output with browser-local session controls. Combined with existing I-1, I-2, and I-3 and an explicit one-job execution method, it enables the first hands-on E1 product evaluation.

It does not prove automatic deferred-job selection, pre-enqueue crash durability, durable transcripts, memory-governance breadth, or long-running production operation.
