#!/usr/bin/env python3
"""Validate the Wave 4 cross-slice documentation convergence boundary."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE_PRS = {
    "#417": "2f8597911774b70f1c001db8332b3dfcc18d23ca",
    "#418": "49fb43130155826fcc8b2b951d77484ff8ddaddf",
    "#420": "3e3d2570ecdfcde4c8bfdee06c5607cb6632c133",
    "#421": "5736636da839486140f72c731f18a4a85c39b13c",
    "#423": "5e0f866e959ab2bc5af00e0502b2026f4b52a779",
    "#424": "be0872edea46cb67fd5269bfaa8c7cb8048fb2c4",
}

REQUIRED = {
    "docs/architecture/wave4_cross_slice_convergence_audit.md": (
        "# Wave 4 Cross-Slice Convergence Audit",
        "## Source PR inventory",
        "## Merge commit inventory",
        "## Wave 4 implemented boundary",
        "## Cross-slice authority map",
        "## Preserved non-goals",
        "## Security and content-leakage review",
        "## Concurrency / race / stale-token review",
        "## Documentation convergence changes",
        "## Smoke / validation coverage",
        "## Remaining post-Wave-4 work",
        "## Frozen next inputs",
        "O1D2 bounded scheduler policy/fairness/pacing: complete",
        "Phase I-4E loopback Forget API and SOUL Lab UI: complete",
        "UI-B1A read-only lifecycle visibility: complete",
        "I-5A Pin / Unpin contract and read-only preflight: complete",
        "I-7A/B Held Apply / Discard contract and read-only preflight: complete",
        "W4-INT is merged",
    ),
    "docs/PROJECT_STATUS.md": (
        "O1D2 bounded scheduler policy/fairness/pacing: complete",
        "O1E stale recovery/cancellation/shutdown: unimplemented",
        "O1F operational validation: unimplemented",
        "O1 overall: in progress",
        "Phase I-4E loopback Forget API and SOUL Lab UI: complete",
        "Phase I-4F full Forget validation: unimplemented",
        "Phase I-4 overall: in progress",
        "UI-B1A read-only lifecycle visibility: complete",
        "I-5A Pin / Unpin contract and read-only preflight: complete",
        "I-5 runtime apply/API/UI/ranking behavior: unimplemented",
        "I-7A/B Held Apply / Discard contract and read-only preflight: complete",
        "I-7 runtime apply/discard/API/UI/durable governance evidence: unimplemented",
        "Wave 4 implementation tracks complete",
        "W4-INT merged",
        "Post-Wave-4 next candidates:",
    ),
    "docs/architecture/project_execution_plan.md": (
        "### Wave 4 completed",
        "O1D2 bounded scheduler policy/fairness/pacing",
        "I-4E loopback API and SOUL Lab Forget UI",
        "UI-B1A read-only lifecycle visibility",
        "I-5A Pin / Unpin contract/preflight",
        "I-7A/B Held Apply / Discard contract/preflight",
        "### Post-Wave-4 next candidates",
        "O1E stale recovery/cancellation/shutdown",
        "O1F operational validation",
        "I-4F crash/race/security/fresh-conversation validation",
        "I-5B or Pin/Unpin apply/API/UI/ranking work, if defined",
        "I-7C or Held Apply/Discard runtime/API/UI/durable evidence work, if defined",
        "E1-R1 trusted Home scene-admission path",
        "O2/O3 should remain after O1E/O1F",
    ),
    "docs/architecture/current_target_migration_guide.md": (
        "O1D2 is current implemented as bounded policy wrapper.",
        "O1E/O1F remain target/unimplemented.",
        "I-4E is current implemented as loopback Forget API/UI.",
        "I-4F remains target/unimplemented validation.",
        "UI-B1A is current implemented read-only visibility.",
        "I-5A is current implemented contract/read-only preflight only.",
        "I-7A/B is current implemented contract/read-only preflight only.",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "O1D2 is current implemented as a bounded policy wrapper",
        "O1E stale recovery/cancellation/shutdown, O1F operational validation",
        "I-4E is current implemented as loopback Forget API/UI.",
        "I-4F remains target/unimplemented validation.",
        "UI-B1A is current implemented read-only visibility.",
        "I-5A is current implemented contract/read-only preflight only.",
        "I-7A/B is current implemented contract/read-only preflight only.",
    ),
}

REQUIRED_LINKS = (
    "wave4_cross_slice_convergence_audit.md",
    "o1d2_scheduler_policy.md",
    "phase_i5_pin_unpin_contract.md",
    "phase_i7ab_held_apply_discard_contract.md",
    "o1d2_completion_report.md",
    "i4e_completion_report.md",
    "ui_b1a_completion_report.md",
    "i5a_completion_report.md",
    "i7ab_completion_report.md",
)

STALE = (
    "Scheduler remaining production: O1D2 policy",
    "Phase I-4E loopback API and SOUL Lab Forget UI: unimplemented",
    "Current Wave 4 follow-up work:",
    "Wave 4 follow-up queue",
    "W4-INT in progress until the convergence PR merges",
    "W4-INT is complete only after that convergence PR merges",
    "W4-INT completes only after the convergence PR containing this audit is merged",
)

FALSE_COMPLETION = (
    "O1E stale recovery/cancellation/shutdown: complete",
    "O1F operational validation: complete",
    "Phase I-4F full Forget validation: complete",
    "I-5 runtime apply/API/UI/ranking behavior: complete",
    "I-7 runtime apply/discard/API/UI/durable governance evidence: complete",
)

CONTENT_LEAKAGE_ANCHORS = (
    "runtime-private source body:",
    "raw prompt:",
    "conversation body:",
    "transcript body:",
    "queue lease secret:",
)

TOUCHED_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/mvp/README.md",
    "docs/architecture/project_execution_plan.md",
    "docs/architecture/current_target_migration_guide.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/wave4_cross_slice_convergence_audit.md",
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
    stale = [anchor for anchor in anchors if anchor.lower() in lowered]
    assert not stale, f"{path}: forbidden anchors: {stale!r}"


def validate_source_inventory() -> None:
    audit = read("docs/architecture/wave4_cross_slice_convergence_audit.md")
    for pr, commit in SOURCE_PRS.items():
        assert pr in audit, f"audit missing source PR {pr}"
        assert commit in audit, f"audit missing merge commit {commit}"


def validate_links() -> None:
    combined = "\n".join(read(path) for path in ("docs/README.md", "docs/architecture/README.md", "docs/mvp/README.md"))
    for required in REQUIRED_LINKS:
        assert required in combined, f"index links missing {required}"


def main() -> None:
    for path, anchors in REQUIRED.items():
        require(path, anchors)
    for path in TOUCHED_DOCS:
        forbid(path, STALE)
        forbid(path, FALSE_COMPLETION)
        forbid(path, CONTENT_LEAKAGE_ANCHORS)
    validate_source_inventory()
    validate_links()
    print("Wave 4 cross-slice convergence smoke passed")


if __name__ == "__main__":
    main()
