"""RelayCTX TTS adapter handoff contract helper.

Phase 5.5-C1 converts Phase 5.5-C0 content-free segmentation hints into a
runtime-private adapter handoff plan. It does not execute TTS, generate audio,
control avatars, persist visible text, or wire into request-runtime SSE.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relayctx_tts_segmentation import (
    RelayCTXTTSBoundaryKind,
    RelayCTXTTSHint,
    RelayCTXTTSHintResult,
)

RelayCTXTTSAdapterHandoffStatus = Literal[
    "disabled",
    "dry_run_ready",
    "ready",
    "empty_input",
    "blocked",
    "invalid_input",
]


@dataclass(frozen=True)
class RelayCTXTTSAdapterHandoffItem:
    """Runtime-private content-free adapter handoff item.

    The item contains offsets and counts only. It deliberately does not contain
    visible text, audio bytes, avatar commands, or adapter transport payloads.
    """

    sequence_index: int
    start_char: int
    end_char: int
    char_count: int
    boundary_kind: RelayCTXTTSBoundaryKind
    recommended_flush: bool
    reason_ids: tuple[str, ...]

    @property
    def content_free(self) -> bool:
        return True

    def to_runtime_dict(self) -> dict[str, object]:
        """Return the runtime-private handoff envelope item."""

        return {
            "sequence_index": self.sequence_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "char_count": self.char_count,
            "boundary_kind": self.boundary_kind,
            "recommended_flush": self.recommended_flush,
            "reason_ids": list(self.reason_ids),
            "content_free": True,
        }


@dataclass(frozen=True)
class RelayCTXTTSAdapterHandoffPlan:
    """Runtime-private TTS adapter handoff plan.

    `handoff_items` may be used only by future in-process adapter wiring. The
    diagnostics projection intentionally omits the array so logs remain
    content-free and small.
    """

    status: RelayCTXTTSAdapterHandoffStatus
    handoff_items: tuple[RelayCTXTTSAdapterHandoffItem, ...]
    enabled: bool
    dry_run_only: bool
    source_hint_status: str | None
    source_hint_candidate_count: int
    source_hint_emitted_count: int
    handoff_candidate_count: int
    emitted_handoff_count: int
    tts_execution_requested: bool
    audio_generation_requested: bool
    avatar_control_requested: bool
    persistence_allowed: bool
    blocked_reasons: tuple[str, ...]

    @property
    def content_free(self) -> bool:
        return True

    @property
    def handoff_emitted(self) -> bool:
        return self.emitted_handoff_count > 0

    def to_log_dict(self) -> dict[str, object]:
        """Return content-free diagnostics; handoff items are omitted."""

        return {
            "schema_version": "relayctx_tts_adapter_handoff.v0",
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "source_hint_status": self.source_hint_status,
            "source_hint_candidate_count": self.source_hint_candidate_count,
            "source_hint_emitted_count": self.source_hint_emitted_count,
            "handoff_candidate_count": self.handoff_candidate_count,
            "emitted_handoff_count": self.emitted_handoff_count,
            "handoff_emitted": self.handoff_emitted,
            "tts_execution_requested": False,
            "audio_generation_requested": False,
            "avatar_control_requested": False,
            "persistence_allowed": False,
            "blocked_reasons": list(self.blocked_reasons),
            "content_free": True,
            "visible_text_omitted": True,
            "hint_array_omitted": True,
            "handoff_items_omitted": True,
            "runtime_private": True,
        }


def build_tts_adapter_handoff_plan(
    hint_result: object,
    *,
    enabled: bool,
    dry_run_only: bool = True,
) -> RelayCTXTTSAdapterHandoffPlan:
    """Build a runtime-private adapter handoff plan from C0 hint results."""

    if not isinstance(hint_result, RelayCTXTTSHintResult):
        return RelayCTXTTSAdapterHandoffPlan(
            status="invalid_input",
            handoff_items=(),
            enabled=enabled,
            dry_run_only=dry_run_only,
            source_hint_status=None,
            source_hint_candidate_count=0,
            source_hint_emitted_count=0,
            handoff_candidate_count=0,
            emitted_handoff_count=0,
            tts_execution_requested=False,
            audio_generation_requested=False,
            avatar_control_requested=False,
            persistence_allowed=False,
            blocked_reasons=("invalid_hint_result",),
        )

    source_status = hint_result.status
    source_candidate_count = hint_result.candidate_hint_count
    source_emitted_count = hint_result.emitted_hint_count

    if not enabled:
        return _build_plan(
            status="disabled",
            enabled=False,
            dry_run_only=dry_run_only,
            hint_result=hint_result,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=(),
        )
    if source_status == "invalid_input":
        return _build_plan(
            status="invalid_input",
            enabled=True,
            dry_run_only=dry_run_only,
            hint_result=hint_result,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=_dedupe((*hint_result.blocked_reasons, "source_invalid_input")),
        )
    if source_status == "blocked":
        return _build_plan(
            status="blocked",
            enabled=True,
            dry_run_only=dry_run_only,
            hint_result=hint_result,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=_dedupe((*hint_result.blocked_reasons, "source_blocked")),
        )
    if source_status == "disabled":
        return _build_plan(
            status="blocked",
            enabled=True,
            dry_run_only=dry_run_only,
            hint_result=hint_result,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=("source_hints_disabled",),
        )
    if source_status == "empty_input":
        return _build_plan(
            status="empty_input",
            enabled=True,
            dry_run_only=dry_run_only,
            hint_result=hint_result,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=(),
        )
    if source_status == "dry_run_ready":
        return RelayCTXTTSAdapterHandoffPlan(
            status="dry_run_ready",
            handoff_items=(),
            enabled=True,
            dry_run_only=True,
            source_hint_status=source_status,
            source_hint_candidate_count=source_candidate_count,
            source_hint_emitted_count=source_emitted_count,
            handoff_candidate_count=source_candidate_count,
            emitted_handoff_count=0,
            tts_execution_requested=False,
            audio_generation_requested=False,
            avatar_control_requested=False,
            persistence_allowed=False,
            blocked_reasons=(),
        )
    if source_status != "ready":
        return _build_plan(
            status="invalid_input",
            enabled=True,
            dry_run_only=dry_run_only,
            hint_result=hint_result,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=("unknown_source_hint_status",),
        )

    candidate_items = _handoff_items_from_hints(hint_result.hints)
    if not candidate_items:
        return _build_plan(
            status="empty_input",
            enabled=True,
            dry_run_only=dry_run_only,
            hint_result=hint_result,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=(),
        )
    if dry_run_only:
        return _build_plan(
            status="dry_run_ready",
            enabled=True,
            dry_run_only=True,
            hint_result=hint_result,
            candidate_items=candidate_items,
            emitted_items=(),
            blocked_reasons=(),
        )
    return _build_plan(
        status="ready",
        enabled=True,
        dry_run_only=False,
        hint_result=hint_result,
        candidate_items=candidate_items,
        emitted_items=candidate_items,
        blocked_reasons=(),
    )


def build_relayctx_tts_adapter_handoff_node_result(
    plan: RelayCTXTTSAdapterHandoffPlan,
) -> PipelineNodeResult:
    """Build a content-free node result for adapter handoff planning."""

    status = "diagnostic_only"
    if plan.status == "invalid_input":
        status = "failed"
    elif plan.status == "blocked":
        status = "blocked"
    elif plan.status == "ready":
        status = "applied"
    return build_pipeline_node_result(
        node_name="relayctx_tts_adapter_handoff",
        status=status,
        decision=plan.status,
        blocked_reasons=plan.blocked_reasons,
        diagnostics=plan.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relayctx_tts_adapter_handoff",
                "schema_version": "relayctx_tts_adapter_handoff.v0",
                "present": True,
                "content_free": True,
                "runtime_private": True,
                "visible_text_omitted": True,
                "hint_array_omitted": True,
                "handoff_items_omitted": True,
                "tts_execution_requested": False,
                "audio_generation_requested": False,
                "avatar_control_requested": False,
                "persistence_allowed": False,
            }
        ],
    )


def _build_plan(
    *,
    status: RelayCTXTTSAdapterHandoffStatus,
    enabled: bool,
    dry_run_only: bool,
    hint_result: RelayCTXTTSHintResult,
    candidate_items: tuple[RelayCTXTTSAdapterHandoffItem, ...],
    emitted_items: tuple[RelayCTXTTSAdapterHandoffItem, ...],
    blocked_reasons: tuple[str, ...],
) -> RelayCTXTTSAdapterHandoffPlan:
    return RelayCTXTTSAdapterHandoffPlan(
        status=status,
        handoff_items=emitted_items,
        enabled=enabled,
        dry_run_only=dry_run_only,
        source_hint_status=hint_result.status,
        source_hint_candidate_count=hint_result.candidate_hint_count,
        source_hint_emitted_count=hint_result.emitted_hint_count,
        handoff_candidate_count=len(candidate_items),
        emitted_handoff_count=len(emitted_items),
        tts_execution_requested=False,
        audio_generation_requested=False,
        avatar_control_requested=False,
        persistence_allowed=False,
        blocked_reasons=blocked_reasons,
    )


def _handoff_items_from_hints(
    hints: Iterable[RelayCTXTTSHint],
) -> tuple[RelayCTXTTSAdapterHandoffItem, ...]:
    return tuple(
        RelayCTXTTSAdapterHandoffItem(
            sequence_index=index,
            start_char=hint.start_char,
            end_char=hint.end_char,
            char_count=hint.char_count,
            boundary_kind=hint.boundary_kind,
            recommended_flush=hint.recommended_flush,
            reason_ids=tuple(hint.reason_ids),
        )
        for index, hint in enumerate(hints)
    )


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)
