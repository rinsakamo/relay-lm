---
relaylm_doc_type: documentation_index
relaylm_authority: repository_documentation_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - documentation entry points change
  - canonical authority ordering changes
  - placement rules change
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact schema details
  - implementation phase completion claims
relaylm_current_status_source: PROJECT_STATUS.md
---
# RelayLM Documentation

This page is the entry point for RelayLM documentation.

RelayLM documentation is AI-first: documents should remain understandable when retrieved partially by ChatGPT, Codex, or another assistant. Use [Documentation Model](DOCUMENTATION_MODEL.md) for document types, metadata, status labels, and authority rules.

## Start here

- [Current project status](PROJECT_STATUS.md) — concise current boundary through completed Phase I-3
- [Documentation model](DOCUMENTATION_MODEL.md) — AI-first document types, metadata, and authority labels
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md) — detailed status and sequencing, including explicit I1-G durability tracking
- [Post-I3 evaluation and work roadmap](architecture/post_i3_evaluation_work_roadmap.md) — planned I-4 through I-9, SOUL Lab conversation, operations, parallel work, and evaluation gates
- [Phase 6 I1-B runtime enqueue and protected source capture](architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md) — ordinary managed request-runtime enqueue and finalized-turn source production
- [Phase 6-C1 Primary MEM worker contract](architecture/phase6c1_primary_mem_worker_contract.md) — exact active-lease, source, retry, crash, and outcome boundary
- [Phase 6-C1-2 one-claimed worker](architecture/phase6c1_one_claimed_primary_worker_handoff.md) — production execution of one exact claimed B3 job
- [Phase 6-C1-4 integrated worker fault smoke](architecture/phase6c1_integrated_worker_fault_smoke_handoff.md) — crash, lease, lock, race, corruption, and leakage convergence
- [Phase 6-C1-5 durable protected source persistence](architecture/phase6c1_durable_protected_source_persistence.md) — source-before-queue publication and restart rehydration
- [Phase 6-C2 one queued-job integration](architecture/phase6c2_one_queued_primary_worker_integration.md) — exact queued record claim, rehydrate, worker execute, and terminal transition
- [Integration I1 Primary MEM two-turn recall](architecture/integration_i1_primary_mem_two_turn_recall.md) — ordinary next-turn retrieval, scope isolation, and bounded RelayCTX injection
- [Phase I-2 real SOUL Lab observation](architecture/phase_i2_real_soul_lab_observation.md) — real latest-run, formed/held/blocked, and used-memory read integration
- [Phase I-3 auditable Primary MEM Correct](architecture/phase_i3_auditable_primary_mem_correct.md) — completed observe/correct/retrieve loop and exact correction authority
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md) — current producer/consumer connection and remaining migration boundary
- [RelayMEM MVP implementation plan](architecture/relaymem_mvp_implementation_plan.md) — Primary MEM persistence, worker integration, recall, Lab observation, and later memory operations
- [SOUL Lab UI-A7 read-only management projection](architecture/soul_lab_ui_a7_management_projection_handoff.md) — local-only secret-free Lab API reads and mock fallback
- [Architecture docs](architecture/README.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Contract docs](contracts/README.md)
- [Smoke and validation docs](smoke/README.md)
- [MVP summaries and milestone notes](mvp/README.md)
- [RelaySOUL design and gate docs](relaysoul/README.md)
- [Config schema](config_schema.md)
- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)

## Current status

Use [Project Status](PROJECT_STATUS.md) for the current developer-facing view and [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) for detailed sequencing.

Phase 5.5 Stream Unpack / TTS handoff preparation is complete for RelayLM Core. Concrete TTS execution, audio queueing, adapter delivery, Live2D/avatar mapping, motion, and lip-sync remain SOUL Lab Runtime MVP responsibilities.

Integration Milestone I1 is complete through ordinary runtime enqueue, B3 lifecycle, C1-0 through C1-5, C2 one-job execution, and Phase I-1 next-turn Primary MEM recall with character/namespace isolation and bounded RelayCTX injection.

Phase I-2 is complete: SOUL Lab can read the latest completed managed run, validated recent Primary memories, durable held/blocked outcomes, and memories actually included in backend-bound context through loopback-only exact-schema APIs. Server-owned data and local preview data remain explicitly separate.

Phase I-3 is complete: one real observed Primary MEM can be corrected through revision-fenced preflight and explicit token-gated apply, with durable audit evidence, page/index/log convergence, and later retrieval of only the corrected current revision. I1-G, automatic queue selection, broader memory governance, Secondary MEM, RelaySOUL apply/rollback, and real SOUL Lab Home conversation remain separate work.

