"""CW-A2 Character Workspace compiler compatibility module.

Prefer importing from :mod:`relaylm.character_workspace`; this module keeps the
implementation addressable as ``relaylm.character_workspace_compiler`` for the
CW-A2 handoff.
"""
from __future__ import annotations

from .character_workspace._compiler import (
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

__all__ = [
    "ARTIFACT_SCHEMA_VERSIONS",
    "COMPILER_NAME",
    "COMPILER_SCHEMA_VERSION",
    "EXPECTED_ARTIFACTS",
    "TIER_ORDER",
    "CharacterWorkspaceBuildArtifact",
    "CharacterWorkspaceCompileResult",
    "build_character_workspace_compiler_projection",
    "compile_character_workspace",
    "write_character_workspace_build_artifacts",
]
