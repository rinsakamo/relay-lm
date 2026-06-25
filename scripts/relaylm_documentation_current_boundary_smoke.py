#!/usr/bin/env python3
"""Validate current Phase 6, I1-I4A, UI-B0, I1-GA, roadmap, and config documentation."""
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
        "character and namespace isolation: complete",
        "I2 real SOUL Lab observation: complete",
        "I3 auditable Primary MEM Correct: complete",
        "I1 observe/correct/retrieve product loop: complete",
        "UI-B0 real Home conversation: complete",
        "I4A Forget / Hide contract: defined target",
        "I4 production Forget runtime, M2 exclusion, and UI: unimplemented",
        "I1-GA contract / design decision / fault model: complete",
        "I1-GB through I1-GE production durability: not implemented",
        "I1-G pre-enqueue background-finalizer durability: unresolved",
        "production Forget lifecycle apply, hidden-state M2 exclusion, Forget history API, or Forget UI",
        "restore / unhide",
        "hard delete, secure erase, or physical purge through Forget",
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
        "### UI-B0: Real Home Conversation — complete",
        "### I1-G: pre-enqueue background-finalizer durability — unresolved",
        "I1-GA contract/design/fault-model work is complete",
        "I1-GB through I1-GE remain planned",
        "Phase I-4B through I-4F",
        "## O1: two-lane bounded scheduler — planned",
        "I-4C1  token/fence/revision ownership",
        "I-4C2  exact replay, prepared resume, forward recovery",
        "UI-B1A  after I1-GC and I-4D",
        "### Wave 0 — current parallel work",
        "### Wave 3 — production proof and product surfaces",
        "I-5 Pin / Unpin",
        "-> I-7 Held Apply / Discard",
        "-> I-6 Merge / Supersession",
        "G1  I1-G complete",
        "M4  Phase I-4 complete",
        "post_i3_evaluation_work_roadmap.md",
        "`docs/config_schema.md`",
        "stale TODO or future-tense text in related documents",
    )

    require(
        "docs/architecture/post_i3_evaluation_work_roadmap.md",
        "Phase I-3: Auditable Correct — complete",
        "Phase I-4: Forget / Hide",
        "I-4A  lifecycle, persistence, concurrency, API, recovery, and fault contract — defined target",
        "Only I-4A is defined. I-4B through I-4F are unimplemented.",
        "I-4C delivery subdivision",
        "I-4C1  exact token validation, shared revision claim, prepared artifact",
        "I-4C2  prepared-operation resume, forward-only recovery, exact replay",
        "Phase I-5: Pin / Unpin",
        "Phase I-6: Merge / Supersession",
        "Phase I-7: Held Apply / Discard",
        "Phase I-8: Secondary MEM Consolidation",
        "Phase I-9: RelaySOUL Proposal / Intervention / Rollback",
        "UI-B0: Real Home Conversation — complete",
        "UI-B1A  after I1-GC and I-4D",
        "### O0: Local one-job runner — complete",
        "E1 is available now as an explicit operator-driven evaluation",
        "I1-G: Pre-enqueue durability",
        "I1-GA  failure-window and durable-finalization contract — complete",
        "O1: Queue scanner and retry scheduler",
        "O1 has two distinct work-source lanes",
        "O2: Supervised worker service",
        "O3: Always-on local operation",
        "Dependency-first implementation waves",
        "### Wave 0 — current parallel work",
        "### Wave 3 — production proof and product surfaces",
        "I-5 Pin / Unpin",
        "-> I-7 Held Apply / Discard",
        "-> I-6 Merge / Supersession",
        "G1  I1-G complete",
        "M4  Phase I-4 complete",
        "E1: Core RelayLM product hypothesis",
        "E2: Primary MEM governance product",
        "E3: Long-term character system",
    )

    require(
        "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md",
        "relaylm_status: target",
        "Defined target contract; runtime unimplemented.",
        "Decision: Candidate A",
        "Forget tombstone",
        "relaylm.mem.primary_current_state.v0",
        "restore or unhide",
        "physical deletion",
        "I1-G pre-enqueue durability",
    )

    require(
        "docs/architecture/soul_lab_ui_b0_real_home_conversation.md",
        "same-origin POST /v1/chat/completions",
        "Real Runtime is the default source mode",
        "New Conversation applies only to the current character",
        "O0 is complete and provides the explicit one-job execution boundary",
        "O0 explicit one-job execution",
        "This path is operator-driven",
        "UI-B0 does not claim that the complete E1 flow is automated",
    )

    require(
        "docs/architecture/soul_lab_ui_mvp.md",
        "UI-B0 real Home conversation: complete",
        "same-origin `POST /v1/chat/completions`",
        "Local Preview remains available only through explicit user selection",
        "O0 explicit local one-job runner: complete outside browser authority",
        "combined with the completed O0 explicit one-job runner",
    )

    require(
        "apps/soul-lab/README.md",
        "real Home conversation through the existing RelayLM `/v1/chat/completions` path",
        "npm run smoke:home-conversation",
        "Conversation transcripts remain browser-process-local",
    )

    require(
        "docs/architecture/current_target_migration_guide.md",
        "A1/A2/B0-B3, ordinary I1-B source-before-queue publication",
        "Phase I-1 verifies the later-turn retrieval path",
        "I1-G pre-enqueue durability",
        "relaymem_slp_runtime_enqueue_apply_enabled=false",
    )

    require(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "M3i-c next-turn recall and scope isolation: complete as Phase I-1",
        "M3i-d real read-only Lab observation: complete as Phase I-2",
        "Observation receipts",
        "auditable Correct: complete",
        "Phase I-4A Forget / Hide contract: defined target",
        "production Forget runtime, M2 exclusion, and UI: unimplemented",
        "I1-G pre-enqueue background-finalizer durability remains unresolved",
        "O0 explicit local one-job caller: complete",
        "The next parallel work is I1-GB durable-finalization publication",
    )

    require(
        "docs/architecture/README.md",
        "Phase I-1 completes ordinary next-turn Primary MEM recall",
        "Phase I-2 adds a bounded read-only observation model",
        "Phase I-3 completes auditable revision-fenced Correct",
        "Phase I-4A defines the target Forget contract",
        "UI-B0 adds a browser-local text-first client",
        "phase_i4_primary_mem_forget_hide_contract.md",
        "soul_lab_ui_b0_real_home_conversation.md",
        "i1g_pre_enqueue_durable_finalization_contract.md",
        "I1-GA defines the target turn-scoped sealed durable-finalization record",
        "I1-G production publication, restart replay, retention/cleanup, and crash integration remain unresolved",
    )

    require(
        "docs/README.md",
        "`config_schema.md`",
        "Current/Target Boundary Matrix",
        "stale TODO/future-tense text in related plans",
        "phase_i2_real_soul_lab_observation.md",
        "phase_i3_auditable_primary_mem_correct.md",
        "phase_i4_primary_mem_forget_hide_contract.md",
        "soul_lab_ui_b0_real_home_conversation.md",
        "i1g_pre_enqueue_durable_finalization_contract.md",
        "post_i3_evaluation_work_roadmap.md",
        "Production Forget apply, M2 exclusion, and the SOUL Lab Forget UI remain unimplemented",
        "I1-G",
    )

    require(
        "docs/architecture/relaymem_slp_current_target.md",
        "Phase 6-B2 performs atomic durable enqueue",
        "Phase 6-B3 performs default-off, dry-run-first",
        "C1-5 durable claim-independent protected source and restart rehydration",
        "C2 one-job claim/rehydrate/execute adapter",
        "O0 local one-job operation is complete",
        "O1 polling/retry scheduling, O2 supervision, and O3 always-on operation remain unimplemented",
        "durably enqueued jobs",
        "I1 next-turn Primary MEM recall: complete",
        "I2 real SOUL Lab observation: complete",
        "I3 auditable Primary MEM Correct: complete",
        "I-4B through I-4F",
        "I1-G pre-enqueue background-finalizer durability remains unresolved",
    )

    require(
        "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",
        "relaylm_status: target",
        "turn-scoped sealed durable-finalization publication record",
        "Window A — unresolved",
        "source-before-queue invariant is absolute",
        "One-record replay algorithm",
        "Required fault matrix",
        "I1-GA — complete in this slice",
        "I1-GB — durable-finalization publication",
        "I1-GC — one-record replay and duplicate suppression",
        "I1-GD — retention, orphan reconciliation, and cleanup",
        "I1-GE — production crash-at-every-boundary integration smoke",
        "Production pre-enqueue durability remains unresolved",
    )

    forbid(
        "docs/PROJECT_STATUS.md",
        "SOUL Lab real observation: next",
        "auditable Correct operation: next",
        "real SOUL Lab Home conversation remain separate work",
        "I1-G pre-enqueue background-finalizer durability: complete",
        "I4 production Forget runtime, M2 exclusion, and UI: complete",
    )
    forbid(
        "docs/README.md",
        "Phase I-3 next step",
        "The next product boundary is Phase I-3",
        "real SOUL Lab Home conversation remain separate work",
        "Forget is implemented",
    )
    forbid(
        "docs/architecture/README.md",
        "The next boundary is Phase I-3",
        "the next Correct boundary",
        "I1-G pre-enqueue background-finalizer production durability: complete",
        "Forget runtime is complete",
    )
    forbid(
        "docs/architecture/soul_lab_ui_mvp.md",
        "Phase I-3 auditable Correct: next",
        "## Phase I-3 next boundary",
        "O0 remains a separate convenience/operations slice",
    )
    forbid(
        "docs/architecture/soul_lab_ui_b0_real_home_conversation.md",
        "Until O0 exists",
        "O0 local one-job runner remains a separate parallel slice",
    )
    forbid(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "O0 and I1-G implementation may proceed in parallel",
    )
    forbid(
        "docs/architecture/relaymem_slp_current_target.md",
        "O0, queue scanner / daemon operation, supervised worker status",
    )
    forbid(
        "docs/architecture/pipeline_implementation_plan.md",
        "I3 I3 auditable",
        "Phase I-3 auditable Correct is the next product boundary",
        "## Active priority: Phase I-3 auditable Correct",
        "Phase I-4B through I-4F: complete",
        "I-5 -> I-6 -> I-7",
    )
    forbid(
        "docs/architecture/post_i3_evaluation_work_roadmap.md",
        "I-5 -> I-6 -> I-7",
    )

    run_i1g_fault_model()
    print("RelayLM documentation current-boundary smoke passed.")


if __name__ == "__main__":
    main()
