---
relaylm_doc_type: subsystem_architecture
relaylm_authority: runtime_resource_observation_job_scheduling_and_mutation_fence_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: runtime
relaylm_update_trigger:
  - RelayRUN scheduling ownership changes
  - runtime resource observation ownership changes
  - compute priority or mutation-fence semantics change
  - multi-backend or host-level supervision is introduced
relaylm_not_authoritative_for:
  - exact hardware API or vendor-specific telemetry
  - exact job-request or resource-snapshot schema
  - semantic fallback owned by REL, SCN, EMO, INT, MEM, CTX, REF, or SLP
  - exact Correct or Forget mutation contract
  - current implementation status or sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
relaylm_related_authority:
  - ../pipeline-responsibilities.md
  - ../relayrun_runtime_checkpoint_design.md
  - request-response-pipeline.md
  - ../memory/formation.md
  - ../phase6b0_relayslp_durable_queue_contract.md
  - ../phase_i4b_primary_current_state_shared_fence.md
---
# RelayLM Runtime Scheduler

## Authority summary

This document is authoritative for target separation between hardware/backend observation, RelayRUN execution scheduling, and immediate control-plane mutation fences. It does not define semantic fallback or exact durable queue and mutation schemas.

## Responsibility map

```text
Runtime Resource Provider
  observes capacity and backend facts

RelayRUN compute scheduler
  admits, orders, defers, skips, cancels, retries, or coalesces operational jobs

RelayRUN control-plane coordination
  propagates mutation fences, revision invalidation, retrieval exclusion,
  and cancellation/conflict signals

Semantic component
  defines the meaning of its own degraded, deferred, or blocked result
```

A Resource Provider is not a second orchestrator. RelayRUN remains the runtime orchestration authority for one RelayLM runtime.

## Resource Provider ownership

A Runtime Resource Provider may report bounded facts such as:

- backend and loaded-model identity;
- active generation class;
- queue depth;
- VRAM, memory, or KV-cache pressure class;
- recent time-to-first-token and throughput bands;
- cancellation and concurrency capability;
- TTS/ASR/backend resource-sharing class;
- health and availability state.

It does not decide that a memory is unimportant, that an affect estimate should become neutral, that a scene should become unknown, or that a mutation may bypass its owning contract.

## RelayRUN operational ownership

RelayRUN may decide:

```text
run_now
defer
busy_skip
cancel_and_retry
coalesce_operational_jobs
block
fallback_route
```

It owns:

- run, node, and operational-job lifecycle;
- compute admission and priority;
- deadline, timeout, retry, and cancellation orchestration;
- dispatch idempotency and duplicate prevention;
- checkpoint and recovery metadata;
- queue correlation and execution lineage under the durable queue contract;
- content-free resource and execution projections.

RelayRUN does not own semantic content or semantic fallback meaning. It also does not coalesce canonical MEM records or decide that two memories have the same meaning.

## Two priority domains

Compute/resource priority and control-plane consistency are related but not one linear queue.

### Compute/resource domain

Default direction:

```text
interactive response generation
  > voice-out when sharing the constrained resource
  > mandatory lightweight response finalization
  > optional probes when admitted
  > Primary Subjective MEM formation
  > Secondary consolidation and relation maintenance
  > embeddings, evaluation, and other maintenance
```

These classes express latency and resource impact. They do not express evidence confidence, subjective salience, or memory importance.

### Control-plane fence domain

The control plane includes:

```text
Correct / Forget / lifecycle mutation fence
canonical revision change
retrieval exclusion
cache revision invalidation
pending-write conflict signal
cancellation signal
```

A control-plane fence is not merely a lower-priority GPU job. Once an owning mutation contract establishes a valid fence, RelayRUN must propagate its operational effect to future retrieval, packing, and uncommitted writes without waiting for unrelated background compute.

Already emitted visible text is not withdrawn. Whether an in-progress not-yet-emitted operation may be cancelled remains governed by transport and mutation contracts.

## Semantic fallback ownership

Examples:

```text
RelayEMO optional probe skipped
  -> RelayEMO emits heuristic/neutral bounded estimate

RelaySCN optional refinement skipped
  -> RelaySCN emits safe default or bounded heuristic

RelayREF optional probe skipped
  -> RelayREF emits partial observation or observation_unavailable

RelaySLP deferred
  -> pending / evidence-only state

Secondary consolidation skipped
  -> canonical MEM remains unchanged
```

RelayRUN records fallback class and reason. It does not create the semantic artifact.

