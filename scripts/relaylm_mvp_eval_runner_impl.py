#!/usr/bin/env python3
"""Implementation for the explicit RelayLM MVP eval runner."""
from __future__ import annotations

import argparse
import json
import os
import subprocess as proc
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from relaylm_mvp_eval_runner_registry import (
    DOC_COMMANDS,
    E1_SCRIPTS,
    GOVERNANCE_PATTERNS,
    O1_SCRIPTS,
    REQUIRED_DOCS,
    RUNNER_FILES,
    TWO_TURN_SCRIPTS,
)

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIP = "SKIP"
STATUS_WARN = "WARN"
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CommandSpec:
    name: str
    argv: tuple[str, ...] = ()
    required: bool = True
    timeout_seconds: float = 90.0
    internal_action: str | None = None


@dataclass(frozen=True)
class CategorySpec:
    name: str
    required: bool
    commands: tuple[CommandSpec, ...]


def _ms(start: float) -> int:
    return max(0, int((time.monotonic() - start) * 1000))


def _py(script: str, *args: str, timeout_seconds: float = 90.0) -> CommandSpec:
    suffix = " " + " ".join(args) if args else ""
    return CommandSpec(
        f"python scripts/{script}{suffix}",
        (sys.executable, f"scripts/{script}", *args),
        True,
        timeout_seconds,
    )


def _description(reason: str) -> str:
    table = {
        "ok": "completed without nested output",
        "missing_script": "required script is not present",
        "missing_doc": "required documentation is not present",
        "missing_root": "repository root could not be validated",
        "duplicate_runner_role": "another MVP evaluation runner-like script is present",
        "doc_anchor_mismatch": "required documentation authority anchor is missing",
        "local_mode_unsupported": "local mode is intentionally unsupported in this slice",
        "governance_smoke_gap": "one or more governance groups had no matching smoke",
        "exit_nonzero": "command exited with non-zero status",
        "timeout": "command timed out",
        "exception": "command failed before completion",
        "skipped_optional_missing": "optional command target is not present",
    }
    return table.get(reason, "bounded runner status")


def _result(command: CommandSpec, status: str, start: float, reason: str) -> dict[str, object]:
    return {
        "name": command.name,
        "required": command.required,
        "status": status,
        "elapsed_ms": _ms(start),
        "failure_reason_id": "none" if status == STATUS_PASS else reason,
        "description": _description(reason),
    }


def _read(path: Path) -> str:
    data = path.read_bytes()
    if len(data) > 131_072:
        raise ValueError("too_large")
    return data.decode("utf-8")


def _preflight(root: Path, command: CommandSpec) -> dict[str, object]:
    start = time.monotonic()
    if not (root / "relaylm").is_dir() or not (root / "scripts").is_dir():
        return _result(command, STATUS_FAIL, start, "missing_root")
    if any(not (root / relative).is_file() for relative in REQUIRED_DOCS):
        return _result(command, STATUS_FAIL, start, "missing_doc")
    try:
        project_status = _read(root / "docs" / "PROJECT_STATUS.md")
        execution_plan = _read(root / "docs" / "architecture" / "project_execution_plan.md")
        e1_doc = _read(root / "docs" / "architecture" / "e1_evaluation_consolidation.md")
    except Exception:
        return _result(command, STATUS_FAIL, start, "missing_doc")
    anchors = (
        (project_status, "O2 supervised worker service: complete as opt-in supervised local scheduler service wrapping O1E; not app-embedded, not default-on, and no new memory mutation authority"),
        (project_status, "O3 always-on local operation: complete as opt-in local CLI/process wrapper around O2; not browser authority, not app-embedded, and not default-on"),
        (project_status, "E1-R5 Primary MEM recall candidate fallback: complete"),
        (execution_plan, "O2 supervised worker service             complete as opt-in local scheduler service"),
        (execution_plan, "O3 always-on local operation             complete as opt-in local CLI/process wrapper"),
        (execution_plan, "E1-R5 Primary MEM recall candidate discovery fallback complete"),
        (e1_doc, "scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py"),
        (e1_doc, "does not require a live LLM"),
    )
    if any(anchor not in body for body, anchor in anchors):
        return _result(command, STATUS_FAIL, start, "doc_anchor_mismatch")
    runner_like = {
        path.name
        for pattern in ("*mvp*eval*", "*evaluation*runner*")
        for path in (root / "scripts").glob(pattern)
        if path.is_file()
    }
    if any(name not in RUNNER_FILES for name in runner_like):
        return _result(command, STATUS_FAIL, start, "duplicate_runner_role")
    return _result(command, STATUS_PASS, start, "ok")


