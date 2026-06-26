"""Verify every deterministic I-4C1 Forget fault seam and durable state."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_mutation_coordinator import (
    inspect_primary_memory_operations,
)
from relaylm.relaymem_primary_recall import _load_control_state

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
REASON = "通常検索から外すため"


def invoke(root, memory_id: str, operation_id: str, seam: str) -> None:
    token = preflight_primary_memory_forget(
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
    try:
        apply_primary_memory_forget_hidden_successor(
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
            fault_at=seam,
        )
    except PrimaryForgetError as exc:
        expected = (
            "failed"
            if seam == "after_revision_claim_before_prepared"
            else "reconciliation_required"
        )
        require(exc.code == expected, (seam, exc.code))
    else:
        raise AssertionError(f"fault seam did not fire: {seam}")


def assert_no_durable_mutation(seam: str) -> None:
    with prepared_store() as (root, memory_id):
        invoke(root, memory_id, f"phase-i4c1-{seam}", seam)
        state = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        require(state.lifecycle_state == "active", (seam, state))
        require(state.mutation_state == "none", (seam, state))
        require(state.retrieval_eligible is True, (seam, state))
        require(state.current_revision == 1, (seam, state))
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(not inspection.corrupt, (seam, inspection))
        require(not inspection.operations, (seam, inspection))
        require(not list(root.rglob("*.prepared.json")), seam)


def assert_prepared_only(seam: str) -> None:
    with prepared_store() as (root, memory_id):
        invoke(root, memory_id, f"phase-i4c1-{seam}", seam)
        state = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        require(state.lifecycle_state == "active", (seam, state))
        require(state.mutation_state == "prepared", (seam, state))
        require(state.retrieval_eligible is False, (seam, state))
        require(state.current_revision == 1, (seam, state))
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(not inspection.corrupt, (seam, inspection))
        require(len(inspection.pending) == 1, (seam, inspection))
        require(inspection.pending[0].operation_kind == "forget", inspection)
        control, reasons = _load_control_state(root)
        require(control is not None and not reasons, (seam, reasons))
        require(
            all(
                item.get("idempotency_key") == memory_id
                for item in (*control["index"], *control["log"])
            ),
            seam,
        )


def assert_hidden_committed(seam: str) -> None:
    with prepared_store() as (root, memory_id):
        invoke(root, memory_id, f"phase-i4c1-{seam}", seam)
        state = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        require(state.lifecycle_state == "hidden", (seam, state))
        require(state.mutation_state == "recovery_required", (seam, state))
        require(state.retrieval_eligible is False, (seam, state))
        require(state.current_revision == 2, (seam, state))
        require(state.current_physical_id != memory_id, (seam, state))
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(not inspection.corrupt, (seam, inspection))
        require(len(inspection.pending) == 1, (seam, inspection))
        control, reasons = _load_control_state(root)
        require(control is not None and not reasons, (seam, reasons))
        require(
            all(
                item.get("idempotency_key") != state.current_physical_id
                for item in (*control["index"], *control["log"])
            ),
            seam,
        )


def main() -> None:
    for seam in (
        "after_lock_before_revision_reread",
        "after_revision_claim_before_prepared",
    ):
        assert_no_durable_mutation(seam)
    for seam in (
        "after_prepared_publication",
        "before_hidden_successor_publication",
    ):
        assert_prepared_only(seam)
    for seam in (
        "after_hidden_successor_publication_before_reread",
        "after_hidden_successor_reread_before_return",
    ):
        assert_hidden_committed(seam)
    print("Phase I-4C1 Primary Forget fault seam smoke passed")


if __name__ == "__main__":
    main()
