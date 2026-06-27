"""E1-R2 explicit operator bootstrap for character-scoped Primary MEM stores.

This module is intentionally small and caller-invoked.  It resolves the
character partition through the existing Primary recall authority and prepares
only the empty store structure required before M3e/M3g can publish Primary MEM
pages.  It never enqueues work, invokes workers, or creates semantic memory
content.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from ._relaymem_primary_index_log_reconciliation_plan import (
    INDEX_PATH,
    LOG_PATH,
    MAX_INDEX_LOG_BYTES,
)
from ._relaymem_primary_page_writer_common import TARGET_DIR
from .config import RelayLMConfig
from .relaymem_primary_recall import resolve_relaymem_character_store_root

REQUEST_SCHEMA = "relaymem.character_store_bootstrap_request.v0"
RESULT_SCHEMA = "relaymem.character_store_bootstrap_result.v0"
PROJECTION_SCHEMA = "relaymem.character_store_bootstrap_projection.v0"

_INDEX_MARKER = "relaymem-primary-index-entry-v0"
_LOG_MARKER = "relaymem-primary-log-entry-v0"
_SAFE_REASON_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")
_REQUIRED_DIRS = tuple(dict.fromkeys(TARGET_DIR.values()))
_REQUIRED_CONTROL_FILES = ((INDEX_PATH, "# Index\n", _INDEX_MARKER), (LOG_PATH, "# Log\n", _LOG_MARKER))
_PUBLIC_STATUSES = {
    "dry_run_missing",
    "dry_run_ready",
    "applied_ready",
    "already_ready",
    "invalid_input",
}


@dataclass(frozen=True)
class CharacterStoreBootstrapRequest:
    schema_version: str
    runtime_private: bool
    content_included: bool
    config: RelayLMConfig
    character_id: str
    apply: bool = False


@dataclass(frozen=True)
class CharacterStoreBootstrapResult:
    schema_version: str
    status: str
    runtime_private: bool
    content_included: bool
    dry_run: bool
    apply_requested: bool
    ready: bool
    mutated: bool
    character_scope_resolved: bool
    config_scope_valid: bool
    existing_directory_count: int
    missing_directory_count: int
    created_directory_count: int
    existing_control_file_count: int
    missing_control_file_count: int
    created_control_file_count: int
    actions_required: bool
    reason_ids: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        """Return the bounded content-free operator projection."""

        return {
            "schema_version": PROJECTION_SCHEMA,
            "status": self.status,
            "diagnostics_only": True,
            "content_free": True,
            "runtime_private": False,
            "content_included": False,
            "memory_text_included": False,
            "semantic_memory_content_created": False,
            "memory_pages_mutated": False,
            "queue_authority_used": False,
            "worker_authority_used": False,
            "scheduler_authority_used": False,
            "home_admission_authority_used": False,
            "path_values_included": False,
            "digest_values_included": False,
            "character_value_included": False,
            "namespace_value_included": False,
            "runtime_identifier_values_included": False,
            "timestamp_values_included": False,
            "raw_exception_included": False,
            "dry_run": self.dry_run,
            "apply_requested": self.apply_requested,
            "ready": self.ready,
            "mutated": self.mutated,
            "character_scope_resolved": self.character_scope_resolved,
            "config_scope_valid": self.config_scope_valid,
            "actions_required": self.actions_required,
            "existing_directory_count": self.existing_directory_count,
            "missing_directory_count": self.missing_directory_count,
            "created_directory_count": self.created_directory_count,
            "existing_control_file_count": self.existing_control_file_count,
            "missing_control_file_count": self.missing_control_file_count,
            "created_control_file_count": self.created_control_file_count,
            "reason_ids": list(self.reason_ids),
        }


def execute_character_store_bootstrap(
    request: CharacterStoreBootstrapRequest,
) -> CharacterStoreBootstrapResult:
    """Plan and optionally apply the explicit character-store bootstrap."""

    if (
        request.schema_version != REQUEST_SCHEMA
        or request.runtime_private is not True
        or request.content_included is not False
    ):
        return _invalid_result("character_store_bootstrap_request_invalid", apply_requested=request.apply)

    config = request.config
    reasons = _validate_config_scope(config, request.character_id)
    root, root_reason = _resolve_safe_store_root(config, request.character_id)
    if root_reason is not None:
        reasons.append(root_reason)
    if reasons:
        return _result(
            status="invalid_input",
            dry_run=not request.apply,
            apply_requested=request.apply,
            ready=False,
            mutated=False,
            character_scope_resolved=root is not None,
            config_scope_valid=False,
            existing_dirs=0,
            missing_dirs=0,
            created_dirs=0,
            existing_controls=0,
            missing_controls=0,
            created_controls=0,
            reasons=reasons,
        )

    assert root is not None
    inspection = _inspect_required_layout(root)
    if inspection.reasons:
        return _result(
            status="invalid_input",
            dry_run=not request.apply,
            apply_requested=request.apply,
            ready=False,
            mutated=False,
            character_scope_resolved=True,
            config_scope_valid=True,
            existing_dirs=inspection.existing_dirs,
            missing_dirs=inspection.missing_dirs,
            created_dirs=0,
            existing_controls=inspection.existing_controls,
            missing_controls=inspection.missing_controls,
            created_controls=0,
            reasons=inspection.reasons,
        )

    missing = inspection.missing_dirs + inspection.missing_controls
    if not request.apply:
        return _result(
            status="dry_run_ready" if missing == 0 else "dry_run_missing",
            dry_run=True,
            apply_requested=False,
            ready=missing == 0,
            mutated=False,
            character_scope_resolved=True,
            config_scope_valid=True,
            existing_dirs=inspection.existing_dirs,
            missing_dirs=inspection.missing_dirs,
            created_dirs=0,
            existing_controls=inspection.existing_controls,
            missing_controls=inspection.missing_controls,
            created_controls=0,
            reasons=("already_ready",) if missing == 0 else ("missing_store_layout_components",),
        )

    if missing == 0:
        return _result(
            status="already_ready",
            dry_run=False,
            apply_requested=True,
            ready=True,
            mutated=False,
            character_scope_resolved=True,
            config_scope_valid=True,
            existing_dirs=inspection.existing_dirs,
            missing_dirs=0,
            created_dirs=0,
            existing_controls=inspection.existing_controls,
            missing_controls=0,
            created_controls=0,
            reasons=("already_ready",),
        )

    apply_result = _apply_missing_layout(root, inspection)
    reread = _inspect_required_layout(root)
    reasons = [*apply_result.reasons, *reread.reasons]
    ready = not reasons and reread.missing_dirs == 0 and reread.missing_controls == 0
    return _result(
        status="applied_ready" if ready else "invalid_input",
        dry_run=False,
        apply_requested=True,
        ready=ready,
        mutated=apply_result.created_dirs > 0 or apply_result.created_controls > 0,
        character_scope_resolved=True,
        config_scope_valid=True,
        existing_dirs=reread.existing_dirs,
        missing_dirs=reread.missing_dirs,
        created_dirs=apply_result.created_dirs,
        existing_controls=reread.existing_controls,
        missing_controls=reread.missing_controls,
        created_controls=apply_result.created_controls,
        reasons=("layout_ready",) if ready else reasons,
    )


def exit_code_for_character_store_bootstrap(result: CharacterStoreBootstrapResult) -> int:
    return 0 if result.status in _PUBLIC_STATUSES and result.status != "invalid_input" else 1


def _validate_config_scope(config: RelayLMConfig, character_id: object) -> list[str]:
    reasons: list[str] = []
    if not isinstance(character_id, str) or not character_id:
        return ["character_store_bootstrap_character_invalid"]
    if character_id not in config.characters:
        reasons.append("character_store_bootstrap_character_not_configured")
    if not config.memory.store_enabled:
        reasons.append("character_store_bootstrap_memory_store_disabled")
    if not isinstance(config.memory.root_path, str) or not config.memory.root_path.strip():
        reasons.append("character_store_bootstrap_root_not_configured")

    matching_namespaces = {
        route.memory_namespace
        for route in config.model_routes.values()
        if route.character_id == character_id and route.memory_namespace is not None
    }
    matching_route_count = sum(1 for route in config.model_routes.values() if route.character_id == character_id)
    if matching_route_count == 0:
        reasons.append("character_store_bootstrap_route_scope_missing")
    elif len(matching_namespaces) > 1:
        reasons.append("character_store_bootstrap_route_scope_ambiguous")
    return reasons


def _resolve_safe_store_root(
    config: RelayLMConfig,
    character_id: str,
) -> tuple[Path | None, str | None]:
    configured = config.memory.root_path
    if not isinstance(configured, str) or configured != configured.strip() or "\x00" in configured:
        return None, "character_store_bootstrap_root_invalid"
    base = Path(configured)
    if not base.is_absolute():
        return None, "character_store_bootstrap_root_not_absolute"
    if base.anchor == str(base):
        return None, "character_store_bootstrap_root_unsafe"
    if _path_has_symlink_component(base):
        return None, "character_store_bootstrap_root_symlink_blocked"
    if not base.exists() or not base.is_dir():
        return None, "character_store_bootstrap_root_missing"
    try:
        base_resolved = base.resolve(strict=True)
    except OSError:
        return None, "character_store_bootstrap_root_unresolvable"
    scoped = resolve_relaymem_character_store_root(str(base_resolved), character_id)
    if scoped is None:
        return None, "character_store_bootstrap_character_scope_unresolved"
    scoped_path = Path(scoped)
    try:
        scoped_path.relative_to(base_resolved)
    except ValueError:
        return None, "character_store_bootstrap_scope_outside_root"
    characters_root = base_resolved / "characters"
    if characters_root.exists():
        if characters_root.is_symlink():
            return None, "character_store_bootstrap_characters_root_symlink_blocked"
        if not characters_root.is_dir():
            return None, "character_store_bootstrap_characters_root_malformed"
    if scoped_path.exists():
        if scoped_path.is_symlink():
            return None, "character_store_bootstrap_character_root_symlink_blocked"
        if not scoped_path.is_dir():
            return None, "character_store_bootstrap_character_root_malformed"
    return scoped_path, None


@dataclass(frozen=True)
class _Inspection:
    existing_dirs: int
    missing_dirs: int
    existing_controls: int
    missing_controls: int
    missing_dir_paths: tuple[str, ...]
    missing_control_paths: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class _ApplyResult:
    created_dirs: int
    created_controls: int
    reasons: tuple[str, ...]


def _inspect_required_layout(root: Path) -> _Inspection:
    existing_dirs = 0
    missing_dirs: list[str] = []
    existing_controls = 0
    missing_controls: list[str] = []
    reasons: list[str] = []

    for relative in _REQUIRED_DIRS:
        reason = _relative_path_reason(relative, allow_file=False)
        if reason is not None:
            reasons.append(reason)
            continue
        path = root / PurePosixPath(relative)
        present, present_reason = _existing_dir_state(root, path)
        if present_reason is not None:
            reasons.append(present_reason)
        elif present:
            existing_dirs += 1
        else:
            missing_dirs.append(relative)

    for relative, header, marker in _REQUIRED_CONTROL_FILES:
        reason = _relative_path_reason(relative, allow_file=True)
        if reason is not None:
            reasons.append(reason)
            continue
        path = root / PurePosixPath(relative)
        state = _control_file_state(root, path, header=header.rstrip("\n"), marker=marker)
        if state == "present":
            existing_controls += 1
        elif state == "missing":
            missing_controls.append(relative)
        else:
            reasons.append(state)

    return _Inspection(
        existing_dirs=existing_dirs,
        missing_dirs=len(missing_dirs),
        existing_controls=existing_controls,
        missing_controls=len(missing_controls),
        missing_dir_paths=tuple(missing_dirs),
        missing_control_paths=tuple(missing_controls),
        reasons=tuple(_reason_ids(reasons)),
    )


def _apply_missing_layout(root: Path, inspection: _Inspection) -> _ApplyResult:
    created_dirs = 0
    created_controls = 0
    reasons: list[str] = []

    root_created, root_reason = _ensure_root_directory(root)
    if root_reason is not None:
        return _ApplyResult(
            created_dirs=created_dirs,
            created_controls=created_controls,
            reasons=tuple(_reason_ids([root_reason])),
        )
    if root_created:
        created_dirs += 1

    for relative in inspection.missing_dir_paths:
        created, reason = _mkdir_relative(root, relative)
        if reason is not None:
            reasons.append(reason)
        elif created:
            created_dirs += 1

    for relative in inspection.missing_control_paths:
        header = "# Index\n" if relative == INDEX_PATH else "# Log\n"
        created, reason = _create_control_file(root, relative, header)
        if reason is not None:
            reasons.append(reason)
        elif created:
            created_controls += 1

    return _ApplyResult(
        created_dirs=created_dirs,
        created_controls=created_controls,
        reasons=tuple(_reason_ids(reasons)),
    )


def _ensure_root_directory(root: Path) -> tuple[bool, str | None]:
    if _path_has_symlink_component(root):
        return False, "character_store_bootstrap_character_root_symlink_blocked"
    existed = root.exists()
    if existed:
        if root.is_symlink():
            return False, "character_store_bootstrap_character_root_symlink_blocked"
        if not root.is_dir():
            return False, "character_store_bootstrap_character_root_malformed"
        return False, None
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False, "character_store_bootstrap_character_root_create_failed"
    if root.is_symlink() or not root.is_dir():
        return False, "character_store_bootstrap_character_root_malformed"
    return True, None


def _existing_dir_state(root: Path, path: Path) -> tuple[bool, str | None]:
    if _contains_symlink_or_escape(root, path):
        return False, "character_store_bootstrap_layout_symlink_or_escape_blocked"
    if not path.exists():
        return False, None
    if not path.is_dir():
        return False, "character_store_bootstrap_layout_entry_malformed"
    return True, None


def _control_file_state(root: Path, path: Path, *, header: str, marker: str) -> str:
    if _contains_symlink_or_escape(root, path):
        return "character_store_bootstrap_control_file_symlink_or_escape_blocked"
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "character_store_bootstrap_control_file_malformed"
    try:
        stat = path.stat()
    except OSError:
        return "character_store_bootstrap_control_file_unreadable"
    if stat.st_nlink > 1:
        return "character_store_bootstrap_control_file_hardlink_blocked"
    if stat.st_size > MAX_INDEX_LOG_BYTES:
        return "character_store_bootstrap_control_file_size_exceeded"
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "character_store_bootstrap_control_file_utf8_invalid"
    except OSError:
        return "character_store_bootstrap_control_file_unreadable"
    lines = text.splitlines()
    if not lines or lines[0] != header:
        return "character_store_bootstrap_control_file_header_mismatch"
    prefix = f"<!-- {marker} "
    suffix = " -->"
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped.startswith("<!-- relaymem-primary-") and marker not in line:
            return "character_store_bootstrap_control_file_schema_conflict"
        if marker not in line:
            continue
        if len(line.encode("utf-8")) > 4096:
            return "character_store_bootstrap_control_marker_too_large"
        if not line.startswith(prefix) or not line.endswith(suffix):
            return "character_store_bootstrap_control_marker_malformed"
        payload = line[len(prefix) : -len(suffix)]
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return "character_store_bootstrap_control_marker_malformed"
        canonical = json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if canonical != payload:
            return "character_store_bootstrap_control_marker_noncanonical"
    return "present"


def _mkdir_relative(root: Path, relative: str) -> tuple[bool, str | None]:
    reason = _relative_path_reason(relative, allow_file=False)
    if reason is not None:
        return False, reason
    current = root
    created = False
    for part in PurePosixPath(relative).parts:
        current = current / part
        if _contains_symlink_or_escape(root, current):
            return created, "character_store_bootstrap_layout_symlink_or_escape_blocked"
        if current.exists():
            if not current.is_dir():
                return created, "character_store_bootstrap_layout_entry_malformed"
            continue
        try:
            current.mkdir()
            created = True
        except FileExistsError:
            if not current.is_dir() or current.is_symlink():
                return created, "character_store_bootstrap_layout_entry_malformed"
        except OSError:
            return created, "character_store_bootstrap_layout_create_failed"
    return created, None


def _mkdir_chain(root: Path, relative: str) -> tuple[bool, str | None]:
    if not relative or "\x00" in relative or "\\" in relative:
        return False, "character_store_bootstrap_relative_path_invalid"
    path = PurePosixPath(relative)
    if path.is_absolute() or path.as_posix() != relative:
        return False, "character_store_bootstrap_relative_path_invalid"
    if any(part in {"", ".", ".."} for part in path.parts):
        return False, "character_store_bootstrap_relative_path_invalid"
    current = root
    created = False
    for part in path.parts:
        current = current / part
        if _contains_symlink_or_escape(root, current):
            return created, "character_store_bootstrap_layout_symlink_or_escape_blocked"
        if current.exists():
            if not current.is_dir():
                return created, "character_store_bootstrap_layout_entry_malformed"
            continue
        try:
            current.mkdir()
            created = True
        except FileExistsError:
            if not current.is_dir() or current.is_symlink():
                return created, "character_store_bootstrap_layout_entry_malformed"
        except OSError:
            return created, "character_store_bootstrap_layout_create_failed"
    return created, None


def _create_control_file(root: Path, relative: str, content: str) -> tuple[bool, str | None]:
    reason = _relative_path_reason(relative, allow_file=True)
    if reason is not None:
        return False, reason
    path = root / PurePosixPath(relative)
    if _contains_symlink_or_escape(root, path):
        return False, "character_store_bootstrap_control_file_symlink_or_escape_blocked"
    parent_created, parent_reason = _mkdir_chain(root, PurePosixPath(relative).parent.as_posix())
    if parent_reason is not None:
        return parent_created, parent_reason
    if path.exists():
        return False, None
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        return False, None
    except OSError:
        return False, "character_store_bootstrap_control_file_create_failed"
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except OSError:
        return True, "character_store_bootstrap_control_file_write_failed"
    return True, None


def _relative_path_reason(relative: str, *, allow_file: bool) -> str | None:
    if not relative or "\x00" in relative or "\\" in relative:
        return "character_store_bootstrap_relative_path_invalid"
    path = PurePosixPath(relative)
    if path.is_absolute() or path.as_posix() != relative:
        return "character_store_bootstrap_relative_path_invalid"
    if any(part in {"", ".", ".."} for part in path.parts):
        return "character_store_bootstrap_relative_path_invalid"
    if allow_file:
        if relative not in {INDEX_PATH, LOG_PATH}:
            return "character_store_bootstrap_relative_path_unsupported"
    elif relative not in _REQUIRED_DIRS:
        return "character_store_bootstrap_relative_path_unsupported"
    return None


def _path_has_symlink_component(path: Path) -> bool:
    absolute = path if path.is_absolute() else Path.cwd() / path
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _contains_symlink_or_escape(root: Path, target: Path) -> bool:
    try:
        relative_parts = target.relative_to(root).parts
    except ValueError:
        return True
    if _path_has_symlink_component(root):
        return True
    current = root
    for part in relative_parts:
        current = current / part
        if current.is_symlink():
            return True
    try:
        resolved = target.resolve(strict=False)
        root_resolved = root.resolve(strict=False)
    except OSError:
        return True
    return resolved != root_resolved and root_resolved not in resolved.parents


def _result(
    *,
    status: str,
    dry_run: bool,
    apply_requested: bool,
    ready: bool,
    mutated: bool,
    character_scope_resolved: bool,
    config_scope_valid: bool,
    existing_dirs: int,
    missing_dirs: int,
    created_dirs: int,
    existing_controls: int,
    missing_controls: int,
    created_controls: int,
    reasons: Sequence[str],
) -> CharacterStoreBootstrapResult:
    return CharacterStoreBootstrapResult(
        schema_version=RESULT_SCHEMA,
        status=status if status in _PUBLIC_STATUSES else "invalid_input",
        runtime_private=True,
        content_included=False,
        dry_run=dry_run,
        apply_requested=apply_requested,
        ready=ready,
        mutated=mutated,
        character_scope_resolved=character_scope_resolved,
        config_scope_valid=config_scope_valid,
        existing_directory_count=max(0, existing_dirs),
        missing_directory_count=max(0, missing_dirs),
        created_directory_count=max(0, created_dirs),
        existing_control_file_count=max(0, existing_controls),
        missing_control_file_count=max(0, missing_controls),
        created_control_file_count=max(0, created_controls),
        actions_required=(missing_dirs + missing_controls) > 0,
        reason_ids=tuple(_reason_ids(reasons)),
    )


def _invalid_result(reason: str, *, apply_requested: bool) -> CharacterStoreBootstrapResult:
    return _result(
        status="invalid_input",
        dry_run=not apply_requested,
        apply_requested=apply_requested,
        ready=False,
        mutated=False,
        character_scope_resolved=False,
        config_scope_valid=False,
        existing_dirs=0,
        missing_dirs=0,
        created_dirs=0,
        existing_controls=0,
        missing_controls=0,
        created_controls=0,
        reasons=(reason,),
    )


def _reason_ids(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        normalized = value if isinstance(value, str) and _SAFE_REASON_RE.fullmatch(value) else "invalid_reason_id"
        if normalized not in output:
            output.append(normalized)
        if len(output) >= 32:
            break
    return output


__all__ = [
    "PROJECTION_SCHEMA",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "CharacterStoreBootstrapRequest",
    "CharacterStoreBootstrapResult",
    "execute_character_store_bootstrap",
    "exit_code_for_character_store_bootstrap",
]
