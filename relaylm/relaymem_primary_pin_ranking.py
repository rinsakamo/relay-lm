"""Phase I-5B bounded Pin-aware ranking helper for Primary MEM recall artifacts."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from .relaymem_primary_pin_apply import load_primary_pin_state_index

RANKING_SCHEMA = "relaylm.mem.primary_pin_ranking.v0"


def apply_primary_pin_priority_to_candidates(
    retrieval_artifact: Mapping[str, Any] | None,
    *,
    store_root: str,
    namespace: str,
) -> dict[str, Any]:
    """Return a deterministic Pin-prioritized order for already selected candidates.

    This is a ranking hint only. It never makes an ineligible memory eligible;
    callers must still apply lifecycle/current-state retrieval gates before
    constructing RelayCTX snippets.
    """

    artifact = deepcopy(dict(retrieval_artifact or {}))
    raw_candidates = artifact.get("selected_mem_candidates")
    candidates = list(raw_candidates) if isinstance(raw_candidates, Sequence) and not isinstance(raw_candidates, (str, bytes, bytearray)) else []
    try:
        index = load_primary_pin_state_index(store_root, namespace=namespace)
    except Exception:
        artifact["primary_pin_ranking"] = {
            "schema_version": RANKING_SCHEMA,
            "applied": False,
            "ranking_hint_only": True,
            "eligible_count": 0,
            "pinned_candidate_count": 0,
            "blocked_reason_ids": ["primary_pin_state_unavailable"],
            "content_included": False,
            "path_included": False,
            "operation_id_included": False,
        }
        return artifact

    decorated: list[tuple[int, int, object]] = []
    pinned_count = 0
    eligible_count = 0
    for position, candidate in enumerate(candidates):
        pinned = False
        if isinstance(candidate, Mapping) and candidate.get("memory_layer") == "primary":
            memory_id = candidate.get("idempotency_key")
            if isinstance(memory_id, str) and index.is_pinned(memory_id):
                pinned = True
                pinned_count += 1
            eligible_count += 1
        decorated.append((0 if pinned else 1, position, candidate))
    decorated.sort(key=lambda item: (item[0], item[1]))
    artifact["selected_mem_candidates"] = [item[2] for item in decorated]
    artifact["primary_pin_ranking"] = {
        "schema_version": RANKING_SCHEMA,
        "applied": True,
        "ranking_hint_only": True,
        "eligible_count": eligible_count,
        "pinned_candidate_count": pinned_count,
        "deterministic_tie_break": "pinned_before_original_order",
        "blocked_reason_ids": list(index.bounded_reason_ids),
        "content_included": False,
        "path_included": False,
        "operation_id_included": False,
        "reason_included": False,
        "token_included": False,
    }
    return artifact


__all__ = ["RANKING_SCHEMA", "apply_primary_pin_priority_to_candidates"]
