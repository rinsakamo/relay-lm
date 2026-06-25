---
relaylm_doc_type: implementation_handoff
relaylm_authority: bounded_ui_integration
relaylm_status: current
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
  - docs/architecture/e1_local_runtime_evaluation_2026_06_25.md
  - docs/architecture/soul_lab_ui_mvp.md
  - docs/architecture/soul_lab_ui_a7_management_projection_handoff.md
  - docs/architecture/integration_i1_primary_mem_two_turn_recall.md
  - docs/architecture/phase_i2_real_soul_lab_observation.md
  - docs/architecture/phase_i3_auditable_primary_mem_correct.md
  - docs/architecture/o0_local_one_job_runner.md
  - docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md
---
# SOUL Lab UI-B0 Real Home Conversation

## Scope

UI-B0 replaces the fixed Home mock-only submit path with a bounded text-first client of the existing RelayLM OpenAI-compatible Chat Completions route. It creates no new conversation, character, memory, SOUL, routing, backend, queue, or worker authority.

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

## Server-owned conversation target

`RootApp` remains the single owner of route, language, theme, and active character. It retains the exact `LabCharacterProjection` values returned by `/lab/api/characters` and separately derives display summaries.

Home accepts a real target only when the active exact projection contains one distinct non-empty route model:

```text
0 routes       -> unavailable
1 route        -> available
2+ routes      -> ambiguous_route
```

The browser does not choose a backend model ID, infer a route from display fields, or treat array order as preferred-route semantics. A future server-owned preferred route would require a separate projection contract.

## Request contract

A request contains only standard Chat Completions fields:

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

Only completed messages from the current real browser-local session enter the next request.

The browser never adds:

- `system` or `developer` messages,
- character IDs or memory namespaces,
- raw SOUL, MEM, or compiled RelayCTX,
- backend IDs or credentials,
- filesystem paths,
- queue, claim, lease, or worker identities,
- hidden instructions or preview messages.

### Persistence qualification boundary

The standard UI-B0 request also does not add trusted `metadata.scene_state` evidence. This is intentional within the current bounded transport contract: the browser must not self-assert arbitrary persistence policy or high-confidence scene authority.

A real workstation evaluation on 2026-06-25 confirmed the resulting boundary:

```text
Home conversation and later recall
  -> works through the existing managed request path

ordinary Home turn requiring new Primary MEM formation
  -> RelaySCN heuristic fallback
  -> confidence/stability below persistence thresholds
  -> persistence fails closed
  -> no protected source or queue record
```

An explicit operator request with bounded scene evidence successfully exercised finalized-turn publication, O0 execution, Primary MEM formation, and later Home recall. Therefore UI-B0 proves real conversation and recall transport, but it does not currently prove that an ordinary Home-origin turn is persistence-eligible. The trusted scene-admission owner remains a separate follow-up decision.

Fetch uses:

```text
path: /v1/chat/completions
credentials: same-origin
cache: no-store
signal: AbortSignal
```

The Vite development server proxies `/v1` to `http://127.0.0.1:8090` with `changeOrigin: false`. The browser never connects directly to LM Studio and UI-B0 adds no permissive CORS policy.

## Non-stream contract

The non-stream parser:

- requires a successful HTTP response,
- reads the body through a bounded `ReadableStream`,
- decodes UTF-8 with fatal validation,
- accepts safe OpenAI-compatible extension fields,
- requires a non-empty `choices` array,
- requires string `choices[0].message.content`,
- validates optional string/null `finish_reason`,
- rejects missing body, malformed JSON, invalid structure, and oversize,
- emits bounded reason codes only.

Raw response bodies, raw JSON, and backend exceptions are never rendered or included in user-facing errors.

## Streaming contract

The SSE parser handles:

- `ReadableStream` byte chunks,
- UTF-8 code points split across chunks,
- LF and CRLF event boundaries split across chunks,
- `data:` lines and comments,
- `[DONE]`,
- role-only assistant deltas,
- absent/null/empty content deltas,
- string content deltas,
- finish reasons,
- optional usage and extension fields,
- request abort,
- malformed JSON/events,
- mixed response IDs,
- missing response body,
- truncated streams,
- byte, text, and event-count bounds.

