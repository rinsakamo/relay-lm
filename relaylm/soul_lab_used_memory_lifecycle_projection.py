"""Versioned read-only lifecycle overlay for historical used-memory evidence."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .soul_lab_observation_projection import LabObservationScope
from .soul_lab_observation_store import bounded_text, normalize_reason_ids
from .soul_lab_read_context import build_lab_read_context


class _ExactModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LabUsedMemoryLifecycleItem(_ExactModel):
    memory_id: str
    injected_summary: str = Field(max_length=512)
    current_summary: str | None = Field(default=None, max_length=512)
    current_lifecycle_state: Literal["active", "hidden", "unknown"]
    representation_changed: bool
    lifecycle_changed: bool
    source_kind: str


class LabMemoryUsedLifecycleProjection(_ExactModel):
    schema_: Literal["relaylm.lab.memory_used_lifecycle.v1"] = Field(
        default="relaylm.lab.memory_used_lifecycle.v1",
        alias="schema",
    )
    source: Literal["relaylm_runtime"] = "relaylm_runtime"
    read_only: Literal[True] = True
    availability: Literal["available", "empty", "unavailable"]
    capability: Literal[
        "backend_bound_memory_evidence_with_current_lifecycle"
    ] = "backend_bound_memory_evidence_with_current_lifecycle"
    character_id: str
    namespace: str
    run_id: str | None
    retrieval_attempted: bool
    candidate_discovered: bool
    selected: bool
    relayctx_injection_performed: bool
    backend_bound_included: bool
    response_generation_completed: bool
    items: list[LabUsedMemoryLifecycleItem] = Field(max_length=16)
    bounded_reason_ids: list[str] = Field(max_length=32)


def build_lab_memory_used_lifecycle_projection(
    scope: LabObservationScope,
) -> LabMemoryUsedLifecycleProjection:
    """Overlay current lifecycle without changing the durable historical receipt."""

    context = build_lab_read_context(scope)
    if context.availability == "unavailable":
        return _empty(
            scope,
            availability="unavailable",
            run_id=None,
            reasons=list(context.unavailable_reasons),
        )
    if context.latest_run is None:
        return _empty(
            scope,
            availability="empty",
            run_id=None,
            reasons=normalize_reason_ids(context.run_reasons),
        )

    run_id = str(context.latest_run["run_id"])
    receipt = context.latest_used_receipt
    if receipt is None:
        return _empty(
            scope,
            availability="empty",
            run_id=run_id,
            response_completed=context.response_generation_completed,
            reasons=normalize_reason_ids([*context.run_reasons, *context.used_reasons]),
        )

    items: list[LabUsedMemoryLifecycleItem] = []
    overlay_reasons: list[str] = []
    for raw in list(receipt.get("items", []))[:16]:
        memory_id = str(raw["memory_id"])
        injected = bounded_text(raw.get("injected_summary"), maximum=512)
        current_summary, lifecycle, reason = context.current_overlay(memory_id)
        if reason is not None:
            overlay_reasons.append(reason)
        items.append(
            LabUsedMemoryLifecycleItem(
                memory_id=memory_id,
                injected_summary=injected,
                current_summary=current_summary,
                current_lifecycle_state=lifecycle,
                representation_changed=(
                    current_summary is not None and current_summary != injected
                ),
                lifecycle_changed=lifecycle == "hidden",
                source_kind=str(raw.get("source_kind", "primary")),
            )
        )
    reasons = normalize_reason_ids(
        [
            *context.run_reasons,
            *context.used_reasons,
            *overlay_reasons,
            *receipt.get("reason_ids", []),
        ]
    )
    return LabMemoryUsedLifecycleProjection(
        availability="available" if items else "empty",
        character_id=scope.character_id,
        namespace=scope.namespace,
        run_id=run_id,
        retrieval_attempted=bool(receipt["retrieval_attempted"]),
        candidate_discovered=bool(receipt["candidate_discovered"]),
        selected=bool(receipt["selected"]),
        relayctx_injection_performed=bool(
            receipt["relayctx_injection_performed"]
        ),
        backend_bound_included=bool(receipt["backend_bound_included"]),
        response_generation_completed=context.response_generation_completed,
        items=items,
        bounded_reason_ids=reasons,
    )


def _empty(
    scope: LabObservationScope,
    *,
    availability: Literal["empty", "unavailable"],
    run_id: str | None,
    reasons: list[str],
    response_completed: bool = False,
) -> LabMemoryUsedLifecycleProjection:
    return LabMemoryUsedLifecycleProjection(
        availability=availability,
        character_id=scope.character_id,
        namespace=scope.namespace,
        run_id=run_id,
        retrieval_attempted=False,
        candidate_discovered=False,
        selected=False,
        relayctx_injection_performed=False,
        backend_bound_included=False,
        response_generation_completed=response_completed,
        items=[],
        bounded_reason_ids=normalize_reason_ids(reasons),
    )


__all__ = [
    "LabMemoryUsedLifecycleProjection",
    "LabUsedMemoryLifecycleItem",
    "build_lab_memory_used_lifecycle_projection",
]
