---
relaylm_doc_type: status
relaylm_authority: current_project_state
relaylm_status: current
relaylm_volatility: high
relaylm_owner: project_status
relaylm_update_trigger:
  - boundary moves between design dry-run read-only and apply
  - default behavior changes
  - supported request shape changes
  - current schema producer or consumer changes
  - active integration milestone changes state
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical implementation evidence
relaylm_related_authority:
  - docs/DOCUMENTATION_MODEL.md
  - docs/architecture/pipeline_responsibility_design.md
  - docs/architecture/pipeline_implementation_plan.md
  - docs/architecture/current_target_migration_guide.md
  - docs/architecture/phase6_async_relayslp_bounded_slice.md
  - docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - docs/architecture/phase6b3_relayslp_queue_state_helpers.md
  - docs/architecture/phase6c1_primary_mem_worker_contract.md
  - docs/architecture/phase6c1_relaymem_primary_pipeline_compose.md
  - docs/architecture/phase6c1_primary_worker_outcome_classifier.md
  - docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md
  - docs/architecture/phase6c1_integrated_worker_fault_smoke_handoff.md
  - docs/architecture/phase6c1_durable_protected_source_persistence.md
  - docs/architecture/phase6c2_one_queued_primary_worker_integration.md
  - docs/architecture/integration_i1_primary_mem_two_turn_recall.md
  - docs/architecture/relaymem_mvp_implementation_plan.md
  - docs/architecture/relaymem_slp_current_target.md
  - docs/architecture/soul_lab_ui_a7_management_projection_handoff.md
  - docs/architecture/phase_i2_real_soul_lab_observation.md
  - docs/architecture/phase_i3_i9_evaluation_work_roadmap.md
---
# RelayLM Project Status

Last reviewed: 2026-06-24 JST

Status reviewed through:

- Phase 6 I1-B ordinary request-runtime enqueue and finalized-turn protected capture,
- Phase 6-C1-0 through C1-5 Primary MEM worker, fault, and durable-source boundaries,
- Phase 6-C2 one queued-job claim / rehydrate / execute integration adapter,
- Phase I-1 Primary MEM next-turn recall and character/namespace isolation,
- Phase I-2 real SOUL Lab latest-run and memory observation integration.

## Purpose and authority

This page is the concise current-state view for developers and reviewers. It records what works now, what remains gated or disconnected, and the immediate implementation priority.

When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibilities and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) owns detailed implementation status and sequencing.
3. Dedicated current contracts own exact schemas and bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) defines compatibility and target interpretation.
5. `docs/mvp/` and historical handoffs are evidence only.

## Current implementation position

```text
Managed-route correctness: Phase 5-C complete through bounded v0/v1 apply and C5 runtime plumbing
Pre-stream hardening: Phase 5-D complete through D2
Stream safety / TTS handoff preparation: Phase 5.5 complete for RelayLM Core
Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete; C2 one-job adapter complete
RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; ordinary next-turn recall and scope isolation complete
SOUL Lab UI: UI-A0 through UI-A7 complete; Phase I-2 real read-only observation connected
I1-G pre-enqueue background-finalizer durability: unresolved
Next product boundary: Phase I-3 auditable Correct operation
```

## Core request/runtime foundation

Current implementation includes:

- OpenAI-compatible `/v1/chat/completions` proxying, routing, and backend forwarding,
- `PipelineContext` and ordered content-free `PipelineNodeResult` collection,
- managed client-history authority through bounded v0/v1 apply,
- selected RelayMEM retrieval and gated RelayCTX injection,
- pure and gated non-stream RelayCTX Unpack,
- Phase 5.5 stream suppression and TTS-safe handoff metadata,
- strict read-only client-instruction cache lookup,
- runtime-private typed parse and default-off cache-write plumbing,
- CJK-aware deterministic token estimation,
- lazy RelayRUN recovery-detail wiring,
- RelaySOUL dry-run/preflight governance foundations.

Current managed-route limitations:

- history-exclusion apply remains default-off and dry-run-only by default,
- active tool transactions remain blocked because minimum-chain reconstruction is absent,
- trusted backend-response instruction-control production and semantic RelaySCN apply are incomplete,
- parser-versioned cache lookup/write compatibility is not implemented.

## Phase 6 RelaySLP orchestration

Implemented:

