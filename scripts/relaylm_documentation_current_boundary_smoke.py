#!/usr/bin/env python3
"""Validate current Phase 6/I1 documentation and config coverage."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *anchors: str) -> None:
    body = read_text(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing current-boundary anchors: {missing!r}"


def forbid(path: str, *anchors: str) -> None:
    body = read_text(path)
    present = [anchor for anchor in anchors if anchor in body]
    assert not present, f"{path}: superseded boundary remains: {present!r}"


def relaylm_config_fields() -> tuple[str, ...]:
    tree = ast.parse(read_text("relaylm/config.py"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RelayLMConfig":
            fields = tuple(
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            )
            assert fields, "relaylm/config.py: RelayLMConfig has no annotated fields"
            return fields
    raise AssertionError("relaylm/config.py: RelayLMConfig class not found")


def require_config_coverage(path: str) -> None:
    body = read_text(path)
    missing = [
        field
        for field in relaylm_config_fields()
        if re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])",
            body,
        )
        is None
    ]
    assert not missing, f"{path}: missing RelayLMConfig fields: {missing!r}"


def main() -> None:
    require_config_coverage("docs/config_schema.md")
    require_config_coverage("config.example.yaml")
    require(
        "docs/config_schema.md",
        "## RelayMEM / RelaySLP Phase 6 flags",
        "relaymem_slp_runtime_enqueue_enabled: false",
        "relaymem_slp_protected_source_root:",
        "relaymem_slp_protected_source_max_artifact_bytes: 262144",
        "At capacity, a new entry is rejected rather than evicting an existing entry.",
        "do not have separate top-level `RelayLMConfig` enable/apply fields",
    )

    require(
        "docs/PROJECT_STATUS.md",
        "C1-0 through C1-5 complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "I1 next-turn Primary MEM recall: complete",
        "character and namespace isolation: complete",
        "I1-G pre-enqueue background-finalizer durability: unresolved",
    )
    forbid(
        "docs/PROJECT_STATUS.md",
        "C1-2 one-already-claimed-job worker execution is not yet on `main`",
        "one-job claim/rehydrate/execute adapter     next integration boundary",
    )

    require(
        "docs/architecture/pipeline_implementation_plan.md",
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase I-1 completes next-turn recall and character/namespace isolation",
        "### I1-D: next-turn recall validation — complete",
        "### I1-G: pre-enqueue background-finalizer durability",
        "`docs/config_schema.md`",
        "stale TODO or future-tense text in related documents",
    )
    forbid(
        "docs/architecture/pipeline_implementation_plan.md",
        "### I1-D: next-turn recall validation\n\nProve that",
        "The remaining I1 connection is next-turn recall",
        "ordinary runtime still lacks the one-job adapter",
    )

    require(
        "docs/architecture/current_target_migration_guide.md",
        "A1/A2/B0-B3, ordinary I1-B source-before-queue publication",
        "Phase I-1 verifies the later-turn retrieval path",
        "I1-G pre-enqueue durability",
        "relaymem_slp_runtime_enqueue_apply_enabled=false",
    )
    forbid(
        "docs/architecture/current_target_migration_guide.md",
        "A1/A2/B1 helpers and B2 atomic durable enqueue",
        "Phase 6 currently reaches B2 atomic durable enqueue",
    )

    require(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "M3i-c next-turn recall and scope isolation: complete as Phase I-1",
        "MEM-M4 Secondary MEM consolidation: deferred until Integration Milestone I1 closes",
    )
    forbid(
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "M3i-c next-turn recall and scope isolation: next",
        "MEM-M4 Secondary MEM consolidation: deferred until M3i-b",
    )

    require(
        "docs/architecture/README.md",
        "Phase I-1 completes next-turn recall with character/namespace isolation",
        "I1-G pre-enqueue background-finalizer durability",
    )
    forbid(
        "docs/architecture/README.md",
        "The next boundary is next-turn recall and character/namespace isolation",
        "remaining next-turn recall integration",
    )

    require(
        "docs/README.md",
        "`config_schema.md`",
        "Current/Target Boundary Matrix",
        "stale TODO/future-tense text in related plans",
    )

    require(
        "docs/architecture/relaymem_slp_current_target.md",
        "C1-5 durable claim-independent protected source and restart rehydration",
        "C2 one-job claim/rehydrate/execute adapter",
        "I1 next-turn Primary MEM recall: complete",
        "Character and namespace isolation: complete",
        "pre-enqueue background-finalizer crash window",
    )

    require(
        "docs/architecture/phase6c2_one_queued_primary_worker_integration.md",
        "exact queued B3 record",
        "canonical B3 claim",
        "C1-5 protected-source lookup / rehydrate",
        "unchanged C1-2 one-claimed worker",
        "Queue scanning/scheduling",
        "Phase I-1 is complete",
        "pre-enqueue background-finalizer crash recovery",
    )

    print("RelayLM documentation current-boundary smoke passed.")


if __name__ == "__main__":
    main()
