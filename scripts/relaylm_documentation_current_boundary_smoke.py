#!/usr/bin/env python3
"""Validate current documentation boundary anchors after Wave 6 convergence."""
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
    "docs/architecture/o1a_two_lane_scheduler_contract.md",
    "docs/architecture/o1b_sealed_i1g_replay_lane.md",
    "docs/architecture/o1d1_production_scheduler_round.md",
    "docs/architecture/o1e_scheduler_operational_controls.md",
    "docs/architecture/o1f_operational_validation.md",
    "docs/architecture/e1_evaluation_consolidation.md",
    "docs/architecture/e1r1_trusted_home_scene_admission.md",
    "docs/architecture/e1r2_character_store_bootstrap.md",
    "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md",
    "docs/architecture/phase_i4b_primary_current_state_shared_fence.md",
    "docs/architecture/phase_i4f_forget_validation.md",
    "docs/architecture/phase_i5_pin_unpin_contract.md",
    "docs/architecture/phase_i5b_pin_unpin_apply.md",
    "docs/architecture/phase_i7ab_held_apply_discard_contract.md",
    "docs/architecture/phase_i7c_held_apply_discard_runtime.md",
    "docs/architecture/soul_lab_ui_mvp.md",
    "docs/relaysoul/relaysoul_gate_design_consistency_review.md",
    "docs/architecture/wave2_cross_slice_convergence_audit.md",
    "docs/architecture/wave3_cross_slice_convergence_audit.md",
    "docs/architecture/wave4_cross_slice_convergence_audit.md",
    "docs/architecture/wave5_cross_slice_convergence_audit.md",
    "docs/architecture/wave6_cross_slice_convergence_audit.md",
)

