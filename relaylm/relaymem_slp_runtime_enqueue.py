"""Phase 6 I1-B deferred enqueue and protected source-capture orchestration.

This helper composes the exact A1, A2, B1, and B2 production boundaries.  It
assembles the canonical 16-field protected C1 payload after B1 has derived the
job and dispatch identities, then publishes that payload to the process-local
registry only after B2 reports a safe enqueue outcome.

The canonical C1-0 typed source is deliberately *not* constructed here.  Its
builder requires a real B3 claimed record, which does not exist in request
finalization and must not be fabricated.  A later claimed-job worker consumes
the retained payload through the registry, which then invokes the canonical
C1-0 builder and one-shot consumer.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relaymem_slp_dispatch_preflight import (
    RelayMEMSLPDispatchPreflightResult,
    build_relaymem_slp_dispatch_preflight,
)
from relaylm.relaymem_slp_durable_enqueue import (
    RelayMEMSLPDurableEnqueueResult,
    enqueue_relaymem_slp_durable_job,
)
from relaylm.relaymem_slp_job_admission import (
    build_relaymem_slp_job_admission_preflight,
)
from relaylm.relaymem_slp_primary_worker_source import (
    SOURCE_SCHEMA,
    RelayMEMSLPPrimaryWorkerSourceScope,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
    RelayMEMSLPSourceRegistryResult,
)
from relaylm.relaymem_slp_queue_record import dedupe, is_token, strict_bool
from relaylm.relaymem_slp_response_handoff import (
    RelayMEMSLPResponseHandoffResult,
    build_relaymem_slp_response_finalization_handoff,
)

RUNTIME_ENQUEUE_SCHEMA = "relaymem.slp_runtime_enqueue.v0"
RUNTIME_ENQUEUE_PROJECTION_SCHEMA = "relaymem.slp_runtime_enqueue_projection.v0"
_MAX_REASONS = 32

RuntimeEnqueueStatus = Literal[
    "disabled",
    "invalid_input",
    "skipped",
    "held",
    "blocked",
    "dry_run_ready",
    "enqueued",
    "duplicate_existing",
    "enqueue_failed",
    "source_retention_failed",
]
FailureStage = Literal[
    "none",
    "gate",
    "admission",
    "handoff",
    "dispatch",
    "source_capture",
    "enqueue",
    "source_retention",
]


@dataclass(frozen=True)
class RelayMEMSLPRuntimeEnqueueProjection:
    """Strict content-free projection for generic diagnostics and trace."""

    status: RuntimeEnqueueStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    admission_eligible: bool
    handoff_ready: bool
    dispatch_ready: bool
    source_capture_built: bool
    typed_source_built: bool
    source_retained: bool
    worker_ready: bool
    enqueue_attempted: bool
    enqueue_new: bool
    duplicate_existing: bool
    blocked: bool
    failure_stage: FailureStage
    blocked_reason_ids: tuple[str, ...]

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": RUNTIME_ENQUEUE_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "raw_messages_included": False,
            "governed_title_included": False,
            "governed_summary_included": False,
            "namespace_value_included": False,
            "identifier_values_included": False,
            "lineage_fingerprint_included": False,
            "idempotency_key_included": False,
            "queue_path_included": False,
            "timestamp_values_included": False,
            "exception_text_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "admission_eligible": self.admission_eligible,
            "handoff_ready": self.handoff_ready,
            "dispatch_ready": self.dispatch_ready,
            "source_capture_built": self.source_capture_built,
            "typed_source_built": self.typed_source_built,
            "source_retained": self.source_retained,
            "worker_ready": self.worker_ready,
            "enqueue_attempted": self.enqueue_attempted,
            "enqueue_new": self.enqueue_new,
            "duplicate_existing": self.duplicate_existing,
            "blocked": self.blocked,
            "failure_stage": self.failure_stage,
            "process_local_source_retention": self.source_retained,
            "restart_complete_source_persistence": False,
            "worker_invoked": False,
            "b3_claim_performed": False,
            "invokes_slp": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "blocked_reason_ids": list(self.blocked_reason_ids),
        }


@dataclass(frozen=True)
class RelayMEMSLPRuntimeEnqueueResult:
    """Runtime-private exact stage results kept separate from public diagnostics."""

    status: RuntimeEnqueueStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    failure_stage: FailureStage
    blocked_reasons: tuple[str, ...]
    admission_result: dict[str, object] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    handoff_result: RelayMEMSLPResponseHandoffResult | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    dispatch_result: RelayMEMSLPDispatchPreflightResult | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    protected_source_payload: dict[str, object] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    source_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    enqueue_result: RelayMEMSLPDurableEnqueueResult | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    source_retention_result: RelayMEMSLPSourceRegistryResult | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def to_runtime_dict(self) -> dict[str, object]:
        projection = project_relaymem_slp_runtime_enqueue(self)
        return {
            "schema_version": RUNTIME_ENQUEUE_SCHEMA,
            "runtime_private": True,
            "content_included": self.protected_source_payload is not None,
            "protected_source_payload_omitted": True,
            "exact_stage_results_omitted": True,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "failure_stage": self.failure_stage,
            "blocked_reasons": list(self.blocked_reasons),
            "projection": projection.to_log_dict(),
        }

    def to_log_dict(self) -> dict[str, object]:
        return project_relaymem_slp_runtime_enqueue(self).to_log_dict()


def apply_relaymem_slp_runtime_enqueue(
    *,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None,
    queue_root: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
    character_id: object = None,
    run_id: str | None = None,
    turn_index: int | None = None,
    session_id: str | None = None,
    namespace: str = "default",
    source_lineage_artifact: Mapping[str, object] | None = None,
    source_count: int = 1,
    relayscn_scene_policy_artifact: object = None,
    relayemo_artifact: object = None,
    governed_messages: object = None,
    governed_experience_artifact: object = None,
    visible_response_finalized: bool = False,
    runtime_terminal_status: str = "completed",
    persistence_policy_status: str = "allowed",
) -> RelayMEMSLPRuntimeEnqueueResult:
    """Compose A1 -> A2 -> B1 -> B2 and retain one protected source capture."""

    enabled_value, enabled_errors = strict_bool(enabled, "enabled_invalid")
    dry_run_value, dry_run_errors = strict_bool(
        dry_run_only,
        "dry_run_only_invalid",
    )
    apply_value, apply_errors = strict_bool(apply_enabled, "apply_enabled_invalid")
    gate_reasons = dedupe((*enabled_errors, *dry_run_errors, *apply_errors))
    if gate_reasons:
        return _result(
            "invalid_input",
            enabled=enabled_value,
            dry_run_only=dry_run_value,
            apply_enabled=apply_value,
            failure_stage="gate",
            blocked_reasons=gate_reasons,
        )
    if not enabled_value:
        return _result(
            "disabled",
            enabled=False,
            dry_run_only=dry_run_value,
            apply_enabled=apply_value,
        )
    if dry_run_value and apply_value:
        return _result(
            "blocked",
            enabled=True,
            dry_run_only=True,
            apply_enabled=True,
            failure_stage="gate",
            blocked_reasons=("apply_enabled_in_dry_run",),
        )
    if not dry_run_value and not apply_value:
        return _result(
            "blocked",
            enabled=True,
            dry_run_only=False,
            apply_enabled=False,
            failure_stage="gate",
            blocked_reasons=("apply_gate_incomplete",),
        )
    if not is_token(character_id):
        return _result(
            "invalid_input",
            enabled=True,
            dry_run_only=dry_run_value,
            apply_enabled=apply_value,
            failure_stage="gate",
            blocked_reasons=("character_id_invalid",),
        )

    admission = build_relaymem_slp_job_admission_preflight(
        enabled=True,
        dry_run_only=True,
        enqueue_enabled=False,
        trigger_mode="turn_end",
        processing_stage="primary_formation",
        run_id=run_id,
        turn_index=turn_index,
        session_id=session_id,
        namespace=namespace,
        source_event_kind="turn",
        source_lineage_artifact=source_lineage_artifact,
        source_count=source_count,
        visible_response_finalized=visible_response_finalized,
        runtime_terminal_status=runtime_terminal_status,
        persistence_policy_status=persistence_policy_status,
    )
    admission_status = admission.get("admission_status")
    if admission_status not in {"admitted_dry_run", "eligible_for_enqueue"}:
        mapped_status: RuntimeEnqueueStatus = (
            "held" if admission_status == "held" else
            "skipped" if admission_status == "skipped" else
            "blocked"
        )
        return _result(
            mapped_status,
            enabled=True,
            dry_run_only=dry_run_value,
            apply_enabled=apply_value,
            failure_stage="admission",
            blocked_reasons=_mapping_reasons(admission),
            admission_result=admission,
        )

    handoff = build_relaymem_slp_response_finalization_handoff(
        admission,
        enabled=True,
        dry_run_only=True,
        response_finalized=visible_response_finalized,
    )
    if handoff.status != "dry_run_candidate" or handoff.candidate is None:
        return _result(
            "blocked",
            enabled=True,
            dry_run_only=dry_run_value,
            apply_enabled=apply_value,
            failure_stage="handoff",
            blocked_reasons=handoff.blocked_reasons or ("response_handoff_not_ready",),
            admission_result=admission,
            handoff_result=handoff,
        )

    dispatch = build_relaymem_slp_dispatch_preflight(
        handoff,
        enabled=True,
        dry_run_only=True,
    )
    if dispatch.status != "dry_run_ready" or dispatch.durable_job is None:
        return _result(
            "blocked",
            enabled=True,
            dry_run_only=dry_run_value,
            apply_enabled=apply_value,
            failure_stage="dispatch",
            blocked_reasons=dispatch.blocked_reasons or ("dispatch_preflight_not_ready",),
            admission_result=admission,
            handoff_result=handoff,
            dispatch_result=dispatch,
        )

    source_scope = RelayMEMSLPPrimaryWorkerSourceScope()
    source_payload = _build_protected_source_payload(
        dispatch,
        relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
        relayemo_artifact=relayemo_artifact,
        governed_messages=governed_messages,
        governed_experience_artifact=governed_experience_artifact,
    )
    if source_payload is None:
        source_scope.close()
        return _result(
            "blocked",
            enabled=True,
            dry_run_only=dry_run_value,
            apply_enabled=apply_value,
            failure_stage="source_capture",
            blocked_reasons=("protected_source_capture_input_invalid",),
            admission_result=admission,
            handoff_result=handoff,
            dispatch_result=dispatch,
        )

    if dry_run_value:
        return _result(
            "dry_run_ready",
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
            admission_result=admission,
            handoff_result=handoff,
            dispatch_result=dispatch,
            protected_source_payload=source_payload,
            source_scope=source_scope,
        )

    if type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        source_scope.close()
        return _result(
            "source_retention_failed",
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
            failure_stage="source_retention",
            blocked_reasons=("exact_source_registry_required",),
            admission_result=admission,
            handoff_result=handoff,
            dispatch_result=dispatch,
            protected_source_payload=source_payload,
        )

    enqueue = enqueue_relaymem_slp_durable_job(
        dispatch,
        queue_root=queue_root,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    if enqueue.status not in {"enqueued_new", "duplicate_existing"}:
        source_scope.close()
        return _result(
            "enqueue_failed",
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
            failure_stage="enqueue",
            blocked_reasons=enqueue.blocked_reasons or ("durable_enqueue_failed",),
            admission_result=admission,
            handoff_result=handoff,
            dispatch_result=dispatch,
            protected_source_payload=source_payload,
            enqueue_result=enqueue,
        )
    if type(enqueue.durable_record) is not dict:
        source_scope.close()
        return _result(
            "source_retention_failed",
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
            failure_stage="source_retention",
            blocked_reasons=("durable_enqueue_record_unavailable",),
            admission_result=admission,
            handoff_result=handoff,
            dispatch_result=dispatch,
            protected_source_payload=source_payload,
            enqueue_result=enqueue,
        )

    retention = registry.publish(
        source_payload=source_payload,
        durable_record=enqueue.durable_record,
        request_scope=source_scope,
        character_id=character_id,
    )
    if retention.status not in {"published_new", "duplicate_existing"}:
        source_scope.close()
        return _result(
            "source_retention_failed",
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
            failure_stage="source_retention",
            blocked_reasons=retention.blocked_reasons or ("protected_source_retention_failed",),
            admission_result=admission,
            handoff_result=handoff,
            dispatch_result=dispatch,
            protected_source_payload=source_payload,
            enqueue_result=enqueue,
            source_retention_result=retention,
        )
    if retention.status == "duplicate_existing":
        # The registry retains the original scope.  This duplicate request-local
        # scope must not remain live or overwrite the existing capture.
        source_scope.close()
    final_status: RuntimeEnqueueStatus = (
        "enqueued" if enqueue.status == "enqueued_new" else "duplicate_existing"
    )
    return _result(
        final_status,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        admission_result=admission,
        handoff_result=handoff,
        dispatch_result=dispatch,
        protected_source_payload=source_payload,
        source_scope=(
            source_scope if retention.status == "published_new" else None
        ),
        enqueue_result=enqueue,
        source_retention_result=retention,
    )


def project_relaymem_slp_runtime_enqueue(
    result: RelayMEMSLPRuntimeEnqueueResult,
) -> RelayMEMSLPRuntimeEnqueueProjection:
    admission_eligible = bool(
        result.admission_result is not None
        and result.admission_result.get("admission_status")
        in {"admitted_dry_run", "eligible_for_enqueue"}
    )
    handoff_ready = bool(
        result.handoff_result is not None
        and result.handoff_result.status == "dry_run_candidate"
        and result.handoff_result.candidate is not None
    )
    dispatch_ready = bool(
        result.dispatch_result is not None
        and result.dispatch_result.status == "dry_run_ready"
        and result.dispatch_result.durable_job is not None
    )
    enqueue = result.enqueue_result
    retention = result.source_retention_result
    return RelayMEMSLPRuntimeEnqueueProjection(
        status=result.status,
        enabled=result.enabled,
        dry_run_only=result.dry_run_only,
        apply_enabled=result.apply_enabled,
        admission_eligible=admission_eligible,
        handoff_ready=handoff_ready,
        dispatch_ready=dispatch_ready,
        source_capture_built=result.protected_source_payload is not None,
        typed_source_built=False,
        source_retained=bool(retention is not None and retention.retained),
        worker_ready=False,
        enqueue_attempted=bool(enqueue is not None and enqueue.enqueue_attempted),
        enqueue_new=bool(enqueue is not None and enqueue.status == "enqueued_new"),
        duplicate_existing=bool(
            enqueue is not None and enqueue.status == "duplicate_existing"
        ),
        blocked=result.status in {
            "invalid_input",
            "blocked",
            "enqueue_failed",
            "source_retention_failed",
        },
        failure_stage=result.failure_stage,
        blocked_reason_ids=result.blocked_reasons,
    )


def build_relaymem_slp_runtime_enqueue_node_result(
    result: RelayMEMSLPRuntimeEnqueueResult,
) -> PipelineNodeResult:
    """Build one content-free integrated runtime projection."""

    node_status = {
        "disabled": "skipped",
        "skipped": "skipped",
        "held": "blocked",
        "blocked": "blocked",
        "invalid_input": "failed",
        "enqueue_failed": "failed",
        "source_retention_failed": "failed",
    }.get(result.status, "diagnostic_only")
    projection = result.to_log_dict()
    return build_pipeline_node_result(
        node_name="relaymem_slp_runtime_enqueue",
        status=node_status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=projection,
        artifacts=[{
            "artifact_name": "relaymem_slp_protected_source_capture",
            "schema_version": SOURCE_SCHEMA,
            "present": result.protected_source_payload is not None,
            "content_free": True,
            "runtime_private": True,
            "protected_payload_omitted": True,
            "typed_source_built": False,
            "source_retained": projection["source_retained"],
            "worker_ready": False,
            "restart_complete": False,
            "identifier_values_included": False,
            "namespace_value_included": False,
            "lineage_fingerprint_included": False,
            "queue_path_included": False,
            "worker_invoked": False,
            "writes_memory": False,
            "changes_visible_response": False,
        }],
    )


def _build_protected_source_payload(
    dispatch: RelayMEMSLPDispatchPreflightResult,
    *,
    relayscn_scene_policy_artifact: object,
    relayemo_artifact: object,
    governed_messages: object,
    governed_experience_artifact: object,
) -> dict[str, object] | None:
    job = dispatch.durable_job
    if job is None:
        return None
    if type(relayscn_scene_policy_artifact) is not dict:
        return None
    if relayemo_artifact is not None and type(relayemo_artifact) is not dict:
        return None
    if type(governed_messages) not in {list, tuple}:
        return None
    if type(governed_experience_artifact) is not dict:
        return None
    return {
        "schema_version": SOURCE_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "job_id": job.job_id,
        "dispatch_idempotency_key": job.dispatch_idempotency_key,
        "run_id": job.run_id,
        "turn_index": job.turn_index,
        "session_id": job.session_id,
        "namespace": job.namespace,
        "source_event_kind": job.source_event_kind,
        "source_count": job.source_count,
        "source_lineage_fingerprint": job.source_lineage_fingerprint,
        "relayscn_scene_policy_artifact": relayscn_scene_policy_artifact,
        "relayemo_artifact": relayemo_artifact,
        "governed_messages": list(governed_messages),
        "governed_experience_artifact": governed_experience_artifact,
    }


def _mapping_reasons(value: Mapping[str, object]) -> tuple[str, ...]:
    reasons = value.get("blocked_reasons")
    if type(reasons) is list:
        return dedupe(tuple(item for item in reasons if type(item) is str))
    return ()


def _result(
    status: RuntimeEnqueueStatus,
    *,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    failure_stage: FailureStage = "none",
    blocked_reasons: Sequence[str] = (),
    admission_result: dict[str, object] | None = None,
    handoff_result: RelayMEMSLPResponseHandoffResult | None = None,
    dispatch_result: RelayMEMSLPDispatchPreflightResult | None = None,
    protected_source_payload: dict[str, object] | None = None,
    source_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = None,
    enqueue_result: RelayMEMSLPDurableEnqueueResult | None = None,
    source_retention_result: RelayMEMSLPSourceRegistryResult | None = None,
) -> RelayMEMSLPRuntimeEnqueueResult:
    return RelayMEMSLPRuntimeEnqueueResult(
        status=status,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        failure_stage=failure_stage,
        blocked_reasons=dedupe(tuple(blocked_reasons))[:_MAX_REASONS],
        admission_result=admission_result,
        handoff_result=handoff_result,
        dispatch_result=dispatch_result,
        protected_source_payload=protected_source_payload,
        source_scope=source_scope,
        enqueue_result=enqueue_result,
        source_retention_result=source_retention_result,
    )


__all__ = [
    "RUNTIME_ENQUEUE_PROJECTION_SCHEMA",
    "RUNTIME_ENQUEUE_SCHEMA",
    "RelayMEMSLPRuntimeEnqueueProjection",
    "RelayMEMSLPRuntimeEnqueueResult",
    "apply_relaymem_slp_runtime_enqueue",
    "build_relaymem_slp_runtime_enqueue_node_result",
    "project_relaymem_slp_runtime_enqueue",
]
