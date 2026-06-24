"""Phase 6-C2 one queued-job claim / rehydrate / execute adapter.

This helper accepts one caller-selected canonical queued B3 record. It delegates
claim mutation to Phase 6-B3, source preparation to Phase 6-C1-5, and execution
plus retry/terminal transition to the unchanged Phase 6-C1-2 worker.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ._relaymem_slp_primary_worker_fence import _check_active_claim, _exact_claimed_record
from .pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from .relaymem_slp_primary_worker import (
    REQUEST_SCHEMA as PRIMARY_WORKER_REQUEST_SCHEMA,
    RelayMEMSLPPrimaryWorkerRequest,
    RelayMEMSLPPrimaryWorkerResult,
    execute_relaymem_slp_primary_worker,
)
from .relaymem_slp_primary_worker_source_adapter import (
    RelayMEMSLPPreparedWorkerSourceResult,
    RelayMEMSLPProtectedSourceReleaseResult,
    prepare_relaymem_slp_primary_worker_source_for_claim,
    release_relaymem_slp_primary_worker_source_after_terminal,
)
from .relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from .relaymem_slp_protected_source_store import (
    DEFAULT_MAX_ARTIFACT_BYTES,
    MAX_ARTIFACT_BYTES_LIMIT,
    RelayMEMSLPDurableProtectedSourceStore,
)
from .relaymem_slp_queue_record import (
    DURABLE_JOB_SCHEMA,
    MAX_LEASE_SECONDS,
    bad_text,
    is_token,
    validate_record_mapping,
)
from .relaymem_slp_queue_state import (
    RelayMEMSLPQueueStateTransitionResult,
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)

REQUEST_SCHEMA = "relaymem.slp_one_queued_job_runner_request.v0"
RESULT_SCHEMA = "relaymem.slp_one_queued_job_runner_result.v0"
PROJECTION_SCHEMA = "relaymem.slp_one_queued_job_runner_projection.v0"

RunnerStatus = Literal[
    "disabled",
    "invalid_input",
    "dry_run_ready",
    "claim_not_applied",
    "claim_lost_before_rehydrate",
    "source_unavailable",
    "source_retryable",
    "source_blocked",
    "worker_completed",
    "worker_failed",
    "cleanup_required",
]

_REASON_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")
_MAX_REASONS = 32


@dataclass(frozen=True, repr=False)
class RelayMEMSLPOneQueuedJobRunnerRequest:
    """Exact runtime-private request for one caller-selected queued job."""

    schema_version: str
    runtime_private: bool
    content_included: bool
    queued_record: dict[str, object] = field(repr=False)
    source_registry: RelayMEMSLPPrimaryWorkerSourceRegistry = field(repr=False)
    character_id: str = field(repr=False)
    queue_root: str = field(repr=False)
    protected_source_root: str = field(repr=False)
    store_root: str = field(repr=False)
    claim_owner: str = field(repr=False)
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    lease_duration_seconds: int
    protected_source_max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPOneQueuedJobRunnerRequest("
            f"schema_version={self.schema_version!r}, enabled={self.enabled!r}, "
            f"dry_run_only={self.dry_run_only!r}, apply_enabled={self.apply_enabled!r}, "
            "runtime_private=True, queued_record_omitted=True, roots_omitted=True)"
        )


@dataclass(frozen=True)
class RelayMEMSLPOneQueuedJobRunnerProjection:
    status: RunnerStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    claim_attempted: bool
    claim_performed: bool
    claim_status: str | None
    source_lookup_status: str | None
    source_prepared: bool
    restart_rehydrated: bool
    worker_invoked: bool
    worker_status: str | None
    queue_transition_performed: bool
    retryable: bool
    terminal: bool
    cleanup_required: bool
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
            "governed_body_included": False,
            "namespace_included": False,
            "runtime_identifiers_included": False,
            "lineage_fingerprint_included": False,
            "idempotency_keys_included": False,
            "claim_fence_included": False,
            "timestamps_included": False,
            "queue_path_included": False,
            "protected_source_path_included": False,
            "store_path_included": False,
            "source_digest_included": False,
            "exception_text_included": False,
            "private_nested_results_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "claim_attempted": self.claim_attempted,
            "claim_performed": self.claim_performed,
            "claim_status": self.claim_status,
            "source_lookup_status": self.source_lookup_status,
            "source_prepared": self.source_prepared,
            "restart_rehydrated": self.restart_rehydrated,
            "worker_invoked": self.worker_invoked,
            "worker_status": self.worker_status,
            "queue_transition_performed": self.queue_transition_performed,
            "retryable": self.retryable,
            "terminal": self.terminal,
            "cleanup_required": self.cleanup_required,
            "reason_ids": list(self.reason_ids),
        }


@dataclass(frozen=True, repr=False)
class RelayMEMSLPOneQueuedJobRunnerResult:
    """Runtime-private integration ledger with a bounded public projection."""

    schema_version: str
    status: RunnerStatus
    runtime_private: bool
    content_included: bool
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    claim_attempted: bool
    claim_performed: bool
    claim_status: str | None
    source_lookup_status: str | None
    source_prepared: bool
    restart_rehydrated: bool
    worker_invoked: bool
    worker_status: str | None
    queue_transition_performed: bool
    retryable: bool
    terminal: bool
    cleanup_required: bool
    reason_ids: tuple[str, ...]
    claim_result: RelayMEMSLPQueueStateTransitionResult | None = field(
        default=None, repr=False, compare=False
    )
    source_result: RelayMEMSLPPreparedWorkerSourceResult | None = field(
        default=None, repr=False, compare=False
    )
    worker_result: RelayMEMSLPPrimaryWorkerResult | None = field(
        default=None, repr=False, compare=False
    )
    cleanup_result: RelayMEMSLPProtectedSourceReleaseResult | None = field(
        default=None, repr=False, compare=False
    )

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPOneQueuedJobRunnerResult("
            f"status={self.status!r}, claim_performed={self.claim_performed!r}, "
            f"source_prepared={self.source_prepared!r}, "
            f"worker_invoked={self.worker_invoked!r}, "
            f"worker_status={self.worker_status!r}, "
            f"cleanup_required={self.cleanup_required!r}, "
            "private_results_omitted=True)"
        )

    def to_log_dict(self) -> dict[str, object]:
        return project_relaymem_slp_one_queued_job_runner(self).to_log_dict()


def execute_one_queued_relaymem_slp_primary_job(
    request: object,
) -> RelayMEMSLPOneQueuedJobRunnerResult:
    """Claim, rehydrate, and execute exactly one canonical queued B3 record."""

    if type(request) is not RelayMEMSLPOneQueuedJobRunnerRequest:
        return _result("invalid_input", None, reasons=("exact_one_queued_job_request_required",))
    _, gate_reasons = _validate_gates(request)
    if gate_reasons:
        return _result("invalid_input", request, reasons=gate_reasons)
    if not request.enabled:
        return _result("disabled", request)

    exact, request_reasons = _validate_request(request)
    if exact is None:
        return _result("invalid_input", request, reasons=request_reasons)
    try:
        source_store = RelayMEMSLPDurableProtectedSourceStore(
            exact.protected_source_root,
            max_artifact_bytes=exact.protected_source_max_artifact_bytes,
        )
    except (TypeError, ValueError):
        return _result(
            "invalid_input", exact, reasons=("protected_source_store_config_invalid",)
        )

    claim_request = RelayMEMSLPQueueTransitionRequest(
        transition_kind="claim",
        job_id=str(exact.queued_record["job_id"]),
        dispatch_idempotency_key=str(
            exact.queued_record["dispatch_idempotency_key"]
        ),
        expected_record_revision=int(exact.queued_record["record_revision"]),
        expected_state="queued",
        claim_owner=exact.claim_owner,
        claim_generation=int(exact.queued_record["claim_generation"]),
        lease_duration_seconds=exact.lease_duration_seconds,
    )
    try:
        claim = transition_relaymem_slp_queue_state(
            claim_request,
            queue_root=exact.queue_root,
            enabled=True,
            dry_run_only=exact.dry_run_only,
            apply_enabled=exact.apply_enabled,
        )
    except Exception:
        return _result(
            "claim_not_applied",
            exact,
            claim_attempted=True,
            reasons=("one_queued_job_claim_failed",),
        )

    claimed = claim.durable_record
    expected_claim_status = "dry_run_ready" if exact.dry_run_only else "applied"
    claim_ok = (
        claim.status == expected_claim_status
        and type(claimed) is dict
        and _exact_claimed_record(claimed)
        and (exact.dry_run_only or (claim.transition_applied and claim.durability_confirmed))
    )
    if not claim_ok:
        return _result(
            "claim_not_applied",
            exact,
            claim_attempted=True,
            claim_result=claim,
            claim_status=claim.status,
            reasons=claim.blocked_reasons or ("one_queued_job_claim_not_applied",),
        )
    assert type(claimed) is dict

    if exact.dry_run_only:
        try:
            loaded = source_store.load_for_claim(
                claimed_record=claimed,
                character_id=exact.character_id,
            )
        except Exception:
            return _result(
                "source_retryable",
                exact,
                claim_attempted=True,
                claim_result=claim,
                claim_status=claim.status,
                source_lookup_status="retryable",
                retryable=True,
                reasons=("protected_source_dry_run_validation_failed",),
            )
        status = _dry_run_source_status(loaded.status)
        return _result(
            status,
            exact,
            claim_attempted=True,
            claim_result=claim,
            claim_status=claim.status,
            source_lookup_status=loaded.status,
            retryable=loaded.status == "retryable",
            reasons=() if loaded.status == "loaded" else loaded.blocked_reasons,
        )

    try:
        active, _, active_reasons = _check_active_claim(
            claimed,
            queue_root=exact.queue_root,
            lease_duration_seconds=exact.lease_duration_seconds,
            renew=False,
        )
    except Exception:
        active = False
        active_reasons = ("one_queued_job_claim_revalidation_failed",)
    if not active:
        return _result(
            "claim_lost_before_rehydrate",
            exact,
            claim_attempted=True,
            claim_performed=True,
            claim_result=claim,
            claim_status=claim.status,
            reasons=active_reasons or ("one_queued_job_claim_not_current",),
        )
    # The canonical B3 dry-run fence rereads the durable record and proves that
    # this exact claimed revision/owner/generation/token is current. Its returned
    # durable_record is a renewal proposal, so the committed claim record remains
    # the exact input for C1-5 and C1-2.
    claimed = dict(claimed)

    try:
        prepared = prepare_relaymem_slp_primary_worker_source_for_claim(
            exact.source_registry,
            claimed_record=claimed,
            character_id=exact.character_id,
            source_store=source_store,
        )
    except Exception:
        return _result(
            "source_retryable",
            exact,
            claim_attempted=True,
            claim_performed=True,
            claim_result=claim,
            claim_status=claim.status,
            source_lookup_status="retryable",
            retryable=True,
            reasons=("protected_source_prepare_failed",),
        )
    if prepared.status != "prepared" or prepared.source is None or prepared.request_scope is None:
        mapped = {
            "source_unavailable": "source_unavailable",
            "retryable": "source_retryable",
            "blocked": "source_blocked",
        }.get(prepared.status, "source_blocked")
        return _result(
            mapped,
            exact,
            claim_attempted=True,
            claim_performed=True,
            claim_result=claim,
            claim_status=claim.status,
            source_result=prepared,
            source_lookup_status=prepared.status,
            restart_rehydrated=prepared.restart_rehydrated,
            retryable=prepared.status == "retryable",
            reasons=prepared.blocked_reasons or ("protected_source_not_prepared",),
        )

    worker_request = RelayMEMSLPPrimaryWorkerRequest(
        schema_version=PRIMARY_WORKER_REQUEST_SCHEMA,
        runtime_private=True,
        content_included=True,
        claimed_record=dict(claimed),
        worker_source=prepared.source,
        request_scope=prepared.request_scope,
        queue_root=exact.queue_root,
        store_root=exact.store_root,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        lease_duration_seconds=exact.lease_duration_seconds,
        retry_not_before=None,
    )
    try:
        try:
            worker = execute_relaymem_slp_primary_worker(worker_request)
        except Exception:
            return _result(
                "worker_failed",
                exact,
                claim_attempted=True,
                claim_performed=True,
                claim_result=claim,
                claim_status=claim.status,
                source_result=prepared,
                source_lookup_status=prepared.status,
                source_prepared=True,
                restart_rehydrated=prepared.restart_rehydrated,
                worker_invoked=True,
                reasons=("one_queued_job_worker_execution_failed",),
            )
    finally:
        prepared.release_prepared_scope()

    terminal = worker.status in {"terminal_succeeded", "terminal_failed"}
    retryable = worker.status == "retry_released"
    cleanup = None
    cleanup_required = False
    cleanup_reasons: tuple[str, ...] = ()
    if terminal:
        transition = worker.queue_transition_result
        terminal_record = transition.durable_record if transition is not None else None
        if type(terminal_record) is not dict:
            cleanup_required = True
            cleanup_reasons = ("terminal_queue_record_unavailable_for_cleanup",)
        else:
            try:
                cleanup = release_relaymem_slp_primary_worker_source_after_terminal(
                    exact.source_registry,
                    terminal_record=terminal_record,
                    character_id=exact.character_id,
                    source_store=source_store,
                )
            except Exception:
                cleanup_required = True
                cleanup_reasons = ("protected_source_terminal_cleanup_failed",)
            else:
                cleanup_required = cleanup.status != "released"
                if cleanup_required:
                    cleanup_reasons = cleanup.blocked_reasons or (
                        "protected_source_cleanup_required",
                    )

    return _result(
        "cleanup_required" if cleanup_required else "worker_completed",
        exact,
        claim_attempted=True,
        claim_performed=True,
        claim_result=claim,
        claim_status=claim.status,
        source_result=prepared,
        source_lookup_status=prepared.status,
        source_prepared=True,
        restart_rehydrated=prepared.restart_rehydrated,
        worker_invoked=True,
        worker_result=worker,
        worker_status=worker.status,
        queue_transition_performed=worker.queue_transition_performed,
        retryable=retryable,
        terminal=terminal,
        cleanup_required=cleanup_required,
        cleanup_result=cleanup,
        reasons=(*worker.reason_ids, *cleanup_reasons),
    )


def project_relaymem_slp_one_queued_job_runner(
    result: RelayMEMSLPOneQueuedJobRunnerResult,
) -> RelayMEMSLPOneQueuedJobRunnerProjection:
    if type(result) is not RelayMEMSLPOneQueuedJobRunnerResult:
        raise ValueError("exact_one_queued_job_result_required")
    if result.schema_version != RESULT_SCHEMA or result.runtime_private is not True:
        raise ValueError("one_queued_job_result_schema_invalid")
    return RelayMEMSLPOneQueuedJobRunnerProjection(
        status=result.status,
        enabled=result.enabled,
        dry_run_only=result.dry_run_only,
        apply_enabled=result.apply_enabled,
        claim_attempted=result.claim_attempted,
        claim_performed=result.claim_performed,
        claim_status=result.claim_status,
        source_lookup_status=result.source_lookup_status,
        source_prepared=result.source_prepared,
        restart_rehydrated=result.restart_rehydrated,
        worker_invoked=result.worker_invoked,
        worker_status=result.worker_status,
        queue_transition_performed=result.queue_transition_performed,
        retryable=result.retryable,
        terminal=result.terminal,
        cleanup_required=result.cleanup_required,
        reason_ids=result.reason_ids,
    )


def build_relaymem_slp_one_queued_job_runner_node_result(
    result: RelayMEMSLPOneQueuedJobRunnerResult,
) -> PipelineNodeResult:
    projection = project_relaymem_slp_one_queued_job_runner(result)
    node_status = {
        "disabled": "skipped",
        "dry_run_ready": "diagnostic_only",
        "worker_completed": "applied" if projection.terminal else "blocked",
        "cleanup_required": "blocked",
        "invalid_input": "failed",
        "worker_failed": "failed",
    }.get(result.status, "blocked")
    return build_pipeline_node_result(
        node_name="relaymem_slp_one_queued_job_runner",
        status=node_status,
        decision=result.status,
        blocked_reasons=result.reason_ids,
        diagnostics=projection.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relaymem_slp_one_queued_job_runner_result",
                "schema_version": RESULT_SCHEMA,
                "present": True,
                "content_free": True,
                "runtime_private": True,
                "private_result_omitted": True,
                "source_content_included": False,
                "queue_record_included": False,
                "claim_fence_included": False,
                "paths_included": False,
                "worker_invoked": result.worker_invoked,
                "queue_transition_performed": result.queue_transition_performed,
                "cleanup_required": result.cleanup_required,
                "mutates_soul": False,
                "changes_visible_response": False,
            }
        ],
    )


def _validate_gates(
    request: RelayMEMSLPOneQueuedJobRunnerRequest,
) -> tuple[tuple[bool, bool, bool], tuple[str, ...]]:
    reasons: list[str] = []
    for name in ("enabled", "dry_run_only", "apply_enabled"):
        if type(getattr(request, name)) is not bool:
            reasons.append(f"one_queued_job_{name}_invalid")
    gates = (request.enabled, request.dry_run_only, request.apply_enabled)
    if not reasons and gates not in {
        (False, True, False),
        (True, True, False),
        (True, False, True),
    }:
        reasons.append("one_queued_job_gate_mode_invalid")
    return gates, _reason_ids(reasons)


def _validate_request(
    value: RelayMEMSLPOneQueuedJobRunnerRequest,
) -> tuple[RelayMEMSLPOneQueuedJobRunnerRequest | None, tuple[str, ...]]:
    reasons: list[str] = []
    if value.schema_version != REQUEST_SCHEMA:
        reasons.append("one_queued_job_request_schema_mismatch")
    if value.runtime_private is not True:
        reasons.append("one_queued_job_runtime_private_required")
    if value.content_included is not False:
        reasons.append("one_queued_job_content_free_request_required")
    if type(value.queued_record) is not dict:
        reasons.append("exact_queued_record_required")
    else:
        record_reasons = validate_record_mapping(value.queued_record)
        reasons.extend(record_reasons)
        if not record_reasons and value.queued_record.get("schema_version") != DURABLE_JOB_SCHEMA:
            reasons.append("queued_record_schema_mismatch")
        if not record_reasons and value.queued_record.get("state") != "queued":
            reasons.append("exact_queued_record_required")
    if type(value.source_registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        reasons.append("exact_source_registry_required")
    if not is_token(value.character_id):
        reasons.append("character_id_invalid")
    if not is_token(value.claim_owner):
        reasons.append("claim_owner_invalid")
    for name in ("queue_root", "protected_source_root", "store_root"):
        root = getattr(value, name)
        if (
            type(root) is not str
            or not root
            or root != root.strip()
            or bad_text(root)
            or not Path(root).is_absolute()
        ):
            reasons.append(f"one_queued_job_{name}_invalid")
    if (
        type(value.lease_duration_seconds) is not int
        or not 1 <= value.lease_duration_seconds <= MAX_LEASE_SECONDS
    ):
        reasons.append("one_queued_job_lease_duration_invalid")
    if (
        type(value.protected_source_max_artifact_bytes) is not int
        or not 1
        <= value.protected_source_max_artifact_bytes
        <= MAX_ARTIFACT_BYTES_LIMIT
    ):
        reasons.append("protected_source_max_artifact_bytes_invalid")
    return (value, ()) if not reasons else (None, _reason_ids(reasons))


def _dry_run_source_status(status: str) -> RunnerStatus:
    if status == "loaded":
        return "dry_run_ready"
    if status == "missing":
        return "source_unavailable"
    if status == "retryable":
        return "source_retryable"
    return "source_blocked"


def _result(
    status: RunnerStatus,
    request: RelayMEMSLPOneQueuedJobRunnerRequest | None,
    *,
    claim_attempted: bool = False,
    claim_performed: bool = False,
    claim_status: str | None = None,
    source_lookup_status: str | None = None,
    source_prepared: bool = False,
    restart_rehydrated: bool = False,
    worker_invoked: bool = False,
    worker_status: str | None = None,
    queue_transition_performed: bool = False,
    retryable: bool = False,
    terminal: bool = False,
    cleanup_required: bool = False,
    reasons: tuple[str, ...] | list[str] = (),
    claim_result: RelayMEMSLPQueueStateTransitionResult | None = None,
    source_result: RelayMEMSLPPreparedWorkerSourceResult | None = None,
    worker_result: RelayMEMSLPPrimaryWorkerResult | None = None,
    cleanup_result: RelayMEMSLPProtectedSourceReleaseResult | None = None,
) -> RelayMEMSLPOneQueuedJobRunnerResult:
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
    return RelayMEMSLPOneQueuedJobRunnerResult(
        schema_version=RESULT_SCHEMA,
        status=status,
        runtime_private=True,
        content_included=False,
        enabled=enabled,
        dry_run_only=dry_run,
        apply_enabled=apply_enabled,
        claim_attempted=claim_attempted,
        claim_performed=claim_performed,
        claim_status=claim_status,
        source_lookup_status=source_lookup_status,
        source_prepared=source_prepared,
        restart_rehydrated=restart_rehydrated,
        worker_invoked=worker_invoked,
        worker_status=worker_status,
        queue_transition_performed=queue_transition_performed,
        retryable=retryable,
        terminal=terminal,
        cleanup_required=cleanup_required,
        reason_ids=_reason_ids(reasons),
        claim_result=claim_result,
        source_result=source_result,
        worker_result=worker_result,
        cleanup_result=cleanup_result,
    )


def _reason_ids(values: object) -> tuple[str, ...]:
    output: list[str] = []
    try:
        iterator = iter(values)  # type: ignore[arg-type]
    except TypeError:
        iterator = iter(("invalid_reason_id",))
    for value in iterator:
        reason = value if type(value) is str and _REASON_RE.fullmatch(value) else "invalid_reason_id"
        if reason not in output:
            output.append(reason)
        if len(output) >= _MAX_REASONS:
            break
    return tuple(output)


__all__ = [
    "PROJECTION_SCHEMA",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "RelayMEMSLPOneQueuedJobRunnerProjection",
    "RelayMEMSLPOneQueuedJobRunnerRequest",
    "RelayMEMSLPOneQueuedJobRunnerResult",
    "build_relaymem_slp_one_queued_job_runner_node_result",
    "execute_one_queued_relaymem_slp_primary_job",
    "project_relaymem_slp_one_queued_job_runner",
]
