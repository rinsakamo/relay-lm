# Scripts Inventory

**Maintainer review only.** This table is mechanically generated for PR-14 (the final PR of the smoke-workflow consolidation series). **No scripts were moved, renamed, or deleted to produce this file** -- it is a read-only snapshot of `scripts/` to help a human decide what (if anything) should be archived, promoted, or documented next. Re-generate it mechanically if `scripts/` or `.github/workflows/` change again; do not hand-edit individual rows.

Snapshot stats: 455 scripts total, 222 referenced by a CI workflow after this PR, 280 referenced by docs, 100 referenced by neither (candidates for maintainer triage).

The directory `scripts/twin_extraction_prompts/` holds two prompt-text assets (not Python scripts) and is excluded from the table below.

## Category guesses

- **active smoke** -- invoked by a `run:` step in a current `.github/workflows/*.yml` file.
- **phase-completion evidence** -- not CI-referenced, but mentioned in `docs/` (commonly a wave/phase completion report or architecture note citing it as the historical validation source).
- **helper** -- name pattern suggests shared support code (leading underscore, `_support`, `_fixture`) rather than a directly-run script.
- **tool** -- not CI-referenced and not mentioned in docs; likely a standalone or manually-run utility. Worth a maintainer look.

## Inventory

| script | CI-referenced after this PR | docs-referenced | category guess |
| --- | --- | --- | --- |
| `_relaylm_i1ge_crash_child.py` | no | yes | helper |
| `_relaylm_i1ge_crash_validation.py` | no | yes | helper |
| `_relaylm_i1ge_replay_crash_child.py` | no | no | helper |
| `_relaylm_o0_local_worker_support.py` | no | no | helper |
| `_relaylm_o1d1_support.py` | no | yes | helper |
| `_relaylm_o1f_support.py` | no | yes | helper |
| `_relaylm_phase6c1_durable_source_support.py` | no | no | helper |
| `_relaylm_phase6c1_fault_fixtures.py` | no | no | helper |
| `_relaylm_phase_i3_test_support.py` | no | no | helper |
| `_relaylm_phase_i4b_test_support.py` | no | no | helper |
| `phase5c4a_backend_e2e.py` | no | no | tool |
| `phase5c4a_block_order.py` | no | no | tool |
| `phase5c4a_cache_fixture.py` | no | no | helper |
| `phase5c4a_explicit_smoke_support.py` | no | no | helper |
| `phase5c4a_smoke_support.py` | no | no | helper |
| `relaylm_acg2_query_detail_analyzer_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_acg3_retrieval_query_normalization_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_acg4_reference_intent_analyzer_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_acg5_relayemo_scene_cleanup_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_acg6_scene_wiki_classifier_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_analyzer_governance_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_api_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_app_orchestration_extract_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_audit_projection_contract_smoke.py` | no | no | tool |
| `relaylm_audit_projection_exact_contract_smoke.py` | no | no | tool |
| `relaylm_character_workspace_compile.py` | no | yes | phase-completion evidence |
| `relaylm_cjk_token_estimation_smoke.py` | yes (smoke-runtime.yml) | no | active smoke |
| `relaylm_client_cache_runtime_dry_run_smoke.py` | no | no | tool |
| `relaylm_client_fp_runtime_dry_run_smoke.py` | no | no | tool |
| `relaylm_client_history_exclusion_apply_contract_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_client_history_exclusion_apply_forward_gate_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_client_history_exclusion_apply_runtime_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_client_history_exclusion_preflight_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_client_identity_runtime_private_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_client_instr_runtime_dry_run_smoke.py` | no | no | tool |
| `relaylm_client_instruction_cache_dry_run_smoke.py` | no | no | tool |
| `relaylm_client_instruction_cache_lookup_dependency_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_client_instruction_cache_lookup_empty_smoke.py` | no | no | tool |
| `relaylm_client_instruction_cache_lookup_runtime_smoke.py` | yes (onboarding-config-smoke.yml, smoke-runtime.yml) | yes | active smoke |
| `relaylm_client_instruction_cache_lookup_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_client_instruction_cache_reader_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_client_instruction_cache_write_runtime_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_client_instruction_extraction_dry_run_smoke.py` | no | no | tool |
| `relaylm_client_instruction_fingerprint_dry_run_smoke.py` | no | no | tool |
| `relaylm_client_instruction_identity_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_client_instruction_relayscn_projection_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_client_instruction_typed_parse_cache_write_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_client_message_canonicalization_dry_run_smoke.py` | no | no | tool |
| `relaylm_client_msg_runtime_dry_run_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_compile_decision_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_compile_decision_request_path_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_compile_gate_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_compiled_message_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_config_memory_seed_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_config_profile_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_config_routing_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_config_scene_state_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_context_block_summary_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_context_compiler_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_ctx_repack_final_gate_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_cw_a1_file_first_workspace_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_cw_a2_workspace_compiler_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_cw_a4_workspace_slp_candidates.py` | no | yes | phase-completion evidence |
| `relaylm_cw_a4_workspace_slp_candidates_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_cw_a4_workspace_slp_review_fix_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_cw_a5_character_creation_templates_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_docs_link_check.py` | yes (docs-link-check.yml, e1-evaluation-consolidation.yml, mvp-eval-runner.yml, phase-i4-forget-hide-contract-smoke.yml, smoke-relaymem.yml, smoke-runtime.yml, smoke-ui.yml, wave4-cross-slice-convergence.yml, wave5-cross-slice-convergence.yml) | yes | active smoke |
| `relaylm_docs_link_check_smoke.py` | yes (docs-link-check.yml) | no | active smoke |
| `relaylm_documentation_current_boundary_smoke.py` | yes (documentation-current-boundary-smoke.yml, e1-evaluation-consolidation.yml, phase-i4-forget-hide-contract-smoke.yml, smoke-relaymem.yml, smoke-ui.yml, wave4-cross-slice-convergence.yml, wave5-cross-slice-convergence.yml) | yes | active smoke |
| `relaylm_e1_evaluation_consolidation_smoke.py` | yes (e1-evaluation-consolidation.yml) | yes | active smoke |
| `relaylm_e1_scoped_primary_recall_regression_smoke.py` | no | no | tool |
| `relaylm_e1r1_trusted_home_scene_admission_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_e1r2_character_store_bootstrap_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_e1r3_provenance_formation_security_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e1r3_provenance_formation_summary_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e1r4_grounded_recall_response_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e1r4_grounded_recall_security_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e1r4_unsupported_detail_suppression_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e1r5_primary_mem_recall_bridge_policy_gate_smoke.py` | no | no | tool |
| `relaylm_e1r5_primary_mem_recall_bridge_relevance_bounds_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e1r5_primary_mem_recall_bridge_security_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e1r5_primary_mem_recall_no_symlink_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e2_value_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e2_value_smoke_harness_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_e2_value_smoke_scenarios_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_fullwidth_space_token_smoke.py` | yes (smoke-runtime.yml) | no | active smoke |
| `relaylm_hardening_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_i1g_pre_enqueue_fault_model_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_i1gb_durable_finalization_app_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_i1gb_durable_finalization_publication_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_i1gb_finalized_source_current_schema_smoke.py` | no | no | tool |
| `relaylm_i1gc_canonical_formation_replay_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_i1gc_durable_finalization_replay_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_i1gd_durable_finalization_retention_contract_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_i1gd_durable_finalization_retention_race_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_i1gd_durable_finalization_retention_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_i1ge_durable_finalization_concurrency_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_i1ge_durable_finalization_nonstream_crash_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_i1ge_durable_finalization_replay_crash_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_i1ge_durable_finalization_retention_crash_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_i1ge_durable_finalization_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_i1ge_durable_finalization_stream_crash_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_i7ab_held_apply_discard_contract_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_jsonl_trace_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_lat1_bench_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_lat1_bench_store_generator.py` | no | yes | phase-completion evidence |
| `relaylm_lat1_retrieval_bench.py` | no | yes | phase-completion evidence |
| `relaylm_lat1_timing_security_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_lat1_timing_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_lat2_stream_timing_security_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_lat2_stream_timing_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_m3c_operation_index_normalization_smoke.py` | yes (smoke-runtime.yml) | no | active smoke |
| `relaylm_memory_adapter_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_adapter_shadow_delta_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_adapter_shadow_scope_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_block_insertion_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_budget_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_candidate_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_light_apply_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_review_apply_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_review_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_review_status_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_review_to_seed_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_seed_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_selection_config_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_selection_summary_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_memory_state_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_merged_review_residuals_smoke.py` | yes (smoke-runtime.yml) | no | active smoke |
| `relaylm_mixed_character_token_policy_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_mvp_completion_report_pr_link_smoke.py` | yes (documentation-completion-report-link.yml, e1-evaluation-consolidation.yml, smoke-relaymem.yml, smoke-runtime.yml, smoke-ui.yml, wave5-cross-slice-convergence.yml) | yes | active smoke |
| `relaylm_mvp_completion_report_smoke.py` | yes (documentation-completion-report-files.yml, documentation-completion-report-model.yml, e1-evaluation-consolidation.yml, mvp-eval-runner.yml, smoke-relaymem.yml, smoke-runtime.yml, smoke-ui.yml, wave4-cross-slice-convergence.yml, wave5-cross-slice-convergence.yml) | yes | active smoke |
| `relaylm_mvp_eval_runner.py` | yes (mvp-eval-runner.yml) | yes | active smoke |
| `relaylm_mvp_eval_runner_impl.py` | no | yes | phase-completion evidence |
| `relaylm_mvp_eval_runner_registry.py` | no | yes | phase-completion evidence |
| `relaylm_mvp_eval_runner_security_smoke.py` | yes (mvp-eval-runner.yml) | yes | active smoke |
| `relaylm_mvp_eval_runner_smoke.py` | yes (mvp-eval-runner.yml) | yes | active smoke |
| `relaylm_o0_local_one_job_runner_ci_runner.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_o0_local_one_job_runner_contract_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_o0_local_one_job_runner_security_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_o0_local_one_job_runner_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_o1a_scheduler_contract_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1a_two_lane_scheduler_contract_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1b_sealed_replay_lane_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1b_sealed_replay_lane_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1c_eligible_queue_lane_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1c_eligible_queue_lane_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1d1_config_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1d1_production_round_concurrency_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1d1_production_round_fault_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1d1_production_round_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1d1_production_round_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1d2_scheduler_policy_config_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1d2_scheduler_policy_fault_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1d2_scheduler_policy_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1d2_scheduler_policy_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1e_scheduler_operational_controls_config_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1e_scheduler_operational_controls_fault_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1e_scheduler_operational_controls_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1e_scheduler_operational_controls_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1f_operational_validation_concurrency_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1f_operational_validation_corruption_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1f_operational_validation_restart_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1f_operational_validation_saturation_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1f_operational_validation_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o1f_operational_validation_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_o2_supervised_scheduler_service_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_o3_always_on_local_scheduler.py` | no | yes | phase-completion evidence |
| `relaylm_o3_always_on_local_scheduler_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_onboarding_config_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_openwebui_lmstudio_config_smoke.py` | yes (onboarding-config-smoke.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_openwebui_lmstudio_proxy_smoke.py` | yes (onboarding-config-smoke.yml, smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_p0_pipeline_ordering_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_package_import_purity_smoke.py` | no | no | tool |
| `relaylm_persona_source_budget_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_phase5c4a_audit_explicit_smoke.py` | no | no | tool |
| `relaylm_phase5c4a_audit_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_phase5c4a_cache_explicit_smoke.py` | no | no | tool |
| `relaylm_phase5c4a_cache_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_phase5c4a_compiler_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_phase5c4a_contract_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_phase5c4a_error_explicit_smoke.py` | no | no | tool |
| `relaylm_phase5c4a_error_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_phase5c4a_fields_explicit_smoke.py` | no | no | tool |
| `relaylm_phase5c4a_fields_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_phase5c4a_gate_explicit_smoke.py` | no | no | tool |
| `relaylm_phase5c4a_gate_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_phase5c4a_optional_explicit_smoke.py` | no | no | tool |
| `relaylm_phase5c4a_optional_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_phase5c4a_projection_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_phase5c4a_renderer_smoke.py` | no | no | tool |
| `relaylm_phase5c4a_runtime_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_phase5c4a_source_smoke.py` | no | no | tool |
| `relaylm_phase6_runtime_enqueue_app_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6_runtime_enqueue_source_capture_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6b0_durable_queue_contract_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6b1_dispatch_preflight_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6b1_dispatch_preflight_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6b2_durable_enqueue_contract_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6b2_durable_enqueue_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6b2_durable_enqueue_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6b3_enqueue_lifecycle_compat_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_phase6b3_precommit_failure_projection_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_phase6b3_queue_root_path_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_phase6b3_queue_state_contract_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6b3_queue_state_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6b3_queue_state_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6c1_durable_protected_source_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase6c1_durable_source_restart_smoke.py` | no | no | tool |
| `relaylm_phase6c1_durable_source_store_smoke.py` | no | no | tool |
| `relaylm_phase6c1_durable_source_uncertain_enqueue_smoke.py` | no | no | tool |
| `relaylm_phase6c1_fault_injection_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_phase6c1_fault_race_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_phase6c1_primary_worker_ci_runner.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase6c1_primary_worker_fault_smoke.py` | no | no | tool |
| `relaylm_phase6c1_primary_worker_outcome_purity_cases.py` | no | no | tool |
| `relaylm_phase6c1_primary_worker_outcome_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6c1_primary_worker_outcome_success_retry_cases.py` | no | no | tool |
| `relaylm_phase6c1_primary_worker_outcome_support.py` | no | no | helper |
| `relaylm_phase6c1_primary_worker_outcome_terminal_cases.py` | no | no | tool |
| `relaylm_phase6c1_primary_worker_outcome_validation_cases.py` | no | no | tool |
| `relaylm_phase6c1_primary_worker_result_validation_smoke.py` | no | no | tool |
| `relaylm_phase6c1_primary_worker_review_fix_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6c1_primary_worker_security_smoke.py` | no | no | tool |
| `relaylm_phase6c1_primary_worker_smoke.py` | no | no | tool |
| `relaylm_phase6c1_primary_worker_source_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase6c1_primary_worker_test_support.py` | no | no | helper |
| `relaylm_phase6c1_worker_content_leakage_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_phase6c1_worker_contract_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_phase6c1_worker_corruption_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_phase6c1_worker_crash_convergence_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_phase6c1_worker_fault_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_phase6c1_worker_integration_ci_runner.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase6c1_worker_lease_race_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_phase6c2_one_queued_job_runner_ci_runner.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase6c2_one_queued_job_runner_security_smoke.py` | no | no | tool |
| `relaylm_phase6c2_one_queued_job_runner_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_phase_i1_two_turn_primary_recall_ci_runner.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i1_two_turn_primary_recall_security_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_phase_i1_two_turn_primary_recall_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase_i2_documentation_boundary_smoke.py` | no | no | tool |
| `relaylm_phase_i2_lab_observation_ci_runner.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i2_lab_observation_security_smoke.py` | no | no | tool |
| `relaylm_phase_i2_lab_observation_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_phase_i3_primary_mem_correct_ci_runner.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i3_primary_mem_correct_fault_smoke.py` | no | no | tool |
| `relaylm_phase_i3_primary_mem_correct_path_safety_smoke.py` | no | no | tool |
| `relaylm_phase_i3_primary_mem_correct_security_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i3_primary_mem_correct_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i3_primary_mem_correct_target_validation_smoke.py` | no | no | tool |
| `relaylm_phase_i3_primary_mem_correct_validation_smoke.py` | no | no | tool |
| `relaylm_phase_i4_forget_hide_contract_smoke.py` | yes (phase-i4-forget-hide-contract-smoke.yml, smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4b_ci_runner.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4b_final_review_regression_smoke.py` | no | no | tool |
| `relaylm_phase_i4b_primary_current_state_resolver_smoke.py` | no | no | tool |
| `relaylm_phase_i4b_primary_forget_preflight_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i4b_primary_forget_security_smoke.py` | no | no | tool |
| `relaylm_phase_i4b_primary_mutation_fence_smoke.py` | no | no | tool |
| `relaylm_phase_i4c1_ci_runner.py` | no | no | tool |
| `relaylm_phase_i4c1_primary_forget_concurrency_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i4c1_primary_forget_corrected_revision_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4c1_primary_forget_fault_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4c1_primary_forget_hidden_successor_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4c1_primary_forget_security_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4c2_ownership_boundary_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4c2_primary_forget_concurrency_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4c2_primary_forget_fault_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4c2_primary_forget_recovery_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4c2_primary_forget_security_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4d_fresh_conversation_smoke.py` | yes (smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4d_historical_projection_smoke.py` | yes (smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i4d_prior_revision_exclusion_smoke.py` | yes (smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4d_recovery_state_exclusion_smoke.py` | yes (smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4d_relayctx_exclusion_smoke.py` | yes (smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4d_security_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i4e_forget_api_security_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i4e_forget_api_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i4f_forget_validation_concurrency_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i4f_forget_validation_fault_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i4f_forget_validation_security_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i4f_forget_validation_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i4f_forget_validation_ui_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i5a_pin_unpin_concurrency_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase_i5a_pin_unpin_contract_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i5a_pin_unpin_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase_i5a_pin_unpin_token_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_phase_i5b_pin_unpin_api_projection_smoke.py` | yes (smoke-ui.yml) | no | active smoke |
| `relaylm_phase_i5b_pin_unpin_apply_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i5b_pin_unpin_concurrency_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i5b_pin_unpin_ranking_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i5b_pin_unpin_security_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i7c_held_governance_api_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i7c_held_governance_concurrency_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i7c_held_governance_runtime_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i7c_held_governance_security_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_phase_i7c_held_governance_ui_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_pipeline_context_node_results_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_pipeline_node_result_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_pipeline_node_results_runtime_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_pm_d5_flat_store_compat_removal_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_pm_d6_relayint_native_artifact_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_pm_d7_runtime_install_hook_fold_in_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_pr3_soul_lab_read_context_smoke.py` | no | no | tool |
| `relaylm_pr4_soul_lab_request_contracts_smoke.py` | no | no | tool |
| `relaylm_profile_compile_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_profile_compile_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_profile_loading_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_pydantic_schema_alias_smoke.py` | no | no | tool |
| `relaylm_reason_ids_smoke.py` | no | no | tool |
| `relaylm_relayctx_short_term_block_assembly_dry_run_smoke.py` | no | no | tool |
| `relaylm_relayctx_short_term_extraction_dry_run_smoke.py` | no | no | tool |
| `relaylm_relayctx_short_term_runtime_injection_apply_smoke.py` | no | no | tool |
| `relaylm_relayctx_short_term_runtime_injection_preflight_smoke.py` | no | no | tool |
| `relaylm_relayctx_short_term_source_diagnostics_smoke.py` | no | no | tool |
| `relaylm_relayctx_stream_suppression_runtime_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_relayctx_stream_unpack_sentinel_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_relayctx_tts_adapter_handoff_runtime_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_relayctx_tts_adapter_handoff_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_relayctx_tts_adapter_transport_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_relayctx_tts_segmentation_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_relayctx_unpack_contract_smoke.py` | no | no | tool |
| `relaylm_relayctx_unpack_marker_safety_smoke.py` | no | no | tool |
| `relaylm_relayctx_unpack_runtime_app_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relayctx_unpack_runtime_smoke.py` | no | no | tool |
| `relaylm_relayemo_canonical_module_smoke.py` | no | no | tool |
| `relaylm_relayemo_smoke.py` | no | no | tool |
| `relaylm_relayint_fast_path_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayint_quick_clarification_apply_smoke.py` | no | no | tool |
| `relaylm_relayint_quick_clarification_preflight_smoke.py` | no | no | tool |
| `relaylm_relaymem_apply_readiness_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaymem_cjk_runtime_estimation_smoke.py` | yes (smoke-runtime.yml) | no | active smoke |
| `relaylm_relaymem_ctx_block_candidate_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaymem_ctx_block_evidence_metadata_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaymem_ctx_injection_plan_dry_run_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_primary_formation_dry_run_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_primary_index_log_apply_security_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_relaymem_primary_index_log_apply_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_relaymem_primary_index_log_reconciliation_marker_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_relaymem_primary_index_log_reconciliation_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_relaymem_primary_index_log_recovery_audit_receipt_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | no | active smoke |
| `relaylm_relaymem_primary_index_log_recovery_audit_security_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_relaymem_primary_index_log_recovery_audit_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_relaymem_primary_page_candidate_review_smoke.py` | no | no | tool |
| `relaylm_relaymem_primary_page_candidate_security_smoke.py` | no | no | tool |
| `relaylm_relaymem_primary_page_candidate_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_relaymem_primary_page_writer_atomicity_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_relaymem_primary_page_writer_security_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_relaymem_primary_page_writer_smoke.py` | yes (smoke-relaymem.yml, smoke-ui.yml) | yes | active smoke |
| `relaylm_relaymem_primary_pipeline_checkpoint_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_relaymem_primary_pipeline_result_validation_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_relaymem_primary_pipeline_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_primary_pipeline_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_primary_write_preflight_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_relaymem_primary_writer_handoff_idempotency_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_primary_writer_handoff_review_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_primary_writer_handoff_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_primary_writer_handoff_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_retrieval_dry_run_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_retrieval_priority_runtime_smoke.py` | no | no | tool |
| `relaylm_relaymem_retrieval_priority_smoke.py` | no | no | tool |
| `relaylm_relaymem_runtime_ctx_injection_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_runtime_payload_diff_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaymem_selection_dry_run_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_slp_job_admission_bounded_metadata_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_relaymem_slp_job_admission_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_relaymem_slp_response_handoff_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_relaymem_slp_response_handoff_status_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_relaymem_snippet_apply_readiness_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaymem_snippet_ctx_block_candidate_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaymem_snippet_evidence_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaymem_snippet_runtime_injection_apply_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relaymem_snippet_runtime_injection_plan_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaymem_store_dry_run_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_relayref_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayrun_checkpoint_index_smoke.py` | no | no | tool |
| `relaylm_relayrun_checkpoint_writer_smoke.py` | no | no | tool |
| `relaylm_relayrun_lazy_recovery_detail_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_relayrun_lazy_recovery_runtime_wiring_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_relayrun_node_sequence_drift_smoke.py` | no | no | tool |
| `relaylm_relayrun_output_relayscn_recovery_gate_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayrun_recovery_apply_preflight_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayrun_recovery_response_draft_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayrun_recovery_response_generator_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayrun_recovery_transition_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayrun_resume_preflight_smoke.py` | no | no | tool |
| `relaylm_relayrun_runtime_checkpoint_dry_run_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_relayrun_user_action_contract_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayrun_visible_recovery_apply_preflight_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayrun_visible_recovery_preflight_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayrun_waiting_user_contract_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relayscn_scene_policy_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaysoul_apply_execution_preflight_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_apply_plan_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_approval_decision_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_approval_package_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_approval_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaysoul_compile_dry_run_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaysoul_explicit_approval_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_patch_candidate_dry_run.py` | no | yes | phase-completion evidence |
| `relaylm_relaysoul_patch_candidate_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaysoul_patch_prompt_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_persistence_execution_preflight_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_persistence_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaysoul_revision_history_store_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_revision_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaysoul_rollback_execution_preflight_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_rollback_plan_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_runtime_feedback_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_relaysoul_storage_envelope_dry_run.py` | no | yes | phase-completion evidence |
| `relaylm_relaysoul_storage_index_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_storage_path_plan_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_storage_writer_preflight_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_temp_revision_compile_dry_run.py` | no | no | tool |
| `relaylm_relaysoul_temp_revision_profile_smoke.py` | yes (onboarding-config-smoke.yml) | no | active smoke |
| `relaylm_request_scope_identity_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_runtime_diagnostics_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_scope_resolution_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_showcase_fixture_gate_smoke.py` | no | no | helper |
| `relaylm_soul_lab_management_projection_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_soul_lab_memory_routes_split_smoke.py` | no | no | tool |
| `relaylm_stable_prefix_hash_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_system_fallback_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_token_budget_truncation_apply_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_token_budget_truncation_dry_run_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_token_budget_truncation_proxy_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_token_budget_truncation_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_token_memory_dry_run_smoke.py` | yes (smoke-runtime.yml) | yes | active smoke |
| `relaylm_token_policy_runtime_gate_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_token_policy_signal_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_token_trace_payload_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_trace_content_free_contract_smoke.py` | yes (onboarding-config-smoke.yml) | yes | active smoke |
| `relaylm_trace_file_check.py` | no | no | tool |
| `relaylm_trace_success_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_twin_extraction_batch_runner.py` | no | yes | phase-completion evidence |
| `relaylm_twin_extraction_common.py` | no | yes | phase-completion evidence |
| `relaylm_twin_extraction_merge.py` | no | yes | phase-completion evidence |
| `relaylm_twin_extraction_preprocess.py` | no | yes | phase-completion evidence |
| `relaylm_twin_extraction_provenance_smoke.py` | no | no | tool |
| `relaylm_twin_extraction_security_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_twin_extraction_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_twin_review_import_bridge.py` | no | yes | phase-completion evidence |
| `relaylm_twin_review_import_bridge_cw_a4_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_twin_review_import_bridge_security_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_twin_review_import_bridge_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_twin_review_to_cw_a4_flow_smoke.py` | no | yes | phase-completion evidence |
| `relaylm_ui_b1a_lifecycle_visibility_api_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_ui_b1a_lifecycle_visibility_security_smoke.py` | yes (smoke-ui.yml) | yes | active smoke |
| `relaylm_wave2_cross_slice_convergence_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_wave2_cross_slice_security_smoke.py` | yes (smoke-relaymem.yml) | no | active smoke |
| `relaylm_wave3_cross_slice_convergence_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_wave3_cross_slice_security_smoke.py` | yes (smoke-relaymem.yml) | yes | active smoke |
| `relaylm_wave4_cross_slice_convergence_smoke.py` | yes (wave4-cross-slice-convergence.yml) | yes | active smoke |
| `relaylm_wave5_cross_slice_convergence_smoke.py` | yes (wave5-cross-slice-convergence.yml) | no | active smoke |
