"""Phase 6-C1-2 one already-claimed Primary MEM job worker.

This module executes exactly one caller-selected canonical B3 claimed record.  It
never scans the queue, allocates a turn index, reconstructs protected content,
or depends on the request-runtime capture registry.  The canonical C1-0 source
is consumed once by RelayMEM compose after an active-lease checkpoint.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from .pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from .relaymem_primary_pipeline import (
    REQUEST_SCHEMA as PRIMARY_PIPELINE_REQUEST_SCHEMA,
    RelayMEMPrimaryPipelineCheckpointResult,
    RelayMEMPrimaryPipelineRequest,
    RelayMEMPrimaryPipelineResult,
    execute_relaymem_primary_pipeline,
    project_relaymem_primary_pipeline,
)
from .relaymem_slp_primary_worker_outcome import (
    RelayMEMSLPPrimaryPageWriteOutcome,
    RelayMEMSLPPrimaryPolicyOutcome,
    RelayMEMSLPPrimaryReconciliationOutcome,
    RelayMEMSLPPrimaryRecoveryAuditOutcome,
    RelayMEMSLPPrimarySourceCorrelationOutcome,
    RelayMEMSLPPrimaryWorkerOutcome,
    classify_relaymem_slp_primary_worker_outcome,
)
from .relaymem_slp_primary_worker_source import (
    RelayMEMSLPPrimaryWorkerSource,
    RelayMEMSLPPrimaryWorkerSourceScope,
    validate_relaymem_slp_primary_worker_source,
)
from .relaymem_slp_queue_record import (
    DURABLE_JOB_SCHEMA,
    MAX_LEASE_SECONDS,
    dedupe,
    parse_timestamp,
    validate_record_mapping,
)
from .relaymem_slp_queue_state import (
    RelayMEMSLPQueueStateTransitionResult,
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)

REQUEST_SCHEMA = "relaymem.slp_primary_worker_request.v0"
RESULT_SCHEMA = "relaymem.slp_primary_worker_result.v0"
PROJECTION_SCHEMA = "relaymem.slp_primary_worker_projection.v0"

WorkerStatus = Literal[
    "disabled",
    "dry_run_ready",
    "invalid_input",
    "lease_invalid_before_source",
    "source_invalid",
    "pipeline_blocked",
    "pipeline_held",
    "lease_lost_before_m3e",
    "lease_lost_before_m3g",
    "lease_lost_before_transition",
    "retry_released",
    "terminal_succeeded",
    "terminal_failed",
    "transition_failed",
]
CheckpointName = Literal[
    "before_source_consumption",
    "before_m3e_page_writer",
    "before_m3g_reconciliation_apply",
]

_REASON_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")
_MAX_REASONS = 32
_CORRELATION_REASONS = frozenset(
    {
        "worker_source_job_id_mismatch",
        "worker_source_dispatch_key_mismatch",
        "worker_source_run_id_mismatch",
        "worker_source_turn_index_mismatch",
        "worker_source_session_id_mismatch",
        "worker_source_namespace_mismatch",
        "worker_source_event_kind_mismatch",
        "worker_source_count_claim_mismatch",
        "worker_source_lineage_mismatch",
    }
)


@dataclass(frozen=True, repr=False)
class RelayMEMSLPPrimaryWorkerRequest:
    """Exact runtime-private request for one already-claimed B3 job."""

    schema_version: str
    runtime_private: bool
    content_included: bool
    claimed_record: dict[str, object] = field(repr=False)
    worker_source: RelayMEMSLPPrimaryWorkerSource = field(repr=False)
    request_scope: RelayMEMSLPPrimaryWorkerSourceScope = field(repr=False)
    queue_root: str = field(repr=False)
    store_root: str = field(repr=False)
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    lease_duration_seconds: int
    retry_not_before: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class RelayMEMSLPPrimaryWorkerProjection:
    """Deterministic content-free worker projection."""

    status: WorkerStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    initial_lease_valid: bool
    source_checkpoint_passed: bool
    m3e_checkpoint_passed: bool
    m3g_checkpoint_passed: bool
    final_checkpoint_passed: bool
    lease_renewed: bool
    lease_renewal_count: int
    pipeline_status: str | None
    outcome_transition_kind: str | None
    queue_transition_performed: bool
    retryable: bool
    terminal: bool
    succeeded: bool
    failed: bool
    reason_ids: tuple[str, ...]

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_messages_included": False,
            "governed_title_included": False,
            "governed_summary_included": False,
            "source_body_included": False,
            "page_content_included": False,
            "index_content_included": False,
            "log_content_included": False,
            "queue_root_included": False,
            "store_root_included": False,
            "queue_filename_included": False,
            "namespace_included": False,
            "runtime_identifiers_included": False,
            "lineage_fingerprint_included": False,
            "dispatch_idempotency_key_included": False,
            "memory_idempotency_key_included": False,
            "claim_owner_included": False,
            "lease_token_included": False,
            "record_revision_included": False,
            "claim_generation_included": False,
            "timestamps_included": False,
            "retry_timestamp_included": False,
            "exception_text_included": False,
            "private_pipeline_result_included": False,
            "private_outcome_result_included": False,
            "private_queue_result_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "initial_lease_valid": self.initial_lease_valid,
            "source_checkpoint_passed": self.source_checkpoint_passed,
            "m3e_checkpoint_passed": self.m3e_checkpoint_passed,
            "m3g_checkpoint_passed": self.m3g_checkpoint_passed,
            "final_checkpoint_passed": self.final_checkpoint_passed,
            "lease_renewed": self.lease_renewed,
            "lease_renewal_count": self.lease_renewal_count,
            "pipeline_status": self.pipeline_status,
            "outcome_transition_kind": self.outcome_transition_kind,
            "queue_transition_performed": self.queue_transition_performed,
            "retryable": self.retryable,
            "terminal": self.terminal,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "reason_ids": list(self.reason_ids),
        }


@dataclass(frozen=True, repr=False)
class RelayMEMSLPPrimaryWorkerResult:
    """Runtime-private execution ledger for one already-claimed job."""

    schema_version: str
    status: WorkerStatus
    runtime_private: bool
    content_included: bool
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    initial_claim_valid: bool
    source_checkpoint_passed: bool
    m3e_checkpoint_passed: bool
    m3g_checkpoint_passed: bool
    final_checkpoint_passed: bool
    lease_renewal_count: int
    pipeline_result: RelayMEMPrimaryPipelineResult | None = field(
        default=None, repr=False
    )
    outcome_result: RelayMEMSLPPrimaryWorkerOutcome | None = field(
        default=None, repr=False
    )
    queue_transition_result: RelayMEMSLPQueueStateTransitionResult | None = field(
        default=None, repr=False
    )
    side_effect_started: bool = False
    queue_transition_performed: bool = False
    reason_ids: tuple[str, ...] = ()

    def to_log_dict(self) -> dict[str, object]:
        return project_relaymem_slp_primary_worker(self).to_log_dict()


class _CheckpointCoordinator:
    """Mutable claim fence retained only during one worker invocation."""

    def __init__(self, request: RelayMEMSLPPrimaryWorkerRequest) -> None:
        self.request = request
        self.current_record = dict(request.claimed_record)
        self.source_checkpoint_passed = False
        self.m3e_checkpoint_passed = False
        self.m3g_checkpoint_passed = False
        self.denied_at: CheckpointName | None = None
        self.reason_ids: tuple[str, ...] = ()
        self.lease_renewal_count = 0

    def __call__(
        self, checkpoint_name: CheckpointName
    ) -> RelayMEMPrimaryPipelineCheckpointResult:
        if checkpoint_name not in {
            "before_source_consumption",
            "before_m3e_page_writer",
            "before_m3g_reconciliation_apply",
        }:
            self.reason_ids = ("primary_worker_checkpoint_name_invalid",)
            return RelayMEMPrimaryPipelineCheckpointResult(False, self.reason_ids)

        renew = (
            not self.request.dry_run_only
            and checkpoint_name
            in {"before_m3e_page_writer", "before_m3g_reconciliation_apply"}
        )
        allowed, transition, reasons = _check_active_claim(
            self.current_record,
            queue_root=self.request.queue_root,
            lease_duration_seconds=self.request.lease_duration_seconds,
            renew=renew,
        )
        if not allowed:
            self.denied_at = checkpoint_name
            self.reason_ids = reasons
            return RelayMEMPrimaryPipelineCheckpointResult(False, reasons)

        if renew:
            assert transition is not None
            record = transition.durable_record
            if not _exact_claimed_record(record):
                self.denied_at = checkpoint_name
                self.reason_ids = ("primary_worker_renewed_record_invalid",)
                return RelayMEMPrimaryPipelineCheckpointResult(
                    False, self.reason_ids
                )
            self.current_record = dict(record)
            self.lease_renewal_count += 1

        if checkpoint_name == "before_source_consumption":
            self.source_checkpoint_passed = True
        elif checkpoint_name == "before_m3e_page_writer":
            self.m3e_checkpoint_passed = True
        else:
            self.m3g_checkpoint_passed = True
        return RelayMEMPrimaryPipelineCheckpointResult(True, ())


def execute_relaymem_slp_primary_worker(
    request: object,
) -> RelayMEMSLPPrimaryWorkerResult:
    """Execute one exact already-claimed Primary MEM job under B3 fences."""

    exact, request_reasons = _validate_request(request)
    if exact is None:
        return _result(
            status="invalid_input",
            request=request if type(request) is RelayMEMSLPPrimaryWorkerRequest else None,
            reasons=request_reasons,
        )
    if not exact.enabled:
        return _result(status="disabled", request=exact)

    initial_allowed, _, initial_reasons = _check_active_claim(
        exact.claimed_record,
        queue_root=exact.queue_root,
        lease_duration_seconds=exact.lease_duration_seconds,
        renew=False,
    )
    if not initial_allowed:
        return _result(
            status="lease_invalid_before_source",
            request=exact,
            reasons=initial_reasons,
        )

    source, source_reasons = validate_relaymem_slp_primary_worker_source(
        exact.worker_source,
        claimed_record=exact.claimed_record,
        request_scope=exact.request_scope,
    )
    if source is None:
        if (
            not exact.dry_run_only
            and source_reasons
            and all(reason in _CORRELATION_REASONS for reason in source_reasons)
        ):
            outcome = classify_relaymem_slp_primary_worker_outcome(
                m3e_result=None,
                m3g_result=None,
                m3h_result=None,
                source_correlation=RelayMEMSLPPrimarySourceCorrelationOutcome(
                    schema_version="relaymem.slp_primary_worker_source_correlation.v0",
                    status="invalid",
                ),
            )
            return _finish_classified_without_pipeline(
                exact, outcome, source_reasons
            )
        return _result(
            status="source_invalid",
            request=exact,
            initial_claim_valid=True,
            reasons=source_reasons,
        )
    assert source is exact.worker_source

    coordinator = _CheckpointCoordinator(exact)
    pipeline_request = RelayMEMPrimaryPipelineRequest(
        schema_version=PRIMARY_PIPELINE_REQUEST_SCHEMA,
        runtime_private=True,
        content_included=True,
        worker_source=source,
        claimed_record=dict(exact.claimed_record),
        request_scope=exact.request_scope,
        store_root=exact.store_root,
        enabled=True,
        dry_run_only=exact.dry_run_only,
        apply_enabled=exact.apply_enabled,
    )
    try:
        pipeline = execute_relaymem_primary_pipeline(
            pipeline_request, checkpoint=coordinator
        )
        project_relaymem_primary_pipeline(pipeline)
    except Exception:
        return _result(
            status="pipeline_blocked",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            reasons=("primary_worker_pipeline_execution_failed",),
        )

    if coordinator.denied_at is not None:
        status: WorkerStatus = {
            "before_source_consumption": "lease_invalid_before_source",
            "before_m3e_page_writer": "lease_lost_before_m3e",
            "before_m3g_reconciliation_apply": "lease_lost_before_m3g",
        }[coordinator.denied_at]
        return _result(
            status=status,
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            side_effect_started=_side_effect_started(pipeline),
            reasons=coordinator.reason_ids,
        )

    if exact.dry_run_only:
        status = "dry_run_ready" if pipeline.status == "dry_run_ready" else (
            "pipeline_held" if pipeline.status == "held" else "pipeline_blocked"
        )
        return _result(
            status=status,
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            side_effect_started=False,
            reasons=pipeline.reason_ids,
        )

    try:
        outcome = _classify_pipeline(pipeline)
    except Exception:
        return _result(
            status="pipeline_blocked",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            side_effect_started=_side_effect_started(pipeline),
            reasons=("primary_worker_outcome_classifier_failed",),
        )
    if type(outcome) is not RelayMEMSLPPrimaryWorkerOutcome:
        return _result(
            status="pipeline_blocked",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            side_effect_started=_side_effect_started(pipeline),
            reasons=("exact_primary_worker_outcome_required",),
        )
    if outcome.status != "classified" or outcome.transition_kind == "blocked_invalid_input":
        return _result(
            status="pipeline_blocked",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            outcome_result=outcome,
            side_effect_started=_side_effect_started(pipeline),
            reasons=(*pipeline.reason_ids, *outcome.blocked_reason_ids),
        )

    final_allowed, _, final_reasons = _check_active_claim(
        coordinator.current_record,
        queue_root=exact.queue_root,
        lease_duration_seconds=exact.lease_duration_seconds,
        renew=False,
    )
    if not final_allowed:
        return _result(
            status="lease_lost_before_transition",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            final_checkpoint_passed=False,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            outcome_result=outcome,
            side_effect_started=_side_effect_started(pipeline),
            reasons=final_reasons,
        )

    transition = _apply_outcome_transition(
        outcome,
        current_record=coordinator.current_record,
        queue_root=exact.queue_root,
        retry_not_before=exact.retry_not_before,
    )
    applied = (
        transition.status == "applied"
        and transition.transition_applied
        and transition.durability_confirmed
    )
    if not applied:
        return _result(
            status="transition_failed",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            final_checkpoint_passed=True,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            outcome_result=outcome,
            queue_transition_result=transition,
            side_effect_started=_side_effect_started(pipeline),
            reasons=transition.blocked_reasons or ("primary_worker_transition_failed",),
        )

    status = {
        "commit_succeeded": "terminal_succeeded",
        "retry_release": "retry_released",
        "commit_failed": "terminal_failed",
    }[outcome.transition_kind]
    return _result(
        status=status,
        request=exact,
        initial_claim_valid=True,
        source_checkpoint_passed=coordinator.source_checkpoint_passed,
        m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
        m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
        final_checkpoint_passed=True,
        lease_renewal_count=coordinator.lease_renewal_count,
        pipeline_result=pipeline,
        outcome_result=outcome,
        queue_transition_result=transition,
        side_effect_started=_side_effect_started(pipeline),
        queue_transition_performed=True,
        reasons=(),
    )


def project_relaymem_slp_primary_worker(
    result: RelayMEMSLPPrimaryWorkerResult,
) -> RelayMEMSLPPrimaryWorkerProjection:
    if type(result) is not RelayMEMSLPPrimaryWorkerResult:
        raise TypeError("exact RelayMEMSLPPrimaryWorkerResult required")
    if (
        result.schema_version != RESULT_SCHEMA
        or result.runtime_private is not True
        or result.content_included is not True
    ):
        raise ValueError("primary worker result envelope invalid")
    if type(result.lease_renewal_count) is not int or result.lease_renewal_count < 0:
        raise ValueError("primary worker renewal count invalid")
    for value in (
        result.enabled,
        result.dry_run_only,
        result.apply_enabled,
        result.initial_claim_valid,
        result.source_checkpoint_passed,
        result.m3e_checkpoint_passed,
        result.m3g_checkpoint_passed,
        result.final_checkpoint_passed,
        result.side_effect_started,
        result.queue_transition_performed,
    ):
        if type(value) is not bool:
            raise ValueError("primary worker result boolean invalid")
    pipeline_status = (
        result.pipeline_result.status
        if type(result.pipeline_result) is RelayMEMPrimaryPipelineResult
        else None
    )
    outcome_kind = (
        result.outcome_result.transition_kind
        if type(result.outcome_result) is RelayMEMSLPPrimaryWorkerOutcome
        else None
    )
    retryable = (
        result.status == "retry_released"
        or (
            type(result.outcome_result) is RelayMEMSLPPrimaryWorkerOutcome
            and result.outcome_result.retryable
        )
    )
    terminal = result.status in {"terminal_succeeded", "terminal_failed"}
    return RelayMEMSLPPrimaryWorkerProjection(
        status=result.status,
        enabled=result.enabled,
        dry_run_only=result.dry_run_only,
        apply_enabled=result.apply_enabled,
        initial_lease_valid=result.initial_claim_valid,
        source_checkpoint_passed=result.source_checkpoint_passed,
        m3e_checkpoint_passed=result.m3e_checkpoint_passed,
        m3g_checkpoint_passed=result.m3g_checkpoint_passed,
        final_checkpoint_passed=result.final_checkpoint_passed,
        lease_renewed=result.lease_renewal_count > 0,
        lease_renewal_count=result.lease_renewal_count,
        pipeline_status=pipeline_status,
        outcome_transition_kind=outcome_kind,
        queue_transition_performed=result.queue_transition_performed,
        retryable=retryable,
        terminal=terminal,
        succeeded=result.status == "terminal_succeeded",
        failed=result.status == "terminal_failed",
        reason_ids=result.reason_ids,
    )


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


def _validate_request(
    value: object,
) -> tuple[RelayMEMSLPPrimaryWorkerRequest | None, tuple[str, ...]]:
    if type(value) is not RelayMEMSLPPrimaryWorkerRequest:
        return None, ("exact_primary_worker_request_required",)
    reasons: list[str] = []
    if value.schema_version != REQUEST_SCHEMA:
        reasons.append("primary_worker_request_schema_mismatch")
    if value.runtime_private is not True:
        reasons.append("primary_worker_request_runtime_private_required")
    if value.content_included is not True:
        reasons.append("primary_worker_request_content_required")
    for name in ("enabled", "dry_run_only", "apply_enabled"):
        if type(getattr(value, name)) is not bool:
            reasons.append(f"primary_worker_request_{name}_invalid")
    mode = (value.enabled, value.dry_run_only, value.apply_enabled)
    if all(type(item) is bool for item in mode) and mode not in {
        (False, True, False),
        (True, True, False),
        (True, False, True),
    }:
        reasons.append("primary_worker_gate_mode_invalid")
    if not _exact_claimed_record(value.claimed_record):
        reasons.append("exact_claimed_record_required")
    if type(value.worker_source) is not RelayMEMSLPPrimaryWorkerSource:
        reasons.append("exact_worker_source_required")
    if type(value.request_scope) is not RelayMEMSLPPrimaryWorkerSourceScope:
        reasons.append("exact_request_scope_required")
    for name in ("queue_root", "store_root"):
        root = getattr(value, name)
        if type(root) is not str or not root or "\x00" in root:
            reasons.append(f"primary_worker_{name}_invalid")
    if (
        type(value.lease_duration_seconds) is not int
        or not 1 <= value.lease_duration_seconds <= MAX_LEASE_SECONDS
    ):
        reasons.append("primary_worker_lease_duration_invalid")
    if value.retry_not_before is not None and parse_timestamp(
        value.retry_not_before
    ) is None:
        reasons.append("primary_worker_retry_not_before_invalid")
    return (value, ()) if not reasons else (None, _reason_ids(reasons))


def _exact_claimed_record(value: object) -> bool:
    return (
        type(value) is dict
        and not validate_record_mapping(value)
        and value.get("schema_version") == DURABLE_JOB_SCHEMA
        and value.get("state") == "claimed"
        and type(value.get("claim_generation")) is int
        and value["claim_generation"] >= 1
        and value.get("attempt_count") == value.get("claim_generation")
        and type(value.get("claim_owner")) is str
        and bool(value["claim_owner"])
        and type(value.get("lease_token")) is str
        and bool(value["lease_token"])
        and value.get("retry_not_before") is None
        and value.get("terminal_reason_id") == ""
    )


def _check_active_claim(
    record: dict[str, object],
    *,
    queue_root: str,
    lease_duration_seconds: int,
    renew: bool,
) -> tuple[
    bool,
    RelayMEMSLPQueueStateTransitionResult | None,
    tuple[str, ...],
]:
    if not _exact_claimed_record(record):
        return False, None, ("exact_claimed_record_required",)
    transition_request = RelayMEMSLPQueueTransitionRequest(
        transition_kind="renew_lease",
        job_id=str(record["job_id"]),
        dispatch_idempotency_key=str(record["dispatch_idempotency_key"]),
        expected_record_revision=int(record["record_revision"]),
        expected_state="claimed",
        claim_owner=str(record["claim_owner"]),
        claim_generation=int(record["claim_generation"]),
        lease_token=str(record["lease_token"]),
        lease_duration_seconds=lease_duration_seconds,
    )
    try:
        transition = transition_relaymem_slp_queue_state(
            transition_request,
            queue_root=queue_root,
            enabled=True,
            dry_run_only=not renew,
            apply_enabled=renew,
        )
    except Exception:
        return False, None, ("primary_worker_lease_check_failed",)
    if renew:
        allowed = (
            transition.status == "applied"
            and transition.transition_applied
            and transition.durability_confirmed
        )
    else:
        allowed = (
            transition.status == "dry_run_ready"
            and not transition.transition_applied
        )
    return (
        allowed,
        transition,
        ()
        if allowed
        else _reason_ids(
            transition.blocked_reasons or ("primary_worker_lease_fence_invalid",)
        ),
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
            page_applied=value["page_applied"],
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


def _finish_classified_without_pipeline(
    request: RelayMEMSLPPrimaryWorkerRequest,
    outcome: RelayMEMSLPPrimaryWorkerOutcome,
    source_reasons: tuple[str, ...],
) -> RelayMEMSLPPrimaryWorkerResult:
    final_allowed, _, final_reasons = _check_active_claim(
        request.claimed_record,
        queue_root=request.queue_root,
        lease_duration_seconds=request.lease_duration_seconds,
        renew=False,
    )
    if not final_allowed:
        return _result(
            status="lease_lost_before_transition",
            request=request,
            initial_claim_valid=True,
            outcome_result=outcome,
            reasons=final_reasons,
        )
    transition = _apply_outcome_transition(
        outcome,
        current_record=request.claimed_record,
        queue_root=request.queue_root,
        retry_not_before=request.retry_not_before,
    )
    if not (
        transition.status == "applied"
        and transition.transition_applied
        and transition.durability_confirmed
    ):
        return _result(
            status="transition_failed",
            request=request,
            initial_claim_valid=True,
            final_checkpoint_passed=True,
            outcome_result=outcome,
            queue_transition_result=transition,
            reasons=transition.blocked_reasons,
        )
    return _result(
        status="terminal_failed",
        request=request,
        initial_claim_valid=True,
        final_checkpoint_passed=True,
        outcome_result=outcome,
        queue_transition_result=transition,
        queue_transition_performed=True,
        reasons=source_reasons,
    )


def _side_effect_started(pipeline: RelayMEMPrimaryPipelineResult) -> bool:
    return pipeline.m3e_result is not None


def _result(
    *,
    status: WorkerStatus,
    request: RelayMEMSLPPrimaryWorkerRequest | None,
    initial_claim_valid: bool = False,
    source_checkpoint_passed: bool = False,
    m3e_checkpoint_passed: bool = False,
    m3g_checkpoint_passed: bool = False,
    final_checkpoint_passed: bool = False,
    lease_renewal_count: int = 0,
    pipeline_result: RelayMEMPrimaryPipelineResult | None = None,
    outcome_result: RelayMEMSLPPrimaryWorkerOutcome | None = None,
    queue_transition_result: RelayMEMSLPQueueStateTransitionResult | None = None,
    side_effect_started: bool = False,
    queue_transition_performed: bool = False,
    reasons: tuple[str, ...] | list[str] = (),
) -> RelayMEMSLPPrimaryWorkerResult:
    enabled = request.enabled if request is not None and type(request.enabled) is bool else False
    dry_run = (
        request.dry_run_only
        if request is not None and type(request.dry_run_only) is bool
        else True
    )
    apply_enabled = (
        request.apply_enabled
        if request is not None and type(request.apply_enabled) is bool
        else False
    )
    return RelayMEMSLPPrimaryWorkerResult(
        schema_version=RESULT_SCHEMA,
        status=status,
        runtime_private=True,
        content_included=True,
        enabled=enabled,
        dry_run_only=dry_run,
        apply_enabled=apply_enabled,
        initial_claim_valid=initial_claim_valid,
        source_checkpoint_passed=source_checkpoint_passed,
        m3e_checkpoint_passed=m3e_checkpoint_passed,
        m3g_checkpoint_passed=m3g_checkpoint_passed,
        final_checkpoint_passed=final_checkpoint_passed,
        lease_renewal_count=lease_renewal_count,
        pipeline_result=pipeline_result,
        outcome_result=outcome_result,
        queue_transition_result=queue_transition_result,
        side_effect_started=side_effect_started,
        queue_transition_performed=queue_transition_performed,
        reason_ids=_reason_ids(reasons),
    )


def _reason_ids(values: Any) -> tuple[str, ...]:
    output: list[str] = []
    try:
        iterator = iter(values)
    except TypeError:
        iterator = iter(("invalid_reason_id",))
    for value in iterator:
        reason = (
            value
            if type(value) is str and _REASON_RE.fullmatch(value)
            else "invalid_reason_id"
        )
        if reason not in output:
            output.append(reason)
        if len(output) >= _MAX_REASONS:
            break
    return dedupe(output)


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
