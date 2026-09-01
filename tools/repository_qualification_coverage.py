#!/usr/bin/env python3
"""Diagnostic inventory for semantic-qualification implementation coverage.

This module intentionally does not decide whether an omitted implementation
surface is release-significant.  It exposes the current owner-closure omissions
so the release-qualification contract can make that decision explicitly rather
than relying on silent owner-local selection.

The audit does not mutate qualification inputs, roots, fingerprints, or evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from tools.repository_authority import (
    Declaration,
    load_declarations,
    qualification_owner_closure,
)


@dataclass(frozen=True, slots=True)
class QualificationCoverageGap:
    """Implementation surfaces in one qualification owner that are not selected."""

    owner: str
    omitted_implementation: tuple[str, ...]


def qualification_coverage_gaps(
    declarations: Sequence[Declaration],
    *,
    roots: Sequence[str],
) -> tuple[QualificationCoverageGap, ...]:
    """Return deterministic implementation omissions for a qualification closure.

    An omission is purely structural: a path appears in an owner's
    ``implementation`` surfaces but not in that same owner's
    ``qualification_inputs``.  This function does not infer that the path must
    be qualification-significant and does not inspect file contents.
    """

    owners_by_id = {declaration.id: declaration for declaration in declarations}
    closure = qualification_owner_closure(declarations, roots=roots)

    gaps: list[QualificationCoverageGap] = []
    for owner in closure:
        declaration = owners_by_id[owner]
        selected = set(declaration.qualification_inputs)
        omitted = tuple(
            sorted(
                path
                for path in declaration.implementation
                if path not in selected
            )
        )
        if omitted:
            gaps.append(QualificationCoverageGap(owner, omitted))
    return tuple(gaps)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventory implementation paths omitted from semantic qualification."
    )
    parser.add_argument(
        "roots",
        nargs="+",
        help="semantic owner ids whose transitive qualification closure should be audited",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path.cwd(),
        help="repository root containing .ai/authority (default: current directory)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    declarations = load_declarations(args.repository_root)
    gaps = qualification_coverage_gaps(declarations, roots=args.roots)
    payload = {
        "roots": sorted(set(args.roots)),
        "gaps": [
            {
                "owner": gap.owner,
                "omitted_implementation": list(gap.omitted_implementation),
            }
            for gap in gaps
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return 1 if gaps else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
