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

RelayLM documentation is AI-first. Documents must remain correct when retrieved partially; current documents must not rely on a later "supersedes earlier text" correction inside the same file.

## Start here

- [Current project status](PROJECT_STATUS.md) — the single current implementation status authority.
- [v0.1 Release Readiness Assessment](release/v0.1-release-readiness.md) — current readiness assessment for the validated and tagged v0.1 boundary; the frozen tag receipt is [v0.1 Final Main-HEAD Validation and Tag Receipt](evidence/releases/v0.1-final-main-validation-tag-receipt.md).
- [Project execution plan](architecture/project_execution_plan.md) — the single MVP execution plan and post-MVP roadmap authority.
- [Documentation governance architecture](architecture/documentation-governance.md) — responsibility and control flow for active authority, retained records, synthesis, validation, and Git-history retirement.
- [Repository maintenance system](architecture/repository-maintenance-system.md) — discovery, reviewed classification, deterministic projection, bounded cleanup, and retirement architecture.
- [Documentation synthesis and retirement](operations/documentation-synthesis-and-retirement.md) — the repeatable D2-D6 operator procedure.
- [File-first Character Workspace design](architecture/file_first_character_workspace_design.md) — the current product direction reset target: editable Markdown character sources compiled into runtime projections.
- [Character Workspace Source Compiler](architecture/character-workspace/source-compiler.md) — the current source tree, parser/validation, and deterministic compiler architecture for the file-first Character Workspace reset.
- [Character Workspace Creation and Import](architecture/character-workspace/creation-and-import.md) — the current bounded creation, template, and local-import architecture for deterministic Character Workspace creation, with exact semantics in the [Character Workspace Creation and Commit Contract](contracts/character-workspace/creation-commit.md).
- [O2 Supervised Scheduler Service](architecture/o2_supervised_scheduler_service.md) — the current opt-in supervised local scheduler service boundary.
- [O3 Always-On Local Scheduler](architecture/o3_always_on_local_scheduler.md) — the current opt-in local CLI/process wrapper boundary.
- [RelayREL relationship design](architecture/relayrel_relationship_design.md) — target-specific relationship state, relationship-conditioned interaction policy, and `RELATIONSHIP.md` / `relationships/<target>.md` ownership.
- [Showcase, Public Starter, and Product Knowledge Ownership](architecture/character-workspace/showcase-starter-product-knowledge.md) — the accepted target ownership split between developer showcase characters, the public adoptable starter, user-authored/imported characters, and official RelayLM product knowledge.
- [Documentation model](DOCUMENTATION_MODEL.md) — document types, metadata, authority, AI reading rules, and the parallel implementation/convergence flow.
- [Pipeline Responsibilities](architecture/pipeline-responsibilities.md) — component responsibility and canonical target order.
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) — compatibility interpretation.
- [E1 MVP evaluation consolidation](architecture/e1_evaluation_consolidation.md) — current E1 evidence inventory and completed E1-R1 through E1-R5 quality work.
- [Implementation evidence](evidence/implementation/README.md) — closed transitional implementation records and focused historical MVP evidence; new PR evidence normally remains in Git, CI, and the pull request.

The current product target is no longer only a memory-governance proxy. The MVP direction is a Markdown/file-first Character Workspace plus governed runtime behavior for relationship-, scene-, emotion-, memory-, and context-aware conversation.

## Parallel implementation documentation rule

Implementation PRs record bounded implementation and validation evidence in the pull request, exact-head CI, and Git history. They do not create a permanent completion report or handoff by default. A convergence PR reads the merged pull requests and validation results, then updates shared current-status documents only when repository-wide synthesis is required. Existing committed completion reports remain transitional evidence during D2-D6 and do not open a later wave or release/evaluation gate.

## Product-critical boundaries

