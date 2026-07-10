#!/usr/bin/env python3
"""Change detection and grouped execution for consolidated smoke workflows."""

from __future__ import annotations

import argparse
import fnmatch
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable

PYTHON = sys.executable

GROUPS = {
    "relaymem": {
        "primary_memory": ["relaylm/relaymem_primary_*", "relaylm/_relaymem_primary_*", "scripts/relaylm_relaymem_primary_*", "docs/architecture/relaymem_m3*", "docs/architecture/phase6c1_relaymem_primary_pipeline_compose.md"],
        "slp_queue": ["relaylm/relaymem_slp_job_admission.py", "relaylm/relaymem_slp_response_handoff.py", "relaylm/relaymem_slp_dispatch_preflight.py", "relaylm/relaymem_slp_durable_enqueue.py", "relaylm/relaymem_slp_queue_*", "relaylm/relaymem_slp_runtime_*", "relaylm/relaymem_slp_finalized_turn_source.py", "scripts/relaylm_phase6b[0-3]*", "scripts/relaylm_phase6_runtime_enqueue_*", "scripts/relaylm_relaymem_slp_*", "docs/architecture/phase6a2_*", "docs/architecture/phase6b*", "docs/architecture/phase6_i1b_*"],
        "durable_finalization": ["relaylm/*durable_finalization*", "relaylm/relaymem_slp_durable_runtime_enqueue.py", "scripts/relaylm_i1g*", "scripts/_relaylm_i1ge_*", "docs/architecture/i1g_*", "docs/mvp/wave3/i1ge_completion_report.md"],
        "scheduler_worker": ["relaylm/relaymem_slp_primary_worker*", "relaylm/_relaymem_slp_primary_worker*", "relaylm/relaymem_slp_protected_source_store.py", "relaylm/_relaymem_slp_protected_source_*", "relaylm/relaymem_slp_one_queued_job_runner.py", "relaylm/relaymem_slp_scheduler_*", "relaylm/local_worker*", "relaylm/relaymem_held_governance_*", "scripts/relaylm_phase6c1_*", "scripts/_relaylm_phase6c1_*", "scripts/relaylm_phase6c2_*", "scripts/relaylm_o[01]*", "scripts/_relaylm_o[01]*", "scripts/relaylm_i7ab_*", "tests/test_relaymem_held_governance_preflight.py", "docs/architecture/o[01]*", "docs/architecture/phase6c*", "docs/architecture/phase_i7ab_*"],
        "recall_correction_forget_pin": ["relaylm/relaymem_primary_recall.py", "relaylm/relaymem_primary_current_state.py", "relaylm/_relaymem_primary_current_state_impl.py", "relaylm/relaymem_primary_mutation_coordinator.py", "relaylm/relaymem_primary_forget*", "relaylm/_relaymem_primary_forget*", "relaylm/relaymem_primary_correction.py", "relaylm/relaymem_primary_pin.py", "relaylm/relaymem_primary_lifecycle_page.py", "relaylm/_relaymem_primary_lifecycle_page_writer.py", "relaylm/relaymem_primary_retrieval_eligibility.py", "scripts/relaylm_phase_i1_*", "scripts/relaylm_phase_i3_*", "scripts/relaylm_phase_i4*", "scripts/_relaylm_phase_i4*", "scripts/relaylm_phase_i5a_*", "docs/architecture/phase_i[1-5]*", "docs/mvp/wave[3-4]/*"],
        "cross_slice_convergence": ["relaylm/relaymem_slp_scheduler_*", "relaylm/relaymem_primary_retrieval_eligibility.py", "scripts/relaylm_wave[2-3]_*", "scripts/relaylm_phase_i4d_security_smoke.py", "docs/mvp/wave3/*", "docs/smoke/*"],
    },
    "runtime": {
        "client_instruction": ["relaylm/client_instruction_*", "relaylm/audit_projection.py", "relaylm/pipeline_context.py", "scripts/relaylm_client_instruction_*", "docs/architecture/phase5c4b_*"],
        "relayctx_tts_stream": ["relaylm/adapter.py", "relaylm/relayctx_*", "scripts/relaylm_relayctx_*", "docs/architecture/phase5_5_*", "docs/architecture/phase55*"],
        "relayrun_lazy_recovery": ["relaylm/relayrun_lazy_recovery.py", "scripts/relaylm_relayrun_*", "docs/architecture/phase5d2_*"],
        "token_estimation": ["relaylm/*token*", "relaylm/relaymem_runtime_ctx.py", "scripts/relaylm_*token*", "scripts/relaylm_cjk_*", "scripts/relaylm_fullwidth_*", "scripts/relaylm_relaymem_cjk_*", "docs/architecture/phase5d1_*"],
        "merged_review_residuals": ["relaylm/relaymem_primary_page_candidate.py", "relaylm/_relaymem_primary_page_candidate_impl.py", "relaylm/relaymem_primary_write_preflight.py", "relaylm/relaymem_store.py", "relaylm/_relaymem_store_impl.py", "relaylm/_client_instruction_cache_write_impl.py", "scripts/relaylm_merged_review_residuals_smoke.py", "scripts/relaylm_m3c_operation_index_normalization_smoke.py"],
        "e1r1_trusted_home_scene_admission": ["scripts/relaylm_e1r1_*", "docs/architecture/e1r1_*", "docs/mvp/wave6/e1r1_*"],
        "e1r2_character_store_bootstrap": ["relaylm/character_store_bootstrap*", "scripts/relaylm_e1r2_*", "docs/architecture/e1r2_*", "docs/mvp/wave6/e1r2_*"],
        "soul_lab_management": ["relaylm/soul_lab_management.py", "relaylm/soul_lab_app.py", "scripts/relaylm_soul_lab_management_projection_smoke.py"],
    },
    "ui": {
        "soul_lab_build": ["apps/soul-lab/**"],
        "lab_observation": ["relaylm/soul_lab_observation.py", "scripts/relaylm_phase_i2_*", "apps/soul-lab/src/features/lab/observation*", "apps/soul-lab/scripts/observation*"],
        "lab_observation_regressions": ["relaylm/relaymem_slp_primary_worker*", "relaylm/relaymem_slp_one_queued_job_runner.py", "scripts/relaylm_phase6c[12]_*", "scripts/relaylm_phase_i1_*", "scripts/relaylm_phase_i2_*"],
        "lab_observation_frontend": ["apps/soul-lab/src/features/lab/observation*", "apps/soul-lab/scripts/observation*", "apps/soul-lab/package*.json"],
        "primary_mem_correct": ["relaylm/relaymem_primary_correction.py", "scripts/relaylm_phase_i3_*", "scripts/_relaylm_phase_i3_*"],
        "primary_mem_correct_regressions": ["relaylm/relaymem_primary_*", "relaylm/_relaymem_primary_*", "scripts/relaylm_relaymem_primary_*", "scripts/relaylm_phase_i3_*"],
        "primary_mem_correct_frontend": ["apps/soul-lab/src/features/lab/correction*", "apps/soul-lab/scripts/correction*", "apps/soul-lab/package*.json"],
        "home_conversation_frontend": ["apps/soul-lab/src/features/home/**", "apps/soul-lab/scripts/*home*", "apps/soul-lab/package*.json"],
        "home_conversation_regressions": ["relaylm/app.py", "relaylm/config.py", "scripts/relaylm_openwebui_lmstudio_*", "scripts/relaylm_documentation_current_boundary_smoke.py"],
        "forget_lifecycle": ["relaylm/relaymem_primary_forget*", "relaylm/relaymem_primary_retrieval_eligibility.py", "scripts/relaylm_phase_i4d_*"],
        "forget_lifecycle_regressions": ["relaylm/relaymem_primary_forget*", "relaylm/relaymem_primary_current_state.py", "scripts/relaylm_phase_i4[bcdef]_*"],
        "forget_lifecycle_frontend": ["apps/soul-lab/src/features/**/usedMemoryLifecycle*", "apps/soul-lab/scripts/*forget*", "apps/soul-lab/scripts/*usedMemory*", "apps/soul-lab/package*.json"],
        "pin_unpin": ["relaylm/relaymem_primary_pin*", "relaylm/soul_lab_memory_pin*", "scripts/relaylm_phase_i5[ab]_*", "apps/soul-lab/**/*pin*", "docs/architecture/phase_i5*"],
        "held_governance": ["relaylm/relaymem_held_governance.py", "relaylm/soul_lab_held_governance.py", "relaylm/lab_held_governance_api.py", "scripts/relaylm_i7ab_*", "scripts/relaylm_phase_i7c_*", "apps/soul-lab/**/*held*", "docs/architecture/phase_i7*"],
        "lifecycle_visibility": ["relaylm/soul_lab_lifecycle_visibility_projection.py", "scripts/relaylm_ui_b1a_lifecycle_visibility_*", "apps/soul-lab/src/features/lifecycle/**", "apps/soul-lab/scripts/lifecycleVisibilitySmoke.mjs"],
    },
}

