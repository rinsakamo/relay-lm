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
- default-off `client_history_exclusion_apply.v0` no-instruction managed apply,
- default-off `client_history_exclusion_apply.v1` explicit-provenance instruction-bearing managed apply,
- an exact backend-forward gate for intentionally requested actual apply,
- strict read-only instruction-cache lookup and C4b content-free diagnostics projection,
- default-off trusted runtime-private typed-parse and cache-writer plumbing,
- default-compatible streaming plus Phase 5.5-B2 gated suppression and C0-C4 handoff metadata construction,
- Phase 6 durable enqueue through B2,
- RelayMEM direct/helper persistence primitives through M3h,
- SOUL Lab UI-A7 loopback-only settings/characters read projections.

Current runtime does not yet provide:

- complete per-node RelayRUN orchestration,
- a full route-authority-aware managed fallback taxonomy,
- explicit forwarded-payload-source typing across all compile paths,
- active tool-chain reconstruction,
- a trusted backend-response instruction-control artifact producer,
- semantic RelaySCN apply from cached interpretation,
- generalized partial-stream recovery,
- Phase 6 queue lifecycle and worker execution,
- ordinary-runtime Primary MEM formation and later-turn recall,
- TTS/audio/avatar adapter delivery or execution.

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

## Current history-apply failure behavior

When all of these are true:

- `client_history_exclusion_apply_enabled=true`,
- `client_history_exclusion_apply_dry_run_only=false`,
- route mode is managed,

backend forwarding requires an exact successful typed apply result and the exact selected request-local candidate.

### v0 no-instruction

A supported no-instruction request requires `client_history_exclusion_apply.v0` with:

```text
status = applied
payload_mutation_applied = true
forwarded_payload present
```

### v1 instruction-bearing

A supported instruction-bearing request requires:

- `client_instruction_source.v1` explicit provenance,
- exact validation against request-local instruction identity,
- `client_history_exclusion_apply.v1` status `applied`,
- exact selected candidate at backend forwarding.

Missing or invalid provenance, candidate mismatch, downstream mutation, active tool-chain requirements, or any non-applied result stops forwarding.

Runtime exceptions are converted into bounded blocked/error results. Failure never restores raw history or treats all system/developer messages as current instruction evidence. Explicit `pass_through` routes are exempt.

## Stable runtime reason posture

Operational reasons should be typed and stable enough for smoke tests and runtime analysis. Raw exception text must not become a public contract.

Representative reason classes include:

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
- history-apply missing/blocked/preparation reasons,
- invalid instruction provenance reasons,
- typed-parse/cache-writer source or validation reasons,
- Phase 6 enqueue/claim/retry lifecycle reasons once implemented.

These names are operational classes, not permission to emit arbitrary freeform exception messages.

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

### Stream failure

Current Phase 5.5 gated suppression preserves already emitted safe visible chunks, blocks incomplete or malformed internal candidates, records content-free state, and avoids duplicate replay.

Generalized partial-stream resume/recovery remains target work. It must:

- preserve already emitted valid visible chunks,
- block incomplete internal/update candidates,
- record partial-stream state and recovery metadata,
- avoid replay or duplication during recovery.

### Deferred Phase 6 failure

An already valid visible response must not become invalid because deferred enqueue, claim, worker execution, or memory persistence fails. Phase 6 status and retry state remain content-free, while memory semantics stay owned by RelayMEM.

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

## SOUL Lab management surface

Current UI-A7 provides local-only read endpoints for settings and character-registry metadata. Access requires both a loopback configured listen host and a loopback transport peer.

The projection must remain:

- read-only,
- exact-schema and allowlist based,
- secret-free,
- free of persona/memory source paths or contents,
- free of prompt, conversation, trace, and credential content,
- independent from Core route availability when access is refused.

Latest-run, memory outcome, settings mutation, character mutation, and durable memory operations remain separate future boundaries.

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
- default streaming chunks are forwarded without full-response buffering,
- gated Phase 5.5 suppression does not duplicate or semantically rewrite safe visible text,
- non-streaming responses remain compatible,
- supported sampling fields and headers are preserved where practical,
- unsupported compatibility-sensitive transactions are explicitly blocked rather than silently rewritten.

### Persona and context

- approved durable persona and output-policy anchors precede lower-authority evidence,
- latest validated user content remains present,
- v1 accepts only explicitly provenanced instruction candidates,
- memory evidence cannot replace identity authority,
- internal tags, artifacts, and diagnostics do not leak into ordinary output.

### Memory and persistence

- missing optional memory degrades cleanly,
- low-confidence, blocked, or contradictory candidates remain inactive/held,
- Retrieval remains read-only,
- persistence is blocked in restricted scenes or waiting-user states,
- RelayMEM direct/helper writes remain gated and idempotent,
- ordinary runtime does not claim autonomous memory formation until Phase 6 worker integration and later-turn recall pass,
- RelaySOUL writes require a separate governed apply path.

### Latency

- pass-through overhead remains small,
- realtime profiles avoid heavy synchronous retrieval by default,
- streaming can begin without waiting for RelaySLP or post-response extraction,
- first-token, first-sentence, and first-TTS-enqueue timings can be measured separately,
- ordinary requests should not eagerly allocate or serialize the complete recovery chain when no recovery-relevant condition exists.

### Recovery and idempotency

- partial failures do not duplicate visible chunks or writes,
- retries/resume use RelayRUN and Phase 6 state and idempotency rules where implemented,
- dispatch idempotency remains separate from RelayMEM memory-write idempotency,
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

RelayMEM persistence
  owns memory meaning, write eligibility, durable content, and write idempotency

RelaySLP / Phase 6
  owns deferred candidate compilation and queue/worker control within their split boundaries

RelayCTX
  owns context construction, selection, token degradation, Repack, and Unpack

RelayRUN
  owns execution order, fallback/recovery, node states, checkpoints,
  lineage, retry/idempotency coordination, and trace projection

Adapters
  own transport compatibility and backend-specific forwarding
```

No operational fallback may blur or transfer these ownership boundaries.
