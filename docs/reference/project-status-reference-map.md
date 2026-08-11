---
relaylm_doc_type: reference
relaylm_authority: project_status_reference_map
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: project_status
relaylm_update_trigger:
  - a linked implementation handoff or evidence path changes
  - established implementation boundary notes change
  - offline tooling, latency, or mobile-dogfood addenda change
relaylm_not_authoritative_for:
  - current implementation status
  - roadmap sequencing
  - exact runtime or schema behavior
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - ../architecture/project_execution_plan.md
---
# Project Status Reference Map

Last reviewed: 2026-07-23 JST

This page preserves established-boundary notes, completed-slice references, implementation/evidence links, and runtime-non-authoritative addenda. Current state remains owned by [RelayLM Project Status](../PROJECT_STATUS.md); roadmap ordering remains owned by the [Project Execution Plan](../architecture/project_execution_plan.md).

## Completed foundation inventory

The following completed boundaries are retained here as reference rather than repeated in the current-status authority:

- managed-route correctness through Phase 5-C, pre-stream hardening through Phase 5-D2, and Stream Unpack through Phase 5.5;
- RelaySLP durable enqueue, fenced lifecycle, one-job execution, local worker, O1 scheduler, and opt-in O2/O3 process operation;
- RelayMEM M1/M2 and executable M3a-M3h, including scoped recall and the E1-R5 fallback fold-in;
- I1-G durable finalization and restart/recovery lifecycle;
- Primary MEM Correct, Forget/Hide, Pin/Unpin, Held Apply/Discard, and their current UI/API boundaries;
- P0-PIPE ordering, ACG-1 through ACG-6, CW-A1 through CW-A5, and current SOUL Lab management surfaces;
- E1-R1 through E1-R5 and the Wave 3 through Wave 7 integration tracks;
- PM-D3 and PM-D5 through PM-D8 closure.

## O1/O2/O3 boundary notes

O1 is complete through the validation-only caller-invoked local scheduler boundary. O2 is an opt-in supervised local scheduler service above O1E. O3 is an opt-in local CLI/process wrapper around O2. Neither is app-embedded, browser authority, default-on, or new memory mutation authority.

The former O1B status detail is historical reference: O1B performs one bounded, non-recursive sealed-record inventory, deterministic eligible-record selection, canonical reread, and at most one I1-GC delegation. It does not itself define the O1C queue algorithm, scheduler loop, polling, supervision, shutdown, or always-on operation.

## Phase 6 and E1 boundary notes

B0-B3 durable enqueue and fenced lifecycle, C1-5 claim-independent protected capture, C2 one-job claim/rehydrate/execute, next-turn Primary MEM recall, and character/namespace isolation are complete.

E1-R4 remains request-side grounding rather than post-hoc visible-response rewriting. E1-R5 remains a bounded query-hinted fallback; M2 remains preferred and no new mutation, scheduler, browser-trust, RelaySOUL, or media authority is added.

## Analyzer Candidate Governance boundary

ACG-1 is the shared contract/helper slice. ACG-2 Grounded Recall Detail Safety, ACG-3 Retrieval Query Normalization, ACG-4 Reference/Intent Analyzer consolidation, ACG-5 RelayEMO scene cleanup, and ACG-6 structured SCN classifier/scene-wiki boundary are complete.

ACG classifier and scene-wiki matches remain non-authoritative by default. They do not grant permissive policy or page mutation authority.

## Character Workspace boundary

CW-A1 file-first sources/parser contracts, CW-A2 compiler projections/KV-cache tiers, CW-A3 browser UI rebuild, CW-A4 dry-run-first MEM/SCENE/REL candidate planning, and CW-A5 creation/templates/showcase import are complete.

Home remains on the existing RelayLM `/v1/chat/completions` path. Real Runtime and Local Preview remain separate. No-character startup enters explicit creation/import; imported runtime/build/state artifacts are rejected and workspace commit does not auto-activate a character.

## Implementation handoff and evidence map

- [P0 RelayREL / RelaySCN / RelayEMO Ordering Fix](../architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md)
- [Analyzer Candidate Governance roadmap](../architecture/analyzer_candidate_governance.md)
- [ACG-1](../architecture/acg1_analyzer_candidate_governance_contract.md), [ACG-2](../architecture/acg2_grounded_recall_detail_safety.md), [ACG-3](../architecture/acg3_retrieval_query_normalization.md), [ACG-4](../architecture/acg4_reference_intent_analyzer.md), [ACG-5](../architecture/acg5_relayemo_scene_cleanup.md), [ACG-6](../architecture/acg6_scene_wiki_classifier.md)
- [CW-A1](../architecture/cw_a1_file_first_source_tree_parser_contracts.md), [CW-A2](../architecture/cw_a2_workspace_compiler_projections.md), [CW-A3](../architecture/cw_a3_character_workspace_ui_rebuild.md), [CW-A4](../architecture/cw_a4_slp_workspace_maintenance_candidates.md), [CW-A5](../architecture/cw_a5_character_creation_templates_showcase_import.md)
- [O2 Supervised Scheduler Service](../architecture/o2_supervised_scheduler_service.md) and [O3 Always-On Local Scheduler](../architecture/o3_always_on_local_scheduler.md)
- [PM-D5](../architecture/pm_d5_relaymem_flat_store_compatibility_removal.md), [PM-D6](../architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md), and [PM-D7](../architecture/pm_d7_runtime_install_hook_fold_in.md)
- [E1-R3](../architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md), [E1-R4](../architecture/e1r4_retrieval_response_grounding.md), and [E1-R5](../architecture/e1r5_primary_mem_recall_candidate_bridge.md)
- [Wave 7 convergence](../evidence/waves/wave7_cross_slice_convergence_audit.md) and [E1-R5 post-correction convergence](../evidence/waves/e1r5_post_wave7_correction_convergence_audit.md)
- [v0.1 readiness](../release/v0.1-release-readiness.md) and [final main validation/tag receipt](../evidence/releases/v0.1-final-main-validation-tag-receipt.md)

## Runtime-non-authoritative addenda

Offline Twin Extraction and approved-review import tooling remain caller-invoked and runtime-non-contact. They do not directly write MEM/SOUL/REL/Primary MEM or auto-promote private material. See [Twin Extraction](../operations/twin-extraction.md) and [Twin Review Import to CW-A4](../operations/twin-review-to-workspace-candidates.md).

LAT-1 and LAT-2 remain measurement-only infrastructure. They do not change request behavior, search algorithms, timeouts, degradation policy, SSE payloads, or latency guarantees. See [LAT-1](../architecture/lat1_latency_measurement.md) and [LAT-2](../architecture/lat2_mobile_perceived_latency.md).

Mobile dogfood documents remain local evaluation/target guidance, not external-publication acceptance or runtime authority. See [Mobile Dogfood Entry](../operations/mobile-dogfood-entry.md) and [Mobile Dogfood Observation](../operations/mobile-dogfood-observation.md).
