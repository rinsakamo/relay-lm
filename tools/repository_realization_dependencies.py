#!/usr/bin/env python3
"""Audit RelayLM-internal runtime realization dependencies against semantic authority."""

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
    """Return unexplained static RelayLM-internal runtime realization edges."""

    errors, _ = _audit_realization_dependencies(root)
    return errors


def realization_dependency_review_signals(root: Path) -> tuple[str, ...]:
    """Return transitive-only runtime edges that merit architecture review."""

    _, review_signals = _audit_realization_dependencies(root)
    return review_signals


def _audit_realization_dependencies(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Classify static RelayLM-internal runtime realization edges.

    Production module ownership is read from existing ``implementation``
    declarations. Imports explicitly contained under ``TYPE_CHECKING`` are
    type/interface dependencies and are excluded from runtime edges.

    Shared owner overlap and direct semantic dependencies explain an edge.
    Transitive-only semantic reachability is reported separately as a non-gating
    review signal. Unreachable edges remain unexplained dependency errors.

    This audit derives runtime realization edges from code. It never mutates or
    infers semantic authority.
    """

    declarations = load_declarations(root)
    module_paths = _production_module_paths(root)
    owners_by_path = _implementation_owners(declarations)
    dependencies = {item.id: frozenset(item.depends_on) for item in declarations}

    errors: set[str] = set()
    review_signals: set[str] = set()
    for importer_module, importer_path in sorted(module_paths.items()):
        importer_owners = owners_by_path.get(importer_path, frozenset())
        for imported_module in _internal_imports(
            root / importer_path,
            importer_module,
            module_paths,
        ):
            imported_path = module_paths[imported_module]
            imported_owners = owners_by_path.get(imported_path, frozenset())

            if importer_owners & imported_owners:
                continue
            if _has_direct_dependency(importer_owners, imported_owners, dependencies):
                continue
            if _has_reachable_dependency(importer_owners, imported_owners, dependencies):
                review_signals.add(
                    f"{importer_path} -> {imported_path}: runtime realization dependency is "
                    f"transitive-only (importer owners: {_format_owners(importer_owners)}; "
                    f"imported owners: {_format_owners(imported_owners)})"
                )
                continue

            errors.add(
                f"{importer_path} -> {imported_path}: realization dependency is unexplained "
                f"(importer owners: {_format_owners(importer_owners)}; "
                f"imported owners: {_format_owners(imported_owners)})"
            )

    return tuple(sorted(errors)), tuple(sorted(review_signals))


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
    collector = _RuntimeImportCollector(importer_module, module_paths)
    collector.visit(tree)
    return tuple(sorted(collector.imports))


class _RuntimeImportCollector(ast.NodeVisitor):
    """Collect static internal imports that execute outside type-checking guards."""

    def __init__(
        self,
        importer_module: str,
        module_paths: Mapping[str, str],
    ) -> None:
        self.importer_module = importer_module
        self.module_paths = module_paths
        self.imports: set[str] = set()

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_guard(node.test):
            # TYPE_CHECKING is false at runtime. The body contains static typing
            # dependencies; an ``else`` branch, if present, remains runtime code.
            for entry in node.orelse:
                self.visit(entry)
            return
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in self.module_paths:
                self.imports.add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        base = _resolve_from_base(self.importer_module, node.level, node.module)
        if base is None or not base.startswith(PACKAGE_ROOT):
            return

        if base in self.module_paths:
            self.imports.add(base)
            return

        # ``from relaylm import module`` or ``from . import module`` names a
        # package plus an imported symbol. Resolve the symbol as a submodule
        # only when that module exists; otherwise the package-marker import is
        # outside this audit's production-module surface.
        for alias in node.names:
            candidate = f"{base}.{alias.name}"
            if candidate in self.module_paths:
                self.imports.add(candidate)


def _is_type_checking_guard(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return (
        isinstance(test, ast.Attribute)
        and test.attr == "TYPE_CHECKING"
        and isinstance(test.value, ast.Name)
        and test.value.id == "typing"
    )


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


def _has_direct_dependency(
    importer_owners: frozenset[str],
    imported_owners: frozenset[str],
    dependencies: Mapping[str, frozenset[str]],
) -> bool:
    return any(
        imported in dependencies.get(importer, ())
        for importer in importer_owners
        for imported in imported_owners
    )


def _has_reachable_dependency(
    importer_owners: frozenset[str],
    imported_owners: frozenset[str],
    dependencies: Mapping[str, frozenset[str]],
) -> bool:
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
        errors, review_signals = _audit_realization_dependencies(arguments.root)
    except (AuthorityError, SyntaxError) as error:
        print(str(error), file=sys.stderr)
        return 1

    for message in review_signals:
        print(f"review: {message}")
    for message in errors:
        print(message, file=sys.stderr)
    if errors:
        return 1

    if review_signals:
        print(
            "runtime realization dependencies explained with "
            f"{len(review_signals)} review signal(s)"
        )
    else:
        print("runtime realization dependencies explained")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
