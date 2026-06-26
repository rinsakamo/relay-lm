"""I-4C2 fault/restart forward-only convergence smoke."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget,
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
    recover_primary_memory_forget,
)
from relaylm.relaymem_primary_recall import _load_control_state

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
REASON = "I4C2_FAULT_REASON_CANARY"


def issue(root, memory_id: str, operation_id: str) -> str:
    return str(
        preflight_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason=REASON,
            operation_id=operation_id,
            now=NOW,
        )["apply_token"]
    )


def apply(root, memory_id: str, operation_id: str, token: str, fault: str | None = None):
    return apply_primary_memory_forget(
        store_root=str(root),
        character_id=CHARACTER,
        namespace=NAMESPACE,
        memory_id=memory_id,
        expected_revision=1,
        expected_lifecycle_state="active",
        reason=REASON,
        operation_id=operation_id,
        apply_token=token,
        now=NOW,
        fault_at=fault,
    )


def recover(root, memory_id: str, operation_id: str, fault: str | None = None):
    return recover_primary_memory_forget(
        store_root=str(root),
        namespace=NAMESPACE,
        memory_id=memory_id,
        operation_id=operation_id,
        now=NOW + timedelta(hours=1),
        fault_at=fault,
    )


def assert_final(root, memory_id: str) -> None:
    state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
    require(state.lifecycle_state == "hidden", state)
    require(state.mutation_state == "none", state)
    require(state.retrieval_eligible is False, state)
    require(state.current_revision == 2, state)
    require(state.controls_valid is True and state.page_valid is True, state)
    mutation_dir = root / "memory/mem/corrections/v0" / memory_id
    require(len(list(mutation_dir.glob("*.prepared.json"))) == 1, mutation_dir)
    require(len(list(mutation_dir.glob("*.tombstone.json"))) == 1, mutation_dir)
    require(not list(mutation_dir.glob("*.applied.json")), mutation_dir)


def expect_fault(callable_, expected: str = "reconciliation_required") -> None:
    try:
        callable_()
    except PrimaryForgetError as exc:
        require(exc.code == expected, exc.code)
    else:
        raise AssertionError("fault seam did not fire")


def initial_lock_fault() -> None:
    with prepared_store() as (root, memory_id):
        operation_id = "phase-i4c2-fault-after-lock"
        token = issue(root, memory_id, operation_id)
        expect_fault(lambda: apply(root, memory_id, operation_id, token, "after_lock_before_operation_reread"))
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.lifecycle_state == "active" and state.mutation_state == "none", state)
        result = apply(root, memory_id, operation_id, token)
        require(result.status == "applied", result)
        assert_final(root, memory_id)


def prepared_resume_fault() -> None:
    with prepared_store() as (root, memory_id):
        operation_id = "phase-i4c2-fault-prepared-resume"
        token = issue(root, memory_id, operation_id)
        expect_fault(
            lambda: apply_primary_memory_forget_hidden_successor(
                store_root=str(root),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                expected_lifecycle_state="active",
                reason=REASON,
                operation_id=operation_id,
                apply_token=token,
                now=NOW,
                fault_at="after_prepared_publication",
            )
        )
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.lifecycle_state == "active" and state.mutation_state == "prepared", state)
        expect_fault(lambda: recover(root, memory_id, operation_id, "after_prepared_reread_before_hidden_resume"))
        result = recover(root, memory_id, operation_id)
        require(result.status == "applied", result)
        assert_final(root, memory_id)


def hidden_publication_fault() -> None:
    with prepared_store() as (root, memory_id):
        operation_id = "phase-i4c2-fault-hidden-publish"
        token = issue(root, memory_id, operation_id)
        expect_fault(lambda: apply(root, memory_id, operation_id, token, "after_hidden_successor_publish_before_reread"))
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.lifecycle_state == "hidden", state)
        require(state.mutation_state == "recovery_required", state)
        result = recover(root, memory_id, operation_id)
        require(result.status == "applied", result)
        assert_final(root, memory_id)


def generic_restart_fault(seam: str) -> None:
    with prepared_store() as (root, memory_id):
        operation_id = f"phase-i4c2-{seam}"[:128]
        token = issue(root, memory_id, operation_id)
        expected = "response_lost" if seam == "after_finalization_before_return" else "reconciliation_required"
        expect_fault(lambda: apply(root, memory_id, operation_id, token, seam), expected)

        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.retrieval_eligible is False, state)
        require(state.lifecycle_state in {"active", "hidden"}, state)
        if seam == "after_m3g_index_before_log":
            control, reasons = _load_control_state(root)
            require(control is not None and not reasons, reasons)
            hidden = state.current_physical_id
            index_count = sum(item.get("idempotency_key") == hidden for item in control["index"])
            log_count = sum(item.get("idempotency_key") == hidden for item in control["log"])
            require(index_count == 1 and log_count == 0, (index_count, log_count))

        result = recover(root, memory_id, operation_id)
        require(result.status == "applied", result)
        assert_final(root, memory_id)
        replay = apply_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason=REASON,
            operation_id=operation_id,
            apply_token=token,
            now=NOW + timedelta(days=1),
        )
        require(replay.idempotent_replay is True, replay)


def main() -> None:
    initial_lock_fault()
    prepared_resume_fault()
    hidden_publication_fault()
    for seam in (
        "after_hidden_reread_before_m3f",
        "after_m3f_plan_before_m3g",
        "after_m3g_index_before_log",
        "after_m3g_before_control_reread",
        "after_controls_reread_before_tombstone",
        "during_tombstone_publish",
        "after_tombstone_publish_before_reread",
        "after_tombstone_reread_before_applied_receipt",
        "after_finalization_before_return",
    ):
        generic_restart_fault(seam)
    print("Phase I-4C2 Primary Forget fault/restart smoke passed")


if __name__ == "__main__":
    main()
