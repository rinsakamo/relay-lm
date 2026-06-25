---
relaylm_doc_type: implementation_plan
relaylm_authority: soul_lab_ui_product_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - SOUL Lab UI slice lands
  - management, observation, correction, or conversation API changes
  - a browser state becomes server-owned
  - mutation boundary changes
relaylm_not_authoritative_for:
  - RelayMEM persistence semantics
  - RelaySLP queue lifecycle
  - RelaySOUL apply contracts
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - soul_lab_runtime_mvp.md
  - soul_lab_ui_a7_management_projection_handoff.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - soul_lab_ui_b0_real_home_conversation.md
  - o0_local_one_job_runner.md
  - integration_i1_primary_mem_two_turn_recall.md
---
# AITuber SOUL Lab UI MVP

## Purpose

AITuber SOUL Lab is the browser-based local UI that turns RelayLM character continuity into an understandable product experience. It is not a generic settings panel or a second runtime authority.

The product loop is:

```text
create or adopt
  -> live and converse in Home
  -> existing RelayLM memory retrieval and context injection
  -> deferred experience processing
  -> observe formed / held / blocked outcomes in Lab
  -> explicitly correct or later govern memory
  -> intervene in Pod only for SOUL-level change
  -> begin a fresh Home conversation
```

The MVP should prove that a RelayLM character can expose stable SOUL, separate MEM, managed context, and relationship continuity without requiring the user to understand every runtime component.

## Current implementation status

```text
UI-A0 / UI-A1 shell and original Home: complete
UI-A2 Adoption preview: complete
UI-A3 Communication preview: complete
UI-A4 Pod preview: complete
UI-A5 Memory Inspector preview: complete
UI-A6 shared shell and Settings: complete
UI-A7 loopback-only settings/characters projection: complete
Phase I-2 real Lab Observation: complete
Phase I-3 auditable Correct: complete
UI-B0 real Home conversation: complete
O0 explicit local one-job runner: complete outside browser authority
Static UI bundle serving from RelayLM: pending
Communication peer transport: pending
RelaySOUL apply / rollback: pending
TTS/audio/avatar Runtime execution: pending
```

UI-B0 replaces the Home mock-only submit path with a bounded client of the existing RelayLM Chat Completions path. Local Preview remains available only through explicit user selection and is never mixed with a real conversation session.

## Deployment shape

Current development topology:

```text
SOUL Lab Vite http://127.0.0.1:5173/lab/
  -> /lab/api/* and /v1/* proxy
RelayLM http://127.0.0.1:8090
  -> configured backend
LM Studio http://127.0.0.1:1234/v1
```

Target packaged topology remains:

```text
RelayLM Core
  localhost API server
  /v1/*
  /lab/api/*
  future static /lab bundle
```

Vite proxies `/lab/api` and `/v1` to loopback RelayLM with `changeOrigin: false`. The browser does not connect directly to LM Studio, receive backend credentials, or add broad CORS access.

## Authority layers

```text
Home
  converse through existing RelayLM route, M2, RelayCTX, and backend authority

Lab Observation
  inspect bounded runtime and memory evidence without changing authority

Memory Correct
  explicit revision-fenced memory intervention with audit

Pod
  future intentional RelaySOUL intervention
```

SOUL Lab does not own:

- backend model IDs,
- memory namespaces or store paths,
- SOUL/system/developer prompts,
- compiled RelayCTX,
- credentials,
- queue or lease identities,
- RelayMEM persistence semantics,
- worker execution or process lifecycle.

## Character scope

The browser maintains one active character display preference per UI instance. The server never uses one global active character.

Exact `/lab/api/characters` projections are retained by character ID. Display-only `CharacterSummary` values are not conversation authority.

For Home conversation:

- zero projected routes -> unavailable,
- one distinct non-empty projected route -> available,
- multiple distinct routes -> `ambiguous_route`,
- browser code does not choose backend IDs or infer route priority.

For observation and correction, every request remains character and namespace scoped through server-owned projections and exact API contracts.

Character switching must abort or invalidate active requests and reject delayed responses, SSE chunks, errors, and finalizers from the prior character.

## Required screens

### First Launch / Adoption

A built-in Lab Assistant may guide creation, adoption, or persona-source import. It is a normal character, not a privileged administrator. Durable registry mutation remains separate.

### Character Selector

The selector changes the browser-active character. Character-specific Home sessions, observation state, memory evidence, and later governance operations remain isolated.

### Home — real text conversation connected

Home is the daily living surface. UI-B0 provides:

