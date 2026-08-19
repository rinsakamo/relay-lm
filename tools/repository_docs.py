#!/usr/bin/env python3
"""RelayLM v1 persistent human documentation projections.

Human-facing root documentation is materialized from repository authority at an
explicit version/release boundary rather than hand-synchronized by every
semantic transaction:

    Write canonical facts continuously. Generate global views on demand.
    Materialize human documentation at release boundaries.

Generation is a pure function of one frozen input commit, the owner-local
authority at that commit, and the release-owned package version. Each generated
document carries machine-readable provenance so a reader can tell which
repository state it describes.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from tools.repository_authority import (
    AuthorityError,
    Declaration,
    consumers_of,
    load_declarations,
)

PROJECTION_SCHEMA_VERSION = 1

#: Human-facing documents generated at a version/release boundary.
PERSISTENT_PROJECTIONS = ("ARCHITECTURE.md",)

_ARCHITECTURE_GENERATOR = "relaylm-architecture-projection"
_VERSION_SOURCE = "src/relaylm/_version.py"
_VERSION_RE = re.compile(r'^__version__\s*=\s*"(?P<version>[^"]+)"', re.MULTILINE)
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_PROVENANCE_RE = re.compile(r"^<!-- (?P<key>[a-z-]+): (?P<value>.*) -->$")


class DocumentationProjectionError(ValueError):
    """Raised when a persistent documentation projection cannot be produced."""


def package_version(root: Path) -> str:
    """Return the release-owned package version declared under ``root``."""

    source = root / _VERSION_SOURCE
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as error:
        raise DocumentationProjectionError(f"{_VERSION_SOURCE}: unreadable: {error}") from None
    match = _VERSION_RE.search(text)
    if match is None:
        raise DocumentationProjectionError(
            f"{_VERSION_SOURCE}: no __version__ assignment found"
        )
    return match.group("version")


def generate(root: Path, *, source_commit: str) -> dict[str, str]:
    """Return every persistent projection generated from one frozen input."""

    if not _COMMIT_RE.fullmatch(source_commit):
        raise DocumentationProjectionError(
            "source commit must be an exact lowercase 40-character commit identity"
        )
    try:
        declarations = load_declarations(root)
    except AuthorityError as error:
        raise DocumentationProjectionError(
            f"repository authority must be valid before projection:\n{error}"
        ) from None

    version = package_version(root)
    return {
        "ARCHITECTURE.md": _render_architecture(declarations, source_commit, version),
    }


def write_projections(root: Path, *, source_commit: str) -> tuple[str, ...]:
    """Materialize the persistent projections under ``root``."""

    generated = generate(root, source_commit=source_commit)
    for name, text in sorted(generated.items()):
        (root / name).write_text(text, encoding="utf-8")
    return tuple(sorted(generated))


def projection_drift(root: Path, *, source_commit: str) -> tuple[str, ...]:
    """Return sorted drift messages between committed and generated projections."""

    generated = generate(root, source_commit=source_commit)
    messages: list[str] = []
    for name, text in sorted(generated.items()):
        path = root / name
        if not path.is_file():
            messages.append(f"{name}: persistent projection has not been materialized")
            continue
        if path.read_text(encoding="utf-8") != text:
            messages.append(
                f"{name}: committed projection does not match generation from"
                f" {source_commit}"
            )
    return tuple(messages)


def provenance_of(text: str) -> dict[str, str]:
    """Return the machine-readable provenance recorded in a generated document."""

    provenance: dict[str, str] = {}
    for line in text.splitlines():
        match = _PROVENANCE_RE.fullmatch(line)
        if match is not None:
            provenance[match.group("key")] = match.group("value")
    return provenance


def _render_architecture(
    declarations: Sequence[Declaration], source_commit: str, version: str
) -> str:
    derived = consumers_of(declarations)
    lines = [
        "# RelayLM 1.0 Architecture",
        "",
        f"<!-- generated-by: {_ARCHITECTURE_GENERATOR} -->",
        f"<!-- projection-schema-version: {PROJECTION_SCHEMA_VERSION} -->",
        f"<!-- source-commit: {source_commit} -->",
        f"<!-- package-version: {version} -->",
        "",
        "This document is a generated projection of RelayLM `v1` repository authority.",
        "It is materialized at a version/release boundary from the frozen input commit",
        "recorded above and is not hand-maintained. For each area the canonical",
        "authority is the surface named under it, not this summary.",
        "",
        "## Semantic owners",
        "",
    ]

    for declaration in declarations:
        lines.extend([f"### {declaration.id}", "", declaration.summary, ""])
        if declaration.owner_issue is not None:
            lines.append(f"- owning Issue: #{declaration.owner_issue}")
        lines.append(f"- canonical authority: {_paths(declaration.canonical_surfaces)}")
        lines.append(f"- depends on: {_names(declaration.depends_on)}")
        lines.append(f"- consumed by: {_names(derived.get(declaration.id, ()))}")
        if declaration.evidence:
            lines.append(
                "- evidence produced: "
                + _names(sorted(record.id for record in declaration.evidence))
            )
        if declaration.evidence_refs:
            lines.append("- evidence referenced: " + _names(declaration.evidence_refs))
        lines.append("")

    lines.extend(["## Dependency graph", "", "```mermaid", "graph LR"])
    edges = [
        (declaration.id, dependency)
        for declaration in declarations
        for dependency in sorted(declaration.depends_on)
    ]
    sources = {source for source, _ in edges}
    for source, target in sorted(edges):
        lines.append(f"  {source} --> {target}")
    for declaration in declarations:
        if declaration.id not in sources:
            lines.append(f"  {declaration.id}")
    lines.extend(["```", ""])
    return "\n".join(lines)


def _paths(values: Sequence[str]) -> str:
    return ", ".join(f"`{value}`" for value in sorted(values)) if values else "none"


def _names(values: Sequence[str]) -> str:
    return ", ".join(sorted(values)) if values else "none"


def _resolve_commit(root: Path, requested: str | None) -> str:
    if requested is not None:
        return requested
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise DocumentationProjectionError(
            "no --commit given and the input commit could not be resolved from git"
        )
    return result.stdout.strip()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument(
        "--commit",
        default=None,
        help="frozen projection input commit; defaults to the current git HEAD",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    render = subparsers.add_parser("render", help="print one generated projection")
    render.add_argument("name", choices=PERSISTENT_PROJECTIONS)
    subparsers.add_parser("write", help="materialize the persistent projections")
    subparsers.add_parser("check", help="verify committed projections match generation")

    arguments = parser.parse_args(argv)
    try:
        commit = _resolve_commit(arguments.root, arguments.commit)
        if arguments.command == "render":
            print(generate(arguments.root, source_commit=commit)[arguments.name], end="")
            return 0
        if arguments.command == "write":
            for name in write_projections(arguments.root, source_commit=commit):
                print(f"wrote {name} from {commit}")
            return 0
        drift = projection_drift(arguments.root, source_commit=commit)
        for message in drift:
            print(message, file=sys.stderr)
        if drift:
            print(
                "regenerate with: python -m tools.repository_docs"
                f" --commit {commit} write",
                file=sys.stderr,
            )
            return 1
        print(f"persistent documentation projection matches {commit}")
        return 0
    except DocumentationProjectionError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
