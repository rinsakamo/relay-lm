from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field

from relaylm.memory_provenance import (
    MemoryProvenance,
    MemoryProvenanceSource,
    MemoryProvenanceSourceKind,
    MemoryTemporalAuthority,
    MemoryTemporalScope,
)
from relaylm.retrieval_lexical import lexical_query_terms, lexical_terms


_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
_FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_MEMORY_METADATA_RESERVED = re.compile(r"^[ \t]*<!--[ \t]+relaylm-memory:")
_MEMORY_METADATA_V1 = re.compile(
    r"^[ \t]*<!--[ \t]+relaylm-memory:v1[ \t]+(.+?)[ \t]+-->[ \t]*$"
)
_MEMORY_METADATA_KEYS = frozenset(
    {"memory_id", "derivation_id", "temporal_scope", "sources"}
)
_MEMORY_SOURCE_KEYS = frozenset({"kind", "reference_id"})


def _unknown_temporal_authority() -> MemoryTemporalAuthority:
    return MemoryTemporalAuthority(temporal_scope=MemoryTemporalScope.UNKNOWN)


@dataclass(frozen=True, slots=True)
class MemoryChunk:
    """One locally complete heading section selected from MEMORY.md."""

    heading_path: tuple[str, ...]
    location: str
    content: str
    temporal_authority: MemoryTemporalAuthority = field(
        default_factory=_unknown_temporal_authority
    )

    def __post_init__(self) -> None:
        if not self.heading_path or not all(part.strip() for part in self.heading_path):
            raise ValueError("memory chunk heading_path must contain non-empty headings")
        if not self.location.strip():
            raise ValueError("memory chunk location must not be empty")
        if not self.content.strip():
            raise ValueError("memory chunk content must not be empty")
        if not isinstance(self.temporal_authority, MemoryTemporalAuthority):
            raise TypeError("memory chunk temporal_authority must be MemoryTemporalAuthority")


@dataclass(frozen=True, slots=True)
class MemoryRetrievalDiagnostics:
    """Content-free aggregate observations from one MEMORY retrieval attempt."""

    mode: str
    parsed_chunk_count: int
    positive_candidate_count: int
    selected_count: int
    chunk_budget_limit: int
    character_budget_limit: int
    character_budget_used: int
    skipped_character_budget_count: int
    unadmitted_chunk_limit_count: int
    chunk_budget_pressure: bool
    character_budget_pressure: bool


@dataclass(frozen=True, slots=True)
class MemoryRetrievalResult:
    chunks: tuple[MemoryChunk, ...]
    diagnostics: MemoryRetrievalDiagnostics


def select_memory_chunks(
    *,
    memory_markdown: str | None,
    query: str,
    max_chunks: int,
    max_chars: int,
) -> tuple[MemoryChunk, ...]:
    """Select complete, positively relevant MEMORY.md heading sections under explicit budgets."""

    return _select_memory_chunks(
        memory_markdown=memory_markdown,
        query=query,
        max_chunks=max_chunks,
        max_chars=max_chars,
    ).chunks


def select_memory_chunks_with_diagnostics(
    *,
    memory_markdown: str | None,
    query: str,
    max_chunks: int,
    max_chars: int,
) -> MemoryRetrievalResult:
    """Select MEMORY chunks and return content-free retrieval-stage diagnostics."""

    return _select_memory_chunks(
        memory_markdown=memory_markdown,
        query=query,
        max_chunks=max_chunks,
        max_chars=max_chars,
    )


def _select_memory_chunks(
    *,
    memory_markdown: str | None,
    query: str,
    max_chunks: int,
    max_chars: int,
) -> MemoryRetrievalResult:
    if max_chunks < 0:
        raise ValueError("max_chunks must not be negative")
    if max_chars < 0:
        raise ValueError("max_chars must not be negative")
    if max_chunks == 0 or max_chars == 0:
        return _empty_retrieval_result(
            mode="zero_budget",
            max_chunks=max_chunks,
            max_chars=max_chars,
        )
    if not memory_markdown:
        return _empty_retrieval_result(
            mode="no_memory",
            max_chunks=max_chunks,
            max_chars=max_chars,
        )
    if not query.strip():
        return _empty_retrieval_result(
            mode="no_query",
            max_chunks=max_chunks,
            max_chars=max_chars,
        )

    chunks = _parse_heading_chunks(memory_markdown)
    query_terms = lexical_query_terms(query)
    if not query_terms:
        return MemoryRetrievalResult(
            chunks=(),
            diagnostics=MemoryRetrievalDiagnostics(
                mode="no_query_terms",
                parsed_chunk_count=len(chunks),
                positive_candidate_count=0,
                selected_count=0,
                chunk_budget_limit=max_chunks,
                character_budget_limit=max_chars,
                character_budget_used=0,
                skipped_character_budget_count=0,
                unadmitted_chunk_limit_count=0,
                chunk_budget_pressure=False,
                character_budget_pressure=False,
            ),
        )

    scored = tuple(_memory_lexical_score(chunk, query_terms) for chunk in chunks)
    ranked_indices = sorted(
        (index for index, score in enumerate(scored) if score > 0),
        key=lambda index: (-scored[index], index),
    )

    selected_indices: list[int] = []
    used_chars = 0
    skipped_character_budget_count = 0
    unadmitted_chunk_limit_count = 0
    for index in ranked_indices:
        if len(selected_indices) >= max_chunks:
            unadmitted_chunk_limit_count += 1
            continue
        cost = len(chunks[index].content)
        if cost > max_chars - used_chars:
            skipped_character_budget_count += 1
            continue
        selected_indices.append(index)
        used_chars += cost

    selected = tuple(chunks[index] for index in sorted(selected_indices))
    return MemoryRetrievalResult(
        chunks=selected,
        diagnostics=MemoryRetrievalDiagnostics(
            mode="lexical",
            parsed_chunk_count=len(chunks),
            positive_candidate_count=len(ranked_indices),
            selected_count=len(selected),
            chunk_budget_limit=max_chunks,
            character_budget_limit=max_chars,
            character_budget_used=used_chars,
            skipped_character_budget_count=skipped_character_budget_count,
            unadmitted_chunk_limit_count=unadmitted_chunk_limit_count,
            chunk_budget_pressure=unadmitted_chunk_limit_count > 0,
            character_budget_pressure=skipped_character_budget_count > 0,
        ),
    )


