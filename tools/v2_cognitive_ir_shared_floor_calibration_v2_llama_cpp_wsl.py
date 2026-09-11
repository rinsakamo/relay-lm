from __future__ import annotations

from collections.abc import Sequence

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as legacy


INNER_TRANSACTION_MODULE_V2 = (
    "tools.v2_cognitive_ir_shared_floor_calibration_v2_llama_cpp_transaction"
)
WALL_TIME_SCHEMA_V2 = (
    "relaylm2-cognitive-ir-shared-floor-calibration-wsl-wall-time-v2"
)


class SharedFloorCalibrationV2WslLauncherError(RuntimeError):
    """The #2619 WSL adapter cannot bind the fresh calibration transaction."""


def main(argv: Sequence[str] | None = None) -> int:
    if legacy.INNER_TRANSACTION_MODULE != (
        "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    ):
        raise SharedFloorCalibrationV2WslLauncherError(
            "legacy shared-floor WSL transaction module binding drifted"
        )
    old_module = legacy.INNER_TRANSACTION_MODULE
    old_schema = legacy.WALL_TIME_SCHEMA
    legacy.INNER_TRANSACTION_MODULE = INNER_TRANSACTION_MODULE_V2
    legacy.WALL_TIME_SCHEMA = WALL_TIME_SCHEMA_V2
    try:
        return legacy.main(argv)
    finally:
        legacy.INNER_TRANSACTION_MODULE = old_module
        legacy.WALL_TIME_SCHEMA = old_schema


if __name__ == "__main__":
    raise SystemExit(main())
