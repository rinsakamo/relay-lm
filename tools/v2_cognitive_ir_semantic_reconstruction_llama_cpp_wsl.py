from __future__ import annotations

from collections.abc import Sequence

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as legacy


INNER_TRANSACTION_MODULE_SEMANTIC_RECONSTRUCTION = (
    "tools.v2_cognitive_ir_semantic_reconstruction_llama_cpp_transaction"
)
WALL_TIME_SCHEMA_SEMANTIC_RECONSTRUCTION = (
    "relaylm2-cognitive-ir-semantic-reconstruction-wsl-wall-time-v1"
)


class SemanticReconstructionWslLauncherError(RuntimeError):
    """The #2723 WSL adapter cannot bind the semantic reconstruction transaction."""


def main(argv: Sequence[str] | None = None) -> int:
    expected = "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    if legacy.INNER_TRANSACTION_MODULE != expected:
        raise SemanticReconstructionWslLauncherError(
            "legacy shared-floor WSL transaction module binding drifted"
        )
    old_module = legacy.INNER_TRANSACTION_MODULE
    old_schema = legacy.WALL_TIME_SCHEMA
    legacy.INNER_TRANSACTION_MODULE = (
        INNER_TRANSACTION_MODULE_SEMANTIC_RECONSTRUCTION
    )
    legacy.WALL_TIME_SCHEMA = WALL_TIME_SCHEMA_SEMANTIC_RECONSTRUCTION
    try:
        return legacy.main(argv)
    finally:
        legacy.INNER_TRANSACTION_MODULE = old_module
        legacy.WALL_TIME_SCHEMA = old_schema


if __name__ == "__main__":
    raise SystemExit(main())
