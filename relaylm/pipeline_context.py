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
    from relaylm.client_history_exclusion_apply import (
        ClientHistoryExclusionApplyResult,
    )
    from relaylm.client_history_exclusion_apply_v1_types import (
        ClientHistoryExclusionApplyV1Result,
    )
    from relaylm.client_instruction_cache_lookup_runtime import (
        ClientInstructionCacheLookupRuntimeResult,
    )
    from relaylm.client_instruction_cache_write import ClientInstructionCacheWriteResult
    from relaylm.client_instruction_identity import ClientInstructionIdentityResult
    from relaylm.client_instruction_typed_parse import ClientInstructionTypedParseResult
    from relaylm.client_history_exclusion_preflight import (
        ClientHistoryExclusionPreflightResult,
    )
    from relaylm.compiler import ContextBlock

_E1R1_RELEVANT_REQUEST_HEADERS = frozenset({
    "x-relaylm-trusted-scene-admission",
    "x-relaylm-trusted-home-scene-admission",
    "x-relaylm-memory-persistence-trust",
})


@dataclass
class PipelineContext:
    """Carry request-local payload state and diagnostics-only node results."""

    request_id: str
    run_id: str
    original_payload: Mapping[str, Any] = field(repr=False)
    forwarded_payload: dict[str, Any] = field(repr=False)
    route: ResolvedRoute
    stream_enabled: bool
    request_headers: Mapping[str, str] = field(default_factory=dict, repr=False)
    last_mutating_step: str | None = None
    node_results: list[PipelineNodeResult] = field(default_factory=list)
    ctx_working_update_candidate: dict[str, Any] | None = field(
        default=None,
        repr=False,
    )
    _compiled_context_blocks: tuple[ContextBlock, ...] | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
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
    _client_instruction_typed_parse_result: ClientInstructionTypedParseResult | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
    _client_instruction_cache_write_result: ClientInstructionCacheWriteResult | None = field(
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
    _client_history_exclusion_apply_result: (
        ClientHistoryExclusionApplyResult
        | ClientHistoryExclusionApplyV1Result
        | None
    ) = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        from relaylm.request_compiler import (
            consume_compiled_context_blocks_runtime_private,
        )

        self.request_headers = _sanitized_relevant_request_headers(
            self.request_headers
        )
        self._compiled_context_blocks = (
            consume_compiled_context_blocks_runtime_private()
        )
        _ACTIVE_PIPELINE_CONTEXT.set(self)
        from relaylm.client_instruction_identity_runtime import (
            prepare_client_instruction_identity_runtime_private,
        )
        from relaylm.client_instruction_cache_lookup_runtime import (
            prepare_client_instruction_cache_lookup_runtime_private,
        )
        from relaylm.client_instruction_cache_write_runtime import (
            prepare_client_instruction_cache_write_runtime_private,
        )
        from relaylm.client_history_exclusion_preflight import (
            prepare_client_history_exclusion_preflight_runtime_private,
        )
        from relaylm.client_history_exclusion_apply_runtime import (
            run_client_history_exclusion_apply_runtime,
        )

        prepare_client_instruction_identity_runtime_private(pipeline_context=self)
        prepare_client_instruction_cache_lookup_runtime_private(pipeline_context=self)
        prepare_client_instruction_cache_write_runtime_private(pipeline_context=self)
        prepare_client_history_exclusion_preflight_runtime_private(pipeline_context=self)
        compiler_used = self.route.mode_applied == "memory_light"
        self._run_instruction_bearing_apply_if_selected(
            compiler_used=compiler_used,
        )
        run_client_history_exclusion_apply_runtime(
            pipeline_context=self,
            compiler_used=compiler_used,
        )

    def _run_instruction_bearing_apply_if_selected(
        self,
        *,
        compiler_used: bool,
    ) -> None:
        from relaylm.client_history_exclusion_apply_v1_prepare import (
            prepare_client_history_exclusion_apply_v1,
        )
        from relaylm.client_history_exclusion_apply_v1_runtime import (
            request_uses_instruction_bearing_v1,
        )
        from relaylm.client_history_exclusion_apply_v1_types import (
            ClientHistoryExclusionApplyV1Result,
            SCHEMA_VERSION,
            build_client_history_exclusion_apply_v1_result,
        )
        from relaylm.managed_apply_finalize import (
            finalize_instruction_bearing_apply,
        )
        from relaylm.managed_apply_projection import (
            build_instruction_bearing_apply_node_result,
        )

        route = self.route
        if route.client_history_exclusion_apply_enabled is not True:
            return
        if not request_uses_instruction_bearing_v1(self):
            return

        managed_route = route.mode_applied != "pass_through"
        dry_run_only = route.client_history_exclusion_apply_dry_run_only
        try:
            if not managed_route:
                result = build_client_history_exclusion_apply_v1_result(
                    status="skipped",
                    dry_run_only=dry_run_only,
                    managed_route=False,
                    compiler_used=compiler_used,
                    blocked_reasons=("pass_through_route_exempt",),
                )
            else:
                preflight = self.client_history_exclusion_preflight_result
                identity = self.client_instruction_identity_result
                prepared, prepare_reasons, selection, evidence_char_count = (
                    prepare_client_history_exclusion_apply_v1(
                        self.original_payload,
                        self.forwarded_payload,
                        self.compiled_context_blocks,
                        preflight,
                        identity,
                    )
                )
                reasons = list(prepare_reasons)
                if compiler_used is not True:
                    reasons.insert(0, "compiled_profile_required")
                if reasons or prepared is None:
                    result = build_client_history_exclusion_apply_v1_result(
                        status="blocked",
                        dry_run_only=dry_run_only,
                        managed_route=True,
                        compiler_used=compiler_used,
                        original_compiled_message_count=(
                            len(self.forwarded_payload.get("messages", []))
                            if isinstance(
                                self.forwarded_payload.get("messages"),
                                list,
                            )
                            else 0
                        ),
                        instruction_resolution_mode=getattr(
                            preflight,
                            "instruction_resolution_mode",
                            "blocked",
                        ),
                        instruction_source_mode=(
                            selection.source_mode
                            if selection is not None
                            else "not_applicable"
                        ),
                        instruction_source_provenance_present=(
                            selection.provenance_present
                            if selection is not None
                            else False
                        ),
                        instruction_candidate_count=(
                            len(identity.identity.candidates)
                            if identity is not None
                            and identity.identity is not None
                            else 0
                        ),
                        selected_instruction_candidate_count=(
                            len(selection.selected_source_indices)
                            if selection is not None
                            else 0
                        ),
                        excluded_instruction_candidate_count=(
                            len(selection.excluded_source_indices)
                            if selection is not None
                            else 0
                        ),
                        instruction_evidence_rendered_char_count=(
                            evidence_char_count
                        ),
                        blocked_reasons=tuple(reasons),
                    )
                else:
                    result = finalize_instruction_bearing_apply(
                        prepared,
                        dry_run_only=dry_run_only,
                        instruction_resolution_mode=getattr(
                            preflight,
                            "instruction_resolution_mode",
                            "blocked",
                        ),
                    )
        except Exception:
            result = ClientHistoryExclusionApplyV1Result(
                schema_version=SCHEMA_VERSION,
                status="blocked",
                dry_run_only=dry_run_only,
                managed_route=managed_route,
                compiler_used=compiler_used,
                blocked_reasons=(
                    "client_history_exclusion_apply_preparation_failed",
                ),
            )

        self.set_client_history_exclusion_apply_result(result)
        self.record_node_result(
            build_instruction_bearing_apply_node_result(result)
        )
        if (
            result.status == "applied"
            and result.payload_mutation_applied is True
            and isinstance(result.forwarded_payload, Mapping)
        ):
            self.replace_forwarded_payload(
                result.forwarded_payload,
                "client_history_exclusion_apply",
            )

    @property
    def compiled_context_blocks(self) -> tuple[ContextBlock, ...] | None:
        """Return request-local typed pre-render compiler blocks."""

        return self._compiled_context_blocks

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

    def set_request_headers(self, headers: Mapping[str, str] | None) -> None:
        """Retain only E1-R1 trust-relevant request header names."""

        self.request_headers = _sanitized_relevant_request_headers(headers)

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

    def set_client_instruction_typed_parse_result(
        self,
        result: ClientInstructionTypedParseResult | None,
    ) -> None:
        """Store one content-bearing typed parse result without serialization."""

        self._client_instruction_typed_parse_result = result

    @property
    def client_instruction_typed_parse_result(
        self,
    ) -> ClientInstructionTypedParseResult | None:
        """Return request-local private typed parse state without copying it."""

        return self._client_instruction_typed_parse_result

    def set_client_instruction_cache_write_result(
        self,
        result: ClientInstructionCacheWriteResult | None,
    ) -> None:
        """Store one content-bearing cache writer result without serialization."""

        self._client_instruction_cache_write_result = result

    @property
    def client_instruction_cache_write_result(
        self,
    ) -> ClientInstructionCacheWriteResult | None:
        """Return request-local private cache writer state without copying it."""

        return self._client_instruction_cache_write_result

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

    def set_client_history_exclusion_apply_result(
        self,
        result: (
            ClientHistoryExclusionApplyResult
            | ClientHistoryExclusionApplyV1Result
            | None
        ),
    ) -> None:
        """Store one content-bearing apply result without serialization."""

        self._client_history_exclusion_apply_result = result

    @property
    def client_history_exclusion_apply_result(
        self,
    ) -> ClientHistoryExclusionApplyResult | ClientHistoryExclusionApplyV1Result | None:
        """Return request-local private apply state without copying it."""

        return self._client_history_exclusion_apply_result

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


def _sanitized_relevant_request_headers(
    headers: Mapping[str, str] | None,
) -> dict[str, str]:
    if not isinstance(headers, Mapping):
        return {}
    retained: dict[str, str] = {}
    for raw_key in headers:
        if not isinstance(raw_key, str):
            continue
        key = raw_key.strip().lower()
        if key in _E1R1_RELEVANT_REQUEST_HEADERS:
            retained[key] = "present"
    return retained
