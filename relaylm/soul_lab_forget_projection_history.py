"""SOUL Lab active-recent and Forget history projection helpers.

These helpers are read-only SOUL Lab projections over existing RelayMEM durable
state.  They do not repair, mutate, or reinterpret core Forget authority; they
only prevent hidden successors from being shown in the active recent view and
surface bounded tombstone evidence for operator audit.
"""
from __future__ import annotations

import json
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ._relaymem_primary_forget_impl import HISTORY_SCHEMA, PrimaryForgetError
from .relaymem_primary_current_state import (
    PrimaryCurrentStateError,
    resolve_primary_current_state,
)
from .relaymem_primary_forget_artifact import MUTATION_ROOT
from .relaymem_primary_forget_finalization_artifact import (
    MAX_TOMBSTONE_BYTES,
    validate_forget_tombstone,
)
from .soul_lab_observation_projection import (
    LabObservationScope,
    LabRecentMemoryProjection,
    build_lab_recent_memory_projection,
)
from .soul_lab_observation_store import normalize_reason_ids, stable_correlation

_MAX_HISTORY_ITEMS = 50


def build_lab_active_recent_memory_projection(
    scope: LabObservationScope, *, limit: int
) -> LabRecentMemoryProjection:
    """Return only active, current, retrieval-eligible Primary memories.

    The base recent projection walks the canonical control log.  After Forget,
    that log can still contain the prior active physical page for a logical
    memory whose current successor is hidden.  SOUL Lab recent is an active view,
    so each candidate is rechecked against the current-state resolver before it
    is shown.
    """

    projection = build_lab_recent_memory_projection(scope, limit=limit)
    if not scope.available or scope.store_root is None or not projection.items:
        return projection

    filtered = []
    reasons: list[str] = list(projection.bounded_reason_ids)
    for item in projection.items:
        try:
            state = resolve_primary_current_state(
                scope.store_root,
                namespace=scope.namespace,
                memory_id=item.memory_id,
            )
        except PrimaryCurrentStateError:
            reasons.append("primary_recent_current_state_unavailable")
            continue
        if (
            state.lifecycle_state != "active"
            or state.mutation_state != "none"
            or not state.controls_valid
            or not state.page_valid
            or not state.retrieval_eligible
            or state.current_revision != item.revision
        ):
            reasons.append("primary_recent_non_active_current_excluded")
            continue
        filtered.append(item)

    return projection.model_copy(
        update={
            "availability": "available" if filtered else "empty",
            "items": filtered,
            "bounded_reason_ids": normalize_reason_ids(reasons),
        }
    )


def build_lab_forget_history_projection(
    *, store_root: str, namespace: str, memory_id: str, base: Mapping[str, Any]
) -> dict[str, Any]:
    """Project durable Forget tombstones as content-free operator history."""

    items = _scan_forget_tombstones(
        store_root=store_root,
        namespace=namespace,
        memory_id=memory_id,
    )
    items.sort(key=_history_order_key, reverse=True)
    bounded_items = items[:_MAX_HISTORY_ITEMS]
    return {
        "schema": HISTORY_SCHEMA,
        "source": "relaylm_runtime",
        "read_only": True,
        "memory_id": memory_id,
        "current_revision": int(base["current_revision"]),
        "current_lifecycle_state": str(base["current_lifecycle_state"]),
        "forget_count": len(items),
        "items": bounded_items,
    }


def _scan_forget_tombstones(
    *, store_root: str, namespace: str, memory_id: str
) -> list[dict[str, Any]]:
    root = _safe_root(store_root)
    directory = root / Path(*MUTATION_ROOT.parts) / memory_id
    if _descendant_has_symlink(root, directory):
        raise PrimaryForgetError("target_corrupt")
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise PrimaryForgetError("target_corrupt")

    try:
        paths = sorted(directory.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise PrimaryForgetError("store_unavailable") from exc

    items: list[dict[str, Any]] = []
    for path in paths:
        if path.name == ".lock" or not path.name.endswith(".tombstone.json"):
            continue
        tombstone = _read_tombstone(path)
        if (
            tombstone.get("namespace") != namespace
            or tombstone.get("memory_id") != memory_id
        ):
            raise PrimaryForgetError("target_corrupt")
        items.append(_history_item(tombstone))
    return items


def _history_item(tombstone: Mapping[str, Any]) -> dict[str, Any]:
    receipt_seed = ":".join(
        (
            "relaylm-lab-forget-history-v0",
            str(tombstone["memory_id"]),
            str(tombstone["operation_key"]),
            str(tombstone["prior_revision"]),
            str(tombstone["result_revision"]),
            str(tombstone["applied_at"]),
        )
    )
    return {
        "receipt_type": "forget_tombstone",
        "operation_kind": "forget",
        "receipt_id": stable_correlation(receipt_seed),
        "prior_revision": int(tombstone["prior_revision"]),
        "result_revision": int(tombstone["result_revision"]),
        "lifecycle_state": "hidden",
        "retrieval_eligible": False,
        "ordinary_retrieval_excluded": True,
        "relayctx_injection_excluded": True,
        "physical_deletion": False,
        "audit_evidence_retained": True,
        "tombstone_present": True,
        "page_converged": bool(tombstone["page_converged"]),
        "index_converged": bool(tombstone["index_converged"]),
        "log_converged": bool(tombstone["log_converged"]),
        "recovery_required": bool(tombstone["recovery_required"]),
        "applied_at": str(tombstone["applied_at"]),
    }


def _history_order_key(item: Mapping[str, Any]) -> tuple[datetime, int, str]:
    try:
        applied = datetime.fromisoformat(str(item["applied_at"]).replace("Z", "+00:00"))
    except ValueError:
        applied = datetime.min.replace(tzinfo=timezone.utc)
    return (
        applied.astimezone(timezone.utc),
        int(item.get("result_revision", 0)),
        str(item.get("receipt_id", "")),
    )


def _read_tombstone(path: Path) -> dict[str, Any]:
    try:
        info = path.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_size <= 0
            or info.st_size > MAX_TOMBSTONE_BYTES
        ):
            raise PrimaryForgetError("target_corrupt")
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except PrimaryForgetError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PrimaryForgetError("target_corrupt") from exc
    if not validate_forget_tombstone(value):
        raise PrimaryForgetError("target_corrupt")
    return dict(value)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate key")
        output[key] = value
    return output


def _safe_root(value: str) -> Path:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise PrimaryForgetError("store_unavailable")
    root = Path(value)
    if _path_has_symlink(root):
        raise PrimaryForgetError("target_corrupt")
    if not root.exists() or not root.is_dir():
        raise PrimaryForgetError("store_unavailable")
    return root


def _path_has_symlink(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path()
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _descendant_has_symlink(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


__all__ = [
    "build_lab_active_recent_memory_projection",
    "build_lab_forget_history_projection",
]
