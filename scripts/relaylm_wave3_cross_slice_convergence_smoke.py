#!/usr/bin/env python3
"""Validate frozen Wave 3 evidence and static implementation authority bounds."""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPORTS = {
    "I1-GE": {
        "path": "docs/evidence/implementation/i1ge_completion_report.md",
        "pr": "#411",
        "merge": "e2caa1bdb53468ca282e8f374ba8ceebf839c976",
        "head": "6cb461cb614d14965f5a49c1c4b517755f44f4a6",
        "handoff": "docs/evidence/implementation/i1ge-durable-finalization-crash-validation-handoff.md",
    },
    "I-4D": {
        "path": "docs/evidence/implementation/i4d_completion_report.md",
        "pr": "#414",
        "merge": "48e890f05f76196b73267559b079f4a05c441077",
        "head": "81c58516a4ba04c6e439ff17d633575bb193f843",
        "handoff": "docs/architecture/phase_i4d_primary_retrieval_exclusion.md",
    },
    "O1D1": {
        "path": "docs/evidence/implementation/o1d1_completion_report.md",
        "pr": "#412",
        "merge": "9b6349236f1a01f3cdccbe9e3c2c874ae1137475",
        "head": "7aa051abe6a9e49a2f67c193b7e742f9406ec54f",
        "handoff": "docs/architecture/o1d1_production_scheduler_round.md",
    },
}

O1D1_FIELDS = (
    "relaymem_local_scheduler_enabled",
    "relaymem_local_scheduler_dry_run_only",
    "relaymem_local_scheduler_apply_enabled",
    "relaymem_local_scheduler_replay_lane_enabled",
    "relaymem_local_scheduler_queue_lane_enabled",
)

