"""Additional subprocess invocation discovery for imported aliases.

The main invocation scanner handles the canonical ``subprocess.run`` form.
This bounded companion records calls made through module aliases such as
``import subprocess as proc`` and direct-call aliases such as
``from subprocess import run as proc_run``. Exact children remain unresolved
unless they are safely literal; the important invariant is that the dispatcher
itself is never hidden from the invocation inventory.
"""
from __future__ import annotations

import ast

from . import repo
from .records import Evidence, InvocationRecord

_METHODS = frozenset({"run", "Popen", "check_call", "check_output"})


def _bindings(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    module_aliases: set[str] = set()
    call_aliases: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess" and alias.asname:
                    module_aliases.add(alias.asname)
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            for alias in node.names:
                if alias.name in _METHODS:
                    bound = alias.asname or alias.name
                    if bound != alias.name:
                        call_aliases.add(bound)
    return frozenset(module_aliases), frozenset(call_aliases)


def _is_alias_call(
    node: ast.AST,
    module_aliases: frozenset[str],
    call_aliases: frozenset[str],
) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Attribute):
        return (
            node.func.attr in _METHODS
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in module_aliases
        )
    return isinstance(node.func, ast.Name) and node.func.id in call_aliases


def scan_subprocess_aliases() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if not (rel.startswith("relaylm/") or rel.startswith("scripts/")):
            continue
        text = repo.read_text(path)
        if text is None or "subprocess" not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        module_aliases, call_aliases = _bindings(tree)
        if not module_aliases and not call_aliases:
            continue
        lines = text.splitlines()
        for node in ast.walk(tree):
            if not _is_alias_call(node, module_aliases, call_aliases):
                continue
            lineno = getattr(node, "lineno", 1)
            snippet = (
                lines[lineno - 1].strip()[:160]
                if 1 <= lineno <= len(lines)
                else "subprocess alias call"
            )
            records.append(
                InvocationRecord(
                    root_id=f"subprocess_alias_child:{rel}:{lineno}",
                    root_kind="subprocess_child",
                    command_or_symbol="unresolved subprocess invocation",
                    source_path=rel,
                    source_line=lineno,
                    reachable_from_fastapi_import_graph=None,
                    notes=[
                        "Subprocess dispatcher discovered through an imported module or call alias; "
                        "the exact child is dynamically assembled and remains unresolved."
                    ],
                    evidence=[Evidence(rel, lineno, snippet)],
                    heuristic_fields=["command_or_symbol"],
                )
            )
    records.sort(key=lambda record: record.sort_key())
    return records
