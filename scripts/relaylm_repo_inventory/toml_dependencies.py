"""Bracket-aware dependency extraction for ``pyproject.toml``.

This companion replaces regex-only array slicing in generated inventory output.
Quoted extras such as ``uvicorn[standard]`` and ``relay-lm[test]`` therefore do
not terminate the surrounding TOML array early.
"""
from __future__ import annotations

import re

from . import repo
from .records import ConfigRecord, Evidence

_DEP_STRING_RE = re.compile(r'"([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?(?:[><=!~ ][^"]*)?"')
_SECTION_RE = re.compile(r"^\[([^]]+)\]\s*$", re.MULTILINE)


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _section(text: str, name: str) -> tuple[str, int] | None:
    matches = list(_SECTION_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1) != name:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[start:end], start
    return None


def _array_after(text: str, assignment_start: int) -> tuple[str, int] | None:
    opening = text.find("[", assignment_start)
    if opening < 0:
        return None
    depth = 0
    quote: str | None = None
    escaped = False
    for offset in range(opening, len(text)):
        char = text[offset]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : offset], opening + 1
    return None


def _records_from_block(
    *,
    text: str,
    block: str,
    block_start: int,
    key_kind: str,
    source_context: str,
) -> list[ConfigRecord]:
    lines = text.splitlines()
    records: list[ConfigRecord] = []
    for match in _DEP_STRING_RE.finditer(block):
        name = match.group(1)
        lineno = _line_of(text, block_start + match.start())
        records.append(
            ConfigRecord(
                key_kind=key_kind,
                name=name,
                source_context=source_context,
                referenced_in=["pyproject.toml"],
                evidence=[Evidence("pyproject.toml", lineno, lines[lineno - 1].strip()[:160])],
                heuristic_fields=[],
            )
        )
    return records


def scan_python_dependencies() -> list[ConfigRecord]:
    path = repo.ROOT / "pyproject.toml"
    text = repo.read_text(path)
    if text is None:
        return []
    records: list[ConfigRecord] = []

    project = _section(text, "project")
    if project is not None:
        body, start = project
        match = re.search(r"^dependencies\s*=", body, re.MULTILINE)
        if match:
            extracted = _array_after(text, start + match.start())
            if extracted is not None:
                block, block_start = extracted
                records.extend(
                    _records_from_block(
                        text=text,
                        block=block,
                        block_start=block_start,
                        key_kind="python_dependency",
                        source_context="runtime",
                    )
                )

    optional = _section(text, "project.optional-dependencies")
    if optional is not None:
        body, start = optional
        for match in re.finditer(r"^(\w[\w-]*)\s*=", body, re.MULTILINE):
            extracted = _array_after(text, start + match.start())
            if extracted is None:
                continue
            block, block_start = extracted
            records.extend(
                _records_from_block(
                    text=text,
                    block=block,
                    block_start=block_start,
                    key_kind="extra_or_mode",
                    source_context=f"optional-dependencies.{match.group(1)}",
                )
            )

    records.sort(key=lambda record: record.sort_key())
    return records
