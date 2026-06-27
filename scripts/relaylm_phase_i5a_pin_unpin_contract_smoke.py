"""I-5A read-only Pin / Unpin contract and history smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require, snapshot_tree
from relaylm.relaymem_primary_forget import apply_primary_memory_forget_hidden_successor, preflight_primary_memory_forget
from relaylm.relaymem_primary_mutation_coordinator import inspect_primary_memory_operations
from relaylm.relaymem_primary_pin import (
    PIN_HISTORY_SCHEMA,
    PIN_PREFLIGHT_RESPONSE_SCHEMA,
    UNPIN_HISTORY_SCHEMA,
    UNPIN_PREFLIGHT_RESPONSE_SCHEMA,
    PrimaryPinError,
    list_primary_memory_pin_history,
    list_primary_memory_unpin_history,
    preflight_primary_memory_pin,
    preflight_primary_memory_unpin,
    validate_primary_memory_pin_token,
    validate_primary_memory_unpin_token,
)

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
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


def _assert_ready(result: dict, *, memory_id: str, schema: str, kind: str) -> None:
    require(result["schema"] == schema, result)
    require(result["status"] == "ready", result)
    require(result["operation_kind"] == kind, result)
    require(result["read_only"] is True, result)
    require(result["memory_id"] == memory_id, result)
    require(result["current_revision"] == 1, result)
    require(result["current_lifecycle_state"] == "active", result)
    require(result["current_mutation_state"] == "none", result)
    require(result["pin_state_contract_only"] is True, result)
    require(isinstance(result["apply_token"], str) and result["apply_token"], result)


def active_targets_are_read_only() -> None:
    with prepared_store() as (root, memory_id):
        before = snapshot_tree(root)
        pin = preflight_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin", now=NOW)
        _assert_ready(pin, memory_id=memory_id, schema=PIN_PREFLIGHT_RESPONSE_SCHEMA, kind="pin")
        require(pin["current_pin_state"] == "unpinned", pin)
        require(pin["target_pin_state"] == "pinned", pin)
        require(pin["effects"] == {"ordinary_retrieval_deleted": False, "ordinary_retrieval_excluded": False, "future_priority_hint_contract": True, "semantic_content_changed": False, "physical_deletion": False, "audit_evidence_retained": True}, pin)
        require(validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin", apply_token=pin["apply_token"], now=NOW)["valid"] is True, pin)
        unpin = preflight_primary_memory_unpin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5a-unpin", now=NOW)
        _assert_ready(unpin, memory_id=memory_id, schema=UNPIN_PREFLIGHT_RESPONSE_SCHEMA, kind="unpin")
        require(unpin["current_pin_state"] == "pinned", unpin)
        require(unpin["target_pin_state"] == "unpinned", unpin)
        require(unpin["effects"] == {"ordinary_retrieval_deleted": False, "ordinary_retrieval_excluded": False, "future_priority_hint_removed_contract": True, "semantic_content_changed": False, "physical_deletion": False, "audit_evidence_retained": True}, unpin)
        require(validate_primary_memory_unpin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5a-unpin", apply_token=unpin["apply_token"], now=NOW)["valid"] is True, unpin)
        pin_history = list_primary_memory_pin_history(store_root=str(root), namespace=NAMESPACE, memory_id=memory_id)
        require(pin_history["schema"] == PIN_HISTORY_SCHEMA and pin_history["pin_count"] == 0 and pin_history["items"] == [], pin_history)
        unpin_history = list_primary_memory_unpin_history(store_root=str(root), namespace=NAMESPACE, memory_id=memory_id)
        require(unpin_history["schema"] == UNPIN_HISTORY_SCHEMA and unpin_history["unpin_count"] == 0 and unpin_history["items"] == [], unpin_history)
        require(not inspect_primary_memory_operations(root, memory_id=memory_id).operations, "unexpected mutation artifacts")
        require(snapshot_tree(root) == before, "I-5A preflight mutated store")


def fail_closed_targets() -> None:
    with prepared_store() as (root, memory_id):
        _expect({"stale_revision"}, lambda: preflight_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=2, reason=PIN_REASON, operation_id="phase-i5a-stale", now=NOW))
    with prepared_store() as (root, memory_id):
        f = preflight_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5a-hide", now=NOW)
        apply_primary_memory_forget_hidden_successor(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5a-hide", apply_token=f["apply_token"], now=NOW)
        _expect({"target_not_active"}, lambda: preflight_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=2, reason=PIN_REASON, operation_id="phase-i5a-hidden", now=NOW))
    with prepared_store() as (root, memory_id):
        f = preflight_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5a-prepared", now=NOW)
        try:
            apply_primary_memory_forget_hidden_successor(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5a-prepared", apply_token=f["apply_token"], now=NOW, fault_at="after_prepared_publication")
        except Exception:
            pass
        _expect({"operation_conflict", "recovery_required"}, lambda: preflight_primary_memory_unpin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5a-prepared-unpin", now=NOW))


def main() -> None:
    active_targets_are_read_only()
    fail_closed_targets()
    print("Phase I-5A Pin/Unpin contract smoke passed")


if __name__ == "__main__":
    main()