- [File-first Character Workspace design](architecture/file_first_character_workspace_design.md)
- [Character Workspace Source Tree Contract](contracts/character-workspace/source-tree.md)
- [Character Workspace Maintenance Candidates Contract](contracts/character-workspace/maintenance-candidates.md)
- [Character Workspace Creation and Commit Contract](contracts/character-workspace/creation-commit.md)
- [RelayREL relationship design](architecture/relayrel_relationship_design.md)
- [Character Workspace Creation and Import](architecture/character-workspace/creation-and-import.md)
- [P0 RelayREL / RelaySCN / RelayEMO ordering fix](architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md)
- [Analyzer Candidate Contract](contracts/analyzer-candidate.md)
- [Query Detail Analyzer Contract](contracts/query-detail-analyzer.md)
- [Retrieval Query Analyzer Contract](contracts/retrieval-query-analyzer.md)
- [Reference/Intent Analyzer Contract](contracts/reference-intent-analyzer.md)
- [RelayEMO Scene Hint Contract](contracts/relayemo-scene-hint.md)
- [Scene Classifier Contract](contracts/scene-classifier.md)
- [Analyzer Candidate Governance](architecture/analyzers/candidate-governance.md)
- [Phase 6 I1-B runtime enqueue and protected source capture](architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md)
- [Phase 6-C1 Primary MEM worker contract](architecture/phase6c1_primary_mem_worker_contract.md)
- [Phase 6-C1-2 one-claimed worker](architecture/phase6c1_one_claimed_primary_worker_handoff.md)
- [Phase 6-C1-5 durable protected source persistence](architecture/phase6c1_durable_protected_source_persistence.md)
- [Phase 6-C2 one queued-job integration](architecture/phase6c2_one_queued_primary_worker_integration.md)
- [O0 local one-job runner](architecture/o0_local_one_job_runner.md)
- [O1A two-lane scheduler contract](architecture/o1a_two_lane_scheduler_contract.md)
- [O1B sealed I1-G replay lane](architecture/o1b_sealed_i1g_replay_lane.md)
- [O1C eligible B2/B3 queue lane](architecture/o1c_eligible_b2_queue_lane.md)
- [O1D1 accepted scheduler gates and one production round](architecture/o1d1_production_scheduler_round.md)
- [O1D2 deterministic scheduler policy](architecture/o1d2_scheduler_policy.md)
- [O1E scheduler operational controls](architecture/o1e_scheduler_operational_controls.md)
- [O1F operational validation](architecture/o1f_operational_validation.md)
- [O2 supervised scheduler service](architecture/o2_supervised_scheduler_service.md)
- [O3 always-on local scheduler](architecture/o3_always_on_local_scheduler.md)
- [O1 manual one-round operations runbook](operations/o1-manual-one-round.md)
- [PM-D5 RelayMEM flat-store compatibility removal](architecture/pm_d5_relaymem_flat_store_compatibility_removal.md)
- [PM-D6 RelayINT native artifact / RelayREF wrapper removal](architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md)
- [PM-D7 runtime install hook fold-in](architecture/pm_d7_runtime_install_hook_fold_in.md)
- [I1-G durable-finalization contract and completed GA-GE boundaries](architecture/i1g_pre_enqueue_durable_finalization_contract.md)
- [I1-GD durable-finalization retention and isolation lifecycle](architecture/i1gd_durable_finalization_retention_cleanup.md)
- [Integration I1 Primary MEM two-turn recall](architecture/integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-4A Primary MEM Forget / Hide contract](architecture/phase_i4_primary_mem_forget_hide_contract.md)
- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md)
- [Phase I-4D Primary retrieval exclusion](architecture/phase_i4d_primary_retrieval_exclusion.md)
- [Phase I-5A Pin / Unpin contract and read-only preflight](architecture/phase_i5_pin_unpin_contract.md)
- [SOUL Lab Memory Pin / Unpin management contract](contracts/ui/memory-pin-unpin-management.md)
- [Held Apply / Discard governance contract](contracts/memory/held-governance.md)
- [SOUL Lab Home conversation contract](contracts/ui/home-conversation.md)
- [SOUL Lab lifecycle visibility contract](contracts/ui/lifecycle-visibility.md)
- [E1 MVP evaluation consolidation](architecture/e1_evaluation_consolidation.md)
- [E1-R1 trusted Home scene admission](architecture/e1r1_trusted_home_scene_admission.md)
- [E1-R2 character-store bootstrap command](architecture/e1r2_character_store_bootstrap.md)
- [E1-R3 provenance-preserving formation summary](architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md)
- [E1-R4 retrieval-response grounding](architecture/e1r4_retrieval_response_grounding.md)
- [E1-R5 Primary MEM recall candidate discovery bridge](architecture/e1r5_primary_mem_recall_candidate_bridge.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)
- [ST-1 Subjective MEM Commit Runtime](architecture/st1_subjective_mem_commit_runtime.md)
- [Subjective MEM Canonical Markdown v1 Physical Contract](contracts/subjective-mem-canonical-markdown-v1.md)
- [Architecture documentation index](architecture/README.md)

