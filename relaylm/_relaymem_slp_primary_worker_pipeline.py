"""Checkpointed Primary pipeline execution for the SLP worker."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ._relaymem_slp_primary_worker_fence import _CheckpointCoordinator
from ._relaymem_slp_primary_worker_types import RelayMEMSLPPrimaryWorkerRequest
from .relaymem_primary_pipeline import (
    REQUEST_SCHEMA,
    RelayMEMPrimaryPipelineRequest,
    RelayMEMPrimaryPipelineResult,
    project_relaymem_primary_pipeline,
)
from .relaymem_slp_primary_worker_source import RelayMEMSLPPrimaryWorkerSource


@dataclass(frozen=True)
class _PrimaryWorkerPipelineExecution:
    pipeline_result: RelayMEMPrimaryPipelineResult | None
    coordinator: _CheckpointCoordinator
    execution_failed: bool


def _build_pipeline_request(
    request: RelayMEMSLPPrimaryWorkerRequest,
    source: RelayMEMSLPPrimaryWorkerSource,
) -> RelayMEMPrimaryPipelineRequest:
    return RelayMEMPrimaryPipelineRequest(
        schema_version=REQUEST_SCHEMA,
        runtime_private=True,
        content_included=True,
        worker_source=source,
        claimed_record=dict(request.claimed_record),
        request_scope=request.request_scope,
        store_root=request.store_root,
        enabled=True,
        dry_run_only=request.dry_run_only,
        apply_enabled=request.apply_enabled,
    )


def _execute_primary_worker_pipeline(
    request: RelayMEMSLPPrimaryWorkerRequest,
    source: RelayMEMSLPPrimaryWorkerSource,
    *,
    execute_pipeline: Callable[..., RelayMEMPrimaryPipelineResult],
) -> _PrimaryWorkerPipelineExecution:
    """Run and validate the pipeline while retaining exact checkpoint state."""

    coordinator = _CheckpointCoordinator(request)
    try:
        pipeline = execute_pipeline(
            _build_pipeline_request(request, source), checkpoint=coordinator
        )
        project_relaymem_primary_pipeline(pipeline)
    except Exception:
        return _PrimaryWorkerPipelineExecution(None, coordinator, True)
    return _PrimaryWorkerPipelineExecution(pipeline, coordinator, False)


__all__ = ["_PrimaryWorkerPipelineExecution", "_execute_primary_worker_pipeline"]