One assistant entry is created for the request. Accepted content deltas append to that entry; a delta never creates another message.

## Request state machine

```text
idle
  -> submitting
  -> streaming       when stream=true
  -> completed
  -> stopped
  -> failed
```

### Stop

Soft Stop aborts only the browser request. It does not stop RelayLM, LM Studio, a queue, or a worker. Received partial text remains visible and the assistant message becomes `stopped`.

### Failure

The user message remains visible. The assistant placeholder becomes a bounded failure state such as HTTP failure, timeout, invalid response, invalid stream, truncation, body unavailable, abort, or network failure. Raw backend content is not exposed and there is no automatic preview fallback.

### Retry

Retry reuses the exact failed/stopped request snapshot. It assigns a new request ID and generation, clears the existing assistant placeholder, and does not append the user message again. Retry is refused when the current route or session no longer matches the snapshot.

## Character, session, and generation fencing

Every real request snapshot captures:

- request ID,
- character ID,
- server-projected route model,
- browser-local session ID,
- generation,
- stream mode,
- exact wire message list,
- assistant placeholder ID.

A completion, SSE delta, failure, or finalizer may update state only while the current character, real session, generation, and route snapshot remain valid. Character changes, source-mode changes, New Conversation, and component unmount abort or invalidate the active request. The character selector UI state is not the safety fence.

Per-character sessions remain separate. Old-character completion and chunk paths cannot write into the new character session.

## Real Runtime and Local Preview

Real Runtime is the default source mode. Local Preview requires explicit user selection.

Sessions are keyed by:

```text
character ID × source mode
```

Therefore:

- different character histories do not mix,
- real and preview histories do not mix,
- preview messages cannot enter a real request,
- a runtime error never switches to preview automatically,
- switching modes preserves distinct browser-local histories.

The current source and request state remain visible through labels such as:

```text
REAL RUNTIME · READY
REAL RUNTIME · STREAMING
REAL RUNTIME · FAILED
REAL RUNTIME · UNAVAILABLE
LOCAL PREVIEW · COMPLETED
```

Real runtime status reuses only the existing content-free `/lab/api/settings` projection. It performs no browser-side network probe and reads no credentials. TTS and avatar configuration are not text-conversation completion gates.

## New Conversation

New Conversation applies only to the current character and current source mode. It:

- aborts and invalidates the in-flight request,
- creates a new browser-local session ID,
- advances the generation fence,
- clears current messages,
- clears the current draft,
- clears the retry snapshot.

It does not alter another character/source session, persisted transcript data, SOUL, Primary MEM, correction receipts, observation evidence, or server state.

A fresh Home conversation proves only that frontend history was reset. Durable-memory influence must still be verified through existing Phase I-2 used-memory evidence.

## Browser defense bounds

UI-B0 centralizes conservative browser-only limits:

```text
messages                 40
user message chars       8,000
visible transcript chars 64,000
response chars           32,000
response bytes           1 MiB
SSE events               2,048
request timeout          120 seconds
```

These do not replace server authority. Oversize is rejected rather than silently truncated and reported as success.

## Memory-use validation

UI-B0 does not implement retrieval or prompt injection.

```text
Home real request
  -> existing M2 selection
  -> existing RelayCTX backend-bound injection
  -> backend response
  -> Phase I-2 used-memory observation evidence
```

Home never displays raw prompts, compiled context, SOUL, MEM pages, or traces. Phase I-2 remains the evidence surface for actual backend-bound memory inclusion. Phase I-3 remains the correction authority.

The 2026-06-25 workstation evaluation confirmed that a Primary MEM formed through the existing worker path could later influence a Home answer under the exact character and namespace scope. The answer recalled the core user fact, but also exposed separate formation-provenance and response-grounding quality gaps documented in [E1 Local Runtime Evaluation](e1_local_runtime_evaluation_2026_06_25.md).

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

The dedicated GitHub workflow passes typecheck, strict Node smoke, production build, compileall, documentation checks, Phase I-1/I-2/I-3 regressions, and OpenWebUI/LM Studio configuration/proxy smokes.

