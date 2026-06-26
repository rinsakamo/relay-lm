#!/usr/bin/env python3
"""Validate current Phase 6, I1-I4C1, UI-B0, I1-G, roadmap, and config docs."""
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


REQUIRED: dict[str, tuple[str, ...]] = {
    "docs/PROJECT_STATUS.md": (
        "C1-0 through C1-5 complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "O0 local one-job runner: complete",
        "O1A two-lane scheduler / adapter / idle contract: complete",
        "O1B sealed-record discovery / I1-GC delegation: not implemented",
        "O1C B2 discovery / O0-compatible C2 delegation: not implemented",
        "O1D ordering / fairness / retry-time / backoff / jitter: not implemented",
        "O1E stale recovery / cancellation / graceful shutdown: not implemented",
        "O1F full operational validation: not implemented",
        "I1 next-turn Primary MEM recall: complete",
        "I2 real SOUL Lab observation: complete",
        "I3 auditable Primary MEM Correct: complete",
        "UI-B0 real Home conversation: complete",
        "I4A Forget / Hide contract: defined target",
        "I4B resolver / shared fence / read-only Forget boundary: complete",
        "I4C1 hidden-successor commit: complete",
        "I4C2 through I4F resume/replay/tombstone, M2 exclusion, UI, and validation: unimplemented",
        "I1-GB durable-finalization publication / pre-release admission: complete",
        "I1-GC restart replay / exact C1-5+B2 convergence / completion marker: unimplemented",
        "Direct Home-origin formation: not currently proven",
        "O1A adds no accepted configuration fields",
    ),
    "docs/architecture/o1a_two_lane_scheduler_contract.md": (
        "Contract and pure deterministic aggregation model complete; production scheduler unimplemented.",
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
    ),
    "docs/architecture/pipeline_implementation_plan.md": (
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter is complete",
        "### I1-F / Phase I-3: auditable Primary MEM Correct — complete",
        "### I1-F2 / Phase I-4A: Primary MEM Forget / Hide contract — defined target",
        "Phase I-4C1 hidden-successor commit: complete",
        "exact read-only preflight/history/token — complete",
        "### I1-G: pre-enqueue durable-finalization — in progress",
        "## O1A: two-lane bounded scheduler contract — complete",
        "O1A completion alone is not O1 completion.",
        "### Wave 0 — completed implementation foundation",
        "### Wave 1 — in progress: one-record recovery and lifecycle commit ownership",
        "Thread B  I-4C1 hidden-successor commit ownership — complete",
        "Direct Home-origin formation remains unproven",
        "I-5 Pin / Unpin",
        "-> I-7 Held Apply / Discard",
        "-> I-6 Merge / Supersession",
        "These fields are not added to `relaylm/config.py`",
    ),
    "docs/architecture/post_i3_evaluation_work_roadmap.md": (
        "Phase I-4B: Current-state resolver and shared mutation fence — complete",
        "Phase I-4C1: Hidden-successor commit — complete",
        "I-4C1  exact token validation",
        "one-winner concurrency — complete",
        "I-4C2  prepared resume",
        "I-4D   index/log convergence",
        "Phase I-5: Pin / Unpin",
        "Phase I-7: Held Apply / Discard",
        "Phase I-6: Merge / Supersession",
        "Phase I-8: Secondary MEM consolidation",
        "Phase I-9: RelaySOUL proposal / intervention / rollback",
        "### Wave 1 — in progress",
        "I1-GC || I-4C2 || O1A design",
        "does not prove direct Home-origin formation",
        "E1: Core RelayLM product hypothesis — available",
        "O1A completion alone does not satisfy the O1 checkpoint.",
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
    "docs/architecture/relaymem_mvp_implementation_plan.md": (
        "M3i-f canonical current-state resolver/shared fence: complete as Phase I-4B",
        "M3i-g hidden-successor commit ownership: complete as Phase I-4C1",
        "Forget hidden-successor commit: complete as I-4C1",
        "The next RelayMEM governance implementation slice is I-4C2",
        "No production hidden-state filtering exists yet because I-4D integration is not implemented",
        "I1-GC one-record replay and completion convergence",
        "I-4C1 hidden-successor commit — complete",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "Phase 6-B3 performs default-off, dry-run-first",
        "Phase I-4C1 hidden-successor commit — complete",
        "Current Primary mutation and lifecycle-read boundary",
        "I-4C1 shared revision claim, prepared artifact, hidden successor         complete",
        "Forget is not product-complete until I-4C2 through I-4F",
        "O1 polling/retry scheduling, O2 supervision, and O3 always-on operation remain unimplemented",
    ),
    "docs/architecture/README.md": (
        "Phase I-4B Primary Current State and Shared Mutation Fence",
        "Phase I-4C1 Primary Forget Hidden-Successor Commit",
        "hidden / recovery_required resolver state",
        "I1-GC restart replay and completion convergence",
        "O1A Two-Lane Scheduler and Idle Contract",
        "O1B through O1F",
    ),
    "docs/README.md": (
        "Phase I-4B Primary Current State and Shared Mutation Fence",
        "Phase I-4C1 Primary Forget Hidden-Successor Commit",
        "Phase I-4C1 is complete for exact token/reason revalidation",
        "I-4C2 recovery/replay/tombstone",
    ),
    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md": (
        "Window A publication side — implemented by I1-GB",
        "Window A recovery side — I1-GC unimplemented",
        "source-before-queue invariant is absolute",
        "I1-G overall is in progress",
        "## O1B caller boundary",
        "queue lane must independently discover the queue root",
    ),
    "docs/architecture/o0_local_one_job_runner.md": (
        "Future O1C reuse boundary",
        "O1C must not launch this CLI as a subprocess",
        "O1A target scheduler gates are design-only",
        "O1B  one sealed I1-G discovery and I1-GC delegation",
    ),
    "docs/architecture/soul_lab_ui_b0_real_home_conversation.md": (
        "same-origin POST /v1/chat/completions",
        "Real Runtime is the default source mode",
        "New Conversation applies only to the current character",
        "This path is operator-driven",
        "UI-B0 does not claim that the complete E1 flow is automated",
    ),
}

