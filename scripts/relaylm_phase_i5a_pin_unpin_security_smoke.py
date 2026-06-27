"""I-5A Pin / Unpin public projection security smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require, snapshot_tree
from relaylm.relaymem_primary_pin import (
    PrimaryPinError,
    list_primary_memory_pin_history,
    preflight_primary_memory_pin,
    preflight_primary_memory_unpin,
    validate_primary_memory_pin_token,
)

NOW = datetime(2026, 6, 27, 3, 0, tzinfo=timezone.utc)
PIN_REASON = "評価中は優先候補として扱う契約を確認するため"
UNPIN_REASON = "優先候補契約を外す前提を確認するため"


def public_results_do_not_leak_private_content_or_identity() -> None:
    with prepared_store() as (root, memory_id):
        before = snapshot_tree(root)
        pin = preflight_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-security", now=NOW)
        unpin = preflight_primary_memory_unpin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=UNPIN_REASON, operation_id="phase-i5a-unpin-security", now=NOW)
        history = list_primary_memory_pin_history(store_root=str(root), namespace=NAMESPACE, memory_id=memory_id)
        validated = validate_primary_memory_pin_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="phase-i5a-pin-security", apply_token=pin["apply_token"], now=NOW)
        require(snapshot_tree(root) == before, "security smoke observed mutation")
        public_text = repr(pin) + repr(unpin) + repr(history) + repr(validated)
        for forbidden in (str(root), NAMESPACE, CHARACTER, PIN_REASON, UNPIN_REASON, "好きな飲み物", "紅茶", "page_digest", "binding_digest", "reason_digest", "current_physical_id", "physical_id", "relative_path", "lineage_fingerprint", "candidate_id", "prepared", "tombstone", "queue", "job", "dispatch", "claim", "Traceback"):
            require(forbidden not in public_text, forbidden)
        token_public = pin["apply_token"].split(".", 1)[0]
        for forbidden in (memory_id, NAMESPACE, CHARACTER, PIN_REASON, "binding_digest"):
            require(forbidden not in token_public, forbidden)


def public_errors_are_bounded_codes() -> None:
    with prepared_store() as (root, memory_id):
        try:
            preflight_primary_memory_pin(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, reason=PIN_REASON, operation_id="bad\noperation", now=NOW)
        except PrimaryPinError as exc:
            require(exc.code == "invalid_request", exc.code)
            require(str(root) not in repr(exc), repr(exc))
            require(NAMESPACE not in repr(exc), repr(exc))
        else:
            raise AssertionError("invalid operation accepted")


def main() -> None:
    public_results_do_not_leak_private_content_or_identity()
    public_errors_are_bounded_codes()
    print("Phase I-5A Pin/Unpin security smoke passed")


if __name__ == "__main__":
    main()
