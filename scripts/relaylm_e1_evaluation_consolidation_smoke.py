#!/usr/bin/env python3
"""Validate the E1 MVP evaluation evidence consolidation boundary after E1-R5."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "docs/architecture/e1_evaluation_consolidation.md": (
        "# E1 MVP Evaluation Evidence Consolidation",
        "## Current E1 proof boundary",
        "## Evidence inventory",
        "## Implemented evidence vs remaining quality work",
        "E1-R1 route-owned trusted Home admission",
        "E1-R2 character-store bootstrap is implemented",
        "E1-R3 provenance-preserving Primary MEM formation summary is implemented",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression is implemented",
        "E1-R5 recall candidate discovery bridge is implemented",
        "Wave 7 Cross-Slice Convergence Audit",
        "## Direct Home-origin admission decision record",
        "Option A",
        "Option B",
        "Implemented by E1-R1",
        "## Character-store bootstrap ergonomics",
        "E1-R2 idempotent character-store bootstrap command",
        "## Speaker-provenance-safe memory summary formation",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "## Evidence-grounded recall behavior",
        "E1-R4 distinguishes retrieved fact from inference",
        "E1-R4 suppresses unsupported date, name, preference, quantity, relationship, and cause details",
        "Implemented E1-R4/E1-R5 boundary",
    ),
    "docs/PROJECT_STATUS.md": (
        "E1 evaluation consolidation: complete",
        "E1-R1 trusted Home scene admission: complete",
        "E1-R2 character-store bootstrap command: complete",
        "E1-R3 provenance-preserving Primary MEM formation summary: complete",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression: complete",
        "E1-R5 Primary MEM recall candidate discovery bridge: complete",
        "W6-INT merged",
        "Wave 7 implementation tracks complete",
        "W7-INT merged",
        "Post-Wave-7 E1-R5 correction merged and converged",
        "Home can be a trusted formation source only through the E1-R1 route-owned gate; browser-owned trust remains rejected.",
    ),
    "docs/architecture/project_execution_plan.md": (
        "E1 evaluation consolidation                    complete",
        "E1-R1 trusted Home scene-admission path         complete",
        "E1-R2 idempotent character-store bootstrap command complete",
        "E1-R3 provenance-preserving Primary MEM formation summary complete",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression complete",
        "E1-R5 Primary MEM recall candidate discovery bridge complete",
        "### Wave 7 completed",
        "### Post-Wave-7 E1-R5 correction completed",
        "### Post-E1-R5 / Post-Wave-7 next candidates",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "E1-R1 route-owned trusted Home scene admission is current implemented.",
        "E1-R2 dry-run-first character-store bootstrap is current implemented.",
        "E1-R3 provenance-preserving summary formation is current implemented.",
        "E1-R4 request-side evidence-grounded recall behavior is current implemented.",
        "E1-R5 scoped Primary recall candidate discovery bridge is current implemented.",
        "request-side grounded recall response             complete as E1-R4",
        "E1-R5 scoped Primary recall bridge                complete as E1-R5",
    ),
    "docs/architecture/current_target_migration_guide.md": (
        "Current Wave 7 compatibility interpretation",
        "E1-R1 is current implemented as route-owned trusted Home scene admission.",
        "E1-R2 is current implemented as dry-run-first character-store bootstrap.",
        "E1-R3 is current implemented as provenance-preserving Primary MEM formation summary.",
        "E1-R4 is current implemented as request-side retrieval-response grounding and unsupported-detail suppression.",
        "E1-R5 is current implemented as bounded scoped Primary MEM recall candidate discovery bridge.",
    ),
    "docs/README.md": (
        "E1 MVP evaluation consolidation",
        "E1-R1 trusted Home scene admission",
        "E1-R2 character-store bootstrap command",
        "E1-R3 provenance-preserving formation summary",
        "E1-R4 retrieval-response grounding",
        "E1-R5 Primary MEM recall candidate discovery bridge",
        "Wave 7 Cross-Slice Convergence Audit",
        "E1-R1 completion report",
        "E1-R2 completion report",
        "E1-R3 completion report",
        "E1-R4 completion report",
        "E1-R5 completion report",
    ),
    "docs/architecture/README.md": (
        "E1 MVP Evaluation Evidence Consolidation",
        "E1-R1 Trusted Home Scene Admission",
        "E1-R2 Character Store Bootstrap",
        "E1-R3 Provenance-Preserving Primary MEM Formation Summary",
        "E1-R4 Retrieval-Response Grounding",
        "E1-R5 Primary MEM Recall Candidate Discovery Bridge",
        "Wave 7 Cross-Slice Convergence Audit",
    ),
    "docs/mvp/README.md": (
        "Wave 7 merged completion reports",
        "E1-R1 completion report",
        "E1-R2 completion report",
        "E1-R3 completion report",
        "E1-R4 completion report",
        "E1-R5 completion report",
    ),
    "docs/mvp/wave5/e1_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "## Implemented production boundary",
        "No runtime behavior changed.",
        "E1 evaluation consolidation",
    ),
    "docs/mvp/wave6/e1r1_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "trusted Home scene admission",
    ),
    "docs/mvp/wave6/e1r2_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "character-store bootstrap",
    ),
    "docs/mvp/wave7/e1r3_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "provenance-preserving Primary MEM formation summary",
    ),
    "docs/mvp/wave7/e1r4_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "retrieval-response grounding and unsupported-detail suppression",
    ),
    "docs/mvp/wave7/e1r5_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "Primary MEM Recall Candidate Discovery Bridge",
        "PR: #439",
    ),
    "docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md": (
        "relaylm_doc_type: implementation_handoff",
        "user_assertion_evidence",
        "assistant_acknowledgement_evidence",
        "assistant_speculation_or_non_factual_evidence",
        "Downstream E1-R4 boundary",
    ),
    "docs/architecture/e1r4_retrieval_response_grounding.md": (
        "relaylm_doc_type: implementation_handoff",
        "relaymem.grounded_recall_context.v0",
        "unsupported_detail_suppressed",
    ),
    "docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md": (
        "relaylm_doc_type: implementation_handoff",
        "Primary MEM Recall Candidate Discovery Bridge",
        "shared I-4D current-state eligibility index",
        "PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py",
    ),
    "docs/architecture/wave7_cross_slice_convergence_audit.md": (
        "# Wave 7 Cross-Slice Convergence Audit",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression",
        "W7-INT is merged.",
    ),
}

EVIDENCE_PATHS = (
    "docs/architecture/e1_local_runtime_evaluation_2026_06_25.md",
    "docs/architecture/e1r1_trusted_home_scene_admission.md",
    "docs/architecture/e1r2_character_store_bootstrap.md",
    "docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md",
    "docs/architecture/e1r4_retrieval_response_grounding.md",
    "docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md",
    "docs/architecture/wave7_cross_slice_convergence_audit.md",
    "docs/architecture/soul_lab_ui_b0_real_home_conversation.md",
    "docs/architecture/soul_lab_ui_b1a_lifecycle_visibility.md",
    "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
    "docs/architecture/phase_i2_real_soul_lab_observation.md",
    "docs/architecture/phase_i4d_primary_retrieval_exclusion.md",
    "docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md",
    "docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md",
    "docs/architecture/phase6c1_durable_protected_source_persistence.md",
    "docs/architecture/phase6c2_one_queued_primary_worker_integration.md",
    "docs/architecture/o0_local_one_job_runner.md",
    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",
    "docs/architecture/i1ge_durable_finalization_crash_validation.md",
    "scripts/relaylm_o0_local_one_job_runner_ci_runner.py",
    "scripts/relaylm_phase6c1_primary_worker_smoke.py",
    "scripts/relaylm_phase6c1_worker_crash_convergence_smoke.py",
    "scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py",
    "scripts/relaylm_e1r3_provenance_formation_summary_smoke.py",
    "scripts/relaylm_e1r3_provenance_formation_security_smoke.py",
    "scripts/relaylm_e1r4_grounded_recall_response_smoke.py",
    "scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py",
    "scripts/relaylm_e1r4_grounded_recall_security_smoke.py",
    "scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py",
    "scripts/relaylm_e1r5_primary_mem_recall_bridge_security_smoke.py",
    "scripts/relaylm_e1r5_primary_mem_recall_no_symlink_smoke.py",
    "scripts/relaylm_e1r5_primary_mem_recall_bridge_relevance_bounds_smoke.py",
    "scripts/relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py",
)

STALE = (
    "Home requests do not currently carry a server-owned trusted scene-admission projection",
    "Direct Home-origin formation: not currently proven; trusted scene admission is missing",
    "Direct Home-origin trusted scene admission remains target work",
    "Character-store bootstrap remains operator-facing and brittle",
    "E1-R1 trusted Home scene-admission path: candidate",
    "E1-R2 idempotent character-store bootstrap command: candidate",
    "E1-R1 trusted Home scene-admission path         candidate",
    "Trusted Home admission is implemented, but formation quality risks are not solved.",
    "E1-R3 provenance-preserving Primary MEM formation summary  current next candidate",
    "E1-R4 retrieval-response grounding and unsupported-detail suppression current next candidate",
    "Recall evidence is present, but evidence-grounded response behavior is not fully evaluated.",
    "E1-R4 evidence-grounded recall behavior remains quality work",
    "E1-R4 remains incomplete quality/evaluation work",
    "M2 alone always selects current eligible scoped Primary MEM",
    "E1-R5 remains incomplete",
)

SCANNED_DOCS = (
    "docs/architecture/e1_evaluation_consolidation.md",
    "docs/PROJECT_STATUS.md",
    "docs/architecture/project_execution_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/current_target_migration_guide.md",
)


def read(path: str) -> str:
    location = ROOT / path
    assert location.exists(), f"missing file: {path}"
    return location.read_text(encoding="utf-8")


def require(path: str, anchors: tuple[str, ...]) -> None:
    body = read(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing anchors: {missing!r}"


def forbid(path: str, anchors: tuple[str, ...]) -> None:
    lowered = read(path).lower()
    forbidden = [anchor for anchor in anchors if anchor.lower() in lowered]
    assert not forbidden, f"{path}: forbidden anchors: {forbidden!r}"


def validate_evidence_paths() -> None:
    missing = [path for path in EVIDENCE_PATHS if not (ROOT / path).exists()]
    assert not missing, f"missing E1 evidence paths: {missing!r}"


def validate_indexes_reference_e1() -> None:
    combined = "\n".join(
        read(path)
        for path in (
            "docs/README.md",
            "docs/architecture/README.md",
            "docs/mvp/README.md",
        )
    )
    for required in (
        "e1_evaluation_consolidation.md",
        "e1_local_runtime_evaluation_2026_06_25.md",
        "e1r1_trusted_home_scene_admission.md",
        "e1r2_character_store_bootstrap.md",
        "e1r3_provenance_preserving_primary_mem_formation_summary.md",
        "e1r4_retrieval_response_grounding.md",
        "e1r5_primary_mem_recall_candidate_bridge.md",
        "wave7_cross_slice_convergence_audit.md",
        "e1_completion_report.md",
        "e1r1_completion_report.md",
        "e1r2_completion_report.md",
        "e1r3_completion_report.md",
        "e1r4_completion_report.md",
        "e1r5_completion_report.md",
    ):
        assert required in combined, f"index links missing {required}"


def main() -> None:
    for path, anchors in REQUIRED.items():
        require(path, anchors)
    for path in SCANNED_DOCS:
        forbid(path, STALE)
    validate_evidence_paths()
    validate_indexes_reference_e1()
    print("E1 evaluation consolidation smoke passed")


if __name__ == "__main__":
    main()
