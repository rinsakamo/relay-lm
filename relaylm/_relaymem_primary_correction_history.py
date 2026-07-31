"""Read-only state and history compatibility for Primary correction."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from ._relaymem_primary_page_writer_common import is_sha256
from .relaymem_primary_recall import _load_control_state
from .relaymem_primary_current_state import (PrimaryCorrectionStateIndex, PrimaryCurrentStateError, empty_primary_current_state_index, load_primary_current_state_index, load_primary_current_target, resolve_primary_current_identity)
from ._relaymem_primary_correction_preflight import HISTORY_SCHEMA, PrimaryCorrectionError, _MAX_REASON, _safe_store_root, _shared_error_code
CorrectionState = PrimaryCorrectionStateIndex


def list_primary_memory_corrections(
    *, store_root: str, namespace: str, memory_id: str
) -> dict[str, Any]:
    root = _safe_store_root(store_root)
    _load_scoped_control_state(
        root, namespace=namespace, logical_memory_id=memory_id
    )
    state = load_primary_correction_state(root, namespace=namespace)
    if "*" in state.invalid_logical or memory_id in state.invalid_logical:
        raise PrimaryCorrectionError("target_corrupt")
    current = state.current_by_logical.get(memory_id)
    if current is None:
        target = _load_current_target(
            root,
            namespace=namespace,
            logical_memory_id=memory_id,
            expected_revision=1,
            state=state,
        )
        current = (str(target["physical_id"]), 1)
    receipts = state.receipts_by_logical.get(memory_id, ())
    items = [
        {
            "correction_id": str(item["correction_id"]),
            "prior_revision": int(item["prior_revision"]),
            "result_revision": int(item["result_revision"]),
            "reason": _bounded(str(item["reason"]), _MAX_REASON),
            "status": str(item["status"]),
            "applied_at": str(item["applied_at"]),
            "title_changed": bool(item["title_changed"]),
            "summary_changed": bool(item["summary_changed"]),
        }
        for item in receipts[-50:]
    ]
    return {
        "schema": HISTORY_SCHEMA,
        "source": "relaylm_runtime",
        "read_only": True,
        "memory_id": memory_id,
        "current_revision": int(current[1]),
        "correction_count": len(receipts),
        "last_corrected_at": str(receipts[-1]["applied_at"]) if receipts else None,
        "last_correction_status": str(receipts[-1]["status"]) if receipts else None,
        "has_prior_revision": bool(receipts),
        "items": items,
    }


def load_primary_correction_state(
    store_root: str | Path, *, namespace: str
) -> CorrectionState:
    """Compatibility wrapper over the canonical Primary current-state index."""

    try:
        return load_primary_current_state_index(store_root, namespace=namespace)
    except PrimaryCurrentStateError as exc:
        raise PrimaryCorrectionError(_shared_error_code(exc.code)) from exc


def resolve_primary_correction_identity(
    state: CorrectionState, physical_identity: str
) -> tuple[str, int, bool] | None:
    """Compatibility wrapper over canonical logical/current identity resolution."""

    return resolve_primary_current_identity(state, physical_identity)


def _load_scoped_control_state(
    root: Path, *, namespace: str, logical_memory_id: str
) -> dict[str, Any]:
    """Confirm logical target membership before reading correction metadata.

    This preserves the not-found/wrong-scope indistinguishability contract even
    after the target has correction receipts in another namespace.
    """

    if not is_sha256(logical_memory_id):
        raise PrimaryCorrectionError("not_found_or_wrong_scope")
    control, reasons = _load_control_state(root)
    if control is None or reasons:
        raise PrimaryCorrectionError("target_corrupt")
    index_matches = [
        entry
        for entry in control["index"]
        if entry.get("idempotency_key") == logical_memory_id
        and entry.get("namespace") == namespace
    ]
    log_matches = [
        entry
        for entry in control["log"]
        if entry.get("idempotency_key") == logical_memory_id
        and entry.get("namespace") == namespace
    ]
    if not index_matches and not log_matches:
        raise PrimaryCorrectionError("not_found_or_wrong_scope")
    if len(index_matches) != 1 or len(log_matches) != 1:
        raise PrimaryCorrectionError("target_corrupt")
    return control


def _load_current_target(
    root: Path,
    *,
    namespace: str,
    logical_memory_id: str,
    expected_revision: int,
    state: CorrectionState,
) -> dict[str, Any]:
    del state
    try:
        return load_primary_current_target(
            root,
            namespace=namespace,
            memory_id=logical_memory_id,
            expected_revision=expected_revision,
        )
    except PrimaryCurrentStateError as exc:
        raise PrimaryCorrectionError(_shared_error_code(exc.code)) from exc


def _empty_state(*, invalid: set[str] | None = None) -> CorrectionState:
    return empty_primary_current_state_index(invalid=invalid)


def _bounded(value: str, maximum: int) -> str:
    return value if len(value) <= maximum else value[: maximum - 1] + "…"
