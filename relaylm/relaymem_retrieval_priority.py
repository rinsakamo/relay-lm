"""RelayMEM retrieval candidate priority helpers.

This module is intentionally helper-only. It does not read memory files, write
memory, mutate RelaySOUL, or inject anything into runtime prompts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_SCHEMA_VERSION = "relaymem.retrieval_priority.v0"

# Higher scores win. Scores intentionally keep wide gaps between memory layers so
# bounded tie-breakers cannot accidentally make raw/legacy evidence outrank
# stable secondary MEM.
_LAYER_BASE_SCORES = {
    "secondary": 900,
    "primary": 700,
    "legacy_flat": 400,
    "unknown": 0,
}

_PATH_TIER_SCORES = (
    ("memory/mem/secondary/summaries/", "secondary_summary", 120),
    ("memory/mem/secondary/relations/", "secondary_relation", 110),
    ("memory/mem/secondary/projects/", "secondary_project", 100),
    ("memory/mem/secondary/concepts/", "secondary_concept", 90),
    ("memory/mem/secondary/claims/", "secondary_claim", 80),
    ("memory/mem/primary/relationships/", "primary_relationship", 60),
    ("memory/mem/primary/projects/", "primary_project", 50),
    ("memory/mem/primary/scenes/", "primary_scene", 40),
    ("memory/mem/primary/sessions/", "primary_session", 30),
    ("memory/mem/summaries/", "legacy_summary", 20),
    ("memory/mem/relations/", "legacy_relation", 15),
    ("memory/mem/projects/", "legacy_project", 10),
    ("memory/mem/concepts/", "legacy_concept", 5),
)

_REASON_SCORES = {
    "keyword_match": 50,
    "store_page_available": 0,
}


def prioritize_relaymem_candidates(
    candidates: Sequence[Mapping[str, Any]] | None,
    *,
    max_candidates: int | None = None,
) -> dict[str, Any]:
    """Rank RelayMEM candidates without exposing content in the projection.

    The returned ``selected_candidates`` may contain runtime-private path metadata
    copied from the input candidates. The ``selection_projection`` is designed for
    content-free diagnostics and intentionally omits paths, snippets, and text.
    """

    raw_candidates = [item for item in candidates or [] if isinstance(item, Mapping)]
    annotated: list[dict[str, Any]] = []
    for original_index, candidate in enumerate(raw_candidates):
        annotated_candidate = dict(candidate)
        priority = _priority_for_candidate(candidate, original_index=original_index)
        annotated_candidate.update(priority["candidate_fields"])
        annotated.append(annotated_candidate)

    annotated.sort(key=_candidate_sort_key)
    limit = _normalize_limit(max_candidates)
    selected = annotated[:limit] if limit is not None else annotated

    return {
        "schema_version": _SCHEMA_VERSION,
        "diagnostics_only": True,
        "read_only": True,
        "writes_memory": False,
        "mutates_soul": False,
        "candidate_count": len(raw_candidates),
        "selected_count": len(selected),
        "selection_policy": {
            "layer_order": ["secondary", "primary", "legacy_flat", "unknown"],
            "tie_breaker": "original_candidate_order",
            "path_tiers_enabled": True,
            "keyword_match_bonus_enabled": True,
        },
        "layer_counts": _layer_counts(annotated),
        "selected_layer_counts": _layer_counts(selected),
        "selected_candidates": selected,
        "selection_projection": _content_free_projection(selected),
    }


def _normalize_limit(max_candidates: int | None) -> int | None:
    if max_candidates is None:
        return None
    return max(0, int(max_candidates))


def _priority_for_candidate(
    candidate: Mapping[str, Any],
    *,
    original_index: int,
) -> dict[str, Any]:
    memory_layer = _memory_layer(candidate)
    path = str(candidate.get("path", ""))
    tier, tier_score = _path_tier(path, memory_layer)
    reason = str(candidate.get("reason", "store_page_available"))
    layer_score = _LAYER_BASE_SCORES.get(memory_layer, _LAYER_BASE_SCORES["unknown"])
    reason_score = _REASON_SCORES.get(reason, 0)
    score = layer_score + tier_score + reason_score
    return {
        "candidate_fields": {
            "retrieval_rank": None,
            "retrieval_priority_score": score,
            "retrieval_priority_tier": tier,
            "retrieval_priority_reasons": _priority_reasons(
                memory_layer=memory_layer,
                tier=tier,
                reason=reason,
            ),
            "retrieval_original_index": original_index,
        }
    }


def _memory_layer(candidate: Mapping[str, Any]) -> str:
    value = candidate.get("memory_layer")
    if value in {"secondary", "primary", "legacy_flat", "unknown"}:
        return str(value)
    path = str(candidate.get("path", ""))
    if path.startswith("memory/mem/secondary/"):
        return "secondary"
    if path.startswith("memory/mem/primary/"):
        return "primary"
    if path.startswith("memory/mem/"):
        return "legacy_flat"
    return "unknown"


def _path_tier(path: str, memory_layer: str) -> tuple[str, int]:
    for prefix, tier, score in _PATH_TIER_SCORES:
        if path.startswith(prefix):
            return tier, score
    return f"{memory_layer}_generic", 0


def _priority_reasons(*, memory_layer: str, tier: str, reason: str) -> list[str]:
    reasons = [f"memory_layer:{memory_layer}", f"tier:{tier}"]
    if reason in _REASON_SCORES:
        reasons.append(f"selection_reason:{reason}")
    else:
        reasons.append("selection_reason:other")
    return reasons


def _candidate_sort_key(candidate: Mapping[str, Any]) -> tuple[int, int]:
    score = candidate.get("retrieval_priority_score")
    original_index = candidate.get("retrieval_original_index")
    return (
        -(score if isinstance(score, int) else 0),
        original_index if isinstance(original_index, int) else 0,
    )


def _layer_counts(candidates: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {"secondary": 0, "primary": 0, "legacy_flat": 0, "unknown": 0}
    for candidate in candidates:
        layer = _memory_layer(candidate)
        counts[layer if layer in counts else "unknown"] += 1
    return counts


def _content_free_projection(candidates: Sequence[dict[str, Any]]) -> dict[str, Any]:
    selected: list[dict[str, Any]] = []
    for rank, candidate in enumerate(candidates):
        candidate["retrieval_rank"] = rank
        selected.append(
            {
                "rank": rank,
                "memory_layer": _memory_layer(candidate),
                "layout_profile": str(candidate.get("layout_profile", "unknown")),
                "priority_tier": str(candidate.get("retrieval_priority_tier", "unknown")),
                "priority_score": int(candidate.get("retrieval_priority_score", 0)),
                "reason_ids": [
                    str(item)
                    for item in candidate.get("retrieval_priority_reasons", [])
                ],
            }
        )
    return {
        "schema_version": "relaymem.retrieval_priority_projection.v0",
        "diagnostics_only": True,
        "content_included": False,
        "path_included": False,
        "snippet_included": False,
        "selected": selected,
    }
