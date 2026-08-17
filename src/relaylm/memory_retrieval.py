from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
_FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")


@dataclass(frozen=True, slots=True)
class MemoryChunk:
    """One locally complete heading section selected from MEMORY.md."""

    heading_path: tuple[str, ...]
    location: str
    content: str

    def __post_init__(self) -> None:
        if not self.heading_path or not all(part.strip() for part in self.heading_path):
            raise ValueError("memory chunk heading_path must contain non-empty headings")
        if not self.location.strip():
            raise ValueError("memory chunk location must not be empty")
        if not self.content.strip():
            raise ValueError("memory chunk content must not be empty")


def select_memory_chunks(
    *,
    memory_markdown: str | None,
    query: str,
    max_chunks: int,
    max_chars: int,
) -> tuple[MemoryChunk, ...]:
    """Select complete, positively relevant MEMORY.md heading sections under explicit budgets."""

    if max_chunks < 0:
        raise ValueError("max_chunks must not be negative")
    if max_chars < 0:
        raise ValueError("max_chars must not be negative")
    if max_chunks == 0 or max_chars == 0 or not memory_markdown or not query.strip():
        return ()

    chunks = _parse_heading_chunks(memory_markdown)
    if not chunks:
        return ()

    query_terms = _lexical_terms(query)
    if not query_terms:
        return ()

    scored = tuple(_memory_lexical_score(chunk, query_terms) for chunk in chunks)
    ranked_indices = sorted(
        (index for index, score in enumerate(scored) if score > 0),
        key=lambda index: (-scored[index], index),
    )

    selected_indices: list[int] = []
    used_chars = 0
    for index in ranked_indices:
        if len(selected_indices) >= max_chunks:
            break
        cost = len(chunks[index].content)
        if cost > max_chars - used_chars:
            continue
        selected_indices.append(index)
        used_chars += cost

    return tuple(chunks[index] for index in sorted(selected_indices))


def _parse_heading_chunks(markdown: str) -> tuple[MemoryChunk, ...]:
    chunks: list[MemoryChunk] = []
    heading_stack: list[str] = []
    current_level: int | None = None
    current_title: str | None = None
    current_body: list[str] = []
    location_counts: dict[str, int] = {}
    fence_char: str | None = None
    fence_length = 0

    def flush() -> None:
        if current_level is None or current_title is None:
            return
        body = "\n".join(current_body).strip()
        if not body:
            return
        path = tuple(heading_stack)
        base_location = "memory/MEMORY.md#" + "/".join(_slug(part) for part in path)
        occurrence = location_counts.get(base_location, 0) + 1
        location_counts[base_location] = occurrence
        location = base_location if occurrence == 1 else f"{base_location}-{occurrence}"
        heading_line = f"{'#' * current_level} {current_title}"
        chunks.append(
            MemoryChunk(
                heading_path=path,
                location=location,
                content=f"{heading_line}\n\n{body}",
            )
        )

    for raw_line in markdown.splitlines():
        fence = _FENCE.match(raw_line)
        if fence_char is not None:
            if current_level is not None:
                current_body.append(raw_line)
            marker = fence.group(1) if fence is not None else ""
            if marker and marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
                fence_length = 0
            continue
        if fence is not None:
            marker = fence.group(1)
            fence_char = marker[0]
            fence_length = len(marker)
            if current_level is not None:
                current_body.append(raw_line)
            continue

        match = _HEADING.match(raw_line)
        if match is None:
            if current_level is not None:
                current_body.append(raw_line)
            continue

        flush()
        level = len(match.group(1))
        title = _clean_heading(match.group(2))
        if not title:
            current_level = None
            current_title = None
            current_body = []
            continue

        if level <= len(heading_stack):
            heading_stack = heading_stack[: level - 1]
        heading_stack.append(title)
        current_level = level
        current_title = title
        current_body = []

    flush()
    return tuple(chunks)


def _memory_lexical_score(chunk: MemoryChunk, query_terms: tuple[str, ...]) -> int:
    heading_terms = frozenset(_lexical_terms(" ".join(chunk.heading_path)))
    content_terms = frozenset(_lexical_terms(chunk.content))
    score = 0
    for term in query_terms:
        if len(term) < 2:
            continue
        if term in heading_terms:
            score += 4
        if term in content_terms:
            score += 1
    return score


def _clean_heading(raw: str) -> str:
    return raw.rstrip().rstrip("#").rstrip()


def _slug(text: str) -> str:
    normalized = _normalize(text).replace("_", "-")
    slug = re.sub(r"[^\w-]+", "-", normalized).strip("-")
    return slug or "section"


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _lexical_terms(text: str) -> tuple[str, ...]:
    normalized = _normalize(text).replace("_", " ")
    return tuple(term for term in re.split(r"[^\w]+", normalized) if term)
