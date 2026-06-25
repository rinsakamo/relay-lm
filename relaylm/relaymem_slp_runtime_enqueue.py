"""Phase 6 I1-B deferred enqueue and protected source-capture orchestration.

The helper consumes only the exact finalized-turn protected source result, then
passes exact production artifacts through A1 -> A2 -> B1 -> B2.  The exact
16-field C1-0 payload is assembled only after B1 assigns job/dispatch identity
and is published to the process-local registry only after a safe B2 outcome.
No worker or M3 stage is invoked here.
"""
from __future__ import annotations

from collections.abc import Sequence
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
from relaylm.relaymem_slp_finalized_turn_source import (
    RelayMEMSLPFinalizedTurnSource,
    RelayMEMSLPFinalizedTurnSourceResult,
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
from relaylm.relaymem_slp_queue_record import dedupe, strict_bool
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
    "source_capture",
    "admission",
    "handoff",
    "dispatch",
    "enqueue",
    "source_retention",
]


@dataclass(frozen=True)
class RelayMEMSLPRuntimeEnqueueProjection:
    status: RuntimeEnqueueStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    finalized_turn_source_ready: bool
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
            "finalized_turn_source_ready": self.finalized_turn_source_ready,
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
    status: RuntimeEnqueueStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    failure_stage: FailureStage
    blocked_reasons: tuple[str, ...]
    finalized_turn_source_result: RelayMEMSLPFinalizedTurnSourceResult | None = field(
        default=None, repr=False, compare=False
    )
    admission_result: dict[str, object] | None = field(
        default=None, repr=False, compare=False
    )
    handoff_result: RelayMEMSLPResponseHandoffResult | None = field(
        default=None, repr=False, compare=False
    )
    dispatch_result: RelayMEMSLPDispatchPreflightResult | None = field(
        default=None, repr=False, compare=False
    )
    protected_source_payload: dict[str, object] | None = field(
        default=None, repr=False, compare=False
    )
    source_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = field(
        default=None, repr=False, compare=False
    )
    enqueue_result: RelayMEMSLPDurableEnqueueResult | None = field(
        default=None, repr=False, compare=False
    )
    source_retention_result: RelayMEMSLPSourceRegistryResult | None = field(
        default=None, repr=False, compare=False
    )

    def to_runtime_dict(self) -> dict[str, object]:
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
            "projection": self.to_log_dict(),
        }

    def to_log_dict(self) -> dict[str, object]:
        return project_relaymem_slp_runtime_enqueue(self).to_log_dict()


