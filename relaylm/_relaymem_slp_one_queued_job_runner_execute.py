"""Execution phases for one validated queued Primary MEM job."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ._relaymem_slp_primary_worker_types import (
    RelayMEMSLPPrimaryWorkerRequest,
    RelayMEMSLPPrimaryWorkerResult,
)
from .relaymem_slp_primary_worker_source_adapter import (
    RelayMEMSLPPreparedWorkerSourceResult,
    RelayMEMSLPProtectedSourceReleaseResult,
)
from .relaymem_slp_queue_state import (
    RelayMEMSLPQueueStateTransitionResult,
    RelayMEMSLPQueueTransitionRequest,
)


@dataclass(frozen=True)
class _OneQueuedJobDependencies:
    transition_queue_state: Callable[..., RelayMEMSLPQueueStateTransitionResult]
    check_active_claim: Callable[..., tuple[bool, object, tuple[str, ...]]]
    exact_claimed_record: Callable[[object], bool]
    prepare_source: Callable[..., RelayMEMSLPPreparedWorkerSourceResult]
    execute_worker: Callable[[object], RelayMEMSLPPrimaryWorkerResult]
    release_terminal_source: Callable[..., RelayMEMSLPProtectedSourceReleaseResult]
    worker_request_schema: str


@dataclass(frozen=True)
class _OneQueuedJobExecution:
    status: str
    claim_attempted: bool = False
    claim_performed: bool = False
    claim_status: str | None = None
    source_lookup_status: str | None = None
    source_prepared: bool = False
    restart_rehydrated: bool = False
    worker_invoked: bool = False
    worker_status: str | None = None
    queue_transition_performed: bool = False
    retryable: bool = False
    terminal: bool = False
    cleanup_required: bool = False
    reasons: tuple[str, ...] = ()
    claim_result: RelayMEMSLPQueueStateTransitionResult | None = None
    source_result: RelayMEMSLPPreparedWorkerSourceResult | None = None
    worker_result: RelayMEMSLPPrimaryWorkerResult | None = None
    cleanup_result: RelayMEMSLPProtectedSourceReleaseResult | None = None


def _execute_one_queued_job(request: object, source_store: object, deps: _OneQueuedJobDependencies) -> _OneQueuedJobExecution:
    claim = _claim_queued_job(request, deps)
    if type(claim) is _OneQueuedJobExecution:
        return claim
    claimed = claim.durable_record
    assert type(claimed) is dict
    if request.dry_run_only:
        return _load_dry_run_source(request, source_store, claim, claimed)
    return _execute_claimed_job(request, source_store, deps, claim, claimed)


def _claim_queued_job(request: object, deps: _OneQueuedJobDependencies) -> object:
    claim_request = RelayMEMSLPQueueTransitionRequest(
        transition_kind="claim",
        job_id=str(request.queued_record["job_id"]),
        dispatch_idempotency_key=str(request.queued_record["dispatch_idempotency_key"]),
        expected_record_revision=int(request.queued_record["record_revision"]),
        expected_state="queued",
        claim_owner=request.claim_owner,
        claim_generation=int(request.queued_record["claim_generation"]),
        lease_duration_seconds=request.lease_duration_seconds,
    )
    try:
        claim = deps.transition_queue_state(
            claim_request,
            queue_root=request.queue_root,
            enabled=True,
            dry_run_only=request.dry_run_only,
            apply_enabled=request.apply_enabled,
        )
    except Exception:
        return _OneQueuedJobExecution(
            "claim_not_applied", claim_attempted=True,
            reasons=("one_queued_job_claim_failed",),
        )
    expected = "dry_run_ready" if request.dry_run_only else "applied"
    claimed = claim.durable_record
    valid = (
        claim.status == expected
        and type(claimed) is dict
        and deps.exact_claimed_record(claimed)
        and (request.dry_run_only or (claim.transition_applied and claim.durability_confirmed))
    )
    if valid:
        return claim
    return _OneQueuedJobExecution(
        "claim_not_applied",
        claim_attempted=True,
        claim_status=claim.status,
        claim_result=claim,
        reasons=claim.blocked_reasons or ("one_queued_job_claim_not_applied",),
    )


def _load_dry_run_source(request: object, source_store: object, claim: object, claimed: dict[str, object]) -> _OneQueuedJobExecution:
    try:
        loaded = source_store.load_for_claim(
            claimed_record=claimed, character_id=request.character_id
        )
    except Exception:
        return _OneQueuedJobExecution(
            "source_retryable",
            claim_attempted=True,
            claim_status=claim.status,
            source_lookup_status="retryable",
            retryable=True,
            claim_result=claim,
            reasons=("protected_source_dry_run_validation_failed",),
        )
    status = {
        "loaded": "dry_run_ready",
        "missing": "source_unavailable",
        "retryable": "source_retryable",
    }.get(loaded.status, "source_blocked")
    return _OneQueuedJobExecution(
        status,
        claim_attempted=True,
        claim_status=claim.status,
        source_lookup_status=loaded.status,
        retryable=loaded.status == "retryable",
        claim_result=claim,
        reasons=() if loaded.status == "loaded" else loaded.blocked_reasons,
    )


def _execute_claimed_job(request: object, source_store: object, deps: _OneQueuedJobDependencies, claim: object, claimed: dict[str, object]) -> _OneQueuedJobExecution:
    try:
        active, _, reasons = deps.check_active_claim(
            claimed,
            queue_root=request.queue_root,
            lease_duration_seconds=request.lease_duration_seconds,
            renew=False,
        )
    except Exception:
        active, reasons = False, ("one_queued_job_claim_revalidation_failed",)
    if not active:
        return _OneQueuedJobExecution(
            "claim_lost_before_rehydrate",
            claim_attempted=True,
            claim_performed=True,
            claim_status=claim.status,
            claim_result=claim,
            reasons=reasons or ("one_queued_job_claim_not_current",),
        )
    return _prepare_and_invoke(request, source_store, deps, claim, dict(claimed))


def _prepare_and_invoke(request: object, source_store: object, deps: _OneQueuedJobDependencies, claim: object, claimed: dict[str, object]) -> _OneQueuedJobExecution:
    try:
        prepared = deps.prepare_source(
            request.source_registry,
            claimed_record=claimed,
            character_id=request.character_id,
            source_store=source_store,
        )
    except Exception:
        return _OneQueuedJobExecution(
            "source_retryable",
            claim_attempted=True,
            claim_performed=True,
            claim_status=claim.status,
            source_lookup_status="retryable",
            retryable=True,
            claim_result=claim,
            reasons=("protected_source_prepare_failed",),
        )
    if prepared.status != "prepared" or prepared.source is None or prepared.request_scope is None:
        return _unprepared_source(claim, prepared)
    worker_request = _build_worker_request(request, deps, claimed, prepared)
    try:
        try:
            worker = deps.execute_worker(worker_request)
        except Exception:
            return _worker_failure(claim, prepared)
    finally:
        prepared.release_prepared_scope()
    return _finish_worker(request, source_store, deps, claim, prepared, worker)


def _unprepared_source(claim: object, prepared: RelayMEMSLPPreparedWorkerSourceResult) -> _OneQueuedJobExecution:
    status = {
        "source_unavailable": "source_unavailable",
        "retryable": "source_retryable",
        "blocked": "source_blocked",
    }.get(prepared.status, "source_blocked")
    return _OneQueuedJobExecution(
        status,
        claim_attempted=True,
        claim_performed=True,
        claim_status=claim.status,
        source_lookup_status=prepared.status,
        restart_rehydrated=prepared.restart_rehydrated,
        retryable=prepared.status == "retryable",
        claim_result=claim,
        source_result=prepared,
        reasons=prepared.blocked_reasons or ("protected_source_not_prepared",),
    )


def _build_worker_request(request: object, deps: _OneQueuedJobDependencies, claimed: dict[str, object], prepared: RelayMEMSLPPreparedWorkerSourceResult) -> RelayMEMSLPPrimaryWorkerRequest:
    return RelayMEMSLPPrimaryWorkerRequest(
        schema_version=deps.worker_request_schema,
        runtime_private=True,
        content_included=True,
        primary_writer_decision=request.primary_writer_decision,
        claimed_record=dict(claimed),
        worker_source=prepared.source,
        request_scope=prepared.request_scope,
        queue_root=request.queue_root,
        store_root=request.store_root,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        lease_duration_seconds=request.lease_duration_seconds,
        retry_not_before=None,
    )


def _worker_failure(claim: object, prepared: RelayMEMSLPPreparedWorkerSourceResult) -> _OneQueuedJobExecution:
    return _OneQueuedJobExecution(
        "worker_failed",
        claim_attempted=True,
        claim_performed=True,
        claim_status=claim.status,
        source_lookup_status=prepared.status,
        source_prepared=True,
        restart_rehydrated=prepared.restart_rehydrated,
        worker_invoked=True,
        claim_result=claim,
        source_result=prepared,
        reasons=("one_queued_job_worker_execution_failed",),
    )


def _finish_worker(request: object, source_store: object, deps: _OneQueuedJobDependencies, claim: object, prepared: RelayMEMSLPPreparedWorkerSourceResult, worker: RelayMEMSLPPrimaryWorkerResult) -> _OneQueuedJobExecution:
    terminal = worker.status in {"terminal_succeeded", "terminal_failed"}
    cleanup = None
    cleanup_required = False
    cleanup_reasons: tuple[str, ...] = ()
    if terminal:
        cleanup, cleanup_required, cleanup_reasons = _cleanup_terminal_source(
            request, source_store, deps, worker
        )
    return _OneQueuedJobExecution(
        "cleanup_required" if cleanup_required else "worker_completed",
        claim_attempted=True,
        claim_performed=True,
        claim_status=claim.status,
        source_lookup_status=prepared.status,
        source_prepared=True,
        restart_rehydrated=prepared.restart_rehydrated,
        worker_invoked=True,
        worker_status=worker.status,
        queue_transition_performed=worker.queue_transition_performed,
        retryable=worker.status == "retry_released",
        terminal=terminal,
        cleanup_required=cleanup_required,
        claim_result=claim,
        source_result=prepared,
        worker_result=worker,
        cleanup_result=cleanup,
        reasons=(*worker.reason_ids, *cleanup_reasons),
    )


def _cleanup_terminal_source(request: object, source_store: object, deps: _OneQueuedJobDependencies, worker: RelayMEMSLPPrimaryWorkerResult) -> tuple[RelayMEMSLPProtectedSourceReleaseResult | None, bool, tuple[str, ...]]:
    transition = worker.queue_transition_result
    terminal_record = transition.durable_record if transition is not None else None
    if type(terminal_record) is not dict:
        return None, True, ("terminal_queue_record_unavailable_for_cleanup",)
    try:
        cleanup = deps.release_terminal_source(
            request.source_registry,
            terminal_record=terminal_record,
            character_id=request.character_id,
            source_store=source_store,
        )
    except Exception:
        return None, True, ("protected_source_terminal_cleanup_failed",)
    required = cleanup.status != "released"
    reasons = cleanup.blocked_reasons or ("protected_source_cleanup_required",)
    return cleanup, required, reasons if required else ()


__all__ = ["_OneQueuedJobDependencies", "_OneQueuedJobExecution", "_execute_one_queued_job"]
