---
relaylm_doc_type: system_architecture
relaylm_authority: relaylm_system_context_authority_planes_and_runtime_boundaries
relaylm_status: current
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - product system boundary or supported integration role changes
  - durable, interactive, deferred, or operator authority planes change
  - canonical subsystem ownership or dependency direction changes
  - public frontend/backend interface posture changes
relaylm_not_authoritative_for:
  - repository-wide current implementation completion
  - exact runtime stage order or component ownership details
  - exact schemas, fields, gates, state machines, or APIs
  - deployment-specific configuration and operator procedure
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline-responsibilities.md
  - runtime/request-response-pipeline.md
  - runtime/compile-and-checkpoint.md
  - runtime/scheduler.md
  - file_first_character_workspace_design.md
  - memory/formation.md
relaylm_related_contracts:
  - ../contracts/governed-evidence-contract-family.md
  - ../contracts/relayctx-session-evidence-overlay.md
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - architecture maintainers
  - integration maintainers
  - AI coding agents
relaylm_authority_level: system
---
# RelayLM System Overview

## Purpose

RelayLM is an OpenAI-compatible Memory Context Proxy and character-runtime coordination layer. It sits between supported frontends and OpenAI-compatible model backends while preserving explicit ownership for character sources, relationship and scene policy, memory, context construction, evidence, deferred formation, runtime control, and transport.

This page owns the repository-wide system context and authority planes. Exact component order is owned by [Pipeline Responsibilities](pipeline-responsibilities.md), mode-specific dataflow by [Request / Response Pipeline](runtime/request-response-pipeline.md), and compile/checkpoint behavior by [Runtime Compile and Checkpoint Architecture](runtime/compile-and-checkpoint.md).

## External context

```text
supported frontend or local integration
  -> RelayLM OpenAI-compatible interface
  -> RelayLM routing and managed-runtime boundary
  -> OpenAI-compatible model backend
```

RelayLM can preserve an explicit delegated pass-through path, but its managed paths construct and govern backend context rather than treating arbitrary client history as character or memory authority.

RelayLM is not:

- a general autonomous-agent framework;
- an unrestricted transcript database;
- a replacement for model-serving backends;
- a frontend-owned memory or persona store;
- a semantic censorship layer for ordinary generated conversation.

## Authority planes

RelayLM separates four non-competing authority planes.

### Durable character and governed state

```text
approved character sources
relationship sources
canonical memory
protected source evidence
accepted contracts and durable operations
```

These authorities survive individual requests. They change only through their owning approval, lifecycle, storage, or evidence contracts.

### Interactive request/response runtime

```text
route and request identity
  -> relationship / scene / expression / intent decisions
  -> read-only retrieval and bounded context construction
  -> model generation
  -> output separation, observation, transport, and finalization
```

The interactive path answers the current request. It does not synchronously perform unrestricted durable character or memory mutation.

### Deferred formation and workspace maintenance

```text
governed evidence
  -> deferred assessment and candidate formation
  -> memory / scene / relationship candidates
  -> character-source proposals
  -> explicit persistence and approval gates
```

Deferred work cannot rewrite an already delivered answer or bypass storage and approval authority.

### Operations and repository governance

```text
runtime scheduling, recovery, checkpoints, diagnostics
repository validation, generated projections, migration, retirement
```

These surfaces coordinate execution and maintenance. They do not acquire semantic persona, scene, relationship, or memory authority merely because they observe or move artifacts.

## Major subsystem map

| Subsystem | Primary responsibility | Important non-responsibility |
|---|---|---|
| OpenAI-compatible interface and adapters | protocol, routing input, backend forwarding, streaming transport | persona, scene, memory, or relationship meaning |
| Character Workspace and RelaySOUL | approved portable character sources and proposal/approval lifecycle | target-specific relationship state or request-local scene state |
| RelayREL | target-specific relationship state and interaction policy | portable character identity or scene classification |
| RelaySCN | request-local situation, disclosure, persistence, and expression policy | prompt assembly or durable memory truth |
| RelayEMO | bounded affect/expression pressure and presentation hints | scene, intent, relationship, or persistence authority |
| RelayINT | pre-action intent, reference, ambiguity, proceed/block, and retrieval need | memory search execution or final wording |
| RelayMEM | canonical subjective memory lifecycle and read-only retrieval | prompt layout or current scene policy |
| RelayCTX | bounded working context, context assembly, token degradation, and output separation | durable memory or semantic policy ownership |
| Main LLM/backend | response generation from the selected context | RelayLM durable state authority |
| RelayREF | bounded post-response observation | pre-action decisions or direct state mutation |
| RelayRUN | execution identity, node state, fallback/recovery, checkpoints, and trace | semantic component decisions or response authorship |
| RelaySLP | deferred assessment and governed candidates/proposals | current-turn response generation |
| Repository/documentation governance | classification, validation, synthesis, migration, and Git-history retirement | runtime semantic behavior |

## Dependency direction

```text
accepted contracts and approved durable sources
  -> semantic policy and selection components
  -> RelayCTX compile inputs
  -> model/backend execution
  -> output observation and runtime finalization
  -> deferred governed candidates
```

Lower layers may consume validated artifacts from owning higher-authority sources. They must not recreate, override, or silently persist another subsystem's decision.

## Current-versus-target rule

This overview describes the stable system boundary, not completion. Current implementation may contain default-off gates, compatibility names, transitional paths, and partially implemented target artifact families. Interpret completion through [Project Status](../PROJECT_STATUS.md), code, schema/version, focused validation, and current/target reference documents.

A target subsystem name or state in architecture does not prove that its complete runtime path is active.

## Safety and privacy invariants

- managed context authority does not fall back to excluded raw client history;
- durable memory, character, relationship, scene, and evidence mutation use explicit owning gates;
- default diagnostics and checkpoints remain content-free unless a protected typed store explicitly allows content;
- browser and frontend surfaces do not own server-side storage, queue, scheduler, route, or character authority;
- user-visible recovery and generated output use the normal response/transport boundary;
- generated indexes, inventories, and records do not become semantic architecture or status authority;
- compatibility and transitional assets have an owner, consumer, removal gate, and replacement validation.

## Non-goals

This overview does not define:

- exact schemas or wire envelopes;
- every runtime mode or failure branch;
- package layout or migration sequencing;
- scheduler policy values;
- memory lifecycle states;
- deployment commands or configuration defaults;
- current implementation completion.
