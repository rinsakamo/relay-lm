"""Runtime-private typed-parse source and cache-writer wiring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from relaylm.client_instruction_cache_write import (
    ClientInstructionCacheWriteResult,
    build_client_instruction_cache_write_node_result,
    build_client_instruction_cache_write_preflight,
)
from relaylm.client_instruction_typed_parse import (
    ClientInstructionTypedParseResult,
    build_client_instruction_typed_parse_node_result,
    validate_client_instruction_typed_parse_candidate,
)

if TYPE_CHECKING:
    from relaylm.pipeline_context import PipelineContext

_RuntimeTypedParseSource = tuple[dict[str, Any] | None, str | None]
_RUNTIME_TYPED_PARSE_SOURCE: ContextVar[_RuntimeTypedParseSource | None] = ContextVar(
    "relaylm_client_instruction_typed_parse_runtime_source",
    default=None,
)
_RUNTIME_FAILURE_REASON = "client_instruction_cache_write_runtime_preparation_failed"
_VERSIONED_PARSE_REASON = "source_typed_parse_parser_version_not_runtime_compatible"


def set_client_instruction_typed_parse_runtime_private_source(
    candidate: Mapping[str, Any] | None,
    *,
    parser_version: str | None = None,
) -> None:
    """Set one process-local runtime-private typed parse source for the next context.

    This is intentionally not read from external request payloads. It exists so a
    trusted in-process producer, and smoke tests, can hand a request-local parse
    candidate to the C5c runtime boundary without treating frontend metadata or
    backend visible text as authoritative.
    """

    copied = deepcopy(dict(candidate)) if isinstance(candidate, Mapping) else None
    _RUNTIME_TYPED_PARSE_SOURCE.set((copied, parser_version))


def consume_client_instruction_typed_parse_runtime_private_source(
) -> _RuntimeTypedParseSource | None:
    source = _RUNTIME_TYPED_PARSE_SOURCE.get()
    _RUNTIME_TYPED_PARSE_SOURCE.set(None)
    return source


def prepare_client_instruction_cache_write_runtime_private(
    *,
    pipeline_context: PipelineContext,
) -> None:
    """Prepare typed parse and gated cache-write state without payload mutation."""

    route = pipeline_context.route
    typed_parse_requested = bool(route.client_instruction_typed_parse_enabled)
    cache_write_requested = bool(route.client_instruction_cache_write_enabled)
    if not typed_parse_requested and not cache_write_requested:
        consume_client_instruction_typed_parse_runtime_private_source()
        pipeline_context.set_client_instruction_typed_parse_result(None)
        pipeline_context.set_client_instruction_cache_write_result(None)
        return

    try:
        typed_parse_result = _prepare_typed_parse_result(
            pipeline_context=pipeline_context,
            enabled=typed_parse_requested,
        )
        pipeline_context.set_client_instruction_typed_parse_result(typed_parse_result)
        typed_parse_node = build_client_instruction_typed_parse_node_result(
            typed_parse_result
        )
        if typed_parse_node is not None:
            pipeline_context.record_node_result(typed_parse_node)

        if not cache_write_requested:
            pipeline_context.set_client_instruction_cache_write_result(None)
            return

        if (
            typed_parse_result is not None
            and typed_parse_result.parser_version is not None
        ):
            cache_write_result = ClientInstructionCacheWriteResult(
                schema_version="client_instruction_cache_write_preflight.v0",
                status="blocked",
                write_preflight_ready=False,
                dry_run_only=route.client_instruction_cache_write_dry_run_only,
                blocked_reasons=(_VERSIONED_PARSE_REASON,),
            )
        else:
            cache_write_result = build_client_instruction_cache_write_preflight(
                parse_result=typed_parse_result,
                identity_result=pipeline_context.client_instruction_identity_result,
                enabled=True,
                dry_run_only=route.client_instruction_cache_write_dry_run_only,
                managed_route=route.mode_applied != "pass_through",
                route_model=route.route_model,
                character_id=route.character_id,
                cache_root=route.client_instruction_cache_root,
                max_entry_bytes=route.client_instruction_cache_max_entry_bytes,
            )
    except Exception:
        typed_parse_result = pipeline_context.client_instruction_typed_parse_result
        if typed_parse_result is None and typed_parse_requested:
            typed_parse_result = ClientInstructionTypedParseResult(
                schema_version="client_instruction_typed_parse_runtime.v0",
                status="blocked",
                parse_ready=False,
                blocked_reasons=(_RUNTIME_FAILURE_REASON,),
            )
            pipeline_context.set_client_instruction_typed_parse_result(typed_parse_result)
        cache_write_result = ClientInstructionCacheWriteResult(
            schema_version="client_instruction_cache_write_preflight.v0",
            status="blocked",
            write_preflight_ready=False,
            dry_run_only=route.client_instruction_cache_write_dry_run_only,
            blocked_reasons=(_RUNTIME_FAILURE_REASON,),
        )

    pipeline_context.set_client_instruction_cache_write_result(cache_write_result)
    cache_write_node = build_client_instruction_cache_write_node_result(cache_write_result)
    if cache_write_node is not None:
        pipeline_context.record_node_result(cache_write_node)


def _prepare_typed_parse_result(
    *,
    pipeline_context: PipelineContext,
    enabled: bool,
) -> ClientInstructionTypedParseResult | None:
    if pipeline_context.route.mode_applied == "pass_through":
        consume_client_instruction_typed_parse_runtime_private_source()
        if not enabled:
            return None
        return ClientInstructionTypedParseResult(
            schema_version="client_instruction_typed_parse_runtime.v0",
            status="skipped",
            parse_ready=False,
            blocked_reasons=("pass_through_route_exempt",),
        )

    source = consume_client_instruction_typed_parse_runtime_private_source()
    if source is None:
        return validate_client_instruction_typed_parse_candidate(
            None,
            enabled=enabled,
            parser_version=None,
        )
    candidate, parser_version = source
    return validate_client_instruction_typed_parse_candidate(
        candidate,
        enabled=enabled,
        parser_version=parser_version,
    )


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, str) and item]
