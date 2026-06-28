"""Phase I-5B durable Pin / Unpin apply smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_forget import apply_primary_memory_forget, preflight_primary_memory_forget
from relaylm.relaymem_primary_pin import PrimaryPinError
from relaylm.relaymem_primary_pin_apply import (
    apply_primary_memory_pin,
    apply_primary_memory_unpin,
    get_primary_memory_pin_state,
    list_primary_memory_pin_history,
    list_primary_memory_unpin_history,
    preflight_primary_memory_pin_apply,
    preflight_primary_memory_unpin_apply,
)

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
PIN_REASON = "I5B_PIN_REASON_CANARY"
UNPIN_REASON = "I5B_UNPIN_REASON_CANARY"
FORGET_REASON = "hide target before pin"


def expect(code: set[str], fn) -> None:
    try:
        fn()
    except PrimaryPinError as exc:
        require(exc.code in code, exc.code)
    else:
        raise AssertionError(f"expected one of {sorted(code)}")


def no_leak(value: object, *extra: str) -> None:
    text = str(value)
    for forbidden in (
        PIN_REASON,
        UNPIN_REASON,
        "reason_digest",
        "token_digest",
        "current_physical_id",
        "store_root",
        "filesystem_path",
        "physical_id:",
        *extra,
    ):
        require(forbidden not in text, forbidden)


def main() -> None:
    with prepared_store() as (root, memory_id):
        preflight = preflight_primary_memory_pin_apply(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5b-pin", now=NOW)
        require(preflight["status"] == "ready", preflight)
        require(preflight["current_pin_state"] == "unpinned", preflight)
        token = preflight["apply_token"]
        applied = apply_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5b-pin", apply_token=token, now=NOW)
        require(applied.status == "applied", applied)
        require(applied.target_pin_state == "pinned", applied)
        require(get_primary_memory_pin_state(str(root), namespace=NAMESPACE, memory_id=memory_id) == "pinned", "pinned state")
        replay = apply_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5b-pin", apply_token=token, now=NOW)
        require(replay.idempotent_replay is True, replay)
        pin_history = list_primary_memory_pin_history(store_root=str(root), namespace=NAMESPACE, memory_id=memory_id)
        require(pin_history["pin_count"] == 1, pin_history)
        no_leak(applied.to_log_dict(), token)
        no_leak(pin_history, token)

        unpin_preflight = preflight_primary_memory_unpin_apply(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5b-unpin", now=NOW)
        require(unpin_preflight["status"] == "ready", unpin_preflight)
        unpinned = apply_primary_memory_unpin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5b-unpin", apply_token=unpin_preflight["apply_token"], now=NOW)
        require(unpinned.status == "applied", unpinned)
        require(get_primary_memory_pin_state(str(root), namespace=NAMESPACE, memory_id=memory_id) == "unpinned", "unpinned state")
        unpin_history = list_primary_memory_unpin_history(store_root=str(root), namespace=NAMESPACE, memory_id=memory_id)
        require(unpin_history["unpin_count"] == 1, unpin_history)
        no_leak(unpinned.to_log_dict(), unpin_preflight["apply_token"])
        no_leak(unpin_history, unpin_preflight["apply_token"])

    with prepared_store() as (root, memory_id):
        forget = preflight_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5b-hide", now=NOW)
        apply_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=FORGET_REASON, operation_id="phase-i5b-hide", apply_token=forget["apply_token"], now=NOW)
        expect({"target_not_active"}, lambda: preflight_primary_memory_pin_apply(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=2, reason=PIN_REASON, operation_id="phase-i5b-hidden-pin", now=NOW))

    print("Phase I-5B Pin/Unpin apply smoke passed")


if __name__ == "__main__":
    main()
