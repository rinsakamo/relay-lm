"""Public I1-GC one-record durable-finalization replay authority."""
from __future__ import annotations

from typing import Any

from . import _relaymem_slp_durable_finalization_replay_impl as _impl
from .relaymem_slp_durable_finalization_replay_current_source import (
    reconstruct_current_finalized_source as _reconstruct_source,
)

COMPLETION_FIELDS = _impl.COMPLETION_FIELDS
COMPLETION_REVISION = _impl.COMPLETION_REVISION
COMPLETION_SCHEMA = _impl.COMPLETION_SCHEMA
REPLAY_PROJECTION_SCHEMA = _impl.REPLAY_PROJECTION_SCHEMA
RelayMEMSLPDurableFinalizationReplayProjection = _impl.RelayMEMSLPDurableFinalizationReplayProjection
RelayMEMSLPDurableFinalizationReplayResult = _impl.RelayMEMSLPDurableFinalizationReplayResult

apply_relaymem_slp_runtime_enqueue = _impl.apply_relaymem_slp_runtime_enqueue
prepare_relaymem_slp_runtime_enqueue = _impl.prepare_relaymem_slp_runtime_enqueue
_rename_noreplace = _impl._rename_noreplace
_hash_without = _impl._hash_without
_acquire_fence = _impl._acquire_fence
_wrap_runtime = _impl._wrap_runtime
_read_completion_fd = _impl._read_completion_fd
_publish_completion = _impl._publish_completion


def _sync_dependency_seams() -> None:
    _impl.apply_relaymem_slp_runtime_enqueue = apply_relaymem_slp_runtime_enqueue
    _impl.prepare_relaymem_slp_runtime_enqueue = prepare_relaymem_slp_runtime_enqueue
    _impl._rename_noreplace = _rename_noreplace
    _impl._acquire_fence = _acquire_fence
    _impl._wrap_runtime = _wrap_runtime
    _impl._reconstruct_source = _reconstruct_source
    _impl._read_completion_fd = _read_completion_fd
    _impl._publish_completion = _publish_completion


def replay_relaymem_slp_durable_finalization_record(
    config: object,
    *,
    locator_digest: object,
    registry: Any,
    fault_injector: Any = None,
) -> RelayMEMSLPDurableFinalizationReplayResult:
    """Converge one caller-selected locator without discovery or execution."""

    _sync_dependency_seams()
    return _impl.replay_relaymem_slp_durable_finalization_record(
        config,
        locator_digest=locator_digest,
        registry=registry,
        fault_injector=fault_injector,
    )


def build_relaymem_slp_durable_finalization_replay_node_result(
    result: RelayMEMSLPDurableFinalizationReplayResult,
):
    return _impl.build_relaymem_slp_durable_finalization_replay_node_result(result)


def completion_filename(locator_digest: str) -> str:
    return _impl.completion_filename(locator_digest)


def validate_completion_marker(
    value: object,
    *,
    expected_locator: str | None = None,
    expected: Any = None,
):
    return _impl.validate_completion_marker(
        value,
        expected_locator=expected_locator,
        expected=expected,
    )


_sync_dependency_seams()

__all__ = [
    "COMPLETION_FIELDS",
    "COMPLETION_REVISION",
    "COMPLETION_SCHEMA",
    "REPLAY_PROJECTION_SCHEMA",
    "RelayMEMSLPDurableFinalizationReplayProjection",
    "RelayMEMSLPDurableFinalizationReplayResult",
    "build_relaymem_slp_durable_finalization_replay_node_result",
    "completion_filename",
    "replay_relaymem_slp_durable_finalization_record",
    "validate_completion_marker",
]
