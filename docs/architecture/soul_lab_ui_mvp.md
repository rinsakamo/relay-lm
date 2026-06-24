---
relaylm_doc_type: implementation_plan
relaylm_authority: soul_lab_ui_product_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - SOUL Lab UI slice lands
  - management or observation API changes
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
  - integration_i1_primary_mem_two_turn_recall.md
---
# AITuber SOUL Lab UI MVP

## Purpose

AITuber SOUL Lab is the browser-based local UI that turns RelayLM's runtime value into an understandable product experience.

It is not a generic settings panel. Its MVP lets a user see a character:

1. be initialized or adopted,
2. live in a Home space,
3. communicate with an external API or another RelayLM character,
4. bring that experience back as formed, held, or blocked memory outcomes,
5. inspect real results in Lab Observation,
6. enter Pod / SOUL Intervention only when the user intentionally changes the character core.

The product loop is:

```text
create or adopt
  -> live in Home
  -> communicate
  -> return with experience
  -> observe real memory formation in Lab
  -> explicitly correct memory when needed
  -> intervene in Pod only for SOUL-level change
  -> live in Home again
```

The MVP should prove:

> A RelayLM character can have a stable SOUL, separate MEM, managed context, and relationship continuity that the user can experience without needing to understand the whole runtime first.

## Current implementation status

```text
UI-A0 / UI-A1 shell and Home: complete
UI-A2 Adoption preview: complete
UI-A3 Communication preview: complete
UI-A4 Pod preview: complete
UI-A5 Memory Inspector preview: complete
UI-A6 shared shell and Settings: complete
UI-A7 loopback-only settings/characters projection: complete
Phase I-2 real Lab Observation: complete
Phase I-3 auditable Correct: next
Static UI bundle serving from RelayLM: pending
TTS/audio/avatar Runtime execution: pending
```

Phase I-2 replaces the Observation route's implicit mock-only behavior with an explicit real-data-first state machine. The legacy Memory Inspector preview remains available only as a user-selected local preview fallback and is never mixed with server data.

## Deployment shape

The target distributable UI is a local browser app served by RelayLM:

```text
RelayLM Core
  localhost API server

AITuber SOUL Lab UI
  browser-based local web app

Backend
  LM Studio / OpenAI-compatible API
```

Target local routes:

```text
http://127.0.0.1:8090/v1/*
  OpenAI-compatible frontend/backend API

http://127.0.0.1:8090/lab
  AITuber SOUL Lab UI

http://127.0.0.1:8090/lab/api/*
  SOUL Lab management and observation API
```

Development may use Vite separately. Static bundle serving from RelayLM is not completed by Phase I-2.

## Visual and interaction layers

The UI has light and dark modes.

- Home remains warm and approachable.
- Lab is an engineering workspace with clear source and status labels.
- Pod uses the strongest visual contrast because it is the only SOUL-level intervention area.

SOUL Lab has three intervention-depth layers plus communication:

```text
Home
  daily conversation and character presence

Lab Observation
  observe runtime state, memory formation, SLP, RelayRUN, and RelayCTX evidence

Pod / SOUL Intervention
  propose, compare, apply, hold, discard, and rollback SOUL-level changes

Communication / PC Chat
  external API or RelayLM peer communication
```

The layers express authority depth:

```text
Home
  live with the character

Lab Observation
  inspect state and experiences without changing authority

Memory Correct
  explicit bounded memory intervention with audit

Pod
  intentional SOUL-level intervention
```

## Character scope

The browser may maintain one active character per UI instance. The server must not use one global active character.

Phase I-2 requires every observation request to carry:

```text
character_id
+ explicit memory namespace
```

The namespace is obtained from the server-owned UI-A7 character projection. The browser must not construct store paths or infer a namespace from local mock records.

Character switching requirements:

- start a new request generation,
- abort prior requests with `AbortController`,
- discard delayed responses from the previous generation,
- validate that every response character and namespace match the active request,
- never render old-character evidence under the new character.

