"""E1-R5 scoped Primary MEM candidate discovery bridge smoke."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from _relaylm_phase_i3_test_support import form_primary_memory, require
from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context
from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CHARACTER = "default"
NAMESPACE = "character_default"
SUMMARY = "評価用に覚えておいて。私は朝の集中作業では、浅煎りのエチオピアコーヒーを飲むのが一番落ち着きます。"
QUESTION = "私が朝の集中作業で落ち着く飲み物って何だっけ？"


def artifact() -> dict[str, object]:
    return {
        "scene_type": "design_talk",
        "retrieval_scope": "long_term_memory",
        "snippet_apply_decision": "eligible_but_not_applied",
        "query_summary": {
            "source": "latest_user_message",
            "term_hints": ["朝の集中作業", "落ち着く飲み物", "飲み物"],
        },
        # Existing sample memories must not override an eligible scoped Primary MEM.
        "selected_mem_candidates": [
            {"path": "memory/mem/projects/default-relaylm-project.md", "memory_layer": "legacy_flat", "reason": "keyword_match"},
            {"path": "memory/mem/projects/default-like-tea.md", "memory_layer": "legacy_flat", "reason": "keyword_match"},
            {"path": "memory/mem/summaries/shared-short-replies.md", "memory_layer": "legacy_flat", "reason": "keyword_match"},
        ],
    }


def main() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        configured_root = Path(directory) / "runtime" / "memory"
        configured_root.mkdir(parents=True)
        scoped_value = resolve_relaymem_character_store_root(str(configured_root), CHARACTER)
        require(scoped_value is not None, "character scope unresolved")
        scoped = Path(scoped_value)
        scoped.mkdir(parents=True)
        memory_id = form_primary_memory(
            scoped,
            namespace=NAMESPACE,
            candidate_id="e1r5-coffee",
            title="朝の集中作業の飲み物",
            summary=SUMMARY,
        )
        require(not (configured_root / "memory").exists(), "top-level symlink workaround present")

        bridged = apply_relaymem_primary_recall_scope(
            artifact(),
            scoped_store_root=str(scoped),
            expected_namespace=NAMESPACE,
            max_snippet_chars=512,
            max_snippet_candidates=3,
            snippet_budget=512,
        )
        runtime = bridged["primary_recall_runtime"]
        projection = bridged["primary_recall_projection"]
        require(runtime["primary_candidate_discovery_attempted"] is True, runtime)
        require(runtime["primary_candidate_count"] >= 1, runtime)
        require(runtime["selected_count"] == 1, runtime)
        require(projection["selected_count"] == 1, projection)
        require(projection["selected_layer_counts"]["primary"] == 1, projection)
        require("primary_recall_no_scoped_match" not in runtime["blocked_reason_ids"], runtime)
        require("浅煎りのエチオピアコーヒー" in json.dumps(runtime, ensure_ascii=False), runtime)

        grounded = build_grounded_recall_context(
            retrieved_memories=runtime["selected_memories"],
            query_text=QUESTION,
            character_id=CHARACTER,
            namespace=NAMESPACE,
        )
        context = grounded.grounded_recall_context or {}
        backend_messages = json.dumps(context.get("backend_messages"), ensure_ascii=False)
        require("[RelayMEM Grounded Recall Context]" in backend_messages, backend_messages)
        require("浅煎りのエチオピアコーヒー" in backend_messages, backend_messages)
        require("Do not invent dates" in backend_messages, backend_messages)

        public = json.dumps(projection, ensure_ascii=False)
        for forbidden in (SUMMARY, "浅煎り", "エチオピア", str(scoped), str(configured_root), memory_id):
            require(forbidden not in public, ("public leak", forbidden, public))
        for flag in (
            "evidence_content_included",
            "runtime_private_evidence_omitted",
            "path_values_included",
            "digest_values_included",
        ):
            require(flag in projection, projection)

    print("E1-R5 Primary MEM recall candidate bridge smoke passed")


if __name__ == "__main__":
    main()
