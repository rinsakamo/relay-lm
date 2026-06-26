#!/usr/bin/env python3
"""Validate current Phase 6, I1-I4C1, UI-B0, I1-G, O1A/O1C, and roadmap docs."""
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


O1A_TARGET_ONLY_FIELDS = (
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
    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",
    "docs/architecture/relaymem_mvp_implementation_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/o0_local_one_job_runner.md",
    "docs/architecture/o1a_two_lane_scheduler_contract.md",
    "docs/architecture/o1c_eligible_b2_queue_lane.md",
)

REQUIRED: dict[str, tuple[str, ...]] = {
    "docs/PROJECT_STATUS.md": (
        "Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete",
        "B0-B3 durable enqueue and fenced lifecycle",
        "B3 lifecycle: complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "I1 next-turn Primary MEM recall: complete",
        "character and namespace isolation: complete",
        "I2 real SOUL Lab observation: complete",
        "I3 auditable Primary MEM Correct: complete",
        "Phase I-4C1 hidden-successor commit: complete",
        "I1-GC one-record restart replay / exact C1-5+B2 convergence / completion marker: complete",
        "I1-GD retention / orphan reconciliation / cleanup: unimplemented",
        "I1-GE full production crash validation: unimplemented",
        "Visible-release restart evidence publication is implemented",
        "Restart-time one-record replay is implemented",
        "Direct Home-origin formation: not currently proven",
        "O1A adds no accepted configuration fields",
        "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete",
        "Scheduler remaining production: O1B and O1D through O1F unimplemented",
    ),
    "docs/architecture/pipeline_implementation_plan.md": (
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter is complete",
        "### I1-E / Phase I-2: real SOUL Lab observation — complete",
        "Observation evidence is read-only",
        "### I1-F / Phase I-3: auditable Primary MEM Correct — complete",
        "### I1-F2 / Phase I-4A: Primary MEM Forget / Hide contract — defined target",
        "Phase I-4C1 hidden-successor commit: complete",
        "exact read-only preflight/history/token",
        "I1-GC  one-record restart replay, exact convergence, completion    complete",
        "### O1A: two-lane bounded scheduler contract — complete",
        "O1A completion alone is not O1 completion.",
        "### Wave 1 — completed commit and replay authorities",
        "### Wave 2 — current parallel implementation candidates",
        "I-5 Pin / Unpin",
        "I-7 Held Apply / Discard",
        "I-6 Merge / Supersession",
        "These fields are not added to `relaylm/config.py`",
        "## O1C current reconciliation",
    ),
    "docs/architecture/post_i3_evaluation_work_roadmap.md": (
        "Phase I-4B: Current-state resolver and shared mutation fence — complete",
        "Phase I-4C1: Hidden-successor commit — complete",
        "I1-GC caller-selected one-record replay",
        "Phase I-5: Pin / Unpin",
        "Phase I-7: Held Apply / Discard",
        "Phase I-6: Merge / Supersession",
        "Phase I-8: Secondary MEM consolidation",
        "Phase I-9: RelaySOUL proposal / intervention / rollback",
        "### Wave 1 — complete",
        "### Wave 2 — current",
        "E1 does not prove direct Home-origin formation",
        "O1A completion alone does not satisfy the O1 checkpoint.",
        "## O1C current reconciliation",
    ),
    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md": (
        "Window A publication side — implemented by I1-GB",
        "Window A recovery side — implemented by I1-GC",
        "I1-GC is complete",
        "source-before-queue invariant is absolute",
        "## O1B caller boundary",
        "queue lane independently discovers the queue root",
        "### I1-GD — unimplemented",
        "### I1-GE — unimplemented",
    ),
    "docs/architecture/relaymem_mvp_implementation_plan.md": (
        "M3i-d real read-only Lab observation: complete as Phase I-2",
        "observation receipts",
        "M3i-f canonical current-state resolver/shared fence: complete as Phase I-4B",
        "M3i-g hidden-successor commit ownership: complete as Phase I-4C1",
        "I1-GC one-record replay and completion convergence is complete",
        "The next RelayMEM governance implementation slice is I-4C2",
        "No production hidden-state filtering exists yet because I-4D integration is not implemented",
        "## O1C current reconciliation",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "Phase 6-B2 performs atomic durable enqueue",
        "Phase 6-B3 performs default-off, dry-run-first",
        "C2 one-job claim/rehydrate/execute adapter",
        "durably enqueued jobs",
        "I2 real SOUL Lab observation: complete",
        "Observation receipts cannot authorize repair or retrieval",
        "I1-GC caller-selected one-record replay",
        "Phase I-4C1 hidden-successor commit — complete",
        "Forget is not product-complete until I-4C2 through I-4F",
        "## O1C current reconciliation",
    ),
    "docs/README.md": (
        "phase_i2_real_soul_lab_observation.md",
        "phase_i3_auditable_primary_mem_correct.md",
        "I1-GA, I1-GB, and I1-GC are complete",
        "Phase I-4C1 is complete",
        "o1c_eligible_b2_queue_lane.md",
        "O1C is complete for one bounded B2/B3 inventory",
    ),
    "docs/architecture/README.md": (
        "phase_i2_real_soul_lab_observation.md",
        "phase_i3_auditable_primary_mem_correct.md",
        "I1-GC provides the caller-selected one-record convergence authority",
        "Phase I-4C1 Primary Forget Hidden-Successor Commit",
        "O1C Eligible B2/B3 Queue Lane",
    ),
    "docs/architecture/o1a_two_lane_scheduler_contract.md": (
        "O1C queue adapter complete; production scheduler loop unimplemented.",
        "replay-lane opportunity completes or returns",
        "I1-GC delegation per round       <= 1",
        "C2 delegation per round          <= 1",
        "Same-round replay-to-queue rule",
        "Lane-local failure isolation",
        "Pure disposition contract",
        "target-only configuration",
        "O1B-O1F handoff",
        "relaylm.local_scheduler_round_result.v0",
        "relaylm.local_scheduler_round_projection.v0",
        "O1A performs no filesystem mutation or production scan",
        "O1C is complete as one bounded production queue-lane adapter",
    ),
    "docs/architecture/o1c_eligible_b2_queue_lane.md": (
        "O1C is complete as one bounded production queue-lane adapter",
        "Shared O0-compatible helper",
        "future_retry_only",
        "Same-round replay independence",
        "O1D ordering, fairness, retry-delay policy, backoff, or jitter",
    ),
    "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md": (
        "relaylm_status: target",
        "I-4C1 hidden-successor commit is implemented",
        "Decision: Candidate A",
        "Forget tombstone",
        "relaylm.mem.primary_current_state.v0",
        "I-4C2 prepared resume/exact replay/tombstone finalization",
        "restore",
        "unhide",
        "physical deletion",
        "I1-G pre-enqueue durability",
    ),
    "docs/architecture/phase_i4b_primary_current_state_shared_fence.md": (
        "Complete for the I-4B read-only boundary.",
        "canonical Primary current-state resolver",
        "shared Correct/Forget mutation fence",
        "five-minute token validation",
        "bounded zero-item history behavior",
        "I-4C1 consumer boundary",
        "relaylm.mem.forget_prepared.v0",
        "I-4C2: prepared resume",
        "I-4D: M3f/M3g convergence",
    ),
    "docs/architecture/phase_i4c1_primary_forget_hidden_successor.md": (
        "Status: complete for the bounded I-4C1 commit boundary.",
        "relaylm.mem.forget_prepared.v0",
        "relaymem.primary_lifecycle_page.v0",
        "hidden / recovery_required / retrieval_eligible=false",
        "I-4C2 prepared resume",
        "M3f or M3g",
    ),
    "docs/architecture/o0_local_one_job_runner.md": (
        "Shared O0/O1C production helper boundary",
        "O1C does not launch this CLI as a subprocess",
        "O1A target scheduler gates are design-only",
        "O1B  one sealed I1-G discovery and I1-GC delegation",
        "O1C  one B2/B3 discovery and C2 delegation — complete",
    ),
    "docs/architecture/soul_lab_ui_b0_real_home_conversation.md": (
        "same-origin POST /v1/chat/completions",
        "Real Runtime is the default source mode",
        "New Conversation applies only to the current character",
        "This path is operator-driven",
        "UI-B0 does not claim that the complete E1 flow is automated",
    ),
}

