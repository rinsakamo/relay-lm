"""One-command WSL operator boundary for the #2516 physical successor."""

from __future__ import annotations

from collections.abc import Sequence

from tools.v1_stage_r_llama_cpp_wsl import main as run_wsl_transaction


INNER_TRANSACTION = "relaylm.actual_model_stage_r_llama_cpp_epistemic_formation_transaction"


def main(argv: Sequence[str] | None = None) -> int:
    return run_wsl_transaction(argv, inner_transaction=INNER_TRANSACTION)


if __name__ == "__main__":
    raise SystemExit(main())