def apply_relaymem_slp_runtime_enqueue(
    finalized_turn_source_result: object,
    *,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None,
    queue_root: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
    prepared_result: RelayMEMSLPRuntimeEnqueueResult | None = None,
) -> RelayMEMSLPRuntimeEnqueueResult:
    """Compose exact finalized source -> A1 -> A2 -> B1 -> B2 -> registry."""

    enabled_value, enabled_errors = strict_bool(enabled, "enabled_invalid")
    dry_run_value, dry_run_errors = strict_bool(
        dry_run_only, "dry_run_only_invalid"
    )
    apply_value, apply_errors = strict_bool(apply_enabled, "apply_enabled_invalid")
    gate_reasons = dedupe((*enabled_errors, *dry_run_errors, *apply_errors))
    if gate_reasons:
        return _result(
            "invalid_input", enabled_value, dry_run_value, apply_value,
            failure_stage="gate", blocked_reasons=gate_reasons,
        )
    if not enabled_value:
        return _result("disabled", False, dry_run_value, apply_value)
    if dry_run_value and apply_value:
        return _result(
            "blocked", True, True, True,
            failure_stage="gate", blocked_reasons=("apply_enabled_in_dry_run",),
        )
    if not dry_run_value and not apply_value:
        return _result(
            "blocked", True, False, False,
            failure_stage="gate", blocked_reasons=("apply_gate_incomplete",),
        )

    preparation = (
        _validate_prepared_runtime_enqueue(
            prepared_result, finalized_turn_source_result
        )
        if prepared_result is not None
        else prepare_relaymem_slp_runtime_enqueue(finalized_turn_source_result)
    )
    if preparation.status != "dry_run_ready":
        return replace_runtime_enqueue_gates(
            preparation,
            enabled=True,
            dry_run_only=dry_run_value,
            apply_enabled=apply_value,
        )

    source_result = preparation.finalized_turn_source_result
    source = source_result.source if source_result is not None else None
    dispatch = preparation.dispatch_result
    payload = preparation.protected_source_payload
    if source is None or dispatch is None or dispatch.durable_job is None or type(payload) is not dict:
        return _result(
            "blocked", True, dry_run_value, apply_value,
            failure_stage="dispatch",
            blocked_reasons=("runtime_enqueue_preparation_invalid",),
            finalized_turn_source_result=source_result,
            admission_result=preparation.admission_result,
            handoff_result=preparation.handoff_result,
            dispatch_result=dispatch,
        )

    scope = RelayMEMSLPPrimaryWorkerSourceScope()
    if dry_run_value:
        return replace_runtime_enqueue_gates(
            preparation,
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
            source_scope=scope,
        )

    if type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        scope.close()
        return _result(
            "source_retention_failed", True, False, True,
            failure_stage="source_retention",
            blocked_reasons=("exact_source_registry_required",),
            finalized_turn_source_result=source_result,
            admission_result=preparation.admission_result,
            handoff_result=preparation.handoff_result,
            dispatch_result=dispatch,
            protected_source_payload=payload,
        )

    enqueue = enqueue_relaymem_slp_durable_job(
        dispatch,
        queue_root=queue_root,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    if enqueue.status not in {"enqueued_new", "duplicate_existing"}:
        scope.close()
        return _result(
            "enqueue_failed", True, False, True,
            failure_stage="enqueue",
            blocked_reasons=enqueue.blocked_reasons or ("durable_enqueue_failed",),
            finalized_turn_source_result=source_result,
            admission_result=preparation.admission_result,
            handoff_result=preparation.handoff_result,
            dispatch_result=dispatch,
            protected_source_payload=payload,
            enqueue_result=enqueue,
        )
    if type(enqueue.durable_record) is not dict:
        scope.close()
        return _result(
            "source_retention_failed", True, False, True,
            failure_stage="source_retention",
            blocked_reasons=("durable_enqueue_record_unavailable",),
            finalized_turn_source_result=source_result,
            admission_result=preparation.admission_result,
            handoff_result=preparation.handoff_result,
            dispatch_result=dispatch,
            protected_source_payload=payload,
            enqueue_result=enqueue,
        )

    retention = registry.publish(
        source_payload=payload,
        durable_record=enqueue.durable_record,
        request_scope=scope,
        character_id=source.character_id,
    )
    if retention.status not in {"published_new", "duplicate_existing"}:
        scope.close()
        return _result(
            "source_retention_failed", True, False, True,
            failure_stage="source_retention",
            blocked_reasons=retention.blocked_reasons or (
                "protected_source_retention_failed",
            ),
            finalized_turn_source_result=source_result,
            admission_result=preparation.admission_result,
            handoff_result=preparation.handoff_result,
            dispatch_result=dispatch,
            protected_source_payload=payload,
            enqueue_result=enqueue,
            source_retention_result=retention,
        )
    if retention.status == "duplicate_existing":
        scope.close()

    return _result(
        "enqueued" if enqueue.status == "enqueued_new" else "duplicate_existing",
        True,
        False,
        True,
        finalized_turn_source_result=source_result,
        admission_result=preparation.admission_result,
        handoff_result=preparation.handoff_result,
        dispatch_result=dispatch,
        protected_source_payload=payload,
        source_scope=scope if retention.status == "published_new" else None,
        enqueue_result=enqueue,
        source_retention_result=retention,
    )



def prepare_relaymem_slp_runtime_enqueue(
    finalized_turn_source_result: object,
) -> RelayMEMSLPRuntimeEnqueueResult:
    """Build exact A1/A2/B1 identity without C1-5, B2, registry, or worker I/O."""

    source_result, source, source_errors = _validate_finalized_source(
        finalized_turn_source_result
    )
    if source_result is None or source is None:
        return _result(
            "blocked", True, True, False,
            failure_stage="source_capture", blocked_reasons=source_errors,
            finalized_turn_source_result=(
                finalized_turn_source_result
                if type(finalized_turn_source_result)
                is RelayMEMSLPFinalizedTurnSourceResult
                else None
            ),
        )

    admission = build_relaymem_slp_job_admission_preflight(
        enabled=True,
        dry_run_only=True,
        enqueue_enabled=False,
        trigger_mode="turn_end",
        processing_stage="primary_formation",
        run_id=source.run_id,
        turn_index=source.turn_index,
        session_id=source.session_id,
        namespace=source.namespace,
        source_event_kind=source.source_event_kind,
        source_lineage_artifact=source.source_lineage_artifact,
        source_count=source.source_count,
        visible_response_finalized=True,
        runtime_terminal_status="completed",
        persistence_policy_status=source.persistence_policy_status,
    )
    admission_status = admission.get("admission_status")
    if admission_status not in {"admitted_dry_run", "eligible_for_enqueue"}:
        mapped: RuntimeEnqueueStatus = (
            "held" if admission_status == "held"
            else "skipped" if admission_status == "skipped"
            else "blocked"
        )
        return _result(
            mapped, True, True, False,
            failure_stage="admission",
            blocked_reasons=_mapping_reasons(admission),
            finalized_turn_source_result=source_result,
            admission_result=admission,
        )

    handoff = build_relaymem_slp_response_finalization_handoff(
        admission, enabled=True, dry_run_only=True, response_finalized=True
    )
    if handoff.status != "dry_run_candidate" or handoff.candidate is None:
        return _result(
            "blocked", True, True, False,
            failure_stage="handoff",
            blocked_reasons=handoff.blocked_reasons or ("response_handoff_not_ready",),
            finalized_turn_source_result=source_result,
            admission_result=admission,
            handoff_result=handoff,
        )

    dispatch = build_relaymem_slp_dispatch_preflight(
        handoff, enabled=True, dry_run_only=True
    )
    if dispatch.status != "dry_run_ready" or dispatch.durable_job is None:
        return _result(
            "blocked", True, True, False,
            failure_stage="dispatch",
            blocked_reasons=dispatch.blocked_reasons or ("dispatch_preflight_not_ready",),
            finalized_turn_source_result=source_result,
            admission_result=admission,
            handoff_result=handoff,
            dispatch_result=dispatch,
        )

    job = dispatch.durable_job
    payload = source.to_protected_source_payload(
        job_id=job.job_id,
        dispatch_idempotency_key=job.dispatch_idempotency_key,
    )
    return _result(
        "dry_run_ready", True, True, False,
        finalized_turn_source_result=source_result,
        admission_result=admission,
        handoff_result=handoff,
        dispatch_result=dispatch,
        protected_source_payload=payload,
    )


def _validate_prepared_runtime_enqueue(
    prepared_result: object,
    finalized_turn_source_result: object,
) -> RelayMEMSLPRuntimeEnqueueResult:
    if type(prepared_result) is not RelayMEMSLPRuntimeEnqueueResult:
        return _result(
            "blocked", True, True, False,
            failure_stage="dispatch",
            blocked_reasons=("exact_runtime_enqueue_preparation_required",),
        )
    if prepared_result.source_scope is not None:
        return _result(
            "blocked", True, True, False,
            failure_stage="dispatch",
            blocked_reasons=("runtime_enqueue_preparation_scope_forbidden",),
        )
    if prepared_result.finalized_turn_source_result is not finalized_turn_source_result:
        return _result(
            "blocked", True, True, False,
            failure_stage="dispatch",
            blocked_reasons=("runtime_enqueue_preparation_source_mismatch",),
        )
    if prepared_result.status != "dry_run_ready":
        return prepared_result
    if (
        prepared_result.dispatch_result is None
        or prepared_result.dispatch_result.durable_job is None
        or type(prepared_result.protected_source_payload) is not dict
    ):
        return _result(
            "blocked", True, True, False,
            failure_stage="dispatch",
            blocked_reasons=("runtime_enqueue_preparation_invalid",),
            finalized_turn_source_result=prepared_result.finalized_turn_source_result,
            admission_result=prepared_result.admission_result,
            handoff_result=prepared_result.handoff_result,
            dispatch_result=prepared_result.dispatch_result,
        )
    return prepared_result


def replace_runtime_enqueue_gates(
    result: RelayMEMSLPRuntimeEnqueueResult,
    *,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    source_scope: RelayMEMSLPPrimaryWorkerSourceScope | None = None,
) -> RelayMEMSLPRuntimeEnqueueResult:
    return RelayMEMSLPRuntimeEnqueueResult(
        status=result.status,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        failure_stage=result.failure_stage,
        blocked_reasons=result.blocked_reasons,
        finalized_turn_source_result=result.finalized_turn_source_result,
        admission_result=result.admission_result,
        handoff_result=result.handoff_result,
        dispatch_result=result.dispatch_result,
        protected_source_payload=result.protected_source_payload,
        source_scope=source_scope,
        enqueue_result=result.enqueue_result,
        source_retention_result=result.source_retention_result,
    )

def build_relaymem_slp_runtime_enqueue_failure_result(
    reason_id: str = "runtime_enqueue_background_failed",
) -> RelayMEMSLPRuntimeEnqueueResult:
    """Return one bounded failure without retaining exception or content text."""

    safe_reason = (
        reason_id
        if type(reason_id) is str and reason_id and len(reason_id) <= 128
        else "runtime_enqueue_background_failed"
    )
    return _result(
        "enqueue_failed", True, False, True,
        failure_stage="enqueue", blocked_reasons=(safe_reason,),
    )


def project_relaymem_slp_runtime_enqueue(
    result: RelayMEMSLPRuntimeEnqueueResult,
) -> RelayMEMSLPRuntimeEnqueueProjection:
    source_result = result.finalized_turn_source_result
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
        finalized_turn_source_ready=bool(
            source_result is not None and source_result.source_ready
        ),
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
            "invalid_input", "blocked", "enqueue_failed", "source_retention_failed"
        },
        failure_stage=result.failure_stage,
        blocked_reason_ids=result.blocked_reasons,
    )