## Required screens

### 1. First Launch / No Character

A built-in Lab Assistant may guide the user into:

- creating a new character,
- adopting an existing RelaySOUL persona source set,
- importing `SOUL.md` and companion sources,
- learning the UI.

The Lab Assistant is a normal RelayLM character, not a privileged administrator. It must not access raw other-character SOUL/MEM, credentials, traces, unapproved configuration changes, or arbitrary filesystem content.

Durable character registry mutation remains outside Phase I-2.

### 2. Character Selector

Requirements:

- multiple registered characters,
- one active character per browser instance,
- character switching,
- per-character SOUL, MEM, relationship, observation, and rollback separation,
- restored browser preference where safe,
- no server-global active character.

Deletion, cloning, shared MEM, and SOUL inheritance remain later work.

### 3. Home

Home is the daily living surface. It may show chat, streaming response, stop response, current character, SOUL version/stability, RelayLM/backend status, current mode, and entry points to Communication and Lab.

Home must not expose raw prompt internals or compiled context by default.

### 4. Communication

Communication demonstrates that memory is not equivalent to chat history.

The user selects a peer, starts communication, requests soft stop, and uses emergency stop only when needed. The character controls what to say, whether to reply, natural stopping, and later interpretation.

Actual peer transport remains Runtime MVP work. Current UI may preview the product flow but must label mock data explicitly.

### 5. Lab Observation — real data connected

Lab Observation is not a raw debugger and not a mandatory approval queue. Ordinary safe memory forms autonomously when RelayMEM and RelaySLP gates allow it.

Phase I-2 real panels include:

- latest completed managed run status,
- formed/held/blocked counts,
- recently formed validated Primary memories,
- held and blocked outcome items,
- memories actually used in the latest completed response,
- RelaySLP status,
- RelayRUN status,
- RelayCTX Repack status,
- RelayCTX Unpack observation status,
- bounded recovery or blocked reasons,
- completion time and duration.

The real observation source is labeled:

```text
Source: RelayLM runtime
```

The explicit preview fallback is labeled:

```text
Source: Local preview data
```

The two sources must never be silently combined.

#### Real read API

```text
GET /lab/api/characters/{character_id}/lab/last-run?namespace=...
GET /lab/api/characters/{character_id}/memory/recent?namespace=...&limit=...
GET /lab/api/characters/{character_id}/memory/held?namespace=...&limit=...
GET /lab/api/characters/{character_id}/lab/last-run/memory/used?namespace=...
```

All routes are:

- read-only,
- loopback configured-host plus actual-peer protected,
- `Cache-Control: no-store`,
- exact versioned schema,
- bounded,
- character/namespace scoped,
- server-source marked.

#### Observation states

The browser implements explicit states:

- loading,
- real server-owned data,
- empty but valid,
- access refused,
- schema invalid,
- runtime unavailable,
- explicit local-preview fallback.

A server error does not automatically merge or replace the view with mock data. The user explicitly selects preview mode.

#### Browser validation

The browser rejects:

- missing keys,
- unexpected keys,
- wrong schema or source marker,
- wrong types or enums,
- oversized summary/title/reason lists,
- invalid opaque IDs,
- mixed character or namespace,
- used-memory evidence for a different latest run,
- used items when backend-bound inclusion was not proven.

React text rendering is used. Observation content is never inserted as HTML.

#### Read-only action boundary

The following controls remain disabled in real mode and are labeled as future work:

- correct,
- forget,
- pin/unpin,
- merge,
- apply held,
- discard held.

Phase I-2 implements no POST/PATCH/PUT/DELETE mutation. Phase I-3 adds only auditable Correct.

### 6. Pod / SOUL Intervention

Pod remains the intentional SOUL intervention concept. It may preview candidate, diff, comparison, apply/hold/discard/rollback flows, but no RelaySOUL mutation is implemented by Phase I-2.

Memory correction belongs to the memory-operation boundary, not Pod-level SOUL mutation.

