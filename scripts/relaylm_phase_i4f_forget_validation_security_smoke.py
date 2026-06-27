"""Phase I-4F token, scope, and leakage validation smoke."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_forget import PrimaryForgetError, apply_primary_memory_forget, preflight_primary_memory_forget, validate_primary_memory_forget_token
from relaylm_phase_i4c2_primary_forget_security_smoke import main as i4c2_security_main
from relaylm_phase_i4e_forget_api_security_smoke import main as i4e_api_security_main

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
REASON = "I4F_SECURITY_REASON_CANARY"


def assert_bounded_error(exc: PrimaryForgetError, root: object, token: str) -> None:
    rendered = str(exc)
    require(rendered == exc.code, rendered)
    for forbidden in (REASON, str(root), token, "reason_digest", "token_digest", "physical_id", "traceback", "tombstone_content"):
        require(forbidden not in rendered, forbidden)


def expect_forget_error(callable_, allowed: set[str], root: object, token: str) -> None:
    try:
        callable_()
    except PrimaryForgetError as exc:
        require(exc.code in allowed, exc.code)
        assert_bounded_error(exc, root, token)
    else:
        raise AssertionError("expected bounded Forget failure")


def strict_token_binding_fail_closed() -> None:
    with prepared_store() as (root, memory_id):
        operation_id = "i4f-security-token"
        token = str(preflight_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=REASON, operation_id=operation_id, now=NOW)["apply_token"])
        validate_primary_memory_forget_token(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=REASON, operation_id=operation_id, apply_token=token, now=NOW)
        variants = ({"operation_id": "wrong-operation"}, {"reason": "wrong bounded reason"}, {"namespace": NAMESPACE + "-wrong"}, {"character_id": CHARACTER + "-wrong"}, {"expected_revision": 2}, {"memory_id": "0" * 64})
        base = {"store_root": str(root), "character_id": CHARACTER, "namespace": NAMESPACE, "memory_id": memory_id, "expected_revision": 1, "expected_lifecycle_state": "active", "reason": REASON, "operation_id": operation_id, "apply_token": token, "now": NOW}
        for variant in variants:
            kwargs = {**base, **variant}
            expect_forget_error(lambda kwargs=kwargs: validate_primary_memory_forget_token(**kwargs), {"token_invalid", "stale_revision", "target_not_found"}, root, token)
        expect_forget_error(lambda: validate_primary_memory_forget_token(**{**base, "now": NOW + timedelta(minutes=6)}), {"token_expired"}, root, token)
        result = apply_primary_memory_forget(**base)
        require(result.status == "applied", result)
        replay = apply_primary_memory_forget(**base)
        require(replay.idempotent_replay is True, replay)


def main() -> None:
    strict_token_binding_fail_closed()
    i4c2_security_main()
    i4e_api_security_main()
    print("Phase I-4F Forget security validation smoke passed")


if __name__ == "__main__":
    main()
