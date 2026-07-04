"""Compatibility exports for CW-A4 RelaySLP workspace candidate planning."""
from __future__ import annotations

from ._slp_core import (
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_READ_BYTES,
    DEFAULT_MAX_SOURCE_FILES,
    SLP_CANDIDATE_SCHEMA_VERSION,
    SLP_PROJECTION_SCHEMA_VERSION,
    SLP_PROPOSAL_SCHEMA_VERSION,
    SLP_RUN_SCHEMA_VERSION,
    CharacterWorkspaceCandidate,
    CharacterWorkspaceProposal,
    CharacterWorkspaceSLPRun,
    WorkspaceSourceEvidence,
    build_character_workspace_slp_projection,
    plan_character_workspace_slp_candidates,
)

__all__ = [
    "DEFAULT_MAX_CANDIDATES",
    "DEFAULT_MAX_READ_BYTES",
    "DEFAULT_MAX_SOURCE_FILES",
    "SLP_CANDIDATE_SCHEMA_VERSION",
    "SLP_PROJECTION_SCHEMA_VERSION",
    "SLP_PROPOSAL_SCHEMA_VERSION",
    "SLP_RUN_SCHEMA_VERSION",
    "CharacterWorkspaceCandidate",
    "CharacterWorkspaceProposal",
    "CharacterWorkspaceSLPRun",
    "WorkspaceSourceEvidence",
    "build_character_workspace_slp_projection",
    "plan_character_workspace_slp_candidates",
]
