# MVP eval runner focused validation
## aggregation smoke
RelayLM MVP eval runner smoke passed
## security smoke
RelayLM MVP eval runner security smoke passed
## static runner
RelayLM MVP eval runner summary
overall_status: FAIL
mode: static
required_passed_count: 3
required_failed_count: 4
optional_skipped_count: 0
categories:
- preflight: PASS required=true elapsed_ms=1 failure_reason_id=none
  - internal:static-preflight: PASS required=true elapsed_ms=1 failure_reason_id=none
- compile: PASS required=true elapsed_ms=62 failure_reason_id=none
  - python -m compileall relaylm scripts: PASS required=true elapsed_ms=62 failure_reason_id=none
- e1_provenance_grounding_recall: FAIL required=true elapsed_ms=627 failure_reason_id=exit_nonzero
  - python scripts/relaylm_e1r3_provenance_formation_summary_smoke.py: PASS required=true elapsed_ms=42 failure_reason_id=none
  - python scripts/relaylm_e1r3_provenance_formation_security_smoke.py: PASS required=true elapsed_ms=42 failure_reason_id=none
  - python scripts/relaylm_e1r4_grounded_recall_response_smoke.py: PASS required=true elapsed_ms=59 failure_reason_id=none
  - python scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py: PASS required=true elapsed_ms=54 failure_reason_id=none
  - python scripts/relaylm_e1r4_grounded_recall_security_smoke.py: PASS required=true elapsed_ms=52 failure_reason_id=none
  - python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py: FAIL required=true elapsed_ms=130 failure_reason_id=exit_nonzero
  - python scripts/relaylm_e1r5_primary_mem_recall_bridge_security_smoke.py: FAIL required=true elapsed_ms=70 failure_reason_id=exit_nonzero
  - python scripts/relaylm_e1r5_primary_mem_recall_no_symlink_smoke.py: FAIL required=true elapsed_ms=69 failure_reason_id=exit_nonzero
  - python scripts/relaylm_e1r5_primary_mem_recall_bridge_relevance_bounds_smoke.py: PASS required=true elapsed_ms=57 failure_reason_id=none
  - python scripts/relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py: PASS required=true elapsed_ms=47 failure_reason_id=none
- two_turn_recall_lifecycle: FAIL required=true elapsed_ms=965 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py: FAIL required=true elapsed_ms=226 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py: PASS required=true elapsed_ms=673 failure_reason_id=none
  - python scripts/relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py: FAIL required=true elapsed_ms=65 failure_reason_id=exit_nonzero
- o1_operational_boundary: FAIL required=true elapsed_ms=728 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1a_scheduler_contract_smoke.py: PASS required=true elapsed_ms=56 failure_reason_id=none
  - python scripts/relaylm_o1b_sealed_replay_lane_smoke.py: FAIL required=true elapsed_ms=172 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1c_eligible_queue_lane_smoke.py: FAIL required=true elapsed_ms=95 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1d1_production_round_smoke.py: FAIL required=true elapsed_ms=44 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1d2_scheduler_policy_smoke.py: FAIL required=true elapsed_ms=50 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1e_scheduler_operational_controls_smoke.py: FAIL required=true elapsed_ms=64 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1f_operational_validation_smoke.py: FAIL required=true elapsed_ms=41 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1f_operational_validation_corruption_smoke.py: FAIL required=true elapsed_ms=41 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1f_operational_validation_concurrency_smoke.py: FAIL required=true elapsed_ms=42 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1f_operational_validation_saturation_smoke.py: FAIL required=true elapsed_ms=41 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1f_operational_validation_restart_smoke.py: FAIL required=true elapsed_ms=41 failure_reason_id=exit_nonzero
  - python scripts/relaylm_o1f_operational_validation_security_smoke.py: FAIL required=true elapsed_ms=35 failure_reason_id=exit_nonzero
