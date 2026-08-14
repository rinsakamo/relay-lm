#!/usr/bin/env python3
"""Validate E1 frozen evidence, stable implementation boundaries, and reference indexes."""
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
        "E1-R4 retrieval-response grounding and unsupported-detail suppression remains valid",
        "E1-R5 is retained only as historical completion and convergence evidence",
        "primary_only` fails closed to `neither",
        "subjective_only",
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
        "E1-R4 remains the shared grounding policy",
        "E1-R4 grounded context and unsupported-detail suppression",
        "Current post-retirement boundary",
        "no Primary root resolution, store open, candidate discovery, selection, recall, fallback, or evidence release",
    ),
    "docs/reference/project-status-reference-map.md": (
        "relaylm_authority: project_status_reference_map",
        "## Completed foundation inventory",
        "E1-R1 through E1-R5",
        "## Phase 6 and E1 boundary notes",
        "E1-R4 remains the shared request-side grounding",
        "E1-R5 remains historical implementation evidence",
        "primary_only` fails closed to `neither",
    ),
    "docs/evidence/implementation/e1_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "relaylm_source_pr: 425",
        "E1 MVP Evaluation Evidence Consolidation Completion Report",
        "frozen implementation evidence",
        "e1_completion_report-source.txt",
        "source PR final-head/merge form",
    ),
    "docs/evidence/implementation/e1r1_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "trusted Home scene admission",
    ),
    "docs/evidence/implementation/e1r2_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "character-store bootstrap",
    ),
    "docs/evidence/implementation/e1r3_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "provenance-preserving Primary MEM formation summary",
    ),
    "docs/evidence/implementation/e1r4_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "retrieval-response grounding and unsupported-detail suppression",
    ),
    "docs/evidence/implementation/e1r5_completion_report.md": (
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
    "docs/evidence/waves/wave7_cross_slice_convergence_audit.md": (
        "# Wave 7 Cross-Slice Convergence Audit",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression",
        "W7-INT is merged.",
    ),
    "docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md": (
        "# E1-R5 Post-Wave-7 Correction Convergence Audit",
        "M2 remains the preferred relevance owner.",
        "PM-D8 is closed by PR #491",
        "The former runtime bridge module remains compatibility no-op only.",
    ),
}

EVIDENCE_PATHS = (
    "docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md",
    "docs/architecture/e1r1_trusted_home_scene_admission.md",
    "docs/architecture/e1r2_character_store_bootstrap.md",
    "docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md",
    "docs/architecture/e1r4_retrieval_response_grounding.md",
    "docs/evidence/waves/wave7_cross_slice_convergence_audit.md",
    "docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md",
    "docs/contracts/ui/home-conversation.md",
    "docs/contracts/ui/lifecycle-visibility.md",
    "docs/architecture/integration_i1_primary_mem_two_turn_recall.md",
    "docs/evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md",
    "docs/architecture/phase_i4d_primary_retrieval_exclusion.md",
    "docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md",
    "docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md",
    "docs/architecture/phase6c1_durable_protected_source_persistence.md",
    "docs/architecture/phase6c2_one_queued_primary_worker_integration.md",
    "docs/architecture/o0_local_one_job_runner.md",
    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",
    "docs/evidence/implementation/i1ge-durable-finalization-crash-validation-handoff.md",
    "scripts/relaylm_o0_local_one_job_runner_ci_runner.py",
    "scripts/relaylm_phase6c1_primary_worker_smoke.py",
    "scripts/relaylm_phase6c1_worker_crash_convergence_smoke.py",
    "scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py",
    "scripts/relaylm_e1r3_provenance_formation_summary_smoke.py",
    "scripts/relaylm_e1r3_provenance_formation_security_smoke.py",
    "scripts/relaylm_e1r4_grounded_recall_response_smoke.py",
    "scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py",
    "scripts/relaylm_e1r4_grounded_recall_security_smoke.py",
    "scripts/relaylm_primary_recall_post_retirement_structure_smoke.py",
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
    "E1-R5 remains incomplete",
    "E1-R5 scoped Primary recall candidate discovery bridge is current implemented.",
    "E1-R5 scoped Primary recall bridge                complete as E1-R5",
    "E1-R5 remains a bounded query-hinted fallback",
    "M2 remains preferred, but if no eligible scoped Primary candidate",
    "Later SOUL Lab Home requests can retrieve current eligible Primary MEM",
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
            "docs/evidence/implementation/README.md",
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
        "e1r5_post_wave7_correction_convergence_audit.md",
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
