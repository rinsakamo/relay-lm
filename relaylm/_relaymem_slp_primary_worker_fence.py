"""Canonical B3 lease fences for the Phase 6-C1-2 worker."""
from __future__ import annotations

import re

from .relaymem_primary_pipeline import RelayMEMPrimaryPipelineCheckpointResult
from .relaymem_slp_queue_record import DURABLE_JOB_SCHEMA, dedupe, validate_record_mapping
from .relaymem_slp_queue_state import (
    RelayMEMSLPQueueStateTransitionResult,
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)
from ._relaymem_slp_primary_worker_types import (
    CheckpointName,
    RelayMEMSLPPrimaryWorkerRequest,
)


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


_REASON_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")


def _reason_ids(values: object) -> tuple[str, ...]:
    output: list[str] = []
    try:
        iterator = iter(values)  # type: ignore[arg-type]
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
        if len(output) >= 32:
            break
    return dedupe(output)


__all__ = ["_CheckpointCoordinator", "_check_active_claim", "_exact_claimed_record"]
