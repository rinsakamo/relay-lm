"""I-4C1 normal, idempotency, crash-state, and leakage smoke."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
    snapshot_tree,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget_hidden_successor,
    list_primary_memory_forget_history,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_mutation_coordinator import (
    inspect_primary_memory_operations,
)
from relaylm.relaymem_primary_recall import _load_control_state

REASON = "今後の通常会話では検索対象から外すため"
NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)


def issue(root: Path, memory_id: str, operation_id: str) -> str:
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


def apply(root: Path, memory_id: str, operation_id: str, token: str, fault: str | None = None):
    return apply_primary_memory_forget_hidden_successor(
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


def normal_and_duplicate() -> None:
    with prepared_store() as (root, memory_id):
        before = snapshot_tree(root)
        prior_state = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        prior_path = root / prior_state.relative_path
        prior_bytes = prior_path.read_bytes()
        token = issue(root, memory_id, "phase-i4c1-normal")
        result = apply(root, memory_id, "phase-i4c1-normal", token)
        require(result.status == "hidden_successor_published", result)
        require(result.prepared_new is True, result)
        require(result.hidden_successor_published is True, result)
        require(result.lifecycle_state == "hidden", result)
        require(result.mutation_state == "recovery_required", result)
        require(result.retrieval_eligible is False, result)
        require(result.prior_revision == 1 and result.result_revision == 2, result)
        require(prior_path.read_bytes() == prior_bytes, "prior active page changed")

        current = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        require(current.lifecycle_state == "hidden", current)
        require(current.mutation_state == "recovery_required", current)
        require(current.retrieval_eligible is False, current)
        require(current.current_revision == 2, current)
        require(current.current_physical_id != prior_state.current_physical_id, current)
        require(current.page_valid is True, current)
        require(current.controls_valid is False, current)

        control, reasons = _load_control_state(root)
        require(control is not None and not reasons, reasons)
        require(
            all(
                item.get("idempotency_key") != current.current_physical_id
                for item in (*control["index"], *control["log"])
            ),
            "M3f/M3g unexpectedly converged hidden successor",
        )
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(not inspection.corrupt, inspection)
        require(len(inspection.pending) == 1, inspection)
        require(inspection.pending[0].operation_kind == "forget", inspection)
        require(inspection.pending[0].state == "prepared", inspection)
        mutation_dir = root / "memory/mem/corrections/v0" / memory_id
        require(len(list(mutation_dir.glob("*.prepared.json"))) == 1, mutation_dir)
        require(not list(mutation_dir.glob("*.applied.json")), mutation_dir)
        require(not list(root.rglob("*tombstone*")), "tombstone created")

        replay = apply(root, memory_id, "phase-i4c1-normal", token)
        require(replay.status == "hidden_successor_existing", replay)
        require(replay.prepared_existing is True, replay)
        require(replay.hidden_successor_existing is True, replay)
        require(replay.result_revision == 2, replay)
        require(snapshot_tree(root) != before, "commit produced no durable evidence")

        history = list_primary_memory_forget_history(
            store_root=str(root), namespace=NAMESPACE, memory_id=memory_id
        )
        require(history["forget_count"] == 0, history)
        require(history["items"] == [], history)
        require(history["current_lifecycle_state"] == "hidden", history)

        public = repr(result) + repr(result.to_log_dict()) + repr(replay)
        for forbidden in (
            str(root), CHARACTER, NAMESPACE, memory_id, token, REASON,
            current.current_physical_id, current.page_digest,
            "lineage_fingerprint", "operation_key", "binding_digest",
            "target_relative_path", "Traceback",
        ):
            require(forbidden not in public, forbidden)


def prepared_crash() -> None:
    with prepared_store() as (root, memory_id):
        token = issue(root, memory_id, "phase-i4c1-prepared-crash")
        try:
            apply(
                root,
                memory_id,
                "phase-i4c1-prepared-crash",
                token,
                "after_prepared_publication",
            )
        except PrimaryForgetError as exc:
            require(exc.code == "reconciliation_required", exc.code)
        else:
            raise AssertionError("prepared fault did not fire")
        current = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        require(current.lifecycle_state == "active", current)
        require(current.mutation_state == "prepared", current)
        require(current.retrieval_eligible is False, current)
        replay = apply(root, memory_id, "phase-i4c1-prepared-crash", token)
        require(replay.status == "prepared_existing", replay)
        require(replay.recovery_required is True, replay)


def hidden_crash() -> None:
    with prepared_store() as (root, memory_id):
        token = issue(root, memory_id, "phase-i4c1-hidden-crash")
        try:
            apply(
                root,
                memory_id,
                "phase-i4c1-hidden-crash",
                token,
                "after_hidden_successor_publication_before_reread",
            )
        except PrimaryForgetError as exc:
            require(exc.code == "reconciliation_required", exc.code)
        else:
            raise AssertionError("hidden fault did not fire")
        current = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        require(current.lifecycle_state == "hidden", current)
        require(current.mutation_state == "recovery_required", current)
        require(current.retrieval_eligible is False, current)
        replay = apply(root, memory_id, "phase-i4c1-hidden-crash", token)
        require(replay.status == "hidden_successor_existing", replay)
        require(replay.result_revision == 2, replay)


def main() -> None:
    normal_and_duplicate()
    prepared_crash()
    hidden_crash()
    print("Phase I-4C1 Primary Forget hidden-successor smoke passed")


if __name__ == "__main__":
    main()
