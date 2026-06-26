"""Shared bounded queue-candidate adapter for O0 and O1C.

This module owns only secure bounded discovery, eligibility classification,
canonical reread, character/store resolution, and exact C2 request
construction.  It never mutates queue state or invokes C2.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

from .config import RelayLMConfig
from .relaymem_primary_recall import resolve_relaymem_character_store_root
from .relaymem_slp_one_queued_job_runner import (
    REQUEST_SCHEMA as C2_REQUEST_SCHEMA,
    RelayMEMSLPOneQueuedJobRunnerRequest,
)
from .relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from .relaymem_slp_protected_source_store import MAX_ARTIFACT_BYTES_LIMIT
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

MAX_DISCOVERY_MAX_ENTRIES = 4096
_FILENAME_RE = re.compile(rf"^{re.escape(FILENAME_PREFIX)}[0-9a-f]{{64}}\.json$")

WorkerMode = Literal["disabled", "dry_run", "apply"]
DiscoveryStatus = Literal["selected", "no_work", "future_retry_only", "busy", "unsafe"]
RereadStatus = Literal["ok", "changed", "unsafe"]
FaultInjector = Callable[[str], None]


@dataclass(frozen=True, repr=False)
class QueueCandidate:
    filename: str = field(repr=False)
    snapshot: RecordSnapshot = field(repr=False)

    def __repr__(self) -> str:
        return "QueueCandidate(filename_omitted=True, snapshot_omitted=True)"


@dataclass(frozen=True, repr=False)
class QueueDiscoveryResult:
    status: DiscoveryStatus
    candidate_observed: bool
    candidate_selected: bool
    future_work_hint_present: bool
    claimed_observed: bool
    terminal_observed: bool
    reason_ids: tuple[str, ...] = ()
    candidate: QueueCandidate | None = field(default=None, repr=False, compare=False)
    earliest_retry_not_before: datetime | None = field(
        default=None, repr=False, compare=False
    )

    def __repr__(self) -> str:
        return (
            "QueueDiscoveryResult("
            f"status={self.status!r}, candidate_observed={self.candidate_observed!r}, "
            f"candidate_selected={self.candidate_selected!r}, "
            f"future_work_hint_present={self.future_work_hint_present!r}, "
            "candidate_omitted=True, retry_timestamp_omitted=True)"
        )


def validate_local_worker_mode(
    config: RelayLMConfig,
) -> tuple[WorkerMode | None, tuple[str, ...]]:
    gates = (
        config.relaymem_local_worker_enabled,
        config.relaymem_local_worker_dry_run_only,
        config.relaymem_local_worker_apply_enabled,
    )
    if any(type(value) is not bool for value in gates):
        return None, ("local_worker_gate_type_invalid",)
    modes: dict[tuple[bool, bool, bool], WorkerMode] = {
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
    if (
        type(config.relaymem_slp_source_registry_max_entries) is not int
        or config.relaymem_slp_source_registry_max_entries < 1
    ):
        return None, ("local_worker_source_registry_limit_invalid",)
    if (
        type(config.relaymem_slp_source_registry_ttl_seconds) is not int
        or config.relaymem_slp_source_registry_ttl_seconds < 1
    ):
        return None, ("local_worker_source_registry_ttl_invalid",)
    if (
        type(config.relaymem_slp_protected_source_max_artifact_bytes) is not int
        or not 1
        <= config.relaymem_slp_protected_source_max_artifact_bytes
        <= MAX_ARTIFACT_BYTES_LIMIT
    ):
        return None, ("local_worker_protected_source_bound_invalid",)
    return mode, ()


def validate_configured_roots(
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
        return None, tuple(reasons)
    return (output[0], output[1], output[2]), ()


def discover_relaymem_slp_queue_candidate(
    queue_root: str,
    *,
    now: datetime,
    max_entries: int,
    fault_injector: FaultInjector | None = None,
) -> QueueDiscoveryResult:
    if not _valid_now(now):
        return _discovery("unsafe", reasons=("queue_discovery_now_invalid",))
    root_fd, root_reasons = open_queue_root(queue_root)
    if root_fd is None:
        return _discovery("unsafe", reasons=root_reasons)
    candidates: list[QueueCandidate] = []
    candidate_observed = False
    claimed_observed = False
    terminal_observed = False
    earliest_future: datetime | None = None
    try:
        _fault(fault_injector, "after_root_open_before_scan")
        lock_error = acquire_queue_lock(root_fd, exclusive=False)
        if lock_error == "queue_lock_busy":
            return _discovery(
                "busy",
                candidate_observed=False,
                reasons=(lock_error,),
            )
        if lock_error:
            return _discovery("unsafe", reasons=(lock_error,))
        try:
            scanned = 0
            try:
                iterator = os.scandir(root_fd)
            except OSError:
                return _discovery("unsafe", reasons=("queue_discovery_failed",))
            with iterator:
                for entry in iterator:
                    _fault(fault_injector, "during_scan")
                    scanned += 1
                    if scanned > max_entries:
                        return _discovery(
                            "unsafe",
                            candidate_observed=candidate_observed,
                            claimed_observed=claimed_observed,
                            terminal_observed=terminal_observed,
                            earliest_future=earliest_future,
                            reasons=("queue_discovery_limit_exceeded",),
                        )
                    filename = entry.name
                    if type(filename) is not str or _FILENAME_RE.fullmatch(filename) is None:
                        continue
                    candidate_observed = True
                    snapshot, status, reasons = read_record_snapshot(root_fd, filename)
                    if snapshot is None or status != "ok":
                        return _discovery(
                            "unsafe",
                            candidate_observed=True,
                            claimed_observed=claimed_observed,
                            terminal_observed=terminal_observed,
                            earliest_future=earliest_future,
                            reasons=reasons or ("queue_record_discovery_invalid",),
                        )
                    state = snapshot.record.get("state")
                    if state == "queued":
                        retry_not_before = snapshot.record.get("retry_not_before")
                        if retry_not_before is None:
                            candidates.append(QueueCandidate(filename, snapshot))
                        else:
                            parsed = parse_timestamp(retry_not_before)
                            if parsed is None:
                                return _discovery(
                                    "unsafe",
                                    candidate_observed=True,
                                    reasons=("queue_retry_timestamp_invalid",),
                                )
                            if parsed <= now:
                                candidates.append(QueueCandidate(filename, snapshot))
                            elif earliest_future is None or parsed < earliest_future:
                                earliest_future = parsed
                    elif state == "claimed":
                        claimed_observed = True
                    else:
                        terminal_observed = True
            _fault(fault_injector, "after_scan_before_selection")
        finally:
            release_queue_lock(root_fd)
    finally:
        os.close(root_fd)

    if candidates:
        candidates.sort(key=lambda item: item.filename)
        return _discovery(
            "selected",
            candidate_observed=candidate_observed,
            candidate=candidates[0],
            claimed_observed=claimed_observed,
            terminal_observed=terminal_observed,
            earliest_future=earliest_future,
        )
    if earliest_future is not None:
        return _discovery(
            "future_retry_only",
            candidate_observed=candidate_observed,
            claimed_observed=claimed_observed,
            terminal_observed=terminal_observed,
            earliest_future=earliest_future,
        )
    return _discovery(
        "no_work",
        candidate_observed=candidate_observed,
        claimed_observed=claimed_observed,
        terminal_observed=terminal_observed,
    )


def canonical_reread_relaymem_slp_queue_candidate(
    queue_root: str,
    candidate: QueueCandidate,
    *,
    now: datetime,
    fault_injector: FaultInjector | None = None,
) -> tuple[RecordSnapshot | None, RereadStatus, tuple[str, ...]]:
    if type(candidate) is not QueueCandidate or not _valid_now(now):
        return None, "unsafe", ("queue_candidate_reread_input_invalid",)
    root_fd, root_reasons = open_queue_root(queue_root)
    if root_fd is None:
        return None, "unsafe", tuple(root_reasons)
    try:
        lock_error = acquire_queue_lock(root_fd, exclusive=False)
        if lock_error == "queue_lock_busy":
            return None, "changed", ("queue_lock_busy_before_claim",)
        if lock_error:
            return None, "unsafe", (lock_error,)
        try:
            _fault(fault_injector, "during_canonical_reread")
            current, status, reasons = read_record_snapshot(root_fd, candidate.filename)
        finally:
            release_queue_lock(root_fd)
    finally:
        os.close(root_fd)
    if current is None or status != "ok":
        if status == "corrupt":
            return None, "unsafe", tuple(reasons)
        return None, "changed", tuple(reasons or ("queue_candidate_missing",))
    if (
        (current.device, current.inode)
        != (candidate.snapshot.device, candidate.snapshot.inode)
        or current.data != candidate.snapshot.data
        or current.record != candidate.snapshot.record
    ):
        return None, "changed", ("queue_candidate_changed_before_claim",)
    due, due_reasons = queued_record_is_due(current.record, now)
    if due_reasons:
        return None, "unsafe", due_reasons
    if not due:
        return None, "changed", ("queue_candidate_no_longer_eligible",)
    return current, "ok", ()


def queued_record_is_due(
    record: dict[str, object], now: datetime
) -> tuple[bool, tuple[str, ...]]:
    if record.get("state") != "queued":
        return False, ()
    retry_not_before = record.get("retry_not_before")
    if retry_not_before is None:
        return True, ()
    parsed = parse_timestamp(retry_not_before)
    if parsed is None:
        return False, ("queue_retry_timestamp_invalid",)
    return parsed <= now, ()


def resolve_relaymem_slp_queue_character_scope(
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


def build_relaymem_slp_one_queued_job_request(
    *,
    config: RelayLMConfig,
    queued_record: dict[str, object],
    character_id: str,
    queue_root: str,
    protected_source_root: str,
    store_root: str,
    mode: Literal["dry_run", "apply"],
) -> RelayMEMSLPOneQueuedJobRunnerRequest:
    if mode not in {"dry_run", "apply"}:
        raise ValueError("queue_candidate_request_mode_invalid")
    source_registry = RelayMEMSLPPrimaryWorkerSourceRegistry(
        max_entries=config.relaymem_slp_source_registry_max_entries,
        ttl_seconds=config.relaymem_slp_source_registry_ttl_seconds,
    )
    return RelayMEMSLPOneQueuedJobRunnerRequest(
        schema_version=C2_REQUEST_SCHEMA,
        runtime_private=True,
        content_included=False,
        queued_record=dict(queued_record),
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


def _valid_now(value: object) -> bool:
    return (
        type(value) is datetime
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def _fault(fault_injector: FaultInjector | None, seam: str) -> None:
    if fault_injector is not None:
        fault_injector(seam)


def _discovery(
    status: DiscoveryStatus,
    *,
    candidate_observed: bool = False,
    candidate: QueueCandidate | None = None,
    claimed_observed: bool = False,
    terminal_observed: bool = False,
    earliest_future: datetime | None = None,
    reasons: tuple[str, ...] | list[str] = (),
) -> QueueDiscoveryResult:
    return QueueDiscoveryResult(
        status=status,
        candidate_observed=candidate_observed,
        candidate_selected=candidate is not None,
        future_work_hint_present=earliest_future is not None,
        claimed_observed=claimed_observed,
        terminal_observed=terminal_observed,
        reason_ids=tuple(reasons),
        candidate=candidate,
        earliest_retry_not_before=earliest_future,
    )


__all__ = [
    "DiscoveryStatus",
    "FaultInjector",
    "MAX_DISCOVERY_MAX_ENTRIES",
    "QueueCandidate",
    "QueueDiscoveryResult",
    "RereadStatus",
    "WorkerMode",
    "build_relaymem_slp_one_queued_job_request",
    "canonical_reread_relaymem_slp_queue_candidate",
    "discover_relaymem_slp_queue_candidate",
    "queued_record_is_due",
    "resolve_relaymem_slp_queue_character_scope",
    "validate_configured_roots",
    "validate_local_worker_mode",
]
