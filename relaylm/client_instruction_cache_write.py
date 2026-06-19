"""Gated cache-write helper for typed client instruction parses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Literal

from relaylm.client_instruction_cache_lookup import resolve_client_instruction_cache_lookup
from relaylm.client_instruction_identity import ClientInstructionIdentityResult
from relaylm.client_instruction_typed_parse import ClientInstructionTypedParseResult
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result

SCHEMA_VERSION = "client_instruction_cache_write_preflight.v0"
_ENTRY_SCHEMA_VERSION = "relaylm.client_instruction_cache.v0"
_DEFAULT_MAX_ENTRY_BYTES = 65536
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_DIAGNOSTIC_KEYS = frozenset(
    {
        "cache_key",
        "cache_key_sha256",
        "instruction_fingerprint_sha256",
        "fingerprint",
        "hash",
        "route_model",
        "character_id",
        "candidate",
        "entry",
        "cache_entry",
        "scene_state",
        "scene_role",
        "scene_context",
        "scene_constraints",
        "role_name",
        "setting",
        "task",
        "participants",
        "constraint_type",
        "value",
        "raw_instruction",
        "raw_response",
        "content",
        "text",
        "messages",
        "prompt",
        "path",
        "filename",
        "file_path",
        "root_path",
    }
)


@dataclass(frozen=True)
class ClientInstructionCacheWriteResult:
    schema_version: str
    status: Literal["ready", "dry_run", "blocked", "skipped", "written"]
    write_preflight_ready: bool
    dry_run_only: bool
    cache_entry_candidate: Mapping[str, Any] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    blocked_reasons: tuple[str, ...] = ()
    cache_entry_candidate_built: bool = False
    cache_write_attempted: bool = False
    cache_entry_written: bool = False
    cache_entry_bytes: int | None = None
    atomic_write_used: bool = False
    runtime_private: bool = True
    content_bearing: bool = True
    diagnostics_only: bool = True
    applied: bool = False


@dataclass(frozen=True)
class _WriteOutcome:
    written: bool
    attempted: bool
    byte_count: int | None
    blocked_reasons: tuple[str, ...] = ()


def build_client_instruction_cache_write_preflight(
    *,
    parse_result: ClientInstructionTypedParseResult | None,
    identity_result: ClientInstructionIdentityResult | None,
    enabled: bool,
    dry_run_only: bool,
    managed_route: bool,
    route_model: str,
    character_id: str | None,
    cache_root: str | Path | None = None,
    max_entry_bytes: int = _DEFAULT_MAX_ENTRY_BYTES,
) -> ClientInstructionCacheWriteResult | None:
    """Plan or apply a gated client-instruction cache write.

    The default/dry-run path performs no filesystem mutation. When
    ``dry_run_only`` is false, the helper validates the candidate entry through
    the cache lookup contract and writes one JSON file under ``cache_root`` via
    temp-file + fsync + atomic replace.
    """

    if not enabled:
        return None
    if not managed_route:
        return ClientInstructionCacheWriteResult(
            schema_version=SCHEMA_VERSION,
            status="skipped",
            write_preflight_ready=False,
            dry_run_only=dry_run_only,
            blocked_reasons=("pass_through_route_exempt",),
        )

    identity = identity_result.identity if identity_result is not None else None
    reasons: list[str] = []
    if identity_result is None or identity_result.ready is not True or identity is None:
        reasons.append("source_identity_not_ready")
    elif (
        identity.empty_instruction is True
        or len(identity.candidates) == 0
        or not _is_sha256(identity.cache_key_sha256)
        or not _is_sha256(identity.instruction_fingerprint_sha256)
    ):
        reasons.append("source_identity_invalid")

    if parse_result is None or parse_result.parse_ready is not True or parse_result.artifact is None:
        reasons.append("source_typed_parse_not_ready")
    elif parse_result.artifact.scene_type is None:
        reasons.append("source_typed_parse_scene_type_missing")

    if not _bounded_text(route_model, 128) or (
        character_id is not None and not _bounded_text(character_id, 128)
    ):
        reasons.append("cache_write_scope_invalid")

    if reasons:
        return ClientInstructionCacheWriteResult(
            schema_version=SCHEMA_VERSION,
            status="blocked",
            write_preflight_ready=False,
            dry_run_only=dry_run_only,
            blocked_reasons=tuple(_unique(reasons)),
        )

    assert identity is not None and parse_result is not None and parse_result.artifact is not None
    artifact = parse_result.artifact
    entry = {
        "schema_version": _ENTRY_SCHEMA_VERSION,
        "cache_key_sha256": identity.cache_key_sha256,
        "instruction_fingerprint_sha256": identity.instruction_fingerprint_sha256,
        "route_model": route_model,
        "character_id": character_id,
        "instruction_parse_schema_version": artifact.schema_version,
        "authority_policy_version": "client_instruction_authority.v1",
        "parser_version": parse_result.parser_version,
        "parse_status": "valid",
        "scene_state": {
            "scene_type": artifact.scene_type,
            "scene_role": _entry_role(artifact.scene_role),
            "scene_context": _entry_context(artifact.scene_context),
            "scene_constraints": [
                {"constraint_type": item.constraint_type, "value": item.value}
                for item in artifact.scene_constraints
            ],
        },
        "durable_candidate_count": len(artifact.durable_persona_candidates),
        "blocked_instruction_kinds": list(artifact.blocked_instruction_kinds),
        "raw_instruction_persisted": False,
        "raw_response_persisted": False,
    }
    reader_reasons = _reader_validation_reasons(
        entry,
        identity_result,
        route_model=route_model,
        character_id=character_id,
        parser_version=parse_result.parser_version,
    )
    if reader_reasons:
        return ClientInstructionCacheWriteResult(
            schema_version=SCHEMA_VERSION,
            status="blocked",
            write_preflight_ready=False,
            dry_run_only=dry_run_only,
            cache_entry_candidate=entry,
            cache_entry_candidate_built=True,
            blocked_reasons=tuple(_unique(reader_reasons)),
        )

    if dry_run_only:
        return ClientInstructionCacheWriteResult(
            schema_version=SCHEMA_VERSION,
            status="dry_run",
            write_preflight_ready=True,
            dry_run_only=True,
            cache_entry_candidate=entry,
            cache_entry_candidate_built=True,
        )

    outcome = _write_cache_entry(
        entry,
        cache_key_sha256=identity.cache_key_sha256,
        cache_root=cache_root,
        max_entry_bytes=max_entry_bytes,
    )
    if not outcome.written:
        return ClientInstructionCacheWriteResult(
            schema_version=SCHEMA_VERSION,
            status="blocked",
            write_preflight_ready=False,
            dry_run_only=False,
            cache_entry_candidate=entry,
            cache_entry_candidate_built=True,
            cache_write_attempted=outcome.attempted,
            cache_entry_written=False,
            cache_entry_bytes=outcome.byte_count,
            blocked_reasons=outcome.blocked_reasons,
        )

    return ClientInstructionCacheWriteResult(
        schema_version=SCHEMA_VERSION,
        status="written",
        write_preflight_ready=True,
        dry_run_only=False,
        cache_entry_candidate=entry,
        cache_entry_candidate_built=True,
        cache_write_attempted=True,
        cache_entry_written=True,
        cache_entry_bytes=outcome.byte_count,
        atomic_write_used=True,
        diagnostics_only=False,
        applied=True,
    )


def build_client_instruction_cache_write_diagnostics(
    result: ClientInstructionCacheWriteResult | None,
) -> dict[str, Any] | None:
    if result is None:
        return None
    diagnostics = {
        "schema_version": result.schema_version,
        "enabled": True,
        "status": result.status,
        "write_preflight_ready": result.write_preflight_ready,
        "dry_run_only": result.dry_run_only,
        "cache_entry_candidate_built": result.cache_entry_candidate_built,
        "cache_write_attempted": result.cache_write_attempted,
        "cache_entry_written": result.cache_entry_written,
        "cache_entry_bytes": result.cache_entry_bytes,
        "atomic_write_used": result.atomic_write_used,
        "raw_instruction_persisted": False,
        "raw_response_persisted": False,
        "blocked_reasons": tuple(result.blocked_reasons),
        "diagnostics_only": result.diagnostics_only,
        "runtime_private_source": result.runtime_private,
        "content_bearing_source": result.content_bearing,
        "applied": result.applied,
    }
    assert_client_instruction_cache_write_diagnostics_content_free(diagnostics)
    return diagnostics


def build_client_instruction_cache_write_node_result(
    result: ClientInstructionCacheWriteResult | None,
) -> PipelineNodeResult | None:
    diagnostics = build_client_instruction_cache_write_diagnostics(result)
    if result is None or diagnostics is None:
        return None
    return build_pipeline_node_result(
        node_name="client_instruction_cache_write",
        status="applied" if result.applied else "diagnostic_only",
        decision=_decision(result),
        blocked_reasons=list(result.blocked_reasons),
        diagnostics={key: value for key, value in diagnostics.items() if key != "blocked_reasons"},
        artifacts=[
            {
                "artifact_name": "client_instruction_cache_write_summary",
                "schema_version": SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": result.diagnostics_only,
                "content_free": True,
                "runtime_private_source": True,
                "applied": result.applied,
            }
        ],
    )


def assert_client_instruction_cache_write_diagnostics_content_free(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_DIAGNOSTIC_KEYS:
                raise ValueError(f"private/content-bearing diagnostics key: {key}")
            assert_client_instruction_cache_write_diagnostics_content_free(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_cache_write_diagnostics_content_free(nested)
        return
    if isinstance(value, str) and _SHA256_RE.fullmatch(value):
        raise ValueError("hash value is not allowed in diagnostics")


def _reader_validation_reasons(
    entry: Mapping[str, Any],
    identity_result: ClientInstructionIdentityResult,
    *,
    route_model: str,
    character_id: str | None,
    parser_version: str | None,
) -> list[str]:
    lookup = resolve_client_instruction_cache_lookup(
        identity_result,
        entry,
        enabled=True,
        route_model=route_model,
        character_id=character_id,
        parser_version=parser_version,
    )
    if lookup is not None and lookup.status == "hit" and lookup.hit is True:
        return []
    reasons = ["cache_entry_reader_validation_failed"]
    if lookup is not None:
        reasons.extend(lookup.blocked_reasons)
        if lookup.miss_reason:
            reasons.append(lookup.miss_reason)
    return _unique(reasons)


def _write_cache_entry(
    entry: Mapping[str, Any],
    *,
    cache_key_sha256: str,
    cache_root: str | Path | None,
    max_entry_bytes: int,
) -> _WriteOutcome:
    if not _is_sha256(cache_key_sha256):
        return _WriteOutcome(False, False, None, ("cache_key_invalid",))
    if cache_root is None or not str(cache_root).strip():
        return _WriteOutcome(False, False, None, ("cache_root_missing",))
    if not _bounded_int(max_entry_bytes, 1048576) or int(max_entry_bytes) <= 0:
        return _WriteOutcome(False, False, None, ("cache_entry_size_limit_invalid",))

    encoded = (
        json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    byte_count = len(encoded)
    if byte_count > int(max_entry_bytes):
        return _WriteOutcome(False, False, byte_count, ("cache_entry_too_large",))

    root = Path(cache_root)
    if root.exists() and root.is_symlink():
        return _WriteOutcome(False, False, byte_count, ("cache_root_symlink_rejected",))

    attempted = False
    tmp_name: str | None = None
    tmp_fd: int | None = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        root_resolved = root.resolve(strict=True)
        if not root_resolved.is_dir():
            return _WriteOutcome(False, False, byte_count, ("cache_root_not_directory",))

        target = root_resolved / f"{cache_key_sha256}.json"
        if target.is_symlink():
            return _WriteOutcome(False, False, byte_count, ("cache_target_symlink_rejected",))
        if target.parent.resolve(strict=True) != root_resolved:
            return _WriteOutcome(False, False, byte_count, ("cache_target_outside_root",))

        tmp_fd, tmp_name = tempfile.mkstemp(
            prefix=f".{cache_key_sha256}.",
            suffix=".tmp",
            dir=root_resolved,
        )
        attempted = True
        with os.fdopen(tmp_fd, "wb") as handle:
            tmp_fd = None
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        assert tmp_name is not None
        os.replace(tmp_name, target)
        tmp_name = None
        _fsync_directory(root_resolved)
    except Exception:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_name:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass
        return _WriteOutcome(False, attempted, byte_count, ("cache_write_failed",))
    return _WriteOutcome(True, attempted, byte_count, ())


def _fsync_directory(path: Path) -> None:
    try:
        dir_fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)


def _entry_role(role: Any) -> dict[str, Any] | None:
    if role is None:
        return None
    return {
        "role_name": role.role_name,
        "role_scope": role.role_scope,
        "role_source": "client_instruction_cache",
        "confidence": role.confidence,
    }


def _entry_context(context: Any) -> dict[str, Any]:
    return {
        "setting": context.setting,
        "task": context.task,
        "participants": list(context.participants),
    }


def _decision(result: ClientInstructionCacheWriteResult) -> str:
    if result.status == "dry_run":
        return "client_instruction_cache_write_dry_run"
    if result.status == "written":
        return "client_instruction_cache_write_written"
    if result.status == "ready":
        return "client_instruction_cache_write_ready"
    if result.status == "skipped":
        return "client_instruction_cache_write_skipped"
    return "client_instruction_cache_write_blocked"


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _bounded_text(value: Any, maximum: int) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def _bounded_int(value: Any, maximum: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= maximum
    )


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))