- governance: FAIL required=true elapsed_ms=2522 failure_reason_id=exit_nonzero
  - internal:governance-smoke-discovery: PASS required=false elapsed_ms=4 failure_reason_id=none
  - python scripts/relaylm_i7ab_held_apply_discard_contract_smoke.py: PASS required=true elapsed_ms=45 failure_reason_id=none
  - python scripts/relaylm_phase_i3_primary_mem_correct_fault_smoke.py: FAIL required=true elapsed_ms=77 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i3_primary_mem_correct_path_safety_smoke.py: FAIL required=true elapsed_ms=99 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i3_primary_mem_correct_security_smoke.py: FAIL required=true elapsed_ms=36 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i3_primary_mem_correct_smoke.py: FAIL required=true elapsed_ms=68 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i3_primary_mem_correct_target_validation_smoke.py: FAIL required=true elapsed_ms=95 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i3_primary_mem_correct_validation_smoke.py: FAIL required=true elapsed_ms=110 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4_forget_hide_contract_smoke.py: PASS required=true elapsed_ms=28 failure_reason_id=none
  - python scripts/relaylm_phase_i4b_primary_forget_preflight_smoke.py: FAIL required=true elapsed_ms=78 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4b_primary_forget_security_smoke.py: FAIL required=true elapsed_ms=78 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4c1_primary_forget_concurrency_smoke.py: FAIL required=true elapsed_ms=78 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4c1_primary_forget_corrected_revision_smoke.py: FAIL required=true elapsed_ms=67 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4c1_primary_forget_fault_smoke.py: FAIL required=true elapsed_ms=68 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4c1_primary_forget_hidden_successor_smoke.py: FAIL required=true elapsed_ms=68 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4c1_primary_forget_security_smoke.py: FAIL required=true elapsed_ms=68 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4c2_primary_forget_concurrency_smoke.py: FAIL required=true elapsed_ms=77 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4c2_primary_forget_fault_smoke.py: FAIL required=true elapsed_ms=68 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4c2_primary_forget_recovery_smoke.py: FAIL required=true elapsed_ms=68 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4c2_primary_forget_security_smoke.py: FAIL required=true elapsed_ms=68 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4e_forget_api_security_smoke.py: FAIL required=true elapsed_ms=35 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4e_forget_api_smoke.py: FAIL required=true elapsed_ms=35 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4f_forget_validation_concurrency_smoke.py: FAIL required=true elapsed_ms=67 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4f_forget_validation_fault_smoke.py: FAIL required=true elapsed_ms=66 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4f_forget_validation_security_smoke.py: FAIL required=true elapsed_ms=68 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4f_forget_validation_smoke.py: FAIL required=true elapsed_ms=38 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i4f_forget_validation_ui_smoke.py: PASS required=true elapsed_ms=29 failure_reason_id=none
  - python scripts/relaylm_phase_i5a_pin_unpin_concurrency_smoke.py: FAIL required=true elapsed_ms=69 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i5a_pin_unpin_contract_smoke.py: FAIL required=true elapsed_ms=69 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i5a_pin_unpin_security_smoke.py: FAIL required=true elapsed_ms=68 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i5a_pin_unpin_token_smoke.py: FAIL required=true elapsed_ms=63 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i5b_pin_unpin_api_projection_smoke.py: FAIL required=true elapsed_ms=34 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i5b_pin_unpin_apply_smoke.py: FAIL required=true elapsed_ms=66 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i5b_pin_unpin_concurrency_smoke.py: FAIL required=true elapsed_ms=67 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i5b_pin_unpin_ranking_smoke.py: FAIL required=true elapsed_ms=66 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i5b_pin_unpin_security_smoke.py: FAIL required=true elapsed_ms=67 failure_reason_id=exit_nonzero
  - python scripts/relaylm_phase_i7c_held_governance_api_smoke.py: PASS required=true elapsed_ms=28 failure_reason_id=none
  - python scripts/relaylm_phase_i7c_held_governance_concurrency_smoke.py: PASS required=true elapsed_ms=64 failure_reason_id=none
  - python scripts/relaylm_phase_i7c_held_governance_runtime_smoke.py: PASS required=true elapsed_ms=64 failure_reason_id=none
  - python scripts/relaylm_phase_i7c_held_governance_security_smoke.py: PASS required=true elapsed_ms=59 failure_reason_id=none
  - python scripts/relaylm_phase_i7c_held_governance_ui_smoke.py: PASS required=true elapsed_ms=28 failure_reason_id=none
- docs_completion_model: PASS required=true elapsed_ms=286 failure_reason_id=none
  - python scripts/relaylm_mvp_completion_report_smoke.py --check-model docs/evidence/implementation/mvp_eval_runner_completion_report.md: PASS required=true elapsed_ms=36 failure_reason_id=none
  - python scripts/relaylm_docs_link_check.py: PASS required=true elapsed_ms=212 failure_reason_id=none
  - python scripts/relaylm_documentation_current_boundary_smoke.py: PASS required=true elapsed_ms=38 failure_reason_id=none
first_failure: category=e1_provenance_grounding_recall command=python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py failure_reason_id=exit_nonzero
next_operator_hint: inspect_first_failed_category_and_rerun_explicitly
