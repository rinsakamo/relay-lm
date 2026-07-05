"""E1-R5 no-symlink scoped Primary MEM recall smoke."""
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
            candidate_id="e1r5-no-symlink",
            title="朝の集中作業",
            summary=SUMMARY,
        )
        require(not (configured_root / "memory").exists(), "compat symlink exists")
        require(not (configured_root / "memory").is_symlink(), "compat symlink exists")

        bridged = apply_relaymem_primary_recall_scope(
            {
                "scene_type": "design_talk",
                "retrieval_scope": "long_term_memory",
                "snippet_apply_decision": "eligible_but_not_applied",
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
        require(runtime["selected_count"] == 1, runtime)
        require(runtime["primary_candidate_discovery_attempted"] is True, runtime)
        require("primary_recall_no_scoped_match" not in runtime["blocked_reason_ids"], runtime)
        require(runtime["selected_memories"][0]["lifecycle_state"] == "active", runtime)
        require(runtime["selected_memories"][0]["current"] is True, runtime)

    print("E1-R5 Primary MEM recall no-symlink smoke passed")


if __name__ == "__main__":
    main()
