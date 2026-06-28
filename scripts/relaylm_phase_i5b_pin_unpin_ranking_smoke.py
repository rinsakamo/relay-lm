"""Phase I-5B Pin / Unpin ranking hint smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i3_test_support import form_primary_memory
from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_pin_apply import (
    apply_primary_memory_pin,
    apply_primary_memory_unpin,
    preflight_primary_memory_pin_apply,
    preflight_primary_memory_unpin_apply,
)
from relaylm.relaymem_primary_pin_ranking import apply_primary_pin_priority_to_candidates

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
PIN_REASON = "ranking priority hint validation"
UNPIN_REASON = "ranking priority hint removal"


def artifact_for(first: str, second: str) -> dict[str, object]:
    return {
        "snippet_apply_decision": "eligible_but_not_applied",
        "selected_mem_candidates": [
            {"memory_layer": "primary", "idempotency_key": first, "reason": "keyword_match", "path": "memory/mem/semantic/first.md"},
            {"memory_layer": "primary", "idempotency_key": second, "reason": "keyword_match", "path": "memory/mem/semantic/second.md"},
        ],
    }


def main() -> None:
    with prepared_store() as (root, first_id):
        second_id = form_primary_memory(root, namespace=NAMESPACE, candidate_id="phase-i5b-ranking-second", title="second", summary="second summary")
        pin = preflight_primary_memory_pin_apply(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=second_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5b-ranking-pin", now=NOW)
        apply_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=second_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5b-ranking-pin", apply_token=pin["apply_token"], now=NOW)
        ranked = apply_primary_pin_priority_to_candidates(artifact_for(first_id, second_id), store_root=str(root), namespace=NAMESPACE)
        require(ranked["selected_mem_candidates"][0]["idempotency_key"] == second_id, ranked)
        require(ranked["primary_pin_ranking"]["ranking_hint_only"] is True, ranked)
        require(ranked["primary_pin_ranking"]["pinned_candidate_count"] == 1, ranked)
        for forbidden in (PIN_REASON, "token_digest", "operation_id:", "physical_id:", "store_root"):
            require(forbidden not in str(ranked), forbidden)
        require(ranked["primary_pin_ranking"]["operation_id_included"] is False, ranked)
        unpin = preflight_primary_memory_unpin_apply(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=second_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5b-ranking-unpin", now=NOW)
        apply_primary_memory_unpin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=second_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5b-ranking-unpin", apply_token=unpin["apply_token"], now=NOW)
        restored = apply_primary_pin_priority_to_candidates(artifact_for(first_id, second_id), store_root=str(root), namespace=NAMESPACE)
        require(restored["selected_mem_candidates"][0]["idempotency_key"] == first_id, restored)
        require(restored["primary_pin_ranking"]["pinned_candidate_count"] == 0, restored)

    print("Phase I-5B Pin/Unpin ranking smoke passed")


if __name__ == "__main__":
    main()
