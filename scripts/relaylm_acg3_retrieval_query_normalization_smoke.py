from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.analyzer_governance import can_open_runtime_policy
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact
from relaylm.relaymem_store import build_relaymem_store_diagnostics
from relaylm.retrieval_query_analyzer import (
    analyze_retrieval_query,
    public_retrieval_query_projection,
    retrieval_query_backend_hints,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _scene_artifact(scene_type: str = "design_talk", scope: str = "project_context") -> dict[str, Any]:
    return {
        "scene_state": {"scene_type": scene_type, "confidence": 0.95, "stability": 0.9},
        "scene_policy": {"relaymem_retrieval_scope": scope},
        "persistence_block": scene_type in {"recovery", "formal_document", "medical_or_safety"},
        "persistence_block_reasons": [f"scene_type_is_{scene_type}"] if scene_type == "recovery" else [],
    }


def _build_store(root: Path) -> None:
    projects = root / "memory" / "mem" / "projects"
    projects.mkdir(parents=True)
    (root / "memory" / "mem" / "index.md").write_text("# Index\nRelayMEM\n", encoding="utf-8")
    (root / "memory" / "mem" / "log.md").write_text("# Log\n", encoding="utf-8")
    (projects / "english.md").write_text(
        "# RelayMEM retrieval design\nRelayMEM retrieval normalization English page.\n",
        encoding="utf-8",
    )
    (projects / "japanese.md").write_text(
        "# エチオピアコーヒー\n朝の集中作業とエチオピアコーヒーの記憶。\n",
        encoding="utf-8",
    )


def _store_diagnostics(store_root: Path) -> dict[str, Any]:
    return build_relaymem_store_diagnostics(
        root_path=str(store_root),
        store_enabled=True,
        retrieval_dry_run_only=True,
    )


def _retrieval_for(
    *,
    store_root: Path,
    content: str,
    scene_type: str = "design_talk",
    relayref_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scope = "current_context_only" if scene_type == "recovery" else "project_context"
    return build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=_scene_artifact(scene_type, scope),
        relayref_artifact=relayref_artifact,
        messages=[{"role": "user", "content": content}],
        store_diagnostics=_store_diagnostics(store_root),
        max_candidates=4,
        ctx_block_apply_enabled=True,
        snippet_extraction_enabled=True,
    )


def _assert_public_projection_content_free(public: dict[str, Any], raw_text: str, private_hints: list[str]) -> None:
    public_text = _serialized(public)
    require(public.get("content_free") is True, public)
    require(raw_text not in public_text, public_text)
    for hint in private_hints:
        require(hint not in public_text, public_text)
    for forbidden_key in (
        "raw_text",
        "raw_user_text",
        "user_text",
        "memory_text",
        "bounded_ngram_hints",
        "structured_terms",
        "backend_private_hints",
    ):
        require(forbidden_key not in public_text, public_text)


def main() -> int:
    english = analyze_retrieval_query("RelayMEM retrieval design")
    english_hints = retrieval_query_backend_hints(english)
    english_public = public_retrieval_query_projection(english)
    require("RelayMEM" in english_hints, english)
    require("retrieval" in english_hints, english)
    require(english_public["query_hint_strategy"] == "whitespace_fallback", english_public)
    require(english_public["query_hint_count"] >= 2, english_public)
    print("ok existing English query hints remain available")

    japanese_text = "エチオピアコーヒー覚えてる？"
    japanese = analyze_retrieval_query(japanese_text)
    japanese_hints = retrieval_query_backend_hints(japanese)
    japanese_public = public_retrieval_query_projection(japanese)
    require(japanese_hints, japanese)
    require(0 < japanese_public["query_hint_count"] <= 6, japanese_public)
    require(
        japanese_public["query_hint_strategy"] in {"mixed_fallback", "bounded_ngram_fallback"},
        japanese_public,
    )
    _assert_public_projection_content_free(japanese_public, japanese_text, japanese_hints)
    print("ok Japanese no-whitespace query produces bounded private hints")

    multilingual_text = "集中作業coffee覚えてる"
    multilingual = analyze_retrieval_query(multilingual_text)
    multilingual_hints = retrieval_query_backend_hints(multilingual)
    require(multilingual_hints, multilingual)
    require(len(multilingual_hints) <= 6, multilingual_hints)
    require(all(2 <= len(hint) <= 32 for hint in multilingual_hints), multilingual_hints)
    _assert_public_projection_content_free(
        public_retrieval_query_projection(multilingual),
        multilingual_text,
        multilingual_hints,
    )
    print("ok no-whitespace multilingual hints are bounded and backend-private")

    for source in ("heuristic", "fallback_regex", "locale_marker"):
        candidate = analyze_retrieval_query("RelayMEM retrieval", source=source)
        public = public_retrieval_query_projection(candidate)
        require(candidate["source_authoritative"] is False, candidate)
        require(candidate["restrictive_only"] is True, candidate)
        require(can_open_runtime_policy(candidate["governance"]) is False, candidate)
        require(public["can_open_runtime_policy"] is False, public)
    print("ok fallback sources cannot open broad/update runtime policy")

    unknown_strategy = analyze_retrieval_query(
        "RelayMEM retrieval",
        query_hint_strategy="open_broad_retrieval",
    )
    unknown_public = public_retrieval_query_projection(unknown_strategy)
    require(retrieval_query_backend_hints(unknown_strategy) == [], unknown_strategy)
    require(unknown_public["query_hint_strategy"] == "unknown", unknown_public)
    require(
        "unknown_query_hint_strategy" in unknown_public["validation_error_ids"],
        unknown_public,
    )
    require(unknown_public["can_open_runtime_policy"] is False, unknown_public)
    print("ok unknown hint strategy fails closed")

    with tempfile.TemporaryDirectory() as td:
        store_root = Path(td)
        _build_store(store_root)

        raw_secret = "SECRET_PRIVATE_QUERY エチオピアコーヒー"
        artifact = _retrieval_for(store_root=store_root, content=raw_secret)
        query_summary = artifact["query_summary"]
        retrieval_query_public = artifact["retrieval_query_candidate"]
        retrieval_query_private = artifact["retrieval_query_private"]
        require(query_summary["content_free"] is True, query_summary)
        require(query_summary["term_hints"] == [], query_summary)
        require(query_summary["query_hint_count"] > 0, query_summary)
        require(retrieval_query_public["content_free"] is True, retrieval_query_public)
        require(retrieval_query_private["runtime_private"] is True, retrieval_query_private)
        require(retrieval_query_private["content_free"] is False, retrieval_query_private)
        require(retrieval_query_private["backend_private_hints"], retrieval_query_private)
        require(
            len(retrieval_query_private["backend_private_hints"])
            == retrieval_query_private["query_hint_count"],
            retrieval_query_private,
        )
        combined_public = _serialized({"query_summary": query_summary, "retrieval_query_candidate": retrieval_query_public})
        require(raw_secret not in combined_public, combined_public)
        for forbidden in ("SECRET_PRIVATE_QUERY", "エチオピアコーヒー覚えてる？"):
            require(forbidden not in combined_public, combined_public)
        print("ok retrieval public diagnostics expose only counts while private hints are preserved")

        jp_retrieval = _retrieval_for(
            store_root=store_root,
            content="エチオピアコーヒー覚えてる？",
        )
        require(
            any(
                isinstance(candidate, dict) and candidate.get("reason") == "keyword_match"
                for candidate in jp_retrieval["selected_mem_candidates"]
            ),
            jp_retrieval,
        )
        require(jp_retrieval["apply_allowed"] is False, jp_retrieval)
        require(jp_retrieval["ctx_injection_plan"]["applied"] is False, jp_retrieval)
        print("ok no-whitespace retrieval can still produce bounded keyword matches")

        unresolved = _retrieval_for(
            store_root=store_root,
            content="それは何の話だった？",
            relayref_artifact={"unresolved_reference_detected": True},
        )
        require(unresolved["fallback_reason"] == "unresolved_reference_requires_confirmation", unresolved)
        require(unresolved["selected_mem_candidates"] == [], unresolved)
        require(unresolved["query_summary"]["ambiguous_reference_terms_present"] is True, unresolved)
        require(unresolved["apply_decision"] == "blocked_unresolved_reference", unresolved)
        print("ok ambiguous reference behavior remains restrictive")

        blocked = _retrieval_for(
            store_root=store_root,
            content="RelayMEM retrieval design",
            scene_type="formal_document",
        )
        require(blocked["fallback_reason"] == "external_memory_blocked_by_scene_policy", blocked)
        require(blocked["selected_mem_candidates"] == [], blocked)
        require(blocked["apply_allowed"] is False, blocked)
        require(blocked["ctx_block"] is None, blocked)
        require(blocked["ctx_injection_plan"]["applied"] is False, blocked)
        require(blocked["snippet_runtime_injection_plan"]["applied"] is False, blocked)
        print("ok scene/lifecycle protections are not bypassed by ACG-3 hints")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
