"""Canonical public Primary current-state resolver compatibility boundary.

Phase I-4C2 extends the read-only I-4B/I-4C1 authority with exact Forget
tombstone evidence. Active ``relaymem.primary_page.v0`` and completed Phase I-3
correction chains keep their existing behavior. The resolver never writes or
attempts recovery.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from . import _relaymem_primary_current_state_impl as _impl
from .relaymem_primary_forget_artifact import FORGET_PREPARED_SCHEMA
from .relaymem_primary_forget_finalization_artifact import FORGET_TOMBSTONE_SCHEMA
from .relaymem_primary_forget_finalized_state import (
    resolve_finalized_forget_current_state,
)
from .relaymem_primary_lifecycle_page import resolve_forget_current_state

PRIMARY_CURRENT_STATE_SCHEMA = _impl.PRIMARY_CURRENT_STATE_SCHEMA
CORRECTION_PREPARED_SCHEMA = _impl.CORRECTION_PREPARED_SCHEMA
CORRECTION_RECEIPT_SCHEMA = _impl.CORRECTION_RECEIPT_SCHEMA
CORRECTION_ROOT = _impl.CORRECTION_ROOT
PrimaryCurrentStateError = _impl.PrimaryCurrentStateError
PrimaryCorrectionStateIndex = _impl.PrimaryCorrectionStateIndex
PrimaryCurrentState = _impl.PrimaryCurrentState
empty_primary_current_state_index = _impl.empty_primary_current_state_index
load_primary_current_state_index = _impl.load_primary_current_state_index
resolve_primary_current_identity = _impl.resolve_primary_current_identity


def resolve_primary_current_state(
    store_root: str | Path,
    *,
    namespace: str,
    memory_id: str,
    expected_revision: int | None = None,
) -> PrimaryCurrentState:
    """Resolve one logical Primary memory including finalized Forget evidence."""

    if expected_revision is not None and (
        type(expected_revision) is not int or expected_revision < 1
    ):
        raise PrimaryCurrentStateError("invalid_request")

    finalized = resolve_finalized_forget_current_state(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
    )
    if finalized is not None:
        if expected_revision is not None and finalized.current_revision != expected_revision:
            raise PrimaryCurrentStateError("stale_revision")
        return finalized

    forget = resolve_forget_current_state(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
    )
    if forget is not None:
        if expected_revision is not None and forget.current_revision != expected_revision:
            raise PrimaryCurrentStateError("stale_revision")
        if forget.mutation_state != "forget_prepared":
            return forget
        reasons = tuple(
            dict.fromkeys(
                (*forget.bounded_reason_ids, "primary_mutation_recovery_required")
            )
        )[:32]
        return replace(
            forget,
            mutation_state="prepared",
            retrieval_eligible=False,
            bounded_reason_ids=reasons,
        )

    state = _impl.resolve_primary_current_state(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
    )
    if state.mutation_state != "prepared":
        return state
    reasons = tuple(
        dict.fromkeys(
            (*state.bounded_reason_ids, "primary_mutation_recovery_required")
        )
    )[:32]
    return replace(
        state,
        mutation_state="recovery_required",
        retrieval_eligible=False,
        bounded_reason_ids=reasons,
    )


def load_primary_current_target(
    store_root: str | Path,
    *,
    namespace: str,
    memory_id: str,
    expected_revision: int,
) -> dict[str, Any]:
    """Return one exact active mutation target; never fall back from hidden state."""

    state = resolve_primary_current_state(
        store_root,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=expected_revision,
    )
    if state.mutation_state == "corrupt" or not state.controls_valid or not state.page_valid:
        raise PrimaryCurrentStateError("target_corrupt")
    if state.lifecycle_state != "active":
        raise PrimaryCurrentStateError("target_not_active")
    if state.mutation_state != "none" or not state.retrieval_eligible:
        raise PrimaryCurrentStateError("operation_conflict")
    return {
        "physical_id": state.current_physical_id,
        "revision": state.current_revision,
        "metadata": dict(state.metadata),
        "page_digest": state.page_digest,
        "relative_path": state.relative_path,
    }


__all__ = [
    "PRIMARY_CURRENT_STATE_SCHEMA",
    "CORRECTION_PREPARED_SCHEMA",
    "CORRECTION_RECEIPT_SCHEMA",
    "FORGET_PREPARED_SCHEMA",
    "FORGET_TOMBSTONE_SCHEMA",
    "CORRECTION_ROOT",
    "PrimaryCurrentStateError",
    "PrimaryCorrectionStateIndex",
    "PrimaryCurrentState",
    "empty_primary_current_state_index",
    "load_primary_current_state_index",
    "resolve_primary_current_identity",
    "resolve_primary_current_state",
    "load_primary_current_target",
]