## Current status pointer

Current runtime and implementation status is intentionally not summarized here. Read [Current project status](PROJECT_STATUS.md) for the current boundary. At the time this index was reviewed, Wave 3 through Wave 7 implementation tracks and W3-INT through W7-INT are merged, E1-R5 is converged as a post-Wave-7 correction, P0-PIPE is complete in PR #458, ACG-1 through ACG-6 analyzer governance slices are complete, CW-A1 through CW-A5 Character Workspace reset slices are complete, O2/O3 supervised local scheduler operation is complete as opt-in local operation support, and PM-D5 through PM-D8 compatibility/debt fold-in slices are complete. PM-D8 completes the E1-R5 bridge canonical adapter fold-in in PR #491. O1F remains validation-only and O2/O3 do not add app-embedded, browser-owned, default-on, or independently mutation-authoritative scheduling.

## Wave 8 implementation evidence

- [MVP eval runner completion report](evidence/implementation/mvp_eval_runner_completion_report.md) — source PR #451. This is an operator-facing evaluation-flow convenience only and does not mark O2/O3 complete.
- [O2/O3 and PM-D5-D7 docs convergence completion report](evidence/implementation/o2_o3_pm_d5_d7_docs_convergence_completion_report.md) — source PR #490. Historical documentation convergence evidence only.
- [E2 Value Smoke Harness completion report](evidence/implementation/e2_value_smoke_harness_completion_report.md) — source PR #481. Harness implementation evidence only; the later human quality judgment remains separate and local-only.
- [Twin Extraction Tooling completion report](evidence/implementation/twin_extraction_completion_report.md) — source PR #503. Offline runtime-non-contact preprocessing/extraction tooling only; no MEM/SOUL ingestion or RelaySLP runtime wiring.
- [LAT-1 Latency Measurement completion report](evidence/implementation/lat1_latency_measurement_completion_report.md) — source PR #505. Measurement-only evidence; no optimization, response-time guarantee, timeout, degradation ladder, search-algorithm, ANN/vector DB, Secondary MEM, SSE timing, O2/O3, or TTS/avatar behavior change.

## Wave 7 implementation evidence

- [Wave 7 Cross-Slice Convergence Audit](evidence/waves/wave7_cross_slice_convergence_audit.md)
- [E1-R3 provenance-preserving formation summary](architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md)
- [E1-R3 completion report](evidence/implementation/e1r3_completion_report.md)
- [E1-R4 retrieval-response grounding](architecture/e1r4_retrieval_response_grounding.md)
- [E1-R4 completion report](evidence/implementation/e1r4_completion_report.md)
- [E1-R5 Primary MEM recall candidate discovery bridge](architecture/e1r5_primary_mem_recall_candidate_bridge.md)
- [E1-R5 completion report](evidence/implementation/e1r5_completion_report.md)
- [E1-R5 Post-Wave-7 Correction Convergence Audit](evidence/waves/e1r5_post_wave7_correction_convergence_audit.md)

