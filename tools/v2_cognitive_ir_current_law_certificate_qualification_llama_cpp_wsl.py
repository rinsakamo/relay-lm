from __future__ import annotations

from collections.abc import Sequence

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as legacy


INNER_TRANSACTION_MODULE_G1 = (
    "tools.v2_cognitive_ir_current_law_certificate_qualification_llama_cpp_transaction"
)
WALL_TIME_SCHEMA_G1 = (
    "relaylm2-cognitive-ir-r6d-current-law-certificate-usability-wsl-wall-time-v1"
)


class CurrentLawCertificateWslLauncherError(RuntimeError):
    """The #2712 WSL adapter cannot bind the G1 transaction."""


def main(argv: Sequence[str] | None = None) -> int:
    expected = "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    if legacy.INNER_TRANSACTION_MODULE != expected:
        raise CurrentLawCertificateWslLauncherError(
            "legacy shared-floor WSL transaction module binding drifted"
        )
    old_module = legacy.INNER_TRANSACTION_MODULE
    old_schema = legacy.WALL_TIME_SCHEMA
    legacy.INNER_TRANSACTION_MODULE = INNER_TRANSACTION_MODULE_G1
    legacy.WALL_TIME_SCHEMA = WALL_TIME_SCHEMA_G1
    try:
        return legacy.main(argv)
    finally:
        legacy.INNER_TRANSACTION_MODULE = old_module
        legacy.WALL_TIME_SCHEMA = old_schema


if __name__ == "__main__":
    raise SystemExit(main())
