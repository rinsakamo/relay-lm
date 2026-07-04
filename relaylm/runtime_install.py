"""Explicit dry-run-first runtime install/preflight for local RelayLM operation."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .character_store_bootstrap import (
    REQUEST_SCHEMA as CHARACTER_BOOTSTRAP_REQUEST_SCHEMA,
    CharacterStoreBootstrapRequest,
    execute_character_store_bootstrap,
)
from .config import RelayLMConfig

REQUEST_SCHEMA = "relaylm.runtime_install_request.v0"
REPORT_SCHEMA = "relaylm.runtime_install_report.v0"
PROJECTION_SCHEMA = "relaylm.runtime_install_projection.v0"

_SAFE_REASON_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")
_PUBLIC_STATUSES = {"dry_run_ready", "dry_run_missing", "applied_ready", "already_ready", "invalid_input"}


@dataclass(frozen=True)
class RuntimeInstallRequest:
    schema_version: str
    runtime_private: bool
    content_included: bool
    config: RelayLMConfig
    config_path: str | None = None
    write: bool = False
    character_id: str | None = None


@dataclass(frozen=True)
class RuntimeInstallAction:
    action: str
    target_kind: str
    would_apply: bool
    applied: bool
    reason_id: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        payload = {
            "action": self.action,
            "target_kind": self.target_kind,
            "would_apply": self.would_apply,
            "applied": self.applied,
        }
        if self.reason_id is not None:
            payload["reason_id"] = self.reason_id
        return payload


@dataclass(frozen=True)
class RuntimeInstallReport:
    schema_version: str
    operation: str
    status: str
    diagnostics_only: bool
    content_free: bool
    runtime_private: bool
    content_included: bool
    dry_run: bool
    write_requested: bool
    config_loaded: bool
    runtime_layout: dict[str, bool]
    actions: tuple[RuntimeInstallAction, ...]
    blocked_reason_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    mutated: bool

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PROJECTION_SCHEMA,
            "operation": self.operation,
            "status": self.status,
            "diagnostics_only": True,
            "content_free": True,
            "runtime_private": False,
            "content_included": False,
            "path_values_included": False,
            "digest_values_included": False,
            "secret_values_included": False,
            "memory_text_included": False,
            "source_text_included": False,
            "queue_payload_included": False,
            "trace_body_included": False,
            "semantic_memory_content_created": False,
            "soul_content_created": False,
            "source_markdown_mutated": False,
            "queue_job_created": False,
            "worker_authority_used": False,
            "scheduler_authority_used": False,
            "service_registration_performed": False,
            "network_access_performed": False,
            "legacy_flat_relaymem_layout_created": False,
            "dry_run": self.dry_run,
            "write_requested": self.write_requested,
            "config_loaded": self.config_loaded,
            "runtime_layout": dict(self.runtime_layout),
            "actions": [action.to_public_dict() for action in self.actions],
            "blocked_reason_ids": list(self.blocked_reason_ids),
            "warnings": list(self.warnings),
            "mutated": self.mutated,
        }


@dataclass(frozen=True)
class _Target:
    kind: str
    path: Path


def execute_runtime_install(request: RuntimeInstallRequest) -> RuntimeInstallReport:
    if request.schema_version != REQUEST_SCHEMA or request.runtime_private is not True or request.content_included is not False:
        return invalid_runtime_install_report("runtime_install_request_invalid", write_requested=request.write, config_loaded=True)

    config_dir, config_reason = _resolve_config_dir(request.config_path)
    if config_reason is not None:
        return invalid_runtime_install_report(config_reason, write_requested=request.write, config_loaded=True)

    write = bool(request.write)
    layout = _empty_layout(character_required=request.character_id is not None)
    actions: list[RuntimeInstallAction] = []
    blocked: list[str] = []
    warnings: list[str] = []

    targets, target_layout, target_warnings, target_blocked = _collect_targets(request.config, config_dir)
    layout.update(target_layout)
    warnings.extend(target_warnings)
    blocked.extend(target_blocked)
    memory_root = next((target.path for target in targets if target.kind == "memory_root"), None)

    if request.character_id is not None:
        char_action, char_blocked, char_present = _prevalidate_character_store(
            config=request.config,
            character_id=request.character_id,
            memory_root=memory_root,
        )
        actions.extend(char_action)
        blocked.extend(char_blocked)
        layout["character_store_present"] = char_present

    for target in targets:
        reason = _directory_safety_reason(target.path, target_kind=target.kind)
        if reason is not None:
            blocked.append(reason)
            actions.append(RuntimeInstallAction("create_directory", target.kind, False, False, reason))
            continue
        if not target.path.exists():
            actions.append(RuntimeInstallAction("create_directory", target.kind, True, False))

    if not blocked and write:
        for target in targets:
            if target.path.exists() and target.path.is_dir():
                continue
            created, reason = _create_directory(target.path)
            if reason is not None:
                blocked.append(reason)
                actions.append(RuntimeInstallAction("create_directory", target.kind, False, False, reason))
                break
            if created:
                actions.append(RuntimeInstallAction("create_directory", target.kind, True, True))

    if not blocked and request.character_id is not None and memory_root is not None:
        character_actions, character_blocked, character_present = _run_character_store_bootstrap(
            config=request.config,
            character_id=request.character_id,
            memory_root=memory_root,
            write=write,
        )
        actions.extend(character_actions)
        blocked.extend(character_blocked)
        layout["character_store_present"] = character_present

    blocked_ids = tuple(_reason_ids(blocked))
    applied_any = any(action.applied for action in actions)
    would_apply_any = any(action.would_apply for action in actions)
    if blocked_ids:
        status = "invalid_input"
    elif write:
        status = "applied_ready" if applied_any else "already_ready"
    else:
        status = "dry_run_missing" if would_apply_any else "dry_run_ready"
    return _report(status, not write, write, True, layout, actions, blocked_ids, warnings, applied_any)


def invalid_runtime_install_report(reason: str, *, write_requested: bool, config_loaded: bool) -> RuntimeInstallReport:
    return _report(
        "invalid_input",
        not write_requested,
        write_requested,
        config_loaded,
        _empty_layout(character_required=False),
        (),
        (reason,),
        (),
        False,
    )


def exit_code_for_runtime_install(report: RuntimeInstallReport) -> int:
    return 0 if report.status in _PUBLIC_STATUSES and report.status != "invalid_input" else 1


def _empty_layout(*, character_required: bool) -> dict[str, bool]:
    return {
        "memory_root_configured": False,
        "character_store_required": character_required,
        "character_store_present": False,
        "queue_root_configured": False,
        "protected_source_root_configured": False,
        "durable_finalization_root_configured": False,
        "trace_parent_configured": False,
        "relayrun_checkpoint_root_configured": False,
        "client_instruction_cache_root_configured": False,
        "generated_build_root_configured": True,
    }


def _collect_targets(config: RelayLMConfig, config_dir: Path) -> tuple[list[_Target], dict[str, bool], list[str], list[str]]:
    targets: list[_Target] = []
    layout: dict[str, bool] = {}
    warnings: list[str] = []
    blocked: list[str] = []
    fields = ((config.memory.root_path, "memory_root", "memory_root_configured"),)
    for value, kind, key in fields:
        resolved, reason = _resolve_configured_directory(value, config_dir=config_dir, target_kind=kind)
        layout[key] = resolved is not None
        if reason:
            blocked.append(reason)
        elif resolved is not None:
            targets.append(_Target(kind, resolved))
        else:
            warnings.append("runtime_install_memory_root_not_configured")
    for name, kind, key in (
        ("relaymem_slp_queue_root", "queue_root", "queue_root_configured"),
        ("relaymem_slp_protected_source_root", "protected_source_root", "protected_source_root_configured"),
        ("relaymem_slp_durable_finalization_root", "durable_finalization_root", "durable_finalization_root_configured"),
        ("relayrun_checkpoint_root", "relayrun_checkpoint_root", "relayrun_checkpoint_root_configured"),
        ("client_instruction_cache_root", "client_instruction_cache_root", "client_instruction_cache_root_configured"),
    ):
        resolved, reason = _resolve_configured_directory(getattr(config, name, None), config_dir=config_dir, target_kind=kind)
        layout[key] = resolved is not None
        if reason:
            blocked.append(reason)
        elif resolved is not None:
            targets.append(_Target(kind, resolved))
    trace_parent, trace_reason = _resolve_trace_parent(config.trace.path, config_dir=config_dir)
    layout["trace_parent_configured"] = trace_parent is not None
    if trace_reason:
        blocked.append(trace_reason)
    elif trace_parent is not None:
        targets.append(_Target("trace_parent", trace_parent))
    targets.append(_Target("generated_build_root", config_dir / ".relaylm" / "build"))
    return targets, layout, warnings, blocked


def _prevalidate_character_store(*, config: RelayLMConfig, character_id: str, memory_root: Path | None) -> tuple[list[RuntimeInstallAction], list[str], bool]:
    if not isinstance(character_id, str) or not character_id:
        return [], ["runtime_install_character_id_invalid"], False
    if character_id not in config.characters:
        return [], ["character_store_bootstrap_character_not_configured"], False
    if not config.memory.store_enabled:
        return [], ["character_store_bootstrap_memory_store_disabled"], False
    if memory_root is None:
        return [], ["runtime_install_character_store_memory_root_not_configured"], False
    present = (memory_root / "characters" / character_id).is_dir()
    return [RuntimeInstallAction("character_store_bootstrap", "character_store_root", True, False, "preflight")], [], present


def _run_character_store_bootstrap(*, config: RelayLMConfig, character_id: str, memory_root: Path, write: bool) -> tuple[list[RuntimeInstallAction], list[str], bool]:
    normalized = config.model_copy(update={"memory": config.memory.model_copy(update={"root_path": str(memory_root)})})
    result = execute_character_store_bootstrap(
        CharacterStoreBootstrapRequest(
            schema_version=CHARACTER_BOOTSTRAP_REQUEST_SCHEMA,
            runtime_private=True,
            content_included=False,
            config=normalized,
            character_id=character_id,
            apply=write,
        )
    )
    public = result.to_public_dict()
    status = str(public.get("status", "invalid_input"))
    if status == "invalid_input":
        return [RuntimeInstallAction("character_store_bootstrap", "character_store_root", False, False, "runtime_install_character_store_bootstrap_failed")], [str(x) for x in public.get("reason_ids", [])], False
    return [RuntimeInstallAction("character_store_bootstrap", "character_store_root", status == "dry_run_missing" or not bool(public.get("ready")), bool(public.get("mutated")), status)], [], bool(public.get("ready")) or (memory_root / "characters" / character_id).is_dir()


def _resolve_config_dir(config_path: str | None) -> tuple[Path, str | None]:
    base = Path(config_path).parent if config_path else Path.cwd()
    try:
        return base.resolve(strict=True), None
    except OSError:
        return Path.cwd(), "runtime_install_config_parent_unresolvable"


def _resolve_trace_parent(value: object, *, config_dir: Path) -> tuple[Path | None, str | None]:
    if value is None or value == "":
        return None, None
    if not isinstance(value, str):
        return None, "runtime_install_trace_path_invalid"
    path, reason = _resolve_path_value(value, config_dir=config_dir, target_kind="trace_path")
    return (path.parent, None) if path is not None and reason is None else (None, reason)


def _resolve_configured_directory(value: object, *, config_dir: Path, target_kind: str) -> tuple[Path | None, str | None]:
    if value is None or value == "":
        return None, None
    if not isinstance(value, str):
        return None, f"runtime_install_{target_kind}_invalid"
    return _resolve_path_value(value, config_dir=config_dir, target_kind=target_kind)


def _resolve_path_value(value: str, *, config_dir: Path, target_kind: str) -> tuple[Path | None, str | None]:
    if value != value.strip() or "\x00" in value or "\\" in value:
        return None, f"runtime_install_{target_kind}_invalid"
    raw = Path(value)
    if any(part == ".." for part in raw.parts):
        return None, f"runtime_install_{target_kind}_path_traversal_blocked"
    resolved = raw if raw.is_absolute() else config_dir / raw
    if resolved.anchor == str(resolved):
        return None, f"runtime_install_{target_kind}_unsafe_root"
    return resolved, None


def _directory_safety_reason(path: Path, *, target_kind: str) -> str | None:
    absolute = path if path.is_absolute() else Path.cwd() / path
    if absolute.anchor == str(absolute):
        return f"runtime_install_{target_kind}_unsafe_root"
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            exists = current.exists()
        except OSError:
            return f"runtime_install_{target_kind}_unresolvable"
        if not exists:
            continue
        if current.is_symlink():
            return f"runtime_install_{target_kind}_symlink_blocked"
        if not current.is_dir():
            return f"runtime_install_{target_kind}_not_directory" if current == absolute else f"runtime_install_{target_kind}_parent_not_directory"
    return None


def _create_directory(path: Path) -> tuple[bool, str | None]:
    if path.exists():
        return (False, None) if path.is_dir() and not path.is_symlink() else (False, "runtime_install_directory_create_conflict")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False, "runtime_install_directory_create_failed"
    return True, None


def _report(status: str, dry_run: bool, write_requested: bool, config_loaded: bool, runtime_layout: dict[str, bool], actions: Sequence[RuntimeInstallAction], blocked_reason_ids: Sequence[str], warnings: Sequence[str], mutated: bool) -> RuntimeInstallReport:
    return RuntimeInstallReport(REPORT_SCHEMA, "runtime_install_preflight", status if status in _PUBLIC_STATUSES else "invalid_input", True, True, True, False, dry_run, write_requested, config_loaded, dict(runtime_layout), tuple(actions), tuple(_reason_ids(blocked_reason_ids)), tuple(_reason_ids(warnings)), mutated)


def _reason_ids(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        normalized = value if isinstance(value, str) and _SAFE_REASON_RE.fullmatch(value) else "invalid_reason_id"
        if normalized not in out:
            out.append(normalized)
        if len(out) >= 48:
            break
    return out


__all__ = [
    "PROJECTION_SCHEMA",
    "REPORT_SCHEMA",
    "REQUEST_SCHEMA",
    "RuntimeInstallAction",
    "RuntimeInstallReport",
    "RuntimeInstallRequest",
    "execute_runtime_install",
    "exit_code_for_runtime_install",
    "invalid_runtime_install_report",
]
