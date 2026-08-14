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

REQUIRED_DOC_ANCHORS = {
    "docs/reference/project-status-reference-map.md": (
        "relaylm_authority: project_status_reference_map",
        "## Completed foundation inventory",
        "opt-in O2/O3 process operation",
        "## O1/O2/O3 boundary notes",
        "## Phase 6 and E1 boundary notes",
        "E1-R5 remains historical evidence; primary_only fails closed to neither",
        "o2_supervised_scheduler_service.md",
        "o3_always_on_local_scheduler.md",
    ),
    "docs/architecture/o2_supervised_scheduler_service.md": (
        "relaylm_authority: o2_supervised_scheduler_service_boundary",
        "# O2 Supervised Scheduler Service",
        "## Authority",
        "O2 has no independent memory, queue, worker, stale-recovery, or finalization authority.",
        "## Non-goals and boundaries",
        "- start background threads;",
        "- start from `create_app()`;",
        "- turn scheduling on by default;",
    ),
    "docs/architecture/o3_always_on_local_scheduler.md": (
        "relaylm_authority: o3_always_on_local_scheduler_boundary",
        "# O3 Always-On Local Scheduler",
        "## Authority",
        "O3 is local operation support. It is not app-embedded and is not browser authority.",
        "## Non-goals and boundaries",
        "- start automatically from FastAPI `create_app()`;",
        "- turn scheduler gates on by default;",
        "- directly mutate queue records;",
    ),
    "docs/architecture/e1_evaluation_consolidation.md": (
        "relaylm_authority: e1_mvp_evaluation_evidence_consolidation",
        "# E1 MVP Evaluation Evidence Consolidation",
        "## Current E1 proof boundary",
        "scripts/relaylm_primary_recall_post_retirement_structure_smoke.py",
        "does not require a live LLM",
    ),
}

E1_SCRIPTS = """
relaylm_e1r3_provenance_formation_summary_smoke.py
relaylm_e1r3_provenance_formation_security_smoke.py
relaylm_e1r4_grounded_recall_response_smoke.py
relaylm_e1r4_unsupported_detail_suppression_smoke.py
relaylm_e1r4_grounded_recall_security_smoke.py
relaylm_primary_recall_post_retirement_structure_smoke.py
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
    ("relaylm_mvp_completion_report_pr_link_smoke.py", ()),
    ("relaylm_docs_link_check.py", ()),
    ("relaylm_documentation_current_boundary_smoke.py", ()),
)

GOVERNANCE_PATTERNS = {
    "forget_hide": ("*forget*smoke.py", "*hide*smoke.py", "relaylm_phase_i4f*_smoke.py"),
    "pin_unpin": ("*pin*unpin*smoke.py", "relaylm_phase_i5b*_smoke.py"),
    "held_apply_discard": ("*held*apply*discard*smoke.py", "relaylm_phase_i7c*_smoke.py"),
    "correct": ("relaylm_phase_i3*_smoke.py",),
}
