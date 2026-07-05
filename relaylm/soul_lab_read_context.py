"""Shared bounded read context for SOUL Lab memory projections."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

from .relaymem_primary_current_state import (
    PrimaryCurrentStateError,
    resolve_primary_current_state,
)
from .relaymem_primary_recall import _load_control_state, _load_validated_page
from .soul_lab_observation_store import (
    bounded_text,
    normalize_reason_ids,
    read_run_receipts_for_scope,
    read_used_receipt_for_run,
)

LifecycleState = Literal["active", "hidden", "unknown"]
CurrentOverlay = tuple[str | None, LifecycleState, str | None]


class LabObservationScopeLike(Protocol):
    known: bool
    available: bool
    character_id: str
    namespace: str
    store_root: str | None
    reason_ids: tuple[str, ...]


def _run_order_key(item: dict[str, Any]) -> tuple[datetime, str]:
    completed = datetime.fromisoformat(str(item["completed_at"]).replace("Z", "+00:00"))
    return completed.astimezone(timezone.utc), str(item["run_id"])


@dataclass
class LabReadContext:
    """One-request read-side facts shared by SOUL Lab memory projections."""

    character_id: str
    namespace: str
    store_root: str | None
    scope_available: bool
    scope_reasons: tuple[str, ...]
    latest_run: dict[str, Any] | None
    run_reasons: list[str]
    latest_used_receipt: dict[str, Any] | None
    used_reasons: list[str]
    used_scope_mismatch: bool
    _current_summary_cache: tuple[dict[str, str], list[str]] | None = field(
        default=None, init=False, repr=False
    )
    _current_overlay_cache: dict[str, CurrentOverlay] = field(
        default_factory=dict, init=False, repr=False
    )

    @property
    def availability(self) -> Literal["available", "empty", "unavailable"]:
        if not self.scope_available or self.store_root is None:
            return "unavailable"
        if self.latest_run is None:
            return "empty"
        return "available"

    @property
    def unavailable_reasons(self) -> tuple[str, ...]:
        if not self.scope_available or self.store_root is None:
            return self.scope_reasons
        return ()

    @property
    def run_id(self) -> str | None:
        if self.latest_run is None:
            return None
        return str(self.latest_run["run_id"])

    @property
    def response_generation_completed(self) -> bool:
        return (
            self.latest_run is not None
            and self.latest_run.get("relayrun_status") == "completed"
        )

    def current_summary_map(self) -> dict[str, str]:
        summaries, _reasons = self._current_summaries()
        return summaries

    def current_summary_reasons(self) -> list[str]:
        _summaries, reasons = self._current_summaries()
        return reasons

    def current_overlay(self, memory_id: str) -> CurrentOverlay:
        cached = self._current_overlay_cache.get(memory_id)
        if cached is not None:
            return cached
        if self.store_root is None:
            result: CurrentOverlay = (
                None,
                "unknown",
                "primary_current_state_unresolved",
            )
        else:
            result = _current_overlay(self.store_root, self.namespace, memory_id)
        self._current_overlay_cache[memory_id] = result
        return result

    def _current_summaries(self) -> tuple[dict[str, str], list[str]]:
        cached = self._current_summary_cache
        if cached is not None:
            return cached
        if self.store_root is None:
            cached = ({}, [])
        else:
            cached = _current_summaries(self.store_root, self.namespace)
        self._current_summary_cache = cached
        return cached


def build_lab_read_context(scope: LabObservationScopeLike) -> LabReadContext:
    if not scope.available or scope.store_root is None:
        return LabReadContext(
            character_id=scope.character_id,
            namespace=scope.namespace,
            store_root=scope.store_root,
            scope_available=False,
            scope_reasons=tuple(scope.reason_ids),
            latest_run=None,
            run_reasons=[],
            latest_used_receipt=None,
            used_reasons=[],
            used_scope_mismatch=False,
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
        return LabReadContext(
            character_id=scope.character_id,
            namespace=scope.namespace,
            store_root=scope.store_root,
            scope_available=True,
            scope_reasons=(),
            latest_run=None,
            run_reasons=normalize_reason_ids(run_reasons),
            latest_used_receipt=None,
            used_reasons=[],
            used_scope_mismatch=False,
        )

    latest = max(runs, key=_run_order_key)
    receipt, used_reasons = read_used_receipt_for_run(
        scope.store_root, str(latest["run_id"])
    )
    used_scope_mismatch = False
    if receipt is not None and (
        receipt.get("character_id") != scope.character_id
        or receipt.get("namespace") != scope.namespace
    ):
        receipt = None
        used_scope_mismatch = True
        used_reasons = normalize_reason_ids(
            [*used_reasons, "observation_receipt_scope_mismatch"]
        )

    return LabReadContext(
        character_id=scope.character_id,
        namespace=scope.namespace,
        store_root=scope.store_root,
        scope_available=True,
        scope_reasons=(),
        latest_run=latest,
        run_reasons=normalize_reason_ids(run_reasons),
        latest_used_receipt=receipt,
        used_reasons=normalize_reason_ids(used_reasons),
        used_scope_mismatch=used_scope_mismatch,
    )


def _current_summaries(store_root: str, namespace: str) -> tuple[dict[str, str], list[str]]:
    root = Path(store_root)
    control, reasons = _load_control_state(root)
    if control is None:
        return {}, reasons
    from .relaymem_primary_correction import (
        load_primary_correction_state,
        resolve_primary_correction_identity,
    )

    correction_state = load_primary_correction_state(root, namespace=namespace)
    summaries: dict[str, str] = {}
    output_reasons = list(reasons)
    for entry in control["index"]:
        if entry.get("namespace") != namespace:
            continue
        physical_identity = entry.get("idempotency_key")
        if not isinstance(physical_identity, str):
            continue
        resolved = resolve_primary_correction_identity(
            correction_state, physical_identity
        )
        if resolved is None:
            output_reasons.append("primary_correction_state_invalid")
            continue
        identity, _revision, is_current = resolved
        if not is_current:
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


def _current_overlay(
    store_root: str,
    namespace: str,
    memory_id: str,
) -> CurrentOverlay:
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


__all__ = [
    "LabReadContext",
    "build_lab_read_context",
]