GLOBAL_PATTERNS = {
    "relaymem": ["pyproject.toml", ".github/workflows/smoke-relaymem.yml", "scripts/relaylm_ci_consolidated_smoke.py"],
    "runtime": ["pyproject.toml", ".github/workflows/smoke-runtime.yml", "scripts/relaylm_ci_consolidated_smoke.py"],
    "ui": ["pyproject.toml", ".github/workflows/smoke-ui.yml", "scripts/relaylm_ci_consolidated_smoke.py", "apps/soul-lab/package*.json", "apps/soul-lab/src/app/**"],
}

COMMANDS = {
    "relaymem": {
        "primary_memory": [[p] for p in ["scripts/relaylm_relaymem_primary_index_log_apply_smoke.py", "scripts/relaylm_relaymem_primary_index_log_apply_security_smoke.py", "scripts/relaylm_relaymem_primary_index_log_reconciliation_smoke.py", "scripts/relaylm_relaymem_primary_index_log_reconciliation_marker_smoke.py", "scripts/relaylm_relaymem_primary_index_log_recovery_audit_smoke.py", "scripts/relaylm_relaymem_primary_index_log_recovery_audit_security_smoke.py", "scripts/relaylm_relaymem_primary_index_log_recovery_audit_receipt_smoke.py", "scripts/relaylm_relaymem_primary_page_writer_smoke.py", "scripts/relaylm_relaymem_primary_page_writer_security_smoke.py", "scripts/relaylm_relaymem_primary_page_writer_atomicity_smoke.py", "scripts/relaylm_relaymem_primary_writer_handoff_smoke.py", "scripts/relaylm_relaymem_primary_writer_handoff_review_smoke.py", "scripts/relaylm_relaymem_primary_writer_handoff_security_smoke.py", "scripts/relaylm_relaymem_primary_writer_handoff_idempotency_smoke.py", "scripts/relaylm_relaymem_primary_pipeline_smoke.py", "scripts/relaylm_relaymem_primary_pipeline_security_smoke.py", "scripts/relaylm_relaymem_primary_pipeline_result_validation_smoke.py", "scripts/relaylm_relaymem_primary_formation_dry_run_smoke.py", "scripts/relaylm_relaymem_primary_write_preflight_smoke.py", "scripts/relaylm_relaymem_primary_page_candidate_smoke.py", "scripts/relaylm_docs_link_check.py"]],
        "slp_queue": [[p] for p in ["scripts/relaylm_phase6b0_durable_queue_contract_smoke.py", "scripts/relaylm_phase6b1_dispatch_preflight_smoke.py", "scripts/relaylm_phase6b1_dispatch_preflight_security_smoke.py", "scripts/relaylm_phase6b2_durable_enqueue_smoke.py", "scripts/relaylm_phase6b2_durable_enqueue_security_smoke.py", "scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py", "scripts/relaylm_relaymem_slp_job_admission_smoke.py", "scripts/relaylm_relaymem_slp_job_admission_bounded_metadata_smoke.py", "scripts/relaylm_phase6b3_enqueue_lifecycle_compat_smoke.py", "scripts/relaylm_phase6b3_precommit_failure_projection_smoke.py", "scripts/relaylm_phase6b3_queue_root_path_smoke.py", "scripts/relaylm_phase6b3_queue_state_smoke.py", "scripts/relaylm_phase6b3_queue_state_security_smoke.py", "scripts/relaylm_phase6b3_queue_state_contract_smoke.py", "scripts/relaylm_relaymem_slp_response_handoff_smoke.py", "scripts/relaylm_relaymem_slp_response_handoff_status_smoke.py", "scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py", "scripts/relaylm_phase6_runtime_enqueue_app_smoke.py", "scripts/relaylm_relayctx_unpack_runtime_app_smoke.py", "scripts/relaylm_openwebui_lmstudio_proxy_smoke.py"]],
        "durable_finalization": [[p] for p in ["scripts/relaylm_i1g_pre_enqueue_fault_model_smoke.py", "scripts/relaylm_i1gb_durable_finalization_publication_smoke.py", "scripts/relaylm_i1gb_durable_finalization_app_smoke.py", "scripts/relaylm_o0_local_one_job_runner_contract_smoke.py", "scripts/relaylm_documentation_current_boundary_smoke.py", "scripts/relaylm_i1gc_durable_finalization_replay_smoke.py", "scripts/relaylm_i1gc_canonical_formation_replay_smoke.py", "scripts/relaylm_i1gd_durable_finalization_retention_smoke.py", "scripts/relaylm_i1gd_durable_finalization_retention_contract_smoke.py", "scripts/relaylm_i1gd_durable_finalization_retention_race_smoke.py", "scripts/relaylm_i1ge_durable_finalization_nonstream_crash_smoke.py", "scripts/relaylm_i1ge_durable_finalization_stream_crash_smoke.py", "scripts/relaylm_i1ge_durable_finalization_replay_crash_smoke.py", "scripts/relaylm_i1ge_durable_finalization_retention_crash_smoke.py", "scripts/relaylm_i1ge_durable_finalization_concurrency_smoke.py", "scripts/relaylm_i1ge_durable_finalization_security_smoke.py"]] + [["scripts/relaylm_mvp_completion_report_smoke.py", "--check-model", "--check-all"]],
        "scheduler_worker": [[p] for p in ["scripts/relaylm_phase6c1_primary_worker_source_smoke.py", "scripts/relaylm_phase6c1_worker_contract_smoke.py", "scripts/relaylm_phase6c1_durable_protected_source_smoke.py", "scripts/relaylm_phase6c1_primary_worker_review_fix_smoke.py", "scripts/relaylm_phase6c1_worker_integration_ci_runner.py", "scripts/relaylm_onboarding_config_smoke.py", "scripts/relaylm_phase6c1_fault_injection_smoke.py", "scripts/relaylm_phase6c1_fault_race_smoke.py", "scripts/relaylm_phase6c1_primary_worker_outcome_smoke.py", "scripts/relaylm_relaymem_primary_pipeline_checkpoint_smoke.py", "scripts/relaylm_phase6c1_primary_worker_ci_runner.py", "scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py", "scripts/relaylm_o0_local_one_job_runner_ci_runner.py", "scripts/relaylm_phase_i2_lab_observation_smoke.py", "scripts/relaylm_o1a_two_lane_scheduler_contract_smoke.py", "scripts/relaylm_o1b_sealed_replay_lane_smoke.py", "scripts/relaylm_o1b_sealed_replay_lane_security_smoke.py", "scripts/relaylm_o1c_eligible_queue_lane_smoke.py", "scripts/relaylm_o1c_eligible_queue_lane_security_smoke.py", "scripts/relaylm_o1d1_config_smoke.py", "scripts/relaylm_o1d1_production_round_smoke.py", "scripts/relaylm_o1d1_production_round_fault_smoke.py", "scripts/relaylm_o1d1_production_round_concurrency_smoke.py", "scripts/relaylm_o1d1_production_round_security_smoke.py", "scripts/relaylm_o1d2_scheduler_policy_smoke.py", "scripts/relaylm_o1d2_scheduler_policy_config_smoke.py", "scripts/relaylm_o1d2_scheduler_policy_fault_smoke.py", "scripts/relaylm_o1d2_scheduler_policy_security_smoke.py", "scripts/relaylm_o1a_scheduler_contract_smoke.py", "scripts/relaylm_o1e_scheduler_operational_controls_smoke.py", "scripts/relaylm_o1e_scheduler_operational_controls_config_smoke.py", "scripts/relaylm_o1e_scheduler_operational_controls_fault_smoke.py", "scripts/relaylm_o1e_scheduler_operational_controls_security_smoke.py", "scripts/relaylm_o1f_operational_validation_smoke.py", "scripts/relaylm_o1f_operational_validation_corruption_smoke.py", "scripts/relaylm_o1f_operational_validation_concurrency_smoke.py", "scripts/relaylm_o1f_operational_validation_saturation_smoke.py", "scripts/relaylm_o1f_operational_validation_restart_smoke.py", "scripts/relaylm_o1f_operational_validation_security_smoke.py", "scripts/relaylm_mvp_completion_report_pr_link_smoke.py", "scripts/relaylm_i7ab_held_apply_discard_contract_smoke.py", "scripts/relaylm_phase6c2_one_queued_job_runner_smoke.py"]] + [["scripts/relaylm_mvp_completion_report_smoke.py", "docs/mvp/wave6/o1f_completion_report.md"], ["-m", "pytest", "tests/test_relaymem_held_governance_preflight.py"]],
        "recall_correction_forget_pin": [[p] for p in ["scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py", "scripts/relaylm_relaymem_store_dry_run_smoke.py", "scripts/relaylm_relaymem_retrieval_dry_run_smoke.py", "scripts/relaylm_relaymem_selection_dry_run_smoke.py", "scripts/relaylm_relaymem_ctx_injection_plan_dry_run_smoke.py", "scripts/relaylm_relaymem_runtime_ctx_injection_smoke.py", "scripts/relaylm_relaymem_snippet_runtime_injection_apply_smoke.py", "scripts/relaylm_phase_i4b_ci_runner.py", "scripts/relaylm_phase_i3_primary_mem_correct_ci_runner.py", "scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py", "scripts/relaylm_phase_i4_forget_hide_contract_smoke.py", "scripts/relaylm_phase_i4c1_primary_forget_hidden_successor_smoke.py", "scripts/relaylm_phase_i4c1_primary_forget_corrected_revision_smoke.py", "scripts/relaylm_phase_i4c1_primary_forget_fault_smoke.py", "scripts/relaylm_phase_i4c1_primary_forget_concurrency_smoke.py", "scripts/relaylm_phase_i4c1_primary_forget_security_smoke.py", "scripts/relaylm_documentation_current_boundary_smoke.py", "scripts/relaylm_phase_i4c2_primary_forget_recovery_smoke.py", "scripts/relaylm_phase_i4c2_primary_forget_fault_smoke.py", "scripts/relaylm_phase_i4c2_primary_forget_concurrency_smoke.py", "scripts/relaylm_phase_i4c2_primary_forget_security_smoke.py", "scripts/relaylm_phase_i4c2_ownership_boundary_smoke.py", "scripts/relaylm_phase_i5a_pin_unpin_contract_smoke.py", "scripts/relaylm_phase_i5a_pin_unpin_token_smoke.py", "scripts/relaylm_phase_i5a_pin_unpin_concurrency_smoke.py", "scripts/relaylm_phase_i5a_pin_unpin_security_smoke.py", "scripts/relaylm_phase_i3_primary_mem_correct_smoke.py", "scripts/relaylm_phase_i3_primary_mem_correct_security_smoke.py", "scripts/relaylm_phase_i4b_primary_forget_preflight_smoke.py", "scripts/relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py"]],
        "cross_slice_convergence": [[p] for p in ["scripts/relaylm_wave2_cross_slice_convergence_smoke.py", "scripts/relaylm_wave2_cross_slice_security_smoke.py", "scripts/relaylm_wave3_cross_slice_convergence_smoke.py", "scripts/relaylm_wave3_cross_slice_security_smoke.py", "scripts/relaylm_phase_i4d_security_smoke.py"]],
    },
    "runtime": {
        "client_instruction": [[p] for p in ["scripts/relaylm_client_instruction_relayscn_projection_smoke.py", "scripts/relaylm_client_instruction_cache_lookup_runtime_smoke.py", "scripts/relaylm_client_instruction_typed_parse_cache_write_smoke.py", "scripts/relaylm_client_instruction_cache_write_runtime_smoke.py"]],
        "relayctx_tts_stream": [[p] for p in ["scripts/relaylm_relayctx_stream_unpack_sentinel_smoke.py", "scripts/relaylm_relayctx_stream_suppression_runtime_smoke.py", "scripts/relaylm_relayctx_tts_adapter_handoff_runtime_smoke.py", "scripts/relaylm_relayctx_tts_adapter_handoff_smoke.py", "scripts/relaylm_relayctx_tts_adapter_transport_smoke.py", "scripts/relaylm_relayctx_tts_segmentation_smoke.py"]],
        "relayrun_lazy_recovery": [[p] for p in ["scripts/relaylm_relayrun_lazy_recovery_detail_smoke.py", "scripts/relaylm_relayrun_lazy_recovery_runtime_wiring_smoke.py", "scripts/relaylm_relayrun_runtime_checkpoint_dry_run_smoke.py"]],
        "token_estimation": [[p] for p in ["scripts/relaylm_cjk_token_estimation_smoke.py", "scripts/relaylm_fullwidth_space_token_smoke.py", "scripts/relaylm_relaymem_cjk_runtime_estimation_smoke.py", "scripts/relaylm_token_memory_dry_run_smoke.py", "scripts/relaylm_token_budget_truncation_smoke.py", "scripts/relaylm_token_budget_truncation_dry_run_smoke.py", "scripts/relaylm_token_budget_truncation_apply_smoke.py", "scripts/relaylm_token_budget_truncation_proxy_smoke.py"]],
        "merged_review_residuals": [["scripts/relaylm_merged_review_residuals_smoke.py"], ["scripts/relaylm_m3c_operation_index_normalization_smoke.py"]],
        "e1r1_trusted_home_scene_admission": [["scripts/relaylm_e1r1_trusted_home_scene_admission_smoke.py"], ["scripts/relaylm_mvp_completion_report_smoke.py", "docs/mvp/wave6/e1r1_completion_report.md"]],
        "e1r2_character_store_bootstrap": [["scripts/relaylm_e1r2_character_store_bootstrap_smoke.py"], ["scripts/relaylm_mvp_completion_report_smoke.py", "docs/mvp/wave6/e1r2_completion_report.md"], ["scripts/relaylm_mvp_completion_report_pr_link_smoke.py"], ["scripts/relaylm_docs_link_check.py"]],
        "soul_lab_management": [["scripts/relaylm_soul_lab_management_projection_smoke.py"]],
    },
    "ui": {
        "lab_observation": [["scripts/relaylm_phase_i2_lab_observation_ci_runner.py"], ["scripts/relaylm_docs_link_check.py"]],
        "lab_observation_regressions": [[p] for p in ["scripts/relaylm_phase6c1_primary_worker_ci_runner.py", "scripts/relaylm_phase6c1_worker_integration_ci_runner.py", "scripts/relaylm_phase6c1_durable_protected_source_smoke.py", "scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py", "scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py"]],
        "primary_mem_correct": [["scripts/relaylm_phase_i3_primary_mem_correct_ci_runner.py"]],
        "primary_mem_correct_regressions": [[p] for p in ["scripts/relaylm_relaymem_primary_page_writer_smoke.py", "scripts/relaylm_relaymem_primary_page_writer_security_smoke.py", "scripts/relaylm_relaymem_primary_page_writer_atomicity_smoke.py", "scripts/relaylm_relaymem_primary_index_log_reconciliation_smoke.py", "scripts/relaylm_relaymem_primary_index_log_reconciliation_marker_smoke.py", "scripts/relaylm_relaymem_primary_index_log_apply_smoke.py", "scripts/relaylm_relaymem_primary_index_log_apply_security_smoke.py", "scripts/relaylm_relaymem_primary_index_log_recovery_audit_smoke.py", "scripts/relaylm_relaymem_primary_index_log_recovery_audit_security_smoke.py", "scripts/relaylm_relaymem_primary_index_log_recovery_audit_receipt_smoke.py"]],
        "home_conversation_regressions": [[p] for p in ["scripts/relaylm_documentation_current_boundary_smoke.py", "scripts/relaylm_openwebui_lmstudio_config_smoke.py", "scripts/relaylm_openwebui_lmstudio_proxy_smoke.py"]],
        "forget_lifecycle": [[p] for p in ["scripts/relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py", "scripts/relaylm_phase_i4d_prior_revision_exclusion_smoke.py", "scripts/relaylm_phase_i4d_recovery_state_exclusion_smoke.py", "scripts/relaylm_phase_i4d_relayctx_exclusion_smoke.py", "scripts/relaylm_phase_i4d_historical_projection_smoke.py", "scripts/relaylm_phase_i4d_security_smoke.py", "scripts/relaylm_phase_i4d_fresh_conversation_smoke.py"]],
        "forget_lifecycle_regressions": [[p] for p in ["scripts/relaylm_phase_i4b_ci_runner.py", "scripts/relaylm_phase_i4c1_primary_forget_hidden_successor_smoke.py", "scripts/relaylm_phase_i4c1_primary_forget_corrected_revision_smoke.py", "scripts/relaylm_phase_i4c1_primary_forget_security_smoke.py", "scripts/relaylm_phase_i4c2_primary_forget_recovery_smoke.py", "scripts/relaylm_phase_i4c2_primary_forget_fault_smoke.py", "scripts/relaylm_phase_i4c2_primary_forget_concurrency_smoke.py", "scripts/relaylm_phase_i4c2_primary_forget_security_smoke.py", "scripts/relaylm_phase_i4c2_ownership_boundary_smoke.py", "scripts/relaylm_phase_i4_forget_hide_contract_smoke.py", "scripts/relaylm_phase_i4b_primary_forget_preflight_smoke.py", "scripts/relaylm_phase_i4c1_primary_forget_fault_smoke.py", "scripts/relaylm_phase_i4c1_primary_forget_concurrency_smoke.py", "scripts/relaylm_phase_i3_primary_mem_correct_smoke.py", "scripts/relaylm_phase_i3_primary_mem_correct_security_smoke.py", "scripts/relaylm_phase_i4e_forget_api_smoke.py", "scripts/relaylm_phase_i4e_forget_api_security_smoke.py", "scripts/relaylm_phase_i4f_forget_validation_smoke.py", "scripts/relaylm_phase_i4f_forget_validation_fault_smoke.py", "scripts/relaylm_phase_i4f_forget_validation_concurrency_smoke.py", "scripts/relaylm_phase_i4f_forget_validation_security_smoke.py", "scripts/relaylm_phase_i4f_forget_validation_ui_smoke.py"]] + [["scripts/relaylm_mvp_completion_report_smoke.py", "docs/mvp/wave5/i4f_completion_report.md"]],
        "pin_unpin": [[p] for p in ["scripts/relaylm_phase_i5a_pin_unpin_contract_smoke.py", "scripts/relaylm_phase_i5b_pin_unpin_apply_smoke.py", "scripts/relaylm_phase_i5b_pin_unpin_api_projection_smoke.py", "scripts/relaylm_phase_i5b_pin_unpin_ranking_smoke.py", "scripts/relaylm_phase_i5b_pin_unpin_concurrency_smoke.py", "scripts/relaylm_phase_i5b_pin_unpin_security_smoke.py"]],
        "held_governance": [[p] for p in ["scripts/relaylm_i7ab_held_apply_discard_contract_smoke.py", "scripts/relaylm_phase_i7c_held_governance_runtime_smoke.py", "scripts/relaylm_phase_i7c_held_governance_api_smoke.py", "scripts/relaylm_phase_i7c_held_governance_concurrency_smoke.py", "scripts/relaylm_phase_i7c_held_governance_security_smoke.py", "scripts/relaylm_phase_i7c_held_governance_ui_smoke.py"]] + [["scripts/relaylm_mvp_completion_report_smoke.py", "docs/mvp/wave6/i7c_completion_report.md"], ["scripts/relaylm_mvp_completion_report_pr_link_smoke.py"]],
        "lifecycle_visibility": [["scripts/relaylm_ui_b1a_lifecycle_visibility_api_smoke.py"], ["scripts/relaylm_ui_b1a_lifecycle_visibility_security_smoke.py"]],
    },
}


def matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def changed_outputs(workflow: str, files: list[str], force_all: bool) -> dict[str, bool]:
    groups = GROUPS[workflow]
    if force_all or any(matches(path, GLOBAL_PATTERNS[workflow]) for path in files):
        return {group: True for group in groups}
    return {group: any(matches(path, patterns) for path in files) for group, patterns in groups.items()}


def run_group(workflow: str, group: str) -> int:
    commands = COMMANDS.get(workflow, {}).get(group)
    if commands is None:
        raise SystemExit(f"group {workflow}/{group} has no Python command list")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [".", "scripts", env.get("PYTHONPATH", "")]))
    for args in commands:
        command = [PYTHON, *args]
        print("+", " ".join(command), flush=True)
        result = subprocess.run(command, env=env, check=False)
        if result.returncode:
            return result.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    changed = subparsers.add_parser("changed")
    changed.add_argument("--workflow", choices=GROUPS, required=True)
    changed.add_argument("--files", type=Path)
    changed.add_argument("--all", action="store_true")
    run = subparsers.add_parser("run")
    run.add_argument("--workflow", choices=COMMANDS, required=True)
    run.add_argument("--group", required=True)
    args = parser.parse_args()
    if args.command == "changed":
        files = []
        if args.files:
            files = [line.strip() for line in args.files.read_text(encoding="utf-8").splitlines() if line.strip()]
        for group, enabled in changed_outputs(args.workflow, files, args.all).items():
            print(f"{group}={'true' if enabled else 'false'}")
        return 0
    return run_group(args.workflow, args.group)


if __name__ == "__main__":
    raise SystemExit(main())
