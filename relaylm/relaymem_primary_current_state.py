"""Canonical public Primary current-state resolver compatibility boundary.

The Phase I-4B implementation remains source-compatible with the original
resolver implementation while classifying any valid unresolved prepared
mutation as recovery-required for fail-closed consumers.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from . import _relaymem_primary_current_state_impl as _impl

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
load_primary_current_target = _impl.load_primary_current_target


def resolve_primary_current_state(
    store_root: str | Path,
    *,
    namespace: str,
    memory_id: str,
    expected_revision: int | None = None,
) -> PrimaryCurrentState:
    """Resolve one logical Primary memory and normalize recovery evidence.

    A valid, unapplied prepared mutation is durable continuation evidence rather
    than an ordinary active state. Public consumers therefore receive the
    canonical ``recovery_required`` classification and retrieval remains closed.
    """

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


__all__ = [
    "PRIMARY_CURRENT_STATE_SCHEMA",
    "CORRECTION_PREPARED_SCHEMA",
    "CORRECTION_RECEIPT_SCHEMA",
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
