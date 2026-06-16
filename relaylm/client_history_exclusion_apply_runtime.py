"""Runtime wiring for managed-route client history exclusion apply."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from relaylm.client_history_exclusion_apply import (
    ClientHistoryExclusionApplyResult,
    build_client_history_exclusion_apply,
)
from relaylm.pipeline_context import replace_pipeline_forwarded_payload

if TYPE_CHECKING:
    from relaylm.pipeline_context import PipelineContext
    from relaylm.routing import ResolvedRoute

_RUNTIME_FAILURE_REASON = "client_history_exclusion_apply_preparation_failed"
_MUTATING_STEP = "client_history_exclusion_apply"


def run_client_history_exclusion_apply_runtime(
    *,
    pipeline_context: PipelineContext,
    compiler_used: bool,
) -> ClientHistoryExclusionApplyResult | None:
    """Prepare and optionally apply the no-instruction history-exclusion slice.

    The result and any rebuilt payload stay request-local. Actual mutation occurs
    only when both runtime gates request apply and the pure contract returns an
    explicit ``applied`` result with a detached payload.
    """

    route = pipeline_context.route
    enabled = route.client_history_exclusion_apply_enabled is True
    if not enabled:
        pipeline_context.set_client_history_exclusion_apply_result(None)
        return None

    managed_route = route.mode_applied != "pass_through"
    try:
        result = build_client_history_exclusion_apply(
            pipeline_context.forwarded_payload,
            pipeline_context.client_history_exclusion_preflight_result,
            enabled=True,
            dry_run_only=route.client_history_exclusion_apply_dry_run_only,
            managed_route=managed_route,
            compiler_used=compiler_used,
        )
    except Exception:
        result = ClientHistoryExclusionApplyResult(
            schema_version="client_history_exclusion_apply.v0",
            status="blocked",
            forwarded_payload=None,
            enabled=True,
            dry_run_only=route.client_history_exclusion_apply_dry_run_only,
            managed_route=managed_route,
            compiler_used=compiler_used,
            instruction_resolution_mode="blocked",
            payload_candidate_present=False,
            payload_mutation_applied=False,
            blocked_reasons=(_RUNTIME_FAILURE_REASON,),
        )

    pipeline_context.set_client_history_exclusion_apply_result(result)
    if _result_is_applicable(result):
        assert isinstance(result.forwarded_payload, Mapping)
        replace_pipeline_forwarded_payload(
            pipeline_context,
            result.forwarded_payload,
            _MUTATING_STEP,
        )
    return result


def client_history_exclusion_apply_blocks_backend(
    route: ResolvedRoute,
    result: ClientHistoryExclusionApplyResult | None,
) -> bool:
    """Return whether an explicit managed-route apply request must fail closed."""

    if route.client_history_exclusion_apply_enabled is not True:
        return False
    if route.client_history_exclusion_apply_dry_run_only is True:
        return False
    if route.mode_applied == "pass_through":
        return False
    return not _result_is_applicable(result)


def client_history_exclusion_apply_failure_reason(
    result: ClientHistoryExclusionApplyResult | None,
) -> str:
    """Return one bounded public reason for headers and request diagnostics."""

    if result is None:
        return "client_history_exclusion_apply_result_missing"
    if _RUNTIME_FAILURE_REASON in result.blocked_reasons:
        return _RUNTIME_FAILURE_REASON
    return "client_history_exclusion_apply_blocked"


def _result_is_applicable(
    result: ClientHistoryExclusionApplyResult | None,
) -> bool:
    return bool(
        result is not None
        and result.status == "applied"
        and result.payload_mutation_applied is True
        and isinstance(result.forwarded_payload, Mapping)
    )
