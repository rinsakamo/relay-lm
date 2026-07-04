"""CW-A1 Markdown source parsing helpers."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

from ._constants import MAX_SOURCE_FILE_BYTES, SOURCE_KIND_BY_FILENAME
from ._types import CharacterMarkdownBlock, CharacterSourceParseResult, CharacterWorkspaceValidationStatus

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
HEADING_ANCHOR_RE = re.compile(r"(?:^|\s)(\^[A-Za-z0-9][A-Za-z0-9_.:-]*)\s*$")
METADATA_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)::\s*(.*)$")


def parse_character_source_file(
    path: str | Path,
    source_kind: str,
    public: bool = False,
) -> CharacterSourceParseResult | dict[str, Any]:
    """Parse one human-editable uppercase source file as a bounded contract object."""

    source_path = Path(path)
    filename = source_path.name
    if source_kind not in set(SOURCE_KIND_BY_FILENAME.values()):
        return _parse_error(filename, "unknown", ("unknown_source_kind",), public)

    try:
        size = source_path.stat().st_size
    except OSError:
        return _parse_error(filename, source_kind, ("source_file_unreadable",), public)

    if size > MAX_SOURCE_FILE_BYTES:
        return _parse_error(filename, source_kind, ("source_file_too_large",), public)

    try:
        text = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return _parse_error(filename, source_kind, ("source_file_not_utf8",), public)
    except OSError:
        return _parse_error(filename, source_kind, ("source_file_unreadable",), public)

    blocks = tuple(parse_markdown_blocks(text))
    result = CharacterSourceParseResult(
        status=CharacterWorkspaceValidationStatus.VALID,
        filename=filename,
        source_kind=source_kind,
        content_hash=_content_hash(text),
        line_count=len(text.splitlines()),
        block_count=len(blocks),
        blocks=blocks,
        error_ids=(),
    )
    return result.to_public_dict() if public else result


def parse_markdown_blocks(text: str, source_path: str | Path | None = None) -> list[CharacterMarkdownBlock]:
    """Parse Markdown headings, optional heading anchors, and ``key:: value`` metadata."""

    del source_path
    lines = text.splitlines()
    heading_starts: list[tuple[int, int, str, str | None]] = []
    for index, line in enumerate(lines, 1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        heading_text = match.group(2).strip()
        anchor_match = HEADING_ANCHOR_RE.search(heading_text)
        anchor = anchor_match.group(1) if anchor_match else None
        if anchor:
            heading_text = heading_text[: anchor_match.start()].rstrip()
        heading_starts.append((index, len(match.group(1)), heading_text, anchor))

    if not heading_starts:
        if not text:
            return []
        return [_markdown_block(0, "", None, 1, len(lines) or 1, lines, text)]

    blocks: list[CharacterMarkdownBlock] = []
    for position, (start_line, level, heading, anchor) in enumerate(heading_starts):
        next_start = heading_starts[position + 1][0] if position + 1 < len(heading_starts) else len(lines) + 1
        end_line = max(start_line, next_start - 1)
        block_lines = lines[start_line - 1 : end_line]
        blocks.append(_markdown_block(level, heading, anchor, start_line, end_line, block_lines))
    return blocks


def _parse_error(
    filename: str,
    source_kind: str,
    error_ids: tuple[str, ...],
    public: bool,
) -> CharacterSourceParseResult | dict[str, Any]:
    result = CharacterSourceParseResult(
        status=CharacterWorkspaceValidationStatus.MALFORMED_MARKDOWN,
        filename=filename,
        source_kind=source_kind,
        content_hash=None,
        line_count=0,
        block_count=0,
        blocks=(),
        error_ids=error_ids,
    )
    return result.to_public_dict() if public else result


def _markdown_block(
    level: int,
    heading: str,
    anchor: str | None,
    start_line: int,
    end_line: int,
    lines: list[str],
    hash_text: str | None = None,
) -> CharacterMarkdownBlock:
    return CharacterMarkdownBlock(
        heading_level=level,
        heading=heading,
        anchor=anchor,
        metadata=tuple(_parse_metadata(lines)),
        start_line=start_line,
        end_line=end_line,
        content_hash=_content_hash(hash_text if hash_text is not None else "\n".join(lines)),
    )


def _parse_metadata(lines: Iterable[str]) -> list[tuple[str, str]]:
    metadata: list[tuple[str, str]] = []
    in_fence = False
    fence_marker: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue
        match = METADATA_RE.match(stripped)
        if match:
            metadata.append((match.group(1).lower(), match.group(2).strip()))
    return metadata


def _content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
