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
  - soul_lab_ui_b1a_lifecycle_visibility.md
  - phase_i4e_forget_api_ui.md
  - phase_i4f_forget_validation.md
  - phase_i5b_pin_unpin_apply.md
  - phase_i7c_held_apply_discard_runtime.md
  - e1r1_trusted_home_scene_admission.md
  - e1r2_character_store_bootstrap.md
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
  -> explicitly correct, forget, pin, or govern held evidence
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
Phase I-4E loopback Forget API and SOUL Lab UI: complete
Phase I-4F Forget product validation: complete
UI-B1A read-only lifecycle and operation visibility: complete
Pin/Unpin runtime API/UI/ranking behavior: complete as I-5B
Held Apply/Discard runtime API/UI/durable evidence: complete as I-7C
E1-R1 route-owned trusted Home scene admission: complete outside browser authority
E1-R2 character-store bootstrap command: complete outside browser authority
O0 explicit local one-job runner: complete outside browser authority
Static UI bundle serving from RelayLM: pending
Communication peer transport: pending
RelaySOUL apply / rollback: pending
TTS/audio/avatar Runtime execution: pending
```

UI-B0 replaces the Home mock-only submit path with a bounded client of the existing RelayLM Chat Completions path. Local Preview remains available only through explicit user selection and is never mixed with a real conversation session.

I-4E adds the real Forget API/UI product surface. I-4F validates product completion, fresh conversation exclusion, security, crash/race behavior, and leakage boundaries over the existing I-4 authorities. UI-B1A adds read-only lifecycle and operation visibility. I-5B adds Pin / Unpin controls. I-7C adds Held Apply / Discard governance controls. These do not make the browser a broad mutation authority beyond the explicit loopback contracts.

E1-R1 enables trusted Home formation only through route-owned server configuration. The browser cannot self-assert trusted persistence policy. E1-R2 is an operator command and is not browser-owned.

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
  may become persistence-eligible only through E1-R1 route-owned server configuration

Lab Observation
  inspect bounded runtime and memory evidence without changing authority

Memory Correct
  explicit revision-fenced memory intervention with audit

Memory Forget
  explicit token-gated loopback lifecycle governance with audit

Memory Pin / Unpin
  explicit token-gated loopback governance with durable content-free evidence and ranking hint

Held Governance
  explicit Apply / Discard preflight and confirmation over already-held evidence

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
- worker execution or process lifecycle,
- route-owned trusted Home admission.

## Character scope

The browser maintains one active character display preference per UI instance. The server never uses one global active character.

Exact `/lab/api/characters` projections are retained by character ID. Display-only `CharacterSummary` values are not conversation authority.

For Home conversation:

- zero projected routes -> unavailable,
- one distinct non-empty projected route -> available,
- multiple distinct routes -> `ambiguous_route`,
- browser code does not choose backend IDs or infer route priority.

For observation, correction, Forget, Pin / Unpin, and Held Governance, every request remains character and namespace scoped through server-owned projections and exact API contracts.

Character switching must abort or invalidate active requests and reject delayed responses, SSE chunks, errors, and finalizers from the prior character.

## Required screens

### Home — real text conversation connected

Home is the daily living surface. UI-B0 provides real same-origin text conversation through `POST /v1/chat/completions` using only server-projected route model plus standard user/assistant messages.

Home never renders raw prompt internals, compiled context, SOUL, MEM pages, protected source, credentials, traces, or queue metadata.

The browser adds no `system` or `developer` message. Existing RelayLM route/character resolution, M2 retrieval, RelayCTX injection, backend forwarding, and deferred RelaySLP processing remain the runtime authority.

### Lab Observation — real data connected

Phase I-2 provides real latest-run, formed/held/blocked, and used-memory evidence through loopback-only bounded APIs. Real and preview data are never combined automatically.

Used-memory evidence is the authority for whether durable memory entered the backend-bound context. Home does not expose raw prompts or infer memory use from visible response text.

### Memory Correct — real mutation connected

Phase I-3 provides read-only preflight, bounded semantic diff, short-lived confirmation token, revision-fenced apply, immutable successor publication, index/log convergence, durable audit receipt, and later corrected M2 retrieval.

### Memory Forget — real mutation connected

Phase I-4E provides loopback-only Forget preflight, confirmation, apply, receipt/history, and SOUL Lab UI behavior over the existing I-4B/I-4C1/I-4C2/I-4D authority chain. Phase I-4F validates the product completion boundary.

### Memory Pin / Unpin — real governance connected

I-5B provides loopback-only Pin / Unpin preflight, explicit confirmation, apply, receipt/history, SOUL Lab UI behavior, durable content-free Pin evidence, and deterministic ranking hint. Pin state is orthogonal to lifecycle and never admits hidden, prepared, recovery-required, corrupt, cross-scope, or prior physical revisions.

### Held Governance — real decision connected

I-7C provides loopback-only Held Apply / Discard preflight, explicit confirmation, durable content-free decision evidence, history, and SOUL Lab UI behavior over already-held candidates. It does not start workers, schedulers, retry loops, C2, O1, or B3 lifecycle transitions from the UI.

### Pod / SOUL Intervention

Pod remains the intentional SOUL-level concept. Candidate comparison, Hold, Discard, Apply, and Rollback are previews only. No RelaySOUL mutation is implied by UI-B0, I-4E, I-4F, UI-B1A, I-5B, I-7C, E1-R1, or E1-R2.

## Security

Lab management, observation, correction, Forget, Pin / Unpin, and Held Governance APIs remain loopback protected according to their dedicated contracts. Host, Origin, forwarded headers, browser claims, and query parameters are not locality proof.

Core `/v1/chat/completions` behavior is unchanged except where route-owned E1-R1 configuration explicitly gates trusted Home admission. UI-B0 uses same-origin fetch with `credentials: "same-origin"`, `cache: "no-store"`, and `AbortSignal`.

Raw backend response bodies, raw SSE, malformed JSON, exceptions, prompt contents, traces, credentials, token claims, store paths, queue identities, and protected source bodies are not shown in UI or console errors.

React text rendering is used; `dangerouslySetInnerHTML` is not used.

## Current completion boundary

SOUL Lab currently proves:

- one real text conversation path from Home to RelayLM,
- real observation of durable memory outcomes and used-memory evidence,
- one real auditable Correct operation,
- one real explicit Forget API/UI path plus product-completion validation,
- one real explicit Pin / Unpin API/UI path plus ranking-hint behavior,
- one real explicit Held Apply / Discard governance API/UI path over held evidence,
- read-only lifecycle and operation visibility,
- browser-local fresh-conversation reset distinct from durable M2 memory,
- explicit separation between real runtime and preview data.

It does not prove:

- automatic queue polling, retry scheduling, or worker supervision,
- durable transcripts,
- Merge/Supersession runtime apply,
- Secondary MEM consolidation,
- RelaySOUL apply/rollback,
- static bundle serving,
- Communication transport,
- TTS/audio/avatar/Live2D/ASR,
- public or remote binding.

For MVP evaluation, UI-B0 is combined with the completed O0 explicit one-job runner, completed O1D1/O1D2/O1E/O1F caller-invoked local scheduler boundary, E1-R1 route-owned trusted Home admission when enabled, and E1-R2 explicit character-store bootstrap. The loop remains non-supervised unless a later O2/O3 phase explicitly proves supervised or always-on operation is required.
