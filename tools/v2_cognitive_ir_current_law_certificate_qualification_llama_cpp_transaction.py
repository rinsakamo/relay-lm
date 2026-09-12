from __future__ import annotations

from collections.abc import Sequence

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction as legacy
from relaylm.v2_cognitive_ir_current_law_certificate_qualification import (
    G1_ARCHITECTURE_CONSEQUENCE,
    G1_CITABLE,
    G1_CLAIM,
    G1_INCOMPLETE,
    G1_INPUT_TOKEN_REQUESTS,
    G1_SEMANTIC_CALLS,
    validate_g1_preregistration,
)
from tools.v2_cognitive_ir_current_law_certificate_qualification_llama_cpp import (
    run_llama_cpp_current_law_certificate_qualification,
)
from tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp import (
    run_llama_cpp_shared_floor_calibration as legacy_runner,
)


class CurrentLawCertificateTransactionError(RuntimeError):
    """The #2712 transaction adapter cannot bind the G1 qualification."""


def main(argv: Sequence[str] | None = None) -> int:
    validate_g1_preregistration()
    if legacy.run_llama_cpp_shared_floor_calibration is not legacy_runner:
        raise CurrentLawCertificateTransactionError(
            "legacy shared-floor transaction runner binding drifted"
        )

    saved = {
        "runner": legacy.run_llama_cpp_shared_floor_calibration,
        "claim": legacy.SHARED_FLOOR_CLAIM,
        "citable": legacy.SHARED_FLOOR_CITABLE,
        "architecture": legacy.SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE,
        "incomplete": legacy.CALIBRATION_INCOMPLETE,
        "max_semantic": legacy.SHARED_FLOOR_MAX_SEMANTIC_CALLS,
        "max_input": legacy.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
        "per_candidate_input": legacy.SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY,
    }
    legacy.run_llama_cpp_shared_floor_calibration = (
        run_llama_cpp_current_law_certificate_qualification
    )
    legacy.SHARED_FLOOR_CLAIM = G1_CLAIM
    legacy.SHARED_FLOOR_CITABLE = G1_CITABLE
    legacy.SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE = G1_ARCHITECTURE_CONSEQUENCE
    legacy.CALIBRATION_INCOMPLETE = G1_INCOMPLETE
    legacy.SHARED_FLOOR_MAX_SEMANTIC_CALLS = G1_SEMANTIC_CALLS
    legacy.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS = G1_INPUT_TOKEN_REQUESTS
    legacy.SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY = G1_INPUT_TOKEN_REQUESTS
    try:
        return legacy.main(argv)
    finally:
        legacy.run_llama_cpp_shared_floor_calibration = saved["runner"]
        legacy.SHARED_FLOOR_CLAIM = saved["claim"]
        legacy.SHARED_FLOOR_CITABLE = saved["citable"]
        legacy.SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE = saved["architecture"]
        legacy.CALIBRATION_INCOMPLETE = saved["incomplete"]
        legacy.SHARED_FLOOR_MAX_SEMANTIC_CALLS = saved["max_semantic"]
        legacy.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS = saved["max_input"]
        legacy.SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY = saved[
            "per_candidate_input"
        ]


if __name__ == "__main__":
    raise SystemExit(main())
