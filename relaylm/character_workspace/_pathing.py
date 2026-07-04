"""CW-A1 workspace path classification helpers."""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from ._constants import OPTIONAL_SOURCE_FILENAMES, PROPOSAL_DOMAINS, REQUIRED_SOURCE_FILENAMES, SOURCE_KIND_BY_FILENAME
from ._types import CharacterWorkspacePathClassification, CharacterWorkspacePathKind

WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:($|/)")


def classify_character_workspace_path(relative_path: str | Path) -> CharacterWorkspacePathClassification:
    """Classify a path relative to ``characters/<character>/`` without touching the filesystem."""

    normalized, errors = _normalize_relative_path(relative_path)
    if errors:
        return _classification(CharacterWorkspacePathKind.UNKNOWN, "", "unknown", reason_ids=errors)

    parts = PurePosixPath(normalized).parts
    if not parts:
        return _classification(CharacterWorkspacePathKind.UNKNOWN, "", "unknown", reason_ids=("empty_path",))
    if len(parts) == 1 and normalized in REQUIRED_SOURCE_FILENAMES:
        return _classification(
            CharacterWorkspacePathKind.REQUIRED_SOURCE,
            normalized,
            "source",
            source_kind=SOURCE_KIND_BY_FILENAME[normalized],
        )
    if len(parts) == 1 and normalized in OPTIONAL_SOURCE_FILENAMES:
        return _classification(
            CharacterWorkspacePathKind.OPTIONAL_SOURCE,
            normalized,
            "source",
            source_kind=SOURCE_KIND_BY_FILENAME[normalized],
        )
    if parts[0] == ".relaylm":
        return _classify_internal_path(normalized, parts)
    if parts[0] == "relationships" and _is_markdown_file(parts):
        return _classification(CharacterWorkspacePathKind.RELATIONSHIP_PAGE, normalized, "relationship")
    if parts[0] == "scenes" and _is_markdown_file(parts):
        return _classification(CharacterWorkspacePathKind.SCENE_PAGE, normalized, "scene")
    if parts[0] == "memory" and _is_markdown_file(parts):
        return _classification(CharacterWorkspacePathKind.MEMORY_PAGE, normalized, "memory")
    if parts[0] == "proposals" and len(parts) >= 2 and parts[1] in PROPOSAL_DOMAINS:
        return _classification(CharacterWorkspacePathKind.PROPOSAL, normalized, parts[1])
    return _classification(
        CharacterWorkspacePathKind.UNKNOWN,
        normalized,
        "unknown",
        reason_ids=("unrecognized_workspace_path",),
    )


def _normalize_relative_path(relative_path: str | Path) -> tuple[str, tuple[str, ...]]:
    raw = str(relative_path).replace("\\", "/")
    if not raw or raw == ".":
        return "", ("empty_path",)
    if raw.startswith("/") or raw.startswith("//") or WINDOWS_DRIVE_RE.match(raw):
        return "", ("path_escape_rejected",)
    if any(part in {"", ".", ".."} for part in raw.split("/")):
        return "", ("path_escape_rejected",)
    path = PurePosixPath(raw)
    if path.is_absolute():
        return "", ("path_escape_rejected",)
    return path.as_posix(), ()


def _classify_internal_path(normalized: str, parts: tuple[str, ...]) -> CharacterWorkspacePathClassification:
    if len(parts) >= 2 and parts[1] == "sources":
        return _classification(CharacterWorkspacePathKind.INTERNAL_SOURCE_EVIDENCE, normalized, "internal_source_evidence")
    if len(parts) >= 2 and parts[1] == "state":
        return _classification(CharacterWorkspacePathKind.INTERNAL_STATE, normalized, "internal_state")
    return _classification(CharacterWorkspacePathKind.INTERNAL_GENERATED, normalized, "internal_generated")


def _classification(
    kind: CharacterWorkspacePathKind,
    normalized_path: str,
    domain: str,
    source_kind: str | None = None,
    reason_ids: tuple[str, ...] = (),
) -> CharacterWorkspacePathClassification:
    return CharacterWorkspacePathClassification(
        kind=kind,
        normalized_path=normalized_path,
        domain=domain,
        source_kind=source_kind,
        reason_ids=reason_ids,
    )


def _is_markdown_file(parts: tuple[str, ...]) -> bool:
    return len(parts) >= 2 and parts[-1].endswith(".md") and parts[-1] == parts[-1].lower()
