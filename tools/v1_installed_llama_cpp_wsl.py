"""Public target wrapper for the installed llama.cpp release-path harness."""

from __future__ import annotations

from collections.abc import Sequence

from tools.v1_installed_llama_cpp_transaction import main as _run_transaction


def main(argv: Sequence[str] | None = None) -> int:
    """Run exactly one transaction-owned installed-path proof."""

    return _run_transaction(argv)


if __name__ == "__main__":
    raise SystemExit(main())