REQUIRED = {
    "docs/PROJECT_STATUS.md": (
        "This page owns current implementation status and active caveats.",
        "[Project Execution Plan](architecture/project_execution_plan.md) owns MVP boundary, dependency sequencing, and roadmap ordering.",
        "I1-GE full production crash validation: complete",
        "I1-G overall: complete",
        "O1F operational validation: complete",
        "O1 overall: complete through validation-only caller-invoked local scheduler boundary",
        "O2 supervised worker service: planned/unimplemented",
        "O3 always-on local operation: planned/unimplemented",
        "Phase I-4 overall: complete",
        "I-5B Pin / Unpin apply/API/UI/ranking behavior: complete",
        "I-7C Held Apply/Discard runtime/API/UI/durable governance evidence: complete",
        "E1-R1 trusted Home scene admission: complete",
        "E1-R2 character-store bootstrap command: complete",
        "Wave 6 implementation tracks complete",
        "W6-INT merged",
        "Post-Wave-6 next candidates:",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression",
    ),
    "docs/README.md": (
        "[Current project status](PROJECT_STATUS.md) — the single current implementation status authority.",
        "O1F operational validation",
        "Phase I-5B Pin / Unpin apply and ranking behavior",
        "Phase I-7C Held Apply / Discard runtime governance",
        "E1-R1 trusted Home scene admission",
        "E1-R2 character-store bootstrap command",
        "Wave 6 Cross-Slice Convergence Audit",
        "I-5B completion report",
        "I-7C completion report",
        "E1-R1 completion report",
        "E1-R2 completion report",
    ),
    "docs/mvp/README.md": (
        "Wave 6 merged completion reports",
        "O1F completion report",
        "I-5B completion report",
        "I-7C completion report",
        "E1-R1 completion report",
        "E1-R2 completion report",
        "W6-INT is merged",
        "Wave 5 merged completion reports",
    ),
    "docs/architecture/README.md": (
        "[Project Execution Plan](project_execution_plan.md)",
        "The current Product and RelayMEM status is intentionally not summarized here.",
        "O1F Operational Validation",
        "Phase I-5B Pin / Unpin Apply",
        "Phase I-7C Held Apply / Discard Runtime",
        "E1-R1 Trusted Home Scene Admission",
        "E1-R2 Character Store Bootstrap",
        "Wave 6 Cross-Slice Convergence Audit",
    ),
    "docs/DOCUMENTATION_MODEL.md": (
        "sweep directly affected feature-family master/contract documents",
        "The feature-family sweep is mandatory.",
        "must not leave a non-frozen master or contract document saying that an already completed subphase",
    ),
    "docs/architecture/current_target_migration_guide.md": (
        "## Current Wave 6 compatibility interpretation",
        "O1F is current implemented as validation-only operational hardening.",
        "I-5B is current implemented as Pin / Unpin apply/API/UI/ranking behavior.",
        "I-7C is current implemented as Held Apply / Discard runtime/API/UI/durable governance evidence.",
        "E1-R1 is current implemented as route-owned trusted Home scene admission.",
        "E1-R2 is current implemented as dry-run-first character-store bootstrap.",
        "O2/O3 remain target/unimplemented.",
    ),
    "docs/architecture/project_execution_plan.md": (
        "This document is the single plan and roadmap authority for RelayLM execution.",
        "MVP boundary",
        "MVP execution lanes",
        "### Wave 6 completed",
        "I-5B Pin / Unpin apply/API/UI/ranking work",
        "I-7C Held Apply/Discard runtime/API/UI/durable evidence",
        "E1-R1 trusted Home scene-admission path",
        "E1-R2 idempotent character-store bootstrap command",
        "### Post-Wave-6 next candidates",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression",
        "O2 supervised worker service, only if required",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "I1-GA through I1-GE are complete",
        "O1F is current implemented as validation-only hardening",
        "O2 supervision and O3 always-on operation remain unimplemented.",
        "I-5B is current implemented as Pin / Unpin apply/API/UI/ranking behavior.",
        "I-7C is current implemented as Held Apply / Discard runtime/API/UI/durable governance evidence.",
        "E1-R1 route-owned trusted Home scene admission is current implemented.",
        "E1-R2 dry-run-first character-store bootstrap is current implemented.",
    ),
    "docs/architecture/e1_evaluation_consolidation.md": (
        "# E1 MVP Evaluation Evidence Consolidation",
        "## Current E1 proof boundary",
        "E1-R1 route-owned trusted Home admission",
        "E1-R2 character-store bootstrap is implemented",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression",
    ),
    "docs/architecture/phase_i5_pin_unpin_contract.md": (
        "I-5A defines the Pin / Unpin governance contract and read-only preflight boundary.",
        "I-5B is implemented as the apply/API/UI/ranking continuation.",
        "Phase I-5B Pin / Unpin apply and ranking behavior",
    ),
    "docs/architecture/phase_i7ab_held_apply_discard_contract.md": (
        "I-7A/B defines the held outcome governance contract and read-only preflight boundary.",
        "I-7C is implemented as the runtime/API/UI/durable-evidence continuation.",
        "Phase I-7C Held Apply / Discard Runtime",
    ),
    "docs/architecture/phase_i7c_held_apply_discard_runtime.md": (
        "relaylm_status: current",
        "I-7C connects the I-7A/B Held Apply / Discard contract to a bounded runtime decision path",
    ),
    "docs/architecture/soul_lab_ui_mvp.md": (
        "Pin/Unpin runtime API/UI/ranking behavior: complete as I-5B",
        "Held Apply/Discard runtime API/UI/durable evidence: complete as I-7C",
        "E1-R1 route-owned trusted Home scene admission: complete outside browser authority",
    ),
    "docs/architecture/wave6_cross_slice_convergence_audit.md": (
        "# Wave 6 Cross-Slice Convergence Audit",
        "relaylm_status: historical_after_merge",
        "## Source PR inventory",
        "## Merge commit inventory",
        "I-5B Pin / Unpin apply/API/UI/ranking behavior",
        "I-7C Held Apply/Discard runtime/API/UI/durable evidence",
        "E1-R1 trusted Home scene-admission path",
        "E1-R2 idempotent character-store bootstrap command",
        "W6-INT is merged.",
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
    O1F operational validation: unimplemented
    O1F validation, O2, and O3
    Post-I-4F next candidates:
    Post-Wave-4 next candidates:
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
    """.splitlines()
    if line.strip()
)

FROZEN_ALLOWLIST = {
    "docs/architecture/wave2_cross_slice_convergence_audit.md": STALE,
    "docs/architecture/wave3_cross_slice_convergence_audit.md": STALE,
    "docs/architecture/wave4_cross_slice_convergence_audit.md": STALE,
    "docs/architecture/wave5_cross_slice_convergence_audit.md": STALE,
}

IMPLEMENTED_FEATURES = (
    "I-4D",
    "I-4E",
    "I-4F",
    "O1D2",
    "O1E",
    "O1F",
    "UI-B1A",
    "I-5B",
    "I-7C",
    "E1-R1",
    "E1-R2",
)

STALE_WORDS = (
    "unimplemented",
    "remain unimplemented",
    "remains unimplemented",
    "future work",
    "pending",
    "candidate",
)

ALLOWED_STALE_LINE_SUBSTRINGS = (
    "must not leave",
    "O2",
    "O3",
    "E1-R3",
    "E1-R4",
    "Merge/Supersession",
    "Secondary MEM",
    "RelaySOUL",
    "TTS",
    "ASR",
)


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


def forbid_completed_feature_stale_lines(path: str) -> None:
    if path in FROZEN_ALLOWLIST:
        return
    failures: list[str] = []
    for line_number, line in enumerate(read(path).splitlines(), start=1):
        stripped = line.strip()
        lowered = stripped.lower()
        if any(allowed in stripped for allowed in ALLOWED_STALE_LINE_SUBSTRINGS):
            continue
        for feature in IMPLEMENTED_FEATURES:
            if feature in stripped and any(word in lowered for word in STALE_WORDS):
                failures.append(f"L{line_number}: {stripped}")
    assert not failures, f"{path}: completed feature described as stale: {failures!r}"


def main() -> None:
    for path, anchors in REQUIRED.items():
        require(path, anchors)
    for path in CURRENT_DOCS:
        forbid(path, STALE)
        forbid_completed_feature_stale_lines(path)
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main()
