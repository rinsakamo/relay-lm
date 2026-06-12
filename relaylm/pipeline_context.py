"""Request-local PipelineContext for RelayLM."""

from __future__ import annotations

from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from relaylm.pipeline_node_result import PipelineNodeResult
from relaylm.routing import ResolvedRoute


@dataclass
class PipelineContext:
    """Carry request-local payload state and diagnostics-only node results."""

    request_id: str
    run_id: str
    original_payload: Mapping[str, Any]
    forwarded_payload: dict[str, Any]
    route: ResolvedRoute
    stream_enabled: bool
    last_mutating_step: str | None = None
    node_results: list[PipelineNodeResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        _ACTIVE_PIPELINE_CONTEXT.set(self)

    def replace_forwarded_payload(
        self,
        new_payload: Mapping[str, Any],
        mutating_step: str,
    ) -> None:
        self.forwarded_payload = dict(new_payload)
        self.last_mutating_step = mutating_step

    def record_node_result(self, result: PipelineNodeResult) -> None:
        """Append one diagnostics-only result without changing runtime routing."""

        self.node_results.append(result)

    def node_results_to_log_dicts(self) -> list[dict[str, Any]]:
        """Return detached log dictionaries for recorded node results."""

        return [result.to_log_dict() for result in self.node_results]


_ACTIVE_PIPELINE_CONTEXT: ContextVar[PipelineContext | None] = ContextVar(
    "relaylm_active_pipeline_context",
    default=None,
)


def consume_active_pipeline_context() -> PipelineContext | None:
    """Return and clear the active request-local context for terminal diagnostics."""

    pipeline_context = _ACTIVE_PIPELINE_CONTEXT.get()
    _ACTIVE_PIPELINE_CONTEXT.set(None)
    return pipeline_context


def replace_pipeline_forwarded_payload(
    pipeline_context: PipelineContext,
    new_payload: Mapping[str, Any],
    mutating_step: str,
) -> dict[str, Any]:
    """Replace PipelineContext forwarded payload and return the current payload.

    This keeps app.py payload mutation call sites explicit while making the
    replacement contract reusable for CTX Repack hardening.
    """

    pipeline_context.replace_forwarded_payload(new_payload, mutating_step)
    return pipeline_context.forwarded_payload
