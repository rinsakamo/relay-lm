#!/usr/bin/env python3
"""Diagnostic inventory for semantic-qualification implementation coverage.

This module intentionally does not decide whether an omitted implementation
surface is release-significant. It exposes owner-closure omissions and the
contract for explicit reasoned exclusions so release qualification can resolve
every implementation surface without silently treating omission as exclusion.

The audit does not mutate qualification inputs, roots, fingerprints, or evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from tools.repository_authority import (
    AuthorityError,
    Declaration,
    load_declarations,
    qualification_owner_closure,
)


@dataclass(frozen=True, slots=True)
class QualificationCoverageGap:
    """Implementation surfaces in one qualification owner that remain unresolved."""

    owner: str
    omitted_implementation: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QualificationExclusion:
    """One explicit owner-local reason not to fingerprint an implementation surface."""

    path: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path.strip():
            raise ValueError("qualification exclusion path must be non-empty")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("qualification exclusion reason must be non-empty")


def qualification_coverage_gaps(
    declarations: Sequence[Declaration],
    *,
    roots: Sequence[str],
    exclusions_by_owner: Mapping[str, Sequence[QualificationExclusion]] | None = None,
) -> tuple[QualificationCoverageGap, ...]:
    """Return unresolved implementation omissions for a qualification closure.

    A path is resolved only when the same owner either selects it in
    ``qualification_inputs`` or explicitly excludes it with a non-empty reason.
    Exclusions are valid only for that owner's implementation surfaces and may
    not contradict a selected qualification input.

    This function deliberately does not infer whether an exclusion reason is a
    good release decision. It only makes the disposition explicit and
    machine-auditable instead of treating silence as exclusion.
    """

    owners_by_id = {declaration.id: declaration for declaration in declarations}
    closure = qualification_owner_closure(declarations, roots=roots)
    supplied = exclusions_by_owner or {}

    unknown_owners = sorted(owner for owner in supplied if owner not in owners_by_id)
    if unknown_owners:
        raise AuthorityError(
            "qualification exclusions name unknown owners: " + ", ".join(unknown_owners)
        )

    gaps: list[QualificationCoverageGap] = []
    for owner in closure:
        declaration = owners_by_id[owner]
        implementation = set(declaration.implementation)
        selected = set(declaration.qualification_inputs)
        excluded: set[str] = set()
        for exclusion in supplied.get(owner, ()):
            if not isinstance(exclusion, QualificationExclusion):
                raise TypeError(
                    "qualification exclusions must contain QualificationExclusion values"
                )
            if exclusion.path in excluded:
                raise AuthorityError(
                    f"{owner}: qualification exclusion repeats '{exclusion.path}'"
                )
            if exclusion.path not in implementation:
                raise AuthorityError(
                    f"{owner}: qualification exclusion '{exclusion.path}' is not an"
                    " implementation surface owned by that owner"
                )
            if exclusion.path in selected:
                raise AuthorityError(
                    f"{owner}: qualification input '{exclusion.path}' cannot also be excluded"
                )
            excluded.add(exclusion.path)

        omitted = tuple(sorted(implementation - selected - excluded))
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
