from __future__ import annotations

from collections.abc import Sequence
import importlib

from relaylm.v2_cognitive_ir_s3_r2 import (
    S3_R2_PREREGISTRATION_SHA256,
    activate_s3_r2_preregistration,
)


def _load_listener_safe_transaction():
    """Activate #2491 before shared transaction modules bind identity constants."""

    activate_s3_r2_preregistration()
    transaction = importlib.import_module(
        "tools.v2_cognitive_ir_s3_llama_cpp_transaction"
    )
    transaction.S3_PREREGISTRATION_SHA256 = S3_R2_PREREGISTRATION_SHA256
    listener_safe = importlib.import_module(
        "tools.v2_cognitive_ir_s3_llama_cpp_transaction_listener_safe"
    )
    return transaction, listener_safe


def main(argv: Sequence[str] | None = None) -> int:
    transaction, listener_safe = _load_listener_safe_transaction()
    transaction.S3_PREREGISTRATION_SHA256 = S3_R2_PREREGISTRATION_SHA256
    return listener_safe.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
