"""Follow-up guards for CW-A4 RelaySLP workspace candidate planning.

This module narrows the public CW-A4 import path to bounded source-root
preflight and all-or-nothing candidate write preflight while preserving the
original core dataclasses and projection schema.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from . import _slp_core as _core
from ._slp_core import (  # re-export stable public contracts
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
)


def _bounded_find_symlink_escape_errors(root: Path) -> tuple[str, ...]:
    """Check only source roots touched by the planner, not the whole workspace."""

    try:
        root_resolved = root.resolve()
    except OSError:
        return ("workspace_root_resolve_failed",)
    for source_root in _core._SOURCE_ROOTS:  # noqa: SLF001 - deliberate follow-up guard
        directory = root / source_root
        if not directory.exists():
            continue
        try:
            resolved = directory.resolve()
        except OSError:
            return ("source_root_resolve_failed",)
        if directory.is_symlink() or not _core._is_relative_to(resolved, root_resolved):  # noqa: SLF001
            return ("symlink_escape_rejected",)
    return ()


def _preflight_artifact_batch(root: Path, writes: Iterable[tuple[str, str]]) -> tuple[str, ...]:
    """Validate a write batch before mutating so conflict cases stay all-or-nothing."""

    errors: list[str] = []
    seen: dict[str, str] = {}
    try:
        root_resolved = root.resolve()
    except OSError:
        return ("workspace_root_resolve_failed",)

    for relative_path, text in writes:
        path_errors = _core._validate_write_path(relative_path)  # noqa: SLF001
        if path_errors:
            errors.extend(path_errors)
            continue
        previous = seen.get(relative_path)
        if previous is not None:
            if previous != text:
                errors.append("candidate_artifact_conflict")
            continue
        seen[relative_path] = text

        target = root / relative_path
        parent = target.parent
        try:
            if _core._path_has_symlink(root, parent):  # noqa: SLF001
                errors.append("write_path_symlink_rejected")
                continue
            if target.is_symlink():
                errors.append("write_path_symlink_rejected")
                continue
            if not target.exists():
                continue
            target_errors = _core._validate_resolved_workspace_destination(root_resolved, target)  # noqa: SLF001
            if target_errors:
                errors.extend(target_errors)
                continue
            if target.is_dir():
                errors.append("write_path_conflict")
                continue
            existing = target.read_text(encoding="utf-8")
            if existing != text:
                errors.append("candidate_artifact_conflict")
        except OSError:
            errors.append("candidate_artifact_write_failed")
        except UnicodeDecodeError:
            errors.append("candidate_artifact_conflict_not_utf8")
    return _core._dedupe(errors)  # noqa: SLF001


def _write_artifact_batch(root: Path, writes: Iterable[tuple[str, str]], *, preflight: bool = True) -> tuple[list[str], list[str]]:
    write_items = tuple(writes)
    if preflight:
        errors = list(_preflight_artifact_batch(root, write_items))
        if errors:
            return [], errors

    written: list[str] = []
    errors: list[str] = []
    for relative_path, text in write_items:
        target = root / relative_path
        try:
            parent = target.parent
            parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                existing = target.read_text(encoding="utf-8")
                if existing == text:
                    written.append(relative_path)
                    continue
                errors.append("candidate_artifact_conflict")
                continue
            target.write_text(text, encoding="utf-8")
            written.append(relative_path)
        except OSError:
            errors.append("candidate_artifact_write_failed")
        except UnicodeDecodeError:
            errors.append("candidate_artifact_conflict_not_utf8")
    return written, errors


def _write_candidate_artifacts(root: Path, candidates: tuple[CharacterWorkspaceCandidate, ...], proposals: tuple[CharacterWorkspaceProposal, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    written: list[str] = []
    errors: list[str] = []

    candidate_writes = tuple(
        (candidate.target_path, _core._candidate_markdown(candidate))  # noqa: SLF001
        for candidate in candidates
        if not _core._candidate_is_blocked(candidate) and candidate.target_path.endswith(".md")  # noqa: SLF001
    )
    candidate_preflight_errors = _preflight_artifact_batch(root, candidate_writes)
    if candidate_preflight_errors:
        return (), _core._dedupe((*candidate_preflight_errors, "proposal_write_skipped_after_candidate_write_failure"))  # noqa: SLF001

    candidate_written, candidate_errors = _write_artifact_batch(root, candidate_writes, preflight=False)
    written.extend(candidate_written)
    errors.extend(candidate_errors)

    successful_candidate_paths = frozenset(candidate_written)
    proposal_writes = tuple(
        (proposal.target_path, _core._json_text(proposal.to_dict()))  # noqa: SLF001
        for proposal in proposals
        if str(proposal.public_summary.get("candidate_target_path", "")) in successful_candidate_paths
    )
    proposal_written, proposal_errors = _write_artifact_batch(root, proposal_writes)
    written.extend(proposal_written)
    errors.extend(proposal_errors)
    if candidate_errors:
        errors.append("proposal_write_limited_to_successful_candidates_after_candidate_write_failure")
    return tuple(dict.fromkeys(written)), _core._dedupe(errors)  # noqa: SLF001


_core._find_symlink_escape_errors = _bounded_find_symlink_escape_errors  # type: ignore[attr-defined]  # noqa: SLF001
_core._write_candidate_artifacts = _write_candidate_artifacts  # type: ignore[attr-defined]  # noqa: SLF001


def plan_character_workspace_slp_candidates(*args: Any, **kwargs: Any) -> CharacterWorkspaceSLPRun:
    return _core.plan_character_workspace_slp_candidates(*args, **kwargs)


def build_character_workspace_slp_projection(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _core.build_character_workspace_slp_projection(*args, **kwargs)


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
