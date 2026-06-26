"""Shared support for Phase I-4D retrieval smokes."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, require
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_recall import apply_relaymem_primary_recall_scope

NOW = datetime(2026, 6, 27, tzinfo=timezone.utc)
FORGOTTEN = "I4D_FORGOTTEN_CONTENT"
UNRELATED = "I4D_UNRELATED_ACTIVE"
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
    value = preflight_primary_memory_forget(
        store_root=str(root),
        character_id=CHARACTER,
        namespace=NAMESPACE,
        memory_id=memory_id,
        expected_revision=revision,
        expected_lifecycle_state="active",
        reason=REASON,
        operation_id=operation_id,
        now=NOW,
    )
    return str(value["apply_token"])


def apply_forget(
    root,
    memory_id: str,
    operation_id: str,
    token: str,
    revision: int,
    fault_at=None,
):
    return apply_primary_memory_forget(
        store_root=str(root),
        character_id=CHARACTER,
        namespace=NAMESPACE,
        memory_id=memory_id,
        expected_revision=revision,
        expected_lifecycle_state="active",
        reason=REASON,
        operation_id=operation_id,
        apply_token=token,
        now=NOW,
        fault_at=fault_at,
    )


def expect_fault(callable_) -> None:
    try:
        callable_()
    except PrimaryForgetError as exc:
        require(exc.code in {"reconciliation_required", "response_lost"}, exc.code)
    else:
        raise AssertionError("expected fault seam")
