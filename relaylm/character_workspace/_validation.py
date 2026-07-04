"""CW-A1 read-only workspace validation and manifest helpers."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import _constants as constants
from ._constants import (
    OPTIONAL_SOURCE_FILENAMES,
    REQUIRED_SOURCE_FILENAMES,
    RESERVED_DIRECTORY_PATHS,
    SOURCE_KIND_BY_FILENAME,
)
from ._parser import parse_character_source_file
from ._pathing import classify_character_workspace_path
from ._types import (
    CharacterWorkspaceLayout,
    CharacterWorkspaceManifest,
    CharacterWorkspaceValidationResult,
    CharacterWorkspaceValidationStatus,
)

CHARACTER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def character_workspace_layout() -> CharacterWorkspaceLayout:
    """Return the CW-A1 target layout contract."""

    return CharacterWorkspaceLayout()


def validate_character_workspace(
    root: str | Path,
    character_id: str | None = None,
    public: bool = False,
) -> CharacterWorkspaceValidationResult | dict[str, Any]:
    """Validate a character workspace root without creating or restoring files."""

    workspace_root = Path(root)
    normalized_character_id = _normalize_character_id(character_id)
    if character_id is not None and normalized_character_id is None:
        result = _validation_result(
            CharacterWorkspaceValidationStatus.INVALID_CHARACTER_ID,
            False,
            None,
            reason_ids=("invalid_character_id",),
            content_free=public,
        )
        return result.to_public_dict() if public else result

    if not workspace_root.exists() or not workspace_root.is_dir():
        result = _validation_result(
            CharacterWorkspaceValidationStatus.INVALID_ROOT,
            False,
            normalized_character_id,
            reason_ids=("workspace_root_missing_or_not_directory",),
            content_free=public,
        )
        return result.to_public_dict() if public else result

    missing_required_sources = tuple(
        filename for filename in REQUIRED_SOURCE_FILENAMES if not (workspace_root / filename).is_file()
    )
    reserved_conflicts = _find_reserved_conflicts(workspace_root)
    source_results = []
    for filename in REQUIRED_SOURCE_FILENAMES + OPTIONAL_SOURCE_FILENAMES:
        path = workspace_root / filename
        if path.is_file():
            source_results.append(parse_character_source_file(path, SOURCE_KIND_BY_FILENAME[filename], public=False))

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

    result = _validation_result(
        status,
        status == CharacterWorkspaceValidationStatus.VALID,
        normalized_character_id,
        missing_required_sources=missing_required_sources,
        reason_ids=tuple(reason_ids),
        reserved_conflicts=tuple(reserved_conflicts),
        source_results=tuple(source_results),
        content_free=public,
    )
    return result.to_public_dict() if public else result


def build_character_workspace_manifest(
    root: str | Path,
    public: bool = False,
) -> CharacterWorkspaceManifest | dict[str, Any]:
    """Build a read-only CW-A1 manifest summary without writing build artifacts."""

    workspace_root = Path(root)
    character_id = workspace_root.name if _normalize_character_id(workspace_root.name) else None
    validation = validate_character_workspace(workspace_root, character_id=character_id, public=False)
    assert isinstance(validation, CharacterWorkspaceValidationResult)

    domain_counts: dict[str, int] = {}
    path_kind_counts: dict[str, int] = {}
    reason_ids = list(validation.reason_ids)
    if workspace_root.exists() and workspace_root.is_dir():
        entry_count = 0
        for path in workspace_root.rglob("*"):
            entry_count += 1
            if entry_count > constants.MAX_MANIFEST_ENTRIES:
                reason_ids.append("manifest_entry_limit_reached")
                break
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
        reason_ids=tuple(reason_ids),
    )
    return manifest.to_public_dict() if public else manifest


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
    for directory in RESERVED_DIRECTORY_PATHS:
        path = root / directory
        if path.exists() and not path.is_dir():
            conflicts.append(directory)
    return conflicts


def _validation_result(
    status: CharacterWorkspaceValidationStatus,
    is_valid: bool,
    character_id: str | None,
    missing_required_sources: tuple[str, ...] = (),
    reason_ids: tuple[str, ...] = (),
    reserved_conflicts: tuple[str, ...] = (),
    source_results: tuple[Any, ...] = (),
    content_free: bool = False,
) -> CharacterWorkspaceValidationResult:
    return CharacterWorkspaceValidationResult(
        status=status,
        is_valid=is_valid,
        character_id=character_id,
        missing_required_sources=missing_required_sources,
        reason_ids=reason_ids,
        reserved_conflicts=reserved_conflicts,
        source_results=source_results,
        content_free=content_free,
    )
