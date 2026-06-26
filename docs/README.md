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

- [Current project status](PROJECT_STATUS.md) — concise current boundary through completed O0 and UI-B0, completed I1-GA/I1-GB, defined Phase I-4A, completed I-4B read-only resolver/fence boundary, and completed I-4C1 hidden-successor commit
- [Documentation model](DOCUMENTATION_MODEL.md) — AI-first document types, metadata, and authority labels
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md) — detailed status and sequencing, including explicit I1-G and O1 durability/operations tracking
- [Post-I3 evaluation and work roadmap](architecture/post_i3_evaluation_work_roadmap.md) — I-4 through I-9, conversation, operations, parallel work, and evaluation gates
- [Character belief, relationship, and social expression dynamics](architecture/character_belief_relationship_dynamics_design.md) — target observation, belief, relationship, SCN/EMO gain, probing, repair, and multi-user expression model
- [Experimental SOUL replacement and memory bootstrap](relaysoul/experimental_soul_replacement_memory_bootstrap_design.md) — explicitly post-MVP non-destructive SOUL fork with governed memory inheritance and optional provisional virtual memory
- [Phase 6 I1-B runtime enqueue and protected source capture](architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md)
- [Phase 6-C1 Primary MEM worker contract](architecture/phase6c1_primary_mem_worker_contract.md)
- [Phase 6-C1-2 one-claimed worker](architecture/phase6c1_one_claimed_primary_worker_handoff.md)
- [Phase 6-C1-5 durable protected source persistence](architecture/phase6c1_durable_protected_source_persistence.md)
- [Phase 6-C2 one queued-job integration](architecture/phase6c2_one_queued_primary_worker_integration.md)
- [O0 local one-job runner](architecture/o0_local_one_job_runner.md) — bounded one-shot local selection and unchanged C2 delegation
- [O1A two-lane scheduler contract](architecture/o1a_two_lane_scheduler_contract.md) — pure replay-then-queue round, idle disposition, target-only gates, and content-free projection; no production scheduler
- [Integration I1 Primary MEM two-turn recall](architecture/integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-2 real SOUL Lab observation](architecture/phase_i2_real_soul_lab_observation.md)
- [Phase I-3 auditable Primary MEM Correct](architecture/phase_i3_auditable_primary_mem_correct.md)
- [Phase I-4A Primary MEM Forget / Hide contract](architecture/phase_i4_primary_mem_forget_hide_contract.md) — target lifecycle, concurrency, audit, recovery, and retrieval-exclusion contract
- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md) — implemented read-only resolver, shared lock/fence, token, and zero-item history boundary
- [Phase I-4C1 Primary Forget Hidden-Successor Commit](architecture/phase_i4c1_primary_forget_hidden_successor.md) — implemented exact prepare, deterministic hidden page, M3e commit, and recovery-required resolution
- [SOUL Lab UI-B0 real Home conversation](architecture/soul_lab_ui_b0_real_home_conversation.md)
- [I1-G pre-enqueue durable-finalization contract and fault model](architecture/i1g_pre_enqueue_durable_finalization_contract.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)
- [SOUL Lab UI-A7 read-only management projection](architecture/soul_lab_ui_a7_management_projection_handoff.md)
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

O0 is complete: `relaylm-worker --once --config config.yaml` performs bounded non-recursive discovery, selects at most one eligible queued record, securely rereads it, resolves the exact config-owned character partition, and delegates unchanged authority to C2/B3/C1-5/C1-2.

O1A is complete only as a contract and pure deterministic model. It fixes replay-before-queue ordering, at most one delegation per lane, independent queue discovery after replay, lane-local failure isolation, `stop | run_next_round | idle` semantics, and a content-free projection. O1B sealed-record discovery, O1C queue discovery/C2 delegation, O1D fairness/backoff, O1E stale recovery/shutdown, O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented. O1A adds no scheduler config fields, CLI command, polling, sleep, or runtime behavior.

Phase I-2 is complete: SOUL Lab can read the latest completed managed run, validated recent Primary memories, durable held/blocked outcomes, and memories actually included in backend-bound context through loopback-only exact-schema APIs.

