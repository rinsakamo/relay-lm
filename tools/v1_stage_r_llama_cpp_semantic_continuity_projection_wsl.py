"""One-command WSL boundary for the retained-formation projection probe."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.v1_stage_r_llama_cpp_wsl import main as run_wsl_transaction


INNER_TRANSACTION = (
    "relaylm.actual_model_stage_r_llama_cpp_semantic_continuity_projection_transaction"
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Invoke exactly one projection transaction using an explicit retained "
            "epistemic-formation artifact."
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
