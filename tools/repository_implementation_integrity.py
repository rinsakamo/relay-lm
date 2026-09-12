from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path


PRODUCTION_ROOTS = ("src", "tools")
_SEQUENCE_MUTATORS = frozenset(
    {
        "append",
        "clear",
        "extend",
        "insert",
        "pop",
        "remove",
        "reverse",
        "__setitem__",
        "__delitem__",
    }
)
_MAPPING_MUTATORS = frozenset(
    {
        "clear",
        "pop",
        "popitem",
        "setdefault",
        "update",
        "__setitem__",
        "__delitem__",
    }
)


@dataclass(frozen=True, order=True, slots=True)
class ImplementationIntegrityViolation:
    path: str
    line: int
    code: str
    message: str


class _ImplementationIntegrityVisitor(ast.NodeVisitor):
    def __init__(self, *, path: str) -> None:
        self.path = path
        self.violations: list[ImplementationIntegrityViolation] = []
        self._sys_names = {"sys"}
        self._sys_modules_names: set[str] = set()
        self._sys_meta_path_names: set[str] = set()
        self._sys_path_hooks_names: set[str] = set()
        self._builtins_names = {"builtins"}
        self._builtins_import_names: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            imported = alias.name
            bound = alias.asname or imported.split(".", 1)[0]
            if imported == "sys":
                self._sys_names.add(bound)
            if imported == "builtins":
                self._builtins_names.add(bound)
            if _is_forbidden_test_instrumentation_import(imported):
                self._add(
                    node,
                    "RGI001",
                    f"production implementation imports test/mock instrumentation: {imported}",
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if _is_forbidden_test_instrumentation_import(module):
            self._add(
                node,
                "RGI001",
                f"production implementation imports test/mock instrumentation: {module}",
            )
        if module == "unittest" and any(alias.name == "mock" for alias in node.names):
            self._add(
                node,
                "RGI001",
                "production implementation imports unittest.mock instrumentation",
            )
        if module == "sys":
            for alias in node.names:
                bound = alias.asname or alias.name
                if alias.name == "modules":
                    self._sys_modules_names.add(bound)
                elif alias.name == "meta_path":
                    self._sys_meta_path_names.add(bound)
                elif alias.name == "path_hooks":
                    self._sys_path_hooks_names.add(bound)
        if module == "builtins":
            for alias in node.names:
                if alias.name == "__import__":
                    self._builtins_import_names.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in {"setattr", "delattr"}:
            self._check_dynamic_attribute_replacement(node)
        if isinstance(node.func, ast.Attribute):
            if self._is_sys_modules(node.func.value) and node.func.attr in _MAPPING_MUTATORS:
                self._add(
                    node,
                    "RGI003",
                    "production implementation mutates sys.modules at runtime",
                )
            if self._is_import_hook_collection(node.func.value) and node.func.attr in _SEQUENCE_MUTATORS:
                self._add(
                    node,
                    "RGI004",
                    "production implementation mutates Python import hooks at runtime",
                )
            if _root_name(node.func.value) == "monkeypatch":
                self._add(
                    node,
                    "RGI005",
                    "production implementation invokes monkeypatch-style runtime substitution",
                )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._check_mutation_target(target, node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_mutation_target(node.target, node)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check_mutation_target(node.target, node)
        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            self._check_mutation_target(target, node)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        if node.arg == "monkeypatch":
            self._add(
                node,
                "RGI005",
                "production implementation declares a monkeypatch runtime dependency",
            )
        self.generic_visit(node)

    def _check_dynamic_attribute_replacement(self, node: ast.Call) -> None:
        if len(node.args) < 2:
            return
        name = node.args[1]
        if not isinstance(name, ast.Constant) or not isinstance(name.value, str):
            return
        attribute = name.value
        target = node.args[0]
        if self._is_sys(target) and attribute == "modules":
            self._add(
                node,
                "RGI003",
                "production implementation replaces sys.modules at runtime",
            )
            return
        if self._is_sys(target) and attribute in {"meta_path", "path_hooks"}:
            self._add(
                node,
                "RGI004",
                "production implementation replaces Python import hooks at runtime",
            )
            return
        if attribute == "__import__" and self._is_builtins(target):
            self._add(
                node,
                "RGI004",
                "production implementation replaces builtins.__import__ at runtime",
            )
            return
        if attribute.startswith("_") and not attribute.startswith("__"):
            self._add(
                node,
                "RGI002",
                f"production implementation dynamically replaces private attribute {attribute!r}",
            )

    def _check_mutation_target(self, target: ast.expr, node: ast.AST) -> None:
        if isinstance(target, ast.Subscript):
            if self._is_sys_modules(target.value):
                self._add(
                    node,
                    "RGI003",
                    "production implementation mutates sys.modules at runtime",
                )
                return
            if self._is_import_hook_collection(target.value):
                self._add(
                    node,
                    "RGI004",
                    "production implementation mutates Python import hooks at runtime",
                )
                return
        if self._is_sys_modules(target):
            self._add(
                node,
                "RGI003",
                "production implementation replaces sys.modules at runtime",
            )
            return
        if self._is_import_hook_collection(target):
            self._add(
                node,
                "RGI004",
                "production implementation replaces Python import hooks at runtime",
            )
            return
        if self._is_builtins_import(target):
            self._add(
                node,
                "RGI004",
                "production implementation replaces builtins.__import__ at runtime",
            )

    def _is_sys(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and node.id in self._sys_names

    def _is_sys_modules(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._sys_modules_names
        return isinstance(node, ast.Attribute) and node.attr == "modules" and self._is_sys(node.value)

    def _is_import_hook_collection(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._sys_meta_path_names or node.id in self._sys_path_hooks_names
        return (
            isinstance(node, ast.Attribute)
            and node.attr in {"meta_path", "path_hooks"}
            and self._is_sys(node.value)
        )

    def _is_builtins(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and node.id in self._builtins_names

    def _is_builtins_import(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._builtins_import_names
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "__import__"
            and self._is_builtins(node.value)
        )

    def _add(self, node: ast.AST, code: str, message: str) -> None:
        self.violations.append(
            ImplementationIntegrityViolation(
                path=self.path,
                line=getattr(node, "lineno", 1),
                code=code,
                message=message,
            )
        )


def _is_forbidden_test_instrumentation_import(module: str) -> bool:
    return (
        module == "pytest"
        or module.startswith("pytest.")
        or module == "mock"
        or module.startswith("mock.")
        or module == "unittest.mock"
        or module.startswith("unittest.mock.")
    )


def _root_name(node: ast.AST) -> str | None:
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def iter_production_python_paths(repo_root: Path) -> Iterable[Path]:
    for root_name in PRODUCTION_ROOTS:
        root = repo_root / root_name
        if not root.is_dir():
            continue
        yield from sorted(path for path in root.rglob("*.py") if path.is_file())


def scan_python_source(
    *,
    source: str,
    path: str = "<memory>",
) -> tuple[ImplementationIntegrityViolation, ...]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return (
            ImplementationIntegrityViolation(
                path=path,
                line=exc.lineno or 1,
                code="RGI000",
                message="production implementation is not valid Python syntax",
            ),
        )
    visitor = _ImplementationIntegrityVisitor(path=path)
    visitor.visit(tree)
    return tuple(sorted(set(visitor.violations)))


def scan_repository(repo_root: Path) -> tuple[ImplementationIntegrityViolation, ...]:
    root = repo_root.resolve()
    violations: list[ImplementationIntegrityViolation] = []
    for path in iter_production_python_paths(root):
        relative = path.relative_to(root).as_posix()
        violations.extend(
            scan_python_source(
                source=path.read_text(encoding="utf-8"),
                path=relative,
            )
        )
    return tuple(sorted(set(violations)))


def _format_violation(violation: ImplementationIntegrityViolation) -> str:
    return f"{violation.path}:{violation.line}: {violation.code} {violation.message}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reject mechanically detectable runtime substitution in RelayLM production surfaces."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="RelayLM repository root (defaults to this checkout)",
    )
    args = parser.parse_args(argv)
    violations = scan_repository(Path(args.repo_root))
    for violation in violations:
        print(_format_violation(violation))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
