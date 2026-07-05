"""E1-R5 Primary MEM recall bridge fallback-discovery policy-gate smoke.

Regression coverage for a P1 fix: fallback discovery from the character-scoped
Primary MEM index/log/page controls must never run merely because the
original ``snippet_apply_decision`` gate was already open (``gate_allowed``).
It must also require ``fallback_policy_blocker is None`` -- i.e. scene policy,
unresolved-reference, and ``current_context_only`` blockers must independently
be absent, even when the M2 gate itself already permitted external memory.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from _relaylm_phase_i3_test_support import form_primary_memory, require
from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CHARACTER = "default"
NAMESPACE = "character_default"
SUMMARY = "私は朝の集中作業では浅煎りのエチオピアコーヒーが落ち着きます。"


def main() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        configured_root = Path(directory) / "runtime" / "memory"
        configured_root.mkdir(parents=True)
        scoped_value = resolve_relaymem_character_store_root(str(configured_root), CHARACTER)
        require(scoped_value is not None, "character scope unresolved")
        scoped = Path(scoped_value)
        scoped.mkdir(parents=True)
        form_primary_memory(
            scoped,
            namespace=NAMESPACE,
            candidate_id="e1r5-policy-gate",
            title="朝の集中作業",
            summary=SUMMARY,
        )

        # snippet_apply_decision="dry_run_only" makes gate_allowed True. Query
        # terms are present and a valid scoped Primary MEM page/index/log
        # exists, so a buggy "gate_allowed alone permits fallback discovery"
        # implementation would still promote this into selected evidence even
        # though retrieval_scope="current_context_only" must block external
        # memory discovery outright.
        bridged = apply_relaymem_primary_recall_scope(
            {
                "scene_type": "design_talk",
                "retrieval_scope": "current_context_only",
                "snippet_apply_decision": "dry_run_only",
                "query_summary": {"term_hints": ["朝の集中作業", "エチオピアコーヒー"]},
                "selected_mem_candidates": [],
            },
            scoped_store_root=str(scoped),
            expected_namespace=NAMESPACE,
            max_snippet_chars=512,
            max_snippet_candidates=3,
            snippet_budget=512,
        )
        runtime = bridged["primary_recall_runtime"]
        projection = bridged["primary_recall_projection"]

        require(runtime["selected_count"] == 0, runtime)
        require(runtime["selected_memories"] == [], runtime)
        require(runtime["primary_candidate_discovery_attempted"] is False, runtime)
        require(
            "current_context_only_no_external_mem" in runtime["blocked_reason_ids"],
            runtime,
        )
        require("primary_candidate_selected" not in runtime["blocked_reason_ids"], runtime)
        require("primary_recall_grounding_applied" not in runtime["blocked_reason_ids"], runtime)
        require("primary_recall_no_scoped_match" in runtime["blocked_reason_ids"], runtime)

        require(projection["grounding_enabled"] is False, projection)
        require(projection["grounded_item_count"] == 0, projection)
        require(projection["scope_matched"] is False, projection)
        require(
            "current_context_only_no_external_mem" in projection["blocked_reason_ids"],
            projection,
        )

    print("E1-R5 Primary MEM recall bridge policy-gate smoke passed")


if __name__ == "__main__":
    main()
