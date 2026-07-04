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

_ALLOWED_METADATA_VALUE_KEYS = frozenset({"status", "importance", "priority", "scope"})
_ORIGINAL_BUILD_ARTIFACTS = _compiler._build_artifacts
_ORIGINAL_COMPILE_CHARACTER_WORKSPACE = _compiler.compile_character_workspace


def _stable_fragment_id_with_source_path(domain: str, relative_path: str, block: object, occurrence: int) -> str:
    anchor = getattr(block, "anchor", None)
    heading = _compiler._slug(getattr(block, "heading", None) or "root")
    path_digest = _compiler.hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:12]
    fragment = str(anchor).lstrip("^") if anchor else heading
    return _compiler._safe_id(f"{domain}:{path_digest}:{relative_path}:{fragment}:{occurrence}")


def _content_free_metadata(metadata: object) -> dict[str, object]:
    if not isinstance(metadata, dict):
        return {}
    return {
        str(key): value
        for key, value in sorted(metadata.items())
        if str(key) in _ALLOWED_METADATA_VALUE_KEYS
    }


def _sanitize_artifact_payload(value: object) -> object:
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            if key == "metadata":
                sanitized[key] = _content_free_metadata(item)
            else:
                sanitized[str(key)] = _sanitize_artifact_payload(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_artifact_payload(item) for item in value]
    return value


def _json_text(value: object) -> str:
    return _compiler.json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"


def _jsonl_text(rows: object) -> str:
    assert isinstance(rows, list)
    return "".join(_compiler.json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)


def _artifact_with_text(artifact: object, text: str) -> object:
    content = text.encode("utf-8")
    return _compiler.CharacterWorkspaceBuildArtifact(
        name=artifact.name,
        relative_path=artifact.relative_path,
        schema_version=artifact.schema_version,
        content=content,
        content_hash=_compiler._content_hash(text),
    )


def _sanitize_artifact_metadata(artifact: object) -> object:
    text = artifact.text()
    if artifact.name.endswith(".jsonl"):
        rows = [_sanitize_artifact_payload(_compiler.json.loads(line)) for line in text.splitlines() if line.strip()]
        return _artifact_with_text(artifact, _jsonl_text(rows))
    if artifact.name.endswith(".json"):
        return _artifact_with_text(artifact, _json_text(_sanitize_artifact_payload(_compiler.json.loads(text))))
    return artifact


def _build_artifacts_with_content_free_metadata(state: object) -> tuple[object, ...]:
    artifacts = _ORIGINAL_BUILD_ARTIFACTS(state)
    return tuple(_sanitize_artifact_metadata(artifact) for artifact in artifacts)


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


def _guarded_compile_character_workspace(root: str | object, *, write: bool = False) -> object:
    root_path = _compiler.Path(root)
    character_id = root_path.name if root_path.name else None
    preflight_errors = _compiler._preflight_root_errors(root_path)
    if preflight_errors:
        return _compiler._blocked_result(character_id, preflight_errors)

    symlink_errors = _compiler._find_symlink_escape_errors(root_path)
    if symlink_errors:
        return _compiler._blocked_result(
            character_id,
            symlink_errors,
            status=_compiler.CharacterWorkspaceValidationStatus.PATH_ESCAPE_REJECTED.value,
        )
    return _ORIGINAL_COMPILE_CHARACTER_WORKSPACE(root_path, write=write)


_compiler._stable_fragment_id = _stable_fragment_id_with_source_path
_compiler._build_artifacts = _build_artifacts_with_content_free_metadata
_compiler.compile_character_workspace = _guarded_compile_character_workspace
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
