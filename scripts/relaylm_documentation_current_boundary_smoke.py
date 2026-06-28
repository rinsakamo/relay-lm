#!/usr/bin/env python3
"""Validate current documentation boundary anchors after Wave 7."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CURRENT_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/mvp/README.md",
    "docs/DOCUMENTATION_MODEL.md",
    "docs/architecture/current_target_migration_guide.md",
    "docs/architecture/project_execution_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/e1_evaluation_consolidation.md",
    "docs/architecture/e1r1_trusted_home_scene_admission.md",
    "docs/architecture/e1r2_character_store_bootstrap.md",
    "docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md",
    "docs/architecture/e1r4_retrieval_response_grounding.md",
    "docs/architecture/phase_i5_pin_unpin_contract.md",
    "docs/architecture/phase_i5b_pin_unpin_apply.md",
    "docs/architecture/phase_i7ab_held_apply_discard_contract.md",
    "docs/architecture/phase_i7c_held_apply_discard_runtime.md",
    "docs/architecture/soul_lab_ui_mvp.md",
    "docs/architecture/wave7_cross_slice_convergence_audit.md",
    "docs/architecture/wave6_cross_slice_convergence_audit.md",
)

REQUIRED = {
    "docs/PROJECT_STATUS.md": (
        "This page owns current implementation status and active caveats.",
        "O1F operational validation: complete",
        "O1 overall: complete through validation-only caller-invoked local scheduler boundary",
        "O2 supervised worker service: planned/unimplemented",
        "O3 always-on local operation: planned/unimplemented",
        "I-5B Pin / Unpin apply/API/UI/ranking behavior: complete",
        "I-7C Held Apply/Discard runtime/API/UI/durable governance evidence: complete",
        "E1-R1 trusted Home scene admission: complete",
        "E1-R2 character-store bootstrap command: complete",
        "E1-R3 provenance-preserving Primary MEM formation summary: complete",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression: complete",
        "Wave 7 implementation tracks complete",
        "W7-INT merged",
        "Post-E1-R4 / Post-Wave-7 next candidates:",
    ),
    "docs/README.md": (
        "[Current project status](PROJECT_STATUS.md) — the single current implementation status authority.",
        "Wave 7 Cross-Slice Convergence Audit",
        "E1-R3 completion report",
        "E1-R4 completion report",
        "E1-R4 retrieval-response grounding",
    ),
    "docs/architecture/README.md": (
        "Wave 7 Cross-Slice Convergence Audit",
        "E1-R4 Retrieval-Response Grounding",
        "implemented E1-R1/E1-R2/E1-R3/E1-R4 evidence",
    ),
    "docs/mvp/README.md": (
        "Wave 7 merged completion reports",
        "source PR #436, merge `7bb2525cb000e893146408065f1aa5976f2b54ab`",
        "source PR #437, merge `e6e5b32cd489dda493ff0171a260dd561a91765c`",
        "docs/mvp/wave7/e1r4_completion_report.md",
    ),
    "docs/architecture/current_target_migration_guide.md": (
        "Current Wave 7 compatibility interpretation",
        "E1-R3 is current implemented as provenance-preserving Primary MEM formation summary.",
        "E1-R4 is current implemented as request-side retrieval-response grounding and unsupported-detail suppression.",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "E1-R4 request-side evidence-grounded recall behavior is current implemented.",
        "request-side grounded recall response             complete as E1-R4",
        "E1-R4 is request-side retrieval-response grounding",
    ),
    "docs/architecture/e1r4_retrieval_response_grounding.md": (
        "# E1-R4 Retrieval-Response Grounding",
        "relaymem.grounded_recall_context.v0",
        "directly_supported",
        "inferred_from_supported",
        "unsupported_detail_suppressed",
        "runtime_private_evidence_omitted=true",
    ),
    "docs/architecture/wave7_cross_slice_convergence_audit.md": (
        "# Wave 7 Cross-Slice Convergence Audit",
        "PR #436",
        "7bb2525cb000e893146408065f1aa5976f2b54ab",
        "PR #437",
        "e6e5b32cd489dda493ff0171a260dd561a91765c",
        "E1-R3 provenance-preserving Primary MEM formation summary: complete",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression: complete",
        "W7-INT is merged.",
    ),
    "docs/mvp/wave7/e1r4_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "retrieval-response grounding and unsupported-detail suppression",
        "Request-side vs response-side decision",
        "Content leakage review",
        "Authority preservation",
    ),
}

STALE = tuple(
    line.strip()
    for line in """
    W5-INT in progress until the convergence PR merges
    W5-INT is in progress until the convergence PR containing this audit is merged.
    O1F remains target/unimplemented.
    I-5 runtime apply/API/UI/ranking behavior: unimplemented
    I-7 runtime apply/discard/API/UI/durable governance evidence: unimplemented
    Direct Home-origin formation: not currently proven; trusted scene admission is missing
    Direct Home-origin trusted scene admission remains target work
    Pin/Unpin runtime API/UI/ranking behavior: pending
    Held Apply/Discard runtime API/UI/durable evidence: pending
    Character-store bootstrap remains operator-facing and brittle
    E1-R3 provenance-preserving Primary MEM formation summary current next candidate
    E1-R4 retrieval-response grounding and unsupported-detail suppression current next candidate
    E1-R4 evidence-grounded recall behavior remains quality work
    E1-R4 remains incomplete quality/evaluation work
    E1-R4 response grounding.
    remaining E1-R4 quality work
    """.splitlines()
    if line.strip()
)


def read(path: str) -> str:
    location = ROOT / path
    assert location.exists(), f"missing file: {path}"
    return location.read_text(encoding="utf-8")


def require(path: str, anchors: tuple[str, ...]) -> None:
    body = read(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing anchors: {missing!r}"


def forbid_current_stale(path: str) -> None:
    if "wave" in path and "cross_slice_convergence_audit" in path:
        return
    body = read(path)
    stale = [anchor for anchor in STALE if anchor in body]
    assert not stale, f"{path}: stale anchors: {stale!r}"


def main() -> None:
    for path, anchors in REQUIRED.items():
        require(path, anchors)
    for path in CURRENT_DOCS:
        forbid_current_stale(path)
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main()
