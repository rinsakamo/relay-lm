from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from tools import v2_cognitive_ir_p2_boundedness_qual_v2_transaction as transaction


def _summary_path(argv: Sequence[str]) -> Path:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--summary-path", required=True)
    known, _ = parser.parse_known_args(list(argv))
    return Path(known.summary_path).expanduser().resolve()


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    summary_path = _summary_path(args)
    child_code = int(transaction.main(args))
    if not summary_path.is_file():
        return child_code if child_code != 0 else 3
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return child_code if child_code != 0 else 3
    if not isinstance(summary, dict):
        return child_code if child_code != 0 else 3
    summary_code = summary.get("transaction_exit_code")
    if isinstance(summary_code, bool) or not isinstance(summary_code, int):
        return child_code if child_code != 0 else 3
    if summary.get("classification") == "P2_BOUNDEDNESS_QUALIFIED_V2":
        return 0 if summary_code == 0 and child_code == 0 else max(summary_code, child_code, 2)
    return summary_code if summary_code != 0 else (child_code if child_code != 0 else 2)


if __name__ == "__main__":
    raise SystemExit(main())
