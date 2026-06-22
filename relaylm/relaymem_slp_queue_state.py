"""Phase 6-B3 fenced durable RelaySLP queue state-transition helpers.

The helper mutates only Phase 6-owned queue-control metadata in an existing
``relaymem.slp_durable_job.v0`` record. It never executes a worker, invokes
RelaySLP, writes RelayMEM content, mutates RelaySOUL, or changes a visible
response.
"""
from __future__ import annotations

import os
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relaymem_slp_queue_record import (
    ALL_STATES,
    DISPATCH_KEY_PREFIX,
    DURABLE_JOB_SCHEMA,
    MAX_COUNTER,
    MAX_LEASE_SECONDS,
    MAX_REASON_COUNT,
    MAX_RECORD_BYTES,
    TERMINAL_STATES,
    canonical_json_bytes,
    dedupe,
    derive_dispatch_key,
    derive_job_id,
    format_timestamp,
    has_prefixed_digest,
    is_counter,
    is_token,
    parse_timestamp,
    record_filename,
    strict_bool,
    validate_record_mapping,
)
from relaylm.relaymem_slp_queue_storage import (
    acquire_queue_lock,
    atomic_replace_record,
    open_queue_root,
    read_record_snapshot,
    release_queue_lock,
)

_RESULT_SCHEMA = "relaymem.slp_queue_state_transition.v0"
_REQUEST_SCHEMA = "relaymem.slp_queue_transition_request.v0"
_PROJECTION_SCHEMA = "relaymem.slp_queue_status_projection.v0"
_JOB_ID_PREFIX = "slp-job-v0:"
_TRANSITION_KINDS = frozenset({
    "claim", "renew_lease", "retry_release", "stale_recovery", "commit_terminal"
})

# Test-only compatibility aliases keep B3 smoke fixtures tied to the exact
# production derivation and validation functions rather than duplicated logic.
_DURABLE_JOB_SCHEMA = DURABLE_JOB_SCHEMA
_MAX_RECORD_BYTES = MAX_RECORD_BYTES
_TERMINAL_STATES = TERMINAL_STATES
_canonical_json_bytes = canonical_json_bytes
_derive_dispatch_key = derive_dispatch_key
_derive_job_id = derive_job_id
_record_filename = record_filename
_validate_record_mapping = validate_record_mapping

TransitionKind = Literal[
    "claim", "renew_lease", "retry_release", "stale_recovery", "commit_terminal"
]
TransitionStatus = Literal[
    "disabled", "invalid_input", "blocked", "not_ready", "dry_run_ready",
    "applied", "conflict", "corrupt", "write_failed",
]


@dataclass(frozen=True)
class RelayMEMSLPQueueTransitionRequest:
    """Exact runtime-private request for one B3 queue transition."""

    transition_kind: TransitionKind
    job_id: str
    dispatch_idempotency_key: str
    expected_record_revision: int
    expected_state: str
    claim_owner: str = ""
    claim_generation: int = 0
    lease_token: str = ""
    lease_duration_seconds: int = 0
    retry_class: str = "unclassified"
    retry_not_before: str | None = None
    failure_class: str = "none"
    terminal_state: str = ""
    terminal_reason_id: str = ""

    def to_runtime_dict(self) -> dict[str, object]:
        return {
            "schema_version": _REQUEST_SCHEMA,
            "transition_kind": self.transition_kind,
            "job_id": self.job_id,
            "dispatch_idempotency_key": self.dispatch_idempotency_key,
            "expected_record_revision": self.expected_record_revision,
            "expected_state": self.expected_state,
            "claim_owner": self.claim_owner,
            "claim_generation": self.claim_generation,
            "lease_token": self.lease_token,
            "lease_duration_seconds": self.lease_duration_seconds,
            "retry_class": self.retry_class,
            "retry_not_before": self.retry_not_before,
            "failure_class": self.failure_class,
            "terminal_state": self.terminal_state,
            "terminal_reason_id": self.terminal_reason_id,
        }


