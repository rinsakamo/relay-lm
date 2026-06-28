"""E1-R5 Primary MEM recall bridge leakage and unsupported-detail smoke."""
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
OTHER_NAMESPACE = "character_other"
SUMMARY = "ユーザーは夜にRAYの天体という曲を聴くのが好きです。"
QUESTION = "天体をいつ初めて聴いた？"


def artifact(namespace_terms: list[str] | None = None) -> dict[str, object]:
    return {
        "scene_type": "design_talk",
        "retrieval_scope": "long_term_memory",
        "snippet_apply_decision": "eligible_but_not_applied",
        "query_summary": {
            "source": "latest_user_message",
            "term_hints": namespace_terms or ["天体", "初めて聴いた", "いつ"],
        },
        "selected_mem_candidates": [],
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
            candidate_id="e1r5-song",
            title="好きな曲",
            summary=SUMMARY,
        )

        bridged = apply_relaymem_primary_recall_scope(
            artifact(),
            scoped_store_root=str(scoped),
            expected_namespace=NAMESPACE,
            max_snippet_chars=512,
            max_snippet_candidates=3,
            snippet_budget=512,
        )
        runtime = bridged["primary_recall_runtime"]
        require(runtime["selected_count"] == 1, runtime)

        grounded = build_grounded_recall_context(
            retrieved_memories=runtime["selected_memories"],
            query_text=QUESTION,
            character_id=CHARACTER,
            namespace=NAMESPACE,
        )
        projection = grounded.to_log_dict()
        backend = json.dumps((grounded.grounded_recall_context or {}).get("backend_messages"), ensure_ascii=False)
        require(projection["status"] == "unsupported_detail_suppressed", projection)
        require("does not support" in backend, backend)
        for invented in ("2026", "6月", "June", "first heard on"):
            require(invented not in backend, ("invented detail", invented, backend))

        wrong_namespace = apply_relaymem_primary_recall_scope(
            artifact(["天体"]),
            scoped_store_root=str(scoped),
            expected_namespace=OTHER_NAMESPACE,
            max_snippet_chars=512,
            max_snippet_candidates=3,
            snippet_budget=512,
        )
        require(wrong_namespace["primary_recall_runtime"]["selected_count"] == 0, wrong_namespace)
        require(
            "primary_recall_no_scoped_match" in wrong_namespace["primary_recall_runtime"]["blocked_reason_ids"],
            wrong_namespace,
        )

        public_values = [bridged["primary_recall_projection"], projection, wrong_namespace["primary_recall_projection"]]
        public = json.dumps(public_values, ensure_ascii=False)
        for forbidden in (SUMMARY, "RAY", "天体", str(scoped), str(configured_root), memory_id, "page_digest", "lineage_fingerprint"):
            require(forbidden not in public, ("public leak", forbidden, public))

    print("E1-R5 Primary MEM recall bridge security smoke passed")


if __name__ == "__main__":
    main()
