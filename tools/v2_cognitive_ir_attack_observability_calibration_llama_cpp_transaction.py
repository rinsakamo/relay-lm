from __future__ import annotations

from collections.abc import Sequence

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction as legacy
from relaylm.v2_cognitive_ir_attack_observability_calibration import (
    ATTACK_OBS_ARCHITECTURE_CONSEQUENCE,
    ATTACK_OBS_CITABLE,
    ATTACK_OBS_CLAIM,
    ATTACK_OBS_INCOMPLETE,
    ATTACK_OBS_INPUT_TOKEN_REQUESTS_PER_CANDIDATE,
    ATTACK_OBS_MAX_INPUT_TOKEN_REQUESTS,
    ATTACK_OBS_MAX_SEMANTIC_CALLS,
    validate_attack_observability_preregistration,
)
from tools.v2_cognitive_ir_attack_observability_calibration_llama_cpp import (
    run_llama_cpp_attack_observability_calibration,
)
from tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp import (
    run_llama_cpp_shared_floor_calibration as legacy_runner,
)


class AttackObservabilityTransactionError(RuntimeError):
    """The #2667 transaction adapter cannot bind the attack calibration."""


def main(argv: Sequence[str] | None = None) -> int:
    validate_attack_observability_preregistration()
    if legacy.run_llama_cpp_shared_floor_calibration is not legacy_runner:
        raise AttackObservabilityTransactionError(
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
        run_llama_cpp_attack_observability_calibration
    )
    legacy.SHARED_FLOOR_CLAIM = ATTACK_OBS_CLAIM
    legacy.SHARED_FLOOR_CITABLE = ATTACK_OBS_CITABLE
    legacy.SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE = (
        ATTACK_OBS_ARCHITECTURE_CONSEQUENCE
    )
    legacy.CALIBRATION_INCOMPLETE = ATTACK_OBS_INCOMPLETE
    legacy.SHARED_FLOOR_MAX_SEMANTIC_CALLS = ATTACK_OBS_MAX_SEMANTIC_CALLS
    legacy.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS = ATTACK_OBS_MAX_INPUT_TOKEN_REQUESTS
    legacy.SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY = (
        ATTACK_OBS_INPUT_TOKEN_REQUESTS_PER_CANDIDATE
    )
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
