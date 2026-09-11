from __future__ import annotations

from collections.abc import Sequence
import importlib

from relaylm.v2_cognitive_ir_s3_r5 import (
    S3_R5_MAX_OUTPUT_TOKENS,
    S3_R5_PREREGISTRATION_SHA256,
    activate_s3_r5_preregistration,
)
from tools.v2_cognitive_ir_s3_r5_llama_cpp import S3R5LlamaCppClient


def _load_listener_safe_transaction():
    """Activate R5 before shared transaction modules bind campaign identity."""

    activate_s3_r5_preregistration()
    transaction = importlib.import_module("tools.v2_cognitive_ir_s3_llama_cpp_transaction")
    transaction.S3_PREREGISTRATION_SHA256 = S3_R5_PREREGISTRATION_SHA256
    transaction.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS = S3_R5_MAX_OUTPUT_TOKENS
    transaction.S3LlamaCppClient = S3R5LlamaCppClient
    listener_safe = importlib.import_module(
        "tools.v2_cognitive_ir_s3_llama_cpp_transaction_listener_safe"
    )
    return transaction, listener_safe


def main(argv: Sequence[str] | None = None) -> int:
    transaction, listener_safe = _load_listener_safe_transaction()
    transaction.S3_PREREGISTRATION_SHA256 = S3_R5_PREREGISTRATION_SHA256
    transaction.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS = S3_R5_MAX_OUTPUT_TOKENS
    transaction.S3LlamaCppClient = S3R5LlamaCppClient
    return listener_safe.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
