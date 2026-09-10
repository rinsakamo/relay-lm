"""One-command llama.cpp transaction for the #2385 evaluation-only diagnostic."""

from __future__ import annotations

from collections.abc import Sequence

from relaylm.actual_model_stage_r_llama_cpp_transaction import (
    main as _main,
)


HOST_MODULE = "relaylm.actual_model_stage_r_llama_cpp_continuity_label_invariance"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the shared physical transaction with the diagnostic host only."""

    return _main(argv, host_module=HOST_MODULE)


if __name__ == "__main__":
    raise SystemExit(main())