The Node smoke covers request shape and same-origin options, valid/invalid non-stream responses, HTTP/malformed/oversize/abort handling, multi-chunk UTF-8 and SSE parsing, role-only and empty deltas, finish reason, `[DONE]`, malformed/truncated/oversized/aborted streams, route ambiguity, session/source separation, reset semantics, stale generation rejection, failed/stopped history filtering, and unsafe-rendering/persistence guards.

## Manual smoke

```text
SOUL Lab Vite :5173
  -> RelayLM :8090
  -> LM Studio :1234
```

1. Start LM Studio OpenAI-compatible serving with a model loaded.
2. Start RelayLM with `relaylm --config config.yaml`.
3. Start SOUL Lab with `npm run dev`.
4. Confirm a server-configured character appears.
5. Exercise non-stream and streaming Real Runtime conversation.
6. Stop streaming and confirm partial text remains.
7. Retry and confirm the user message is not duplicated.
8. Switch character during streaming and confirm no old chunk appears.
9. Use New Conversation and confirm only current browser-local history and draft reset.
10. Select Local Preview explicitly and confirm it never enters Real Runtime history.
11. Make RelayLM unavailable and confirm no automatic mock fallback occurs.
12. Confirm no raw prompt, SOUL, MEM, trace, credential, path, or queue identity is displayed.
13. Do not treat a successful Home response as proof that finalized-turn persistence or queue publication occurred.

A real LM Studio workstation manual smoke is environment validation and is not fabricated by CI.

## E1 evaluation path

O0 is complete and provides the explicit one-job execution boundary for the first E1 evaluation. The current proven path separates formation admission from the Home transport:

```text
explicit trusted scene-qualified managed request
  -> durable protected source and queue publication
  -> O0 explicit one-job execution
  -> formed Primary MEM
  -> Phase I-2 observation

SOUL Lab Home real conversation
  -> existing M2 / RelayCTX recall
  -> remembered-fact question
  -> Phase I-2 used-memory evidence
  -> Phase I-3 Correct when required
```

The earlier shorthand `real Home conversation -> O0` is not currently a verified formation path because UI-B0 sends no trusted scene qualification and ordinary heuristic fallback fails persistence closed. A follow-up must add a trusted server- or route-owned admission contract before direct Home-origin formation can be claimed.

This path is operator-driven. O0 does not poll, schedule retries, or create browser worker authority, and UI-B0 does not claim that the complete E1 flow is automated.

## Known limitations and separate slices

- multiple projected routes remain fail-closed; UI-B0 adds no route priority semantics,
- browser transcripts are process-local and non-durable,
- Home requests do not currently carry trusted scene-admission evidence and therefore do not reliably publish new Primary MEM work,
- the character-scoped Primary store requires explicit operator bootstrap before first apply,
- the current formation summary can combine user and assistant text without speaker-safe factual provenance,
- later generated answers can add unsupported details beyond retrieved evidence,
- static SOUL Lab serving remains separate,
- O0 local one-job runner is complete as an explicit operator-invoked one-shot boundary; O1 polling and retry scheduling remain separate,
- I1-GB durable-finalization publication is complete, while I1-GC replay/completion convergence, I1-GD cleanup, and I1-GE full crash validation remain separate,
- I-4 Forget/Hide and later memory governance remain separate,
- queue scanning, scheduling, worker supervision, and always-on operation remain separate,
- Secondary MEM and RelaySOUL proposal/intervention/rollback remain separate,
- TTS, audio, avatar, Live2D, ASR, and peer transport remain separate.

## Proof boundary

UI-B0 proves a bounded browser client can exercise the existing real RelayLM text and later-memory-recall path with safe local session controls and explicit source separation. Combined with existing I-1/I-2/I-3 and the completed O0 one-job boundary, it enabled the first hands-on E1 evaluation and exposed the remaining scene-admission, store-bootstrap, provenance, and response-grounding gaps.

It does not prove direct Home-origin Primary MEM formation, automatic queue polling or retry scheduling, I1-GC restart replay/completion convergence, I1-GE full crash recovery, durable transcripts, broad memory governance, evidence-grounded generation, or long-running production operation.
