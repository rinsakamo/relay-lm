"""Phase I-5B Pin / Unpin security and leakage smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_pin import PrimaryPinError
from relaylm.relaymem_primary_pin_apply import apply_primary_memory_pin, list_primary_memory_pin_history, preflight_primary_memory_pin_apply

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
REASON = "I5B_SECURITY_REASON_CANARY"


def expect(code: set[str], fn) -> None:
    try:
        fn()
    except PrimaryPinError as exc:
        require(exc.code in code, exc.code)
    else:
        raise AssertionError(f"expected one of {sorted(code)}")


def main() -> None:
    with prepared_store() as (root, memory_id):
        preflight = preflight_primary_memory_pin_apply(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=REASON, operation_id="phase-i5b-security-pin", now=NOW)
        token = preflight["apply_token"]
        expect({"token_invalid"}, lambda: apply_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=REASON, operation_id="phase-i5b-security-pin", apply_token=token + "x", now=NOW))
        expect({"token_invalid", "target_not_found", "stale_revision"}, lambda: apply_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace="wrong-scope", memory_id=memory_id, expected_revision=1, reason=REASON, operation_id="phase-i5b-security-pin", apply_token=token, now=NOW))
        result = apply_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=REASON, operation_id="phase-i5b-security-pin", apply_token=token, now=NOW)
        projection = result.to_log_dict()
        history = list_primary_memory_pin_history(store_root=str(root), namespace=NAMESPACE, memory_id=memory_id)
        text = str({"projection": projection, "history": history})
        for forbidden in (REASON, token, "reason_digest", "token_digest", "current_physical_id", "store_root", "filesystem_path", "physical_id:"):
            require(forbidden not in text, forbidden)
        require(projection["content_included"] is False, projection)
        require(projection["path_included"] is False, projection)
        require(projection["physical_id_included"] is False, projection)
        require(history["items"][0]["effect_flags"]["ordinary_retrieval_excluded"] is False, history)

    print("Phase I-5B Pin/Unpin security smoke passed")


if __name__ == "__main__":
    main()