ABSENT_SCHEDULER_FIELDS = (
    "relaymem_local_scheduler_interval_seconds",
    "relaymem_local_scheduler_poll_interval_seconds",
    "relaymem_local_scheduler_backoff_seconds",
    "relaymem_local_scheduler_jitter_seconds",
    "relaymem_local_scheduler_shutdown_timeout_seconds",
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *anchors: str) -> None:
    body = read(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing anchors {missing!r}"


def forbid(path: str, *anchors: str) -> None:
    body = read(path)
    stale = [anchor for anchor in anchors if anchor in body]
    assert not stale, f"{path}: forbidden anchors {stale!r}"


def relaylm_config_fields() -> tuple[str, ...]:
    tree = ast.parse(read("relaylm/config.py"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RelayLMConfig":
            names: list[str] = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    names.append(item.target.id)
            return tuple(names)
    raise AssertionError("RelayLMConfig not found")


def check_reports_and_handoffs() -> None:
    audit = read("docs/evidence/waves/wave3_cross_slice_convergence_audit.md")
    assert "relaylm_authority: wave3_cross_slice_convergence_record" in audit
    assert "W3-INT merged" in audit
    assert "Divergence found and corrected" in audit
    for slice_name, data in REPORTS.items():
        report = read(data["path"])
        assert "relaylm_doc_type: implementation_completion_report" in report, slice_name
        assert data["pr"] in report, slice_name
        assert data["handoff"] in audit, slice_name
        assert data["merge"] in audit, slice_name
        assert data["head"] in audit, slice_name
        handoff = read(data["handoff"])
        assert "relaylm_doc_type:" in handoff or slice_name == "I-4D", slice_name
        assert "unimplemented" in report or "Known limitations" in report, slice_name


def check_o1d1_static_boundary() -> None:
    fields = relaylm_config_fields()
    for field in O1D1_FIELDS:
        assert field in fields, field
        require("docs/reference/configuration.md", field)
        require("config.example.yaml", field)
    for field in ABSENT_SCHEDULER_FIELDS:
        assert field not in fields, field
    config = read("relaylm/config.py")
    for field in O1D1_FIELDS:
        assert re.search(rf"{field}: StrictBool", config), field

    round_code = read("relaylm/relaymem_slp_scheduler_round.py")
    replay_call = "replay_lane = run_relaymem_slp_scheduler_replay_lane_once"
    queue_call = "queue_lane = run_relaymem_slp_scheduler_queue_lane_once"
    assert round_code.index(replay_call) < round_code.index(queue_call)
    require(
        "relaylm/relaymem_slp_scheduler_round.py",
        replay_call,
        queue_call,
        'invocation_order.append("replay")',
        'invocation_order.append("queue")',
        "return result",
    )
    forbid(
        "relaylm/relaymem_slp_scheduler_round.py",
        "while True",
        "time.sleep",
        "asyncio.sleep",
        "poll_interval",
        "leader_election",
    )
    require(
        "docs/architecture/o1d1_production_scheduler_round.md",
        "O1C",
        "I1-GC delegation <= 1",
        "C2 delegation    <= 1",
        "total work units <= 2",
    )


def check_i4d_static_boundary() -> None:
    # The I-4D architecture document was canonicalized on `main` independently
    # of RT-1D-R5, so the pre-canonicalization phrases no longer exist. These
    # anchors are re-pointed at the exact current wording and preserve the same
    # static boundary intent: the exclusion compatibility boundary itself, the
    # runtime-private RelayCTX grounding handoff, the bounded lab event, the
    # one-authority rule, the read-only historical/operational survival, and
    # the R5 removal gate. The document itself is not modified.
    require(
        "docs/architecture/phase_i4d_primary_retrieval_exclusion.md",
        "Primary MEM Retrieval Exclusion Compatibility Boundary",
        "runtime-private RelayCTX grounding handoff",
        "relaylm.lab.memory_used.v0",
        "One-authority boundary",
        "Read-only historical and operational use",
        "R5 removal gate",
    )
    require(
        "relaylm/relaymem_primary_retrieval_eligibility.py",
        "eligible_current_active",
        "excluded_prior_revision",
        "excluded_hidden",
        "excluded_prepared",
        "excluded_recovery_required",
    )
    # RT-1D-R5 retired the ordinary Primary reader, so the recall facade is now
    # the read-only history/observation/admin re-export surface. The eligibility
    # index moved with the ordinary path it served; what must still converge here
    # is the preserved read-only store access those projections depend on.
    require(
        "relaylm/relaymem_primary_recall.py",
        "resolve_relaymem_character_store_root",
        "_load_control_state",
    )


def check_i1ge_static_boundary() -> None:
    require(
        "docs/evidence/implementation/i1ge-durable-finalization-crash-validation-handoff.md",
        "validation-only production evidence",
        "real child-process `os._exit` seams",
        "sealed durable-finalization evidence through exact C1-5/B2 correlation",
        "It does not mean B3 terminal success, C2 execution, worker execution, Primary MEM formation",
    )
    require(
        "docs/evidence/implementation/i1ge_completion_report.md",
        "No post-source report modification exists",
        "source-before-queue",
    )


def check_indexes_and_reference_map() -> None:
    require(
        "docs/reference/project-status-reference-map.md",
        "relaylm_authority: project_status_reference_map",
        "I1-G durable finalization and restart/recovery lifecycle",
        "Primary MEM Correct, Forget/Hide, Pin/Unpin, Held Apply/Discard",
        "Wave 3 through Wave 7 integration tracks",
    )
    require(
        "docs/evidence/implementation/README.md",
        "I1-GE completion report",
        "I-4D completion report",
        "O1D1 completion report",
    )
    require(
        "docs/evidence/waves/README.md",
        "Wave 3 cross-slice convergence audit",
    )
    require(
        "docs/architecture/project_execution_plan.md",
        "relaylm_doc_type: implementation_plan",
        "relaylm_authority: mvp_execution_plan_and_post_mvp_roadmap",
        "This document is the single plan and roadmap authority for RelayLM execution.",
        "It does not own current implementation status; read [Project Status](../PROJECT_STATUS.md) first.",
    )
    require(
        "docs/evidence/waves/wave3_cross_slice_convergence_audit.md",
        "I1-G overall complete",
        "Phase I-4 overall in progress",
        "O1 overall in progress",
        "W3-INT merged",
        "Wave 4 follow-up planning may use the frozen W3-INT authority map and inputs",
    )


def main() -> None:
    check_reports_and_handoffs()
    check_i1ge_static_boundary()
    check_i4d_static_boundary()
    check_o1d1_static_boundary()
    check_indexes_and_reference_map()
    print("Wave 3 cross-slice convergence smoke passed")
    Path("wave3-convergence.log").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
