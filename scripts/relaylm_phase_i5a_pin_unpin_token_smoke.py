"""I-5A Pin / Unpin opaque token binding and expiry smoke."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from _relaylm_phase_i3_test_support import form_primary_memory
from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_pin import (
    PrimaryPinError,
    preflight_primary_memory_pin,
    preflight_primary_memory_unpin,
    validate_primary_memory_pin_token,
    validate_primary_memory_unpin_token,
)

NOW = datetime(2026, 6, 27, 1, 0, tzinfo=timezone.utc)
PIN_REASON = "評価中は優先候補として扱う契約を確認するため"
UNPIN_REASON = "優先候補契約を外す前提を確認するため"


def _expect(code: set[str], fn) -> None:
    try:
        fn()
    except PrimaryPinError as exc:
        require(exc.code in code, exc.code)
    else:
        raise AssertionError(f"expected one of {sorted(code)}")


def pin_token_binding() -> None:
    with prepared_store() as (root, memory_id):
        other_memory_id = form_primary_memory(root, namespace=NAMESPACE, candidate_id="phase-i5a-other-primary", title="別の記憶", summary="これは別の記憶です。")
        token = preflight_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-token", now=NOW)["apply_token"]
        public_part = token.split(".", 1)[0]
        for forbidden in (CHARACTER, NAMESPACE, memory_id, other_memory_id, "binding_digest", "current_physical_id", PIN_REASON):
            require(forbidden not in public_part, forbidden)
        validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-token", apply_token=token, now=NOW)
        _expect({"token_invalid"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason="別の理由", operation_id="phase-i5a-pin-token", apply_token=token, now=NOW))
        _expect({"token_invalid"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-token-other", apply_token=token, now=NOW))
        _expect({"token_invalid"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=other_memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-token", apply_token=token, now=NOW))
        _expect({"token_invalid", "target_not_found"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace="phase-i5a-other-namespace", memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-token", apply_token=token, now=NOW))
        _expect({"stale_revision"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=2, reason=PIN_REASON, operation_id="phase-i5a-pin-token", apply_token=token, now=NOW))
        _expect({"token_expired"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-token", apply_token=token, now=NOW + timedelta(minutes=5)))
        _expect({"token_invalid"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-token", apply_token=token + "a", now=NOW))


def unpin_token_binding() -> None:
    with prepared_store() as (root, memory_id):
        token = preflight_primary_memory_unpin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5a-unpin-token", now=NOW)["apply_token"]
        validate_primary_memory_unpin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5a-unpin-token", apply_token=token, now=NOW)
        _expect({"token_invalid"}, lambda: validate_primary_memory_unpin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON + "変更", operation_id="phase-i5a-unpin-token", apply_token=token, now=NOW))
        _expect({"token_invalid"}, lambda: validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5a-unpin-token", apply_token=token, now=NOW))


def missing_memory_fails_closed() -> None:
    with prepared_store() as (root, _memory_id):
        missing = hashlib.sha256(b"missing-i5a-memory").hexdigest()
        _expect({"target_not_found"}, lambda: preflight_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=missing, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-missing-memory", now=NOW))


def main() -> None:
    pin_token_binding()
    unpin_token_binding()
    missing_memory_fails_closed()
    print("Phase I-5A Pin/Unpin token smoke passed")


if __name__ == "__main__":
    main()
