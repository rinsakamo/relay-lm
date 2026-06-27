"""O1F validation-only helpers for the bounded local scheduler stack.

This module inspects existing O1E/O1D2/O1D1 and B3/I1-G boundaries. It does
not add polling, sleeping, daemon behavior, service supervision, worker pools,
queue lifecycle authority, or memory mutation.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
import re
from typing import Final, Literal

from .config import RelayLMConfig
from .relaymem_slp_durable_finalization_store import RelayMEMSLPDurableFinalizationStore
from .relaymem_slp_primary_worker_source_registry import RelayMEMSLPPrimaryWorkerSourceRegistry
from .relaymem_slp_queue_record import ALL_STATES, FILENAME_PREFIX, parse_timestamp
from .relaymem_slp_queue_storage import acquire_queue_lock, open_queue_root, read_record_snapshot, release_queue_lock
from .relaymem_slp_scheduler_operations import (
    SchedulerCancellationToken,
    SchedulerOperationalControlsResult,
    run_relaymem_slp_scheduler_operational_controls_once,
)
from .relaymem_slp_scheduler_policy import SchedulerPolicyState

VALIDATION_RESULT_SCHEMA: Final = "relaylm.local_scheduler_operational_validation_result.v0"
VALIDATION_PROJECTION_SCHEMA: Final = "relaylm.local_scheduler_operational_validation_projection.v0"
MAX_VALIDATION_REASON_IDS: Final = 16
MAX_VALIDATION_CATEGORIES: Final = 16
MAX_VALIDATION_SCAN_ENTRIES: Final = 4096
MAX_VALIDATION_PROJECTION_BYTES: Final = 8192
_REASON_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_QUEUE_FILENAME_RE: Final = re.compile(rf"^{re.escape(FILENAME_PREFIX)}[0-9a-f]{{64}}\.json$")

ValidationStatus = Literal[
    "validated",
    "invalid_input",
    "unsafe",
    "operation_unsafe",
    "content_leakage_blocked",
    "boundedness_failed",
]

FORBIDDEN_PUBLIC_TOKENS: Final = (
    "O1F_PRIVATE_CONTENT_CANARY",
    "O1F_RAW_EXCEPTION_CANARY",
    "O1F_PRIVATE_PATH_CANARY",
    "slp-job-v0:",
    "slp-dispatch-v0:",
    "lease-v0-",
    "protected_source",
    "visible_response",
    "backend_text",
    "memory_body",
    "raw_exception",
    "private_delegate_result",
)


@dataclass(frozen=True, repr=False)
class SchedulerOperationalValidationResult:
    """Bounded content-free validation result for O1F smoke/workflow use."""

    status: ValidationStatus
    categories: tuple[str, ...] = ()
    operation_status: str = "not_invoked"
    stale_recovery_status: str = "not_invoked"
    scheduler_policy_status: str = "not_invoked"
    scheduler_round_invoked: bool = False
    scanned_entry_count: int = 0
    checked_candidate_count: int = 0
    unsafe: bool = False
    bounded_reason_ids: tuple[str, ...] = ()
    operation_result: SchedulerOperationalControlsResult | None = field(default=None, repr=False, compare=False)
    schema_version: str = field(default=VALIDATION_RESULT_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if self.status not in {
            "validated",
            "invalid_input",
            "unsafe",
            "operation_unsafe",
            "content_leakage_blocked",
            "boundedness_failed",
        }:
            raise ValueError("scheduler_operational_validation_status_invalid")
        for name in ("scheduler_round_invoked", "unsafe"):
            if type(getattr(self, name)) is not bool:
                raise TypeError("scheduler_operational_validation_bool_invalid")
        for name in ("scanned_entry_count", "checked_candidate_count"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= MAX_VALIDATION_SCAN_ENTRIES:
                raise ValueError("scheduler_operational_validation_count_invalid")
        if self.operation_result is not None and type(self.operation_result) is not SchedulerOperationalControlsResult:
            raise TypeError("exact_scheduler_operational_result_required")
        object.__setattr__(self, "categories", _reason_ids(self.categories, maximum=MAX_VALIDATION_CATEGORIES))
        object.__setattr__(self, "bounded_reason_ids", _reason_ids(self.bounded_reason_ids, maximum=MAX_VALIDATION_REASON_IDS))

    def __repr__(self) -> str:
        return (
            "SchedulerOperationalValidationResult("
            f"status={self.status!r}, operation_status={self.operation_status!r}, "
            f"unsafe={self.unsafe!r}, private_values_omitted=True)"
        )

    def projection(self) -> Mapping[str, object]:
        return {
            "schema_version": VALIDATION_PROJECTION_SCHEMA,
            "status": self.status,
            "operation_status": self.operation_status,
            "stale_recovery_status": self.stale_recovery_status,
            "scheduler_policy_status": self.scheduler_policy_status,
            "scheduler_round_invoked": self.scheduler_round_invoked,
            "unsafe": self.unsafe,
            "scanned_entry_count": self.scanned_entry_count,
            "checked_candidate_count": self.checked_candidate_count,
            "categories": list(self.categories),
            "bounded_reason_ids": list(self.bounded_reason_ids),
        }


def validate_scheduler_operational_boundary_once(
    *,
    config: RelayLMConfig,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None = None,
    now: datetime | None = None,
    policy_state: SchedulerPolicyState | None = None,
    cancellation: SchedulerCancellationToken | object | None = None,
    fault_injector: object | None = None,
) -> SchedulerOperationalValidationResult:
    """Run one existing O1E invocation, then validate only its public boundary."""

    if type(config) is not RelayLMConfig:
        return _validation_result("invalid_input", ("operational_validation_config_invalid",), unsafe=True)
    if registry is not None and type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _validation_result("invalid_input", ("operational_validation_registry_invalid",), unsafe=True)
    if now is not None and not _valid_now(now):
        return _validation_result("invalid_input", ("operational_validation_now_invalid",), unsafe=True)
    if policy_state is not None and type(policy_state) is not SchedulerPolicyState:
        return _validation_result("invalid_input", ("operational_validation_policy_state_invalid",), unsafe=True)
    if fault_injector is not None and not callable(fault_injector):
        return _validation_result("invalid_input", ("operational_validation_fault_injector_invalid",), unsafe=True)

    try:
        operation = run_relaymem_slp_scheduler_operational_controls_once(
            config=config,
            registry=registry,
            now=now,
            policy_state=policy_state,
            cancellation=cancellation,  # type: ignore[arg-type]
            fault_injector=fault_injector,  # type: ignore[arg-type]
        )
    except Exception:
        return _validation_result("unsafe", ("operational_validation_invocation_failed",), unsafe=True)
    if type(operation) is not SchedulerOperationalControlsResult:
        return _validation_result("unsafe", ("operational_validation_operation_result_invalid",), unsafe=True)

    projection = operation.projection()
    leakage = validate_content_free_projection(projection, repr(operation))
    if leakage:
        return _from_operation(operation, "content_leakage_blocked", ("leakage",), leakage, unsafe=True)
    bounded = validate_bounded_public_projection(projection)
    if bounded:
        return _from_operation(operation, "boundedness_failed", ("boundedness",), bounded, unsafe=True)
    if operation.unsafe:
        return _from_operation(
            operation,
            "operation_unsafe",
            ("operation",),
            tuple(operation.bounded_reason_ids) or ("scheduler_operation_unsafe",),
            unsafe=True,
        )
    return _from_operation(operation, "validated", ("operation",), ("scheduler_operational_boundary_validated",), unsafe=False)


def validate_queue_root_inventory(
    *,
    queue_root: str | None,
    max_scan_entries: int = MAX_VALIDATION_SCAN_ENTRIES,
    now: datetime | None = None,
) -> SchedulerOperationalValidationResult:
    """Read-only bounded validation of B3 queue files using queue storage authority."""

    if type(max_scan_entries) is not int or not 1 <= max_scan_entries <= MAX_VALIDATION_SCAN_ENTRIES:
        return _validation_result("invalid_input", ("operational_validation_scan_limit_invalid",), unsafe=True)
    if now is not None and not _valid_now(now):
        return _validation_result("invalid_input", ("operational_validation_now_invalid",), unsafe=True)
    root_fd, root_reasons = open_queue_root(queue_root)
    if root_fd is None:
        return _validation_result("unsafe", root_reasons, categories=("corruption",), unsafe=True)

    scanned = 0
    checked = 0
    reasons: list[str] = []
    try:
        lock_error = acquire_queue_lock(root_fd, exclusive=False)
        if lock_error:
            return _validation_result("unsafe", (lock_error,), categories=("concurrency",), unsafe=True)
        try:
            try:
                iterator = os.scandir(root_fd)
            except OSError:
                return _validation_result("unsafe", ("operational_validation_queue_scan_failed",), categories=("corruption",), unsafe=True)
            with iterator:
                for entry in iterator:
                    scanned += 1
                    if scanned > max_scan_entries:
                        return _validation_result(
                            "unsafe",
                            ("operational_validation_scan_limit_exceeded",),
                            categories=("saturation",),
                            scanned=MAX_VALIDATION_SCAN_ENTRIES,
                            checked=checked,
                            unsafe=True,
                        )
                    name = entry.name
                    if type(name) is not str or _QUEUE_FILENAME_RE.fullmatch(name) is None:
                        continue
                    snapshot, status, read_reasons = read_record_snapshot(root_fd, name)
                    checked += 1
                    if snapshot is None or status != "ok":
                        reasons.extend(read_reasons or ("operational_validation_queue_record_invalid",))
                        break
                    reasons.extend(_validate_queue_record_operational_shape(snapshot.record, now=now))
                    if reasons:
                        break
        finally:
            release_queue_lock(root_fd)
    finally:
        os.close(root_fd)

    if reasons:
        return _validation_result(
            "unsafe",
            tuple(reasons),
            categories=("corruption",),
            scanned=min(scanned, MAX_VALIDATION_SCAN_ENTRIES),
            checked=min(checked, MAX_VALIDATION_SCAN_ENTRIES),
            unsafe=True,
        )
    return _validation_result(
        "validated",
        ("queue_inventory_validated",),
        categories=("corruption", "saturation"),
        scanned=scanned,
        checked=checked,
        unsafe=False,
    )


def validate_durable_finalization_locator(
    *,
    sealed_root: str | None,
    locator_digest: str,
) -> SchedulerOperationalValidationResult:
    """Read one sealed I1-G locator through the existing immutable store reader."""

    if type(sealed_root) is not str or type(locator_digest) is not str:
        return _validation_result("invalid_input", ("durable_finalization_validation_input_invalid",), unsafe=True)
    try:
        store = RelayMEMSLPDurableFinalizationStore(sealed_root)
        result = store.read_evidence(locator_digest)
    except Exception:
        return _validation_result("unsafe", ("durable_finalization_validation_failed",), categories=("corruption",), unsafe=True)
    reasons = tuple(result.blocked_reasons) or (f"durable_finalization_{result.status}",)
    if result.status == "loaded" and result.sealed and result.replayable:
        return _validation_result("validated", ("sealed_i1g_record_validated",), categories=("restart",), unsafe=False)
    if result.status in {"missing", "blocked"} and not result.record_present:
        return _validation_result("validated", reasons, categories=("restart",), unsafe=False)
    return _validation_result("unsafe", reasons, categories=("corruption", "restart"), unsafe=True)


def validate_source_queue_correlation(
    *,
    source_dispatch_idempotency_key: object,
    queue_dispatch_idempotency_key: object,
) -> SchedulerOperationalValidationResult:
    """Validate one source/queue correlation equality without projecting IDs."""

    if type(source_dispatch_idempotency_key) is not str or type(queue_dispatch_idempotency_key) is not str:
        return _validation_result("invalid_input", ("source_queue_correlation_input_invalid",), categories=("correlation",), unsafe=True)
    if source_dispatch_idempotency_key != queue_dispatch_idempotency_key:
        return _validation_result("unsafe", ("source_queue_correlation_mismatch",), categories=("correlation",), unsafe=True)
    return _validation_result("validated", ("source_queue_correlation_validated",), categories=("correlation",), unsafe=False)


def validate_content_free_projection(*values: object) -> tuple[str, ...]:
    """Return bounded leakage reasons if a public value contains private tokens."""

    try:
        text = json.dumps(values, ensure_ascii=True, sort_keys=True, default=str)
    except (TypeError, ValueError, RecursionError):
        return ("projection_encoding_failed",)
    lowered = text.lower()
    for token in FORBIDDEN_PUBLIC_TOKENS:
        if token.lower() in lowered:
            return ("projection_private_token_leaked",)
    return ()


def validate_bounded_public_projection(projection: object) -> tuple[str, ...]:
    if not isinstance(projection, Mapping):
        return ("projection_shape_invalid",)
    try:
        encoded = json.dumps(projection, ensure_ascii=True, sort_keys=True, default=str)
    except (TypeError, ValueError, RecursionError):
        return ("projection_encoding_failed",)
    if len(encoded.encode("utf-8")) > MAX_VALIDATION_PROJECTION_BYTES:
        return ("projection_size_exceeded",)
    reasons = projection.get("bounded_reason_ids", [])
    if not isinstance(reasons, list) or len(reasons) > MAX_VALIDATION_REASON_IDS:
        return ("projection_reason_bound_invalid",)
    for reason in reasons:
        if type(reason) is not str or _REASON_RE.fullmatch(reason) is None:
            return ("projection_reason_invalid",)
    categories = projection.get("categories", [])
    if categories != []:
        if not isinstance(categories, list) or len(categories) > MAX_VALIDATION_CATEGORIES:
            return ("projection_category_bound_invalid",)
        for category in categories:
            if type(category) is not str or _REASON_RE.fullmatch(category) is None:
                return ("projection_category_invalid",)
    return ()


def _validate_queue_record_operational_shape(record: Mapping[str, object], *, now: datetime | None) -> tuple[str, ...]:
    state = record.get("state")
    if state not in ALL_STATES:
        return ("operational_validation_unsupported_queue_state",)
    if parse_timestamp(record.get("created_at")) is None or parse_timestamp(record.get("updated_at")) is None:
        return ("operational_validation_queue_timestamp_invalid",)
    if state == "claimed":
        if parse_timestamp(record.get("lease_acquired_at")) is None or parse_timestamp(record.get("lease_expires_at")) is None:
            return ("operational_validation_claim_lease_invalid",)
        if not record.get("claim_owner") or not record.get("lease_token"):
            return ("operational_validation_claim_identity_missing",)
    if now is not None and state == "claimed":
        expiry = parse_timestamp(record.get("lease_expires_at"))
        if expiry is None:
            return ("operational_validation_claim_lease_invalid",)
    return ()


def _from_operation(
    operation: SchedulerOperationalControlsResult,
    status: ValidationStatus,
    categories: Sequence[str],
    reasons: Sequence[str],
    *,
    unsafe: bool,
) -> SchedulerOperationalValidationResult:
    projection = operation.projection()
    return SchedulerOperationalValidationResult(
        status=status,
        categories=_reason_ids(categories, maximum=MAX_VALIDATION_CATEGORIES),
        operation_status=operation.status,
        stale_recovery_status=operation.stale_recovery_status,
        scheduler_policy_status=str(projection.get("scheduler_policy_status", "not_invoked")),
        scheduler_round_invoked=operation.scheduler_round_invoked,
        unsafe=unsafe,
        bounded_reason_ids=_reason_ids(reasons, maximum=MAX_VALIDATION_REASON_IDS),
        operation_result=operation,
    )


def _validation_result(
    status: ValidationStatus,
    reasons: Sequence[str],
    *,
    categories: Sequence[str] = (),
    scanned: int = 0,
    checked: int = 0,
    unsafe: bool,
) -> SchedulerOperationalValidationResult:
    return SchedulerOperationalValidationResult(
        status=status,
        categories=_reason_ids(categories, maximum=MAX_VALIDATION_CATEGORIES),
        scanned_entry_count=min(max(scanned, 0), MAX_VALIDATION_SCAN_ENTRIES),
        checked_candidate_count=min(max(checked, 0), MAX_VALIDATION_SCAN_ENTRIES),
        unsafe=unsafe,
        bounded_reason_ids=_reason_ids(reasons, maximum=MAX_VALIDATION_REASON_IDS),
    )


def _reason_ids(values: Sequence[str], *, maximum: int) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        values = ("operational_validation_reason_invalid",)
    output: list[str] = []
    for value in values:
        reason = value if type(value) is str and _REASON_RE.fullmatch(value) else "operational_validation_reason_invalid"
        if reason not in output:
            output.append(reason)
        if len(output) >= maximum:
            break
    if not output:
        output.append("operational_validation_status")
    return tuple(output)


def _valid_now(value: object) -> bool:
    return bool(type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None)


__all__ = [
    "FORBIDDEN_PUBLIC_TOKENS",
    "MAX_VALIDATION_SCAN_ENTRIES",
    "SchedulerOperationalValidationResult",
    "VALIDATION_PROJECTION_SCHEMA",
    "VALIDATION_RESULT_SCHEMA",
    "validate_bounded_public_projection",
    "validate_content_free_projection",
    "validate_durable_finalization_locator",
    "validate_queue_root_inventory",
    "validate_scheduler_operational_boundary_once",
    "validate_source_queue_correlation",
]
