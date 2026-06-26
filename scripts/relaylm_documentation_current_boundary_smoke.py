#!/usr/bin/env python3
"""Validate current post-Wave-3 documentation boundaries."""
from __future__ import annotations

import ast
import re
from pathlib import Path

from relaylm_i1g_pre_enqueue_fault_model_smoke import main as run_i1g_fault_model
from relaylm_o1a_two_lane_scheduler_contract_smoke import main as run_o1a_contract

ROOT = Path(__file__).resolve().parents[1]

O1D1_ACCEPTED_FIELDS = (
    "relaymem_local_scheduler_enabled",
    "relaymem_local_scheduler_dry_run_only",
    "relaymem_local_scheduler_apply_enabled",
    "relaymem_local_scheduler_replay_lane_enabled",
    "relaymem_local_scheduler_queue_lane_enabled",
)

CURRENT_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/pipeline_implementation_plan.md",
    "docs/architecture/post_i3_evaluation_work_roadmap.md",
    "docs/architecture/relaymem_mvp_implementation_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/wave3_cross_slice_convergence_audit.md",
    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",
    "docs/architecture/i1gd_durable_finalization_retention_cleanup.md",
    "docs/architecture/i1ge_durable_finalization_crash_validation.md",
    "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md",
    "docs/architecture/phase_i4b_primary_current_state_shared_fence.md",
    "docs/architecture/phase_i4c1_primary_forget_hidden_successor.md",
    "docs/architecture/phase_i4c2_primary_forget_recovery_finalization.md",
    "docs/architecture/phase_i4d_primary_retrieval_exclusion.md",
    "docs/architecture/o0_local_one_job_runner.md",
    "docs/architecture/o1a_two_lane_scheduler_contract.md",
    "docs/architecture/o1b_sealed_i1g_replay_lane.md",
    "docs/architecture/o1c_eligible_b2_queue_lane.md",
    "docs/architecture/o1d1_production_scheduler_round.md",
)

