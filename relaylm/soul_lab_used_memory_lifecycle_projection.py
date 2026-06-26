"""Versioned read-only lifecycle overlay for historical used-memory evidence."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .relaymem_primary_current_state import (
    PrimaryCurrentStateError,
    resolve_primary_current_state,
)
from .soul_lab_observation_projection import LabObservationScope, _run_order_key
from .soul_lab_observation_store import (
    bounded_text,
    normalize_reason_ids,
    read_run_receipts_for_scope,
    read_used_receipt_for_run,
)


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
    schema: Literal[
        "relaylm.lab.memory_used_lifecycle.v1"
    ] = "relaylm.lab.memory_used_lifecycle.v1"
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

    if not scope.available or scope.store_root is None:
        return _empty(
            scope,
            availability="unavailable",
            run_id=None,
            reasons=list(scope.reason_ids),
        )
    runs, run_reasons = read_run_receipts_for_scope(
        scope.store_root, scope.character_id, scope.namespace
    )
    runs = [
        item
        for item in runs
        if item.get("character_id") == scope.character_id
        and item.get("namespace") == scope.namespace
    ]
    if not runs:
        return _empty(
            scope,
            availability="empty",
            run_id=None,
            reasons=normalize_reason_ids(run_reasons),
        )
    latest = max(runs, key=_run_order_key)
    run_id = str(latest["run_id"])
    receipt, used_reasons = read_used_receipt_for_run(scope.store_root, run_id)
    if receipt is not None and (
        receipt.get("character_id") != scope.character_id
        or receipt.get("namespace") != scope.namespace
    ):
        receipt = None
        used_reasons = normalize_reason_ids(
            [*used_reasons, "observation_receipt_scope_mismatch"]
        )
    if receipt is None:
        return _empty(
            scope,
            availability="empty",
            run_id=run_id,
            response_completed=latest["relayrun_status"] == "completed",
            reasons=normalize_reason_ids([*run_reasons, *used_reasons]),
        )

    items: list[LabUsedMemoryLifecycleItem] = []
    overlay_reasons: list[str] = []
    for raw in list(receipt.get("items", []))[:16]:
        memory_id = str(raw["memory_id"])
        injected = bounded_text(raw.get("injected_summary"), maximum=512)
        current_summary, lifecycle, reason = _current_overlay(
            scope.store_root, scope.namespace, memory_id
        )
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
            *run_reasons,
            *used_reasons,
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
        response_generation_completed=latest["relayrun_status"] == "completed",
        items=items,
        bounded_reason_ids=reasons,
    )


def _current_overlay(
    store_root: str,
    namespace: str,
    memory_id: str,
) -> tuple[str | None, Literal["active", "hidden", "unknown"], str | None]:
    try:
        state = resolve_primary_current_state(
            store_root, namespace=namespace, memory_id=memory_id
        )
    except PrimaryCurrentStateError:
        return None, "unknown", "primary_current_state_unresolved"
    if state.lifecycle_state == "hidden":
        return None, "hidden", None
    if (
        state.lifecycle_state == "active"
        and state.mutation_state == "none"
        and state.retrieval_eligible is True
        and state.controls_valid is True
        and state.page_valid is True
    ):
        return bounded_text(state.summary, maximum=512), "active", None
    return None, "unknown", "primary_current_state_ineligible"


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
