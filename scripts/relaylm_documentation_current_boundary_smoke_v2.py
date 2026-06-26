#!/usr/bin/env python3
"""Validate current integrated RelayLM documentation boundaries."""
from __future__ import annotations

import ast
import re
from pathlib import Path

from relaylm_i1g_pre_enqueue_fault_model_smoke import main as run_i1g_fault_model
from relaylm_o1a_two_lane_scheduler_contract_smoke import main as run_o1a_contract

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *anchors: str) -> None:
    body = read(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing anchors: {missing!r}"


def forbid(path: str, *anchors: str) -> None:
    body = read(path)
    stale = [anchor for anchor in anchors if anchor in body]
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

    target_only = (
        "relaymem_local_scheduler_enabled",
        "relaymem_local_scheduler_dry_run_only",
        "relaymem_local_scheduler_apply_enabled",
        "relaymem_local_scheduler_replay_lane_enabled",
        "relaymem_local_scheduler_queue_lane_enabled",
    )
    for path in ("relaylm/config.py", "docs/config_schema.md", "config.example.yaml"):
        forbid(path, *target_only)

    required = {
        "docs/PROJECT_STATUS.md": (
            "I1-GD retention / orphan reconciliation / isolation lifecycle / cleanup: complete",
            "I1-GE full production crash validation: unimplemented",
            "Scheduler replay lane: O1B one bounded sealed-record discovery/reread/I1-GC adapter complete",
            "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete",
            "Scheduler remaining production: O1D through O1F unimplemented",
            "Phase I-4C1 hidden-successor commit: complete",
        ),
        "docs/README.md": (
            "I1-GA through I1-GD are complete",
            "o1c_eligible_b2_queue_lane.md",
            "Phase I-4C1 is complete",
        ),
        "docs/architecture/README.md": (
            "i1gd_durable_finalization_retention_cleanup.md",
            "o1b_sealed_i1g_replay_lane.md",
            "o1c_eligible_b2_queue_lane.md",
            "O1C queue discovery is complete",
        ),
        "docs/architecture/pipeline_implementation_plan.md": (
            "I1-GD  bounded retention, isolation, orphan cleanup",
            "O1B sealed replay-lane adapter: complete",
            "O1C eligible queue-lane adapter: complete",
            "O1D through O1F production scheduling: unimplemented",
        ),
        "docs/architecture/post_i3_evaluation_work_roadmap.md": (
            "I1-GD bounded retention and isolation cleanup — complete",
            "O1B/O1C bounded production lane adapters",
            "O1D through O1F remain unimplemented",
        ),
        "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md": (
            "### I1-GD — complete",
            "### O1B — complete",
            "### O1C — complete",
            "### O1D through O1F — unimplemented",
            "relaymem.slp_durable_finalization_isolation.v0",
        ),
        "docs/architecture/i1gd_durable_finalization_retention_cleanup.md": (
            "Status: **implemented production boundary**",
            "shared I1-GC nonblocking per-record fence",
            "delete isolation marker last",
            "sealed_pending",
        ),
        "docs/architecture/relaymem_mvp_implementation_plan.md": (
            "I1-GD bounded retention and isolation cleanup: complete",
            "O1C is complete for one bounded",
            "The next RelayMEM governance implementation slice is I-4C2",
        ),
        "docs/architecture/relaymem_slp_current_target.md": (
            "I1-GD one bounded maintenance pass",
            "O1C delegation",
            "Forget is not product-complete until I-4C2 through I-4F",
        ),
        "docs/architecture/o0_local_one_job_runner.md": (
            "Shared O0/O1C production helper boundary",
            "O1C  one B2/B3 discovery and C2 delegation — complete",
        ),
        "docs/architecture/o1a_two_lane_scheduler_contract.md": (
            "O1B replay adapter and O1C queue adapter complete",
            "O1D  deterministic within-lane ordering",
            "Same-round replay-to-queue rule",
        ),
        "docs/architecture/o1b_sealed_i1g_replay_lane.md": (
            "Production replay-lane adapter complete",
            "existing I1-GC delegation at most once",
        ),
        "docs/architecture/o1c_eligible_b2_queue_lane.md": (
            "O1C is complete as one bounded production queue-lane adapter",
            "Same-round replay independence",
        ),
        "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md": (
            "I-4C1 hidden-successor commit is implemented",
            "I-4C2 prepared resume/exact replay/tombstone finalization",
        ),
        "docs/architecture/phase_i4b_primary_current_state_shared_fence.md": (
            "Complete for the I-4B read-only boundary.",
            "I-4C2: prepared resume",
        ),
        "docs/architecture/phase_i4c1_primary_forget_hidden_successor.md": (
            "Status: complete for the bounded I-4C1 commit boundary.",
            "I-4C2 prepared resume",
        ),
        "docs/architecture/soul_lab_ui_b0_real_home_conversation.md": (
            "same-origin POST /v1/chat/completions",
            "UI-B0 does not claim that the complete E1 flow is automated",
        ),
    }
    for path, anchors in required.items():
        require(path, *anchors)

    stale = (
        "### I1-GD — unimplemented",
        "I1-GD retention / orphan reconciliation / cleanup: unimplemented",
        "I1-GC through I1-GE remain unimplemented",
        "Window A recovery side — I1-GC unimplemented",
        "This section supersedes earlier",
        "supersedes earlier roadmap entries",
    )
    for path in required:
        forbid(path, *stale)

    run_i1g_fault_model()
    run_o1a_contract()
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main()
