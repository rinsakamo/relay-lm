"""Transaction selector for the #2715 no-accepted-Continuity diagnostic."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from relaylm.actual_model_stage_r_llama_cpp_transaction import main as run_transaction


HOST_MODULE = (
    "relaylm.actual_model_stage_r_llama_cpp_production_unresolved_no_pass1_"
    "no_accepted_continuity"
)
HOST_SUMMARY_FILENAME = (
    "production-unresolved-no-pass1-no-accepted-continuity-t2-summary.json"
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--retained-formation-artifact", required=True)
    args, transaction_argv = parser.parse_known_args(
        list(sys.argv[1:] if argv is None else argv)
    )
    retained_path = Path(args.retained_formation_artifact).expanduser().resolve()
    return run_transaction(
        transaction_argv,
        host_module=HOST_MODULE,
        host_summary_filename=HOST_SUMMARY_FILENAME,
        host_args=("--retained-formation-artifact", str(retained_path)),
    )


if __name__ == "__main__":
    raise SystemExit(main())
