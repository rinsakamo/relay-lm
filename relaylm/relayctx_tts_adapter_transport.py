"""RelayCTX TTS adapter-facing transport contract helper.

Phase 5.5-C3 converts Phase 5.5-C1 runtime-private handoff metadata into
an adapter-facing transport envelope. It does not execute TTS, send transport
I/O, generate audio, control avatars, persist visible text, or wire into the
request-runtime stream path.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relayctx_tts_adapter_handoff import (
    RelayCTXTTSAdapterHandoffItem,
    RelayCTXTTSAdapterHandoffPlan,
)
from relaylm.relayctx_tts_segmentation import RelayCTXTTSBoundaryKind

RelayCTXTTSAdapterTransportStatus = Literal[
    "disabled",
    "dry_run_ready",
    "ready",
    "empty_input",
    "blocked",
    "invalid_input",
]


@dataclass(frozen=True)
class RelayCTXTTSAdapterTransportItem:
    """Runtime-private content-free adapter transport item.

    The item is intentionally offset/count based. It does not include visible
    text, audio bytes, avatar commands, endpoint URLs, or delivery credentials.
    A future external adapter layer may use the offsets against its own
    runtime-private safe-visible buffer; RelayLM core does not dereference or
    deliver that content here.
    """

    transport_sequence_index: int
    handoff_sequence_index: int
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
        """Return the runtime-private transport-envelope item."""

        return {
            "transport_sequence_index": self.transport_sequence_index,
            "handoff_sequence_index": self.handoff_sequence_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "char_count": self.char_count,
            "boundary_kind": self.boundary_kind,
            "recommended_flush": self.recommended_flush,
            "reason_ids": list(self.reason_ids),
            "content_free": True,
        }


@dataclass(frozen=True)
class RelayCTXTTSAdapterTransportEnvelope:
    """Runtime-private adapter-facing TTS transport envelope.

    `transport_items` may be consumed only by a later external adapter bridge.
    The diagnostics projection intentionally omits the item array so persisted
    logs remain content-free and small.
    """

    status: RelayCTXTTSAdapterTransportStatus
    transport_items: tuple[RelayCTXTTSAdapterTransportItem, ...]
    enabled: bool
    dry_run_only: bool
    source_handoff_status: str | None
    source_handoff_candidate_count: int
    source_handoff_emitted_count: int
    transport_candidate_count: int
    emitted_transport_count: int
    transport_delivery_requested: bool
    tts_execution_requested: bool
    audio_generation_requested: bool
    avatar_control_requested: bool
    persistence_allowed: bool
    blocked_reasons: tuple[str, ...]

    @property
    def content_free(self) -> bool:
        return True

    @property
    def transport_emitted(self) -> bool:
        return self.emitted_transport_count > 0

    def to_log_dict(self) -> dict[str, object]:
        """Return content-free diagnostics; transport items are omitted."""

        return {
            "schema_version": "relayctx_tts_adapter_transport.v0",
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "source_handoff_status": self.source_handoff_status,
            "source_handoff_candidate_count": self.source_handoff_candidate_count,
            "source_handoff_emitted_count": self.source_handoff_emitted_count,
            "transport_candidate_count": self.transport_candidate_count,
            "emitted_transport_count": self.emitted_transport_count,
            "transport_emitted": self.transport_emitted,
            "transport_delivery_requested": False,
            "tts_execution_requested": False,
            "audio_generation_requested": False,
            "avatar_control_requested": False,
            "persistence_allowed": False,
            "blocked_reasons": list(self.blocked_reasons),
            "content_free": True,
            "visible_text_omitted": True,
            "handoff_items_omitted": True,
            "transport_items_omitted": True,
            "runtime_private": True,
            "external_io_performed": False,
        }


def build_tts_adapter_transport_envelope(
    handoff_plan: object,
    *,
    enabled: bool,
    dry_run_only: bool = True,
) -> RelayCTXTTSAdapterTransportEnvelope:
    """Build a runtime-private adapter-facing transport envelope.

    This helper defines the transport contract only. It never performs network,
    filesystem, TTS, audio, avatar, or persistence side effects.
    """

    if not isinstance(handoff_plan, RelayCTXTTSAdapterHandoffPlan):
        return RelayCTXTTSAdapterTransportEnvelope(
            status="invalid_input",
            transport_items=(),
            enabled=enabled,
            dry_run_only=dry_run_only,
            source_handoff_status=None,
            source_handoff_candidate_count=0,
            source_handoff_emitted_count=0,
            transport_candidate_count=0,
            emitted_transport_count=0,
            transport_delivery_requested=False,
            tts_execution_requested=False,
            audio_generation_requested=False,
            avatar_control_requested=False,
            persistence_allowed=False,
            blocked_reasons=("invalid_handoff_plan",),
        )

    if not enabled:
        return _build_envelope(
            status="disabled",
            enabled=False,
            dry_run_only=dry_run_only,
            handoff_plan=handoff_plan,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=(),
        )
    if handoff_plan.status == "invalid_input":
        return _build_envelope(
            status="invalid_input",
            enabled=True,
            dry_run_only=dry_run_only,
            handoff_plan=handoff_plan,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=_dedupe((*handoff_plan.blocked_reasons, "source_handoff_invalid_input")),
        )
    if handoff_plan.status == "blocked":
        return _build_envelope(
            status="blocked",
            enabled=True,
            dry_run_only=dry_run_only,
            handoff_plan=handoff_plan,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=_dedupe((*handoff_plan.blocked_reasons, "source_handoff_blocked")),
        )
    if handoff_plan.status == "disabled":
        return _build_envelope(
            status="blocked",
            enabled=True,
            dry_run_only=dry_run_only,
            handoff_plan=handoff_plan,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=("source_handoff_disabled",),
        )
    if handoff_plan.status == "empty_input":
        return _build_envelope(
            status="empty_input",
            enabled=True,
            dry_run_only=dry_run_only,
            handoff_plan=handoff_plan,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=(),
        )
    if handoff_plan.status == "dry_run_ready":
        return RelayCTXTTSAdapterTransportEnvelope(
            status="dry_run_ready",
            transport_items=(),
            enabled=True,
            dry_run_only=True,
            source_handoff_status=handoff_plan.status,
            source_handoff_candidate_count=handoff_plan.handoff_candidate_count,
            source_handoff_emitted_count=handoff_plan.emitted_handoff_count,
            transport_candidate_count=handoff_plan.handoff_candidate_count,
            emitted_transport_count=0,
            transport_delivery_requested=False,
            tts_execution_requested=False,
            audio_generation_requested=False,
            avatar_control_requested=False,
            persistence_allowed=False,
            blocked_reasons=(),
        )
    if handoff_plan.status != "ready":
        return _build_envelope(
            status="invalid_input",
            enabled=True,
            dry_run_only=dry_run_only,
            handoff_plan=handoff_plan,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=("unknown_source_handoff_status",),
        )

    candidate_items = _transport_items_from_handoff_items(handoff_plan.handoff_items)
    if not candidate_items:
        return _build_envelope(
            status="empty_input",
            enabled=True,
            dry_run_only=dry_run_only,
            handoff_plan=handoff_plan,
            candidate_items=(),
            emitted_items=(),
            blocked_reasons=(),
        )
    if dry_run_only:
        return _build_envelope(
            status="dry_run_ready",
            enabled=True,
            dry_run_only=True,
            handoff_plan=handoff_plan,
            candidate_items=candidate_items,
            emitted_items=(),
            blocked_reasons=(),
        )
    return _build_envelope(
        status="ready",
        enabled=True,
        dry_run_only=False,
        handoff_plan=handoff_plan,
        candidate_items=candidate_items,
        emitted_items=candidate_items,
        blocked_reasons=(),
    )


def build_relayctx_tts_adapter_transport_node_result(
    envelope: RelayCTXTTSAdapterTransportEnvelope,
) -> PipelineNodeResult:
    """Build a content-free node result for adapter transport planning."""

    status = "diagnostic_only"
    if envelope.status == "invalid_input":
        status = "failed"
    elif envelope.status == "blocked":
        status = "blocked"
    elif envelope.status == "ready":
        status = "applied"
    return build_pipeline_node_result(
        node_name="relayctx_tts_adapter_transport",
        status=status,
        decision=envelope.status,
        blocked_reasons=envelope.blocked_reasons,
        diagnostics=envelope.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relayctx_tts_adapter_transport",
                "schema_version": "relayctx_tts_adapter_transport.v0",
                "present": True,
                "content_free": True,
                "runtime_private": True,
                "visible_text_omitted": True,
                "handoff_items_omitted": True,
                "transport_items_omitted": True,
                "transport_delivery_requested": False,
                "tts_execution_requested": False,
                "audio_generation_requested": False,
                "avatar_control_requested": False,
                "persistence_allowed": False,
                "external_io_performed": False,
            }
        ],
    )


def _build_envelope(
    *,
    status: RelayCTXTTSAdapterTransportStatus,
    enabled: bool,
    dry_run_only: bool,
    handoff_plan: RelayCTXTTSAdapterHandoffPlan,
    candidate_items: tuple[RelayCTXTTSAdapterTransportItem, ...],
    emitted_items: tuple[RelayCTXTTSAdapterTransportItem, ...],
    blocked_reasons: tuple[str, ...],
) -> RelayCTXTTSAdapterTransportEnvelope:
    return RelayCTXTTSAdapterTransportEnvelope(
        status=status,
        transport_items=emitted_items,
        enabled=enabled,
        dry_run_only=dry_run_only,
        source_handoff_status=handoff_plan.status,
        source_handoff_candidate_count=handoff_plan.handoff_candidate_count,
        source_handoff_emitted_count=handoff_plan.emitted_handoff_count,
        transport_candidate_count=len(candidate_items),
        emitted_transport_count=len(emitted_items),
        transport_delivery_requested=False,
        tts_execution_requested=False,
        audio_generation_requested=False,
        avatar_control_requested=False,
        persistence_allowed=False,
        blocked_reasons=blocked_reasons,
    )


def _transport_items_from_handoff_items(
    handoff_items: Iterable[RelayCTXTTSAdapterHandoffItem],
) -> tuple[RelayCTXTTSAdapterTransportItem, ...]:
    return tuple(
        RelayCTXTTSAdapterTransportItem(
            transport_sequence_index=index,
            handoff_sequence_index=item.sequence_index,
            start_char=item.start_char,
            end_char=item.end_char,
            char_count=item.char_count,
            boundary_kind=item.boundary_kind,
            recommended_flush=item.recommended_flush,
            reason_ids=tuple(item.reason_ids),
        )
        for index, item in enumerate(handoff_items)
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
