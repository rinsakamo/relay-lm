"""Read-only SOUL Lab lifecycle and operation visibility projection."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import RelayLMConfig
from .relaymem_primary_current_state import (
    PrimaryCurrentStateError,
    load_primary_current_state_index,
    resolve_primary_current_state,
)
from .relaymem_primary_recall import _load_control_state
from .relaymem_slp_queue_record import (
    FILENAME_PREFIX,
    MAX_RECORD_BYTES,
    decode_canonical_record,
    validate_record_mapping,
)
from .soul_lab_observation_projection import LabObservationScope
from .soul_lab_observation_store import normalize_reason_ids

LifecycleState = Literal[
    "active", "hidden", "prepared", "recovery_required", "corrupt", "unknown"
]
Availability = Literal["available", "empty", "unavailable", "not_connected"]

_DF_COMPONENT_RE = re.compile(
    r"^(?:durable-finalization-v0-|durable-finalization-completion-v0-)"
    r"([0-9a-f]{64})(?:\.base|\.seal|\.segment-[0-9]{6}|\.segment-isolation)?\.json$"
)
_QUEUE_RE = re.compile(rf"^{re.escape(FILENAME_PREFIX)}[0-9a-f]{{64}}\.json$")
_MAX_SCAN_ENTRIES = 4096
_MAX_MEMORY_ITEMS = 20


class _ExactModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LabLifecycleMemoryItem(_ExactModel):
    memory_id: str
    current_lifecycle_state: LifecycleState
    current_revision: int | None = Field(default=None, ge=1)
    current_physical_status: Literal[
        "current", "hidden", "prepared", "recovery_required", "corrupt", "unknown"
    ]
    retrieval_eligible: bool | None
    historical_used_memory_remains_unchanged: Literal[True] = True
    bounded_reason_ids: list[str] = Field(max_length=32)


class LabDurableFinalizationVisibility(_ExactModel):
    availability: Availability
    status: Literal["pending", "complete", "isolated", "mixed", "none", "unknown", "unavailable", "not_connected"]
    pending_count: int = Field(ge=0)
    complete_count: int = Field(ge=0)
    isolated_count: int = Field(ge=0)
    content_free: Literal[True] = True
    locator_values_included: Literal[False] = False
    path_values_included: Literal[False] = False
    bounded_reason_ids: list[str] = Field(max_length=32)


class LabQueueWorkerVisibility(_ExactModel):
    availability: Availability
    status: Literal[
        "queued", "processing", "formed", "held", "blocked", "failed", "mixed", "none", "unknown", "unavailable", "not_connected"
    ]
    queued_count: int = Field(ge=0)
    processing_count: int = Field(ge=0)
    formed_count: int = Field(ge=0)
    held_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    content_free: Literal[True] = True
    queue_identifiers_included: Literal[False] = False
    claim_values_included: Literal[False] = False
    scheduler_controls_exposed: Literal[False] = False
    worker_controls_exposed: Literal[False] = False
    bounded_reason_ids: list[str] = Field(max_length=32)


class LabFreshConversationVisibility(_ExactModel):
    browser_local_session_reset_visible: Literal[True] = True
    durable_memory_store_reset: Literal[False] = False
    durable_memory_store_retained: Literal[True] = True
    active_current_memories_remain_retrieval_eligible: Literal[True] = True
    hidden_or_current_ineligible_memories_remain_excluded: Literal[True] = True
    home_transcript_is_durable_source: Literal[False] = False
    durable_transcript_persistence: Literal[False] = False


class LabLifecycleVisibilityProjection(_ExactModel):
    schema: Literal["relaylm.lab.lifecycle_visibility.v0"] = "relaylm.lab.lifecycle_visibility.v0"
    source: Literal["relaylm_runtime"] = "relaylm_runtime"
    read_only: Literal[True] = True
    availability: Availability
    capability: Literal[
        "read_only_lifecycle_and_operation_visibility"
    ] = "read_only_lifecycle_and_operation_visibility"
    character_id: str
    namespace: str
    memory_items: list[LabLifecycleMemoryItem] = Field(max_length=_MAX_MEMORY_ITEMS)
    durable_finalization: LabDurableFinalizationVisibility
    queue_worker: LabQueueWorkerVisibility
    fresh_conversation: LabFreshConversationVisibility = Field(
        default_factory=LabFreshConversationVisibility
    )
    mutation_controls_exposed: Literal[False] = False
    scheduler_controls_exposed: Literal[False] = False
    repair_controls_exposed: Literal[False] = False
    raw_content_included: Literal[False] = False
    raw_paths_included: Literal[False] = False
    raw_private_identifiers_included: Literal[False] = False
    bounded_reason_ids: list[str] = Field(max_length=32)


def build_lab_lifecycle_visibility_projection(
    scope: LabObservationScope,
    *,
    config: RelayLMConfig,
) -> LabLifecycleVisibilityProjection:
    """Build a bounded read-only UI-B1A projection without mutating runtime state."""

    memory_items, memory_availability, memory_reasons = _memory_visibility(scope)
    durable = _durable_finalization_visibility(config)
    queue = _queue_worker_visibility(config)
    all_reasons = normalize_reason_ids(
        [*scope.reason_ids, *memory_reasons, *durable.bounded_reason_ids, *queue.bounded_reason_ids]
    )
    availability: Availability
    if not scope.available:
        availability = "unavailable"
    elif memory_availability == "available" or durable.availability == "available" or queue.availability == "available":
        availability = "available"
    elif memory_availability == "empty" or durable.availability == "empty" or queue.availability == "empty":
        availability = "empty"
    elif durable.availability == "not_connected" and queue.availability == "not_connected":
        availability = "not_connected"
    else:
        availability = "unavailable"
    return LabLifecycleVisibilityProjection(
        availability=availability,
        character_id=scope.character_id,
        namespace=scope.namespace,
        memory_items=memory_items,
        durable_finalization=durable,
        queue_worker=queue,
        bounded_reason_ids=all_reasons,
    )


def _memory_visibility(
    scope: LabObservationScope,
) -> tuple[list[LabLifecycleMemoryItem], Availability, list[str]]:
    if not scope.available or scope.store_root is None:
        return [], "unavailable", list(scope.reason_ids)
    root = Path(scope.store_root)
    control, reasons = _load_control_state(root)
    if control is None:
        return [], "unavailable", normalize_reason_ids(reasons)
    try:
        state_index = load_primary_current_state_index(root, namespace=scope.namespace)
    except Exception:  # defensive: do not leak exception text through lab projection
        return [], "unavailable", ["primary_current_state_index_unavailable"]

    logical_ids: set[str] = set()
    for collection_name in ("index", "log"):
        for entry in control.get(collection_name, []):
            if entry.get("namespace") != scope.namespace:
                continue
            physical_id = entry.get("idempotency_key")
            if not _sha256_text(physical_id):
                continue
            logical = state_index.logical_by_physical.get(str(physical_id), str(physical_id))
            if _sha256_text(logical):
                logical_ids.add(str(logical))
    logical_ids.update(item for item in state_index.current_by_logical if _sha256_text(item))
    logical_ids.update(item for item in state_index.receipts_by_logical if _sha256_text(item))

    items: list[LabLifecycleMemoryItem] = []
    projection_reasons = list(reasons)
    for memory_id in sorted(logical_ids)[:_MAX_MEMORY_ITEMS]:
        try:
            state = resolve_primary_current_state(
                root, namespace=scope.namespace, memory_id=memory_id
            )
        except PrimaryCurrentStateError:
            projection_reasons.append("primary_current_state_unresolved")
            items.append(_unknown_memory(memory_id))
            continue
        lifecycle = _public_lifecycle(state.lifecycle_state, state.mutation_state)
        items.append(
            LabLifecycleMemoryItem(
                memory_id=memory_id,
                current_lifecycle_state=lifecycle,
                current_revision=state.current_revision,
                current_physical_status=_physical_status(lifecycle),
                retrieval_eligible=bool(state.retrieval_eligible),
                bounded_reason_ids=normalize_reason_ids(state.bounded_reason_ids),
            )
        )
    if len(logical_ids) > _MAX_MEMORY_ITEMS:
        projection_reasons.append("lifecycle_visibility_memory_limit_reached")
    availability: Availability = "available" if items else "empty"
    return items, availability, normalize_reason_ids(projection_reasons)


def _durable_finalization_visibility(config: RelayLMConfig) -> LabDurableFinalizationVisibility:
    root_value = config.relaymem_slp_durable_finalization_root
    if not isinstance(root_value, str) or not root_value:
        return _durable_result("not_connected", "not_connected", ("durable_finalization_root_not_configured",))
    root = Path(root_value)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        return _durable_result("unavailable", "unavailable", ("durable_finalization_root_unavailable",))
    groups: dict[str, set[str]] = {}
    reasons: list[str] = []
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name)
    except OSError:
        return _durable_result("unavailable", "unavailable", ("durable_finalization_scan_failed",))
    for index, path in enumerate(entries):
        if index >= _MAX_SCAN_ENTRIES:
            reasons.append("durable_finalization_scan_limit_reached")
            break
        if path.is_symlink() or not path.is_file():
            continue
        match = _DF_COMPONENT_RE.fullmatch(path.name)
        if match is None:
            continue
        locator = match.group(1)
        if ".segment-isolation." in path.name:
            component = "isolation"
        elif path.name.startswith("durable-finalization-completion-v0-"):
            component = "completion"
        elif path.name.endswith(".seal.json"):
            component = "seal"
        else:
            component = "other"
        groups.setdefault(locator, set()).add(component)
    pending = complete = isolated = 0
    for components in groups.values():
        if "isolation" in components:
            isolated += 1
        elif "completion" in components:
            complete += 1
        elif "seal" in components:
            pending += 1
    return LabDurableFinalizationVisibility(
        availability="available" if groups else "empty",
        status=_dominant_status({"pending": pending, "complete": complete, "isolated": isolated}),
        pending_count=pending,
        complete_count=complete,
        isolated_count=isolated,
        bounded_reason_ids=normalize_reason_ids(reasons),
    )


def _queue_worker_visibility(config: RelayLMConfig) -> LabQueueWorkerVisibility:
    root_value = config.relaymem_slp_queue_root
    if not isinstance(root_value, str) or not root_value:
        return _queue_result("not_connected", "not_connected", ("queue_root_not_configured",))
    root = Path(root_value)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        return _queue_result("unavailable", "unavailable", ("queue_root_unavailable",))
    counters = {name: 0 for name in ("queued", "processing", "formed", "held", "blocked", "failed")}
    reasons: list[str] = []
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name)
    except OSError:
        return _queue_result("unavailable", "unavailable", ("queue_scan_failed",))
    for index, path in enumerate(entries):
        if index >= _MAX_SCAN_ENTRIES:
            reasons.append("queue_scan_limit_reached")
            break
        if path.is_symlink() or not path.is_file() or _QUEUE_RE.fullmatch(path.name) is None:
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            reasons.append("queue_record_read_failed")
            continue
        if not raw or len(raw) > MAX_RECORD_BYTES:
            reasons.append("queue_record_size_invalid")
            continue
        record, reason = decode_canonical_record(raw)
        if record is None:
            reasons.append(reason or "queue_record_invalid")
            continue
        validation = validate_record_mapping(record)
        if validation:
            reasons.extend(validation)
            continue
        counters[_queue_bucket(record)] += 1
    total = sum(counters.values())
    return LabQueueWorkerVisibility(
        availability="available" if total else "empty",
        status=_dominant_status(counters),
        queued_count=counters["queued"],
        processing_count=counters["processing"],
        formed_count=counters["formed"],
        held_count=counters["held"],
        blocked_count=counters["blocked"],
        failed_count=counters["failed"],
        bounded_reason_ids=normalize_reason_ids(reasons),
    )


def _queue_bucket(record: dict[str, object]) -> str:
    state = record.get("state")
    if state == "queued":
        return "queued"
    if state == "claimed":
        return "processing"
    if state == "succeeded":
        return "formed"
    marker = f"{record.get('failure_class', '')}:{record.get('terminal_reason_id', '')}".lower()
    if "held" in marker:
        return "held"
    if "blocked" in marker or "policy" in marker:
        return "blocked"
    return "failed"


def _public_lifecycle(lifecycle_state: str, mutation_state: str) -> LifecycleState:
    if mutation_state == "corrupt":
        return "corrupt"
    if mutation_state == "recovery_required":
        return "recovery_required"
    if mutation_state == "prepared":
        return "prepared"
    if lifecycle_state == "hidden":
        return "hidden"
    if lifecycle_state == "active" and mutation_state == "none":
        return "active"
    return "unknown"


def _physical_status(lifecycle: LifecycleState) -> str:
    return "current" if lifecycle == "active" else lifecycle


def _unknown_memory(memory_id: str) -> LabLifecycleMemoryItem:
    return LabLifecycleMemoryItem(
        memory_id=memory_id,
        current_lifecycle_state="unknown",
        current_revision=None,
        current_physical_status="unknown",
        retrieval_eligible=None,
        bounded_reason_ids=["primary_current_state_unresolved"],
    )


def _dominant_status(counters: dict[str, int]) -> str:
    active = [name for name, count in counters.items() if count > 0]
    if not active:
        return "none"
    return active[0] if len(active) == 1 else "mixed"


def _durable_result(availability: Availability, status: str, reasons: tuple[str, ...]) -> LabDurableFinalizationVisibility:
    return LabDurableFinalizationVisibility(
        availability=availability,
        status=status,  # type: ignore[arg-type]
        pending_count=0,
        complete_count=0,
        isolated_count=0,
        bounded_reason_ids=normalize_reason_ids(reasons),
    )


def _queue_result(availability: Availability, status: str, reasons: tuple[str, ...]) -> LabQueueWorkerVisibility:
    return LabQueueWorkerVisibility(
        availability=availability,
        status=status,  # type: ignore[arg-type]
        queued_count=0,
        processing_count=0,
        formed_count=0,
        held_count=0,
        blocked_count=0,
        failed_count=0,
        bounded_reason_ids=normalize_reason_ids(reasons),
    )


def _sha256_text(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


__all__ = [
    "LabDurableFinalizationVisibility",
    "LabFreshConversationVisibility",
    "LabLifecycleMemoryItem",
    "LabLifecycleVisibilityProjection",
    "LabQueueWorkerVisibility",
    "build_lab_lifecycle_visibility_projection",
]
