"""CW-A1 Character Workspace public dataclasses."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._constants import (
    INTERNAL_DIRECTORIES,
    LOWERCASE_WORKSPACE_DIRECTORIES,
    OPTIONAL_SOURCE_FILENAMES,
    PROPOSAL_DIRECTORIES,
    REQUIRED_SOURCE_FILENAMES,
    SCHEMA_VERSION,
)


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
        if self.kind in {CharacterWorkspacePathKind.REQUIRED_SOURCE, CharacterWorkspacePathKind.OPTIONAL_SOURCE}:
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
        return {
            "schema_version": SCHEMA_VERSION,
            "status": self.status.value,
            "is_valid": self.is_valid,
            "character_id": self.character_id,
            "missing_required_sources": self.missing_required_sources,
            "reason_ids": self.reason_ids,
            "reserved_conflict_count": len(self.reserved_conflicts),
            "source_results": tuple(source.to_public_dict() for source in self.source_results),
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
