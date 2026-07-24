---
relaylm_doc_type: system_architecture
relaylm_authority: relaylm_component_responsibility_and_canonical_pipeline_order
relaylm_status: current
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - canonical runtime stage order changes
  - component responsibility or non-ownership changes
  - request, response, or deferred-formation handoff boundaries change
  - a semantic component is added, removed, or split
relaylm_not_authoritative_for:
  - repository-wide current implementation completion
  - exact schemas, fields, defaults, or state machines
  - mode-specific failure and streaming detail
  - package layout or migration sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - system-overview.md
  - runtime/request-response-pipeline.md
  - runtime/compile-and-checkpoint.md
  - safe_soul_scene_ctx_compile_chain.md
  - memory/formation.md
relaylm_related_contracts:
  - ../contracts/pipeline_node_result_contract.md
  - ../contracts/runtime_compile_artifact_contract.md
  - ../contracts/relayctx-session-evidence-overlay.md
  - ../contracts/shared-assessment-subjective-mem.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - runtime maintainers
  - integration maintainers
  - architecture reviewers
  - AI coding agents
relaylm_authority_level: system
---
# RelayLM Pipeline Responsibilities

## Purpose

This page defines the stable responsibility boundaries and canonical semantic order of the RelayLM runtime. It separates semantic decisions, context construction, model execution, output observation, orchestration, transport, and deferred formation so one component cannot silently acquire another component's authority.

Repository-wide system context is owned by [RelayLM System Overview](system-overview.md). Mode-specific request, streaming, response-finalization, correction, and pass-through behavior is owned by [Request / Response Pipeline](runtime/request-response-pipeline.md). Exact artifact and schema rules remain in contracts.

## Core rule

RelayLM keeps semantic decisions separate from runtime orchestration and transport.

```text
semantic policy and selection
  -> bounded context construction
  -> model execution
  -> visible emission and response-complete finalization branches

out of band after the answer
  governed evidence -> deferred assessment and candidate formation
```

No stage may recreate an upstream semantic decision merely because its artifact is missing or inconvenient.

## Canonical order

### Accepted target: optional pre-request admission

```text
source occurrence
  -> governed Evidence capture/admission
  -> optional RelayATN reject / hold / select
  -> admitted request
```

RelayATN is a gated target before the normal request shell for future continuous-input environments. This branch does not claim current runtime implementation. RelayATN does not write RelayCTX, scene, relationship, persona, or memory state.

### Interactive request/response path

```text
validated request evidence
  -> RelayRUN request shell and PipelineContext
  -> RelayREL target relationship selection
  -> input-side RelaySCN
  -> input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval when allowed
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> Main LLM / backend execution
       |- streaming chunk branch
       |    -> incremental RelayCTX Unpack / output boundary
       |    -> adapter transport and user-visible chunk
       |    -> RelayRUN chunk and idempotency accounting
       |
       `- response-complete branch
            -> finalized assistant Evidence
            -> RelayCTX final Unpack validation
            -> RelayREF
            -> return-side RelayEMO and output-side RelaySCN consumers
            -> RelayRUN response finalization
            -> non-stream response or stream-close transport
            -> deferred coverage / enqueue handoff
```

RelayREL precedes RelaySCN so route- or session-authenticated relationship policy can constrain scene, expression, disclosure, and memory handling. RelayREL does not override RelaySCN public/private scene constraints, safety gates, or current-scene authority.

The compile gate is a request-local authority-aware decision phase, not a standalone semantic component. RelayRUN surrounds and records the flow but does not reinterpret semantic artifacts. Streaming emission and response-complete finalization are separate branches; mode-specific details remain in the request/response pipeline authority.

### Deferred after-turn path

```text
finalized governed evidence
  -> RelaySLP
  -> Shared Assessment
  -> character-scoped Subjective Formation
  -> memory / scene / relationship candidates
  -> character-source proposals
  -> owning persistence and approval gates
