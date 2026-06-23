"""Exact compose-to-classifier adapters for the Phase 6-C1-2 worker."""
from __future__ import annotations

from typing import Any

from .relaymem_primary_pipeline import RelayMEMPrimaryPipelineResult
from .relaymem_slp_primary_worker_outcome import (
    RelayMEMSLPPrimaryPageWriteOutcome,
    RelayMEMSLPPrimaryPolicyOutcome,
    RelayMEMSLPPrimaryReconciliationOutcome,
    RelayMEMSLPPrimaryRecoveryAuditOutcome,
    RelayMEMSLPPrimaryWorkerOutcome,
    classify_relaymem_slp_primary_worker_outcome,
)
from .relaymem_slp_queue_state import (
    RelayMEMSLPQueueStateTransitionResult,
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)


def _classify_pipeline(
    pipeline: RelayMEMPrimaryPipelineResult,
) -> RelayMEMSLPPrimaryWorkerOutcome:
    policy_stage = pipeline.last_stage in {
        "m3a_formation", "m3b_write_preflight"
    }
    if (
        pipeline.status in {"held", "blocked"}
        and policy_stage
        and pipeline.m3e_result is None
        and pipeline.m3g_result is None
    ):
        policy = RelayMEMSLPPrimaryPolicyOutcome(
            schema_version="relaymem.slp_primary_worker_policy_outcome.v0",
            status="held" if pipeline.status == "held" else "blocked",
            reason_id=(
                pipeline.reason_ids[0]
                if pipeline.reason_ids
                else "primary_memory_policy_blocked"
            ),
        )
        return classify_relaymem_slp_primary_worker_outcome(
            m3e_result=None,
            m3g_result=None,
            m3h_result=None,
            policy_outcome=policy,
        )
    return classify_relaymem_slp_primary_worker_outcome(
        m3e_result=_m3e_snapshot(pipeline.m3e_result),
        m3g_result=_m3g_snapshot(pipeline.m3g_result),
        m3h_result=_m3h_snapshot(pipeline.m3h_result),
    )


def _m3e_snapshot(
    value: dict[str, Any] | None,
) -> RelayMEMSLPPrimaryPageWriteOutcome | None:
    if type(value) is not dict:
        return None
    try:
        return RelayMEMSLPPrimaryPageWriteOutcome(
            schema_version=value["schema_version"],
            status=value["status"],
            handoff_valid=value["handoff_valid"],
            writes_memory=value["writes_memory"],
            page_applied=(
                value["page_applied"]
                or (
                    value["status"] == "already_applied"
                    and value["idempotent_noop"] is True
                )
            ),
            idempotent_noop=value["idempotent_noop"],
            durability_confirmed=value["durability_confirmed"],
            cleanup_complete=value["cleanup_complete"],
            blocked_reason_ids=tuple(value["blocked_reasons"]),
        )
    except (KeyError, TypeError):
        return None


def _m3g_snapshot(
    value: dict[str, Any] | None,
) -> RelayMEMSLPPrimaryReconciliationOutcome | None:
    if type(value) is not dict:
        return None
    try:
        return RelayMEMSLPPrimaryReconciliationOutcome(
            schema_version=value["schema_version"],
            status=value["status"],
            plan_valid=value["plan_valid"],
            page_verified=value["page_verified"],
            writes_memory=value["writes_memory"],
            index_reconciled=value["index_reconciled"],
            log_reconciled=value["log_reconciled"],
            index_updated=value["index_updated"],
            log_updated=value["log_updated"],
            index_idempotent_noop=value["index_idempotent_noop"],
            log_idempotent_noop=value["log_idempotent_noop"],
            durability_confirmed=value["durability_confirmed"],
            cleanup_complete=value["cleanup_complete"],
            blocked_reason_ids=tuple(value["blocked_reasons"]),
        )
    except (KeyError, TypeError):
        return None


def _m3h_snapshot(
    value: dict[str, Any] | None,
) -> RelayMEMSLPPrimaryRecoveryAuditOutcome | None:
    if type(value) is not dict or type(value.get("projection")) is not dict:
        return None
    projection = value["projection"]
    try:
        return RelayMEMSLPPrimaryRecoveryAuditOutcome(
            schema_version=value["schema_version"],
            status=value["status"],
            receipt_valid=value["receipt_valid"],
            source_status=value["source_status"],
            store_state=value["store_state"],
            page_verified=projection["page_verified"],
            index_state=projection["index_state"],
            log_state=projection["log_state"],
            cleanup_artifacts_present=projection["cleanup_artifacts_present"],
            recovery_classification=value["recovery_classification"],
            blocked_reason_ids=tuple(value["blocked_reasons"]),
        )
    except (KeyError, TypeError):
        return None


def _apply_outcome_transition(
    outcome: RelayMEMSLPPrimaryWorkerOutcome,
    *,
    current_record: dict[str, object],
    queue_root: str,
    retry_not_before: str | None,
) -> RelayMEMSLPQueueStateTransitionResult:
    common = {
        "job_id": str(current_record["job_id"]),
        "dispatch_idempotency_key": str(
            current_record["dispatch_idempotency_key"]
        ),
        "expected_record_revision": int(current_record["record_revision"]),
        "expected_state": "claimed",
        "claim_owner": str(current_record["claim_owner"]),
        "claim_generation": int(current_record["claim_generation"]),
        "lease_token": str(current_record["lease_token"]),
    }
    if outcome.transition_kind == "retry_release":
        request = RelayMEMSLPQueueTransitionRequest(
            transition_kind="retry_release",
            **common,
            retry_class=outcome.retry_class,
            retry_not_before=retry_not_before,
            failure_class=outcome.failure_class,
        )
    else:
        request = RelayMEMSLPQueueTransitionRequest(
            transition_kind="commit_terminal",
            **common,
            terminal_state=outcome.terminal_state,
            failure_class=outcome.failure_class,
            terminal_reason_id=outcome.terminal_reason_id,
        )
    try:
        return transition_relaymem_slp_queue_state(
            request,
            queue_root=queue_root,
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
    except Exception:
        return RelayMEMSLPQueueStateTransitionResult(
            status="write_failed",
            transition_kind=request.transition_kind,
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
            queue_io_performed=False,
            transition_attempted=True,
            transition_applied=False,
            durability_confirmed=False,
            previous_state="claimed",
            proposed_state=None,
            durable_record=None,
            blocked_reasons=("primary_worker_transition_execution_failed",),
        )


def _side_effect_started(pipeline: RelayMEMPrimaryPipelineResult) -> bool:
    return pipeline.m3e_result is not None


__all__ = [
    "_apply_outcome_transition",
    "_classify_pipeline",
    "_side_effect_started",
    "classify_relaymem_slp_primary_worker_outcome",
]
