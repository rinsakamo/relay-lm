#!/usr/bin/env python3
"""Validate current Phase 6, I1-I4B, UI-B0, I1-GA/I1-GB, roadmap, and config documentation."""
from __future__ import annotations

import ast
import re
from pathlib import Path

from relaylm_i1g_pre_enqueue_fault_model_smoke import main as run_i1g_fault_model

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *anchors: str) -> None:
    body = text(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing anchors: {missing!r}"


def forbid(path: str, *anchors: str) -> None:
    body = text(path)
    present = [anchor for anchor in anchors if anchor in body]
    assert not present, f"{path}: stale anchors: {present!r}"


def config_fields() -> tuple[str, ...]:
    tree = ast.parse(text("relaylm/config.py"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RelayLMConfig":
            return tuple(
                item.target.id
                for item in node.body
                if isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
            )
    raise AssertionError("RelayLMConfig not found")


def config_coverage(path: str) -> None:
    body = text(path)
    missing = [
        field
        for field in config_fields()
        if re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])", body
        )
        is None
    ]
    assert not missing, f"{path}: missing config fields: {missing!r}"


def main() -> None:
    config_coverage("docs/config_schema.md")
    config_coverage("config.example.yaml")

    require(
        "docs/PROJECT_STATUS.md",
        "C1-0 through C1-5 complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "O0 local one-job runner: complete",
        "O1 queue scanner / retry scheduler / polling: not implemented",
        "I1 next-turn Primary MEM recall: complete",
        "I2 real SOUL Lab observation: complete",
        "I3 auditable Primary MEM Correct: complete",
        "UI-B0 real Home conversation: complete",
        "I4A Forget / Hide contract: defined target",
        "I4B resolver / shared fence / read-only Forget boundary: complete",
        "I4C through I4F hidden apply, M2 exclusion, UI, and validation: unimplemented",
        "I1-GA contract / design decision / fault model: complete",
        "I1-GB durable-finalization publication / pre-release admission: complete",
        "I1-GC restart replay / exact C1-5+B2 convergence / completion marker: unimplemented",
        "Direct Home-origin formation: not currently proven",
        "I-4C hidden-lifecycle apply/recovery",
    )

    require(
        "docs/architecture/pipeline_implementation_plan.md",
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter is complete",
        "### O0: local one-job runner — complete",
        "### I1-D: next-turn recall validation — complete",
        "### I1-E / Phase I-2: real SOUL Lab observation — complete",
        "### I1-F / Phase I-3: auditable Primary MEM Correct — complete",
        "### I1-F2 / Phase I-4A: Primary MEM Forget / Hide contract — defined target",
        "I-4B now implements the canonical read-only resolver",
        "exact read-only preflight/history/token — complete",
        "### UI-B0: Real Home Conversation — complete",
        "### I1-G: pre-enqueue durable-finalization — in progress",
        "### Wave 0 — completed implementation foundation",
        "### Wave 1 — current: one-record recovery and lifecycle commit ownership",
        "I1-GC || I-4C1 || O1A design",
        "Direct Home-origin formation remains unproven",
        "I-5 Pin / Unpin",
        "-> I-7 Held Apply / Discard",
        "-> I-6 Merge / Supersession",
        "G1  I1-G complete",
        "M4  Phase I-4 complete",
    )

    require(
        "docs/architecture/post_i3_evaluation_work_roadmap.md",
        "Phase I-4B: Current-state resolver and shared mutation fence — complete",
        "I-4B canonical read-only current-state resolver",
        "I-4C1  exact token validation",
        "I-4C2  prepared resume",
        "I-4D   index/log convergence",
        "Phase I-5: Pin / Unpin",
        "Phase I-7: Held Apply / Discard",
        "Phase I-6: Merge / Supersession",
        "Phase I-8: Secondary MEM consolidation",
        "Phase I-9: RelaySOUL proposal / intervention / rollback",
        "UI-B0: Real Home Conversation — complete",
        "UI-B1: Memory lifecycle visibility — planned",
        "O0: Local one-job runner — complete",
        "I1-G: Pre-enqueue durability — in progress",
        "O1: Two-lane bounded scheduler — planned",
        "O2: Supervised worker service — planned",
        "O3: Always-on local operation — planned",
        "### Wave 1 — current",
        "I1-GC || I-4C1 || O1A design",
        "does not prove direct Home-origin formation",
        "E1: Core RelayLM product hypothesis — available",
        "E2: Primary MEM governance product — future",
        "E3: Long-term character system — future",
    )

    require(
        "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md",
        "relaylm_status: target",
        "Decision: Candidate A",
        "Forget tombstone",
        "relaylm.mem.primary_current_state.v0",
        "restore or unhide",
        "physical deletion",
        "I1-G pre-enqueue durability",
    )

    require(
        "docs/architecture/phase_i4b_primary_current_state_shared_fence.md",
        "Complete for the I-4B read-only boundary.",
        "canonical Primary current-state resolver",
        "shared Correct/Forget mutation fence",
        "five-minute token validation",
        "bounded zero-item history behavior",
        "I-4C: hidden successor apply",
        "I-4D: canonical hidden/prepared/recovery/corrupt exclusion",
    )

    require(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "M3i-f canonical current-state resolver/shared fence: complete as Phase I-4B",
        "Forget resolver/shared fence/read-only preflight-token-history: complete as I-4B",
        "The next RelayMEM governance implementation slice is I-4C1",
        "No production hidden-state filtering exists yet",
        "I1-GC one-record replay and completion convergence",
        "I-4C1 hidden-successor commit ownership",
    )

    require(
        "docs/architecture/relaymem_slp_current_target.md",
        "Phase I-4B completes the canonical read-only Primary current-state resolver",
        "Current Primary mutation and lifecycle-read boundary",
        "I-4B  current-state resolver and shared Correct/Forget fence            complete",
        "Forget is not product-complete until I-4C through I-4F",
        "O1 polling/retry scheduling, O2 supervision, and O3 always-on operation remain unimplemented",
    )

    require(
        "docs/architecture/README.md",
        "Phase I-4B now implements the canonical read-only current-state resolver",
        "Phase I-4B Primary Current State and Shared Mutation Fence",
        "I1-GC restart replay and completion convergence",
    )

    require(
        "docs/README.md",
        "Phase I-4B Primary Current State and Shared Mutation Fence",
        "Phase I-4B is complete for the canonical read-only current-state resolver",
        "I-4C through I-4F production apply, exclusion, UI, and validation remain unimplemented",
        "post_i3_evaluation_work_roadmap.md",
    )

    require(
        "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",
        "relaylm_status: current",
        "Window A publication side — implemented by I1-GB",
        "Window A recovery side — I1-GC unimplemented",
        "source-before-queue invariant is absolute",
        "I1-G overall is in progress",
    )

    require(
        "docs/architecture/soul_lab_ui_b0_real_home_conversation.md",
        "same-origin POST /v1/chat/completions",
        "Real Runtime is the default source mode",
        "New Conversation applies only to the current character",
        "This path is operator-driven",
        "UI-B0 does not claim that the complete E1 flow is automated",
    )

    forbid(
        "docs/PROJECT_STATUS.md",
        "canonical lifecycle resolver and hidden-state M2 exclusion",
        "production Forget preflight/apply/history",
        "I4 production Forget runtime, M2 exclusion, and UI: unimplemented",
        "I1-G overall: complete",
    )
    forbid(
        "docs/architecture/pipeline_implementation_plan.md",
        "I-4B || O1A design",
        "Phase I-4B through I-4F runtime, M2, UI, and validation: unimplemented",
        "The explicit E1 path is complete:\n\n```text\nHome real conversation\n  -> O0 one-job execution",
    )
    forbid(
        "docs/architecture/post_i3_evaluation_work_roadmap.md",
        "Only I-4A is defined. I-4B through I-4F are unimplemented.",
        "Current:\n  I-4B || O1A design",
        "### Wave 0 — current parallel work",
    )
    forbid(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "The next RelayMEM governance implementation slice is I-4B",
        "All remain unimplemented.",
        "Forget resolver/apply/M2/UI/smoke: unimplemented as I-4B through I-4F",
    )
    forbid(
        "docs/architecture/relaymem_slp_current_target.md",
        "The current resolver is correction-specific.",
        "I-4B  common current-state resolver and shared Correct/Forget fence   unimplemented",
        "the canonical lifecycle resolver defined by I-4A",
    )
    forbid(
        "docs/README.md",
        "Phase I-4A is defined as a target contract only.",
        "Phase I-3 next step",
        "Forget is implemented",
    )

    run_i1g_fault_model()
    print("relaylm documentation current-boundary smoke: ok")


if __name__ == "__main__":
    main()