## Job requirement model

A compute job submitted to RelayRUN should declare bounded operational requirements, for example:

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

The exact schema remains a contract concern. Operational requirements are declared to RelayRUN rather than inferred ad hoc by each component.

A mutation-fence request uses a separate owning contract and must not be disguised as this compute-job shape.

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

Exact numeric telemetry is optional. Stable classes are sufficient when a backend cannot expose accurate counters.

## Single-GPU behavior

For the initial one-GPU local deployment:

1. interactive response generation has priority over deferred SLP compute;
2. TTS has priority over SLP when it shares the same constrained resource;
3. optional analyzer/probe jobs may busy-skip;
4. Primary formation may defer and later coalesce with newer compatible evidence coverage;
5. Secondary consolidation and maintenance do not start while an interactive request is pending;
6. concurrent response generation and SLP generation are disabled unless explicitly validated for the backend and hardware profile;
7. RelayLM does not lengthen visible responses to create hidden background time.

## Interactive arrival during SLP

```text
safe cancellation supported
  -> cancel current uncommitted SLP attempt
  -> retain idempotent pending coverage
  -> start interactive request

safe cancellation not supported
  -> prevent additional background admission
  -> let the bounded current operation complete
  -> immediately prioritize interactive request

compatible not-yet-started formation work
  -> coalesce source coverage under exact scope and privacy partitions
  -> replace redundant operational jobs with one idempotent job
```

A partially generated SLP candidate is not committed merely because cancellation is inconvenient.

## Busy-skip, defer, and block

### Busy-skip

Use when an optional operation has a complete owner-defined fallback for the current turn.

Examples:

- optional RelayEMO structured probe;
- optional RelaySCN classifier refinement;
- optional RelayREF semantic probe.

### Defer

Use when work remains useful later and its source references are durable.

Examples:

- Shared Assessment pass;
- Subjective Formation pass;
- relation adjudication;
- Secondary consolidation;
- cache rebuild after the old revision has already become retrieval-ineligible.

### Block

Use only when no authority-safe fallback exists. A block reason is operational and does not imply a semantic conclusion.

## Operational job coalescing

RelayRUN may coalesce pending operational formation jobs only when:

- they address the same character namespace and compatible evidence group;
- no committed output depends on the superseded job;
- dispatch idempotency and source coverage remain explicit;
- scope, participant, relationship, and privacy partitions are not widened;
- all source references remain covered;
- the assessment and subjective-formation stage boundary remains explicit.

RelayRUN does not decide semantic merge, reinforcement, refinement, or supersession.

## Queue pressure

Under queue pressure:

- Protected Source Evidence is never discarded merely to reduce formation backlog;
- redundant or not-yet-started operational jobs may be regenerated or coalesced;
- maintenance jobs may be dropped and rescheduled;
- review-required and explicit mutation operations remain separately identifiable;
- queue age never becomes memory salience or evidence confidence;
- a valid lifecycle mutation fence remains effective even when projection rebuild is deferred.

## Voice and adapter interaction

RelayRUN schedules generation and adapter work according to resource sharing. RelayEMO supplies hints; adapters execute them.

If TTS uses CPU or a separate backend, SLP may run while audio is playing when the Main LLM backend is idle. If TTS shares the GPU, voice-out remains ahead of SLP compute.

## Failure and recovery

```text
Resource Provider unavailable
  -> conservative configured capacity
  -> optional background work defers

backend unhealthy
  -> governed fallback or error path

background job timeout
  -> no semantic commit
  -> retry only under idempotency rules

mutation fence established but rebuild fails
  -> old revision remains retrieval-ineligible
  -> fail-closed recovery state

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
- TTS, ASR, vision, or image generation sharing accelerators;
- several concurrent characters or users.

A host supervisor owns resource leases and backend allocation, not per-turn semantic pipeline decisions. Each RelayRUN remains responsible for its own job lifecycle and component handoffs.

## Fixed invariants

- Resource Provider reports facts; RelayRUN decides operational timing.
- Compute priority and mutation-fence consistency are separate domains.
- RelayRUN does not create semantic fallback content.
- Interactive response and shared-resource voice-out outrank deferred formation compute.
- Evidence remains durable when formation jobs defer or coalesce.
- Coalescing applies to operational jobs, not semantic memory identity.
- Valid lifecycle mutation fences affect future retrieval before deferred rebuild completes.
- A separate host supervisor is added only for cross-runtime resource allocation.