## Wave 6 implementation evidence

- [Wave 6 Cross-Slice Convergence Audit](evidence/waves/wave6_cross_slice_convergence_audit.md)
- [O1F completion report](evidence/implementation/o1f_completion_report.md)
- [I-5B completion report](evidence/implementation/i5b_completion_report.md)
- [I-7C completion report](evidence/implementation/i7c_completion_report.md)
- [E1-R1 completion report](evidence/implementation/e1r1_completion_report.md)
- [E1-R2 completion report](evidence/implementation/e1r2_completion_report.md)
- [Docs Horizontal Status Sweep completion report](evidence/implementation/docs_horizontal_status_sweep_completion_report.md)
- [O1F operational validation](architecture/o1f_operational_validation.md)
- [E1-R1 trusted Home scene admission](architecture/e1r1_trusted_home_scene_admission.md)
- [E1-R2 character-store bootstrap command](architecture/e1r2_character_store_bootstrap.md)

## Wave 5 / E1 evaluation evidence

- [Wave 5 Cross-Slice Convergence Audit](evidence/waves/wave5_cross_slice_convergence_audit.md)
- [O1E completion report](evidence/implementation/o1e_completion_report.md)
- [I-4F completion report](evidence/implementation/i4f_completion_report.md)
- [E1 completion report](evidence/implementation/e1_completion_report.md)
- [O1E scheduler operational controls](architecture/o1e_scheduler_operational_controls.md)
- [E1 MVP evaluation consolidation](architecture/e1_evaluation_consolidation.md)
- [E1 local runtime evaluation](evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md)

## Wave 4 implementation evidence

- [Wave 4 Cross-Slice Convergence Audit](evidence/waves/wave4_cross_slice_convergence_audit.md)
- [O1D2 completion report](evidence/implementation/o1d2_completion_report.md)
- [I-4E completion report](evidence/implementation/i4e_completion_report.md)
- [UI-B1A completion report](evidence/implementation/ui_b1a_completion_report.md)
- [I-5A completion report](evidence/implementation/i5a_completion_report.md)
- [I-7A/B completion report](evidence/implementation/i7ab_completion_report.md)

## Offline tooling and runbooks

