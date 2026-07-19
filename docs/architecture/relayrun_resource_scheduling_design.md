---
relaylm_doc_type: stable_architecture
relaylm_authority: relayrun_resource_observation_and_job_scheduling_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - RelayRUN scheduling ownership changes
  - runtime resource observation ownership changes
  - job priority or degradation semantics change
  - multi-backend or host-level supervision is introduced
relaylm_not_authoritative_for:
  - exact hardware API or vendor-specific telemetry
  - exact job-request or resource-snapshot schema
  - semantic fallback owned by REL, SCN, EMO, INT, MEM, CTX, REF, or SLP
  - current implementation status
  - implementation sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../adr/0004-single-call-interactive-runtime-deferred-formation.md
  - pipeline_responsibility_design.md
  - relayrun_runtime_checkpoint_design.md
  - runtime_dataflow_modes.md
  - subjective_mem_deferred_formation_design.md
---
# RelayRUN Resource Scheduling Design

## Purpose

This document defines the target separation between hardware/backend observation and RelayRUN execution scheduling.

```text
Runtime Resource Provider
  observes capacity and backend facts

RelayRUN
  admits, orders, defers, skips, cancels, retries, or coalesces jobs

Semantic component
  defines the meaning of its own degraded or deferred result
```

RelayRUN remains the sole runtime pipeline orchestrator for one RelayLM runtime. A Resource Provider is not a second orchestration layer.

## Ownership boundary

### Runtime Resource Provider owns observations

A provider may report bounded facts such as:

- backend identity and loaded model identity;
- active generation class;
- queue depth;
- VRAM or memory pressure class;
- KV-cache pressure class;
- recent time-to-first-token and throughput bands;
- cancellation and concurrency capability;
- TTS/ASR/backend resource-sharing class;
- health and availability state.

The provider does not decide that a memory is unimportant, that an affect estimate should be neutral, or that a scene should become unknown.

### RelayRUN owns execution decisions

RelayRUN may decide:

```text
run_now
defer
busy_skip
cancel_and_retry
coalesce
block
fallback_route
```

It owns:

- job and node lifecycle;
- priority and admission;
- deadline, timeout, retry, and cancellation orchestration;
- idempotency and duplicate prevention;
- queue ownership and lineage;
- checkpoint and recovery metadata;
- resource-reason projections.

RelayRUN does not own semantic content or semantic fallback meaning.

### Semantic components own degraded meaning

Examples:

```text
RelayEMO optional LLM probe skipped
  -> RelayEMO emits heuristic/neutral bounded estimate

RelaySCN optional classifier skipped
  -> RelaySCN emits its safe default or bounded heuristic result

RelaySLP deferred
  -> RelaySLP remains pending / evidence-only

Secondary consolidation skipped
  -> RelayMEM canonical state remains unchanged
```

RelayRUN records which fallback class was requested or applied, but it does not invent the fallback artifact.

## Default priority direction

```text
P0 interactive response generation and voice-out
P1 explicit governed user mutation
P2 mandatory lightweight response-finalization processing
P3 Primary Subjective MEM formation
P4 Secondary consolidation and relation maintenance
P5 embeddings, cache rebuild, evaluation, and maintenance
```

Priority classes express latency and user-impact order. They do not express evidence confidence, subjective salience, or memory importance.

## Job requirement model

A job submitted to RelayRUN should declare bounded operational requirements, for example:

```yaml
runtime_job_request:
  job_id: slp-formation-123
  node_class: relayslp_subjective_formation
  priority_class: deferred_primary_formation
  latency_class: background
  deferrable: true
  skippable: false
  cancellable: true
  retryable: true
  coalescible: true
  idempotency_key: formation-evidence-group-123-character-r3
  fallback_class: evidence_only
  max_input_tokens: 4096
  max_output_tokens: 384
  preferred_backend_class: main_llm
  cache_affinity_key: relayslp-v0
```

The exact schema remains deferred. The stable rule is that operational requirements are declared to RelayRUN rather than inferred ad hoc inside each component.

## Resource snapshot model

A provider snapshot may resemble:

```yaml
runtime_resource_snapshot:
  backend_id: lmstudio-local
  model_id: local-main-llm
  generation_active: true
  active_job_class: interactive_response
  queue_depth: 2
  resource_pressure_class: high
  kv_cache_pressure_class: high
  recent_ttft_band: medium
  recent_throughput_band: normal
  cancellation_supported: false
  concurrent_generation_supported: false
  healthy: true
```