FORBIDDEN: dict[str, tuple[str, ...]] = {
    "docs/PROJECT_STATUS.md": (
        "canonical lifecycle resolver and hidden-state M2 exclusion",
        "production Forget preflight/apply/history",
        "I4 production Forget runtime, M2 exclusion, and UI: unimplemented",
        "I4C through I4F hidden apply, M2 exclusion, UI, and validation: unimplemented",
        "I1-G overall: complete",
        "O1 queue scanner / retry scheduler / polling: not implemented",
        "O1 automatic scheduler: complete",
    ),
    "docs/architecture/pipeline_implementation_plan.md": (
        "I-4B || O1A design",
        "I1-GC || I-4C1 || O1A design",
        "Phase I-4B through I-4F runtime, M2, UI, and validation: unimplemented",
        "Phase I-4C through I-4F hidden apply, M2, UI, and validation: unimplemented",
        "### Wave 1 — current: one-record recovery and lifecycle commit ownership",
        "The explicit E1 path is complete:\n\n```text\nHome real conversation\n  -> O0 one-job execution",
    ),
    "docs/architecture/post_i3_evaluation_work_roadmap.md": (
        "Only I-4A is defined. I-4B through I-4F are unimplemented.",
        "Current:\n  I-4B || O1A design",
        "### Wave 0 — current parallel work",
        "I1-GC || I-4C1 || O1A design",
    ),
    "docs/architecture/relaymem_mvp_implementation_plan.md": (
        "The next RelayMEM governance implementation slice is I-4B",
        "The next RelayMEM governance implementation slice is I-4C1",
        "All remain unimplemented.",
        "Forget resolver/apply/M2/UI/smoke: unimplemented as I-4B through I-4F",
        "O1 scanner/retry-scheduler design",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "The current resolver is correction-specific.",
        "I-4B  common current-state resolver and shared Correct/Forget fence   unimplemented",
        "I-4C1 shared revision claim, prepared artifact, hidden successor         unimplemented",
        "the canonical lifecycle resolver defined by I-4A",
    ),
    "docs/README.md": (
        "Phase I-4A is defined as a target contract only.",
        "Phase I-3 next step",
        "I-4C through I-4F production apply, exclusion, UI, and validation remain unimplemented",
        "Forget is implemented",
        "O1/O2/O3 automatic operation remain unimplemented",
    ),
}


def main() -> None:
    validate_config_coverage("docs/config_schema.md")
    validate_config_coverage("config.example.yaml")
    for path in ("relaylm/config.py", "docs/config_schema.md", "config.example.yaml"):
        forbid(path, *O1A_TARGET_ONLY_FIELDS)
    for path, anchors in REQUIRED.items():
        require(path, *anchors)
    for path, anchors in FORBIDDEN.items():
        forbid(path, *anchors)
    run_i1g_fault_model()
    run_o1a_contract()
    print("relaylm documentation current-boundary smoke: ok")


if __name__ == "__main__":
    main()


# I1-GC documentation boundary assertions
def _assert_i1gc_documentation_boundary() -> None:
    root = Path(__file__).resolve().parents[1]
    required = ('docs/PROJECT_STATUS.md', 'docs/README.md', 'docs/architecture/README.md', 'docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md', 'docs/architecture/pipeline_implementation_plan.md', 'docs/architecture/post_i3_evaluation_work_roadmap.md', 'docs/architecture/relaymem_slp_current_target.md', 'docs/architecture/relaymem_mvp_implementation_plan.md')
    for relative in required:
        text = (root / relative).read_text(encoding="utf-8")
        assert 'I1-GC durable-finalization replay current boundary (2026-06-26)' in text, relative
        assert "I1-GD" in text, relative
        assert "I1-GE" in text, relative
        assert "O1" in text, relative
    replay = (root / "relaylm/relaymem_slp_durable_finalization_replay.py").read_text(encoding="utf-8")
    implementation = (root / "relaylm/_relaymem_slp_durable_finalization_replay_impl.py").read_text(encoding="utf-8")
    assert "replay_relaymem_slp_durable_finalization_record" in replay
    assert "COMPLETION_SCHEMA" in implementation
    assert "transition_relaymem_slp_queue_state" not in implementation


if __name__ == "__main__":
    _assert_i1gc_documentation_boundary()
