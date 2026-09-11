from __future__ import annotations

from collections.abc import Sequence

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction as legacy
from relaylm.v2_cognitive_ir_shared_floor_calibration_v2 import (
    validate_shared_floor_v2_preregistration,
)
from tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp import (
    run_llama_cpp_shared_floor_calibration as legacy_runner,
)
from tools.v2_cognitive_ir_shared_floor_calibration_v2_llama_cpp import (
    run_llama_cpp_shared_floor_calibration_v2,
)


class SharedFloorCalibrationV2TransactionError(RuntimeError):
    """The #2619 transaction adapter cannot bind the fresh calibration identity."""


def main(argv: Sequence[str] | None = None) -> int:
    validate_shared_floor_v2_preregistration()
    if legacy.run_llama_cpp_shared_floor_calibration is not legacy_runner:
        raise SharedFloorCalibrationV2TransactionError(
            "legacy shared-floor transaction runner binding drifted"
        )
    legacy.run_llama_cpp_shared_floor_calibration = (
        run_llama_cpp_shared_floor_calibration_v2
    )
    try:
        return legacy.main(argv)
    finally:
        legacy.run_llama_cpp_shared_floor_calibration = legacy_runner


if __name__ == "__main__":
    raise SystemExit(main())
