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
PASSPHRASE_SUMMARY = "評価用メモです。私はRelayLM MVP評価では、合言葉を「青い灯台」と呼ぶことにしました。"
PASSPHRASE_QUESTION = "RelayLM MVP評価の合言葉として、私が「呼ぶことにしました」と言った言葉は何ですか？"


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


def no_selected_candidates_artifact() -> dict[str, object]:
    return {
        "scene_type": "design_talk",
        "retrieval_scope": "long_term_memory",
        "snippet_apply_decision": "blocked_no_candidates",
        "snippet_apply_blocked_reasons": [
            "blocked_no_candidates",
            "ctx_block_candidate_entries_empty",
            "snippet_candidates_empty",
            "included_snippet_entries_empty",
        ],
        "query_summary": {
            "source": "latest_user_message",
            "term_hints": [],
            "term_hints_content_free": True,
            "query_hint_strategy": "mixed_fallback",
            "query_hint_count": 3,
            "content_free": True,
        },
        "retrieval_query_private": {
            "schema_version": "relaylm.retrieval_query_private_hints.v0",
            "runtime_private": True,
            "content_free": False,
            "source": "retrieval_query_analyzer",
            "backend_private_hints": ["RelayLM MVP評価", "合言葉", "青い灯台"],
            "query_hint_count": 3,
        },
        "selected_mem_candidates": [],
    }


def disabled_store_no_selected_candidates_artifact() -> dict[str, object]:
    blocked = no_selected_candidates_artifact()
    blocked["fallback_reason"] = "memory_store_disabled"
    blocked["store_diagnostics"] = {
        "schema_version": "relaymem.store_diagnostics.v0",
        "diagnostics_only": True,
        "store_enabled": False,
        "fallback_reason": "memory_store_disabled",
    }
    return blocked


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
        passphrase_memory_id = form_primary_memory(
            scoped,
            namespace=NAMESPACE,
            candidate_id="e1r5-blue-lighthouse",
            title="RelayLM MVP評価の合言葉",
            summary=PASSPHRASE_SUMMARY,
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

        no_candidate_bridged = apply_relaymem_primary_recall_scope(
            no_selected_candidates_artifact(),
            scoped_store_root=str(scoped),
            expected_namespace=NAMESPACE,
            max_snippet_chars=512,
            max_snippet_candidates=3,
            snippet_budget=512,
        )
        no_candidate_runtime = no_candidate_bridged["primary_recall_runtime"]
        no_candidate_projection = no_candidate_bridged["primary_recall_projection"]
        require(no_candidate_bridged["query_summary"]["term_hints"] == [], no_candidate_bridged)
        require(no_candidate_bridged["query_summary"]["content_free"] is True, no_candidate_bridged)
        require(no_candidate_runtime["primary_candidate_discovery_attempted"] is True, no_candidate_runtime)
        require(no_candidate_runtime["primary_candidate_count"] > 0, no_candidate_runtime)
        require(no_candidate_runtime["selected_count"] == 1, no_candidate_runtime)
        require(no_candidate_projection["primary_candidate_discovery_attempted"] is True, no_candidate_projection)
        require(no_candidate_projection["primary_candidate_count"] > 0, no_candidate_projection)
        require(no_candidate_projection["selected_count"] == 1, no_candidate_projection)
        require(no_candidate_projection["grounding_enabled"] is True, no_candidate_projection)
        require(no_candidate_projection["grounded_item_count"] == 1, no_candidate_projection)
        require(no_candidate_bridged["snippet_apply_decision"] == "eligible_but_not_applied", no_candidate_bridged)
        require("primary_candidate_query_terms_missing" not in no_candidate_runtime["blocked_reason_ids"], no_candidate_runtime)
        require("primary_recall_no_scoped_match" not in no_candidate_runtime["blocked_reason_ids"], no_candidate_runtime)
        require("existing_retrieval_gate_blocked" not in no_candidate_runtime["blocked_reason_ids"], no_candidate_runtime)
        require("青い灯台" in json.dumps(no_candidate_runtime, ensure_ascii=False), no_candidate_runtime)

        disabled_store_bridged = apply_relaymem_primary_recall_scope(
            disabled_store_no_selected_candidates_artifact(),
            scoped_store_root=str(scoped),
            expected_namespace=NAMESPACE,
            max_snippet_chars=512,
            max_snippet_candidates=3,
            snippet_budget=512,
        )
        disabled_runtime = disabled_store_bridged["primary_recall_runtime"]
        disabled_projection = disabled_store_bridged["primary_recall_projection"]
        require(disabled_runtime["primary_candidate_discovery_attempted"] is False, disabled_runtime)
        require(disabled_runtime["primary_candidate_count"] == 0, disabled_runtime)
        require(disabled_runtime["selected_count"] == 0, disabled_runtime)
        require("memory_store_disabled" in disabled_runtime["blocked_reason_ids"], disabled_runtime)
        require("primary_recall_no_scoped_match" in disabled_runtime["blocked_reason_ids"], disabled_runtime)
        require(disabled_projection["grounding_enabled"] is False, disabled_projection)
        require(disabled_projection["grounded_item_count"] == 0, disabled_projection)
        require(disabled_store_bridged["snippet_apply_decision"] == "blocked_no_candidates", disabled_store_bridged)

        public = json.dumps(
            [projection, no_candidate_projection, disabled_projection],
            ensure_ascii=False,
        )
        for forbidden in (
            SUMMARY,
            PASSPHRASE_SUMMARY,
            "浅煎り",
            "エチオピア",
            "青い灯台",
            str(scoped),
            str(configured_root),
            memory_id,
            passphrase_memory_id,
        ):
            require(forbidden not in public, ("public leak", forbidden, public))
        for flag in (
            "evidence_content_included",
            "runtime_private_evidence_omitted",
            "path_values_included",
            "digest_values_included",
        ):
            require(flag in projection, projection)
            require(flag in no_candidate_projection, no_candidate_projection)
            require(flag in disabled_projection, disabled_projection)

    print("E1-R5 Primary MEM recall candidate bridge smoke passed")


if __name__ == "__main__":
    main()
