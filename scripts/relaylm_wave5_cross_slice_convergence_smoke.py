#!/usr/bin/env python3
"""Validate the Wave 5 cross-slice convergence audit after W5 merge."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "docs/architecture/wave5_cross_slice_convergence_audit.md": (
        "# Wave 5 Cross-Slice Convergence Audit",
        "relaylm_status: historical_after_merge",
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
        "docs/mvp/wave5/e1_completion_report.md",
        "docs/mvp/wave5/o1e_completion_report.md",
        "docs/mvp/wave5/i4f_completion_report.md",
        "docs/architecture/e1_evaluation_consolidation.md",
        "docs/architecture/o1e_scheduler_operational_controls.md",
        "docs/architecture/phase_i4f_forget_validation.md",
        "O1F operational validation",
        "E1-R1 trusted Home scene-admission path",
        "W5-INT is merged.",
    ),
    "docs/PROJECT_STATUS.md": (
        "O1E stale recovery/cancellation/shutdown: complete",
        "O1F operational validation: complete",
        "Phase I-4F full Forget validation: complete",
        "E1 evaluation consolidation: complete",
        "Post-O1F next candidates:",
        "W5-INT merged",
    ),
    "docs/architecture/project_execution_plan.md": (
        "### Wave 5 completed",
        "### O1F validation completed",
        "### Post-O1F next candidates",
        "O1E stale recovery/cancellation/shutdown complete",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "O1A through O1F",
        "bounded scheduler operational controls            complete as O1E",
        "operational validation hardening                  complete as O1F",
    ),
    "docs/mvp/README.md": (
        "Wave 5 merged completion reports",
        "O1E completion report",
        "I-4F completion report",
        "W5-INT is merged",
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

FROZEN_ALLOWLIST = {
    "docs/architecture/wave2_cross_slice_convergence_audit.md",
    "docs/architecture/wave3_cross_slice_convergence_audit.md",
    "docs/architecture/wave4_cross_slice_convergence_audit.md",
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    for path, anchors in REQUIRED.items():
        body = read(path)
        missing = [anchor for anchor in anchors if anchor not in body]
        assert not missing, f"{path}: missing anchors: {missing!r}"

    for path in (
        "docs/PROJECT_STATUS.md",
        "docs/architecture/project_execution_plan.md",
        "docs/architecture/current_target_migration_guide.md",
        "docs/architecture/relaymem_slp_current_target.md",
        "docs/README.md",
        "docs/architecture/README.md",
        "docs/mvp/README.md",
    ):
        if path in FROZEN_ALLOWLIST:
            continue
        body = read(path)
        stale = [anchor for anchor in FORBIDDEN_CURRENT if anchor in body]
        assert not stale, f"{path}: stale Wave 5 anchors: {stale!r}"

    print("Wave 5 cross-slice convergence smoke passed")


if __name__ == "__main__":
    main()
