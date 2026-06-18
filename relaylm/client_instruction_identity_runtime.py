"""Request-local runtime-private wiring for client instruction identity."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from relaylm.client_instruction_extraction import (
    build_client_instruction_extraction_dry_run,
)
from relaylm.client_instruction_identity import (
    ClientInstructionIdentityResult,
    assert_client_instruction_identity_diagnostics_content_free,
    build_client_instruction_identity,
    build_client_instruction_identity_diagnostics,
)
from relaylm.pipeline_context import PipelineContext
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result


_SCHEMA_VERSION = "client_instruction_identity.v0"
_RUNTIME_FAILURE_REASON = "identity_runtime_preparation_failed"


def client_instruction_identity_dependency_enabled(route: Any) -> bool:
    """Return whether identity preparation is required by a runtime consumer."""

    return bool(
        getattr(route, "client_instruction_extraction_dry_run_enabled", False)
        or getattr(route, "client_instruction_cache_lookup_enabled", False)
        or getattr(route, "client_history_exclusion_apply_enabled", False)
    )


def prepare_client_instruction_identity_runtime_private(
    *,
    pipeline_context: PipelineContext,
) -> None:
    """Prepare one request-local content-bearing identity without side effects."""

    if not client_instruction_identity_dependency_enabled(pipeline_context.route):
        pipeline_context.set_client_instruction_identity_result(None)
        return

    try:
        managed_route = pipeline_context.route.mode_applied != "pass_through"
        extraction_artifact = build_client_instruction_extraction_dry_run(
            pipeline_context.original_payload,
            enabled=True,
            managed_route=managed_route,
        )
        result = build_client_instruction_identity(
            pipeline_context.original_payload,
            extraction_artifact,
            enabled=True,
            route_model=pipeline_context.route.route_model,
            character_id=pipeline_context.route.character_id,
        )
        if result is None:
            result = _runtime_failure_result()
    except Exception:
        result = _runtime_failure_result()

    pipeline_context.set_client_instruction_identity_result(result)


def build_client_instruction_identity_runtime_node_result(
    result: ClientInstructionIdentityResult | None,
) -> PipelineNodeResult | None:
    """Build one content-free node result from a stored runtime-private result."""

    summary = build_client_instruction_identity_diagnostics(result)
    if summary is None:
        return None
    assert_client_instruction_identity_diagnostics_content_free(summary)

    ready = result is not None and result.ready is True
    decision = (
        "instruction_identity_ready"
        if ready
        else "instruction_identity_blocked"
    )
    blocked_reasons = _strings(summary.get("blocked_reasons"))
    diagnostics = {
        key: value for key, value in summary.items() if key != "blocked_reasons"
    }
    node_result = build_pipeline_node_result(
        node_name="client_instruction_identity",
        status="diagnostic_only",
        decision=decision,
        blocked_reasons=blocked_reasons,
        diagnostics=diagnostics,
        artifacts=[
            {
                "artifact_name": "client_instruction_identity_runtime_summary",
                "schema_version": _SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "runtime_private_source": True,
                "applied": False,
            }
        ],
    )
    assert_client_instruction_identity_diagnostics_content_free(
        node_result.to_log_dict()
    )
    return node_result


def _runtime_failure_result() -> ClientInstructionIdentityResult:
    return ClientInstructionIdentityResult(
        schema_version=_SCHEMA_VERSION,
        ready=False,
        identity=None,
        blocked_reasons=(_RUNTIME_FAILURE_REASON,),
    )


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return []
    return [item for item in value if isinstance(item, str) and item]
