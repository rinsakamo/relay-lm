"""Phase 6-C1-2 one already-claimed Primary MEM job worker.

The public module preserves the exact request/result/projection API and the
patchable compose/classifier seams. Runtime-private implementation is split
across adjacent modules so validation, lease fencing, outcome adaptation, and
projection ownership remain explicit.
"""
from __future__ import annotations

from . import _relaymem_slp_primary_worker_execute as _execute
from . import _relaymem_slp_primary_worker_outcome_adapter as _outcome_adapter
from .pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from ._relaymem_slp_primary_worker_types import (
    PROJECTION_SCHEMA,
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    RelayMEMSLPPrimaryWorkerProjection,
    RelayMEMSLPPrimaryWorkerRequest,
    RelayMEMSLPPrimaryWorkerResult,
)
from ._relaymem_slp_primary_worker_view import project_relaymem_slp_primary_worker

execute_relaymem_primary_pipeline = _execute.execute_relaymem_primary_pipeline
classify_relaymem_slp_primary_worker_outcome = (
    _execute.classify_relaymem_slp_primary_worker_outcome
)


def execute_relaymem_slp_primary_worker(
    request: object,
) -> RelayMEMSLPPrimaryWorkerResult:
    """Execute exactly one caller-selected canonical B3 claimed record."""

    pipeline = globals()["execute_relaymem_primary_pipeline"]
    classifier = globals()["classify_relaymem_slp_primary_worker_outcome"]
    _execute.execute_relaymem_primary_pipeline = pipeline
    _execute.classify_relaymem_slp_primary_worker_outcome = classifier
    _outcome_adapter.classify_relaymem_slp_primary_worker_outcome = classifier
    return _execute.execute_relaymem_slp_primary_worker(request)


def build_relaymem_slp_primary_worker_node_result(
    result: RelayMEMSLPPrimaryWorkerResult,
) -> PipelineNodeResult:
    projection = project_relaymem_slp_primary_worker(result)
    node_status = {
        "disabled": "skipped",
        "dry_run_ready": "diagnostic_only",
        "terminal_succeeded": "applied",
        "retry_released": "blocked",
        "terminal_failed": "failed",
        "invalid_input": "failed",
        "transition_failed": "failed",
    }.get(result.status, "blocked")
    return build_pipeline_node_result(
        node_name="relaymem_slp_primary_worker",
        status=node_status,
        decision=result.status,
        blocked_reasons=result.reason_ids,
        diagnostics=projection.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relaymem_slp_primary_worker_result",
                "schema_version": RESULT_SCHEMA,
                "present": True,
                "content_free": True,
                "runtime_private": True,
                "private_result_omitted": True,
                "source_content_included": False,
                "pipeline_result_included": False,
                "outcome_result_included": False,
                "queue_record_included": False,
                "claim_fence_included": False,
                "queue_transition_performed": result.queue_transition_performed,
                "writes_memory": result.side_effect_started,
                "mutates_soul": False,
                "changes_visible_response": False,
            }
        ],
    )


__all__ = [
    "PROJECTION_SCHEMA",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "RelayMEMSLPPrimaryWorkerProjection",
    "RelayMEMSLPPrimaryWorkerRequest",
    "RelayMEMSLPPrimaryWorkerResult",
    "build_relaymem_slp_primary_worker_node_result",
    "execute_relaymem_slp_primary_worker",
    "project_relaymem_slp_primary_worker",
]