def _governance_scripts(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    found: set[str] = set()
    missing: list[str] = []
    for group, patterns in GOVERNANCE_PATTERNS.items():
        group_found = {
            path.name
            for pattern in patterns
            for path in (root / "scripts").glob(pattern)
            if path.is_file()
        }
        if group_found:
            found.update(group_found)
        else:
            missing.append(group)
    return tuple(sorted(found)), tuple(missing)


def _run_single(root: Path, command: CommandSpec) -> dict[str, object]:
    if command.internal_action == "static_preflight":
        return _preflight(root, command)
    if command.internal_action == "governance_discovery":
        start = time.monotonic()
        _found, missing = _governance_scripts(root)
        return _result(
            command,
            STATUS_WARN if missing else STATUS_PASS,
            start,
            "governance_smoke_gap" if missing else "ok",
        )
    if command.internal_action == "local_unsupported":
        return _result(command, STATUS_FAIL, time.monotonic(), "local_mode_unsupported")
    return _run_process(root, command)


def _run_process(root: Path, command: CommandSpec) -> dict[str, object]:
    start = time.monotonic()
    for part in command.argv[1:]:
        if part.startswith("scripts/") and part.endswith(".py") and not (root / part).is_file():
            return _result(
                command,
                STATUS_FAIL if command.required else STATUS_SKIP,
                start,
                "missing_script" if command.required else "skipped_optional_missing",
            )
    env = os.environ.copy()
    env["PYTHONPATH"] = ".:scripts" if not env.get("PYTHONPATH") else f".:scripts:{env['PYTHONPATH']}"
    try:
        completed = proc.run(
            list(command.argv),
            cwd=root,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=command.timeout_seconds,
        )
    except proc.TimeoutExpired:
        return _result(command, STATUS_FAIL, start, "timeout")
    except Exception:
        return _result(command, STATUS_FAIL, start, "exception")
    if completed.returncode != 0:
        return _result(command, STATUS_FAIL, start, "exit_nonzero")
    return _result(command, STATUS_PASS, start, "ok")


def _category_status(results: Sequence[dict[str, object]], required: bool) -> str:
    if not results:
        return STATUS_FAIL if required else STATUS_SKIP
    statuses = [item["status"] for item in results]
    if STATUS_FAIL in statuses:
        return STATUS_FAIL
    if STATUS_WARN in statuses:
        return STATUS_WARN
    if all(status == STATUS_SKIP for status in statuses):
        return STATUS_SKIP
    return STATUS_PASS


def _category_reason(results: Sequence[dict[str, object]]) -> str:
    for item in results:
        if item["status"] in {STATUS_FAIL, STATUS_WARN}:
            return str(item["failure_reason_id"])
    return "none"


def _first_problem_result(results: Sequence[dict[str, object]]) -> dict[str, object] | None:
    for item in results:
        if item["status"] in {STATUS_FAIL, STATUS_WARN}:
            return item
    return None


def run_categories(root: Path, categories: Sequence[CategorySpec], *, mode: str, fail_fast: bool = False) -> dict[str, object]:
    started = time.monotonic()
    category_results: list[dict[str, object]] = []
    first_failure: dict[str, str] | None = None
    for category in categories:
        category_start = time.monotonic()
        command_results: list[dict[str, object]] = []
        for command in category.commands:
            result = _run_single(root, command)
            command_results.append(result)
            if result["status"] == STATUS_FAIL and first_failure is None:
                first_failure = {
                    "category": category.name,
                    "command": str(result["name"]),
                    "failure_reason_id": str(result["failure_reason_id"]),
                }
            if fail_fast and result["status"] == STATUS_FAIL and command.required:
                break
        status = _category_status(command_results, category.required)
        if category.required and status == STATUS_WARN and first_failure is None:
            problem = _first_problem_result(command_results)
            first_failure = {
                "category": category.name,
                "command": str(problem["name"] if problem else category.name),
                "failure_reason_id": str(problem["failure_reason_id"] if problem else _category_reason(command_results)),
            }
        category_results.append(
            {
                "name": category.name,
                "required": category.required,
                "status": status,
                "elapsed_ms": _ms(category_start),
                "failure_reason_id": "none" if status in {STATUS_PASS, STATUS_SKIP} else _category_reason(command_results),
                "commands": command_results,
            }
        )
        if fail_fast and status in {STATUS_FAIL, STATUS_WARN} and category.required:
            break
    required_passed = sum(1 for item in category_results if item["required"] and item["status"] == STATUS_PASS)
    required_failed = sum(
        1 for item in category_results if item["required"] and item["status"] in {STATUS_FAIL, STATUS_WARN}
    )
    optional_skipped = sum(1 for item in category_results if not item["required"] and item["status"] == STATUS_SKIP)
    overall = STATUS_FAIL if required_failed else STATUS_PASS
    return {
        "schema_version": "relaylm.mvp_eval_runner.summary.v1",
        "overall_status": overall,
        "mode": mode,
        "required_passed_count": required_passed,
        "required_failed_count": required_failed,
        "optional_skipped_count": optional_skipped,
        "categories": category_results,
        "first_failure": first_failure or "none",
        "next_operator_hint": (
            "static_evaluation_boundary_passed" if overall == STATUS_PASS and mode == "static"
            else "local_mode_boundary_passed" if overall == STATUS_PASS
            else "inspect_first_failed_category_and_rerun_explicitly"
        ),
        "elapsed_ms": _ms(started),
    }


def _script_category(name: str, scripts: Sequence[str]) -> CategorySpec:
    return CategorySpec(name=name, required=True, commands=tuple(_py(script) for script in scripts))


def build_static_categories(root: Path, *, include_slow: bool = False) -> tuple[CategorySpec, ...]:
    del include_slow
    governance, _missing = _governance_scripts(root)
    return (
        CategorySpec("preflight", True, (CommandSpec("internal:static-preflight", internal_action="static_preflight"),)),
        CategorySpec("compile", True, (CommandSpec("python -m compileall relaylm scripts", (sys.executable, "-m", "compileall", "relaylm", "scripts"), True, 180.0),)),
        _script_category("e1_provenance_grounding_recall", E1_SCRIPTS),
        _script_category("two_turn_recall_lifecycle", TWO_TURN_SCRIPTS),
        _script_category("o1_operational_boundary", O1_SCRIPTS),
        CategorySpec("governance", True, (CommandSpec("internal:governance-smoke-discovery", required=False, internal_action="governance_discovery"), *tuple(_py(script) for script in governance))),
        CategorySpec("docs_completion_model", True, tuple(_py(script, *args) for script, args in DOC_COMMANDS)),
    )


def build_local_categories(root: Path, *, include_slow: bool = False) -> tuple[CategorySpec, ...]:
    del include_slow
    return (
        build_static_categories(root)[0],
        CategorySpec("local_mode_boundary", True, (CommandSpec("internal:local-mode-unsupported-no-sleep-no-polling", internal_action="local_unsupported"),)),
    )


def filter_categories(categories: Sequence[CategorySpec], selected: Sequence[str]) -> tuple[CategorySpec, ...]:
    if not selected:
        return tuple(categories)
    table = {category.name: category for category in categories}
    if any(name not in table for name in selected):
        raise ValueError("unknown_category")
    return tuple(table[name] for name in selected)


def format_category_list(categories: Sequence[CategorySpec], *, mode: str) -> str:
    lines = ["RelayLM MVP eval runner command list", f"mode: {mode}", "categories:"]
    for category in categories:
        lines.append(f"- {category.name} required={str(category.required).lower()}")
        lines.extend(f"  - {command.name} required={str(command.required).lower()}" for command in category.commands)
    return "\n".join(lines) + "\n"


def format_summary_text(summary: dict[str, object]) -> str:
    lines = [
        "RelayLM MVP eval runner summary",
        f"overall_status: {summary['overall_status']}",
        f"mode: {summary['mode']}",
        f"required_passed_count: {summary['required_passed_count']}",
        f"required_failed_count: {summary['required_failed_count']}",
        f"optional_skipped_count: {summary['optional_skipped_count']}",
        "categories:",
    ]
    for category in summary["categories"]:  # type: ignore[index]
        lines.append(f"- {category['name']}: {category['status']} required={str(category['required']).lower()} elapsed_ms={category['elapsed_ms']} failure_reason_id={category['failure_reason_id']}")
        for command in category["commands"]:  # type: ignore[index]
            lines.append(f"  - {command['name']}: {command['status']} required={str(command['required']).lower()} elapsed_ms={command['elapsed_ms']} failure_reason_id={command['failure_reason_id']}")
    first = summary["first_failure"]
    lines.append("first_failure: none" if first == "none" else f"first_failure: category={first['category']} command={first['command']} failure_reason_id={first['failure_reason_id']}")  # type: ignore[index]
    lines.append(f"next_operator_hint: {summary['next_operator_hint']}")
    return "\n".join(lines) + "\n"


def write_summary_json(summary: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run explicit RelayLM MVP evaluation checks.")
    parser.add_argument("--mode", choices=("static", "local"), required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--include-slow", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--character", default="Mira")
    parser.add_argument("--namespace", default="eval-wave7")
    parser.add_argument("--runtime-root", default="runtime")
    parser.add_argument("--max-rounds", type=int, default=3)
    args = parser.parse_args(argv)
    if args.max_rounds <= 0:
        parser.error("--max-rounds must be a positive finite integer")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    categories = build_static_categories(REPO_ROOT, include_slow=args.include_slow) if args.mode == "static" else build_local_categories(REPO_ROOT, include_slow=args.include_slow)
    try:
        categories = filter_categories(categories, args.category)
    except ValueError:
        print("error: unknown category", file=sys.stderr)
        return 2
    if args.list:
        print(format_category_list(categories, mode=args.mode), end="")
        return 0
    summary = run_categories(REPO_ROOT, categories, mode=args.mode, fail_fast=args.fail_fast)
    print(format_summary_text(summary), end="")
    if args.json_out:
        try:
            write_summary_json(summary, args.json_out)
        except OSError:
            print("error: could not write JSON summary", file=sys.stderr)
            return 2
    return 0 if summary["overall_status"] == STATUS_PASS else 1
