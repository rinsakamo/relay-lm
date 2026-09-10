"""Transaction selector for the #2516 llama.cpp physical owner."""

from __future__ import annotations

from collections.abc import Sequence

from relaylm.actual_model_stage_r_llama_cpp_transaction import main as run_transaction


HOST_MODULE = "relaylm.actual_model_stage_r_llama_cpp_epistemic_formation"


def main(argv: Sequence[str] | None = None) -> int:
    return run_transaction(argv, host_module=HOST_MODULE)


if __name__ == "__main__":
    raise SystemExit(main())