```

The deferred path does not answer the current turn and cannot retroactively replace delivered output.

## Responsibility matrix

| Component | Owns | Must not own |
|---|---|---|
| Evidence authority | source identity, admission, authorization, retention, lineage, protected response binding | turn admission, prompt layout, memory meaning |
| RelayATN | target pre-request reject/hold/select for future continuous-input profiles | evidence admission, CTX, scene, relationship, or memory mutation |
| RelayRUN | run/turn identity, node state, timeout/retry orchestration, fallback/recovery routing, stream state, checkpoints, trace, idempotency | scene, emotion, intent, memory, persona, prompt, or final wording semantics |
| PipelineContext | request-local original/forwarded payload coordination, explicit replacement reasons, ordered node results, and detached candidates | semantic policy or durable state |
| RelayREL | authenticated target relationship selection and interaction policy | portable character identity, scene classification, memory truth |
| input-side RelaySCN | request-local situation, disclosure, persistence, confirmation, memory-scope, and expression policy | prompt assembly, affect state, relationship state, durable memory writes |
| input-side RelayEMO | bounded affect estimate and expression pressure | scene, intent, relationship, persistence, or memory authority |
| RelayINT | pre-action intent, reference, ambiguity, clarification, proceed/block, and retrieval-need decisions | retrieval execution, memory mutation, final response wording |
| RelayMEM Retrieval | bounded read-only selection of eligible approved memory | prompt layout, scene policy, synchronous memory writes |
| RelayCTX Repack | selected context layout, authority order, stable/dynamic separation, token-budget degradation, backend message rendering | scene, relationship, intent, or durable memory policy |
| Runtime Compile Gate | authority-aware selection of one prepared backend payload or fail-closed outcome | semantic source selection or checkpoint persistence |
| Main LLM/backend | response generation from the selected context | RelayLM durable persona, relationship, scene, or memory authority |
| RelayCTX Unpack | visible-output and internal-candidate separation | semantic content judgment or direct durable mutation |
| RelayREF | bounded observation after generated output exists | pre-action intent, same-turn scene/retrieval decisions, direct consumer mutation |
| return-side RelayEMO | engine-neutral display, TTS, or avatar expression hint | response meaning rewrite or durable emotion truth |
| output-side RelaySCN | next-turn scene, recovery, and persistence observations | general output rewriting |
| RelaySLP | deferred assessment, memory/scene/relationship candidates, and character-source proposals | current-turn response generation or unapproved direct source mutation |
| adapters | OpenAI-compatible request/response transport, backend forwarding, streaming and media execution | semantic persona, scene, relationship, memory, or persistence decisions |

## Timing invariants

```text
RelayINT  = before action
RelayREF  = after response
RelaySLP  = after the current user-visible answer
```

Additional invariants:

1. ordinary managed conversation uses one Main LLM response-generation call unless a separately governed optional probe or tool transaction is invoked;
2. RelayMEM Retrieval is read-only in the interactive path;
3. RelayCTX constructs bounded context but does not create semantic policy;
4. streaming chunk emission and response-complete finalization are separate paths;
5. output-side observations do not retroactively change same-turn input-side decisions;
6. already emitted text is never replaced or replayed;
7. user-visible clarification and recovery text passes through the normal output boundary;
8. default diagnostics and checkpoints remain content-free;
9. optional analyzer or observer failure degrades to bounded absence, not authority transfer;
10. deferred formation never delays or invalidates an already delivered answer.

## Content-bearing and content-free boundary

Runtime-private artifacts may contain selected relationship, scene, intent, memory, context, request, prompt, candidate, and response content when their owning path requires it.

Generic diagnostics, traces, checkpoint summaries, generated indexes, and public projections may contain only allowlisted booleans, counts, bands, enum classes, reason identifiers, schema versions, and opaque identities. They do not become a second content store or semantic authority.

## Current-versus-target interpretation

This page defines canonical responsibility and order. It does not assert that every target handoff is default-on or fully implemented. Current runtime may still expose compatibility node names, default-off gates, dry-run/preflight artifacts, and partial target families.

Interpret implementation through [Project Status](../PROJECT_STATUS.md), code, current schema/version, focused tests and smoke, and dedicated current/target documents. A target stage name alone is never completion evidence.

## Failure behavior

When a required artifact is missing, invalid, stale, unauthorized, or incompatible:

- the consumer applies its documented safe default, skip, clarification, bounded fallback, or fail-closed behavior;
- it does not recreate the producer's semantics;
- it records only allowlisted content-free failure metadata;
- it does not mutate durable state outside an owning transaction;
- it does not restore excluded client authority on managed routes;
- it does not bypass the normal output path.

## Non-goals

This page does not define:

- exact artifact fields or wire schemas;
- current implementation completion;
- scheduler priority values or service operation;
- memory lifecycle transitions or storage syntax;
- frontend UI behavior;
- package layout, module names, or migration order;
- deployment configuration or operator commands.