- [Mobile Dogfood Entry](operations/mobile-dogfood-entry.md) — target boundary for future single-owner Cloudflare access; external publication is blocked until a dedicated chat-only origin and negative-path acceptance evidence exist. Do not expose Vite, RelayLM `/v1`, `/lab/api`, LM Studio, or management/debug surfaces.
- [Mobile Dogfood Observation Method](operations/mobile-dogfood-observation.md) — daily/weekly single-owner observation method and local-only record templates ([daily note](templates/evaluation/mobile-dogfood-daily-note.md), [weekly review](templates/evaluation/mobile-dogfood-weekly-review.md), [summary report stub](templates/evaluation/mobile-dogfood-summary-report.md)) for conversation quality, MEM behavior, and perceived latency; content-bearing transcripts stay local-only, and this adds no runtime, Cloudflare automation, or MEM/SOUL mutation behavior.
- [Twin Extraction prompt specification](operations/twin-extraction-prompts.md) — caller-invoked, bounded, runtime-non-contact offline material-extraction prompts and tooling notes.
- [Twin Extraction runbook](operations/twin-extraction.md) — execution steps for the offline preprocessing/batch-runner/merge CLIs, including the review import bridge (`scripts/relaylm_twin_review_import_bridge.py`) that turns an approved `twin_extraction_review.json` into `.relaylm/sources/imports/twin-extraction/` governed import sources for CW-A4. This tooling does not connect to MEM/SOUL bootstrap or the RelaySLP pipeline; the bridge does not write MEM/SOUL/REL/Primary MEM or any uppercase source directly, and `private_only` material is never auto-promoted.
- [Twin Review Import -> CW-A4 Workspace Candidate Flow](operations/twin-review-to-workspace-candidates.md) — connects the P1 Twin Extraction review and PR2 import bridge output to CW-A4 (`scripts/relaylm_cw_a4_workspace_slp_candidates.py`) dry-run and write-candidates planning, documenting the full runbook and generated-artifact review steps. This is a documentation/smoke-only connective flow: it does not apply MEM/SOUL/REL directly, does not create a Primary MEM page, and does not auto-promote `private_only` material.
- [ReLM Showcase合成Fixture雛形](operations/relm-showcase-fixture-authoring.md) — public synthetic showcase fixture schema, authoring guidance, workspace-memory mapping, and gate conditions separated from private Twin Extraction fixtures.
- [LAT-1 Latency Measurement](architecture/lat1_latency_measurement.md) — RelayRUN per-node timing and `timing_summary` schema, plus the offline M2 retrieval scaling bench (`scripts/relaylm_lat1_bench_store_generator.py`, `scripts/relaylm_lat1_retrieval_bench.py`). Measurement only; no request-path or search-algorithm behavior change. See also [LAT-1 Retrieval Scaling Method](operations/lat1-retrieval-scaling.md) (repeatable method) and [LAT-1 Retrieval Scaling Report Template](templates/evaluation/lat1-retrieval-scaling-report.md) (non-authoritative template; no real run has been recorded).
- [LAT-2 Mobile Perceived Latency](architecture/lat2_mobile_perceived_latency.md) — content-free `relayrun.stream_timing.v0` trace measuring streaming `time_to_first_chunk_ms`/`stream_drain_ms`/`stream_chunk_count` as a second, later trace record, since LAT-1's `timing_summary.time_to_first_token_ms` stays `null` for streaming. Measurement only; no SSE payload, backend-forwarding, or search-algorithm behavior change.

## Target architecture and post-MVP design

- [File-first Character Workspace design](architecture/file_first_character_workspace_design.md)
- [RelayREL relationship design](architecture/relayrel_relationship_design.md)
- [Showcase, Public Starter, and Product Knowledge Ownership](architecture/character-workspace/showcase-starter-product-knowledge.md)
- [Character belief, relationship, and social expression dynamics](architecture/character_belief_relationship_dynamics_design.md)
- [ADR: character-conditioned belief without rewriting observation](adr/character_conditioned_belief_model.md)
- [Character Personality and Experience Architecture](architecture/character/personality-and-experience.md)

These documents are target architecture unless explicitly listed as a current completed boundary above.

## Canonical precedence

1. `docs/PROJECT_STATUS.md` owns current implementation status and active caveats.
2. `architecture/project_execution_plan.md` owns MVP boundary, dependency sequencing, and roadmap ordering.
3. `architecture/pipeline-responsibilities.md` owns component responsibility and canonical target order.
4. Dedicated current contracts own exact bounded behavior.
5. `current_target_migration_guide.md` owns current/target/compatibility interpretation.
6. `docs/evidence/` and `docs/architecture/` evaluation records are historical or bounded evidence unless listed as current authorities above.

## Placement rules

- repository-wide current status -> `docs/PROJECT_STATUS.md`
- MVP execution plan and post-MVP roadmap -> `docs/architecture/project_execution_plan.md`
- active and completed bounded handoffs -> `docs/architecture/`
- schemas and contracts -> `docs/contracts/`
- RelaySOUL durable identity/personality -> `docs/architecture/character/`; exact RelaySOUL contracts -> `docs/contracts/`; completed RelaySOUL implementation evidence -> `docs/evidence/implementation/`
- permanent operator, smoke, and troubleshooting procedures -> `docs/operations/`
- completed bounded evaluation evidence -> `docs/evidence/evaluations/`