REQUIRED = {
    "docs/PROJECT_STATUS.md": """
I1-GE full production crash validation: complete
I1-G overall: complete
Phase I-4D ordinary retrieval lifecycle exclusion: complete
Phase I-4E loopback API and SOUL Lab Forget UI: unimplemented
Phase I-4F full Forget validation: unimplemented
Phase I-4 overall: in progress
O1D1 accepted gates/one-round coordinator: complete
O1 overall: in progress
O2 supervised worker service: planned/unimplemented
O3 always-on local operation: planned/unimplemented
Wave 3 implementation tracks complete
W3-INT complete only after this PR is merged
Wave 4 not open while W3-INT is unmerged
""",
    "docs/README.md": """
I1-GA through I1-GE are complete
O1D1 is complete for accepted scheduler gates plus one bounded production round
I-4D ordinary M2/RelayCTX lifecycle and prior-revision exclusion plus read-only historical lifecycle projection is complete
W3-INT complete only after its PR is merged
""",
    "docs/mvp/README.md": """
Wave 3 merged completion reports
I1-GE completion report
I-4D completion report
O1D1 completion report
Wave 3 Cross-Slice Convergence Audit
""",
    "docs/architecture/README.md": """
I1-GE Durable-finalization Crash Validation
O1D1 Accepted Scheduler Gates and One Production Round
Phase I-4D Primary Retrieval Exclusion
Wave 3 Cross-Slice Convergence Audit
W3-INT complete only after its PR is merged
""",
    "docs/architecture/pipeline_implementation_plan.md": """
I1-G overall: complete
Phase I-4D retrieval exclusion: complete
Phase I-4 overall: in progress
O1D1 accepted gates and one production round: complete
O1 overall: in progress
Wave 4 not open while W3-INT is unmerged
""",
    "docs/architecture/post_i3_evaluation_work_roadmap.md": """
I1-GA through I1-GE
I-4E, I-4F, O1D2, O1E, and O1F remain incomplete
Wave 4 not open while W3-INT is unmerged
""",
    "docs/architecture/relaymem_mvp_implementation_plan.md": """
I-4D retrieval exclusion/history projection: complete
I-4E API/UI and I-4F validation: unimplemented
O1D1 accepted gates and one production round: complete
O1 overall remains in progress
""",
    "docs/architecture/relaymem_slp_current_target.md": """
I1-GA through I1-GE are complete
O1D1 accepts the five exact scheduler gates
I-4D consumes the complete shared current-state authority before snippet construction
Forget is not product-complete until I-4E
""",
    "docs/architecture/wave3_cross_slice_convergence_audit.md": """
Wave 3 source PR inventory
I1-G overall complete
Phase I-4 overall in progress
O1 overall in progress
Wave 4 not open while this PR is unmerged
O1D2
I-4E
UI-B1A
""",
    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md": """
I1-GA through I1-GE are complete
I1-G overall is complete only for sealed durable-finalization evidence
I1-GE is complete as validation-only real process-exit/fresh-restart proof
""",
    "docs/architecture/i1ge_durable_finalization_crash_validation.md": """
I1-GE is complete as validation-only production evidence
real child-process `os._exit` seams
It does not mean B3 terminal success, C2 execution, worker execution, Primary MEM formation
""",
    "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md": """
I-4B, I-4C1, I-4C2, and I-4D are implemented
I-4E still owns loopback mutation API and SOUL Lab Forget UI
I-4F still owns crash/race/security/fresh-conversation validation
""",
    "docs/architecture/phase_i4d_primary_retrieval_exclusion.md": """
A candidate survives only when M2 already selected it
A hidden successor remains lifecycle authority; retrieval never falls back to a prior active revision.
I-4E remains the loopback API and SOUL Lab mutation UI. I-4F remains the full production validation slice.
""",
    "docs/architecture/o1a_two_lane_scheduler_contract.md": """
O1B replay adapter, O1C queue adapter, and O1D1 one production round are complete.
O1D1 is now the production wiring for exactly one such round.
O1D2 and O1E own the later policy and controls required to start, delay, cancel, or stop subsequent rounds.
""",
    "docs/architecture/o1d1_production_scheduler_round.md": """
O1D1 implements one accepted, server-configured, single-threaded production scheduler round.
relaymem_local_scheduler_enabled: false
relaymem_local_scheduler_dry_run_only: true
relaymem_local_scheduler_apply_enabled: false
relaymem_local_scheduler_replay_lane_enabled: true
relaymem_local_scheduler_queue_lane_enabled: true
The coordinator passes no replay result, locator, job/dispatch identity, candidate object, or priority hint into O1C.
""",
}

STALE = tuple(
    line.strip()
    for line in """
I1-GE full production crash validation: unimplemented
I1-GE validation-only full production crash proof: unimplemented
I1-GE remains unimplemented
I1-G overall: in progress
Phase I-4D through I-4F exclusion, UI, and validation: unimplemented
Phase I-4D retrieval exclusion: unimplemented
I-4D ordinary M2/RelayCTX lifecycle exclusion: unimplemented
No production hidden-state filtering exists yet because I-4D integration is not implemented
I-4D M2/RelayCTX lifecycle exclusion, loopback mutation routes, and SOUL Lab Forget UI remain unimplemented
O1D1 accepted gates and one production round: unimplemented
O1D1 through O1F: unimplemented
O1D1 remains unimplemented
O1A target field names remain design-only until O1D1 accepts them
O1D1 is the phase that will accept those exact scheduler gates
accepted config.py config-schema or config-example changes before O1D1
I1-GC through I1-GE remain planned
I1-GC through I1-GE remain unimplemented
O1B through O1F remain unimplemented
O1C through O1F, O2, and O3 remain unimplemented
### Wave 3 — current independent implementation tracks
""".splitlines()
    if line.strip()
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def anchors(block: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in block.strip().splitlines() if line.strip())


def require(path: str, block: str) -> None:
    body = read(path)
    missing = [anchor for anchor in anchors(block) if anchor not in body]
    assert not missing, f"{path}: missing anchors: {missing!r}"


def forbid(path: str, values: tuple[str, ...]) -> None:
    body = read(path)
    stale = [anchor for anchor in values if anchor in body]
    assert not stale, f"{path}: stale anchors: {stale!r}"


def config_fields() -> tuple[str, ...]:
    tree = ast.parse(read("relaylm/config.py"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RelayLMConfig":
            return tuple(
                item.target.id
                for item in node.body
                if isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
            )
    raise AssertionError("RelayLMConfig not found")


def validate_config_coverage(path: str) -> None:
    body = read(path)
    missing = [
        field
        for field in config_fields()
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])", body)
        is None
    ]
    assert not missing, f"{path}: missing config fields: {missing!r}"


def main() -> None:
    validate_config_coverage("docs/config_schema.md")
    validate_config_coverage("config.example.yaml")
    for path in ("relaylm/config.py", "docs/config_schema.md", "config.example.yaml"):
        require(path, "\n".join(O1D1_ACCEPTED_FIELDS))
    for path, block in REQUIRED.items():
        require(path, block)
    for path in CURRENT_DOCS:
        forbid(path, STALE)
    run_i1g_fault_model()
    run_o1a_contract()
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main()
