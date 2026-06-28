"""Phase I-5B Pin / Unpin bounded idempotency smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_pin_apply import apply_primary_memory_pin, apply_primary_memory_unpin, preflight_primary_memory_pin_apply, preflight_primary_memory_unpin_apply

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
PIN_REASON = "concurrency pin reason"
UNPIN_REASON = "concurrency unpin reason"


def main() -> None:
    with prepared_store() as (root, memory_id):
        a = preflight_primary_memory_pin_apply(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5b-idempotent-a", now=NOW)
        b = preflight_primary_memory_pin_apply(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason="second bounded reason", operation_id="phase-i5b-idempotent-b", now=NOW)
        first = apply_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5b-idempotent-a", apply_token=a["apply_token"], now=NOW)
        require(first.status == "applied", first)
        replay = apply_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5b-idempotent-a", apply_token=a["apply_token"], now=NOW)
        require(replay.idempotent_replay is True, replay)
        second = apply_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason="second bounded reason", operation_id="phase-i5b-idempotent-b", apply_token=b["apply_token"], now=NOW)
        require(second.status == "already_pinned", second)
        u = preflight_primary_memory_unpin_apply(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5b-idempotent-unpin", now=NOW)
        done = apply_primary_memory_unpin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5b-idempotent-unpin", apply_token=u["apply_token"], now=NOW)
        require(done.status == "applied", done)
    print("Phase I-5B Pin/Unpin concurrency smoke passed")


if __name__ == "__main__":
    main()
