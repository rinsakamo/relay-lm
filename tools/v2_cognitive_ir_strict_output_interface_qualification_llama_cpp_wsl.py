from __future__ import annotations

from collections.abc import Sequence

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as legacy


INNER_TRANSACTION_MODULE_STRICT_OUTPUT_INTERFACE_QUALIFICATION = (
    "tools.v2_cognitive_ir_strict_output_interface_qualification_llama_cpp_transaction"
)
WALL_TIME_SCHEMA_STRICT_OUTPUT_INTERFACE_QUALIFICATION = (
    "relaylm2-cognitive-ir-strict-output-interface-qualification-wsl-wall-time-v1"
)


class StrictOutputInterfaceQualificationWslLauncherError(RuntimeError):
    """The #2748 WSL adapter cannot bind the E4-IFQ1 transaction."""


def main(argv: Sequence[str] | None = None) -> int:
    expected = "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    if legacy.INNER_TRANSACTION_MODULE != expected:
        raise StrictOutputInterfaceQualificationWslLauncherError(
            "legacy shared-floor WSL transaction module binding drifted"
        )
    old_module = legacy.INNER_TRANSACTION_MODULE
    old_schema = legacy.WALL_TIME_SCHEMA
    legacy.INNER_TRANSACTION_MODULE = (
        INNER_TRANSACTION_MODULE_STRICT_OUTPUT_INTERFACE_QUALIFICATION
    )
    legacy.WALL_TIME_SCHEMA = (
        WALL_TIME_SCHEMA_STRICT_OUTPUT_INTERFACE_QUALIFICATION
    )
    try:
        return legacy.main(argv)
    finally:
        legacy.INNER_TRANSACTION_MODULE = old_module
        legacy.WALL_TIME_SCHEMA = old_schema


if __name__ == "__main__":
    raise SystemExit(main())
