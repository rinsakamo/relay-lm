"""Exact compose-to-classifier and bounded retry adapters for Phase 6-C1-2."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
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
from .relaymem_slp_queue_record import format_timestamp, parse_timestamp
from .relaymem_slp_queue_state import (
    RelayMEMSLPQueueStateTransitionResult,
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)

MAX_WORKER_ATTEMPTS = 5
_RETRY_BASE_SECONDS = {
    "transient_lock_contention": 5,
    "primary_reconciliation_retry": 20,
}
_RETRY_JITTER_SECONDS = {
    "transient_lock_contention": 5,
    "primary_reconciliation_retry": 10,
}


def _classify_pipeline(
    pipeline: RelayMEMPrimaryPipelineResult,
) -> RelayMEMSLPPrimaryWorkerOutcome:
    policy = _exact_policy_outcome(pipeline)
    if policy is not None:
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


def _exact_policy_outcome(
    pipeline: RelayMEMPrimaryPipelineResult,
) -> RelayMEMSLPPrimaryPolicyOutcome | None:
    """Return a policy outcome only when exact M3a/M3b evidence proves it."""

    if pipeline.status not in {"held", "blocked"}:
        return None
    status: str | None = None
    if pipeline.last_stage == "m3a_formation":
        value = pipeline.m3a_result
        if type(value) is not dict:
            return None
        candidates = value.get("candidates")
        count = value.get("candidate_count")
        if (
            type(candidates) is not list
            or type(count) is not int
            or count != 1
            or len(candidates) != 1
            or type(candidates[0]) is not dict
        ):
            return None
        promotion = candidates[0].get("promotion_policy")
        safety = candidates[0].get("safety_scope")
        if promotion == "review_required" or safety == "held_for_review":
            status = "held"
        elif promotion != "free_to_update" or safety != "ordinary_memory":
            status = "blocked"
    elif pipeline.last_stage == "m3b_write_preflight":
        value = pipeline.m3b_result
        if type(value) is not dict:
            return None
        operations = value.get("operations")
        count = value.get("operation_count")
        if (
            type(operations) is not list
            or type(count) is not int
            or count != 1
            or len(operations) != 1
            or type(operations[0]) is not dict
        ):
            return None
        preflight = operations[0].get("preflight_status")
        if preflight == "held":
            status = "held"
        elif preflight != "eligible":
            status = "blocked"
    if status is None:
        return None
    return RelayMEMSLPPrimaryPolicyOutcome(
        schema_version="relaymem.slp_primary_worker_policy_outcome.v0",
        status=status,
        reason_id=(
            pipeline.reason_ids[0]
            if pipeline.reason_ids
            else (
                "primary_memory_candidate_held_for_review"
                if status == "held"
                else "primary_memory_policy_blocked"
            )
        ),
    )


def _bounded_outcome_and_retry(
    outcome: RelayMEMSLPPrimaryWorkerOutcome,
    current_record: dict[str, object],
) -> tuple[RelayMEMSLPPrimaryWorkerOutcome, str | None]:
    """Apply finite attempts and derive a future bounded retry timestamp."""

    if outcome.transition_kind != "retry_release":
        return outcome, None
    attempt_count = current_record.get("attempt_count")
    if type(attempt_count) is not int or attempt_count >= MAX_WORKER_ATTEMPTS:
        return (
            RelayMEMSLPPrimaryWorkerOutcome(
                status="classified",
                transition_kind="commit_failed",
                terminal_state="failed",
                retry_class="none",
                failure_class=outcome.failure_class,
                terminal_reason_id="primary_mem_retry_attempt_limit_reached",
                retryable=False,
                terminal=True,
                policy_held=False,
                manual_confirmation_required=False,
                recovery_isolation_required=False,
                durable_success_verified=False,
                blocked_reason_ids=(),
            ),
            None,
        )
    base = _RETRY_BASE_SECONDS[outcome.retry_class]
    spread = _RETRY_JITTER_SECONDS[outcome.retry_class]
    seed = "\0".join(
        (
            str(current_record["job_id"]),
            str(current_record["claim_generation"]),
            outcome.retry_class,
        )
    ).encode("utf-8")
    jitter = int.from_bytes(hashlib.sha256(seed).digest()[:4], "big") % spread
    updated = parse_timestamp(current_record.get("updated_at"))
    now = _now_utc()
    if updated is not None and updated > now:
        now = updated
    return outcome, format_timestamp(now + timedelta(seconds=base + jitter))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


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
        "dispatch_idempotency_key": str(current_record["dispatch_idempotency_key"]),
        "expected_record_revision": int(current_record["record_revision"]),
        "expected_state": "claimed",
        "claim_owner": str(current_record["claim_owner"]),
        "claim_generation": int(current_record["claim_generation"]),
        "lease_token": str(current_record["lease_token"]),
    }
    if outcome.transition_kind == "retry_release":
        if retry_not_before is None:
            raise ValueError("bounded retry timestamp required")
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
    "MAX_WORKER_ATTEMPTS",
    "_apply_outcome_transition",
    "_bounded_outcome_and_retry",
    "_classify_pipeline",
    "_side_effect_started",
    "classify_relaymem_slp_primary_worker_outcome",
]
