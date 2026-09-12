from __future__ import annotations

from collections.abc import Sequence

import tools.v2_cognitive_ir_s3_r5_llama_cpp_wsl as legacy


INNER_TRANSACTION_MODULE_D1 = (
    "tools.v2_cognitive_ir_s3_r6d_d1_llama_cpp_transaction"
)
WALL_TIME_SCHEMA_D1 = "relaylm2-cognitive-ir-s3-r6d-d1-wsl-wall-time-v1"


class D1WslLauncherError(RuntimeError):
    """The D1 WSL adapter cannot bind the shared-discriminator transaction."""


def main(argv: Sequence[str] | None = None) -> int:
    if legacy.INNER_TRANSACTION_MODULE != (
        "tools.v2_cognitive_ir_s3_r5_llama_cpp_transaction"
    ):
        raise D1WslLauncherError("legacy S3-R5 WSL transaction binding drifted")
    old_module = legacy.INNER_TRANSACTION_MODULE
    old_schema = legacy.WALL_TIME_SCHEMA
    legacy.INNER_TRANSACTION_MODULE = INNER_TRANSACTION_MODULE_D1
    legacy.WALL_TIME_SCHEMA = WALL_TIME_SCHEMA_D1
    try:
        return legacy.main(argv)
    finally:
        legacy.INNER_TRANSACTION_MODULE = old_module
        legacy.WALL_TIME_SCHEMA = old_schema


if __name__ == "__main__":
    raise SystemExit(main())
