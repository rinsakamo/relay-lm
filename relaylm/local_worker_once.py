"""O0 local one-job runner.

This module preserves the operator-facing O0 contract while consuming the
shared O0/O1C queue-candidate helper.  All claim, rehydration, worker, retry,
terminal, and cleanup authority remains delegated to Phase 6-C2.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from .config import RelayLMConfig
from .relaymem_slp_one_queued_job_runner import (
    RelayMEMSLPOneQueuedJobRunnerResult,
    execute_one_queued_relaymem_slp_primary_job,
)
from .relaymem_slp_queue_candidate import (
    MAX_DISCOVERY_MAX_ENTRIES,
    QueueCandidate,
    build_relaymem_slp_one_queued_job_request,
    canonical_reread_relaymem_slp_queue_candidate,
    discover_relaymem_slp_queue_candidate,
    resolve_relaymem_slp_queue_character_scope,
    validate_configured_roots,
    validate_local_worker_mode,
)
from .relaymem_slp_queue_record import is_token
from .relaymem_slp_queue_storage import RecordSnapshot

REQUEST_SCHEMA = "relaymem.local_worker_once_request.v0"
RESULT_SCHEMA = "relaymem.local_worker_once_result.v0"
PROJECTION_SCHEMA = "relaymem.local_worker_once_projection.v0"

_REASON_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")
_MAX_REASONS = 32

O0Status = Literal[
    "disabled",
    "invalid_input",
    "queue_busy",
    "no_eligible_work",
    "unsafe_queue_state",
    "candidate_changed",
    "dry_run_ready",
    "executed",
    "execution_failed",
]
ExitCategory = Literal[
    "completed",
    "no_eligible_work",
    "dry_run_ready",
    "invalid_configuration",
    "unsafe_queue_state",
    "unexpected_failure",
]


@dataclass(frozen=True, repr=False)
class RelayLMLocalWorkerOnceRequest:
    schema_version: str
    runtime_private: bool
    content_included: bool
    config: RelayLMConfig = field(repr=False)
    character_id: str | None = field(default=None, repr=False)

    def __repr__(self) -> str:
        return (
            "RelayLMLocalWorkerOnceRequest("
            f"schema_version={self.schema_version!r}, "
            "runtime_private=True, config_omitted=True, character_id_omitted=True)"
        )


@dataclass(frozen=True)
class RelayLMLocalWorkerOnceProjection:
    status: O0Status
    exit_category: ExitCategory
    selected: bool
    eligible: bool
    canonical_reread_performed: bool
    character_scope_resolved: bool
    c2_status: str | None
    claim_attempted: bool
    claim_performed: bool
    source_prepared: bool
    restart_rehydrated: bool
    worker_invoked: bool
    worker_status: str | None
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
            "governed_content_included": False,
            "namespace_included": False,
            "character_id_included": False,
            "runtime_identifiers_included": False,
            "claim_fence_included": False,
            "timestamps_included": False,
            "path_values_included": False,
            "source_digest_included": False,
            "exception_text_included": False,
            "private_nested_results_included": False,
            "status": self.status,
            "exit_category": self.exit_category,
            "selected": self.selected,
            "eligible": self.eligible,
            "canonical_reread_performed": self.canonical_reread_performed,
            "character_scope_resolved": self.character_scope_resolved,
            "c2_status": self.c2_status,
            "claim_attempted": self.claim_attempted,
            "claim_performed": self.claim_performed,
            "source_prepared": self.source_prepared,
            "restart_rehydrated": self.restart_rehydrated,
            "worker_invoked": self.worker_invoked,
            "worker_status": self.worker_status,
            "retryable": self.retryable,
            "terminal": self.terminal,
            "cleanup_required": self.cleanup_required,
            "reason_ids": list(self.reason_ids),
        }


@dataclass(frozen=True, repr=False)
class RelayLMLocalWorkerOnceResult:
    schema_version: str
    status: O0Status
    runtime_private: bool
    content_included: bool
    exit_category: ExitCategory
    selected: bool
    eligible: bool
    canonical_reread_performed: bool
    character_scope_resolved: bool
    c2_result: RelayMEMSLPOneQueuedJobRunnerResult | None = field(
        default=None, repr=False, compare=False
    )
    reason_ids: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            "RelayLMLocalWorkerOnceResult("
            f"status={self.status!r}, exit_category={self.exit_category!r}, "
            f"selected={self.selected!r}, c2_result_omitted=True)"
        )

    def to_log_dict(self) -> dict[str, object]:
        return project_local_worker_once(self).to_log_dict()


# Compatibility alias retained for the existing O0 security smoke and any
# private test seam. Production O1C imports the shared public helper directly.
_Candidate = QueueCandidate


def execute_local_worker_once(request: object) -> RelayLMLocalWorkerOnceResult:
    """Run one bounded O0 invocation and execute at most one C2 request."""

    exact, reasons = _validate_request(request)
    if exact is None:
        return _result(
            "invalid_input",
            "invalid_configuration",
            reasons=reasons,
        )
    config = exact.config
    mode, gate_reasons = _worker_mode(config)
    if gate_reasons:
        return _result(
            "invalid_input",
            "invalid_configuration",
            reasons=gate_reasons,
        )
    if mode == "disabled":
        return _result("disabled", "completed")
    assert mode in {"dry_run", "apply"}

    roots, root_reasons = _validated_roots(config)
    if roots is None:
        return _result(
            "invalid_input",
            "invalid_configuration",
            reasons=root_reasons,
        )
    queue_root, protected_source_root, configured_store_root = roots
    candidate, discovery_status, discovery_reasons = _discover_candidate(
        queue_root,
        now=datetime.now(timezone.utc),
        max_entries=config.relaymem_local_worker_discovery_max_entries,
    )
    if discovery_status == "unsafe":
        return _result(
            "unsafe_queue_state",
            "unsafe_queue_state",
            reasons=discovery_reasons,
        )
    if discovery_status == "busy":
        return _result(
            "queue_busy",
            "completed",
            reasons=discovery_reasons,
        )
    if candidate is None:
        return _result(
            "no_eligible_work",
            "no_eligible_work",
            reasons=discovery_reasons,
        )

    current, reread_status, reread_reasons = _canonical_reread(
        queue_root,
        candidate,
        now=datetime.now(timezone.utc),
    )
    if current is None:
        status: O0Status = (
            "unsafe_queue_state" if reread_status == "unsafe" else "candidate_changed"
        )
        return _result(
            status,
            "unsafe_queue_state",
            selected=True,
            eligible=True,
            canonical_reread_performed=True,
            reasons=reread_reasons,
        )

    character_id, store_root, scope_reasons = _resolve_character_scope(
        config,
        namespace=current.record.get("namespace"),
        explicit_character_id=exact.character_id,
        configured_store_root=configured_store_root,
    )
    if character_id is None or store_root is None:
        return _result(
            "invalid_input",
            "invalid_configuration",
            selected=True,
            eligible=True,
            canonical_reread_performed=True,
            reasons=scope_reasons,
        )

    try:
        c2_request = build_relaymem_slp_one_queued_job_request(
            config=config,
            queued_record=dict(current.record),
            character_id=character_id,
            queue_root=queue_root,
            protected_source_root=protected_source_root,
            store_root=store_root,
            mode=mode,
        )
        c2_result = execute_one_queued_relaymem_slp_primary_job(c2_request)
    except Exception:
        return _result(
            "execution_failed",
            "unexpected_failure",
            selected=True,
            eligible=True,
            canonical_reread_performed=True,
            character_scope_resolved=True,
            reasons=("local_worker_c2_unexpected_failure",),
        )

    if mode == "dry_run" and c2_result.status == "dry_run_ready":
        status: O0Status = "dry_run_ready"
        category: ExitCategory = "dry_run_ready"
    else:
        status = "executed"
        category = "completed"
    return _result(
        status,
        category,
        selected=True,
        eligible=True,
        canonical_reread_performed=True,
        character_scope_resolved=True,
        c2_result=c2_result,
        reasons=c2_result.reason_ids,
    )


def project_local_worker_once(
    result: RelayLMLocalWorkerOnceResult,
) -> RelayLMLocalWorkerOnceProjection:
    c2 = result.c2_result
    return RelayLMLocalWorkerOnceProjection(
        status=result.status,
        exit_category=result.exit_category,
        selected=result.selected,
        eligible=result.eligible,
        canonical_reread_performed=result.canonical_reread_performed,
        character_scope_resolved=result.character_scope_resolved,
        c2_status=c2.status if c2 is not None else None,
        claim_attempted=c2.claim_attempted if c2 is not None else False,
        claim_performed=c2.claim_performed if c2 is not None else False,
        source_prepared=c2.source_prepared if c2 is not None else False,
        restart_rehydrated=c2.restart_rehydrated if c2 is not None else False,
        worker_invoked=c2.worker_invoked if c2 is not None else False,
        worker_status=c2.worker_status if c2 is not None else None,
        retryable=c2.retryable if c2 is not None else False,
        terminal=c2.terminal if c2 is not None else False,
        cleanup_required=c2.cleanup_required if c2 is not None else False,
        reason_ids=result.reason_ids,
    )


def exit_code_for_local_worker_once(result: RelayLMLocalWorkerOnceResult) -> int:
    return {
        "completed": 0,
        "no_eligible_work": 0,
        "dry_run_ready": 0,
        "invalid_configuration": 64,
        "unsafe_queue_state": 65,
        "unexpected_failure": 70,
    }[result.exit_category]


def _validate_request(
    value: object,
) -> tuple[RelayLMLocalWorkerOnceRequest | None, tuple[str, ...]]:
    if type(value) is not RelayLMLocalWorkerOnceRequest:
        return None, ("exact_local_worker_once_request_required",)
    reasons: list[str] = []
    if value.schema_version != REQUEST_SCHEMA:
        reasons.append("local_worker_once_request_schema_mismatch")
    if value.runtime_private is not True:
        reasons.append("local_worker_once_runtime_private_required")
    if value.content_included is not False:
        reasons.append("local_worker_once_content_free_request_required")
    if type(value.config) is not RelayLMConfig:
        reasons.append("exact_relaylm_config_required")
    if value.character_id is not None and not is_token(value.character_id):
        reasons.append("local_worker_character_id_invalid")
    return (value, ()) if not reasons else (None, _reason_ids(reasons))


def _worker_mode(config: RelayLMConfig) -> tuple[str | None, tuple[str, ...]]:
    mode, reasons = validate_local_worker_mode(config)
    return mode, _reason_ids(reasons)


def _validated_roots(
    config: RelayLMConfig,
) -> tuple[tuple[str, str, str] | None, tuple[str, ...]]:
    roots, reasons = validate_configured_roots(config)
    return roots, _reason_ids(reasons)


def _discover_candidate(
    queue_root: str,
    *,
    now: datetime,
    max_entries: int,
) -> tuple[_Candidate | None, str, tuple[str, ...]]:
    result = discover_relaymem_slp_queue_candidate(
        queue_root,
        now=now,
        max_entries=max_entries,
    )
    if result.status == "selected":
        return result.candidate, "selected", _reason_ids(result.reason_ids)
    if result.status in {"no_work", "future_retry_only"}:
        return None, "no_work", _reason_ids(result.reason_ids)
    return None, result.status, _reason_ids(result.reason_ids)


def _canonical_reread(
    queue_root: str,
    candidate: _Candidate,
    *,
    now: datetime,
) -> tuple[RecordSnapshot | None, str, tuple[str, ...]]:
    current, status, reasons = canonical_reread_relaymem_slp_queue_candidate(
        queue_root,
        candidate,
        now=now,
    )
    return current, status, _reason_ids(reasons)


def _resolve_character_scope(
    config: RelayLMConfig,
    *,
    namespace: object,
    explicit_character_id: str | None,
    configured_store_root: str,
) -> tuple[str | None, str | None, tuple[str, ...]]:
    character_id, store_root, reasons = resolve_relaymem_slp_queue_character_scope(
        config,
        namespace=namespace,
        explicit_character_id=explicit_character_id,
        configured_store_root=configured_store_root,
    )
    return character_id, store_root, _reason_ids(reasons)


def _result(
    status: O0Status,
    exit_category: ExitCategory,
    *,
    selected: bool = False,
    eligible: bool = False,
    canonical_reread_performed: bool = False,
    character_scope_resolved: bool = False,
    c2_result: RelayMEMSLPOneQueuedJobRunnerResult | None = None,
    reasons: object = (),
) -> RelayLMLocalWorkerOnceResult:
    return RelayLMLocalWorkerOnceResult(
        schema_version=RESULT_SCHEMA,
        status=status,
        runtime_private=True,
        content_included=False,
        exit_category=exit_category,
        selected=selected,
        eligible=eligible,
        canonical_reread_performed=canonical_reread_performed,
        character_scope_resolved=character_scope_resolved,
        c2_result=c2_result,
        reason_ids=_reason_ids(reasons),
    )


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
        if len(output) >= _MAX_REASONS:
            break
    return tuple(output)


__all__ = [
    "MAX_DISCOVERY_MAX_ENTRIES",
    "PROJECTION_SCHEMA",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "RelayLMLocalWorkerOnceProjection",
    "RelayLMLocalWorkerOnceRequest",
    "RelayLMLocalWorkerOnceResult",
    "execute_local_worker_once",
    "exit_code_for_local_worker_once",
    "project_local_worker_once",
]
