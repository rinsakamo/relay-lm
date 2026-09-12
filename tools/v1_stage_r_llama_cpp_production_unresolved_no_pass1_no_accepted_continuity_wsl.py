"""Thin v1 WSL adapter for the #2715 no-accepted-Continuity discriminator."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.v1_stage_r_llama_cpp_wsl import main as run_wsl_transaction


INNER_TRANSACTION = (
    "relaylm.actual_model_stage_r_llama_cpp_production_unresolved_no_pass1_"
    "no_accepted_continuity_transaction"
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Invoke exactly one unresolved-only/no-Pass1 transaction that removes "
            "only the already-compiled accepted Continuity context prefix."
        )
    )
    parser.add_argument("--retained-formation-artifact", required=True)
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    retained_path = Path(args.retained_formation_artifact).expanduser().resolve()
    return run_wsl_transaction(
        [],
        inner_transaction=INNER_TRANSACTION,
        inner_args=("--retained-formation-artifact", str(retained_path)),
    )


if __name__ == "__main__":
    raise SystemExit(main())
