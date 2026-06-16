# RelayLM Runtime Operational Requirements

## Purpose

This document defines cross-cutting runtime requirements that are not owned by a single semantic pipeline component: reliability, fallback, observability, privacy, compatibility, latency, and product-level acceptance.

Use [Pipeline Responsibility Design](pipeline_responsibility_design.md) for ownership, [Runtime Architecture](runtime_architecture.md) for runtime layering and modes, [Pipeline Implementation Plan](pipeline_implementation_plan.md) for current status, [AI Character Product Principles](ai_character_product_principles.md) for product goals, and [Current / Target / Migration Guide](current_target_migration_guide.md) for interpretation.

## Current implemented boundary

Current runtime provides:

- OpenAI-compatible route resolution and backend forwarding,
- current profile compilation and selected RelayCTX Repack phases,
- typed `CompileApplyDecision` plus the content-free `mvp-ctx-apply-0` compile-decision diagnostics artifact,
- request-level diagnostics and checkpoint-like RelayRUN artifacts,
- a default-off no-instruction history-exclusion apply contract,
- a backend-forward gate for explicitly requested actual apply.

Current runtime does not yet provide:

- complete per-node RelayRUN orchestration,
- a full route-authority-aware managed fallback taxonomy,
- explicit forwarded-payload-source typing across all compile paths,
- Stream Unpack,
- idempotent partial-stream recovery.

Target requirements below remain requirements even when the complete runtime path is not yet implemented.

## Reliability baseline

RelayLM must preserve a usable OpenAI-compatible path when optional context features are unavailable, provided doing so does not change route authority or violate compatibility gates.

The strongest baseline is:

```text
valid compatible request
  -> route resolution
  -> backend adapter forwarding
  -> streaming or non-streaming compatible response
```

Optional memory, retrieval, persona-source, or context-enrichment failures should not crash the process or corrupt a request. RelayRUN owns target runtime fallback/recovery orchestration and records resulting node states, reasons, checkpoints, and content-free trace projections.

## Route-aware fallback policy

Fallback is route-specific. `pass_through` is an explicit delegated route, not the generic final step of managed-route degradation.

### Explicit delegated `pass_through`

```text
explicit route delegation
  -> preserve compatible client messages
  -> backend forwarding
  -> compatible transport error when forwarding cannot continue
```

The client owns the delegated context authority for this route.

### RelayLM-managed route

```text
full RelayLM-managed payload
  -> reduced RelayLM-managed payload
  -> authority-safe minimal RelayLM-managed payload
  -> otherwise blocked/error outcome
```

A managed compilation or apply failure must not restore excluded prior client history or raw client system/developer messages.

Required invariants:

- fallback must not bypass RelaySCN safety or persistence policy,
- fallback must not bypass RelayINT ambiguity or clarification blocks,
- fallback must not reintroduce client history or instructions excluded by authority contracts,
- fallback must not silently change tool, structured-output, multimodal, or streaming semantics,
- fallback must not convert untrusted memory or repaired context into trusted prompt content,
- fallback must not mutate MEM or SOUL merely to keep a request running,
- a safe compatible blocked/error result is preferable to an authority-changing downgrade.

The older conceptual chain `memory_full -> memory_light -> pass_through` may describe historical mode degradation only. It must not be interpreted as managed-route authority fallback. `pass_through` requires explicit route delegation.

## Current no-instruction apply failure behavior

When all of these are true:

- `client_history_exclusion_apply_enabled=true`,
- `client_history_exclusion_apply_dry_run_only=false`,
- route mode is managed,

backend forwarding requires an exact successful `client_history_exclusion_apply.v0` result with:

```text
status = applied
payload_mutation_applied = true
forwarded_payload present
```

The following stop forwarding:

- missing result,
- blocked result,
- skipped result on a managed route,
- `ready` candidate-only result,
- any otherwise non-applied result.

Runtime exceptions are converted into a bounded `blocked` result. `client_history_exclusion_apply.v0` does not currently define a separate `failed` status.

Explicit `pass_through` routes are exempt. This current gate covers only the no-instruction slice.

## Stable runtime reason posture

Operational reasons should be typed and stable enough for smoke tests and runtime analysis. Raw exception text must not become a public contract.

Representative reason IDs include:

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
- `waiting_user_required`,
- `client_history_exclusion_apply_result_missing`,
- `client_history_exclusion_apply_blocked`,
- `client_history_exclusion_apply_preparation_failed`.

These names are examples of stable operational classes, not permission to emit arbitrary freeform exception messages.

## Failure-domain behavior

### Optional enrichment failure

Examples include memory-store unavailability, retrieval timeout, or a missing optional profile block.

Expected behavior:

- omit or reduce only the optional enrichment when policy allows,
- preserve validated current input and required approved anchors,
- record typed reason IDs,
- continue through the normal adapter path.

### Context compile failure

Expected behavior:

- reject malformed or mixed-authority payloads,
- use a reduced managed payload only when authority and compatibility checks pass,
- never restore raw prior client context on a managed route,
- never send a partially trusted mixed payload merely because compilation failed.

### Backend failure

Expected behavior:

- return a compatible backend-facing/transport error or enter the defined recovery state,
- preserve content-free RelayRUN checkpoint/trace evidence,
- do not fabricate a successful assistant answer.

### Partial stream failure — target requirement

Expected behavior:

- preserve already emitted valid visible chunks,
- block incomplete internal/update candidates,
- record partial-stream state and recovery metadata,
- do not replay or duplicate emitted chunks during recovery.

