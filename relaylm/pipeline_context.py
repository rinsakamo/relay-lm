"""Request-local PipelineContext for RelayLM."""

from __future__ import annotations

from collections.abc import Mapping
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from relaylm.pipeline_node_result import PipelineNodeResult
from relaylm.routing import ResolvedRoute

if TYPE_CHECKING:
    from relaylm.client_instruction_identity import ClientInstructionIdentityResult
    from relaylm.client_instruction_cache_lookup_runtime import (
        ClientInstructionCacheLookupRuntimeResult,
    )
    from relaylm.client_history_exclusion_preflight import (
        ClientHistoryExclusionPreflightResult,
    )


@dataclass
class PipelineContext:
    """Carry request-local payload state and diagnostics-only node results."""

    request_id: str
    run_id: str
    original_payload: Mapping[str, Any] = field(repr=False)
    forwarded_payload: dict[str, Any] = field(repr=False)
    route: ResolvedRoute
    stream_enabled: bool
    last_mutating_step: str | None = None
    node_results: list[PipelineNodeResult] = field(default_factory=list)
    ctx_working_update_candidate: dict[str, Any] | None = field(
        default=None,
        repr=False,
    )
    _client_instruction_identity_result: ClientInstructionIdentityResult | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
    _client_instruction_cache_lookup_runtime_result: (
        ClientInstructionCacheLookupRuntimeResult | None
    ) = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
    _client_history_exclusion_preflight_result: (
        ClientHistoryExclusionPreflightResult | None
    ) = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        _ACTIVE_PIPELINE_CONTEXT.set(self)
        from relaylm.client_instruction_identity_runtime import (
            prepare_client_instruction_identity_runtime_private,
        )
        from relaylm.client_instruction_cache_lookup_runtime import (
            prepare_client_instruction_cache_lookup_runtime_private,
        )
        from relaylm.client_history_exclusion_preflight import (
            prepare_client_history_exclusion_preflight_runtime_private,
        )

        prepare_client_instruction_identity_runtime_private(pipeline_context=self)
        prepare_client_instruction_cache_lookup_runtime_private(pipeline_context=self)
        prepare_client_history_exclusion_preflight_runtime_private(pipeline_context=self)

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

    def set_ctx_working_update_candidate(
        self,
        candidate: Mapping[str, Any] | None,
    ) -> None:
        """Store one detached request-local candidate without persistence."""

        self.ctx_working_update_candidate = (
            deepcopy(dict(candidate)) if isinstance(candidate, Mapping) else None
        )

    def set_client_instruction_identity_result(
        self,
        result: ClientInstructionIdentityResult | None,
    ) -> None:
        """Store one content-bearing request-local result without serialization."""

        self._client_instruction_identity_result = result

    @property
    def client_instruction_identity_result(
        self,
    ) -> ClientInstructionIdentityResult | None:
        """Return the request-local private identity result without copying it."""

        return self._client_instruction_identity_result

    def set_client_instruction_cache_lookup_runtime_result(
        self,
        result: ClientInstructionCacheLookupRuntimeResult | None,
    ) -> None:
        """Store one content-bearing cache lookup result without serialization."""

        self._client_instruction_cache_lookup_runtime_result = result

    @property
    def client_instruction_cache_lookup_runtime_result(
        self,
    ) -> ClientInstructionCacheLookupRuntimeResult | None:
        """Return request-local private cache lookup state without copying it."""

        return self._client_instruction_cache_lookup_runtime_result

    def set_client_history_exclusion_preflight_result(
        self,
        result: ClientHistoryExclusionPreflightResult | None,
    ) -> None:
        """Store one content-bearing preflight result without serialization."""

        self._client_history_exclusion_preflight_result = result

    @property
    def client_history_exclusion_preflight_result(
        self,
    ) -> ClientHistoryExclusionPreflightResult | None:
        """Return request-local private preflight state without copying it."""

        return self._client_history_exclusion_preflight_result

    def node_results_to_log_dicts(self) -> list[dict[str, Any]]:
        """Return detached log dictionaries for recorded node results."""

        return [result.to_log_dict() for result in self.node_results]


_ACTIVE_PIPELINE_CONTEXT: ContextVar[PipelineContext | None] = ContextVar(
    "relaylm_active_pipeline_context",
    default=None,
)


def get_active_pipeline_context() -> PipelineContext | None:
    """Return the active request-local context without consuming it."""

    return _ACTIVE_PIPELINE_CONTEXT.get()


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
