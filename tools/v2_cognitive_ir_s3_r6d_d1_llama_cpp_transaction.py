from __future__ import annotations

from collections.abc import Sequence
import importlib

from relaylm.v2_cognitive_ir_s3_r6d_d1 import (
    D1_MAX_OUTPUT_TOKENS,
    D1_PREREGISTRATION_SHA256,
    activate_d1_preregistration,
)
from tools.v2_cognitive_ir_s3_r5_llama_cpp import S3R5LlamaCppClient


def _load_listener_safe_transaction():
    """Activate D1 before the generic S3 transaction binds campaign globals."""

    activate_d1_preregistration()
    transaction = importlib.import_module("tools.v2_cognitive_ir_s3_llama_cpp_transaction")
    transaction.S3_PREREGISTRATION_SHA256 = D1_PREREGISTRATION_SHA256
    transaction.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS = D1_MAX_OUTPUT_TOKENS
    transaction.S3LlamaCppClient = S3R5LlamaCppClient
    listener_safe = importlib.import_module(
        "tools.v2_cognitive_ir_s3_llama_cpp_transaction_listener_safe"
    )
    return transaction, listener_safe


def main(argv: Sequence[str] | None = None) -> int:
    transaction, listener_safe = _load_listener_safe_transaction()
    transaction.S3_PREREGISTRATION_SHA256 = D1_PREREGISTRATION_SHA256
    transaction.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS = D1_MAX_OUTPUT_TOKENS
    transaction.S3LlamaCppClient = S3R5LlamaCppClient
    return listener_safe.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