Complete partial-stream recovery is not current implementation.

## OpenAI-compatible surface

Current baseline supports:

- `GET /v1/models`,
- `POST /v1/chat/completions`,
- streaming and non-streaming forwarding,
- route model mapping,
- common request and sampling fields when the backend supports them.

Tool calls, structured output, vision/multimodal content, and other compatibility-sensitive shapes must be preserved or explicitly blocked by preflight. They must not be flattened or casually repacked as ordinary text.

Primary frontend and authority references:

- [OpenWebUI + LM Studio MVP](../openwebui_lmstudio_mvp.md),
- [Open-LLM-VTuber Integration Design](open_llm_vtuber_integration.md),
- [Client History Authority Contract](client_history_authority_contract.md),
- [Client Instruction Authority Contract](client_instruction_authority_contract.md),
- [Managed-Route Fallback Authority Contract](managed_route_fallback_contract.md).

## Observability contract

RelayLM should expose product-relevant decisions without leaking prompt, user, persona, or memory content by default.

Recommended typed fields include:

- request/run/turn identifier presence or approved IDs,
- route and backend identifiers/classes,
- character, session, memory, and cache namespace presence/classes,
- requested/applied mode,
- stream flag,
- compiler/retrieval/node status,
- selected block identifiers or counts,
- approximate token/input size,
- fallback or blocked reason IDs,
- retrieved-memory and candidate counts,
- checkpoint, lineage, and schema versions,
- payload mutation and candidate-presence booleans.

Default persisted audit and trace projections must remain content-free and use typed allowlists.

They must not include:

- raw user/client messages,
- backend payloads,
- prompt text or compiled block bodies,
- memory/snippet/page bodies,
- scene semantic values such as role, setting, task, participant, or constraint text,
- persona-source bodies,
- final response text,
- arbitrary nested runtime artifacts,
- secret-bearing paths or URLs.

Runtime-private payload candidates may contain content required for execution but remain request-local or in explicitly protected storage.

Diagnostics and operational metadata must not be inserted into stable prompt prefixes. Machine evidence is not backend context.

## Privacy and local-first posture

RelayLM handles persona sources, conversation evidence, relationship state, and memory. The default posture is:

- local-first storage,
- explicit memory/cache namespaces,
- no external memory service required for the base product,
- no hidden remote telemetry,
- backend URLs visible in configuration,
- clear deletion/forgetting paths for local memory and caches,
- minimal content exposure in logs and traces,
- no namespace mixing merely because one process serves multiple characters, users, rooms, scenes, or sessions.

When a hosted or remote backend is configured, documentation and UI should make clear that selected compiled context is sent to that backend as part of the request.

Namespace isolation is a privacy boundary. Character, user/viewer, room, scene, session, memory, and cache scopes must not be mixed without an explicit validated relationship.

## Acceptance criteria

Runtime acceptance covers more than unit-level correctness.

### Compatibility

- a frontend can point its OpenAI-compatible base URL to RelayLM,
- model routes resolve predictably,
- current streaming chunks are forwarded without full-response buffering,
- non-streaming responses remain compatible,
- supported sampling fields and headers are preserved where practical,
- unsupported compatibility-sensitive transactions are explicitly blocked rather than silently rewritten.

### Persona and context

- approved durable persona and output-policy anchors precede lower-authority evidence,
- latest validated user content remains present,
- memory evidence cannot replace identity authority,
- internal tags, artifacts, and diagnostics do not leak into ordinary output.

### Memory and persistence

- missing optional memory degrades cleanly,
- low-confidence, blocked, or contradictory candidates remain inactive/held,
- Retrieval remains read-only,
- persistence is blocked in restricted scenes or waiting-user states,
- actual RelaySLP and RelaySOUL writes require separate future gates.

### Latency

- pass-through overhead remains small,
- realtime profiles avoid heavy synchronous retrieval by default,
- streaming can begin without waiting for RelaySLP or post-response extraction,
- first-token, first-sentence, and first-TTS-enqueue timings can be measured separately,
- ordinary requests should not eagerly allocate or serialize the complete recovery chain when no recovery-relevant condition exists after Phase 5-D2.

### Recovery and idempotency — target acceptance

- partial failures do not duplicate visible chunks or writes,
- retries/resume use RelayRUN state and idempotency rules,
- repaired context remains untrusted until required confirmation,
- safe blocked/error outcomes remain observable,
- checkpoint persistence is not misrepresented as proof that resume is supported.

## Operational ownership

```text
RelaySCN
  owns scene, safety, memory-scope, expression, and persistence policy

RelayINT
  owns semantic proceed/block, ambiguity, clarification, and retrieval decisions

RelayMEM Retrieval
  owns read-only current-answer evidence

RelaySLP
  owns deferred memory/SOUL candidate compilation and gated write preparation

RelayCTX
  owns context construction, selection, token degradation, Repack, and Unpack

RelayRUN
  owns execution order, fallback/recovery, node states, checkpoints,
  lineage, retry/idempotency, and trace projection

Adapters
  own transport compatibility and backend-specific forwarding
```

No operational fallback may blur or transfer these ownership boundaries.

## Non-goals

This document does not define:

- the current implementation phase in detail,
- a historical MVP roadmap,
- memory schema details,
- scene-policy schema details,
- prompt block layout details,
- backend-specific KV-cache behavior,
- concrete TTS or avatar engine implementation.

Those remain in their dedicated current, target, integration, and historical documents.
