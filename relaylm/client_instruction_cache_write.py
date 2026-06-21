"""Gated cache-write helper for typed client instruction parses."""

from __future__ import annotations

from pathlib import Path

from . import _client_instruction_cache_write_impl as _impl
from .client_instruction_identity import ClientInstructionIdentityResult
from .client_instruction_typed_parse import ClientInstructionTypedParseResult


SCHEMA_VERSION = _impl.SCHEMA_VERSION
ClientInstructionCacheWriteResult = _impl.ClientInstructionCacheWriteResult
build_client_instruction_cache_write_diagnostics = (
    _impl.build_client_instruction_cache_write_diagnostics
)
build_client_instruction_cache_write_node_result = (
    _impl.build_client_instruction_cache_write_node_result
)
assert_client_instruction_cache_write_diagnostics_content_free = (
    _impl.assert_client_instruction_cache_write_diagnostics_content_free
)


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
    max_entry_bytes: int = 65536,
) -> ClientInstructionCacheWriteResult | None:
    """Plan or apply a write while rejecting parser-versioned parse artifacts."""

    if (
        enabled
        and managed_route
        and parse_result is not None
        and parse_result.parse_ready is True
        and parse_result.artifact is not None
        and parse_result.parser_version is not None
    ):
        return ClientInstructionCacheWriteResult(
            schema_version=SCHEMA_VERSION,
            status="blocked",
            write_preflight_ready=False,
            dry_run_only=dry_run_only,
            blocked_reasons=(
                "source_typed_parse_parser_version_not_runtime_compatible",
            ),
        )

    return _impl.build_client_instruction_cache_write_preflight(
        parse_result=parse_result,
        identity_result=identity_result,
        enabled=enabled,
        dry_run_only=dry_run_only,
        managed_route=managed_route,
        route_model=route_model,
        character_id=character_id,
        cache_root=cache_root,
        max_entry_bytes=max_entry_bytes,
    )


__all__ = [
    "SCHEMA_VERSION",
    "ClientInstructionCacheWriteResult",
    "build_client_instruction_cache_write_preflight",
    "build_client_instruction_cache_write_diagnostics",
    "build_client_instruction_cache_write_node_result",
    "assert_client_instruction_cache_write_diagnostics_content_free",
]
