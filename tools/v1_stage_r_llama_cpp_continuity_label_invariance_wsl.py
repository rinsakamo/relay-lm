"""Carry the #2385 llama.cpp diagnostic transaction into a fresh child."""

from __future__ import annotations

from collections.abc import Sequence

import tools.v1_stage_r_llama_cpp_wsl as _base_wrapper


INNER_TRANSACTION = (
    "relaylm.actual_model_stage_r_llama_cpp_continuity_label_invariance_transaction"
)


def main(argv: Sequence[str] | None = None) -> int:
    """Create fresh wrapper-owned roots and invoke the diagnostic exactly once."""

    return _base_wrapper.main(argv, inner_transaction=INNER_TRANSACTION)


if __name__ == "__main__":
    raise SystemExit(main())
