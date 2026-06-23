"""Strict request and result helpers for the Phase 6-C1-2 worker."""
from __future__ import annotations

import re
from typing import Any

from .relaymem_primary_pipeline import RelayMEMPrimaryPipelineResult
from .relaymem_slp_primary_worker_outcome import RelayMEMSLPPrimaryWorkerOutcome
from .relaymem_slp_primary_worker_source import (
    RelayMEMSLPPrimaryWorkerSource,
    RelayMEMSLPPrimaryWorkerSourceScope,
)
from .relaymem_slp_queue_record import MAX_LEASE_SECONDS, dedupe, parse_timestamp
from .relaymem_slp_queue_state import RelayMEMSLPQueueStateTransitionResult
from ._relaymem_slp_primary_worker_fence import (
    _check_active_claim,
    _exact_claimed_record,
)
from ._relaymem_slp_primary_worker_outcome_adapter import _apply_outcome_transition
from ._relaymem_slp_primary_worker_types import (
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    RelayMEMSLPPrimaryWorkerRequest,
    RelayMEMSLPPrimaryWorkerResult,
    WorkerStatus,
)

_REASON_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")
_MAX_REASONS = 32


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
    enabled = (
        request.enabled
        if request is not None and type(request.enabled) is bool
        else False
    )
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
    "_finish_classified_without_pipeline",
    "_reason_ids",
    "_result",
    "_validate_request",
]
