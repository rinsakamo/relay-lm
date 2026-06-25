"""Shared Correct/Forget mutation fence smoke."""
from __future__ import annotations

from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_mutation_coordinator import (
    inspect_primary_memory_operations,
    primary_memory_mutation_lock_path,
)
from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
)


def expect_code(call, code: str) -> None:
    try:
        call()
    except (PrimaryCorrectionError, PrimaryForgetError) as exc:
        require(exc.code == code, (exc.code, code))
    else:
        raise AssertionError(f"expected {code}")


def main() -> None:
    with prepared_store() as (root, memory_id):
        lock_path = primary_memory_mutation_lock_path(root, memory_id)
        require(
            lock_path
            == root / "memory" / "mem" / "corrections" / "v0" / memory_id / ".lock",
            lock_path,
        )
        require(not lock_path.exists(), "read-only lock lookup created file")

        correct = preflight_primary_memory_correction(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            corrected_title="好きな飲み物",
            corrected_summary="好きな飲み物はコーヒーです。",
            reason="訂正要求",
            operation_id="shared-op",
        )
        expect_code(
            lambda: apply_primary_memory_correction(
                store_root=str(root),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                operation_id="shared-op",
                apply_token=correct["apply_token"],
                fault_at="after_audit_prepared",
            ),
            "reconciliation_required",
        )
        require(lock_path.is_file(), lock_path)
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(not inspection.corrupt, inspection)
        require(len(inspection.pending) == 1, inspection)
        require(inspection.pending[0].operation_kind == "correct", inspection)

        expect_code(
            lambda: preflight_primary_memory_forget(
                store_root=str(root),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                expected_lifecycle_state="active",
                reason="今後の通常検索から除外する",
                operation_id="forget-different-op",
            ),
            "operation_conflict",
        )
        expect_code(
            lambda: preflight_primary_memory_forget(
                store_root=str(root),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                expected_lifecycle_state="active",
                reason="今後の通常検索から除外する",
                operation_id="shared-op",
            ),
            "operation_conflict",
        )
        locks = list(root.rglob(".lock"))
        require(locks == [lock_path], locks)

    print("Phase I-4B Primary shared mutation fence smoke passed")


if __name__ == "__main__":
    main()