- current character and SOUL/configuration summary,
- explicit `REAL RUNTIME` and `LOCAL PREVIEW` modes,
- streaming enabled by default with a non-stream option,
- same-origin `POST /v1/chat/completions`,
- only server-projected route model plus standard user/assistant messages,
- bounded non-stream JSON validation,
- bounded UTF-8/SSE parsing,
- one assistant entry updated by content deltas,
- Stop that aborts only the browser request and preserves partial text,
- bounded failure reasons without raw backend content,
- Retry from the exact failed/stopped snapshot without duplicate user messages,
- New Conversation that resets only the current browser-local character/source session,
- per-character and per-source-mode histories,
- request ID, character ID, route model, session ID, and generation fencing,
- browser-only input/output/message/event/time bounds.

Home never renders raw prompt internals, compiled context, SOUL, MEM pages, protected source, credentials, traces, or queue metadata.

A real request body is limited to:

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

The browser adds no `system` or `developer` message. Existing RelayLM route/character resolution, M2 retrieval, RelayCTX injection, backend forwarding, and deferred RelaySLP processing remain unchanged.

### Communication

Communication remains a product-flow preview. Actual external or peer transport remains Runtime MVP work and must stay explicitly labeled as preview until connected.

### Lab Observation — real data connected

Phase I-2 provides real latest-run, formed/held/blocked, and used-memory evidence through loopback-only bounded APIs. Real and preview data are never combined automatically.

Used-memory evidence is the authority for whether durable memory entered the backend-bound context. Home does not expose raw prompts or infer memory use from visible response text.

### Memory Correct — real mutation connected

Phase I-3 provides read-only preflight, bounded semantic diff, short-lived confirmation token, revision-fenced apply, immutable successor publication, index/log convergence, durable audit receipt, and later corrected M2 retrieval.

Forget, Pin, Merge, Held Apply/Discard, Secondary MEM, and RelaySOUL mutation remain disabled or preview-only until their dedicated phases.

### Pod / SOUL Intervention

Pod remains the intentional SOUL-level concept. Candidate comparison, Hold, Discard, Apply, and Rollback are previews only. No RelaySOUL mutation is implied by UI-B0.

### Settings / Runtime Boundary

Settings uses content-free server projections from:

```text
GET /lab/api/settings
GET /lab/api/characters
```

Browser code does not read configuration files, credentials, source locations, or persona contents.

## Runtime status boundary

Real Home mode reuses only `/lab/api/settings` content-free configuration projection. It does not add network probes, credential reads, or direct endpoint checks.

Text conversation requires RelayLM and the Main LLM path. TTS, audio, avatar, and Live2D are not Home conversation completion gates.

Local Preview alone may show existing mock runtime and event data.

## Browser state boundary

Allowed browser-local state:

- route, language, theme,
- active character display preference,
- character × source-mode conversation session,
- draft,
- stream preference,
- current request controller and bounded snapshot.

Conversation transcripts are process-local and are not persisted to `localStorage`. Credentials, raw runtime objects, SOUL, MEM, compiled context, and protected source are never browser state.

## Security

Lab management, observation, and correction APIs remain loopback protected according to their dedicated contracts. Host, Origin, forwarded headers, browser claims, and query parameters are not locality proof.

Core `/v1/chat/completions` behavior is unchanged. UI-B0 uses same-origin fetch with `credentials: "same-origin"`, `cache: "no-store"`, and `AbortSignal`.

Raw backend response bodies, raw SSE, malformed JSON, exceptions, prompt contents, traces, and credentials are not shown in UI or console errors by the conversation transport.

React text rendering is used; `dangerouslySetInnerHTML` is not used.

## Validation

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run smoke:home-conversation
npm run build
```

The UI-B0 smoke verifies standard request shape, no authority-bearing extra fields, non-stream validation, SSE chunk/UTF-8 boundaries, role-only and empty deltas, `[DONE]`, finish reasons, abort, malformed/truncated/oversized streams, route ambiguity, source/session separation, reset behavior, and stale-generation rejection.

Repository regressions include Phase I-1, Phase I-2, Phase I-3, documentation boundary, and OpenWebUI/LM Studio proxy/configuration smokes.

## Current completion boundary

SOUL Lab currently proves:

- one real text conversation path from Home to RelayLM,
- real observation of durable memory outcomes and used-memory evidence,
- one real auditable Correct operation,
- browser-local fresh-conversation reset distinct from durable M2 memory,
- explicit separation between real runtime and preview data.

It does not prove:

- automatic queue polling, retry scheduling, or worker supervision,
- I1-G pre-enqueue durability,
- durable transcripts,
- Forget/Pin/Merge/Held governance,
- Secondary MEM consolidation,
- RelaySOUL apply/rollback,
- static bundle serving,
- Communication transport,
- TTS/audio/avatar/Live2D/ASR,
- public or remote binding.

For the first E1 evaluation, UI-B0 is combined with the completed O0 explicit one-job runner. The loop remains operator-driven; O1 automatic polling/retry scheduling and O2 supervision remain separate operations slices.
