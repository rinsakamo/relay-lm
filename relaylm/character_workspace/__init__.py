"""Character Workspace file-first source tree and parser contracts.

CW-A1 is read-only and contract-only.  It describes and validates the target
Markdown-first character workspace layout without compiler projections, runtime
wiring, uppercase source mutation, or default character restoration.
"""
from __future__ import annotations

from . import _constants as _constants
from ._constants import (
    INTERNAL_BUILD_FILES,
    INTERNAL_DIRECTORIES,
    INTERNAL_STATE_FILES,
    LOWERCASE_WORKSPACE_DIRECTORIES,
    MAX_MANIFEST_ENTRIES,
    MAX_SOURCE_FILE_BYTES,
    OPTIONAL_SOURCE_FILENAMES,
    PROPOSAL_DIRECTORIES,
    REQUIRED_SOURCE_FILENAMES,
    RESERVED_DIRECTORY_PATHS,
    SCHEMA_VERSION,
)
from ._parser import parse_character_source_file, parse_markdown_blocks
from ._pathing import classify_character_workspace_path
from ._types import (
    CharacterMarkdownBlock,
    CharacterSourceParseResult,
    CharacterWorkspaceLayout,
    CharacterWorkspaceManifest,
    CharacterWorkspacePathClassification,
    CharacterWorkspacePathKind,
    CharacterWorkspaceValidationResult,
    CharacterWorkspaceValidationStatus,
)
from ._validation import build_character_workspace_manifest, character_workspace_layout, validate_character_workspace


def __setattr__(name: str, value: object) -> None:
    # Keep smoke-time monkeypatches for the public manifest entry limit wired to
    # the implementation module that reads the bounded limit.
    globals()[name] = value
    if name == "MAX_MANIFEST_ENTRIES":
        _constants.MAX_MANIFEST_ENTRIES = value  # type: ignore[assignment]


__all__ = [
    "INTERNAL_BUILD_FILES",
    "INTERNAL_DIRECTORIES",
    "INTERNAL_STATE_FILES",
    "LOWERCASE_WORKSPACE_DIRECTORIES",
    "MAX_MANIFEST_ENTRIES",
    "MAX_SOURCE_FILE_BYTES",
    "OPTIONAL_SOURCE_FILENAMES",
    "PROPOSAL_DIRECTORIES",
    "REQUIRED_SOURCE_FILENAMES",
    "RESERVED_DIRECTORY_PATHS",
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