Exact numeric telemetry is optional. Stable classes are sufficient when the backend cannot expose accurate counters.

## Single-GPU interactive behavior

For the initial one-GPU local deployment:

1. interactive response generation has priority over SLP;
2. TTS has priority over SLP when it shares the same constrained resource;
3. optional classifier/probe jobs may busy-skip;
4. Primary formation may defer and later coalesce with newer related evidence;
5. Secondary consolidation and maintenance must not start while an interactive request is pending;
6. concurrent Main LLM response and SLP generation are disabled unless explicitly validated for the backend and hardware profile.

RelayLM must not lengthen user-facing responses to create hidden time for background work.

## Interactive arrival during SLP

When a new interactive request arrives while SLP is active, RelayRUN selects among backend-supported behaviors:

```text
safe cancellation supported
  -> cancel current SLP attempt
  -> retain idempotent pending job
  -> start interactive request

safe cancellation not supported
  -> prevent additional background admission
  -> let the bounded current operation complete
  -> immediately prioritize interactive request

coalescible formation not yet started
  -> merge related pending evidence references
  -> replace redundant jobs with one new idempotent job
```

A partially generated SLP candidate is not committed merely because cancellation is inconvenient.

## Busy-skip versus defer

### Busy-skip

Use when the optional operation has a complete owner-defined fallback for the current turn.

Examples:

- optional RelayEMO structured probe;
- optional RelaySCN classifier refinement;
- optional RelayREF semantic probe.

### Defer

Use when the work remains useful later and its source references are durable.

Examples:

- Shared Assessment and Subjective MEM formation;
- relation adjudication;
- Secondary consolidation;
- cache rebuild.

### Block

Use only when no authority-safe fallback exists for the current operation. A block reason remains operational and does not imply a semantic conclusion.

## Coalescing rules

Formation job records are operational and may be regenerated from durable governed evidence. RelayRUN may coalesce jobs when:

- they address the same character namespace and compatible evidence group;
- no committed output depends on the superseded job;
- idempotency and source coverage remain explicit;
- scope, participant, or privacy partitions are not widened;
- the resulting job preserves all source references.

RelayRUN must not coalesce canonical MEM records or decide that two memories have the same meaning.

## Queue pressure

Under queue pressure:

- Protected Source Evidence is never discarded merely to reduce formation backlog;
- redundant or not-yet-started formation jobs may be regenerated or coalesced;
- maintenance jobs may be dropped and rescheduled;
- review-required or explicit mutation jobs remain separately identifiable;
- queue-age metrics must not become memory salience or evidence confidence.

## Voice and adapter interaction

RelayRUN schedules generation and adapter work according to resource sharing. RelayEMO supplies TTS/avatar hints; adapters execute them.

If TTS uses CPU or a separate backend, SLP may run while audio is playing when the Main LLM backend is idle. If TTS shares the GPU, voice-out remains ahead of SLP.

## Failure and recovery

```text
Resource Provider unavailable
  -> RelayRUN uses conservative configured capacity
  -> optional background work defers

backend unhealthy
  -> RelayRUN selects governed fallback or error path

background job timeout
  -> no semantic commit
  -> retry only under idempotency rules

interactive stream already emitted
  -> no replay or replacement of emitted content
```

Default diagnostics expose content-free classes and reason IDs only.

## Host-level supervisor boundary

A separate host-level Resource Supervisor is unnecessary for the initial single-runtime deployment.

It may be introduced when one host must allocate resources across:

- several RelayRUN instances;
- several local LLM backends;
- multiple GPUs;
- TTS, ASR, vision, or image generation sharing the same accelerators;
- several concurrent characters or users.

A host supervisor owns resource leases and backend allocation, not per-turn semantic pipeline decisions. Each RelayRUN remains responsible for its own job lifecycle and component handoffs.

## Non-goals

This design does not:

- define CUDA, ROCm, LM Studio, llama.cpp, or operating-system APIs;
- make RelayRUN a memory or scene judge;
- use job priority as evidence strength or MEM salience;
- authorize parallel generation on unvalidated hardware;
- require a host supervisor for one local backend;
- permit background work to delay or distort ordinary conversation.

## Fixed boundaries

- Resource Provider reports facts; RelayRUN decides timing.
- RelayRUN does not create semantic fallback content.
- Interactive response and voice-out outrank deferred formation.
- Evidence remains durable even when formation jobs defer or coalesce.
- Coalescing applies to operational jobs, not semantic memory identity.
- A separate host supervisor is added only for cross-runtime resource allocation.
