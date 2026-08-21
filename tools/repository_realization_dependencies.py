#!/usr/bin/env python3
"""Audit RelayLM-internal realization dependencies against semantic authority."""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath

from tools.repository_authority import AuthorityError, Declaration, load_declarations

PRODUCTION_PACKAGE_DIRECTORY = "src/relaylm"
PACKAGE_ROOT = "relaylm"


def realization_dependency_errors(root: Path) -> tuple[str, ...]:
    """Return unexplained static RelayLM-internal realization dependency edges.

    Production module ownership is read from existing ``implementation``
    declarations. A static internal import is structurally explained when the
    importing and imported modules share an owner or when any importing owner
    can reach any imported owner through semantic ``depends_on`` edges.

    This audit derives realization edges from code. It never mutates or infers
    semantic authority.
    """

    declarations = load_declarations(root)
    module_paths = _production_module_paths(root)
    owners_by_path = _implementation_owners(declarations)
    dependencies = {item.id: frozenset(item.depends_on) for item in declarations}

    errors: set[str] = set()
    for importer_module, importer_path in sorted(module_paths.items()):
        importer_owners = owners_by_path.get(importer_path, frozenset())
        for imported_module in _internal_imports(root / importer_path, importer_module, module_paths):
            imported_path = module_paths[imported_module]
            imported_owners = owners_by_path.get(imported_path, frozenset())
            if _edge_is_explained(
                importer_owners,
                imported_owners,
                dependencies,
            ):
                continue
            errors.add(
                f"{importer_path} -> {imported_path}: realization dependency is unexplained "
                f"(importer owners: {_format_owners(importer_owners)}; "
                f"imported owners: {_format_owners(imported_owners)})"
            )
    return tuple(sorted(errors))


def _production_module_paths(root: Path) -> dict[str, str]:
    package = root / PRODUCTION_PACKAGE_DIRECTORY
    if not package.is_dir():
        return {}

    modules: dict[str, str] = {}
    for candidate in sorted(package.rglob("*.py")):
        if candidate.name == "__init__.py":
            continue
        relative = candidate.relative_to(root).as_posix()
        module = _module_name(relative)
        modules[module] = relative
    return modules


def _module_name(relative: str) -> str:
    path = PurePosixPath(relative)
    package_relative = path.relative_to("src").with_suffix("")
    return ".".join(package_relative.parts)


def _implementation_owners(
    declarations: Sequence[Declaration],
) -> dict[str, frozenset[str]]:
    owners: dict[str, set[str]] = {}
    for declaration in declarations:
        for surface in declaration.implementation:
            owners.setdefault(surface, set()).add(declaration.id)
    return {path: frozenset(ids) for path, ids in owners.items()}


def _internal_imports(
    path: Path,
    importer_module: str,
    module_paths: Mapping[str, str],
) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in module_paths:
                    imports.add(alias.name)
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        base = _resolve_from_base(importer_module, node.level, node.module)
        if base is None or not base.startswith(PACKAGE_ROOT):
            continue

        if base in module_paths:
            imports.add(base)
            continue

        # ``from relaylm import module`` or ``from . import module`` names a
        # package plus an imported symbol. Resolve the symbol as a submodule
        # only when that module exists; otherwise the package-marker import is
        # outside this audit's production-module surface.
        for alias in node.names:
            candidate = f"{base}.{alias.name}"
            if candidate in module_paths:
                imports.add(candidate)

    return tuple(sorted(imports))


def _resolve_from_base(importer_module: str, level: int, module: str | None) -> str | None:
    if level == 0:
        return module

    package_parts = importer_module.split(".")[:-1]
    ascend = level - 1
    if ascend > len(package_parts):
        return None
    base_parts = package_parts[: len(package_parts) - ascend]
    if module:
        base_parts.extend(module.split("."))
    return ".".join(base_parts)


def _edge_is_explained(
    importer_owners: frozenset[str],
    imported_owners: frozenset[str],
    dependencies: Mapping[str, frozenset[str]],
) -> bool:
    if importer_owners & imported_owners:
        return True
    return any(
        _is_reachable(importer, imported, dependencies)
        for importer in importer_owners
        for imported in imported_owners
    )


def _is_reachable(
    source: str,
    target: str,
    dependencies: Mapping[str, frozenset[str]],
) -> bool:
    pending = list(dependencies.get(source, ()))
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(dependencies.get(current, ()))
    return False


def _format_owners(owners: Iterable[str]) -> str:
    values = sorted(owners)
    return ", ".join(values) if values else "<none>"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="repository root to audit"
    )
    arguments = parser.parse_args(argv)

    try:
        errors = realization_dependency_errors(arguments.root)
    except (AuthorityError, SyntaxError) as error:
        print(str(error), file=sys.stderr)
        return 1

    for message in errors:
        print(message, file=sys.stderr)
    if errors:
        return 1

    print("realization dependencies explained")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
