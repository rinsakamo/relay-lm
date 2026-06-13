"""Runtime-private read-only instruction cache lookup wiring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING, Any, Literal

from relaylm.client_instruction_cache_lookup import (
    ClientInstructionCacheLookupResult,
    assert_client_instruction_cache_lookup_diagnostics_content_free,
    build_client_instruction_cache_lookup_diagnostics,
    resolve_client_instruction_cache_lookup,
)
from relaylm.client_instruction_cache_reader import (
    ClientInstructionCacheReadResult,
    build_client_instruction_cache_read_diagnostics,
    read_client_instruction_cache_candidate,
)
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result

if TYPE_CHECKING:
    from relaylm.pipeline_context import PipelineContext


_SCHEMA_VERSION = "client_instruction_cache_lookup_runtime.v0"
_RUNTIME_FAILURE_REASON = "instruction_cache_runtime_preparation_failed"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_DIAGNOSTIC_KEYS = frozenset(
    {
        "root_path",
        "path",
        "filename",
        "file_path",
        "cache_key",
        "cache_key_sha256",
        "instruction_fingerprint_sha256",
        "fingerprint",
        "hash",
        "route_model",
        "character_id",
        "candidate_entry",
        "lookup_entry",
        "entry",
        "scene_type",
        "scene_role",
        "scene_context",
        "scene_constraints",
        "raw_json",
        "raw_instruction",
        "content",
        "text",
        "messages",
        "exception",
        "exception_text",
    }
)


@dataclass(frozen=True)
class ClientInstructionCacheLookupRuntimeResult:
    schema_version: str
    status: Literal["hit", "miss", "blocked", "skipped"]
    reader_result: ClientInstructionCacheReadResult | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    lookup_result: ClientInstructionCacheLookupResult | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    blocked_reasons: tuple[str, ...] = ()
    applied: bool = False
    runtime_private: bool = True
    content_bearing: bool = True


def prepare_client_instruction_cache_lookup_runtime_private(
    *,
    pipeline_context: PipelineContext,
) -> None:
    """Prepare request-local read-only cache lookup state without applying it."""

    if not pipeline_context.route.client_instruction_cache_lookup_enabled:
        pipeline_context.set_client_instruction_cache_lookup_runtime_result(None)
        return

    try:
        result = _prepare(pipeline_context=pipeline_context)
    except Exception:
        result = ClientInstructionCacheLookupRuntimeResult(
            schema_version=_SCHEMA_VERSION,
            status="blocked",
            blocked_reasons=(_RUNTIME_FAILURE_REASON,),
        )
    pipeline_context.set_client_instruction_cache_lookup_runtime_result(result)


def build_client_instruction_cache_lookup_runtime_diagnostics(
    result: ClientInstructionCacheLookupRuntimeResult | None,
) -> dict[str, Any] | None:
    """Build a content-free summary for runtime-private cache lookup state."""

    if result is None:
        return None

    reader = build_client_instruction_cache_read_diagnostics(result.reader_result)
    lookup = build_client_instruction_cache_lookup_diagnostics(result.lookup_result)
    if lookup is not None:
        assert_client_instruction_cache_lookup_diagnostics_content_free(lookup)

    blocked_reasons = _unique(
        [
            *result.blocked_reasons,
            *_strings(reader.get("blocked_reasons") if reader else None),
            *_strings(lookup.get("blocked_reasons") if lookup else None),
        ]
    )
    diagnostics = {
        "schema_version": _SCHEMA_VERSION,
        "enabled": True,
        "status": result.status,
        "cache_hit": result.status == "hit",
        "cache_miss": result.status == "miss",
        "cache_read_attempted": reader is not None and reader.get("read_attempted") is True,
        "cache_lookup_attempted": lookup is not None,
        "reader_status": reader.get("status") if reader else None,
        "lookup_status": lookup.get("status") if lookup else None,
        "entry_present": reader.get("entry_present") if reader else False,
        "entry_parsed": reader.get("entry_parsed") if reader else False,
        "bytes_read": reader.get("bytes_read") if reader else 0,
        "max_entry_bytes": (
            reader.get("max_entry_bytes") if reader else result.reader_result.max_entry_bytes
            if result.reader_result is not None else 65536
        ),
        "cache_root_configured": reader.get("cache_root_configured") if reader else False,
        "cache_root_present": reader.get("cache_root_present") if reader else False,
        "reader_miss_reason": reader.get("miss_reason") if reader else None,
        "lookup_miss_reason": lookup.get("miss_reason") if lookup else None,
        "blocked_reasons": tuple(blocked_reasons),
        "runtime_private_source": True,
        "applied": result.applied,
        "read_only": True,
    }
    assert_client_instruction_cache_lookup_runtime_diagnostics_content_free(diagnostics)
    return diagnostics


def build_client_instruction_cache_lookup_runtime_node_result(
    result: ClientInstructionCacheLookupRuntimeResult | None,
) -> PipelineNodeResult | None:
    """Build a content-free PipelineNodeResult for runtime cache lookup."""

    diagnostics = build_client_instruction_cache_lookup_runtime_diagnostics(result)
    if diagnostics is None:
        return None

    decision = _decision(result)
    blocked_reasons = _strings(diagnostics.get("blocked_reasons"))
    node_diagnostics = {
        key: value for key, value in diagnostics.items() if key != "blocked_reasons"
    }
    node_result = build_pipeline_node_result(
        node_name="client_instruction_cache_lookup",
        status="diagnostic_only",
        decision=decision,
        blocked_reasons=blocked_reasons,
        diagnostics=node_diagnostics,
        artifacts=[
            {
                "artifact_name": "client_instruction_cache_lookup_runtime_summary",
                "schema_version": _SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "runtime_private_source": True,
                "read_only": True,
                "applied": False,
            }
        ],
    )
    assert_client_instruction_cache_lookup_runtime_diagnostics_content_free(
        node_result.to_log_dict()
    )
    return node_result


def assert_client_instruction_cache_lookup_runtime_diagnostics_content_free(
    value: Any,
) -> None:
    """Reject private cache content, hashes, paths, and exception details."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_DIAGNOSTIC_KEYS:
                raise ValueError(f"private/content-bearing diagnostics key: {key}")
            assert_client_instruction_cache_lookup_runtime_diagnostics_content_free(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_cache_lookup_runtime_diagnostics_content_free(nested)
        return
    if isinstance(value, str) and _SHA256_RE.fullmatch(value):
        raise ValueError("hash value is not allowed in diagnostics")


def _prepare(*, pipeline_context: PipelineContext) -> ClientInstructionCacheLookupRuntimeResult:
    route = pipeline_context.route
    if route.mode_applied == "pass_through":
        return ClientInstructionCacheLookupRuntimeResult(
            schema_version=_SCHEMA_VERSION,
            status="skipped",
            blocked_reasons=("pass_through_route_exempt",),
        )

    identity_result = pipeline_context.client_instruction_identity_result
    identity = identity_result.identity if identity_result is not None else None
    if (
        identity_result is None
        or identity_result.ready is not True
        or identity is None
        or bool(identity_result.blocked_reasons)
        or identity.empty_instruction is True
        or len(identity.candidates) == 0
    ):
        lookup_result = resolve_client_instruction_cache_lookup(
            identity_result,
            None,
            enabled=True,
            route_model=route.route_model,
            character_id=route.character_id,
        )
        return ClientInstructionCacheLookupRuntimeResult(
            schema_version=_SCHEMA_VERSION,
            status="blocked",
            lookup_result=lookup_result,
            blocked_reasons=tuple(lookup_result.blocked_reasons)
            if lookup_result is not None
            else ("source_identity_missing",),
        )

    reader_result = read_client_instruction_cache_candidate(
        root_path=route.client_instruction_cache_root,
        cache_key_sha256=identity.cache_key_sha256,
        enabled=True,
        max_entry_bytes=route.client_instruction_cache_max_entry_bytes,
    )
    if reader_result is None:
        return ClientInstructionCacheLookupRuntimeResult(
            schema_version=_SCHEMA_VERSION,
            status="blocked",
            blocked_reasons=(_RUNTIME_FAILURE_REASON,),
        )
    if reader_result.status == "blocked":
        return ClientInstructionCacheLookupRuntimeResult(
            schema_version=_SCHEMA_VERSION,
            status="blocked",
            reader_result=reader_result,
            blocked_reasons=reader_result.blocked_reasons,
        )

    candidate_entry = (
        reader_result.candidate_entry if reader_result.status == "found" else None
    )
    lookup_result = resolve_client_instruction_cache_lookup(
        identity_result,
        candidate_entry,
        enabled=True,
        route_model=route.route_model,
        character_id=route.character_id,
    )
    if lookup_result is None:
        return ClientInstructionCacheLookupRuntimeResult(
            schema_version=_SCHEMA_VERSION,
            status="blocked",
            reader_result=reader_result,
            blocked_reasons=(_RUNTIME_FAILURE_REASON,),
        )
    if lookup_result.status == "hit":
        status: Literal["hit", "miss", "blocked", "skipped"] = "hit"
    elif lookup_result.status == "miss":
        status = "miss"
    else:
        status = "blocked"
    return ClientInstructionCacheLookupRuntimeResult(
        schema_version=_SCHEMA_VERSION,
        status=status,
        reader_result=reader_result,
        lookup_result=lookup_result,
        blocked_reasons=lookup_result.blocked_reasons,
    )


def _decision(result: ClientInstructionCacheLookupRuntimeResult | None) -> str:
    if result is None:
        return _RUNTIME_FAILURE_REASON
    if result.status == "hit":
        return "instruction_cache_hit"
    if result.status == "miss":
        return "instruction_cache_miss"
    if result.status == "skipped":
        return "pass_through_route_exempt"
    reasons = set(result.blocked_reasons)
    if _RUNTIME_FAILURE_REASON in reasons:
        return _RUNTIME_FAILURE_REASON
    if result.reader_result is not None and result.reader_result.status == "blocked":
        return "instruction_cache_read_blocked"
    if result.lookup_result is not None and result.lookup_result.status == "blocked":
        lookup_reasons = set(result.lookup_result.blocked_reasons)
        if any(reason.startswith("source_") for reason in lookup_reasons):
            return "instruction_cache_source_blocked"
        return "instruction_cache_lookup_blocked"
    return "instruction_cache_source_blocked"


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
