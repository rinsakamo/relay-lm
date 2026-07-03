from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.relaymem_retrieval_priority import prioritize_relaymem_candidates
from relaylm.retrieval_query_analyzer import (
    analyze_retrieval_query,
    public_retrieval_query_projection,
    retrieval_query_backend_hints,
)

_SCHEMA_VERSION = "relaymem.retrieval_priority_runtime.v0"
_MAX_PRIORITY_DISCOVERY_CANDIDATES = 128


def install_relaymem_retrieval_priority_runtime(
    retrieval_module: Any | None = None,
) -> None:
    if retrieval_module is None:
        from relaylm import relaymem_retrieval as retrieval_module

    if getattr(retrieval_module, "_relaymem_m2b_priority_runtime_installed", False):
        return

    original_build = retrieval_module.build_relaymem_retrieval_dry_run_artifact

    def _select_mem_candidates_dry_run(
        *,
        fallback_reason: str,
        store_diagnostics: Mapping[str, Any] | None,
        query_terms: list[str],
        max_candidates: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        if fallback_reason not in retrieval_module._RETRIEVAL_ELIGIBLE_FALLBACK_REASONS:
            return [], []
        if not isinstance(store_diagnostics, Mapping):
            return [], []
        root_path = store_diagnostics.get("root_path")
        if not isinstance(root_path, str) or not root_path:
            return [], []

        final_limit = max(0, int(max_candidates))
        discovery_cap = _priority_discovery_cap(final_limit)
        discovery = retrieval_module.discover_relaymem_page_candidates(
            root_path=root_path,
            query_terms=query_terms,
            max_candidates=discovery_cap,
            max_scan=discovery_cap,
        )
        candidates: list[dict[str, Any]] = []
        for candidate in discovery.get("candidates", []):
            if not isinstance(candidate, Mapping):
                continue
            dry_run_candidate = dict(candidate)
            estimated_chars = dry_run_candidate.get("estimated_chars")
            dry_run_candidate["estimated_tokens"] = (
                max(1, int(estimated_chars) // 4)
                if isinstance(estimated_chars, int) and estimated_chars > 0
                else 0
            )
            dry_run_candidate["applied_to_ctx"] = False
            candidates.append(dry_run_candidate)

        prioritized = prioritize_relaymem_candidates(
            candidates,
            max_candidates=final_limit,
        )
        blocked = [
            {"path": str(item.get("path")), "reason": str(item.get("reason"))}
            for item in discovery.get("blocked_files", [])
            if isinstance(item, Mapping)
        ]
        discovery_reason = discovery.get("fallback_reason")
        if isinstance(discovery_reason, str) and discovery_reason not in {
            "memory_store_read_only_selection_dry_run",
        }:
            blocked.append({"reason": discovery_reason})
        return list(prioritized["selected_candidates"]), blocked

    def build_relaymem_retrieval_dry_run_artifact(
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        artifact = original_build(*args, **kwargs)
        messages = kwargs.get("messages")
        latest_user_text = _latest_user_text(
            messages if isinstance(messages, Sequence) and not isinstance(messages, str) else []
        )
        retrieval_query_candidate = analyze_retrieval_query(
            latest_user_text,
            source="heuristic",
        )
        backend_private_hints = retrieval_query_backend_hints(retrieval_query_candidate)
        artifact["query_summary"] = _content_free_query_summary(
            latest_user_text=latest_user_text,
            retrieval_query_candidate=retrieval_query_candidate,
        )
        artifact["retrieval_query_candidate"] = public_retrieval_query_projection(
            retrieval_query_candidate
        )
        artifact["retrieval_query_private"] = {
            "schema_version": "relaylm.retrieval_query_private_hints.v0",
            "runtime_private": True,
            "content_free": False,
            "source": "retrieval_query_analyzer",
            "backend_private_hints": tuple(backend_private_hints),
            "query_hint_count": len(backend_private_hints),
        }
        selected_mem_candidates = artifact.get("selected_mem_candidates")
        artifact["retrieval_priority"] = _runtime_priority_projection(
            selected_mem_candidates
            if isinstance(selected_mem_candidates, Sequence)
            and not isinstance(selected_mem_candidates, str)
            else []
        )
        return artifact

    retrieval_module._select_mem_candidates_dry_run = _select_mem_candidates_dry_run
    retrieval_module.build_relaymem_retrieval_dry_run_artifact = (
        build_relaymem_retrieval_dry_run_artifact
    )
    retrieval_module._relaymem_m2b_priority_runtime_installed = True


def _priority_discovery_cap(max_candidates: int) -> int:
    normalized = max(0, int(max_candidates))
    if normalized == 0:
        return 0
    return _MAX_PRIORITY_DISCOVERY_CANDIDATES


def _content_free_query_summary(
    *,
    latest_user_text: str,
    retrieval_query_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    projection = public_retrieval_query_projection(retrieval_query_candidate)
    return {
        "source": "latest_user_message",
        "input_chars": len(latest_user_text),
        "term_hints": [],
        "term_hints_content_free": True,
        "query_hint_strategy": projection["query_hint_strategy"],
        "query_hint_count": projection["query_hint_count"],
        "ambiguous_reference_terms_present": projection["has_ambiguous_reference"],
        "content_free": True,
    }


def _latest_user_text(messages: Sequence[Mapping[str, Any]]) -> str:
    for message in reversed(messages):
        if not isinstance(message, Mapping) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, Sequence) and not isinstance(content, str):
            parts: list[str] = []
            for item in content:
                if isinstance(item, Mapping) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
    return ""


def _runtime_priority_projection(
    selected_mem_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    prioritized = prioritize_relaymem_candidates(selected_mem_candidates)
    return {
        "schema_version": _SCHEMA_VERSION,
        "diagnostics_only": True,
        "read_only": True,
        "runtime_wiring": "dry_run_only",
        "source": "selected_mem_candidates",
        "content_included": False,
        "path_included": False,
        "snippet_included": False,
        "applied_to_ctx": False,
        "payload_mutation_allowed": False,
        "writes_memory": False,
        "mutates_soul": False,
        "candidate_count": prioritized["candidate_count"],
        "selected_count": prioritized["selected_count"],
        "selection_policy": prioritized["selection_policy"],
        "layer_counts": prioritized["layer_counts"],
        "selected_layer_counts": prioritized["selected_layer_counts"],
        "selection_projection": prioritized["selection_projection"],
    }
