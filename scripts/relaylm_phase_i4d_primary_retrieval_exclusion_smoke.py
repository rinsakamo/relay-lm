"""Phase I-4D lifecycle-aware Primary retrieval exclusion smoke."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from _relaylm_phase_i3_test_support import form_primary_memory
from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_correction import (
    apply_primary_memory_correction,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget,
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_recall import apply_relaymem_primary_recall_scope
from relaylm.relaymem_primary_retrieval_eligibility import (
    load_primary_retrieval_eligibility_index,
)

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
FORGOTTEN = "好きな飲み物は紅茶です。"
UNRELATED = "好きな色は青です。"
REASON = "I4D_FORGET_REASON_CANARY"


def artifact(paths: list[str]) -> dict:
    return {
        "scene_type": "design_talk",
        "retrieval_scope": "current_context_only",
        "snippet_apply_decision": "eligible_but_not_applied",
        "selected_mem_candidates": [
            {"path": path, "memory_layer": "primary", "reason": "keyword_match"}
            for path in paths
        ],
    }


def recall(root, paths: list[str]) -> dict:
    return apply_relaymem_primary_recall_scope(
        artifact(paths),
        scoped_store_root=str(root),
        expected_namespace=NAMESPACE,
        max_snippet_chars=512,
        max_snippet_candidates=8,
        snippet_budget=512,
    )


def issue(root, memory_id: str, operation_id: str, revision: int) -> str:
    return str(preflight_primary_memory_forget(
        store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
        memory_id=memory_id, expected_revision=revision,
        expected_lifecycle_state="active", reason=REASON,
        operation_id=operation_id, now=NOW,
    )["apply_token"])


def apply_forget(root, memory_id: str, operation_id: str, token: str, revision: int, fault_at=None):
    return apply_primary_memory_forget(
        store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
        memory_id=memory_id, expected_revision=revision,
        expected_lifecycle_state="active", reason=REASON,
        operation_id=operation_id, apply_token=token, now=NOW, fault_at=fault_at,
    )


def expect_fault(callable_) -> None:
    try:
        callable_()
    except PrimaryForgetError as exc:
        require(exc.code in {"reconciliation_required", "response_lost"}, exc.code)
    else:
        raise AssertionError("expected fault seam")


def active_corrected_and_finalized() -> None:
    with prepared_store() as (root, memory_id):
        initial = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        selected = recall(root, [initial.relative_path])
        require(selected["primary_recall_runtime"]["selected_count"] == 1, selected)
        require(FORGOTTEN in json.dumps(selected, ensure_ascii=False), selected)

        correction = preflight_primary_memory_correction(
            store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
            memory_id=memory_id, expected_revision=1,
            corrected_title="好きな飲み物（訂正）",
            corrected_summary="好きな飲み物は緑茶です。",
            reason="I4D correction", operation_id="i4d-correct", now=NOW,
        )
        apply_primary_memory_correction(
            store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
            memory_id=memory_id, expected_revision=1, operation_id="i4d-correct",
            apply_token=str(correction["apply_token"]), now=NOW,
        )
        corrected = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(corrected.current_revision == 2, corrected)
        corrected_result = recall(root, [initial.relative_path, corrected.relative_path])
        runtime = corrected_result["primary_recall_runtime"]
        require(runtime["selected_count"] == 1, runtime)
        require(runtime["selected_memories"][0]["revision"] == 2, runtime)
        require("primary_recall_superseded_revision_excluded" in runtime["blocked_reason_ids"], runtime)

        unrelated_id = form_primary_memory(
            root, namespace=NAMESPACE, candidate_id="phase-i4d-unrelated",
            title="好きな色", summary=UNRELATED,
        )
        unrelated = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=unrelated_id)

        token = issue(root, memory_id, "i4d-forget-corrected", 2)
        result = apply_forget(root, memory_id, "i4d-forget-corrected", token, 2)
        require(result.status == "applied", result)
        hidden = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(hidden.lifecycle_state == "hidden", hidden)

        index = load_primary_retrieval_eligibility_index(root, namespace=NAMESPACE)
        require(index.evaluate(initial.current_physical_id).reason_id == "excluded_prior_revision", index)
        require(index.evaluate(corrected.current_physical_id).reason_id == "excluded_prior_revision", index)
        require(index.evaluate(hidden.current_physical_id).reason_id == "excluded_hidden", index)

        filtered = recall(root, [initial.relative_path, corrected.relative_path, unrelated.relative_path])
        runtime = filtered["primary_recall_runtime"]
        require(runtime["selected_count"] == 1, runtime)
        require(UNRELATED in runtime["selected_memories"][0]["summary"], runtime)
        serialized = json.dumps(filtered, ensure_ascii=False)
        require(FORGOTTEN not in serialized and "緑茶" not in serialized, serialized)
        require(REASON not in serialized and token not in serialized, serialized)
        for key in (
            "selected_mem_candidates", "snippet_candidates", "evidence_envelope",
            "ctx_block_snippet_candidate", "snippet_runtime_injection_plan",
        ):
            require("緑茶" not in json.dumps(filtered.get(key), ensure_ascii=False), key)


def prepared_and_recovery_states() -> None:
    with prepared_store() as (root, memory_id):
        active = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        token = issue(root, memory_id, "i4d-prepared", 1)
        expect_fault(lambda: apply_primary_memory_forget_hidden_successor(
            store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
            memory_id=memory_id, expected_revision=1,
            expected_lifecycle_state="active", reason=REASON,
            operation_id="i4d-prepared", apply_token=token, now=NOW,
            fault_at="after_prepared_publication",
        ))
        index = load_primary_retrieval_eligibility_index(root, namespace=NAMESPACE)
        require(index.evaluate(active.current_physical_id).reason_id == "excluded_prepared", index)
        require(recall(root, [active.relative_path])["primary_recall_runtime"]["selected_count"] == 0, root)

    with prepared_store() as (root, memory_id):
        active = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        token = issue(root, memory_id, "i4d-hidden-recovery", 1)
        expect_fault(lambda: apply_forget(
            root, memory_id, "i4d-hidden-recovery", token, 1,
            "after_hidden_successor_publish_before_reread",
        ))
        hidden = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(hidden.lifecycle_state == "hidden", hidden)
        index = load_primary_retrieval_eligibility_index(root, namespace=NAMESPACE)
        require(index.evaluate(hidden.current_physical_id).reason_id == "excluded_recovery_required", index)
        require(recall(root, [active.relative_path])["primary_recall_runtime"]["selected_count"] == 0, root)


def content_free_decisions() -> None:
    with prepared_store() as (root, memory_id):
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        index = load_primary_retrieval_eligibility_index(root, namespace=NAMESPACE)
        decision = index.evaluate(state.current_physical_id)
        require(decision.reason_id == "eligible_current_active", decision)
        public = repr(index) + repr(decision) + repr(decision.to_log_dict())
        for forbidden in (str(root), NAMESPACE, memory_id, state.current_physical_id, FORGOTTEN):
            require(forbidden not in public, forbidden)


def main() -> None:
    active_corrected_and_finalized()
    prepared_and_recovery_states()
    content_free_decisions()
    print("Phase I-4D Primary retrieval exclusion smoke passed")


if __name__ == "__main__":
    main()