- A1 deferred job-admission preflight,
- A2 finalized-turn handoff,
- B0 durable queue schema and state machine,
- B1 deterministic dispatch/job-record preflight,
- B2 atomic durable enqueue,
- B3 fenced claim, renew, retry release, stale recovery, and terminal commit,
- I1-B ordinary managed non-stream and stream post-response A1 -> A2 -> B1 -> B2 wiring,
- C1-0 exact claim-correlated protected worker source and one-shot scope,
- C1-1 canonical M3a-M3h compose,
- C1-2 lease-fenced execution of one already-claimed canonical B3 job,
- C1-3 pure RelayMEM-outcome classification,
- C1-4 integrated crash, lease-loss, lock-contention, stale-claim, corruption, and leakage smoke,
- C1-5 source-before-queue durable protected artifact publication and restart rehydration,
- C2 exact queued-record claim, durable rehydrate, C1-2 execution, and terminal-only cleanup.

C1-5 keeps the queue record content-free. The process-local registry is only an optional hot cache; a new claim may rehydrate the claim-independent protected capture for durably enqueued jobs and construct a fresh C1-0 source/scope.

Current limitations:

- no queue scanner, daemon, or scheduler automatically selects and claims queued work,
- C1-5 is restart-complete only for protected-source recovery of durably enqueued jobs,
- the pre-enqueue background-finalizer crash window remains unresolved: a process exit after visible response delivery but before source/queue publication may still lose that deferred turn.

## RelayMEM Primary persistence and recall

Implemented:

- M3a Primary MEM formation candidate,
- M3b source lineage, safety, and memory-write preflight,
- M3c deterministic Primary page candidate,
- M3d writer/store-target handoff,
- M3e atomic no-clobber page publication,
- M3f deterministic index/log reconciliation preflight,
- M3g gated index-before-log reconciliation apply,
- M3h read-only receipt/store recovery audit,
- C1-1 exact M3a-M3h composition,
- C1-2 one-active-claim execution,
- Phase I-1 ordinary next-turn M2 retrieval,
- exact Primary page plus canonical index/log validation,
- bounded RelayCTX injection for the correct character and namespace,
- proof that the generated response path receives the injected memory.

Current limitations:

- ordinary response finalization intentionally does not invoke M3a-M3h inline,
- Secondary MEM consolidation is not implemented,
- durable Correct/forget/pin/merge mutation is not implemented.

## SOUL Lab UI and real observation

UI-A0 through UI-A7 and Phase I-2 provide:

- TypeScript/React/Vite browser shell,
- Japanese-default and English-preview localization,
- light/dark themes,
- active-character selection and character-scoped browser state,
- Home, Adoption, Communication, Pod, Settings, and Lab Observation surfaces,
- loopback-only `GET /lab/api/settings` and `GET /lab/api/characters`,
- loopback-only latest-run, recent Primary memory, held/blocked outcome, and used-memory APIs,
- exact versioned server projections and strict exact-key browser validation,
- explicit loading, empty, refused, invalid-schema, unavailable, real-data, and local-preview states,
- AbortController plus request generation to discard stale responses after character switching,
- bounded titles, summaries, reasons, item counts, and response size,
- durable restart-readable observation receipts only where existing authority did not preserve evidence,
- source labels that keep `RelayLM runtime` and `Local preview data` separate,
- disabled Correct/forget/pin/merge/apply/discard controls pending I-3.

Phase I-2 observation receipts are read-model evidence only. They are not Primary MEM, are not retrievable by M1/M2, do not replace protected source, do not alter B3/C1 authority, and cannot repair runtime state.

Current limitations:

- no durable character-registry mutation,
- no Correct/forget/pin/unpin/merge or held apply/discard operation,
- no RelaySOUL apply or rollback,
- no persisted transcript inspection,
- no TTS/audio/avatar execution,
- no static serving of the built SOUL Lab bundle from RelayLM.

## Active implementation priority

### Phase I-3: auditable Correct operation

The next bounded product path is one auditable correction whose result changes later retrieval behavior without bypassing existing RelayMEM authority.

Required boundary:

```text
real Lab Observation item
  -> explicit Correct request
  -> exact character/namespace/current-memory validation
  -> bounded mutation preflight
  -> atomic authoritative memory update and audit evidence
  -> later M2 retrieval observes the corrected representation
```

