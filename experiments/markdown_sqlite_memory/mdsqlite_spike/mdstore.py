"""Markdown steady-state authority store.

Pages are multi-memory Markdown files. Each durable memory is one block,
delimited by HTML comments carrying a stable block ID. The syntax used here
is EXPERIMENTAL (``relaymem-spike`` v0) and does not imply a final
production syntax.

A page looks like::

    <!-- relaymem-spike:page-syntax v=0 (experimental; not production syntax) -->
    # Page Title

    <!-- relaymem-spike:block id=blk_a1b2c3 -->
    - status: active
    - kind: fact
    - user_tags: alpha, beta
    - system_tags: auto
    - source_refs: conv:0001#3
    - revision: 2
    - updated: 2026-07-12T00:00:00+00:00

    The durable memory content, free-form Markdown text.
    <!-- relaymem-spike:end -->

Rendering is deterministic: ``render_page(parse_page(text)) == text`` for
any text produced by ``render_page``.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

SYNTAX_HEADER = (
    "<!-- relaymem-spike:page-syntax v=0 (experimental; not production syntax) -->"
)
_BLOCK_START_RE = re.compile(r"^<!-- relaymem-spike:block id=([A-Za-z0-9_\-]+) -->$")
_BLOCK_END = "<!-- relaymem-spike:end -->"
_HEADER_FIELD_RE = re.compile(r"^- ([a-z_]+): ?(.*)$")

# Digest of a missing/empty page, used as the pre-image for page creation.
EMPTY_DIGEST = hashlib.sha256(b"").hexdigest()

_LIST_FIELDS = ("user_tags", "system_tags", "source_refs")
_HEADER_ORDER = (
    "status",
    "kind",
    "user_tags",
    "system_tags",
    "source_refs",
    "revision",
    "updated",
)


class MarkdownSyntaxError(ValueError):
    """Raised when a page does not conform to the experimental syntax."""


@dataclass
class Block:
    block_id: str
    status: str = "active"
    kind: str = "fact"
    user_tags: tuple[str, ...] = ()
    system_tags: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    revision: int = 1
    updated: str = ""
    content: str = ""

    def normalized_text(self) -> str:
        return " ".join(self.content.split()).lower()

    def content_key(self) -> str:
        """Equivalence key for duplicate detection and tombstones."""
        return hashlib.sha256(self.normalized_text().encode("utf-8")).hexdigest()

    def subject_key(self) -> str:
        """Crude subject heuristic for contradiction candidates."""
        return " ".join(self.normalized_text().split()[:3])

    def digest(self) -> str:
        return hashlib.sha256(render_block(self).encode("utf-8")).hexdigest()


@dataclass
class Page:
    title: str
    blocks: list[Block] = field(default_factory=list)

    def get(self, block_id: str) -> Block | None:
        for block in self.blocks:
            if block.block_id == block_id:
                return block
        return None


def stable_block_id(seed: str) -> str:
    return "blk_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]


def _render_list(values: tuple[str, ...]) -> str:
    return ", ".join(values)


def render_block(block: Block) -> str:
    lines = [f"<!-- relaymem-spike:block id={block.block_id} -->"]
    values = {
        "status": block.status,
        "kind": block.kind,
        "user_tags": _render_list(block.user_tags),
        "system_tags": _render_list(block.system_tags),
        "source_refs": _render_list(block.source_refs),
        "revision": str(block.revision),
        "updated": block.updated,
    }
    for key in _HEADER_ORDER:
        lines.append(f"- {key}: {values[key]}".rstrip())
    lines.append("")
    content = block.content.strip("\n")
    if content:
        lines.append(content)
    lines.append(_BLOCK_END)
    return "\n".join(lines)


def render_page(page: Page) -> str:
    parts = [SYNTAX_HEADER, f"# {page.title}"]
    for block in page.blocks:
        parts.append(render_block(block))
    return "\n\n".join(parts) + "\n"


def _parse_list(value: str) -> tuple[str, ...]:
    value = value.strip()
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_block(block_id: str, lines: list[str], path: str) -> Block:
    fields: dict[str, str] = {}
    idx = 0
    while idx < len(lines) and lines[idx].strip():
        match = _HEADER_FIELD_RE.match(lines[idx])
        if not match:
            raise MarkdownSyntaxError(
                f"{path}: malformed header line in block {block_id}: {lines[idx]!r}"
            )
        fields[match.group(1)] = match.group(2)
        idx += 1
    content = "\n".join(lines[idx:]).strip("\n")
    try:
        revision = int(fields.get("revision", "1"))
    except ValueError as exc:
        raise MarkdownSyntaxError(
            f"{path}: non-integer revision in block {block_id}"
        ) from exc
    return Block(
        block_id=block_id,
        status=fields.get("status", "active"),
        kind=fields.get("kind", "fact"),
        user_tags=_parse_list(fields.get("user_tags", "")),
        system_tags=_parse_list(fields.get("system_tags", "")),
        source_refs=_parse_list(fields.get("source_refs", "")),
        revision=revision,
        updated=fields.get("updated", ""),
        content=content,
    )


def parse_page(text: str, path: str = "<memory>") -> Page:
    if not text.strip():
        return Page(title="Untitled")
    title = "Untitled"
    blocks: list[Block] = []
    lines = text.splitlines()
    idx = 0
    seen: set[str] = set()
    while idx < len(lines):
        line = lines[idx]
        start = _BLOCK_START_RE.match(line)
        if start:
            block_id = start.group(1)
            if block_id in seen:
                raise MarkdownSyntaxError(f"{path}: duplicate block id {block_id}")
            seen.add(block_id)
            body: list[str] = []
            idx += 1
            while idx < len(lines) and lines[idx] != _BLOCK_END:
                body.append(lines[idx])
                idx += 1
            if idx >= len(lines):
                raise MarkdownSyntaxError(
                    f"{path}: unterminated block {block_id} (missing end marker)"
                )
            blocks.append(_parse_block(block_id, body, path))
        elif line.startswith("# ") and title == "Untitled":
            title = line[2:].strip()
        idx += 1
    return Page(title=title, blocks=blocks)


def text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    """Digest of the page file; EMPTY_DIGEST when the file does not exist."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return EMPTY_DIGEST
    return hashlib.sha256(data).hexdigest()


def atomic_replace(path: Path, text: str) -> None:
    """Durably replace ``path`` with ``text``.

    Writes to a temporary file in the same directory, fsyncs it, atomically
    renames it over the destination, then fsyncs the directory so the rename
    itself is durable. POSIX semantics; Windows durability is out of scope
    for this spike.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".spike-tmp")
    data = text.encode("utf-8")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def load_pages(pages_dir: Path) -> dict[str, str]:
    """Return {relative_path: text} for every Markdown page under the root."""
    pages: dict[str, str] = {}
    if not pages_dir.exists():
        return pages
    for file in sorted(pages_dir.rglob("*.md")):
        pages[file.relative_to(pages_dir).as_posix()] = file.read_text(
            encoding="utf-8"
        )
    return pages


def with_block(page: Page, block: Block) -> Page:
    """Return a copy of ``page`` with ``block`` inserted or replaced."""
    blocks = list(page.blocks)
    for i, existing in enumerate(blocks):
        if existing.block_id == block.block_id:
            blocks[i] = block
            break
    else:
        blocks.append(block)
    return replace(page, blocks=blocks)


def without_block(page: Page, block_id: str) -> Page:
    return replace(
        page, blocks=[b for b in page.blocks if b.block_id != block_id]
    )