@dataclass(frozen=True)
class RelayMEMSLPQueueStateTransitionResult:
    """Runtime-private B3 result with a content-free public projection."""

    status: TransitionStatus
    transition_kind: str | None
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    queue_io_performed: bool
    transition_attempted: bool
    transition_applied: bool
    durability_confirmed: bool
    previous_state: str | None
    proposed_state: str | None
    durable_record: dict[str, object] | None
    blocked_reasons: tuple[str, ...]

    def to_runtime_dict(self) -> dict[str, object]:
        return {
            "schema_version": _RESULT_SCHEMA,
            "helper_only": True,
            "runtime_private_record": True,
            "status": self.status,
            "transition_kind": self.transition_kind,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "queue_io_performed": self.queue_io_performed,
            "transition_attempted": self.transition_attempted,
            "transition_applied": self.transition_applied,
            "durability_confirmed": self.durability_confirmed,
            "previous_state": self.previous_state,
            "proposed_state": self.proposed_state,
            "durable_record": (
                dict(self.durable_record) if self.durable_record is not None else None
            ),
            "worker_invoked": False,
            "invokes_slp": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "blocked_reasons": list(self.blocked_reasons),
        }

    def to_log_dict(self) -> dict[str, object]:
        record = self.durable_record or {}
        state = self.proposed_state or self.previous_state
        return {
            "schema_version": _PROJECTION_SCHEMA,
            "status": self.status,
            "transition_kind": self.transition_kind,
            "queue_state": state,
            "attempt_count": record.get("attempt_count", 0),
            "claim_active": state == "claimed",
            "lease_present": bool(record.get("lease_token")) if record else False,
            "terminal": state in TERMINAL_STATES,
            "retry_class": record.get("retry_class", "unclassified"),
            "failure_class": record.get("failure_class", "none"),
            "transition_attempted": self.transition_attempted,
            "transition_applied": self.transition_applied,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def transition_relaymem_slp_queue_state(
    request: object,
    *,
    queue_root: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> RelayMEMSLPQueueStateTransitionResult:
    """Inspect or atomically apply one fenced durable queue transition."""

    enabled_value, enabled_errors = strict_bool(enabled, "enabled_invalid")
    dry_run_value, dry_run_errors = strict_bool(
        dry_run_only, "dry_run_only_invalid"
    )
    apply_value, apply_errors = strict_bool(apply_enabled, "apply_enabled_invalid")
    gate_errors = dedupe((*enabled_errors, *dry_run_errors, *apply_errors))
    kind = (
        request.transition_kind
        if type(request) is RelayMEMSLPQueueTransitionRequest
        else None
    )
    if gate_errors:
        return _result(
            "invalid_input", kind, enabled_value, dry_run_value, apply_value,
            False, False, False, False, None, None, None, gate_errors,
        )
    if not enabled_value:
        return _result(
            "disabled", kind, False, dry_run_value, apply_value,
            False, False, False, False, None, None, None, (),
        )

    exact_request, request_errors = _validate_request(request)
    if exact_request is None:
        return _result(
            "invalid_input", kind, True, dry_run_value, apply_value,
            False, False, False, False, None, None, None, request_errors,
        )
    apply_requested = not dry_run_value and apply_value
    if not dry_run_value and not apply_value:
        return _result(
            "blocked", exact_request.transition_kind, True, False, False,
            False, False, False, False, None, None, None,
            ("apply_gate_incomplete",),
        )

    root_fd, root_errors = open_queue_root(queue_root)
    if root_fd is None:
        return _result(
            "write_failed", exact_request.transition_kind, True,
            dry_run_value, apply_value, False, apply_requested, False, False,
            None, None, None, root_errors,
        )
    try:
        lock_error = acquire_queue_lock(root_fd, exclusive=apply_requested)
        if lock_error:
            return _result(
                "blocked", exact_request.transition_kind, True,
                dry_run_value, apply_value, True, apply_requested, False, False,
                None, None, None, (lock_error,),
            )
        try:
            return _transition_locked(
                root_fd,
                exact_request,
                dry_run_only=dry_run_value,
                apply_enabled=apply_value,
                apply_requested=apply_requested,
            )
        finally:
            release_queue_lock(root_fd)
    finally:
        os.close(root_fd)


def build_relaymem_slp_queue_state_node_result(
    result: RelayMEMSLPQueueStateTransitionResult,
) -> PipelineNodeResult:
    """Build the content-free B3 node projection."""

    node_status = {
        "disabled": "skipped",
        "invalid_input": "failed",
        "blocked": "blocked",
        "not_ready": "blocked",
        "conflict": "blocked",
        "corrupt": "blocked",
        "write_failed": "failed",
    }.get(result.status, "diagnostic_only")
    return build_pipeline_node_result(
        node_name="relaymem_slp_queue_state",
        status=node_status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=result.to_log_dict(),
        artifacts=[{
            "artifact_name": "relaymem_slp_durable_queue_state",
            "schema_version": DURABLE_JOB_SCHEMA,
            "present": result.durable_record is not None,
            "content_free": True,
            "runtime_private": True,
            "record_omitted": True,
            "dispatch_idempotency_key_included": False,
            "job_id_included": False,
            "claim_owner_included": False,
            "lease_token_included": False,
            "timestamps_included": False,
            "queue_path_included": False,
            "transition_attempted": result.transition_attempted,
            "transition_applied": result.transition_applied,
            "worker_invoked": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
        }],
    )


def _validate_request(
    value: object,
) -> tuple[RelayMEMSLPQueueTransitionRequest | None, tuple[str, ...]]:
    if type(value) is not RelayMEMSLPQueueTransitionRequest:
        return None, ("exact_transition_request_required",)
    request = value
    errors: list[str] = []
    if request.transition_kind not in _TRANSITION_KINDS:
        errors.append("transition_kind_invalid")
    dispatch_valid = has_prefixed_digest(
        request.dispatch_idempotency_key, DISPATCH_KEY_PREFIX
    )
    if not dispatch_valid:
        errors.append("dispatch_idempotency_key_invalid")
    if not has_prefixed_digest(request.job_id, _JOB_ID_PREFIX):
        errors.append("job_id_invalid")
    elif dispatch_valid and request.job_id != derive_job_id(
        request.dispatch_idempotency_key
    ):
        errors.append("job_dispatch_identity_mismatch")
    if not is_counter(request.expected_record_revision):
        errors.append("expected_record_revision_invalid")
    if request.expected_state not in ALL_STATES:
        errors.append("expected_state_invalid")
    if not is_counter(request.claim_generation):
        errors.append("claim_generation_invalid")
    if (
        type(request.lease_duration_seconds) is not int
        or not 0 <= request.lease_duration_seconds <= MAX_LEASE_SECONDS
    ):
        errors.append("lease_duration_seconds_invalid")
    if request.claim_owner and not is_token(request.claim_owner):
        errors.append("claim_owner_invalid")
    if request.lease_token and not is_token(request.lease_token):
        errors.append("lease_token_invalid")
    if not is_token(request.retry_class):
        errors.append("retry_class_invalid")
    if (
        request.retry_not_before is not None
        and parse_timestamp(request.retry_not_before) is None
    ):
        errors.append("retry_not_before_invalid")
    if not is_token(request.failure_class):
        errors.append("failure_class_invalid")
    if (
        request.terminal_state
        and request.terminal_state not in {"succeeded", "failed", "cancelled"}
    ):
        errors.append("terminal_state_invalid")
    if request.terminal_reason_id and not is_token(request.terminal_reason_id):
        errors.append("terminal_reason_id_invalid")
    _validate_request_kind(request, errors)
    return (request, ()) if not errors else (None, dedupe(errors))


def _validate_request_kind(
    request: RelayMEMSLPQueueTransitionRequest,
    errors: list[str],
) -> None:
    kind = request.transition_kind
    if kind == "claim":
        _expect(errors, request.expected_state == "queued", "claim_expected_state_invalid")
        _expect(errors, bool(request.claim_owner), "claim_owner_required")
        _expect(errors, not request.lease_token, "claim_lease_token_must_be_empty")
        _expect(errors, request.lease_duration_seconds > 0, "claim_lease_duration_required")
        _expect_default_classification(request, errors, "claim")
        _expect_empty_terminal(request, errors, "claim")
    elif kind == "renew_lease":
        _expect(errors, request.expected_state == "claimed", "renew_expected_state_invalid")
        _expect(errors, bool(request.claim_owner), "renew_claim_owner_required")
        _expect(errors, bool(request.lease_token), "renew_lease_token_required")
        _expect(errors, request.lease_duration_seconds > 0, "renew_lease_duration_required")
        _expect_default_classification(request, errors, "renew")
        _expect_empty_terminal(request, errors, "renew")
    elif kind == "retry_release":
        _expect(errors, request.expected_state == "claimed", "retry_release_expected_state_invalid")
        _expect(errors, bool(request.claim_owner), "retry_release_claim_owner_required")
        _expect(errors, bool(request.lease_token), "retry_release_lease_token_required")
        _expect(errors, request.lease_duration_seconds == 0, "retry_release_lease_duration_nonzero")
        _expect(errors, request.retry_class != "unclassified", "retry_release_retry_class_required")
        _expect(errors, request.failure_class != "none", "retry_release_failure_class_required")
        _expect_empty_terminal(request, errors, "retry_release")
    elif kind == "stale_recovery":
        _expect(errors, request.expected_state == "claimed", "stale_recovery_expected_state_invalid")
        _expect(errors, bool(request.lease_token), "stale_recovery_lease_token_required")
        _expect(errors, request.lease_duration_seconds == 0, "stale_recovery_lease_duration_nonzero")
        _expect_default_classification(request, errors, "stale_recovery")
        _expect_empty_terminal(request, errors, "stale_recovery")
    elif kind == "commit_terminal":
        _validate_terminal_request(request, errors)


def _validate_terminal_request(
    request: RelayMEMSLPQueueTransitionRequest,
    errors: list[str],
) -> None:
    _expect(errors, request.lease_duration_seconds == 0, "terminal_lease_duration_nonzero")
    _expect(errors, bool(request.terminal_state), "terminal_state_required")
    _expect(errors, bool(request.terminal_reason_id), "terminal_reason_id_required")
    _expect(
        errors,
        request.retry_class == "unclassified" and request.retry_not_before is None,
        "terminal_unused_retry_fields_nondefault",
    )
    if request.terminal_state == "failed":
        _expect(errors, request.failure_class != "none", "terminal_failure_class_required")
    elif request.terminal_state in {"succeeded", "cancelled"}:
        _expect(errors, request.failure_class == "none", "terminal_failure_class_must_be_none")
    if request.expected_state == "queued":
        _expect(errors, request.terminal_state == "cancelled", "queued_terminal_target_not_cancelled")
        _expect(
            errors,
            not request.claim_owner and not request.lease_token,
            "queued_terminal_claim_fence_must_be_empty",
        )
    elif request.expected_state == "claimed":
        _expect(errors, bool(request.claim_owner), "terminal_claim_owner_required")
        _expect(errors, bool(request.lease_token), "terminal_lease_token_required")
    elif request.claim_owner or request.lease_token:
        errors.append("terminal_immutable_claim_fence_must_be_empty")


def _expect(errors: list[str], condition: bool, reason: str) -> None:
    if not condition:
        errors.append(reason)


def _expect_default_classification(
    request: RelayMEMSLPQueueTransitionRequest,
    errors: list[str],
    prefix: str,
) -> None:
    if (
        request.retry_class != "unclassified"
        or request.retry_not_before is not None
        or request.failure_class != "none"
    ):
        errors.append(f"{prefix}_unused_classification_fields_nondefault")


def _expect_empty_terminal(
    request: RelayMEMSLPQueueTransitionRequest,
    errors: list[str],
    prefix: str,
) -> None:
    if request.terminal_state or request.terminal_reason_id:
        errors.append(f"{prefix}_terminal_fields_nonempty")


def _transition_locked(
    root_fd: int,
    request: RelayMEMSLPQueueTransitionRequest,
    *,
    dry_run_only: bool,
    apply_enabled: bool,
    apply_requested: bool,
) -> RelayMEMSLPQueueStateTransitionResult:
    filename = record_filename(request.dispatch_idempotency_key)
    snapshot, read_status, read_reasons = read_record_snapshot(root_fd, filename)
    if snapshot is None:
        status: TransitionStatus = "corrupt" if read_status == "corrupt" else "write_failed"
        if read_status == "missing":
            status = "conflict"
        return _result(
            status, request.transition_kind, True, dry_run_only, apply_enabled,
            True, apply_requested, False, False, None, None, None, read_reasons,
        )
    record = snapshot.record
    state = str(record["state"])
    if (
        record["job_id"] != request.job_id
        or record["dispatch_idempotency_key"] != request.dispatch_idempotency_key
    ):
        return _result(
            "conflict", request.transition_kind, True, dry_run_only, apply_enabled,
            True, apply_requested, False, False, state, None, record,
            ("request_record_identity_mismatch",),
        )
    if state in TERMINAL_STATES:
        return _result(
            "blocked", request.transition_kind, True, dry_run_only, apply_enabled,
            True, apply_requested, False, False, state, state, record,
            ("terminal_state_immutable",),
        )
    if record["record_revision"] != request.expected_record_revision:
        return _conflict(request, dry_run_only, apply_enabled, apply_requested, state, record, "record_revision_mismatch")
    if state != request.expected_state:
        return _conflict(request, dry_run_only, apply_enabled, apply_requested, state, record, "record_state_mismatch")

    proposal, proposal_status, reasons = _build_proposal(record, request, _now_utc())
    if proposal is None:
        return _result(
            proposal_status, request.transition_kind, True, dry_run_only, apply_enabled,
            True, apply_requested, False, False, state, state, record, reasons,
        )
    proposal_errors = validate_record_mapping(proposal)
    if proposal_errors:
        return _result(
            "corrupt", request.transition_kind, True, dry_run_only, apply_enabled,
            True, apply_requested, False, False, state, str(proposal.get("state")),
            record, ("proposed_record_invalid", *proposal_errors),
        )
    if not apply_requested:
        return _result(
            "dry_run_ready", request.transition_kind, True, dry_run_only,
            apply_enabled, True, False, False, False, state,
            str(proposal["state"]), proposal, (),
        )
    outcome = atomic_replace_record(root_fd, filename, snapshot, proposal)
    return _result(
        outcome.status, request.transition_kind, True, dry_run_only, apply_enabled,
        True, True, outcome.transition_applied, outcome.durability_confirmed,
        state, str(proposal["state"]), outcome.record, outcome.reasons,
    )


def _build_proposal(
    record: Mapping[str, object],
    request: RelayMEMSLPQueueTransitionRequest,
    now: datetime,
) -> tuple[dict[str, object] | None, TransitionStatus, tuple[str, ...]]:
    revision = int(record["record_revision"])
    if revision >= MAX_COUNTER:
        return None, "blocked", ("record_revision_limit_reached",)
    current_updated_at = parse_timestamp(record["updated_at"])
    assert current_updated_at is not None
    if now < current_updated_at:
        return None, "blocked", ("queue_clock_regression",)
    now_text = format_timestamp(now)
    proposal = dict(record)
    kind = request.transition_kind

    if kind == "claim":
        if request.claim_generation != record["claim_generation"]:
            return None, "conflict", ("claim_generation_mismatch",)
        not_before = parse_timestamp(record["retry_not_before"])
        if not_before is not None and now < not_before:
            return None, "not_ready", ("retry_not_before_pending",)
        if int(record["attempt_count"]) >= MAX_COUNTER:
            return None, "blocked", ("attempt_count_limit_reached",)
        if int(record["claim_generation"]) >= MAX_COUNTER:
            return None, "blocked", ("claim_generation_limit_reached",)
        expires_text, error = _lease_expiry(now, request.lease_duration_seconds)
        if error:
            return None, "blocked", (error,)
        proposal.update({
            "state": "claimed",
            "record_revision": revision + 1,
            "updated_at": now_text,
            "attempt_count": int(record["attempt_count"]) + 1,
            "claim_generation": int(record["claim_generation"]) + 1,
            "claim_owner": request.claim_owner,
            "lease_token": _new_lease_token(),
            "lease_acquired_at": now_text,
            "lease_expires_at": expires_text,
            "retry_not_before": None,
            "terminal_reason_id": "",
        })
        return proposal, "dry_run_ready", ()

    state = str(record["state"])
    if kind in {"renew_lease", "retry_release", "commit_terminal"} and state == "claimed":
        fence_error = _check_claim_fence(record, request, require_owner=True)
        if fence_error:
            return None, "conflict", (fence_error,)
        expiry = parse_timestamp(record["lease_expires_at"])
        assert expiry is not None
        if now >= expiry:
            return None, "not_ready", ("active_lease_expired_stale_recovery_required",)

    if kind == "renew_lease":
        renewed_text, error = _lease_expiry(now, request.lease_duration_seconds)
        if error:
            return None, "blocked", (error,)
        proposal.update({
            "record_revision": revision + 1,
            "updated_at": now_text,
            "lease_expires_at": renewed_text,
        })
        return proposal, "dry_run_ready", ()

    if kind == "retry_release":
        proposal.update({
            "state": "queued",
            "record_revision": revision + 1,
            "updated_at": now_text,
            "claim_owner": "",
            "lease_token": "",
            "lease_acquired_at": None,
            "lease_expires_at": None,
            "retry_class": request.retry_class,
            "retry_not_before": request.retry_not_before,
            "failure_class": request.failure_class,
            "terminal_reason_id": "",
        })
        return proposal, "dry_run_ready", ()

    if kind == "stale_recovery":
        fence_error = _check_claim_fence(record, request, require_owner=False)
        if fence_error:
            return None, "conflict", (fence_error,)
        expiry = parse_timestamp(record["lease_expires_at"])
        assert expiry is not None
        if now < expiry:
            return None, "not_ready", ("stale_lease_not_expired",)
        proposal.update({
            "state": "queued",
            "record_revision": revision + 1,
            "updated_at": now_text,
            "claim_owner": "",
            "lease_token": "",
            "lease_acquired_at": None,
            "lease_expires_at": None,
            "retry_class": "stale_lease_recovery",
            "retry_not_before": None,
            "failure_class": "stale_lease_expired",
            "terminal_reason_id": "",
        })
        return proposal, "dry_run_ready", ()

    if kind == "commit_terminal":
        if state == "queued" and request.claim_generation != record["claim_generation"]:
            return None, "conflict", ("claim_generation_mismatch",)
        proposal.update({
            "state": request.terminal_state,
            "record_revision": revision + 1,
            "updated_at": now_text,
            "claim_owner": "",
            "lease_token": "",
            "lease_acquired_at": None,
            "lease_expires_at": None,
            "retry_not_before": None,
            "failure_class": request.failure_class,
            "terminal_reason_id": request.terminal_reason_id,
        })
        return proposal, "dry_run_ready", ()
    return None, "invalid_input", ("transition_kind_invalid",)


def _check_claim_fence(
    record: Mapping[str, object],
    request: RelayMEMSLPQueueTransitionRequest,
    *,
    require_owner: bool,
) -> str | None:
    if require_owner and record["claim_owner"] != request.claim_owner:
        return "claim_owner_mismatch"
    if record["claim_generation"] != request.claim_generation:
        return "claim_generation_mismatch"
    if record["lease_token"] != request.lease_token:
        return "lease_token_mismatch"
    return None


def _lease_expiry(base: datetime, seconds: int) -> tuple[str | None, str | None]:
    try:
        return format_timestamp(base + timedelta(seconds=seconds)), None
    except (OverflowError, ValueError):
        return None, "lease_timestamp_overflow"


def _new_lease_token() -> str:
    return "lease-v0-" + secrets.token_hex(32)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _conflict(
    request: RelayMEMSLPQueueTransitionRequest,
    dry_run_only: bool,
    apply_enabled: bool,
    apply_requested: bool,
    state: str,
    record: Mapping[str, object],
    reason: str,
) -> RelayMEMSLPQueueStateTransitionResult:
    return _result(
        "conflict", request.transition_kind, True, dry_run_only, apply_enabled,
        True, apply_requested, False, False, state, state, record, (reason,),
    )


def _result(
    status: TransitionStatus | str,
    transition_kind: str | None,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    queue_io_performed: bool,
    transition_attempted: bool,
    transition_applied: bool,
    durability_confirmed: bool,
    previous_state: str | None,
    proposed_state: str | None,
    durable_record: Mapping[str, object] | None,
    reasons: Sequence[str],
) -> RelayMEMSLPQueueStateTransitionResult:
    return RelayMEMSLPQueueStateTransitionResult(
        status=status,  # type: ignore[arg-type]
        transition_kind=transition_kind,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        queue_io_performed=queue_io_performed,
        transition_attempted=transition_attempted,
        transition_applied=transition_applied,
        durability_confirmed=durability_confirmed,
        previous_state=previous_state,
        proposed_state=proposed_state,
        durable_record=(dict(durable_record) if durable_record is not None else None),
        blocked_reasons=dedupe(reasons)[:MAX_REASON_COUNT],
    )


__all__ = [
    "RelayMEMSLPQueueTransitionRequest",
    "RelayMEMSLPQueueStateTransitionResult",
    "build_relaymem_slp_queue_state_node_result",
    "transition_relaymem_slp_queue_state",
]
