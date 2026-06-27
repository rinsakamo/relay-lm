#!/usr/bin/env python3
"""Validate current documentation boundary anchors after Wave 5 convergence."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CURRENT_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/mvp/README.md",
    "docs/architecture/current_target_migration_guide.md",
    "docs/architecture/project_execution_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/o1e_scheduler_operational_controls.md",
    "docs/architecture/e1_evaluation_consolidation.md",
    "docs/architecture/phase_i4f_forget_validation.md",
    "docs/architecture/wave2_cross_slice_convergence_audit.md",
    "docs/architecture/wave3_cross_slice_convergence_audit.md",
    "docs/architecture/wave4_cross_slice_convergence_audit.md",
    "docs/architecture/wave5_cross_slice_convergence_audit.md",
)

REQUIRED = {
    "docs/PROJECT_STATUS.md": (
        "This page owns current implementation status and active caveats.",
        "[Project Execution Plan](architecture/project_execution_plan.md) owns MVP boundary, dependency sequencing, and roadmap ordering.",
        "I1-GE full production crash validation: complete",
        "I1-G overall: complete",
        "O1D2 bounded scheduler policy/fairness/pacing: complete",
        "O1E stale recovery/cancellation/shutdown: complete",
        "O1F operational validation: unimplemented",
        "O1 overall: in progress",
        "Phase I-4E loopback Forget API and SOUL Lab UI: complete",
        "Phase I-4F full Forget validation: complete",
        "Phase I-4 overall: complete",
        "UI-B1A read-only lifecycle visibility: complete",
        "I-5A Pin / Unpin contract and read-only preflight: complete",
        "I-5 runtime apply/API/UI/ranking behavior: unimplemented",
        "I-7A/B Held Apply / Discard contract and read-only preflight: complete",
        "I-7 runtime apply/discard/API/UI/durable governance evidence: unimplemented",
        "Wave 4 implementation tracks complete",
        "W4-INT merged",
        "Post-Wave-4 / Wave 5 implementation tracks complete",
        "W5-INT in progress until the convergence PR merges",
        "E1 evaluation consolidation: complete",
        "Direct Home-origin formation: not currently proven; trusted scene admission is missing",
        "Post-W5-INT next candidates:",
    ),
    "docs/README.md": (
        "[Current project status](PROJECT_STATUS.md) — the single current implementation status authority.",
        "[Project execution plan](architecture/project_execution_plan.md) — the single MVP execution plan and post-MVP roadmap authority.",
        "Current runtime and implementation status is intentionally not summarized here.",
        "O1D2 deterministic scheduler policy",
        "O1E scheduler operational controls",
        "Phase I-4F Forget product validation",
        "Phase I-5A Pin / Unpin contract and read-only preflight",
        "Phase I-7A/B Held Apply / Discard contract and read-only preflight",
        "Wave 5 Cross-Slice Convergence Audit",
        "O1E completion report",
        "I-4F completion report",
        "E1 MVP evaluation consolidation",
        "E1 completion report",
        "The next wave and release/evaluation gate remain closed",
    ),
    "docs/mvp/README.md": (
        "Wave 5 merged completion reports",
        "E1 completion report",
        "O1E completion report",
        "I-4F completion report",
        "Wave 5 Cross-Slice Convergence Audit",
        "Wave 4 merged completion reports",
        "O1D2 completion report",
        "I-4E completion report",
        "UI-B1A completion report",
        "I-5A completion report",
        "I-7A/B completion report",
        "Wave 4 Cross-Slice Convergence Audit",
    ),
    "docs/architecture/README.md": (
        "[Project Execution Plan](project_execution_plan.md)",
        "The current Product and RelayMEM status is intentionally not summarized here.",
        "[RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md) — compatibility stub",
        "O1D2 Deterministic Scheduler Policy",
        "O1E Scheduler Operational Controls",
        "Phase I-4F Forget Product Validation",
        "Phase I-5A Pin / Unpin Contract",
        "Phase I-7A/B Held Apply / Discard Contract",
        "Wave 5 Cross-Slice Convergence Audit",
        "Wave 4 Cross-Slice Convergence Audit",
        "E1 MVP Evaluation Evidence Consolidation",
    ),
    "docs/architecture/current_target_migration_guide.md": (
        "MVP sequencing and roadmap ordering live in [Project Execution Plan](project_execution_plan.md)",
        "O1D2 is current implemented as bounded policy wrapper.",
        "O1E is current implemented as bounded caller-invoked operational controls.",
        "O1F remains target/unimplemented.",
        "I-4E is current implemented as loopback Forget API/UI.",
        "I-4F is current implemented as validation-only Forget product completion.",
        "UI-B1A is current implemented read-only visibility.",
        "I-5A is current implemented contract/read-only preflight only.",
        "I-7A/B is current implemented contract/read-only preflight only.",
        "E1 evaluation consolidation is current docs/evidence only.",
        "Direct Home-origin trusted scene admission remains target work.",
    ),
    "docs/architecture/project_execution_plan.md": (
        "This document is the single plan and roadmap authority for RelayLM execution.",
        "MVP boundary",
        "MVP execution lanes",
        "### Wave 4 completed",
        "### Wave 5 completed",
        "### E1 evaluation consolidation completed",
        "### Post-Wave-5 next candidates",
        "O1D2 bounded scheduler policy/fairness/pacing",
        "O1E stale recovery/cancellation/shutdown complete",
        "I-4E loopback API and SOUL Lab Forget UI",
        "I-4F crash/race/security/fresh-conversation validation",
        "UI-B1A read-only lifecycle visibility",
        "I-5A Pin / Unpin contract/preflight",
        "I-7A/B Held Apply / Discard contract/preflight",
        "E1 evaluation consolidation                    complete",
        "direct Home-origin formation decision           Option A for current MVP",
        "MVP completion criteria",
        "Post-MVP roadmap",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "I1-GA through I1-GE are complete",
        "O1D1 accepts the five exact scheduler gates",
        "O1D2 is current implemented as a bounded policy wrapper",
        "O1E is current implemented as a bounded caller-invoked operational-control layer.",
        "O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented.",
        "I-4E is current implemented as loopback Forget API/UI.",
        "I-4F is current implemented as validation-only Forget product completion.",
        "UI-B1A is current implemented read-only visibility.",
        "I-5A is current implemented contract/read-only preflight only.",
        "I-7A/B is current implemented contract/read-only preflight only.",
        "E1 evaluation consolidation is current as an evidence/documentation boundary.",
        "bounded scheduler operational controls            complete as O1E",
    ),
    "docs/architecture/o1e_scheduler_operational_controls.md": (
        "# O1E Scheduler Operational Controls",
        "Status: implemented in this slice.",
        "optional one stale-claim recovery orchestration through B3",
        "Cancellation and shutdown boundary",
        "Stale recovery",
        "O1F remains responsible for full corruption, concurrency, saturation, restart, leakage, and operational validation.",
    ),
    "docs/architecture/e1_evaluation_consolidation.md": (
        "# E1 MVP Evaluation Evidence Consolidation",
        "## Direct Home-origin formation decision record",
        "Recommended for the current MVP boundary.",
        "E1-R1 trusted Home scene-admission path",
        "E1-R2 idempotent character-store bootstrap command",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression",
    ),
    "docs/architecture/phase_i4f_forget_validation.md": (
        "# Phase I-4F Forget Product Completion Validation",
        "## Validation matrix",
        "## Non-goals preserved",
        "## Validation commands",
    ),
    "docs/architecture/wave4_cross_slice_convergence_audit.md": (
        "# Wave 4 Cross-Slice Convergence Audit",
        "## Source PR inventory",
        "## Merge commit inventory",
        "## Frozen next inputs",
        "W4-INT is merged",
    ),
    "docs/architecture/wave5_cross_slice_convergence_audit.md": (
        "# Wave 5 Cross-Slice Convergence Audit",
        "## Source PR inventory",
        "## Merge commit inventory",
        "## Converged current boundary",
        "E1 evaluation consolidation",
        "O1E scheduler operational controls",
        "I-4F Forget product-completion validation",
        "O1E stale recovery/cancellation/shutdown",
        "I-4F crash/race/security/fresh-conversation validation",
        "## Frozen next inputs",
        "W5-INT is in progress until the convergence PR containing this audit is merged.",
    ),
}

STALE = tuple(
    line.strip()
    for line in """
    pending review and merge
    W3-INT complete only after this PR is merged
    W3-INT complete only after its PR is merged
    Wave 4 not open while W3-INT is unmerged
    Wave 4 not open while this PR is unmerged
    After W3-INT merge:
    planned after W3-INT
    Scheduler remaining production: O1D2 policy
    Phase I-4E loopback API and SOUL Lab Forget UI: unimplemented
    Current Wave 4 follow-up work:
    Wave 4 follow-up queue
    I-4E API/UI and I-4F validation
    O1D2 scheduling policy, O1E recovery/shutdown
    W4-INT in progress until the convergence PR merges
    W4-INT is complete only after that convergence PR merges
    W4-INT completes only after the convergence PR containing this audit is merged
    Phase I-4F full Forget validation: unimplemented
    Phase I-4 overall: in progress
    O1E stale recovery/cancellation/shutdown: unimplemented
    O1E/O1F remain target/unimplemented.
    Post-I-4F next candidates:
    Post-Wave-4 next candidates:
    """.splitlines()
    if line.strip()
)

FROZEN_ALLOWLIST = {
    "docs/architecture/wave2_cross_slice_convergence_audit.md": STALE,
    "docs/architecture/wave3_cross_slice_convergence_audit.md": STALE,
    "docs/architecture/wave4_cross_slice_convergence_audit.md": STALE,
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, anchors: tuple[str, ...]) -> None:
    body = read(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing anchors: {missing!r}"


def forbid(path: str, values: tuple[str, ...]) -> None:
    body = read(path)
    allowed = FROZEN_ALLOWLIST.get(path, ())
    stale = [anchor for anchor in values if anchor not in allowed and anchor in body]
    assert not stale, f"{path}: stale anchors: {stale!r}"


def main() -> None:
    for path, anchors in REQUIRED.items():
        require(path, anchors)
    for path in CURRENT_DOCS:
        forbid(path, STALE)
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main()