STALE_O1C = (
    "Scheduler production: O1B through O1F unimplemented",
    "Future O1C reuse boundary",
    "O1C will later extract or reuse",
    "O1C  one eligible B2 record discovery and one C2 delegation",
    "O1C queue discovery/C2 delegation remains unimplemented",
)

STALE_I1GC = (
    "I1-GC restart replay / downstream convergence / completion marker: unimplemented",
    "I1-GC restart replay / exact C1-5+B2 convergence / completion marker: unimplemented",
    "I1-GC one-record restart replay and completion convergence, I1-GD cleanup, and I1-GE crash validation",
    "I1-GC/GD/GE replay, cleanup, and full crash validation: unimplemented",
    "I1-GC through I1-GE remain planned",
    "I1-GC through I1-GE remain unimplemented",
    "I1-GC  one-record restart replay, exact convergence, completion    unimplemented",
    "I1-GC  one-record restart replay, duplicate convergence, completion     current implementation work",
    "Window A recovery side — I1-GC unimplemented",
    "I1-GC replay/completion, I1-GD cleanup, and I1-GE full crash validation remain unimplemented",
    "I1-GC restart replay and completion convergence, I1-GD retention/cleanup, and I1-GE full production crash validation remain unimplemented",
    "This section supersedes earlier",
    "supersedes earlier roadmap entries",
)


def main() -> None:
    validate_config_coverage("docs/config_schema.md")
    validate_config_coverage("config.example.yaml")
    for path in ("relaylm/config.py", "docs/config_schema.md", "config.example.yaml"):
        forbid(path, *O1A_TARGET_ONLY_FIELDS)

    for path, anchors in REQUIRED.items():
        require(path, *anchors)

    for path in CURRENT_DOCS:
        forbid(path, *STALE_I1GC)
        forbid(path, *STALE_O1C)

    run_i1g_fault_model()
    run_o1a_contract()
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main()
