"""Part C: config key, feature flag, and dependency-surface inventory."""
from __future__ import annotations

import json
import re

from . import repo
from .records import ConfigRecord, Evidence

_ENV_VAR_RE = re.compile(r'os\.(?:environ(?:\.get)?|getenv)\(\s*["\'](\w+)["\']')
_WORKFLOW_ENV_RE = re.compile(r"\$\{\{\s*(?:secrets|env|vars)\.(\w+)\s*\}\}")
_FEATURE_FLAG_SUFFIXES = ("_enabled", "_dry_run_only", "_apply_enabled", "_trigger_enabled")


def _flatten_yaml(value, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            full = f"{prefix}.{k}" if prefix else str(k)
            keys.append(full)
            keys.extend(_flatten_yaml(v, full))
    return keys


def scan_env_vars() -> list[ConfigRecord]:
    hits: dict[str, list[Evidence]] = {}
    for path in repo.iter_repo_files(suffixes=(".py",)):
        rel = repo.relative(path)
        if not (rel.startswith("relaylm/") or rel.startswith("scripts/") or rel.startswith("tests/")):
            continue
        text = repo.read_text(path)
        if text is None or "environ" not in text and "getenv" not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in _ENV_VAR_RE.finditer(line):
                hits.setdefault(match.group(1), []).append(Evidence(rel, lineno, line.strip()[:160]))

    workflows_dir = repo.ROOT / ".github" / "workflows"
    if workflows_dir.is_dir():
        for path in sorted(workflows_dir.glob("*.y*ml")):
            rel = repo.relative(path)
            text = repo.read_text(path)
            if text is None:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                for match in _WORKFLOW_ENV_RE.finditer(line):
                    hits.setdefault(match.group(1), []).append(Evidence(rel, lineno, line.strip()[:160]))

    records: list[ConfigRecord] = []
    for name, evidence in hits.items():
        referenced_in = sorted({e.file for e in evidence})
        source_context = "workflow-only" if all(f.startswith(".github/") for f in referenced_in) else "code"
        records.append(
            ConfigRecord(
                key_kind="env_var",
                name=name,
                source_context=source_context,
                referenced_in=referenced_in,
                evidence=evidence,
                heuristic_fields=["source_context"],
            )
        )
    return records


def scan_config_keys_and_flags() -> list[ConfigRecord]:
    records: list[ConfigRecord] = []
    example_config = repo.ROOT / "config.example.yaml"
    text = repo.read_text(example_config)
    if text is None:
        return records
    try:
        import yaml

        data = yaml.safe_load(text)
    except Exception:
        data = None
    if not isinstance(data, dict):
        return records
    lines = text.splitlines()
    for dotted_key in _flatten_yaml(data):
        leaf = dotted_key.rsplit(".", 1)[-1]
        is_flag = leaf.endswith(_FEATURE_FLAG_SUFFIXES)
        lineno = 1
        for idx, line in enumerate(lines, start=1):
            stripped = line.split(":", 1)[0].strip()
            if stripped == leaf:
                lineno = idx
                break
        records.append(
            ConfigRecord(
                key_kind="feature_flag" if is_flag else "config_key",
                name=dotted_key,
                source_context="config.example.yaml",
                referenced_in=["config.example.yaml"],
                evidence=[Evidence("config.example.yaml", lineno, lines[lineno - 1].strip()[:160])],
                heuristic_fields=["key_kind"],
            )
        )
    return records


_DEP_STRING_RE = re.compile(r'"([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?(?:[><=!~ ][^"]*)?"')


def _pkg_name(literal: str) -> str:
    return re.split(r"[><=!~\[]", literal, maxsplit=1)[0].strip()


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_python_dependencies() -> list[ConfigRecord]:
    records: list[ConfigRecord] = []
    pyproject = repo.ROOT / "pyproject.toml"
    text = repo.read_text(pyproject)
    if text is None:
        return records

    runtime_match = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL | re.MULTILINE)
    if runtime_match:
        block, block_start = runtime_match.group(1), runtime_match.start(1)
        for dep_match in _DEP_STRING_RE.finditer(block):
            pkg = _pkg_name(dep_match.group(1))
            if not pkg:
                continue
            lineno = _line_of(text, block_start + dep_match.start())
            records.append(
                ConfigRecord(
                    key_kind="python_dependency",
                    name=pkg,
                    source_context="runtime",
                    referenced_in=["pyproject.toml"],
                    evidence=[Evidence("pyproject.toml", lineno, text.splitlines()[lineno - 1].strip()[:160])],
                    heuristic_fields=[],
                )
            )

    extras_section = re.search(
        r"^\[project\.optional-dependencies\]\s*$(.*?)(?=^\[|\Z)", text, re.DOTALL | re.MULTILINE
    )
    if extras_section:
        section_text, section_start = extras_section.group(1), extras_section.start(1)
        for extra_match in re.finditer(r'^(\w[\w-]*)\s*=\s*\[(.*?)\]', section_text, re.DOTALL | re.MULTILINE):
            extra_name, dep_block = extra_match.group(1), extra_match.group(2)
            dep_block_start = section_start + extra_match.start(2)
            for dep_match in _DEP_STRING_RE.finditer(dep_block):
                pkg = _pkg_name(dep_match.group(1))
                if not pkg:
                    continue
                lineno = _line_of(text, dep_block_start + dep_match.start())
                records.append(
                    ConfigRecord(
                        key_kind="extra_or_mode",
                        name=pkg,
                        source_context=f"optional-dependencies.{extra_name}",
                        referenced_in=["pyproject.toml"],
                        evidence=[Evidence("pyproject.toml", lineno, text.splitlines()[lineno - 1].strip()[:160])],
                        heuristic_fields=[],
                    )
                )
    return records


