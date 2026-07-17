"""Final bounded hardening for invocation-root inventory output.

The original scanner intentionally uses several broad heuristics.  This module
replaces the two remaining problematic surfaces at report-build time:

* direct literal tuple/list subprocess loops are expanded into child roots;
* dynamic imports are discovered from Python AST calls, never raw strings.

It also relinks newly discovered child roots to storage records so the generated
artifact remains useful for later human review.  Nothing here makes a deletion,
migration, or liveness decision.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from . import repo
from .records import Evidence, InvocationRecord

_SUBPROCESS_METHODS = frozenset({"run", "Popen", "check_call", "check_output"})


def _read_ast(path: Path) -> tuple[str, ast.Module] | None:
    text = repo.read_text(path)
    if text is None:
        return None
    try:
        return text, ast.parse(text)
    except SyntaxError:
        return None


def _line_snippet(lines: list[str], lineno: int, fallback: str) -> str:
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()[:160]
    return fallback[:160]


def _subprocess_bindings(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    module_aliases: set[str] = set()
    call_aliases: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    module_aliases.add(alias.asname or "subprocess")
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            for alias in node.names:
                if alias.name in _SUBPROCESS_METHODS:
                    call_aliases.add(alias.asname or alias.name)
    return frozenset(module_aliases), frozenset(call_aliases)


def _is_subprocess_call(
    node: ast.AST,
    module_aliases: frozenset[str],
    call_aliases: frozenset[str],
) -> ast.Call | None:
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Attribute):
        if (
            node.func.attr in _SUBPROCESS_METHODS
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in module_aliases
        ):
            return node
    elif isinstance(node.func, ast.Name) and node.func.id in call_aliases:
        return node
    return None


def _expr_contains_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node))


def _literal_string_members(node: ast.AST) -> tuple[str, ...]:
    if not isinstance(node, (ast.Tuple, ast.List)):
        return ()
    members = tuple(
        element.value
        for element in node.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    )
    return members if len(members) == len(node.elts) else ()


def scan_literal_loop_subprocess_children() -> list[InvocationRecord]:
    """Expand subprocess loops whose iterable is a literal tuple or list."""
    records: list[InvocationRecord] = []
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if not (rel.startswith("relaylm/") or rel.startswith("scripts/")):
            continue
        parsed = _read_ast(path)
        if parsed is None:
            continue
        text, tree = parsed
        if "subprocess" not in text:
            continue
        module_aliases, call_aliases = _subprocess_bindings(tree)
        if not module_aliases and not call_aliases:
            continue
        lines = text.splitlines()
        for loop in (node for node in ast.walk(tree) if isinstance(node, ast.For)):
            if not isinstance(loop.target, ast.Name):
                continue
            members = _literal_string_members(loop.iter)
            if not members:
                continue
            for candidate in ast.walk(loop):
                call = _is_subprocess_call(candidate, module_aliases, call_aliases)
                if call is None or not call.args:
                    continue
                if not _expr_contains_name(call.args[0], loop.target.id):
                    continue
                lineno = getattr(call, "lineno", 1)
                for child in members:
                    records.append(
                        InvocationRecord(
                            root_id=f"subprocess_child:{rel}:{lineno}:{child}",
                            root_kind="subprocess_child",
                            command_or_symbol=f"python {child}",
                            source_path=rel,
                            source_line=lineno,
                            reachable_from_fastapi_import_graph=None,
                            notes=[
                                "Child enumerated from a direct literal tuple/list "
                                f"used by loop variable '{loop.target.id}'."
                            ],
                            evidence=[
                                Evidence(
                                    rel,
                                    lineno,
                                    _line_snippet(lines, lineno, "subprocess call"),
                                )
                            ],
                            heuristic_fields=["command_or_symbol"],
                        )
                    )
    records.sort(key=lambda record: record.sort_key())
    return records


def _dynamic_import_bindings(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    module_aliases: set[str] = set()
    call_aliases: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib":
                    module_aliases.add(alias.asname or "importlib")
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    call_aliases.add(alias.asname or "import_module")
    return frozenset(module_aliases), frozenset(call_aliases)


def _dynamic_import_call(
    node: ast.AST,
    module_aliases: frozenset[str],
    call_aliases: frozenset[str],
) -> tuple[ast.Call, str] | None:
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Attribute):
        if (
            node.func.attr == "import_module"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in module_aliases
        ):
            return node, f"{node.func.value.id}.import_module"
    elif isinstance(node.func, ast.Name):
        if node.func.id in call_aliases or node.func.id == "__import__":
            return node, node.func.id
    return None


def scan_dynamic_import_calls() -> list[InvocationRecord]:
    """Discover actual dynamic-import calls while ignoring strings/comments."""
    records: list[InvocationRecord] = []
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if not (rel.startswith("relaylm/") or rel.startswith("scripts/")):
            continue
        parsed = _read_ast(path)
        if parsed is None:
            continue
        text, tree = parsed
        if "import_module" not in text and "__import__" not in text:
            continue
        module_aliases, call_aliases = _dynamic_import_bindings(tree)
        lines = text.splitlines()
        for node in ast.walk(tree):
            found = _dynamic_import_call(node, module_aliases, call_aliases)
            if found is None:
                continue
            call, callee = found
            lineno = getattr(call, "lineno", 1)
            target: str | None = None
            if call.args:
                first = call.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    target = first.value
            command = f"{callee}({target!r})" if target is not None else f"{callee}(<dynamic>)"
            notes = [
                "Dynamic import call discovered from the Python AST; comments and string "
                "literals are excluded."
            ]
            heuristic_fields: list[str] = []
            if target is None:
                notes.append("The target module name is dynamically assembled and remains unresolved.")
                heuristic_fields.append("command_or_symbol")
            records.append(
                InvocationRecord(
                    root_id=f"dynamic_import:{rel}:{lineno}:{target or 'unresolved'}",
                    root_kind="dynamic_import",
                    command_or_symbol=command,
                    source_path=rel,
                    source_line=lineno,
                    reachable_from_fastapi_import_graph=None,
                    notes=notes,
                    evidence=[
                        Evidence(
                            rel,
                            lineno,
                            _line_snippet(lines, lineno, command),
                        )
                    ],
                    heuristic_fields=heuristic_fields,
                )
            )
    records.sort(key=lambda record: record.sort_key())
    return records


def _dict_sort_key(record: dict) -> tuple:
    return (
        str(record.get("root_kind", "")),
        str(record.get("source_path", "")),
        int(record.get("source_line") or -1),
        str(record.get("root_id", "")),
    )


def harden_inventory_dicts(
    storage: list[dict] | None,
    invocations: list[dict] | None,
) -> tuple[list[dict] | None, list[dict] | None]:
    """Replace broad dynamic-import hits and add literal-loop child roots."""
    if invocations is None:
        return storage, invocations

    hardened = [dict(record) for record in invocations if record.get("root_kind") != "dynamic_import"]
    additions = [
        record.to_dict()
        for record in (
            scan_literal_loop_subprocess_children() + scan_dynamic_import_calls()
        )
    ]
    by_id = {str(record.get("root_id")): record for record in hardened}
    for record in additions:
        by_id[str(record.get("root_id"))] = record
    hardened = sorted(by_id.values(), key=_dict_sort_key)

    if storage is not None:
        child_additions = [
            record for record in additions if record.get("root_kind") == "subprocess_child"
        ]
        for storage_record in storage:
            roots = set(storage_record.get("invocation_roots") or [])
            source_path = str(storage_record.get("source_path") or "")
            source_stem = Path(source_path).stem
            for root in child_additions:
                command = str(root.get("command_or_symbol") or "")
                if source_path and (source_path in command or source_stem in command):
                    roots.add(str(root["root_id"]))
            storage_record["invocation_roots"] = sorted(roots)

    return storage, hardened
