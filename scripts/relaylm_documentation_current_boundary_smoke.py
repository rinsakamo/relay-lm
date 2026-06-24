#!/usr/bin/env python3
"""Validate current Phase 6, I1-I3, I1-G, roadmap, and config documentation."""
from __future__ import annotations
import ast
import re
from pathlib import Path
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
                item.target.id for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            )
    raise AssertionError("RelayLMConfig not found")

def config_coverage(path: str) -> None:
    body = text(path)
    missing = [field for field in config_fields() if re.search(
        rf"(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])", body
    ) is None]
    assert not missing, f"{path}: missing config fields: {missing!r}"

def main() -> None:
    config_coverage("docs/config_schema.md")
    config_coverage("config.example.yaml")
    require("docs/PROJECT_STATUS.md",
        "C1-0 through C1-5 complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "I1 next-turn Primary MEM recall: complete",
        "character and namespace isolation: complete",
        "I2 real SOUL Lab observation: complete",
        "I1-G pre-enqueue background-finalizer durability: unresolved",
        "I3 auditable Primary MEM Correct: complete",
        "I1 observe/correct/retrieve product loop: complete")
    require("docs/architecture/pipeline_implementation_plan.md",
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter is complete",
        "### I1-D: next-turn recall validation — complete",
        "### I1-E / Phase I-2: real SOUL Lab observation — complete",
        "### I1-F / Phase I-3: auditable Primary MEM Correct — complete",
        "### I1-G: pre-enqueue background-finalizer durability — unresolved",
        "post_i3_evaluation_work_roadmap.md",
        "`docs/config_schema.md`",
        "stale TODO or future-tense text in related documents")
    require("docs/architecture/post_i3_evaluation_work_roadmap.md",
        "Phase I-3: Auditable Correct — complete",
        "Phase I-4: Forget / Hide",
        "Phase I-5: Pin / Unpin",
        "Phase I-6: Merge / Supersession",
        "Phase I-7: Held Apply / Discard",
        "Phase I-8: Secondary MEM Consolidation",
        "Phase I-9: RelaySOUL Proposal / Intervention / Rollback",
        "UI-B0: Real Home Conversation",
        "O0: Local one-job runner",
        "I1-G: Pre-enqueue durability",
        "O1: Queue scanner and retry scheduler",
        "O2: Supervised worker service",
        "O3: Always-on local operation",
        "E1: Core RelayLM product hypothesis",
        "E2: Primary MEM governance product",
        "E3: Long-term character system")
    require("docs/architecture/current_target_migration_guide.md",
        "A1/A2/B0-B3, ordinary I1-B source-before-queue publication",
        "Phase I-1 verifies the later-turn retrieval path",
        "I1-G pre-enqueue durability",
        "relaymem_slp_runtime_enqueue_apply_enabled=false")
    require("docs/architecture/relaymem_mvp_implementation_plan.md",
        "M3i-c next-turn recall and scope isolation: complete as Phase I-1",
        "M3i-d real read-only Lab observation: complete as Phase I-2",
        "I1-G pre-enqueue background-finalizer durability remains unresolved")
    require("docs/architecture/README.md",
        "Phase I-1 completes ordinary next-turn Primary MEM recall",
        "Phase I-2 adds a bounded read-only observation model",
        "Phase I-3 completes auditable revision-fenced Correct",
        "post_i3_evaluation_work_roadmap.md",
        "I1-G pre-enqueue background-finalizer durability")
    require("docs/README.md",
        "`config_schema.md`", "Current/Target Boundary Matrix",
        "stale TODO/future-tense text in related plans",
        "phase_i2_real_soul_lab_observation.md",
        "phase_i3_auditable_primary_mem_correct.md",
        "post_i3_evaluation_work_roadmap.md", "I1-G")
    require("docs/architecture/relaymem_slp_current_target.md",
        "C1-5 durable claim-independent protected source and restart rehydration",
        "C2 one-job claim/rehydrate/execute adapter",
        "I1 next-turn Primary MEM recall: complete",
        "I2 real SOUL Lab observation: complete",
        "I1-G pre-enqueue background-finalizer durability")
    forbid("docs/PROJECT_STATUS.md",
        "SOUL Lab real observation: next",
        "auditable Correct operation: next")
    forbid("docs/README.md",
        "Phase I-3 next step",
        "The next product boundary is Phase I-3")
    forbid("docs/architecture/README.md",
        "The next boundary is Phase I-3",
        "the next Correct boundary")
    forbid("docs/architecture/pipeline_implementation_plan.md",
        "I3 I3 auditable",
        "Phase I-3 auditable Correct is the next product boundary",
        "## Active priority: Phase I-3 auditable Correct")
    print("RelayLM documentation current-boundary smoke passed.")

if __name__ == "__main__":
    main()
