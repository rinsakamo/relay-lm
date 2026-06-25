"""Forget token, scope, bounds, artifact, and leakage security smoke."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    preflight_primary_memory_forget,
    validate_primary_memory_forget_token,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
)


def expect_code(call, code: str) -> None:
    try:
        call()
    except PrimaryForgetError as exc:
        require(exc.code == code, (exc.code, code))
    else:
        raise AssertionError(f"expected {code}")


def kwargs(root: Path, memory_id: str) -> dict[str, object]:
    return {
        "store_root": str(root),
        "character_id": CHARACTER,
        "namespace": NAMESPACE,
        "memory_id": memory_id,
        "expected_revision": 1,
        "expected_lifecycle_state": "active",
        "reason": "通常検索から除外する",
        "operation_id": "security-op",
    }


def main() -> None:
    issued = datetime(2026, 6, 25, 0, 0, tzinfo=timezone.utc)
    with prepared_store() as (root, memory_id):
        base = kwargs(root, memory_id)
        expect_code(
            lambda: preflight_primary_memory_forget(
                **{**base, "expected_revision": True}
            ),
            "invalid_request",
        )
        expect_code(
            lambda: preflight_primary_memory_forget(
                **{**base, "expected_lifecycle_state": "hidden"}
            ),
            "invalid_request",
        )
        expect_code(
            lambda: preflight_primary_memory_forget(
                **{**base, "reason": " " + str(base["reason"])}
            ),
            "invalid_request",
        )
        expect_code(
            lambda: preflight_primary_memory_forget(
                **{**base, "operation_id": "x" * 129}
            ),
            "invalid_request",
        )

        preflight = preflight_primary_memory_forget(**base, now=issued)
        token = str(preflight["apply_token"])
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        expect_code(
            lambda: validate_primary_memory_forget_token(
                **base, apply_token=tampered, now=issued
            ),
            "token_invalid",
        )
        expect_code(
            lambda: validate_primary_memory_forget_token(
                **{**base, "reason": "別の理由"},
                apply_token=token,
                now=issued,
            ),
            "token_invalid",
        )
        expect_code(
            lambda: validate_primary_memory_forget_token(
                **{**base, "operation_id": "other-operation"},
                apply_token=token,
                now=issued,
            ),
            "token_invalid",
        )
        expect_code(
            lambda: validate_primary_memory_forget_token(
                **{**base, "namespace": "wrong-namespace"},
                apply_token=token,
                now=issued,
            ),
            "token_invalid",
        )
        expect_code(
            lambda: validate_primary_memory_forget_token(
                **base,
                apply_token=token,
                now=issued + timedelta(minutes=5),
            ),
            "token_expired",
        )

        state = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        rendered = repr(state) + repr(state.to_log_dict())
        for forbidden in (
            memory_id,
            state.current_physical_id,
            NAMESPACE,
            state.relative_path,
            state.page_digest,
            "好きな飲み物は紅茶です。",
        ):
            require(forbidden not in rendered, forbidden)

    with prepared_store() as (root, memory_id):
        artifact_dir = (
            root / "memory" / "mem" / "corrections" / "v0" / memory_id
        )
        artifact_dir.mkdir(parents=True)
        (artifact_dir / ("0" * 64 + ".prepared.json")).write_bytes(
            b"x" * 40000
        )
        expect_code(
            lambda: preflight_primary_memory_forget(
                **kwargs(root, memory_id)
            ),
            "target_corrupt",
        )

    with prepared_store() as (root, memory_id):
        outside = root / "outside"
        outside.mkdir()
        correction_root = root / "memory" / "mem" / "corrections"
        correction_root.mkdir(parents=True)
        (correction_root / "v0").symlink_to(outside, target_is_directory=True)
        expect_code(
            lambda: preflight_primary_memory_forget(
                **kwargs(root, memory_id)
            ),
            "target_corrupt",
        )

    print("Phase I-4B Primary Forget security smoke passed")


if __name__ == "__main__":
    main()
