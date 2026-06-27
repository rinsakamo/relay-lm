#!/usr/bin/env python3
"""Validate the E1 MVP evaluation evidence consolidation boundary."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "docs/architecture/e1_evaluation_consolidation.md": (
        "# E1 MVP Evaluation Evidence Consolidation",
        "## Current E1 proof boundary",
        "## Evidence inventory",
        "## Implemented evidence vs assumptions",
        "## Direct Home-origin formation decision record",
        "Option A",
        "Option B",
        "Recommended for the current MVP boundary.",
        "E1-R1 trusted Home scene-admission path",
        "## Character-store bootstrap ergonomics",
        "E1-R2 idempotent character-store bootstrap command",
        "## Speaker-provenance-safe memory summary formation",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "## Evidence-grounded recall behavior",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression",
        "## Evaluation smoke boundary",
        "Home conversation is real, but Home-origin trusted memory formation is not proven.",
        "Trusted formation lane is proven, but all formation quality risks are not solved.",
        "Recall evidence is present, but evidence-grounded response behavior is not fully evaluated.",
    ),
    "docs/PROJECT_STATUS.md": (
        "E1 evaluation consolidation: complete",
        "Direct Home-origin formation: not currently proven; trusted scene admission is missing",
        "W4-INT merged",
        "Home is conversation, recall, observation, and governance evaluation unless a future trusted scene-admission phase changes that boundary.",
    ),
    "docs/architecture/project_execution_plan.md": (
        "E1 evaluation consolidation                    complete",
        "direct Home-origin formation decision           Option A for current MVP",
        "E1-R1 trusted Home scene-admission path",
        "E1-R2 idempotent character-store bootstrap command",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "E1 evaluation consolidation is current as an evidence/documentation boundary.",
        "Direct Home-origin trusted memory formation remains unimplemented.",
    ),
    "docs/architecture/current_target_migration_guide.md": (
        "E1 evaluation consolidation is current docs/evidence only",
        "Direct Home-origin trusted scene admission remains target work",
    ),
    "docs/README.md": (
        "E1 MVP evaluation consolidation",
        "E1 completion report",
    ),
    "docs/architecture/README.md": (
        "E1 MVP Evaluation Evidence Consolidation",
    ),
    "docs/mvp/README.md": (
        "Wave 5 merged completion reports",
        "E1 completion report",
    ),
    "docs/mvp/wave5/e1_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "## Implemented production boundary",
        "No runtime behavior changed.",
        "E1 evaluation consolidation",
    ),
}

EVIDENCE_PATHS = (
    "docs/architecture/e1_local_runtime_evaluation_2026_06_25.md",
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
    "scripts/relaylm_i1ge_durable_finalization_security_smoke.py",
    "scripts/relaylm_i1ge_durable_finalization_concurrency_smoke.py",
)

STALE = (
    "Home-origin trusted memory formation is proven",
    "Direct Home-origin formation: complete",
    "trusted scene admission for direct Home-origin Primary MEM formation: complete",
    "E1-R1 trusted Home scene-admission path: complete",
    "E1-R2 idempotent character-store bootstrap command: complete",
    "E1-R3 provenance-preserving Primary MEM formation summary: complete",
    "E1-R4 retrieval-response grounding and unsupported-detail suppression: complete",
)

CONTENT_LEAKAGE_ANCHORS = (
    "runtime-private source body:",
    "raw prompt:",
    "conversation body:",
    "transcript body:",
    "queue lease secret:",
    "claim token:",
    "token digest:",
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
        "e1_completion_report.md",
    ):
        assert required in combined, f"index links missing {required}"


def main() -> None:
    for path, anchors in REQUIRED.items():
        require(path, anchors)
    for path in SCANNED_DOCS:
        forbid(path, STALE)
        forbid(path, CONTENT_LEAKAGE_ANCHORS)
    validate_evidence_paths()
    validate_indexes_reference_e1()
    print("E1 evaluation consolidation smoke passed")


if __name__ == "__main__":
    main()