Phase I-3 is complete: one real observed Primary MEM can be corrected through revision-fenced preflight and token-gated apply, with durable audit evidence, page/index/log convergence, and later retrieval of only the corrected current revision.

UI-B0 is complete: SOUL Lab Home uses a single unambiguous server-projected route and the existing same-origin RelayLM `/v1/chat/completions` path for bounded non-stream and SSE conversation. Real Runtime and Local Preview sessions are explicit and separate; Stop preserves partial text, Retry does not duplicate the user message, New Conversation resets only browser-local current-session history, and stale character/session/generation/route completions are rejected.

I1-GA and I1-GB are complete: the contract/fault model and bounded durable base/segment/seal publication now run before protected response release in explicit apply mode. I1-GC one-record restart replay and completion convergence, I1-GD retention/cleanup, and I1-GE full production crash integration remain unimplemented; I1-G overall is in progress.

Phase I-4A defines the target contract. Phase I-4B is complete for the canonical read-only current-state resolver, shared Correct/Forget mutation fence, Forget preflight, five-minute token validation, and bounded zero-item history. Phase I-4C1 is complete for exact token/reason revalidation, shared revision claim, immutable Forget prepare, deterministic hidden successor, existing M3c/M3d/M3e publication, canonical reread, one-winner concurrency, and `hidden / recovery_required / false` resolution. I-4C2 recovery/replay/tombstone, I-4D M3f/M3g and M2 exclusion, the loopback mutation API, and the SOUL Lab Forget UI remain unimplemented.

UI-B0 does not create browser-owned SOUL, MEM, namespace, backend, credential, prompt, or worker authority. I1-GC through I1-GE, Phase I-4C2 through I-4F, O1/O2/O3 automatic operation, later memory governance, Secondary MEM, RelaySOUL apply/rollback, static UI serving, TTS/audio/avatar, and always-on operation remain separate work.

The planned sequence is documented in [Post-I3 Evaluation and Work Roadmap](architecture/post_i3_evaluation_work_roadmap.md).

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
- [Character belief, relationship, and social expression dynamics](architecture/character_belief_relationship_dynamics_design.md)
- [Experimental SOUL replacement and memory bootstrap](relaysoul/experimental_soul_replacement_memory_bootstrap_design.md)
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
- [O0 Local one-job runner](architecture/o0_local_one_job_runner.md)
- [O1A Two-Lane Scheduler Contract](architecture/o1a_two_lane_scheduler_contract.md)
- [Integration I1 Primary MEM two-turn recall](architecture/integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-2 Real SOUL Lab Observation](architecture/phase_i2_real_soul_lab_observation.md)
- [Phase I-3 Auditable Primary MEM Correct](architecture/phase_i3_auditable_primary_mem_correct.md)
- [Phase I-4A Primary MEM Forget / Hide Contract](architecture/phase_i4_primary_mem_forget_hide_contract.md)
- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md)
- [Phase I-4C1 Primary Forget Hidden-Successor Commit](architecture/phase_i4c1_primary_forget_hidden_successor.md)
- [SOUL Lab UI-B0 Real Home Conversation](architecture/soul_lab_ui_b0_real_home_conversation.md)
- [I1-G Pre-enqueue Durable-finalization Contract](architecture/i1g_pre_enqueue_durable_finalization_contract.md)
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

The ordinary managed path is complete through observe/correct/retrieve, O0 manual one-shot execution, and the text-first Home experiment surface. I1-GB publishes restart evidence before visible completion, but I1-GC restart replay/completion convergence and I1-GD/I1-GE remain unimplemented. O1A defines the bounded two-lane round and idle contract only; O1B-O1F production scheduling work remains unimplemented. Phase I-4A defines the target Forget / Hide contract, I-4B completes the read-only resolver/shared-fence boundary, and I-4C1 completes hidden-successor commit ownership; I-4C2 through I-4F recovery, exclusion, UI, and validation remain unimplemented. O2/O3 and later governance remain separate roadmap work.
