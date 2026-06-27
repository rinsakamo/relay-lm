#!/usr/bin/env python3
"""Validate Wave 3 cross-slice convergence documentation and static authority bounds."""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPORTS = {
    "I1-GE": {
        "path": "docs/mvp/wave3/i1ge_completion_report.md",
        "pr": "#411",
        "merge": "e2caa1bdb53468ca282e8f374ba8ceebf839c976",
        "head": "6cb461cb614d14965f5a49c1c4b517755f44f4a6",
        "handoff": "docs/architecture/i1ge_durable_finalization_crash_validation.md",
    },
    "I-4D": {
        "path": "docs/mvp/wave3/i4d_completion_report.md",
        "pr": "#414",
        "merge": "48e890f05f76196b73267559b079f4a05c441077",
        "head": "81c58516a4ba04c6e439ff17d633575bb193f843",
        "handoff": "docs/architecture/phase_i4d_primary_retrieval_exclusion.md",
    },
    "O1D1": {
        "path": "docs/mvp/wave3/o1d1_completion_report.md",
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
    audit = read("docs/architecture/wave3_cross_slice_convergence_audit.md")
    assert "relaylm_authority: wave3_cross_slice_convergence_record" in audit
    assert "Wave 4 is not open" in audit
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
        require("docs/config_schema.md", field)
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
        "invocation_order.append(\"replay\")",
        "invocation_order.append(\"queue\")",
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
        "The coordinator passes no replay result, locator, job/dispatch identity, candidate object, or priority hint into O1C.",
        "I1-GC delegation <= 1",
        "C2 delegation    <= 1",
        "total work units <= 2",
    )


def check_i4d_static_boundary() -> None:
    require(
        "docs/architecture/phase_i4d_primary_retrieval_exclusion.md",
        "before RelayCTX/backend-bound injection",
        "A candidate survives only when M2 already selected it",
        "A hidden successor remains lifecycle authority; retrieval never falls back to a prior active revision.",
        "The durable `relaylm.lab.memory_used.v0` receipt and existing v0 endpoint remain unchanged.",
        "I-4E remains the loopback API and SOUL Lab mutation UI. I-4F remains the full production validation slice.",
    )
    require(
        "relaylm/relaymem_primary_retrieval_eligibility.py",
        "eligible_current_active",
        "excluded_prior_revision",
        "excluded_hidden",
        "excluded_prepared",
        "excluded_recovery_required",
    )
    require(
        "relaylm/relaymem_primary_recall.py",
        "load_primary_retrieval_eligibility_index",
        "apply_relaymem_primary_recall_scope",
    )


def check_i1ge_static_boundary() -> None:
    require(
        "docs/architecture/i1ge_durable_finalization_crash_validation.md",
        "validation-only production evidence",
        "real child-process `os._exit` seams",
        "sealed durable-finalization evidence through exact C1-5/B2 correlation",
        "It does not mean B3 terminal success, C2 execution, worker execution, Primary MEM formation",
    )
    require(
        "docs/mvp/wave3/i1ge_completion_report.md",
        "No production module, runtime schema, configuration schema, or repository-wide shared status/plan/index document is modified.",
        "source-before-queue",
    )


def check_shared_docs() -> None:
    require(
        "docs/PROJECT_STATUS.md",
        "I1-GE full production crash validation: complete",
        "I1-G overall: complete",
        "Phase I-4D ordinary retrieval lifecycle exclusion: complete",
        "Phase I-4 overall: in progress",
        "O1D1 accepted gates/one-round coordinator: complete",
        "O1 overall: in progress",
        "Wave 3 implementation tracks complete",
        "Wave 4 not open while W3-INT is unmerged",
    )
    require(
        "docs/mvp/README.md",
        "Wave 3 merged completion reports",
        "I1-GE completion report",
        "I-4D completion report",
        "O1D1 completion report",
    )
    require(
        "docs/README.md",
        "I1-GA through I1-GE are complete",
        "O1D1 is complete for accepted scheduler gates plus one bounded production round",
        "I-4D ordinary M2/RelayCTX lifecycle and prior-revision exclusion plus read-only historical lifecycle projection is complete",
    )
    require(
        "docs/architecture/README.md",
        "I1-GE Durable-finalization Crash Validation",
        "Wave 3 Cross-Slice Convergence Audit",
        "W3-INT complete only after its PR is merged",
    )
    require(
        "docs/architecture/pipeline_implementation_plan.md",
        "I1-G overall: complete",
        "Phase I-4 overall: in progress",
        "O1D1 accepted gates and one production round: complete",
        "Wave 4 not open while W3-INT is unmerged",
    )
    require(
        "docs/architecture/post_i3_evaluation_work_roadmap.md",
        "I1-GA through I1-GE",
        "I-4E, I-4F, O1D2, O1E, and O1F remain incomplete",
        "Wave 4 not open while W3-INT is unmerged",
    )
    require(
        "docs/architecture/wave3_cross_slice_convergence_audit.md",
        "I1-G overall complete",
        "Phase I-4 overall in progress",
        "O1 overall in progress",
        "Wave 4 not open while this PR is unmerged",
    )


def main() -> None:
    check_reports_and_handoffs()
    check_i1ge_static_boundary()
    check_i4d_static_boundary()
    check_o1d1_static_boundary()
    check_shared_docs()
    print("Wave 3 cross-slice convergence smoke passed")
    Path("wave3-convergence.log").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