The planned sequence after I-3 is documented in [Post-I3 Evaluation and Work Roadmap](architecture/post_i3_evaluation_work_roadmap.md).

Use [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) before treating proposed schemas, future execution gates, or historical compatibility artifacts as current behavior.

## Canonical precedence

When documents disagree:

1. `pipeline_responsibility_design.md` owns component names, responsibility, and target order.
2. `pipeline_implementation_plan.md` owns implementation status and sequencing.
3. Dedicated current contracts own implemented schemas and bounded behavior.
4. `current_target_migration_guide.md` owns compatibility/target interpretation.
5. `docs/mvp/` and `docs/architecture/archive/` are historical evidence.

`DOCUMENTATION_MODEL.md` owns document type metadata and AI reading rules; it does not override the content authority list above.

## Primary architecture entry points

- [Architecture docs index](architecture/README.md)
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md)
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md)
- [Post-I3 evaluation and work roadmap](architecture/post_i3_evaluation_work_roadmap.md)
- [Phase 6 Asynchronous RelaySLP bounded slice](architecture/phase6_async_relayslp_bounded_slice.md)
- [Phase 6-A1 Job admission](architecture/phase6a1_relayslp_job_admission_contract.md)
- [Phase 6-A2 Response-finalization handoff](architecture/phase6a2_relayslp_response_handoff_contract.md)
- [Phase 6-B0 Durable queue contract](architecture/phase6b0_relayslp_durable_queue_contract.md)
- [Phase 6-B1 Dispatch preflight](architecture/phase6b1_relayslp_dispatch_preflight.md)
- [Phase 6-B2 Atomic durable enqueue](architecture/phase6b2_relayslp_atomic_durable_enqueue.md)
- [Phase 6-B3 Fenced queue state helpers](architecture/phase6b3_relayslp_queue_state_helpers.md)
- [Phase 6 I1-B Runtime enqueue and protected source capture](architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md)
- [Phase 6-C1 Primary MEM worker contract](architecture/phase6c1_primary_mem_worker_contract.md)
- [Phase 6-C1-1 RelayMEM Primary pipeline compose](architecture/phase6c1_relaymem_primary_pipeline_compose.md)
- [Phase 6-C1-2 One-claimed Primary MEM worker](architecture/phase6c1_one_claimed_primary_worker_handoff.md)
- [Phase 6-C1-3 Primary worker outcome classifier](architecture/phase6c1_primary_worker_outcome_classifier.md)
- [Phase 6-C1-4 Integrated worker fault smoke](architecture/phase6c1_integrated_worker_fault_smoke_handoff.md)
- [Phase 6-C1-5 Durable protected source persistence](architecture/phase6c1_durable_protected_source_persistence.md)
- [Phase 6-C2 One queued-job Primary worker integration](architecture/phase6c2_one_queued_primary_worker_integration.md)
- [Integration I1 Primary MEM two-turn recall](architecture/integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-2 Real SOUL Lab Observation](architecture/phase_i2_real_soul_lab_observation.md)
- [Phase I-3 Auditable Primary MEM Correct](architecture/phase_i3_auditable_primary_mem_correct.md)
- [Completed Phase 5.5 Stream Unpack bounded slice](architecture/phase5_5_stream_unpack_bounded_slice.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Client history authority contract](architecture/client_history_authority_contract.md)
- [Client instruction authority contract](architecture/client_instruction_authority_contract.md)
- [Runtime architecture](architecture/runtime_architecture.md)
- [Runtime operational requirements](architecture/runtime_operational_requirements.md)
- [Runtime compile gate design](architecture/runtime_compile_gate_design.md)
- [Managed-route fallback authority contract](architecture/managed_route_fallback_contract.md)
- [RelayRUN runtime checkpoint design](architecture/relayrun_runtime_checkpoint_design.md)
- [Context packing design](architecture/context_packing_design.md)
- [Memory lifecycle design](architecture/memory_lifecycle_design.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)
- [RelayMEM MVP implementation plan](architecture/relaymem_mvp_implementation_plan.md)
- [RelayMEM SLP execution design](architecture/relaymem_slp_execution_design.md)
- [RelayMEM-M3d Primary writer handoff](architecture/relaymem_m3d_primary_writer_handoff.md)
- [RelayMEM-M3e Atomic Primary page writer](architecture/relaymem_m3e_atomic_primary_page_writer.md)
- [RelayMEM-M3f Index/log reconciliation preflight](architecture/relaymem_m3f_primary_index_log_reconciliation_preflight.md)
- [RelayMEM-M3g Index/log reconciliation apply](architecture/relaymem_m3g_primary_index_log_reconciliation_apply.md)
- [RelayMEM-M3h Reconciliation recovery audit](architecture/relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md)
- [Scene lifecycle design](architecture/scene_lifecycle_design.md)
- [AI VTuber pipeline profile](architecture/ai_vtuber_pipeline_profile.md)
- [SOUL Lab UI MVP](architecture/soul_lab_ui_mvp.md)
- [SOUL Lab UI-A0 / UI-A1 handoff](architecture/soul_lab_ui_a0_a1_handoff.md)
- [SOUL Lab UI-A2 Adoption handoff](architecture/soul_lab_ui_a2_adoption_handoff.md)
- [SOUL Lab UI-A3 Communication handoff](architecture/soul_lab_ui_a3_communication_handoff.md)
- [SOUL Lab UI-A4 Pod handoff](architecture/soul_lab_ui_a4_pod_handoff.md)
- [SOUL Lab UI-A5 Memory Inspector handoff](architecture/soul_lab_ui_a5_memory_inspector_handoff.md)
- [SOUL Lab UI-A6 Shared Shell / Settings handoff](architecture/soul_lab_ui_a6_shared_shell_settings_handoff.md)
- [SOUL Lab UI-A7 Read-only Management Projection handoff](architecture/soul_lab_ui_a7_management_projection_handoff.md)
- [SOUL Lab Runtime MVP](architecture/soul_lab_runtime_mvp.md)
- [RelayINT MVP design](architecture/relayint_mvp_design.md)