def scan_node_dependencies() -> list[ConfigRecord]:
    records: list[ConfigRecord] = []
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
        lines = text.splitlines()
        for section_key, context in (("dependencies", "node-runtime"), ("devDependencies", "node-dev")):
            deps = data.get(section_key)
            if not isinstance(deps, dict):
                continue
            for name in sorted(deps):
                lineno = 1
                needle = f'"{name}"'
                for idx, line in enumerate(lines, start=1):
                    if needle in line:
                        lineno = idx
                        break
                records.append(
                    ConfigRecord(
                        key_kind="node_dependency",
                        name=name,
                        source_context=context,
                        referenced_in=[rel],
                        evidence=[Evidence(rel, lineno, lines[lineno - 1].strip()[:160])],
                        heuristic_fields=[],
                    )
                )
    return records


def scan_workflow_only_tools() -> list[ConfigRecord]:
    records: list[ConfigRecord] = []
    workflows_dir = repo.ROOT / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return records
    uses_re = re.compile(r"uses:\s*([\w./-]+)@")
    hits: dict[str, list[Evidence]] = {}
    for path in sorted(workflows_dir.glob("*.y*ml")):
        rel = repo.relative(path)
        text = repo.read_text(path)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = uses_re.search(line)
            if match:
                hits.setdefault(match.group(1), []).append(Evidence(rel, lineno, line.strip()[:160]))
    for name, evidence in hits.items():
        records.append(
            ConfigRecord(
                key_kind="workflow_tool",
                name=name,
                source_context="workflow-only",
                referenced_in=sorted({e.file for e in evidence}),
                evidence=evidence,
                heuristic_fields=[],
            )
        )
    return records


def collect_all() -> list[ConfigRecord]:
    records: list[ConfigRecord] = []
    records.extend(scan_env_vars())
    records.extend(scan_config_keys_and_flags())
    records.extend(scan_python_dependencies())
    records.extend(scan_node_dependencies())
    records.extend(scan_workflow_only_tools())
    records.sort(key=lambda r: r.sort_key())
    return records
