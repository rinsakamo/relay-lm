"""Path-aware YAML config-key evidence for the repository inventory."""
from __future__ import annotations

import re

from . import repo
from .records import ConfigRecord, Evidence

_FEATURE_FLAG_SUFFIXES = (
    "_enabled",
    "_dry_run_only",
    "_apply_enabled",
    "_trigger_enabled",
)
_YAML_KEY_RE = re.compile(
    r"^(?P<indent> *)(?P<key>(?:[^:#]|:(?!\s))[^:]*?)\s*:(?P<rest>.*)$"
)


def _flatten_yaml(value, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            full = f"{prefix}.{key}" if prefix else str(key)
            keys.append(full)
            keys.extend(_flatten_yaml(child, full))
    return keys


def _unquote_key(value: str) -> str:
    value = value.strip()
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    return value


def _yaml_key_lines(text: str) -> dict[str, int]:
    """Map dotted mapping paths to their exact source lines."""

    result: dict[str, int] = {}
    stack: list[tuple[int, str]] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.lstrip(" ")
        if not stripped or stripped.startswith(("#", "-")):
            continue
        match = _YAML_KEY_RE.match(raw_line)
        if match is None:
            continue
        indent = len(match.group("indent"))
        key = _unquote_key(match.group("key"))
        if not key:
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        dotted = ".".join([*(item[1] for item in stack), key])
        result[dotted] = lineno
        rest = match.group("rest").strip()
        if not rest or rest.startswith("#"):
            stack.append((indent, key))
    return result


def scan_config_keys_and_flags() -> list[ConfigRecord]:
    path = repo.ROOT / "config.example.yaml"
    text = repo.read_text(path)
    if text is None:
        return []

    try:
        import yaml

        data = yaml.safe_load(text)
    except Exception:
        data = None
    if not isinstance(data, dict):
        return []

    lines = text.splitlines()
    key_lines = _yaml_key_lines(text)
    records: list[ConfigRecord] = []
    for dotted_key in _flatten_yaml(data):
        leaf = dotted_key.rsplit(".", 1)[-1]
        is_flag = leaf.endswith(_FEATURE_FLAG_SUFFIXES)
        lineno = key_lines.get(dotted_key)
        heuristic_fields = ["key_kind"]
        if lineno is None:
            lineno = 1
            heuristic_fields.append("source_line")
        records.append(
            ConfigRecord(
                key_kind="feature_flag" if is_flag else "config_key",
                name=dotted_key,
                source_context="config.example.yaml",
                referenced_in=["config.example.yaml"],
                evidence=[
                    Evidence(
                        "config.example.yaml",
                        lineno,
                        lines[lineno - 1].strip()[:160],
                    )
                ],
                heuristic_fields=heuristic_fields,
            )
        )
    records.sort(key=lambda record: record.sort_key())
    return records
