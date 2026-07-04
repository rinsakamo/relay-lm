"""Character Workspace file-first source tree, parser contracts, and compiler projections.

CW-A1 is read-only and contract-only for source tree/parser validation. CW-A2
adds an explicit compiler for deterministic ``.relaylm/build/**`` projection
artifacts without runtime prompt injection or uppercase source mutation.
"""
from __future__ import annotations

import sys
from types import ModuleType

from . import _compiler as _compiler
from . import _constants as _constants


def _stable_fragment_id_with_source_path(domain: str, relative_path: str, block: object, occurrence: int) -> str:
    anchor = getattr(block, "anchor", None)
    if anchor:
        return _compiler._safe_id(f"{domain}:{relative_path}:{str(anchor).lstrip('^')}:{occurrence}")
    heading = _compiler._slug(getattr(block, "heading", None) or "root")
    return _compiler._safe_id(f"{domain}:{relative_path}:{heading}:{occurrence}")


def _guarded_write_character_workspace_build_artifacts(root: str | object, result: object) -> tuple[str, ...]:
    """Write build artifacts without following pre-existing artifact symlinks."""

    if not result.is_valid:
        raise ValueError("cannot write invalid Character Workspace compile result")

    root_path = _compiler.Path(root)
    build_root = _compiler._safe_build_root(root_path)
    if build_root.exists() and build_root.is_symlink():
        raise ValueError("build artifact root is a symlink")
    build_root.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    root_resolved = root_path.resolve()
    for artifact in result.artifacts:
        target = build_root / artifact.name
        if target.name != artifact.name or artifact.name not in _compiler.EXPECTED_ARTIFACTS:
            raise ValueError("unexpected build artifact path")
        if target.is_symlink():
            raise ValueError("build artifact path is a symlink")
        if not _compiler._is_relative_to(target.resolve(), root_resolved):
            raise ValueError("build artifact write escaped workspace root")
        target.write_bytes(artifact.content)
        written.append(f".relaylm/build/{artifact.name}")
    return tuple(written)


_compiler._stable_fragment_id = _stable_fragment_id_with_source_path
_compiler.write_character_workspace_build_artifacts = _guarded_write_character_workspace_build_artifacts

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
