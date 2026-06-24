"""Pure, bounded SOUL Lab observation projections."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import RelayLMConfig
from .relaymem_primary_recall import (
    _load_control_state,
    _load_validated_page,
    resolve_relaymem_character_store_root,
)
from .soul_lab_observation_store import (
    bounded_text,
    normalize_reason_ids,
    read_outcome_receipts,
    read_outcome_receipts_for_run,
    read_run_receipts,
    read_used_receipt_for_run,
    read_used_receipts,
    stable_correlation,
)

SourceMarker = Literal["relaylm_runtime"]
Availability = Literal["available", "empty", "unavailable"]


class _ExactModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LabRecentMemoryItem(_ExactModel):
    memory_id: str
    layer: Literal["primary"] = "primary"
    status: Literal["formed"] = "formed"
    title: str = Field(max_length=160)
    bounded_summary: str = Field(max_length=512)
    confidence_label: Literal["not_recorded"] = "not_recorded"
    scope_label: Literal["character_namespace"] = "character_namespace"
    formed_at: str | None = None
    pinned: bool | None = None
    source_kind: str


class LabMemoryOutcomeItem(_ExactModel):
    outcome_id: str
    run_id: str
    status: Literal["held", "blocked"]
    title: str = Field(max_length=160)
    bounded_summary: str = Field(max_length=512)
    observed_at: str
    reason_ids: list[str] = Field(max_length=32)


class LabUsedMemoryItem(_ExactModel):
    memory_id: str
    injected_summary: str = Field(max_length=512)
    current_summary: str | None = Field(default=None, max_length=512)
    representation_changed: bool
    source_kind: str


class LabLastRunProjection(_ExactModel):
    schema: Literal["relaylm.lab.last_run.v0"] = "relaylm.lab.last_run.v0"
    source: SourceMarker = "relaylm_runtime"
    read_only: Literal[True] = True
    availability: Availability
    capability: Literal["latest_completed_managed_run"] = "latest_completed_managed_run"
    character_id: str
    namespace: str
    run_id: str | None
    status: Literal["completed", "failed", "empty", "unavailable"]
    started_at: str | None
    completed_at: str | None
    duration_ms: int | None
    response_mode: Literal["stream", "non_stream", "unknown"]
    slp_status: str
    memory_outcome_status: Literal["formed", "held", "blocked", "mixed", "none", "unavailable"]
    relayrun_status: str
    relayctx_repack_status: str
    relayctx_unpack_status: str
    formed_count: int = Field(ge=0)
    held_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    used_memory_count: int = Field(ge=0)
    recovery_required: bool
    bounded_reason_ids: list[str] = Field(max_length=32)


class LabRecentMemoryProjection(_ExactModel):
    schema: Literal["relaylm.lab.memory_recent.v0"] = "relaylm.lab.memory_recent.v0"
    source: SourceMarker = "relaylm_runtime"
    read_only: Literal[True] = True
    availability: Availability
    capability: Literal["validated_primary_memory_read"] = "validated_primary_memory_read"
    character_id: str
    namespace: str
    limit: int = Field(ge=1, le=50)
    next_cursor: str | None = None
    items: list[LabRecentMemoryItem] = Field(max_length=50)
    bounded_reason_ids: list[str] = Field(max_length=32)


class LabMemoryHeldProjection(_ExactModel):
    schema: Literal["relaylm.lab.memory_held.v0"] = "relaylm.lab.memory_held.v0"
    source: SourceMarker = "relaylm_runtime"
    read_only: Literal[True] = True
    availability: Availability
    capability: Literal["durable_memory_outcome_read"] = "durable_memory_outcome_read"
    character_id: str
    namespace: str
    limit: int = Field(ge=1, le=50)
    next_cursor: str | None = None
    items: list[LabMemoryOutcomeItem] = Field(max_length=50)
    bounded_reason_ids: list[str] = Field(max_length=32)


class LabMemoryUsedProjection(_ExactModel):
    schema: Literal["relaylm.lab.memory_used.v0"] = "relaylm.lab.memory_used.v0"
    source: SourceMarker = "relaylm_runtime"
    read_only: Literal[True] = True
    availability: Availability
    capability: Literal["backend_bound_memory_evidence_read"] = "backend_bound_memory_evidence_read"
    character_id: str
    namespace: str
    run_id: str | None
    retrieval_attempted: bool
    candidate_discovered: bool
    selected: bool
    relayctx_injection_performed: bool
    backend_bound_included: bool
    response_generation_completed: bool
    items: list[LabUsedMemoryItem] = Field(max_length=16)
    bounded_reason_ids: list[str] = Field(max_length=32)


@dataclass(frozen=True)
class LabObservationScope:
    known: bool
    available: bool
    character_id: str
    namespace: str
    store_root: str | None
    reason_ids: tuple[str, ...]


def resolve_lab_observation_scope(config: RelayLMConfig, *, character_id: str, namespace: str) -> LabObservationScope:
    route_pairs = {
        (route.character_id, route.memory_namespace)
        for route in config.model_routes.values()
        if route.character_id is not None and route.memory_namespace is not None
    }
    known_character = character_id in config.characters or any(pair[0] == character_id for pair in route_pairs)
    if not known_character:
        return LabObservationScope(False, False, character_id, namespace, None, ("character_unknown",))
    if (character_id, namespace) not in route_pairs:
        return LabObservationScope(True, False, character_id, namespace, None, ("namespace_not_mapped",))
    configured_root = config.memory.root_path
    if not isinstance(configured_root, str) or not configured_root:
        return LabObservationScope(True, False, character_id, namespace, None, ("memory_store_unconfigured",))
    partition = Path(configured_root) / "characters"
    if not (partition.exists() or partition.is_symlink()):
        return LabObservationScope(True, False, character_id, namespace, None, ("character_partition_unavailable",))
    scoped = resolve_relaymem_character_store_root(configured_root, character_id)
    if not isinstance(scoped, str) or not Path(scoped).is_dir():
        return LabObservationScope(True, False, character_id, namespace, None, ("character_store_unavailable",))
    return LabObservationScope(True, True, character_id, namespace, scoped, ())


def _run_order_key(item: dict[str, object]) -> tuple[datetime, str]:
    completed = datetime.fromisoformat(str(item["completed_at"]).replace("Z", "+00:00"))
    return completed.astimezone(timezone.utc), str(item["run_id"])


def build_lab_last_run_projection(scope: LabObservationScope) -> LabLastRunProjection:
    if not scope.available or scope.store_root is None:
        return LabLastRunProjection(
            availability="unavailable", character_id=scope.character_id, namespace=scope.namespace,
            run_id=None, status="unavailable", started_at=None, completed_at=None,
            duration_ms=None, response_mode="unknown", slp_status="unavailable",
            memory_outcome_status="unavailable", relayrun_status="unavailable",
            relayctx_repack_status="unavailable", relayctx_unpack_status="unavailable",
            formed_count=0, held_count=0, blocked_count=0, used_memory_count=0,
            recovery_required=False, bounded_reason_ids=list(scope.reason_ids),
        )
    runs, run_reasons = read_run_receipts(scope.store_root)
    runs = [item for item in runs if item.get("character_id") == scope.character_id and item.get("namespace") == scope.namespace]
    if not runs:
        return LabLastRunProjection(
            availability="empty", character_id=scope.character_id, namespace=scope.namespace,
            run_id=None, status="empty", started_at=None, completed_at=None, duration_ms=None,
            response_mode="unknown", slp_status="unavailable", memory_outcome_status="none",
            relayrun_status="unavailable", relayctx_repack_status="unavailable",
            relayctx_unpack_status="unavailable", formed_count=0, held_count=0,
            blocked_count=0, used_memory_count=0, recovery_required=False,
            bounded_reason_ids=normalize_reason_ids(run_reasons),
        )
    latest = max(runs, key=_run_order_key)
    run_id = str(latest["run_id"])
    outcomes, outcome_reasons = read_outcome_receipts_for_run(scope.store_root, run_id)
    matched_outcomes = [item for item in outcomes if item.get("namespace") == scope.namespace]
    counts = {state: sum(item.get("outcome_status") == state for item in matched_outcomes) for state in ("formed", "held", "blocked")}
    used_match, used_reasons = read_used_receipt_for_run(scope.store_root, run_id)
    if used_match is not None and (
        used_match.get("character_id") != scope.character_id
        or used_match.get("namespace") != scope.namespace
    ):
        used_match = None
        used_reasons = normalize_reason_ids([*used_reasons, "observation_receipt_scope_mismatch"])
    nonzero = [state for state, count in counts.items() if count]
    outcome_status = nonzero[0] if len(nonzero) == 1 else "mixed" if nonzero else "none"
    slp_status = str(latest["slp_status"])
    if counts["blocked"]:
        slp_status = "terminal_failed"
    elif counts["held"]:
        slp_status = "held"
    elif counts["formed"]:
        slp_status = "terminal_succeeded"
    reasons = normalize_reason_ids([
        *run_reasons, *outcome_reasons, *used_reasons, *latest.get("reason_ids", []),
        *(reason for item in matched_outcomes for reason in item.get("reason_ids", [])),
    ])
    return LabLastRunProjection(
        availability="available", character_id=scope.character_id, namespace=scope.namespace,
        run_id=run_id, status="completed" if latest["relayrun_status"] == "completed" else "failed",
        started_at=str(latest["started_at"]), completed_at=str(latest["completed_at"]),
        duration_ms=int(latest["duration_ms"]), response_mode=latest["response_mode"],
        slp_status=slp_status, memory_outcome_status=outcome_status,
        relayrun_status=str(latest["relayrun_status"]),
        relayctx_repack_status=str(latest["relayctx_repack_status"]),
        relayctx_unpack_status=str(latest["relayctx_unpack_status"]),
        formed_count=counts["formed"], held_count=counts["held"], blocked_count=counts["blocked"],
        used_memory_count=len(used_match.get("items", [])) if used_match else 0,
        recovery_required=bool(latest["recovery_required"]), bounded_reason_ids=reasons,
    )


def build_lab_recent_memory_projection(scope: LabObservationScope, *, limit: int) -> LabRecentMemoryProjection:
    bounded_limit = max(1, min(int(limit), 50))
    if not scope.available or scope.store_root is None:
        return LabRecentMemoryProjection(
            availability="unavailable", character_id=scope.character_id, namespace=scope.namespace,
            limit=bounded_limit, items=[], bounded_reason_ids=list(scope.reason_ids),
        )
    root = Path(scope.store_root)
    control, reasons = _load_control_state(root)
    if control is None:
        return LabRecentMemoryProjection(
            availability="unavailable", character_id=scope.character_id, namespace=scope.namespace,
            limit=bounded_limit, items=[], bounded_reason_ids=normalize_reason_ids(reasons),
        )
    items: list[LabRecentMemoryItem] = []
    seen: set[str] = set()
    projection_reasons: list[str] = list(reasons)
    for entry in reversed(control["log"]):
        if entry.get("namespace") != scope.namespace:
            continue
        identity = entry.get("idempotency_key")
        if not isinstance(identity, str) or identity in seen:
            continue
        loaded, blocked = _load_validated_page(
            root, {"path": entry.get("page_relative_path")},
            expected_namespace=scope.namespace, control=control,
        )
        if loaded is None:
            projection_reasons.extend(blocked)
            continue
        seen.add(identity)
        summary = bounded_text(loaded.get("summary"), maximum=512)
        items.append(LabRecentMemoryItem(
            memory_id=identity, title="",
            bounded_summary=summary, source_kind=str(loaded.get("memory_kind", "primary")),
        ))
        if len(items) >= bounded_limit:
            break
    return LabRecentMemoryProjection(
        availability="available" if items else "empty", character_id=scope.character_id,
        namespace=scope.namespace, limit=bounded_limit, items=items,
        bounded_reason_ids=normalize_reason_ids(projection_reasons),
    )


def build_lab_memory_held_projection(scope: LabObservationScope, *, limit: int) -> LabMemoryHeldProjection:
    bounded_limit = max(1, min(int(limit), 50))
    if not scope.available or scope.store_root is None:
        return LabMemoryHeldProjection(
            availability="unavailable", character_id=scope.character_id, namespace=scope.namespace,
            limit=bounded_limit, items=[], bounded_reason_ids=list(scope.reason_ids),
        )
    receipts, reasons = read_outcome_receipts(scope.store_root)
    selected = [item for item in receipts if item.get("namespace") == scope.namespace and item.get("outcome_status") in {"held", "blocked"}]
    selected.sort(key=lambda item: (str(item.get("observed_at", "")), str(item.get("run_id", "")), str(item.get("job_correlation_id", ""))), reverse=True)
    items = [LabMemoryOutcomeItem(
        outcome_id=stable_correlation(f"{item['run_id']}:{item['job_correlation_id']}"),
        run_id=str(item["run_id"]), status=item["outcome_status"],
        title=bounded_text(item.get("title"), maximum=160),
        bounded_summary=bounded_text(item.get("bounded_summary"), maximum=512),
        observed_at=str(item["observed_at"]),
        reason_ids=normalize_reason_ids(item.get("reason_ids", [])),
    ) for item in selected[:bounded_limit]]
    return LabMemoryHeldProjection(
        availability="available" if items else "empty", character_id=scope.character_id,
        namespace=scope.namespace, limit=bounded_limit, items=items,
        bounded_reason_ids=normalize_reason_ids(reasons),
    )


def build_lab_memory_used_projection(scope: LabObservationScope) -> LabMemoryUsedProjection:
    if not scope.available or scope.store_root is None:
        return LabMemoryUsedProjection(
            availability="unavailable", character_id=scope.character_id, namespace=scope.namespace,
            run_id=None, retrieval_attempted=False, candidate_discovered=False, selected=False,
            relayctx_injection_performed=False, backend_bound_included=False,
            response_generation_completed=False, items=[], bounded_reason_ids=list(scope.reason_ids),
        )
    runs, run_reasons = read_run_receipts(scope.store_root)
    runs = [item for item in runs if item.get("character_id") == scope.character_id and item.get("namespace") == scope.namespace]
    if not runs:
        return LabMemoryUsedProjection(
            availability="empty", character_id=scope.character_id, namespace=scope.namespace,
            run_id=None, retrieval_attempted=False, candidate_discovered=False, selected=False,
            relayctx_injection_performed=False, backend_bound_included=False,
            response_generation_completed=False, items=[], bounded_reason_ids=normalize_reason_ids(run_reasons),
        )
    latest = max(runs, key=_run_order_key)
    run_id = str(latest["run_id"])
    receipt, used_reasons = read_used_receipt_for_run(scope.store_root, run_id)
    if receipt is not None and (
        receipt.get("character_id") != scope.character_id
        or receipt.get("namespace") != scope.namespace
    ):
        receipt = None
        used_reasons = normalize_reason_ids([*used_reasons, "observation_receipt_scope_mismatch"])
    if receipt is None:
        return LabMemoryUsedProjection(
            availability="empty", character_id=scope.character_id, namespace=scope.namespace,
            run_id=run_id, retrieval_attempted=False, candidate_discovered=False, selected=False,
            relayctx_injection_performed=False, backend_bound_included=False,
            response_generation_completed=latest["relayrun_status"] == "completed", items=[],
            bounded_reason_ids=normalize_reason_ids([*run_reasons, *used_reasons]),
        )
    current, current_reasons = _current_summaries(scope.store_root, scope.namespace)
    items: list[LabUsedMemoryItem] = []
    for item in receipt.get("items", []):
        memory_id = str(item["memory_id"])
        injected = bounded_text(item.get("injected_summary"), maximum=512)
        current_summary = current.get(memory_id)
        items.append(LabUsedMemoryItem(
            memory_id=memory_id, injected_summary=injected, current_summary=current_summary,
            representation_changed=current_summary is not None and current_summary != injected,
            source_kind=str(item.get("source_kind", "primary")),
        ))
    reasons = normalize_reason_ids([*run_reasons, *used_reasons, *current_reasons, *receipt.get("reason_ids", [])])
    return LabMemoryUsedProjection(
        availability="available" if items else "empty", character_id=scope.character_id,
        namespace=scope.namespace, run_id=run_id,
        retrieval_attempted=bool(receipt["retrieval_attempted"]),
        candidate_discovered=bool(receipt["candidate_discovered"]), selected=bool(receipt["selected"]),
        relayctx_injection_performed=bool(receipt["relayctx_injection_performed"]),
        backend_bound_included=bool(receipt["backend_bound_included"]),
        response_generation_completed=latest["relayrun_status"] == "completed", items=items, bounded_reason_ids=reasons,
    )


def _current_summaries(store_root: str, namespace: str) -> tuple[dict[str, str], list[str]]:
    root = Path(store_root)
    control, reasons = _load_control_state(root)
    if control is None:
        return {}, reasons
    summaries: dict[str, str] = {}
    output_reasons = list(reasons)
    for entry in control["index"]:
        if entry.get("namespace") != namespace:
            continue
        identity = entry.get("idempotency_key")
        if not isinstance(identity, str):
            continue
        loaded, blocked = _load_validated_page(
            root, {"path": entry.get("page_relative_path")},
            expected_namespace=namespace, control=control,
        )
        if loaded is None:
            output_reasons.extend(blocked)
            continue
        summaries[identity] = bounded_text(loaded.get("summary"), maximum=512)
    return summaries, normalize_reason_ids(output_reasons)


__all__ = [
    "LabLastRunProjection", "LabMemoryHeldProjection", "LabMemoryUsedProjection",
    "LabObservationScope", "LabRecentMemoryProjection", "build_lab_last_run_projection",
    "build_lab_memory_held_projection", "build_lab_memory_used_projection",
    "build_lab_recent_memory_projection", "resolve_lab_observation_scope",
]
