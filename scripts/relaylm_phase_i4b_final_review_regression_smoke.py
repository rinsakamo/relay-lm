"""Final-review regression smoke for recovery and token canonicality."""
from __future__ import annotations

from datetime import datetime, timezone

from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    preflight_primary_memory_forget,
    validate_primary_memory_forget_token,
)
from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
)


def main() -> None:
    with prepared_store() as (root, memory_id):
        preflight = preflight_primary_memory_correction(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            corrected_title="好きな飲み物",
            corrected_summary="好きな飲み物は水です。",
            reason="回復状態を検証するため",
            operation_id="phase-i4b-recovery-required",
        )
        try:
            apply_primary_memory_correction(
                store_root=str(root),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                operation_id="phase-i4b-recovery-required",
                apply_token=str(preflight["apply_token"]),
                fault_at="after_audit_prepared",
            )
        except PrimaryCorrectionError as exc:
            require(exc.code == "reconciliation_required", exc.code)
        else:
            raise AssertionError("prepared recovery fault did not fire")

        state = resolve_primary_current_state(
            root,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
        )
        require(state.mutation_state == "recovery_required", state)
        require(state.retrieval_eligible is False, state)
        require(
            "primary_mutation_recovery_required" in state.bounded_reason_ids,
            state,
        )

    issued = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
    with prepared_store() as (root, memory_id):
        kwargs = {
            "store_root": str(root),
            "character_id": CHARACTER,
            "namespace": NAMESPACE,
            "memory_id": memory_id,
            "expected_revision": 1,
            "expected_lifecycle_state": "active",
            "reason": "通常検索から除外する",
            "operation_id": "phase-i4b-canonical-token",
        }
        result = preflight_primary_memory_forget(**kwargs, now=issued)
        token = str(result["apply_token"])
        payload_part, signature_part = token.split(".", 1)
        noncanonical = f"{payload_part}=.{signature_part}"
        try:
            validate_primary_memory_forget_token(
                **kwargs,
                apply_token=noncanonical,
                now=issued,
            )
        except PrimaryForgetError as exc:
            require(exc.code == "token_invalid", exc.code)
        else:
            raise AssertionError("noncanonical token encoding accepted")

        validated = validate_primary_memory_forget_token(
            **kwargs,
            apply_token=token,
            now=issued,
        )
        require(validated["valid"] is True, validated)

    print("Phase I-4B final-review regression smoke passed")


if __name__ == "__main__":
    main()
