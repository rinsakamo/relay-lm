"""Character Workspace file-first source tree, parser contracts, and compiler projections.

CW-A1 is read-only and contract-only for source tree/parser validation. CW-A2
adds an explicit compiler for deterministic ``.relaylm/build/**`` projection
artifacts without runtime prompt injection or uppercase source mutation.
"""
from __future__ import annotations

import sys
from types import ModuleType

from . import _constants as _constants

from ._compiler import (  # noqa: E402
    ARTIFACT_SCHEMA_VERSIONS,
    COMPILER_NAME,
    COMPILER_SCHEMA_VERSION,
    EXPECTED_ARTIFACTS,
    TIER_ORDER,
    CharacterWorkspaceBuildArtifact,
    CharacterWorkspaceCompileResult,
    build_character_workspace_compiler_projection,
    compile_character_workspace,
    write_character_workspace_build_artifacts,
)
from ._constants import (  # noqa: E402
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
from ._parser import parse_character_source_file, parse_markdown_blocks  # noqa: E402
from ._pathing import classify_character_workspace_path  # noqa: E402
from ._types import (  # noqa: E402
    CharacterMarkdownBlock,
    CharacterSourceParseResult,
    CharacterWorkspaceLayout,
    CharacterWorkspaceManifest,
    CharacterWorkspacePathClassification,
    CharacterWorkspacePathKind,
    CharacterWorkspaceValidationResult,
    CharacterWorkspaceValidationStatus,
)
from ._validation import build_character_workspace_manifest, character_workspace_layout, validate_character_workspace  # noqa: E402


class _CharacterWorkspaceModule(ModuleType):
    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if name == "MAX_MANIFEST_ENTRIES":
            _constants.MAX_MANIFEST_ENTRIES = value  # type: ignore[assignment]


sys.modules[__name__].__class__ = _CharacterWorkspaceModule


__all__ = [
    "ARTIFACT_SCHEMA_VERSIONS",
    "COMPILER_NAME",
    "COMPILER_SCHEMA_VERSION",
    "EXPECTED_ARTIFACTS",
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
    "TIER_ORDER",
    "CharacterMarkdownBlock",
    "CharacterSourceParseResult",
    "CharacterWorkspaceBuildArtifact",
    "CharacterWorkspaceCompileResult",
    "CharacterWorkspaceLayout",
    "CharacterWorkspaceManifest",
    "CharacterWorkspacePathClassification",
    "CharacterWorkspacePathKind",
    "CharacterWorkspaceValidationResult",
    "CharacterWorkspaceValidationStatus",
    "build_character_workspace_compiler_projection",
    "build_character_workspace_manifest",
    "character_workspace_layout",
    "classify_character_workspace_path",
    "compile_character_workspace",
    "parse_character_source_file",
    "parse_markdown_blocks",
    "validate_character_workspace",
    "write_character_workspace_build_artifacts",
]
