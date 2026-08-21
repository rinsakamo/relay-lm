#!/usr/bin/env python3
"""Validate semantic-owner coverage for RelayLM production Python modules."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from tools.repository_authority import AuthorityError, load_declarations

PRODUCTION_PACKAGE_DIRECTORY = "src/relaylm"


def production_code_coverage_errors(root: Path) -> tuple[str, ...]:
    """Return owner-coverage errors for production Python modules under ``root``.

    Every ``.py`` module under ``src/relaylm`` must be listed by at least one
    semantic owner's ``implementation`` surface. ``__init__.py`` package markers
    are excluded. Shared implementation remains valid because this check proves
    coverage, not exclusive implementation ownership.
    """

    package = root / PRODUCTION_PACKAGE_DIRECTORY
    if not package.is_dir():
        return ()

    declarations = load_declarations(root)
    declared = {
        surface
        for declaration in declarations
        for surface in declaration.implementation
    }

    errors: list[str] = []
    for candidate in sorted(package.rglob("*.py")):
        if candidate.name == "__init__.py":
            continue
        relative = candidate.relative_to(root).as_posix()
        if relative not in declared:
            errors.append(f"{relative}: production module has no semantic owner")
    return tuple(errors)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="repository root to validate"
    )
    arguments = parser.parse_args(argv)

    try:
        errors = production_code_coverage_errors(arguments.root)
    except AuthorityError as error:
        print(str(error), file=sys.stderr)
        return 1

    for message in errors:
        print(message, file=sys.stderr)
    if errors:
        return 1

    print("production code ownership valid")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
