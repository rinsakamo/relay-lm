"""Part B: invocation-root inventory.

This module discovers places where code in the repository is *invoked from*:
FastAPI routes, console scripts, ``python -m`` entry points, operator CLIs,
GitHub Actions steps, subprocess children, registries, pytest/smoke roots,
frontend package.json scripts and routes, static/package assets, and
dynamically resolved imports.

Absence of a module from the shallow FastAPI import-graph heuristic
(``reachable_from_fastapi_import_graph``) is never treated as evidence that
the module is dead. Many legitimate invocation roots in this repository
(operator CLIs, workflow commands, schedulers, migration tooling) are never
imported by ``relaylm/app.py`` at all -- that is expected, not a defect.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from . import repo
from .records import Evidence, InvocationRecord

_FASTAPI_METHODS = frozenset({"get", "post", "put", "delete", "patch", "options", "head", "websocket"})
_MAIN_GUARD_RE = re.compile(r'^\s*if\s+__name__\s*==\s*["\']__main__["\']\s*:')
_ARGPARSE_FLAG_RE = re.compile(r'add_argument\(\s*["\'](--[\w-]+)["\']')
_DYNAMIC_IMPORT_RE = re.compile(r"(importlib\.import_module\(|__import__\()")
_ROUTE_PATH_RE = re.compile(r'path:\s*["\']([^"\']+)["\']')
_JSX_ROUTE_RE = re.compile(r'<Route\s+[^>]*path=["\']([^"\']+)["\']')
_NAVIGATION_START_RE = re.compile(r"\bconst\s+navigation\b[^=]*=\s*\[")
_NAVIGATION_ROUTE_RE = re.compile(r'\broute:\s*["\']([^"\']+)["\']')
_SUBPROCESS_METHODS = frozenset({"run", "Popen", "check_call", "check_output"})


def _module_dotted_name(path: Path) -> str:
    rel = repo.relative(path)
    assert rel.startswith("relaylm/")
    stem = rel[: -len(".py")] if rel.endswith(".py") else rel
    return stem.replace("/", ".")


def _read_python_ast(path: Path) -> tuple[str, ast.Module] | None:
    text = repo.read_text(path)
    if text is None:
        return None
    try:
        return text, ast.parse(text)
    except SyntaxError:
        return None


def _line_snippet(lines: list[str], lineno: int, fallback: str = "") -> str:
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()[:160]
    return fallback[:160]


def scan_fastapi_routes() -> list[InvocationRecord]:
    """Discover single- and multi-line FastAPI decorators via the Python AST."""
    records: list[InvocationRecord] = []
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if not rel.startswith("relaylm/"):
            continue
        parsed = _read_python_ast(path)
        if parsed is None:
            continue
        text, tree = parsed
        if "@app." not in text and "@router." not in text:
            continue
        lines = text.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                owner = decorator.func.value
                method = decorator.func.attr
                if method not in _FASTAPI_METHODS or not isinstance(owner, ast.Name) or owner.id not in {"app", "router"}:
                    continue
                if not decorator.args:
                    continue
                route_arg = decorator.args[0]
                if not isinstance(route_arg, ast.Constant) or not isinstance(route_arg.value, str):
                    continue
                route_path = route_arg.value
                lineno = getattr(decorator, "lineno", getattr(node, "lineno", 1))
                root_id = f"fastapi:{method}:{route_path}"
                records.append(
                    InvocationRecord(
                        root_id=root_id,
                        root_kind="fastapi_route",
                        command_or_symbol=f"{method.upper()} {route_path}",
                        source_path=rel,
                        source_line=lineno,
                        reachable_from_fastapi_import_graph=None,
                        notes=[
                            "Direct FastAPI decorator discovered from the Python AST; "
                            "core-app reachability is populated separately."
                        ],
                        evidence=[Evidence(rel, lineno, _line_snippet(lines, lineno, f"@{owner.id}.{method}(..."))],
                        heuristic_fields=["reachable_from_fastapi_import_graph"],
                    )
                )
    return records


def scan_console_scripts() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    pyproject = repo.ROOT / "pyproject.toml"
    text = repo.read_text(pyproject)
    if text is None:
        return records
    lines = text.splitlines()
    in_section = False
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("["):
            in_section = stripped == "[project.scripts]"
            continue
        if not in_section or not stripped or stripped.startswith("#"):
            continue
        match = re.match(r'([\w.-]+)\s*=\s*"([^"]+)"', stripped)
        if not match:
            continue
        name, target = match.group(1), match.group(2)
        records.append(
            InvocationRecord(
                root_id=f"console_script:{name}",
                root_kind="console_script",
                command_or_symbol=f"{name} -> {target}",
                source_path="pyproject.toml",
                source_line=lineno,
                reachable_from_fastapi_import_graph=None,
                notes=["Installed console entry point from [project.scripts]."],
                evidence=[Evidence("pyproject.toml", lineno, stripped[:160])],
                heuristic_fields=[],
            )
        )
    return records


def scan_python_dash_m_and_operator_cli() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if not (rel.startswith("relaylm/") or rel.startswith("scripts/")):
            continue
        text = repo.read_text(path)
        if text is None:
            continue
        lines = text.splitlines()
        main_line = None
        for lineno, line in enumerate(lines, start=1):
            if _MAIN_GUARD_RE.match(line):
                main_line = lineno
                break
        if main_line is None:
            continue
        name = path.name
        category_hints = []
        for token, label in (
            ("migrat", "migration"),
            ("maintenance", "maintenance"),
            ("generate", "generator"),
            ("benchmark", "benchmark"),
            ("registry", "registry-adjacent"),
        ):
            if token in name.lower():
                category_hints.append(label)
        if rel.startswith("relaylm/"):
            dotted = _module_dotted_name(path)
            root_kind = "python_dash_m"
            command = f"python -m {dotted}"
            note = "Package module runnable via `python -m`; not necessarily imported by app.py."
        else:
            root_kind = "operator_cli"
            command = f"python {rel}"
            note = "Operator CLI script; invoked directly, not through the FastAPI import graph."
        if name.endswith("_smoke.py"):
            root_kind = "smoke_only_root"
            note = (
                "Filename indicates a smoke-only entry point. Smoke-only status is "
                "not evidence the underlying capability is dead or unused."
            )
        notes = [note]
        if category_hints:
            notes.append("Heuristic category hint(s) from filename: " + ", ".join(sorted(set(category_hints))) + ".")
        flags = sorted({m.group(1) for m in _ARGPARSE_FLAG_RE.finditer(text)})
        if flags:
            notes.append("Observed argparse flags: " + ", ".join(flags) + ".")
        records.append(
            InvocationRecord(
                root_id=f"{root_kind}:{rel}",
                root_kind=root_kind,
                command_or_symbol=command,
                source_path=rel,
                source_line=main_line,
                reachable_from_fastapi_import_graph=None,
                notes=notes,
                evidence=[Evidence(rel, main_line, lines[main_line - 1].strip()[:160])],
                heuristic_fields=["notes"] if category_hints else [],
            )
        )
    return records


def _normalized_run_command(run_text: str) -> str:
    lines = [line.rstrip() for line in run_text.strip().splitlines()]
    return "\n".join(line for line in lines if line.strip())


def scan_github_actions_commands() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    workflows_dir = repo.ROOT / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return records
    try:
        import yaml
    except ImportError:
        return records
    for path in sorted(workflows_dir.glob("*.y*ml")):
        rel = repo.relative(path)
        text = repo.read_text(path)
        if text is None:
            continue
        lines = text.splitlines()
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        jobs = doc.get("jobs") or {}
        if not isinstance(jobs, dict):
            continue
        for job_name, job in sorted(jobs.items()):
            if not isinstance(job, dict):
                continue
            steps = job.get("steps") or []
            if not isinstance(steps, list):
                continue
            for step_index, step in enumerate(steps):
                if not isinstance(step, dict) or "run" not in step:
                    continue
                run_text = step.get("run")
                if not isinstance(run_text, str):
                    continue
                command = _normalized_run_command(run_text)
                if not command:
                    continue
                step_name = step.get("name") or f"step-{step_index}"
                command_lines = command.splitlines()
                anchor = next(
                    (line.strip() for line in command_lines if line.strip() and not line.lstrip().startswith(("set ", "#"))),
                    command_lines[0].strip(),
                )
                lineno = 1
                for idx, line in enumerate(lines, start=1):
                    if anchor[:40] and anchor[:40] in line:
                        lineno = idx
                        break
                root_id = f"github_actions:{rel}:{job_name}:{step_index}"
                records.append(
                    InvocationRecord(
                        root_id=root_id,
                        root_kind="github_actions_step",
                        command_or_symbol=command,
                        source_path=rel,
                        source_line=lineno,
                        reachable_from_fastapi_import_graph=None,
                        notes=[
                            f"Workflow '{path.name}', job '{job_name}', step '{step_name}'.",
                            "Full normalized multi-line run command is preserved.",
                        ],
                        evidence=[Evidence(rel, lineno, anchor[:160])],
                        heuristic_fields=["source_line"],
                    )
                )
    return records


def _string_sequences(tree: ast.Module) -> dict[str, tuple[str, ...]]:
    values: dict[str, tuple[str, ...]] = {}
    for stmt in tree.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        value = stmt.value
        if not isinstance(value, (ast.Tuple, ast.List)):
            continue
        constants = tuple(
            element.value
            for element in value.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        )
        if len(constants) != len(value.elts) or not constants:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                values[target.id] = constants
    return values


def _subprocess_call(node: ast.AST) -> ast.Call | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr not in _SUBPROCESS_METHODS:
        return None
    if not isinstance(node.func.value, ast.Name) or node.func.value.id != "subprocess":
        return None
    return node


def _expr_contains_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node))


def _constant_command_parts(arg: ast.AST) -> list[str]:
    if not isinstance(arg, (ast.List, ast.Tuple)):
        return []
    parts: list[str] = []
    for element in arg.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            parts.append(element.value)
        elif isinstance(element, ast.Attribute) and isinstance(element.value, ast.Name):
            parts.append(f"{element.value.id}.{element.attr}")
        else:
            parts.append("<dynamic>")
    return parts


def _child_from_parts(parts: list[str]) -> tuple[str, str] | None:
    if not parts:
        return None
    interpreter = parts[0]
    kind = "node" if interpreter == "node" else "python" if interpreter in {"python", "python3", "sys.executable"} else interpreter
    if len(parts) >= 3 and parts[1] == "-m" and parts[2] != "<dynamic>":
        return kind, f"-m {parts[2]}"
    if len(parts) >= 2 and parts[1] != "<dynamic>":
        return kind, parts[1]
    return None


def scan_subprocess_children() -> list[InvocationRecord]:
    """Discover subprocess calls across lines and enumerate safe tuple-driven children."""
    records: list[InvocationRecord] = []
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if not (rel.startswith("relaylm/") or rel.startswith("scripts/")):
            continue
        parsed = _read_python_ast(path)
        if parsed is None:
            continue
        text, tree = parsed
        if "subprocess." not in text:
            continue
        lines = text.splitlines()
        sequences = _string_sequences(tree)
        handled_calls: set[int] = set()

        for loop in (node for node in ast.walk(tree) if isinstance(node, ast.For)):
            if not isinstance(loop.target, ast.Name) or not isinstance(loop.iter, ast.Name):
                continue
            members = sequences.get(loop.iter.id)
            if not members:
                continue
            for candidate in ast.walk(loop):
                call = _subprocess_call(candidate)
                if call is None or not call.args or not _expr_contains_name(call.args[0], loop.target.id):
                    continue
                handled_calls.add(id(call))
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
                                f"Child enumerated from static sequence '{loop.iter.id}' "
                                f"used by loop variable '{loop.target.id}'."
                            ],
                            evidence=[Evidence(rel, lineno, _line_snippet(lines, lineno, "subprocess call"))],
                            heuristic_fields=["command_or_symbol"],
                        )
                    )

        for candidate in ast.walk(tree):
            call = _subprocess_call(candidate)
            if call is None or id(call) in handled_calls:
                continue
            lineno = getattr(call, "lineno", 1)
            parts = _constant_command_parts(call.args[0]) if call.args else []
            resolved = _child_from_parts(parts)
            if resolved is not None:
                kind, child = resolved
                command = f"{kind} {child}"
                notes = ["Child process command inferred from AST call arguments."]
            else:
                command = "unresolved subprocess invocation"
                notes = [
                    "Subprocess call exists, but its exact child is dynamically assembled and "
                    "was not safely resolvable by static analysis."
                ]
            records.append(
                InvocationRecord(
                    root_id=f"subprocess_child:{rel}:{lineno}:{command}",
                    root_kind="subprocess_child",
                    command_or_symbol=command,
                    source_path=rel,
                    source_line=lineno,
                    reachable_from_fastapi_import_graph=None,
                    notes=notes,
                    evidence=[Evidence(rel, lineno, _line_snippet(lines, lineno, "subprocess call"))],
                    heuristic_fields=["command_or_symbol"],
                )
            )
    return records


def scan_registries() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if "registry" not in path.stem.lower():
            continue
        if not (rel.startswith("relaylm/") or rel.startswith("scripts/")):
            continue
        text = repo.read_text(path)
        if text is None:
            continue
        lines = text.splitlines()
        records.append(
            InvocationRecord(
                root_id=f"registry:{rel}",
                root_kind="registry",
                command_or_symbol=f"module {rel}",
                source_path=rel,
                source_line=1,
                reachable_from_fastapi_import_graph=None,
                notes=[
                    "Filename matches registry naming convention. Dynamically resolved "
                    "contents of this registry are not enumerated by static scanning; "
                    "this is a coarse heuristic pointer, not a full expansion.",
                ],
                evidence=[Evidence(rel, 1, lines[0].strip()[:160] if lines else "")],
                heuristic_fields=["root_kind", "notes"],
            )
        )
    return records


def scan_pytest_roots() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    tests_dir = repo.ROOT / "tests"
    if not tests_dir.is_dir():
        return records
    for path in repo.iter_repo_files(root=tests_dir, suffixes=(".py",)):
        rel = repo.relative(path)
        if not path.name.startswith("test_"):
            continue
        records.append(
            InvocationRecord(
                root_id=f"pytest_root:{rel}",
                root_kind="pytest_root",
                command_or_symbol=f"pytest {rel}",
                source_path=rel,
                source_line=1,
                reachable_from_fastapi_import_graph=None,
                notes=['Collected by pytest via testpaths = ["tests"] in pyproject.toml.'],
                evidence=[Evidence(rel, 1, path.name)],
                heuristic_fields=[],
            )
        )
    return records


def scan_npm_scripts() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    apps_dir = repo.ROOT / "apps"
    if not apps_dir.is_dir():
        return records
    for package_json in sorted(apps_dir.glob("*/package.json")):
        rel = repo.relative(package_json)
        text = repo.read_text(package_json)
        if text is None:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        scripts = data.get("scripts")
        if not isinstance(scripts, dict):
            continue
        lines = text.splitlines()
        for name, command in sorted(scripts.items()):
            lineno = 1
            needle = f'"{name}"'
            for idx, line in enumerate(lines, start=1):
                if needle in line:
                    lineno = idx
                    break
            records.append(
                InvocationRecord(
                    root_id=f"npm_script:{rel}:{name}",
                    root_kind="npm_script",
                    command_or_symbol=f"npm run {name} -> {command}",
                    source_path=rel,
                    source_line=lineno,
                    reachable_from_fastapi_import_graph=None,
                    notes=[f"Declared in {rel} scripts block."],
                    evidence=[Evidence(rel, lineno, f'"{name}": "{command}"'[:160])],
                    heuristic_fields=["source_line"],
                )
            )
    return records


def scan_frontend_routes() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    apps_dir = repo.ROOT / "apps"
    if not apps_dir.is_dir():
        return records
    for path in repo.iter_repo_files(root=apps_dir, suffixes=(".ts", ".tsx", ".mjs", ".js")):
        rel = repo.relative(path)
        text = repo.read_text(path)
        if text is None:
            continue
        lines = text.splitlines()
        seen: set[tuple[int, str]] = set()

        for lineno, line in enumerate(lines, start=1):
            for regex in (_ROUTE_PATH_RE, _JSX_ROUTE_RE):
                match = regex.search(line)
                if not match:
                    continue
                route_path = match.group(1)
                seen.add((lineno, route_path))

        in_navigation = False
        bracket_depth = 0
        for lineno, line in enumerate(lines, start=1):
            if not in_navigation and _NAVIGATION_START_RE.search(line):
                in_navigation = True
                bracket_depth = line.count("[") - line.count("]")
            elif in_navigation:
                bracket_depth += line.count("[") - line.count("]")
            if in_navigation:
                match = _NAVIGATION_ROUTE_RE.search(line)
                if match:
                    seen.add((lineno, f"#/{match.group(1)}"))
                if bracket_depth <= 0 and "];" in line:
                    in_navigation = False

        for lineno, route_path in sorted(seen):
            hash_route = route_path.startswith("#/")
            records.append(
                InvocationRecord(
                    root_id=f"frontend_route:{rel}:{lineno}:{route_path}",
                    root_kind="frontend_route",
                    command_or_symbol=route_path,
                    source_path=rel,
                    source_line=lineno,
                    reachable_from_fastapi_import_graph=None,
                    notes=[
                        "Canonical hash-navigation route from the bounded navigation array."
                        if hash_route
                        else "Route literal matched by a bounded frontend heuristic; may include false positives."
                    ],
                    evidence=[Evidence(rel, lineno, _line_snippet(lines, lineno, route_path))],
                    heuristic_fields=["command_or_symbol"],
                )
            )
    return records


def scan_static_and_package_data() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    candidates = [
        repo.ROOT / "relaylm" / "character_workspace",
        repo.ROOT / "apps" / "soul-lab" / "public",
        repo.ROOT / "apps" / "soul-lab" / "src" / "locales",
        repo.ROOT / "examples",
    ]
    for directory in candidates:
        if not directory.is_dir():
            continue
        rel_dir = repo.relative(directory)
        files = repo.iter_repo_files(root=directory)
        if not files:
            continue
        records.append(
            InvocationRecord(
                root_id=f"static_or_package_data:{rel_dir}",
                root_kind="static_or_package_data",
                command_or_symbol=f"directory {rel_dir} ({len(files)} file(s))",
                source_path=rel_dir,
                source_line=None,
                reachable_from_fastapi_import_graph=None,
                notes=[
                    "Directory grouped as static/package-data by a fixed candidate list, "
                    "not full package-data manifest resolution.",
                ],
                evidence=[Evidence(repo.relative(f), 1, f.name) for f in files[:5]],
                heuristic_fields=["root_kind"],
            )
        )
    return records


def scan_dynamic_imports() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if not (rel.startswith("relaylm/") or rel.startswith("scripts/")):
            continue
        text = repo.read_text(path)
        if text is None or "import_module(" not in text and "__import__(" not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not _DYNAMIC_IMPORT_RE.search(line):
                continue
            records.append(
                InvocationRecord(
                    root_id=f"dynamic_import:{rel}:{lineno}",
                    root_kind="dynamic_import",
                    command_or_symbol=line.strip()[:160],
                    source_path=rel,
                    source_line=lineno,
                    reachable_from_fastapi_import_graph=None,
                    notes=[
                        "Configuration-selected or dynamically resolved import; target "
                        "module name is not statically resolvable by this scanner.",
                    ],
                    evidence=[Evidence(rel, lineno, line.strip()[:160])],
                    heuristic_fields=["command_or_symbol"],
                )
            )
    return records


def build_import_graph(start: str, max_depth: int = 12) -> frozenset[str]:
    """Best-effort BFS over static ``relaylm.*`` imports from one entry point."""
    module_trees: dict[str, ast.Module] = {}
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if not rel.startswith("relaylm/"):
            continue
        parsed = _read_python_ast(path)
        if parsed is not None:
            module_trees[_module_dotted_name(path)] = parsed[1]

    def imports_of(dotted: str) -> set[str]:
        tree = module_trees.get(dotted)
        if tree is None:
            return set()
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("relaylm"):
                        found.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("relaylm"):
                found.add(node.module)
        return found

    visited = {start}
    frontier = {start}
    depth = 0
    while frontier and depth < max_depth:
        next_frontier: set[str] = set()
        for dotted in frontier:
            for imported in imports_of(dotted):
                if imported not in visited and imported in module_trees:
                    visited.add(imported)
                    next_frontier.add(imported)
        frontier = next_frontier
        depth += 1
    return frozenset(visited)


def build_fastapi_import_graph(max_depth: int = 12) -> frozenset[str]:
    return build_import_graph("relaylm.app", max_depth=max_depth)


def collect_all() -> list[InvocationRecord]:
    records: list[InvocationRecord] = []
    records.extend(scan_fastapi_routes())
    records.extend(scan_console_scripts())
    records.extend(scan_python_dash_m_and_operator_cli())
    records.extend(scan_github_actions_commands())
    records.extend(scan_subprocess_children())
    records.extend(scan_registries())
    records.extend(scan_pytest_roots())
    records.extend(scan_npm_scripts())
    records.extend(scan_frontend_routes())
    records.extend(scan_static_and_package_data())
    records.extend(scan_dynamic_imports())

    core_reachable = build_import_graph("relaylm.app")
    lab_reachable = build_import_graph("relaylm.soul_lab_app")
    for record in records:
        if record.root_kind not in {"python_dash_m", "fastapi_route"}:
            continue
        dotted = (
            record.source_path[: -len(".py")].replace("/", ".")
            if record.source_path.endswith(".py")
            else record.source_path
        )
        record.reachable_from_fastapi_import_graph = dotted in core_reachable
        record.heuristic_fields = sorted(
            set(record.heuristic_fields) | {"reachable_from_fastapi_import_graph"}
        )
        if dotted in lab_reachable and dotted not in core_reachable:
            record.notes.append(
                "Reachable from the SOUL Lab entry point (`relaylm.soul_lab_app`) "
                "but not from the core `relaylm.app` import graph."
            )
        elif dotted not in core_reachable:
            record.notes.append(
                "Not found in the core FastAPI import-graph heuristic. This is NOT "
                "evidence of dead code: operator CLIs, schedulers, migration tooling, "
                "and workflow-invoked modules are routinely absent from app.py's import graph."
            )

    records.sort(key=lambda r: r.sort_key())
    return records