## Management and observation API boundary

UI-A7 existing routes remain content-free:

```text
GET /lab/api/settings
GET /lab/api/characters
```

Phase I-2 observation routes may expose only limited, bounded, validated content:

- memory title when safely available,
- bounded memory summary,
- user-facing status,
- confidence/scope label when authoritative,
- bounded observation/reason labels.

They must not expose:

- raw SOUL,
- full MEM pages,
- raw protected source,
- full transcript or prompt,
- backend payload,
- credentials,
- filesystem paths,
- raw trace or exception,
- queue identity,
- digests or lease metadata,
- arbitrary serialized objects.

## Loopback security

A Lab route succeeds only when:

```text
validated listen host is loopback
AND
actual ASGI peer is loopback
```

Host, Origin, forwarded headers, browser claims, and query parameters are not locality proof.

Core `/healthz` and `/v1/models` behavior remains unchanged.

## CTX and EMO boundary

RelayCTX Repack is the backend-bound context owner. Phase I-2 observes whether selected memory was actually included; it does not infer use from a candidate list or frontend history.

RelayCTX Unpack remains the return-side separation boundary. If no durable/current evidence exists for an Unpack status, the Lab reports `not_observed` rather than inventing success.

RelayEMO remains optional presentation metadata and is not a substitute for safety, memory, or protocol authority.

## Settings boundary

Settings remains minimal and server-projected. Browser code does not directly read configuration files or credentials.

Security defaults:

- bind to `127.0.0.1` by default,
- remote access off by default,
- API keys stay server-side,
- browser does not directly read or write SOUL/MEM files,
- raw inspection remains explicit and gated.

## Phase I-3 next boundary

The next UI slice is one auditable Correct operation:

```text
select one real observed Primary memory
  -> enter bounded correction
  -> review exact current representation and scope
  -> submit explicit Correct request
  -> display applied / refused / conflict / unavailable result
  -> later ordinary response demonstrates corrected retrieval
```

The UI must preserve original and corrected representations as distinct audit concepts. Correct must not silently become replace-all, forget, pin, merge, held apply, or SOUL edit.

## Completion boundary

Phase I-2 UI completion means:

- real runtime data is visible in Lab Observation,
- source ownership is explicit,
- empty/refused/invalid/unavailable/fallback states are distinct,
- stale responses are discarded on character switch,
- exact browser validation rejects malformed or mixed-scope responses,
- real and mock data are not mixed,
- mutation controls cannot change storage,
- raw protected/internal content is not exposed.

It does not mean static bundle serving, actual Communication transport, TTS/audio/avatar execution, RelaySOUL intervention, or memory mutation is complete.

<!-- phase-i3-auditable-primary-mem-correct -->
## Phase I-3 auditable Primary MEM Correct — complete (2026-06-24)

Phase I-3 completes the first real observe/correct/retrieve loop. A formed Primary MEM observed through Phase I-2 can be corrected through read-only preflight, bounded semantic diff, explicit short-lived-token apply, immutable successor-page publication through the existing M3e boundary, canonical M3f/M3g index/log convergence, and immutable audit receipt finalization. Existing M2 retrieval resolves only the corrected current revision and existing RelayCTX injection remains the sole prompt path.

Character/namespace isolation, stable logical memory identity, no-clobber publication, exact operation idempotency, one-winner revision fencing, crash recovery, and historical used-memory integrity are preserved. Correction reason, audit receipt, paths, digests, lineage, queue/lease state, and prior full pages are not retrieval inputs or public prompt content.

Authority and exact contracts: `docs/architecture/phase_i3_auditable_primary_mem_correct.md`.

Still separate and unresolved: the I1-G process-exit window after visible-response delivery but before background-finalizer protected-source and B2 queue publication. Phase I-3 does not implement forget, pin/unpin, merge, held apply/discard, Secondary MEM consolidation, RelaySOUL mutation, queue scanner/scheduler/daemon, static UI serving, or TTS/audio/avatar execution.