def build_relaymem_slp_runtime_enqueue_node_result(
    result: RelayMEMSLPRuntimeEnqueueResult,
) -> PipelineNodeResult:
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


def _validate_finalized_source(
    value: object,
) -> tuple[
    RelayMEMSLPFinalizedTurnSourceResult | None,
    RelayMEMSLPFinalizedTurnSource | None,
    tuple[str, ...],
]:
    if type(value) is not RelayMEMSLPFinalizedTurnSourceResult:
        return None, None, ("exact_finalized_turn_source_result_required",)
    if type(value.source) is not RelayMEMSLPFinalizedTurnSource:
        return value, None, value.blocked_reasons or ("finalized_turn_source_not_ready",)
    if value.status != "ready" or value.source_ready is not True:
        return value, None, value.blocked_reasons or ("finalized_turn_source_not_ready",)
    source = value.source
    if source.schema_version != "relaymem.slp_finalized_turn_source.v0":
        return value, None, ("finalized_turn_source_schema_mismatch",)
    return value, source, ()


def _mapping_reasons(value: dict[str, object]) -> tuple[str, ...]:
    reasons = value.get("blocked_reasons")
    if type(reasons) is list:
        return dedupe(tuple(item for item in reasons if type(item) is str))
    return ()


def _result(
    status: RuntimeEnqueueStatus,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    *,
    failure_stage: FailureStage = "none",
    blocked_reasons: Sequence[str] = (),
    finalized_turn_source_result: RelayMEMSLPFinalizedTurnSourceResult | None = None,
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
        finalized_turn_source_result=finalized_turn_source_result,
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
    "prepare_relaymem_slp_runtime_enqueue",
    "build_relaymem_slp_runtime_enqueue_failure_result",
    "build_relaymem_slp_runtime_enqueue_node_result",
    "project_relaymem_slp_runtime_enqueue",
]