Phase I-3 must not be widened into general memory administration, RelaySOUL mutation, queue scheduling, or daemon lifecycle.

## Planned evaluation and work roadmap

[Phase I-3 through I-9 Evaluation and Work Roadmap](architecture/phase_i3_i9_evaluation_work_roadmap.md) records the planned sequence after the current boundary:

```text
I-3  Correct
I-4  Forget / Hide
I-5  Pin / Unpin
I-6  Merge / Supersession
I-7  Held Apply / Discard
I-8  Secondary MEM consolidation
I-9  RelaySOUL proposal / intervention / rollback
```

It also defines real SOUL Lab Home conversation, a local one-job runner, I1-G durability, queue scanning, worker supervision, always-on operation, detailed work slices, and three staged evaluation gates. Those items remain planned and do not change the current completion claims on this page.

## Completion boundary (2026-06-24)

- I1-B producer: complete
- B3 lifecycle: complete
- C1-0 through C1-5 complete
- C2 one-job claim/rehydrate/execute adapter: complete
- I1 next-turn Primary MEM recall: complete
- character and namespace isolation: complete
- I2 real SOUL Lab observation: complete
- I1-G pre-enqueue background-finalizer durability: unresolved
- auditable Correct operation: next as Phase I-3

## Safe defaults and compatibility

Current safe defaults remain conservative:

```text
client_history_exclusion_apply_enabled = false
client_history_exclusion_apply_dry_run_only = true
memory.token_budget_truncation_enabled = false
client_instruction_typed_parse_enabled = false
client_instruction_cache_write_enabled = false
client_instruction_cache_write_dry_run_only = true
relayctx_stream_unpack_dry_run_enabled = false
relayctx_stream_unpack_dry_run_only = true
relayctx_tts_adapter_handoff_runtime_enabled = false
relayctx_tts_adapter_handoff_runtime_dry_run_only = true
relaymem_slp_runtime_enqueue_enabled = false
relaymem_slp_runtime_enqueue_dry_run_only = true
relaymem_slp_runtime_enqueue_apply_enabled = false
```

Consequences:

- default `memory_light` compatibility may preserve frontend history until managed apply is intentionally enabled,
- stream suppression and TTS handoff metadata remain default-off,
- Phase 6 source publication/B2 enqueue remains explicitly gated,
- B3/C1-2/C2 are caller-driven boundaries rather than separately configured daemons,
- I1-B never claims or executes a worker inline with visible response delivery,
- all SOUL Lab management and observation routes remain local-only read surfaces.

## Not yet implemented

The runtime does not yet provide:

- complete current-turn-only reconstruction for every compatibility-sensitive request shape,
- active tool-chain reconstruction,
- parser-versioned cache compatibility,
- queue scanner, daemon, or scheduler-driven worker execution,
- restart completion for I1-G's pre-enqueue background-finalizer crash window,
- Secondary MEM consolidation,
- durable correction/forget/pin/merge or held apply/discard operations,
- actual RelaySOUL apply, rollback, or persistence execution,
- RelayLM static serving of SOUL Lab,
- adapter transport delivery, TTS, audio generation, or avatar control,
- complete output-side RelayREF and Output-side RelaySCN,
- complete Runtime Compile Gate v1 taxonomy,
- model-specific exact tokenizer integration,
- `/v1/responses` support.

## Usable runtime path

```text
OpenWebUI
  -> RelayLM http://127.0.0.1:8090/v1
  -> LM Studio http://127.0.0.1:1234/v1
```

The memory write path remains explicitly gated. C1-5 and C2 provide restart-safe protected-source recovery and one exact queued-job execution; Phase I-1 provides ordinary scoped recall; Phase I-2 provides bounded read-only observation. Queue scheduling and the pre-enqueue background-finalizer crash window remain separate unresolved operational boundaries.

## Phase I-2 and I1-G cross-boundary status

- Phase 6-C1-0 through C1-5 complete
- C2 one-job claim/rehydrate/execute adapter: complete
- I1 next-turn Primary MEM recall: complete
- character and namespace isolation: complete
- I2 real SOUL Lab observation: complete
- I1-G pre-enqueue background-finalizer durability: unresolved
- auditable Correct operation: next as Phase I-3

I1-G tracks the process-exit window after visible response delivery but before protected-source and B2 queue publication. Phase I-2 observation receipts do not repair or reclassify that durability gap.