## Contracts and safety gates

Contract, artifact, schema, approval, and gate documents are collected under `docs/contracts/`.

Current compile behavior includes typed compile decisions, content-free diagnostics, and bounded history-exclusion apply contracts v0/v1. Complete Runtime Compile Gate v1 remains target work.

## MVP and historical material

`docs/mvp/` contains historical implementation snapshots. `docs/architecture/archive/` preserves superseded rationale. Neither overrides current architecture, contracts, project status, or implementation sequencing.

## Setup, smoke, and validation

- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)
- [Smoke and validation docs](smoke/README.md)
- [OpenWebUI + RelayLM troubleshooting](smoke/openwebui_lmstudio_troubleshooting.md)

Run the Markdown-link audit after moving, renaming, or adding links:

```bash
python scripts/relaylm_docs_link_check.py
```

## Documentation maintenance

AI-first maintenance rules:

- add front matter to active current/architecture/plan/contract docs,
- include type, authority, status, volatility, owner, update trigger, and non-authority fields,
- keep current/target/compatibility/historical status explicit,
- do not encode source text, prompts, traces, cache bodies, or runtime-private data in metadata,
- when an implemented handoff changes milestone state, review Project Status, the implementation plan, this index, the architecture index, `config_schema.md`, the Current/Target Boundary Matrix and affected sections, stale TODO/future-tense text in related plans, and status-checking smoke scripts together.

Placement rules:

- repository-wide current status -> `docs/PROJECT_STATUS.md`
- completed or active bounded handoffs -> `docs/architecture/`
- cross-cutting architecture and pipeline docs -> `docs/architecture/`
- historical rationale -> `docs/architecture/archive/`
- MVP snapshots -> `docs/mvp/`
- schemas and contracts -> `docs/contracts/`
- smoke and troubleshooting -> `docs/smoke/`
- RelaySOUL governance -> `docs/relaysoul/`

Current Phase 6 handoff is [Phase 6-C2 One Queued Primary Worker Integration](architecture/phase6c2_one_queued_primary_worker_integration.md). Phase I-1 two-turn recall, Phase I-2 real Lab observation, and Phase I-3 auditable Correct are complete. Post-I3 planned work is documented in the [Post-I3 Evaluation and Work Roadmap](architecture/post_i3_evaluation_work_roadmap.md).

## Integration I1 through Phase I-3 completion

The ordinary managed path is complete through observe/correct/retrieve: Turn 1 can publish and execute one durable Primary MEM job through C2, Turn 2 can select the resulting memory through existing M2 and inject it through RelayCTX, SOUL Lab can observe the real result, and Phase I-3 can create an auditable successor revision that later retrieval resolves as current.

I1-G remains unresolved: a process exit after visible-response delivery but before protected-source and B2 queue publication may still lose that deferred turn.
