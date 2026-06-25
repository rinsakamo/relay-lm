"""O0 local one-job runner.

This module performs bounded, read-only discovery of at most one eligible durable
RelaySLP queue record and delegates all claim, rehydration, worker, retry,
terminal, and cleanup authority to the existing Phase 6-C2 adapter.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .config import RelayLMConfig
from .relaymem_primary_recall import resolve_relaymem_character_store_root
from .relaymem_slp_one_queued_job_runner import (
    REQUEST_SCHEMA as C2_REQUEST_SCHEMA,
    RelayMEMSLPOneQueuedJobRunnerRequest,
    RelayMEMSLPOneQueuedJobRunnerResult,
    execute_one_queued_relaymem_slp_primary_job,
)
from .relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from .relaymem_slp_queue_record import (
    FILENAME_PREFIX,
    MAX_LEASE_SECONDS,
    is_token,
    parse_timestamp,
)
from .relaymem_slp_queue_storage import (
    RecordSnapshot,
    acquire_queue_lock,
    open_queue_root,
    read_record_snapshot,
    release_queue_lock,
)

REQUEST_SCHEMA = "relaymem.local_worker_once_request.v0"
RESULT_SCHEMA = "relaymem.local_worker_once_result.v0"
PROJECTION_SCHEMA = "relaymem.local_worker_once_projection.v0"

MAX_DISCOVERY_MAX_ENTRIES = 4096
_FILENAME_RE = re.compile(rf"^{re.escape(FILENAME_PREFIX)}[0-9a-f]{{64}}\.json$")
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


@dataclass(frozen=True)
class _Candidate:
    filename: str
    snapshot: RecordSnapshot


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
        source_registry = RelayMEMSLPPrimaryWorkerSourceRegistry(
            max_entries=config.relaymem_slp_source_registry_max_entries,
            ttl_seconds=config.relaymem_slp_source_registry_ttl_seconds,
        )
        c2_request = RelayMEMSLPOneQueuedJobRunnerRequest(
            schema_version=C2_REQUEST_SCHEMA,
            runtime_private=True,
            content_included=False,
            queued_record=dict(current.record),
            source_registry=source_registry,
            character_id=character_id,
            queue_root=queue_root,
            protected_source_root=protected_source_root,
            store_root=store_root,
            claim_owner=config.relaymem_local_worker_claim_owner,
            enabled=True,
            dry_run_only=mode == "dry_run",
            apply_enabled=mode == "apply",
            lease_duration_seconds=config.relaymem_local_worker_lease_duration_seconds,
            protected_source_max_artifact_bytes=(
                config.relaymem_slp_protected_source_max_artifact_bytes
            ),
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
    gates = (
        config.relaymem_local_worker_enabled,
        config.relaymem_local_worker_dry_run_only,
        config.relaymem_local_worker_apply_enabled,
    )
    if any(type(value) is not bool for value in gates):
        return None, ("local_worker_gate_type_invalid",)
    modes = {
        (False, True, False): "disabled",
        (True, True, False): "dry_run",
        (True, False, True): "apply",
    }
    mode = modes.get(gates)
    if mode is None:
        return None, ("local_worker_gate_mode_invalid",)
    if not is_token(config.relaymem_local_worker_claim_owner):
        return None, ("local_worker_claim_owner_invalid",)
    if (
        type(config.relaymem_local_worker_lease_duration_seconds) is not int
        or not 1
        <= config.relaymem_local_worker_lease_duration_seconds
        <= MAX_LEASE_SECONDS
    ):
        return None, ("local_worker_lease_duration_invalid",)
    if (
        type(config.relaymem_local_worker_discovery_max_entries) is not int
        or not 1
        <= config.relaymem_local_worker_discovery_max_entries
        <= MAX_DISCOVERY_MAX_ENTRIES
    ):
        return None, ("local_worker_discovery_limit_invalid",)
    return mode, ()


def _validated_roots(
    config: RelayLMConfig,
) -> tuple[tuple[str, str, str] | None, tuple[str, ...]]:
    values = (
        ("queue_root", config.relaymem_slp_queue_root),
        ("protected_source_root", config.relaymem_slp_protected_source_root),
        ("store_root", config.memory.root_path),
    )
    output: list[str] = []
    reasons: list[str] = []
    for name, value in values:
        if (
            type(value) is not str
            or not value
            or value != value.strip()
            or "\x00" in value
            or not Path(value).is_absolute()
        ):
            reasons.append(f"local_worker_{name}_invalid")
        else:
            output.append(value)
    if reasons:
        return None, _reason_ids(reasons)
    return (output[0], output[1], output[2]), ()


def _discover_candidate(
    queue_root: str,
    *,
    now: datetime,
    max_entries: int,
) -> tuple[_Candidate | None, str, tuple[str, ...]]:
    root_fd, root_reasons = open_queue_root(queue_root)
    if root_fd is None:
        return None, "unsafe", _reason_ids(root_reasons)
    candidates: list[_Candidate] = []
    try:
        lock_error = acquire_queue_lock(root_fd, exclusive=False)
        if lock_error == "queue_lock_busy":
            return None, "busy", (lock_error,)
        if lock_error:
            return None, "unsafe", (lock_error,)
        try:
            scanned = 0
            try:
                iterator = os.scandir(root_fd)
            except OSError:
                return None, "unsafe", ("queue_discovery_failed",)
            with iterator:
                for entry in iterator:
                    scanned += 1
                    if scanned > max_entries:
                        return None, "unsafe", ("queue_discovery_limit_exceeded",)
                    filename = entry.name
                    if type(filename) is not str or _FILENAME_RE.fullmatch(filename) is None:
                        continue
                    snapshot, status, reasons = read_record_snapshot(root_fd, filename)
                    if snapshot is None or status != "ok":
                        return None, "unsafe", _reason_ids(
                            reasons or ("queue_record_discovery_invalid",)
                        )
                    if _eligible(snapshot.record, now):
                        candidates.append(_Candidate(filename, snapshot))
        finally:
            release_queue_lock(root_fd)
    finally:
        os.close(root_fd)
    if not candidates:
        return None, "no_work", ()
    candidates.sort(key=lambda item: item.filename)
    return candidates[0], "selected", ()


def _canonical_reread(
    queue_root: str,
    candidate: _Candidate,
    *,
    now: datetime,
) -> tuple[RecordSnapshot | None, str, tuple[str, ...]]:
    root_fd, root_reasons = open_queue_root(queue_root)
    if root_fd is None:
        return None, "unsafe", _reason_ids(root_reasons)
    try:
        lock_error = acquire_queue_lock(root_fd, exclusive=False)
        if lock_error:
            return None, "changed", ("queue_lock_busy_before_claim",)
        try:
            current, status, reasons = read_record_snapshot(root_fd, candidate.filename)
        finally:
            release_queue_lock(root_fd)
    finally:
        os.close(root_fd)
    if current is None or status != "ok":
        if status == "corrupt":
            return None, "unsafe", _reason_ids(reasons)
        return None, "changed", _reason_ids(reasons or ("queue_candidate_missing",))
    if (
        (current.device, current.inode)
        != (candidate.snapshot.device, candidate.snapshot.inode)
        or current.data != candidate.snapshot.data
        or current.record != candidate.snapshot.record
    ):
        return None, "changed", ("queue_candidate_changed_before_claim",)
    if not _eligible(current.record, now):
        return None, "changed", ("queue_candidate_no_longer_eligible",)
    return current, "ok", ()


def _eligible(record: dict[str, object], now: datetime) -> bool:
    if record.get("state") != "queued":
        return False
    retry_not_before = record.get("retry_not_before")
    if retry_not_before is None:
        return True
    parsed = parse_timestamp(retry_not_before)
    return parsed is not None and parsed <= now


def _resolve_character_scope(
    config: RelayLMConfig,
    *,
    namespace: object,
    explicit_character_id: str | None,
    configured_store_root: str,
) -> tuple[str | None, str | None, tuple[str, ...]]:
    if not is_token(namespace):
        return None, None, ("local_worker_namespace_invalid",)
    pairs: set[tuple[str, str]] = set()
    for route in config.model_routes.values():
        character_id = route.character_id
        memory_namespace = route.memory_namespace
        if (
            is_token(character_id)
            and is_token(memory_namespace)
            and character_id in config.characters
        ):
            pairs.add((character_id, memory_namespace))
    assert type(namespace) is str
    if explicit_character_id is not None:
        if (explicit_character_id, namespace) not in pairs:
            return None, None, ("local_worker_character_namespace_mismatch",)
        character_id = explicit_character_id
    else:
        matches = sorted({char for char, ns in pairs if ns == namespace})
        if not matches:
            return None, None, ("local_worker_character_scope_not_found",)
        if len(matches) != 1:
            return None, None, ("local_worker_character_scope_ambiguous",)
        character_id = matches[0]
    store_root = resolve_relaymem_character_store_root(
        configured_store_root,
        character_id,
    )
    if store_root is None or not Path(store_root).is_absolute():
        return None, None, ("local_worker_character_store_root_unavailable",)
    return character_id, store_root, ()


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
