#!/usr/bin/env python3
"""Data registry for the explicit RelayLM MVP eval runner."""
from __future__ import annotations

RUNNER_FILES = {
    "relaylm_mvp_eval_runner.py",
    "relaylm_mvp_eval_runner_impl.py",
    "relaylm_mvp_eval_runner_registry.py",
    "relaylm_mvp_eval_runner_smoke.py",
    "relaylm_mvp_eval_runner_security_smoke.py",
}

REQUIRED_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/architecture/project_execution_plan.md",
    "docs/architecture/e1_evaluation_consolidation.md",
)

E1_SCRIPTS = """
relaylm_e1r3_provenance_formation_summary_smoke.py
relaylm_e1r3_provenance_formation_security_smoke.py
relaylm_e1r4_grounded_recall_response_smoke.py
relaylm_e1r4_unsupported_detail_suppression_smoke.py
relaylm_e1r4_grounded_recall_security_smoke.py
relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py
relaylm_e1r5_primary_mem_recall_bridge_security_smoke.py
relaylm_e1r5_primary_mem_recall_no_symlink_smoke.py
relaylm_e1r5_primary_mem_recall_bridge_relevance_bounds_smoke.py
relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py
""".split()

TWO_TURN_SCRIPTS = """
relaylm_phase_i1_two_turn_primary_recall_smoke.py
relaylm_phase_i1_two_turn_primary_recall_security_smoke.py
relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py
""".split()

O1_SCRIPTS = """
relaylm_o1a_scheduler_contract_smoke.py
relaylm_o1b_sealed_replay_lane_smoke.py
relaylm_o1c_eligible_queue_lane_smoke.py
relaylm_o1d1_production_round_smoke.py
relaylm_o1d2_scheduler_policy_smoke.py
relaylm_o1e_scheduler_operational_controls_smoke.py
relaylm_o1f_operational_validation_smoke.py
relaylm_o1f_operational_validation_corruption_smoke.py
relaylm_o1f_operational_validation_concurrency_smoke.py
relaylm_o1f_operational_validation_saturation_smoke.py
relaylm_o1f_operational_validation_restart_smoke.py
relaylm_o1f_operational_validation_security_smoke.py
""".split()

DOC_COMMANDS = (
    (
        "relaylm_mvp_completion_report_smoke.py",
        ("--check-model", "docs/mvp/wave8/mvp_eval_runner_completion_report.md"),
    ),
    ("relaylm_docs_link_check.py", ()),
    ("relaylm_documentation_current_boundary_smoke.py", ()),
)

GOVERNANCE_PATTERNS = {
    "forget_hide": ("*forget*smoke.py", "*hide*smoke.py", "relaylm_phase_i4f*_smoke.py"),
    "pin_unpin": ("*pin*unpin*smoke.py", "relaylm_phase_i5b*_smoke.py"),
    "held_apply_discard": ("*held*apply*discard*smoke.py", "relaylm_phase_i7c*_smoke.py"),
    "correct": ("*correct*smoke.py", "relaylm_phase_i3*_smoke.py"),
}
