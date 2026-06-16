# RelayLM Runtime Operational Requirements

## Purpose

This document defines cross-cutting runtime requirements that are not owned by a single semantic pipeline component: reliability, fallback, observability, privacy, compatibility, and product-level acceptance.

Component ownership remains defined by [Pipeline Responsibility Design](pipeline_responsibility_design.md). Runtime layering and modes remain defined by [Runtime Architecture](runtime_architecture.md). Product experience goals remain defined by [AI Character Product Principles](ai_character_product_principles.md).

## Reliability baseline

RelayLM must preserve a usable OpenAI-compatible path even when optional context features are unavailable.

The strongest baseline is:

```text
valid compatible request
  -> route resolution
  -> backend adapter forwarding
  -> streaming or non-streaming compatible response
```

Optional memory, retrieval, persona-source, or context-enrichment failures should not crash the process or corrupt the request. RelayRUN owns runtime fallback/recovery orchestration and records the resulting node states, reasons, checkpoints, and trace projections.

## Fallback policy

Fallback is normal product behavior, not an exceptional afterthought.

Conceptual degradation order:

```text
memory_full
  -> memory_light
  -> pass_through
  -> compatible backend error or recovery state
```

This order is conditional, not unconditional. A fallback may run only when it preserves request compatibility and all applicable policy boundaries.

Required invariants:

- fallback must not bypass RelaySCN safety or persistence policy,
- fallback must not bypass RelayINT ambiguity or clarification blocks,
- fallback must not reintroduce client history or instructions excluded by authority contracts,
- fallback must not silently change tool, structured-output, multimodal, or streaming semantics,
- fallback must not convert untrusted memory or repaired context into trusted prompt content,
- fallback must not mutate MEM or SOUL merely to keep a request running,
- a safe compatible error is preferable to an unsafe semantic downgrade.

Typical runtime reasons include:

- `route_not_found`,
- `backend_unavailable`,
- `profile_load_failed`,
- `memory_store_unavailable`,
- `context_budget_exceeded`,
- `compiler_error`,
- `retrieval_timeout`,
- `streaming_forward_error`,
- `request_incompatible_with_repack`,
- `policy_blocked`,
- `waiting_user_required`.

Reason names should be typed/stable enough for smoke tests and operational analysis. Raw exception text should not become a public contract.

## Failure-domain behavior

### Optional enrichment failure

Examples: memory store unavailable, retrieval timeout, optional profile block missing.

Expected behavior:

- omit or downgrade only the optional enrichment when policy allows,
- preserve latest input and required stable blocks,
- record the omitted block and fallback reason,
- continue through the normal adapter path.

### Context compile failure

Expected behavior:

- fail closed for malformed or unsafe compiled context,
- use a lower mode only when compatibility and authority gates permit it,
- never send a partially trusted mixed payload merely because compilation failed.

### Backend failure

Expected behavior:

- return a compatible backend-facing error or enter the defined recovery path,
- preserve RelayRUN checkpoint/trace evidence,
- do not fabricate a successful assistant answer.

### Partial stream failure

Expected behavior:

- preserve already emitted valid visible chunks,
- block incomplete internal/update candidates,
- record partial-stream state and recovery metadata,
- do not replay or duplicate emitted chunks during recovery.

## OpenAI-compatible surface

The runtime baseline supports:

- `GET /v1/models`,
- `POST /v1/chat/completions`,
- streaming and non-streaming responses,
- route model mapping,
- common sampling fields when the backend supports them.

Tool calls, structured output, vision/multimodal content, and other compatibility-sensitive request shapes must be preserved or explicitly blocked by preflight. They must not be casually repacked as ordinary text.

The primary local setup and dedicated integration/authority documents define the detailed frontend boundary:

- [OpenWebUI + LM Studio MVP](../openwebui_lmstudio_mvp.md),
- [Open-LLM-VTuber Integration Design](open_llm_vtuber_integration.md),
- [Client History Authority Contract](client_history_authority_contract.md),
- [Client Instruction Authority Contract](client_instruction_authority_contract.md).

## Observability contract

RelayLM should expose product-relevant decisions without leaking prompt or memory content by default.

Recommended typed fields include:

- request/run/turn identifiers,
- route and backend identifiers,
- character, session, memory, and cache namespace identifiers,
- requested/applied mode,
- stream flag,
- compiler/retrieval node status,
- selected block identifiers or counts,
- approximate token/input size,
- fallback or blocked reasons,
- retrieved-memory and candidate counts,
- checkpoint, lineage, and schema versions.

Default audit and trace projections must remain content-free:

- do not include raw user messages,
- do not include backend payloads,
- do not include prompt text,
- do not include memory/snippet/page bodies,
- do not include final response text unless a separate explicitly approved diagnostic surface requires it,
- do not copy arbitrary nested artifacts into audit records,
- use typed allowlisted projections rather than generic recursive sanitization.

Diagnostics must not be inserted into stable prompt prefixes. Operational metadata is machine evidence, not backend context.

## Privacy and local-first posture

RelayLM handles persona sources, conversation evidence, relationship state, and memory. The default posture is:

- local-first storage,
- explicit memory/cache namespaces,
- no external memory service required for the base product,
- no hidden remote telemetry,
- backend URLs visible in configuration,
- clear deletion/forgetting paths for local memory,
- minimal content exposure in logs and traces.

When a hosted or remote backend is configured, documentation and UI should make clear that selected compiled context is sent to that backend as part of the request.

Namespace isolation is a privacy boundary. Character, user/viewer, room, scene, session, memory, and cache scopes must not be mixed merely because they share one RelayLM process.

## Acceptance criteria

Runtime acceptance should cover more than unit-level correctness.

### Compatibility

- frontend can point its OpenAI-compatible base URL to RelayLM,
- model routes resolve predictably,
- streaming chunks are forwarded without full-response buffering,
- non-streaming responses remain compatible,
- supported sampling fields and headers are preserved where practical.

### Persona/context

- stable persona and output-policy blocks precede dynamic memory/RAG,
- latest user input remains preserved,
- memory evidence cannot replace identity authority,
- internal tags and diagnostics do not leak into ordinary output.

### Memory safety

- missing optional memory degrades cleanly,
- low-confidence or contradictory candidates remain inactive/held,
- retrieval does not mutate memory,
- persistence is blocked in restricted scenes or waiting-user states.

### Latency

- pass-through overhead remains small,
- realtime profiles avoid heavy synchronous retrieval by default,
- streaming can begin without waiting for RelaySLP or post-response extraction,
- first-token, first-sentence, and first-TTS-enqueue timings can be measured separately.

### Recovery and idempotency

- partial failures do not duplicate visible chunks or writes,
- retries/resume use RelayRUN state and idempotency rules,
- repaired context remains untrusted until required confirmation,
- safe blocked/error outcomes remain observable.

## Operational ownership

```text
RelaySCN
  owns scene, safety, memory-scope, expression, and persistence policy

RelayINT
  owns semantic proceed/block, ambiguity, and clarification decisions

RelayMEM / RelaySLP
  own retrieval evidence and deferred memory compilation boundaries

RelayCTX
  owns prompt construction, selection, and token-budget degradation

RelayRUN
  owns execution order, fallback/recovery, node states, checkpoints,
  lineage, retry/idempotency, and trace projection

Adapters
  own transport compatibility and backend-specific forwarding
```

No operational fallback may blur these ownership boundaries.

## Non-goals

This document does not define:

- the current implementation phase,
- a historical MVP roadmap,
- memory schema details,
- scene-policy schema details,
- prompt block layout details,
- backend-specific KV-cache behavior.

Those remain in their dedicated current documents.
