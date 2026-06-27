"""I-5A Correct/Forget interaction smoke for read-only Pin / Unpin tokens."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_correction import apply_primary_memory_correction, preflight_primary_memory_correction
from relaylm.relaymem_primary_forget import apply_primary_memory_forget_hidden_successor, preflight_primary_memory_forget
from relaylm.relaymem_primary_pin import (
    PrimaryPinError,
    preflight_primary_memory_pin,
    preflight_primary_memory_unpin,
    validate_primary_memory_pin_token,
    validate_primary_memory_unpin_token,
)

NOW = datetime(2026, 6, 27, 2, 0, tzinfo=timezone.utc)
PIN_REASON = "評価中は優先候補として扱う契約を確認するため"
UNPIN_REASON = "優先候補契約を外す前提を確認するため"
FORGET_REASON = "通常検索から外すため"


def _expect(code: set[str], fn) -> None:
    try:
        fn()
    except PrimaryPinError as exc:
        require(exc.code in code, exc.code)
    else:
        raise AssertionError(f"expected one of {sorted(code)}")


def pin_token_becomes_stale_after_correct_apply() -> None:
    with prepared_store() as (root, memory_id):
        pin = preflight_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-before-correct", now=NOW)
        correction = preflight_primary_memory_correction(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, corrected_title="好きな飲み物（訂正）", corrected_summary="好きな飲み物は緑茶です。", reason="内容を訂正するため", operation_id="phase-i5a-correct-after-pin", now=NOW)
        apply_primary_memory_correction(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, operation_id="phase-i5a-correct-after-pin", apply_token=correction["apply_token"], now=NOW)
        _expect({"stale_revision"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-before-correct", apply_token=pin["apply_token"], now=NOW))


def unpin_token_becomes_stale_after_forget_apply() -> None:
    with prepared_store() as (root, memory_id):
        unpin = preflight_primary_memory_unpin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5a-unpin-before-forget", now=NOW)
        forget = preflight_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5a-forget-after-unpin", now=NOW)
        apply_primary_memory_forget_hidden_successor(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5a-forget-after-unpin", apply_token=forget["apply_token"], now=NOW)
        _expect({"stale_revision", "target_not_active"}, lambda: validate_primary_memory_unpin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5a-unpin-before-forget", apply_token=unpin["apply_token"], now=NOW))


def pending_forget_blocks_pin_token_validation() -> None:
    with prepared_store() as (root, memory_id):
        pin = preflight_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-before-pending", now=NOW)
        forget = preflight_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5a-forget-pending", now=NOW)
        try:
            apply_primary_memory_forget_hidden_successor(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5a-forget-pending", apply_token=forget["apply_token"], now=NOW, fault_at="after_prepared_publication")
        except Exception:
            pass
        _expect({"operation_conflict", "recovery_required", "stale_revision"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-before-pending", apply_token=pin["apply_token"], now=NOW))


def main() -> None:
    pin_token_becomes_stale_after_correct_apply()
    unpin_token_becomes_stale_after_forget_apply()
    pending_forget_blocks_pin_token_validation()
    print("Phase I-5A Pin/Unpin concurrency smoke passed")


if __name__ == "__main__":
    main()
