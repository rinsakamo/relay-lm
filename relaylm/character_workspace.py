"""Character Workspace file-first source tree and parser contracts.

CW-A1 is intentionally read-only and contract-only.  It describes and validates
the target Markdown-first character workspace layout without compiling prompt
projections, wiring runtime defaults, mutating uppercase sources, or restoring a
default character.  Public diagnostics are content-free: they may expose stable
schema keys, enum values, source filenames, hashes, counts, and reason IDs, but
not raw Markdown bodies, private filesystem paths, queue records, memory IDs, or
internal payloads.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

SCHEMA_VERSION = "relaylm.character_workspace.v0"

MAX_SOURCE_FILE_BYTES = 512 * 1024

REQUIRED_SOURCE_FILENAMES = (
    "SOUL.md",
    "STYLE.md",
    "EMOTION.md",
    "SCENE.md",
    "RELATIONSHIP.md",
    "MEMORY.md",
    "BOUNDARY.md",
)
OPTIONAL_SOURCE_FILENAMES = ("LORE.md",)

LOWERCASE_WORKSPACE_DIRECTORIES = (
    "relationships",
    "relationships/_inbox",
    "scenes",
    "scenes/_inbox",
    "memory",
    "memory/people",
    "memory/projects",
    "memory/topics",
    "memory/episodes",
    "memory/inbox",
    "memory/forgotten",
)
PROPOSAL_DIRECTORIES = (
    "proposals/soul",
    "proposals/style",
    "proposals/emotion",
    "proposals/scene",
    "proposals/relationship",
    "proposals/memory",
    "proposals/boundary",
)
INTERNAL_DIRECTORIES = (
    ".relaylm/sources/conversations",
    ".relaylm/sources/corrections",
    ".relaylm/sources/imports",
    ".relaylm/state",
    ".relaylm/build",
    ".relaylm/indexes",
    ".relaylm/projections",
    ".relaylm/audit",
    ".relaylm/queue",
)
INTERNAL_STATE_FILES = (
    ".relaylm/state/scene_state.json",
    ".relaylm/state/emotion_state.json",
    ".relaylm/state/relationship_state_cache.json",
)
INTERNAL_BUILD_FILES = (
    ".relaylm/build/character_manifest.json",
    ".relaylm/build/style_projection.json",
    ".relaylm/build/emotion_projection.json",
    ".relaylm/build/scene_units.jsonl",
    ".relaylm/build/relationship_projection.json",
    ".relaylm/build/memory_units.jsonl",
    ".relaylm/build/context_projection.json",
    ".relaylm/build/links.jsonl",
)

PROPOSAL_DOMAINS = frozenset({
    "soul",
    "style",
    "emotion",
    "scene",
    "relationship",
    "memory",
    "boundary",
})

SOURCE_KIND_BY_FILENAME = {
    filename: filename.removesuffix(".md").lower()
    for filename in REQUIRED_SOURCE_FILENAMES + OPTIONAL_SOURCE_FILENAMES
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
HEADING_ANCHOR_RE = re.compile(r"(?:^|\s)(\^[A-Za-z0-9][A-Za-z0-9_.:-]*)\s*$")
METADATA_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)::\s*(.*)$")
CHARACTER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class CharacterWorkspacePathKind(str, Enum):
    REQUIRED_SOURCE = "required_source"
    OPTIONAL_SOURCE = "optional_source"
    RELATIONSHIP_PAGE = "relationship_page"
    SCENE_PAGE = "scene_page"
    MEMORY_PAGE = "memory_page"
    PROPOSAL = "proposal"
    INTERNAL_GENERATED = "internal_generated"
    INTERNAL_STATE = "internal_state"
    INTERNAL_SOURCE_EVIDENCE = "internal_source_evidence"
    UNKNOWN = "unknown"


class CharacterWorkspaceValidationStatus(str, Enum):
    VALID = "valid"
    MISSING_REQUIRED_SOURCE = "missing_required_source"
    INVALID_CHARACTER_ID = "invalid_character_id"
    INVALID_ROOT = "invalid_root"
    PATH_ESCAPE_REJECTED = "path_escape_rejected"
    RESERVED_PATH_CONFLICT = "reserved_path_conflict"
    MALFORMED_MARKDOWN = "malformed_markdown"


@dataclass(frozen=True)
class CharacterWorkspaceLayout:
    required_source_filenames: tuple[str, ...] = REQUIRED_SOURCE_FILENAMES
    optional_source_filenames: tuple[str, ...] = OPTIONAL_SOURCE_FILENAMES
    expected_directories: tuple[str, ...] = LOWERCASE_WORKSPACE_DIRECTORIES
    proposal_directories: tuple[str, ...] = PROPOSAL_DIRECTORIES
    internal_directories: tuple[str, ...] = INTERNAL_DIRECTORIES


@dataclass(frozen=True)
class CharacterWorkspacePathClassification:
    kind: CharacterWorkspacePathKind
    normalized_path: str
    domain: str
    source_kind: str | None = None
    reason_ids: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "kind": self.kind.value,
            "domain": self.domain,
            "source_kind": self.source_kind,
            "reason_ids": self.reason_ids,
            "content_free": True,
        }
        if self.kind in {
            CharacterWorkspacePathKind.REQUIRED_SOURCE,
            CharacterWorkspacePathKind.OPTIONAL_SOURCE,
        }:
            result["filename"] = self.normalized_path
        return result


@dataclass(frozen=True)
class CharacterMarkdownBlock:
    heading_level: int
    heading: str
    anchor: str | None
    metadata: tuple[tuple[str, str], ...]
    start_line: int
    end_line: int
    content_hash: str

    def metadata_dict(self) -> dict[str, str]:
        return dict(self.metadata)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "heading_level": self.heading_level,
            "has_anchor": self.anchor is not None,
            "metadata_keys": tuple(key for key, _value in self.metadata),
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content_hash": self.content_hash,
            "content_free": True,
        }


@dataclass(frozen=True)
class CharacterSourceParseResult:
    status: CharacterWorkspaceValidationStatus
    filename: str
    source_kind: str
    content_hash: str | None
    line_count: int
    block_count: int
    blocks: tuple[CharacterMarkdownBlock, ...]
    error_ids: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == CharacterWorkspaceValidationStatus.VALID

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "filename": self.filename,
            "source_kind": self.source_kind,
            "status": self.status.value,
            "content_hash": self.content_hash,
            "line_count": self.line_count,
            "block_count": self.block_count,
            "error_ids": self.error_ids,
            "content_free": True,
        }


@dataclass(frozen=True)
class CharacterWorkspaceValidationResult:
    status: CharacterWorkspaceValidationStatus
    is_valid: bool
    character_id: str | None
    missing_required_sources: tuple[str, ...]
    reason_ids: tuple[str, ...]
    reserved_conflicts: tuple[str, ...]
    source_results: tuple[CharacterSourceParseResult, ...]
    content_free: bool = False

    def to_public_dict(self) -> dict[str, Any]:
        public_sources = tuple(source.to_public_dict() for source in self.source_results)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": self.status.value,
            "is_valid": self.is_valid,
            "character_id": self.character_id,
            "missing_required_sources": self.missing_required_sources,
            "reason_ids": self.reason_ids,
            "reserved_conflict_count": len(self.reserved_conflicts),
            "source_results": public_sources,
            "content_free": True,
        }


@dataclass(frozen=True)
class CharacterWorkspaceManifest:
    status: CharacterWorkspaceValidationStatus
    is_valid: bool
    character_id: str | None
    source_results: tuple[CharacterSourceParseResult, ...]
    domain_counts: tuple[tuple[str, int], ...]
    path_kind_counts: tuple[tuple[str, int], ...]
    reason_ids: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": self.status.value,
            "is_valid": self.is_valid,
            "character_id": self.character_id,
            "source_results": tuple(source.to_public_dict() for source in self.source_results),
            "domain_counts": self.domain_counts,
            "path_kind_counts": self.path_kind_counts,
            "reason_ids": self.reason_ids,
            "content_free": True,
        }


def character_workspace_layout() -> CharacterWorkspaceLayout:
    """Return the CW-A1 target layout contract."""

    return CharacterWorkspaceLayout()


def classify_character_workspace_path(relative_path: str | Path) -> CharacterWorkspacePathClassification:
    """Classify a path relative to ``characters/<character>/``.

    Absolute paths and traversal are rejected deterministically as ``unknown``.
    The function never touches the filesystem.
    """

    normalized, errors = _normalize_relative_path(relative_path)
    if errors:
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.UNKNOWN,
            normalized_path="",
            domain="unknown",
            reason_ids=errors,
        )

    parts = PurePosixPath(normalized).parts
    if not parts:
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.UNKNOWN,
            normalized_path="",
            domain="unknown",
            reason_ids=("empty_path",),
        )

    if len(parts) == 1 and normalized in REQUIRED_SOURCE_FILENAMES:
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.REQUIRED_SOURCE,
            normalized_path=normalized,
            domain="source",
            source_kind=SOURCE_KIND_BY_FILENAME[normalized],
        )

    if len(parts) == 1 and normalized in OPTIONAL_SOURCE_FILENAMES:
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.OPTIONAL_SOURCE,
            normalized_path=normalized,
            domain="source",
            source_kind=SOURCE_KIND_BY_FILENAME[normalized],
        )

    if parts[0] == ".relaylm":
        return _classify_internal_path(normalized, parts)

    if parts[0] == "relationships" and _is_markdown_file(parts):
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.RELATIONSHIP_PAGE,
            normalized_path=normalized,
            domain="relationship",
        )

    if parts[0] == "scenes" and _is_markdown_file(parts):
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.SCENE_PAGE,
            normalized_path=normalized,
            domain="scene",
        )

    if parts[0] == "memory" and _is_markdown_file(parts):
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.MEMORY_PAGE,
            normalized_path=normalized,
            domain="memory",
        )

    if parts[0] == "proposals" and len(parts) >= 2 and parts[1] in PROPOSAL_DOMAINS:
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.PROPOSAL,
            normalized_path=normalized,
            domain=parts[1],
        )

    return CharacterWorkspacePathClassification(
        kind=CharacterWorkspacePathKind.UNKNOWN,
        normalized_path=normalized,
        domain="unknown",
        reason_ids=("unrecognized_workspace_path",),
    )


def validate_character_workspace(
    root: str | Path,
    character_id: str | None = None,
    public: bool = False,
) -> CharacterWorkspaceValidationResult | dict[str, Any]:
    """Validate a character workspace root without creating or restoring files."""

    workspace_root = Path(root)
    normalized_character_id = _normalize_character_id(character_id)
    if character_id is not None and normalized_character_id is None:
        result = CharacterWorkspaceValidationResult(
            status=CharacterWorkspaceValidationStatus.INVALID_CHARACTER_ID,
            is_valid=False,
            character_id=None,
            missing_required_sources=(),
            reason_ids=("invalid_character_id",),
            reserved_conflicts=(),
            source_results=(),
            content_free=public,
        )
        return result.to_public_dict() if public else result

    if not workspace_root.exists() or not workspace_root.is_dir():
        result = CharacterWorkspaceValidationResult(
            status=CharacterWorkspaceValidationStatus.INVALID_ROOT,
            is_valid=False,
            character_id=normalized_character_id,
            missing_required_sources=(),
            reason_ids=("workspace_root_missing_or_not_directory",),
            reserved_conflicts=(),
            source_results=(),
            content_free=public,
        )
        return result.to_public_dict() if public else result

    missing_required_sources = tuple(
        filename
        for filename in REQUIRED_SOURCE_FILENAMES
        if not (workspace_root / filename).is_file()
    )

    reserved_conflicts = _find_reserved_conflicts(workspace_root)

    source_results = []
    for filename in REQUIRED_SOURCE_FILENAMES + OPTIONAL_SOURCE_FILENAMES:
        path = workspace_root / filename
        if path.is_file():
            source_results.append(
                parse_character_source_file(
                    path,
                    SOURCE_KIND_BY_FILENAME[filename],
                    public=False,
                )
            )

    malformed = any(not result.is_valid for result in source_results)
    reason_ids = []
    if missing_required_sources:
        reason_ids.append("missing_required_source")
    if reserved_conflicts:
        reason_ids.append("reserved_path_conflict")
    if malformed:
        reason_ids.append("malformed_markdown")

    if missing_required_sources:
        status = CharacterWorkspaceValidationStatus.MISSING_REQUIRED_SOURCE
    elif reserved_conflicts:
        status = CharacterWorkspaceValidationStatus.RESERVED_PATH_CONFLICT
    elif malformed:
        status = CharacterWorkspaceValidationStatus.MALFORMED_MARKDOWN
    else:
        status = CharacterWorkspaceValidationStatus.VALID

    result = CharacterWorkspaceValidationResult(
        status=status,
        is_valid=status == CharacterWorkspaceValidationStatus.VALID,
        character_id=normalized_character_id,
        missing_required_sources=missing_required_sources,
        reason_ids=tuple(reason_ids),
        reserved_conflicts=tuple(reserved_conflicts),
        source_results=tuple(source_results),
        content_free=public,
    )
    return result.to_public_dict() if public else result


def parse_character_source_file(
    path: str | Path,
    source_kind: str,
    public: bool = False,
) -> CharacterSourceParseResult | dict[str, Any]:
    """Parse one human-editable uppercase source file as a bounded contract object."""

    source_path = Path(path)
    filename = source_path.name
    if source_kind not in set(SOURCE_KIND_BY_FILENAME.values()):
        result = CharacterSourceParseResult(
            status=CharacterWorkspaceValidationStatus.MALFORMED_MARKDOWN,
            filename=filename,
            source_kind="unknown",
            content_hash=None,
            line_count=0,
            block_count=0,
            blocks=(),
            error_ids=("unknown_source_kind",),
        )
        return result.to_public_dict() if public else result

    try:
        size = source_path.stat().st_size
    except OSError:
        result = CharacterSourceParseResult(
            status=CharacterWorkspaceValidationStatus.MALFORMED_MARKDOWN,
            filename=filename,
            source_kind=source_kind,
            content_hash=None,
            line_count=0,
            block_count=0,
            blocks=(),
            error_ids=("source_file_unreadable",),
        )
        return result.to_public_dict() if public else result

    if size > MAX_SOURCE_FILE_BYTES:
        result = CharacterSourceParseResult(
            status=CharacterWorkspaceValidationStatus.MALFORMED_MARKDOWN,
            filename=filename,
            source_kind=source_kind,
            content_hash=None,
            line_count=0,
            block_count=0,
            blocks=(),
            error_ids=("source_file_too_large",),
        )
        return result.to_public_dict() if public else result

    try:
        text = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        result = CharacterSourceParseResult(
            status=CharacterWorkspaceValidationStatus.MALFORMED_MARKDOWN,
            filename=filename,
            source_kind=source_kind,
            content_hash=None,
            line_count=0,
            block_count=0,
            blocks=(),
            error_ids=("source_file_not_utf8",),
        )
        return result.to_public_dict() if public else result
    except OSError:
        result = CharacterSourceParseResult(
            status=CharacterWorkspaceValidationStatus.MALFORMED_MARKDOWN,
            filename=filename,
            source_kind=source_kind,
            content_hash=None,
            line_count=0,
            block_count=0,
            blocks=(),
            error_ids=("source_file_unreadable",),
        )
        return result.to_public_dict() if public else result

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
    """Parse Markdown headings, optional heading anchors, and ``key:: value`` metadata.

    ``source_path`` is accepted for caller symmetry but intentionally not copied
    into the returned block objects; callers must keep public diagnostics free of
    private filesystem paths.
    """

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
        return [
            CharacterMarkdownBlock(
                heading_level=0,
                heading="",
                anchor=None,
                metadata=tuple(_parse_metadata(lines)),
                start_line=1,
                end_line=len(lines) or 1,
                content_hash=_content_hash(text),
            )
        ]

    blocks: list[CharacterMarkdownBlock] = []
    for position, (start_line, level, heading, anchor) in enumerate(heading_starts):
        next_start = heading_starts[position + 1][0] if position + 1 < len(heading_starts) else len(lines) + 1
        end_line = max(start_line, next_start - 1)
        block_lines = lines[start_line - 1 : end_line]
        blocks.append(
            CharacterMarkdownBlock(
                heading_level=level,
                heading=heading,
                anchor=anchor,
                metadata=tuple(_parse_metadata(block_lines)),
                start_line=start_line,
                end_line=end_line,
                content_hash=_content_hash("\n".join(block_lines)),
            )
        )

    return blocks


def build_character_workspace_manifest(
    root: str | Path,
    public: bool = False,
) -> CharacterWorkspaceManifest | dict[str, Any]:
    """Build a read-only CW-A1 manifest summary.

    This is not the CW-A2 compiler output and it does not write
    ``.relaylm/build/character_manifest.json``.
    """

    workspace_root = Path(root)
    character_id = workspace_root.name if _normalize_character_id(workspace_root.name) else None
    validation = validate_character_workspace(workspace_root, character_id=character_id, public=False)
    assert isinstance(validation, CharacterWorkspaceValidationResult)

    domain_counts: dict[str, int] = {}
    path_kind_counts: dict[str, int] = {}
    if workspace_root.exists() and workspace_root.is_dir():
        for path in sorted(workspace_root.rglob("*")):
            try:
                relative = path.relative_to(workspace_root)
            except ValueError:
                continue
            classification = classify_character_workspace_path(relative.as_posix())
            domain_counts[classification.domain] = domain_counts.get(classification.domain, 0) + 1
            path_kind_counts[classification.kind.value] = path_kind_counts.get(classification.kind.value, 0) + 1

    manifest = CharacterWorkspaceManifest(
        status=validation.status,
        is_valid=validation.is_valid,
        character_id=character_id,
        source_results=validation.source_results,
        domain_counts=tuple(sorted(domain_counts.items())),
        path_kind_counts=tuple(sorted(path_kind_counts.items())),
        reason_ids=validation.reason_ids,
    )
    return manifest.to_public_dict() if public else manifest


def _normalize_relative_path(relative_path: str | Path) -> tuple[str, tuple[str, ...]]:
    raw = str(relative_path).replace("\\", "/")
    if not raw or raw == ".":
        return "", ("empty_path",)
    path = PurePosixPath(raw)
    if path.is_absolute() or raw.startswith("/"):
        return "", ("path_escape_rejected",)
    parts = path.parts
    if any(part in {"..", ""} for part in parts):
        return "", ("path_escape_rejected",)
    if any(part == "." for part in parts):
        return "", ("path_escape_rejected",)
    return path.as_posix(), ()


def _classify_internal_path(
    normalized: str,
    parts: tuple[str, ...],
) -> CharacterWorkspacePathClassification:
    if len(parts) >= 2 and parts[1] == "sources":
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.INTERNAL_SOURCE_EVIDENCE,
            normalized_path=normalized,
            domain="internal_source_evidence",
        )
    if len(parts) >= 2 and parts[1] == "state":
        return CharacterWorkspacePathClassification(
            kind=CharacterWorkspacePathKind.INTERNAL_STATE,
            normalized_path=normalized,
            domain="internal_state",
        )
    return CharacterWorkspacePathClassification(
        kind=CharacterWorkspacePathKind.INTERNAL_GENERATED,
        normalized_path=normalized,
        domain="internal_generated",
    )


def _is_markdown_file(parts: tuple[str, ...]) -> bool:
    return len(parts) >= 2 and parts[-1].endswith(".md") and parts[-1] == parts[-1].lower()


def _normalize_character_id(character_id: str | None) -> str | None:
    if character_id is None:
        return None
    if not CHARACTER_ID_RE.match(character_id):
        return None
    return character_id


def _find_reserved_conflicts(root: Path) -> list[str]:
    conflicts: list[str] = []

    for filename in REQUIRED_SOURCE_FILENAMES + OPTIONAL_SOURCE_FILENAMES:
        path = root / filename
        if path.exists() and not path.is_file():
            conflicts.append(filename)

    for directory in LOWERCASE_WORKSPACE_DIRECTORIES + PROPOSAL_DIRECTORIES + INTERNAL_DIRECTORIES:
        path = root / directory
        if path.exists() and not path.is_dir():
            conflicts.append(directory)

    relaylm_root = root / ".relaylm"
    if relaylm_root.exists() and not relaylm_root.is_dir():
        conflicts.append(".relaylm")

    return conflicts


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


__all__ = [
    "INTERNAL_BUILD_FILES",
    "INTERNAL_DIRECTORIES",
    "INTERNAL_STATE_FILES",
    "LOWERCASE_WORKSPACE_DIRECTORIES",
    "MAX_SOURCE_FILE_BYTES",
    "OPTIONAL_SOURCE_FILENAMES",
    "PROPOSAL_DIRECTORIES",
    "REQUIRED_SOURCE_FILENAMES",
    "SCHEMA_VERSION",
    "CharacterMarkdownBlock",
    "CharacterSourceParseResult",
    "CharacterWorkspaceLayout",
    "CharacterWorkspaceManifest",
    "CharacterWorkspacePathClassification",
    "CharacterWorkspacePathKind",
    "CharacterWorkspaceValidationResult",
    "CharacterWorkspaceValidationStatus",
    "build_character_workspace_manifest",
    "character_workspace_layout",
    "classify_character_workspace_path",
    "parse_character_source_file",
    "parse_markdown_blocks",
    "validate_character_workspace",
]
