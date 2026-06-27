"""Phase I-4F race/concurrency product validation smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_correction import PrimaryCorrectionError, apply_primary_memory_correction, preflight_primary_memory_correction
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import PrimaryForgetError, apply_primary_memory_forget, preflight_primary_memory_forget
from relaylm_phase_i4c2_primary_forget_concurrency_smoke import main as i4c2_concurrency_main

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
REASON = "I4F_CONCURRENCY_REASON"


def issue_forget(root, memory_id: str, operation_id: str) -> str:
    return str(preflight_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=REASON, operation_id=operation_id, now=NOW)["apply_token"])


def apply_forget(root, memory_id: str, operation_id: str, token: str):
    return apply_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=REASON, operation_id=operation_id, apply_token=token, now=NOW)


def issue_correct(root, memory_id: str, operation_id: str) -> str:
    return str(preflight_primary_memory_correction(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, corrected_title="I4F corrected title", corrected_summary="I4F corrected summary", reason="I4F correction reason", operation_id=operation_id, now=NOW)["apply_token"])


def apply_correct(root, memory_id: str, operation_id: str, token: str):
    return apply_primary_memory_correction(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, operation_id=operation_id, apply_token=token, now=NOW)


def require_error(callable_, allowed: set[str]) -> None:
    try:
        callable_()
    except (PrimaryForgetError, PrimaryCorrectionError) as exc:
        require(exc.code in allowed, exc.code)
        require(str(exc) == exc.code, str(exc))
    else:
        raise AssertionError("expected bounded stale/conflict failure")


def correct_preflight_then_forget_wins() -> None:
    with prepared_store() as (root, memory_id):
        correct_token = issue_correct(root, memory_id, "i4f-correct-stale")
        forget_token = issue_forget(root, memory_id, "i4f-forget-winner")
        result = apply_forget(root, memory_id, "i4f-forget-winner", forget_token)
        require(result.status == "applied", result)
        require_error(lambda: apply_correct(root, memory_id, "i4f-correct-stale", correct_token), {"stale_revision", "operation_conflict", "target_not_active"})
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.lifecycle_state == "hidden" and state.retrieval_eligible is False, state)


def forget_preflight_then_correct_wins() -> None:
    with prepared_store() as (root, memory_id):
        forget_token = issue_forget(root, memory_id, "i4f-forget-stale")
        correct_token = issue_correct(root, memory_id, "i4f-correct-winner")
        correction = apply_correct(root, memory_id, "i4f-correct-winner", correct_token)
        require(correction.get("status") == "applied", correction)
        require_error(lambda: apply_forget(root, memory_id, "i4f-forget-stale", forget_token), {"stale_revision", "operation_conflict", "target_not_active"})
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.lifecycle_state == "active" and state.current_revision == 2, state)


def hidden_target_rejects_new_mutation() -> None:
    with prepared_store() as (root, memory_id):
        token = issue_forget(root, memory_id, "i4f-hide-target")
        result = apply_forget(root, memory_id, "i4f-hide-target", token)
        require(result.status == "applied", result)
        require_error(lambda: preflight_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=2, expected_lifecycle_state="active", reason=REASON, operation_id="i4f-hidden-repeat", now=NOW), {"target_not_active", "already_hidden", "stale_revision"})
        require_error(lambda: preflight_primary_memory_correction(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=2, corrected_title="hidden target", corrected_summary="hidden target", reason="hidden target correction", operation_id="i4f-hidden-correct", now=NOW), {"target_not_active", "stale_revision", "operation_conflict"})


def main() -> None:
    correct_preflight_then_forget_wins()
    forget_preflight_then_correct_wins()
    hidden_target_rejects_new_mutation()
    i4c2_concurrency_main()
    print("Phase I-4F Forget concurrency validation smoke passed")


if __name__ == "__main__":
    main()