def _empty_retrieval_result(
    *,
    mode: str,
    max_chunks: int,
    max_chars: int,
) -> MemoryRetrievalResult:
    return MemoryRetrievalResult(
        chunks=(),
        diagnostics=MemoryRetrievalDiagnostics(
            mode=mode,
            parsed_chunk_count=0,
            positive_candidate_count=0,
            selected_count=0,
            chunk_budget_limit=max_chunks,
            character_budget_limit=max_chars,
            character_budget_used=0,
            skipped_character_budget_count=0,
            unadmitted_chunk_limit_count=0,
            chunk_budget_pressure=False,
            character_budget_pressure=False,
        ),
    )


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
        temporal_authority, semantic_body_lines = _extract_memory_metadata(current_body)
        body = "\n".join(semantic_body_lines).strip()
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
                temporal_authority=temporal_authority,
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


def _extract_memory_metadata(
    body_lines: list[str],
) -> tuple[MemoryTemporalAuthority, list[str]]:
    authority = _unknown_temporal_authority()
    semantic_lines: list[str] = []
    first_nonblank_seen = False
    fence_char: str | None = None
    fence_length = 0

    for line in body_lines:
        fence = _FENCE.match(line)
        if fence_char is not None:
            semantic_lines.append(line)
            marker = fence.group(1) if fence is not None else ""
            if marker and marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
                fence_length = 0
            continue

        if fence is not None:
            marker = fence.group(1)
            fence_char = marker[0]
            fence_length = len(marker)
            if line.strip():
                first_nonblank_seen = True
            semantic_lines.append(line)
            continue

        if not line.strip():
            semantic_lines.append(line)
            continue

        reserved = _MEMORY_METADATA_RESERVED.match(line) is not None
        if not first_nonblank_seen:
            first_nonblank_seen = True
            if reserved:
                authority = _parse_memory_metadata_line(line)
                continue

        if reserved:
            continue
        semantic_lines.append(line)

    return authority, semantic_lines


def _parse_memory_metadata_line(line: str) -> MemoryTemporalAuthority:
    match = _MEMORY_METADATA_V1.match(line)
    if match is None:
        return _unknown_temporal_authority()

    try:
        payload = json.loads(match.group(1), object_pairs_hook=_unique_json_object)
        if not isinstance(payload, dict) or frozenset(payload) != _MEMORY_METADATA_KEYS:
            raise ValueError("unsupported memory metadata shape")

        memory_id = payload["memory_id"]
        derivation_id = payload["derivation_id"]
        temporal_scope = payload["temporal_scope"]
        raw_sources = payload["sources"]
        if not isinstance(memory_id, str):
            raise TypeError("memory_id must be a string")
        if not isinstance(derivation_id, str):
            raise TypeError("derivation_id must be a string")
        if not isinstance(temporal_scope, str):
            raise TypeError("temporal_scope must be a string")
        if not isinstance(raw_sources, list):
            raise TypeError("sources must be a list")

        sources: list[MemoryProvenanceSource] = []
        for raw_source in raw_sources:
            if (
                not isinstance(raw_source, dict)
                or frozenset(raw_source) != _MEMORY_SOURCE_KEYS
            ):
                raise ValueError("unsupported memory provenance source shape")
            kind = raw_source["kind"]
            reference_id = raw_source["reference_id"]
            if not isinstance(kind, str):
                raise TypeError("source kind must be a string")
            if not isinstance(reference_id, str):
                raise TypeError("source reference_id must be a string")
            sources.append(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind(kind),
                    reference_id=reference_id,
                )
            )

        provenance = MemoryProvenance(
            memory_id=memory_id,
            derivation_id=derivation_id,
            sources=tuple(sources),
        )
        return MemoryTemporalAuthority(
            temporal_scope=MemoryTemporalScope(temporal_scope),
            provenance=provenance,
        )
    except (TypeError, ValueError):
        return _unknown_temporal_authority()


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _memory_lexical_score(chunk: MemoryChunk, query_terms: frozenset[str]) -> int:
    heading_terms = frozenset(lexical_terms(" ".join(chunk.heading_path)))
    content_terms = frozenset(lexical_terms(chunk.content))
    score = 0
    for term in query_terms:
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
