#!/usr/bin/env python3
"""Validate frozen Wave 5 convergence evidence and stale-current bounds without prose coupling."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "docs/evidence/waves/wave5_cross_slice_convergence_audit.md": (
        "# Wave 5 Cross-Slice Convergence Audit",
        "relaylm_status: frozen",
        "E1 evaluation consolidation",
        "O1E scheduler operational controls",
        "I-4F Forget product-completion validation",
        "#425",
        "#426",
        "#427",
        "#428",
        "95c159ff747a167cd6cf99c7c5df656fd01e345d",
        "49750ccb693ab6ebca1f5a0947c69c06a4a03d31",
        "937718dcb328fda5e3e37bb951b39fc66629f57a",
        "668d0e403102d342f44bf6299cd4dbe0d5f4eaaa",
        "docs/evidence/implementation/e1_completion_report.md",
        "docs/evidence/implementation/o1e_completion_report.md",
        "docs/evidence/implementation/i4f_completion_report.md",
        "docs/architecture/e1_evaluation_consolidation.md",
        "docs/architecture/o1e_scheduler_operational_controls.md",
        "O1F operational validation",
        "E1-R1 trusted Home scene-admission path",
        "W5-INT is merged.",
    ),
    "docs/reference/project-status-reference-map.md": (
        "relaylm_authority: project_status_reference_map",
        "## Completed foundation inventory",
        "RelaySLP durable enqueue, fenced lifecycle, one-job execution, local worker, O1 scheduler",
        "E1-R1 through E1-R5",
        "Wave 3 through Wave 7 integration tracks",
        "Primary MEM Correct, Forget/Hide, Pin/Unpin, Held Apply/Discard",
    ),
    "docs/evidence/implementation/README.md": (
        "O1E completion report",
        "I-4F completion report",
    ),
}

FORBIDDEN_CURRENT = (
    "O1E stale recovery/cancellation/shutdown: unimplemented",
    "O1E/O1F remain target/unimplemented.",
    "O1F operational validation: unimplemented",
    "Post-I-4F next candidates:",
    "Post-Wave-4 next candidates:",
    "W5-INT in progress until the convergence PR merges",
    "W5-INT is in progress until the convergence PR containing this audit is merged.",
)

SCANNED_CURRENT_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/architecture/project_execution_plan.md",
    "docs/architecture/current_target_migration_guide.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/evidence/implementation/README.md",
    "docs/evidence/waves/README.md",
)


def read(path: str) -> str:
    location = ROOT / path
    assert location.exists(), f"missing file: {path}"
    return location.read_text(encoding="utf-8")


def main() -> None:
    for path, anchors in REQUIRED.items():
        body = read(path)
        missing = [anchor for anchor in anchors if anchor not in body]
        assert not missing, f"{path}: missing anchors: {missing!r}"

    for path in SCANNED_CURRENT_DOCS:
        body = read(path)
        stale = [anchor for anchor in FORBIDDEN_CURRENT if anchor in body]
        assert not stale, f"{path}: stale Wave 5 anchors: {stale!r}"

    print("Wave 5 cross-slice convergence smoke passed")


if __name__ == "__main__":
    main()
