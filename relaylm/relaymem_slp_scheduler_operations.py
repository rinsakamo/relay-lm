"""O1E bounded scheduler operational controls.

One explicit caller invocation may run cancellation checkpoints, at most one B3
stale-claim recovery, and at most one O1D2/O1D1 scheduler round. This module
never sleeps, polls, loops, daemonizes, starts threads, or supervises services.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
import re
import signal
from typing import Final, Iterator, Literal

from .config import RelayLMConfig
from .relaymem_slp_primary_worker_source_registry import RelayMEMSLPPrimaryWorkerSourceRegistry
from .relaymem_slp_queue_record import FILENAME_PREFIX, parse_timestamp
from .relaymem_slp_queue_state import (
    RelayMEMSLPQueueStateTransitionResult,
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)
from .relaymem_slp_queue_storage import (
    RecordSnapshot,
    acquire_queue_lock,
    open_queue_root,
    read_record_snapshot,
    release_queue_lock,
)
from .relaymem_slp_scheduler_policy import (
    SchedulerPolicyRoundResult,
    SchedulerPolicyState,
    run_relaymem_slp_scheduler_round_once_with_policy,
)

OPERATIONS_RESULT_SCHEMA: Final = "relaylm.local_scheduler_operational_controls_result.v0"
OPERATIONS_PROJECTION_SCHEMA: Final = "relaylm.local_scheduler_operational_controls_projection.v0"
MAX_OPERATION_REASON_IDS: Final = 16
MAX_STALE_SCAN_ENTRIES: Final = 4096
_REASON_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_QUEUE_FILENAME_RE: Final = re.compile(rf"^{re.escape(FILENAME_PREFIX)}[0-9a-f]{{64}}\.json$")

OperationalMode = Literal["disabled", "dry_run", "apply"]
OperationalStatus = Literal[
    "disabled",
    "dry_run_ready",
    "invalid_input",
    "invalid_config",
    "cancelled_before_start",
    "cancelled_before_stale_recovery",
    "cancelled_before_scheduler_round",
    "cancelled_after_scheduler_round",
    "shutdown_requested",
    "scheduler_round_completed",
    "completed",
    "unexpected_failure",
]
StaleRecoveryStatus = Literal[
    "not_invoked",
    "stale_recovery_disabled",
    "stale_recovery_dry_run_ready",
    "stale_recovery_attempted",
    "stale_recovery_no_candidate",
    "stale_recovery_failed",
]
FaultInjector = Callable[[str], None]
CancellationProbe = Callable[[], bool]
_OPERATIONAL_STATUSES: Final = frozenset({
    "disabled",
    "dry_run_ready",
    "invalid_input",
    "invalid_config",
    "cancelled_before_start",
    "cancelled_before_stale_recovery",
    "cancelled_before_scheduler_round",
    "cancelled_after_scheduler_round",
    "shutdown_requested",
    "scheduler_round_completed",
    "completed",
    "unexpected_failure",
})
_STALE_RECOVERY_STATUSES: Final = frozenset({
    "not_invoked",
    "stale_recovery_disabled",
    "stale_recovery_dry_run_ready",
    "stale_recovery_attempted",
    "stale_recovery_no_candidate",
    "stale_recovery_failed",
})


@dataclass(frozen=True, repr=False)
class SchedulerCancellationToken:
    """Small explicit cancellation probe wrapper."""

    is_cancelled: CancellationProbe = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not callable(self.is_cancelled):
            raise TypeError("scheduler_cancellation_probe_required")

    def requested(self) -> bool:
        try:
            return bool(self.is_cancelled())
        except Exception:
            return True

    def __repr__(self) -> str:
        return "SchedulerCancellationToken(probe_omitted=True)"


class SchedulerSignalCancellationAdapter:
    """Opt-in SIGINT/SIGTERM adapter; no threads, timers, loops, or service."""

    def __init__(self) -> None:
        self._requested = False
        self.token = SchedulerCancellationToken(lambda: self._requested)

    def request_shutdown(self, signum: int | None = None, frame: object | None = None) -> None:
        del signum, frame
        self._requested = True

    @contextmanager
    def installed(self, signals: Sequence[int] = (signal.SIGINT, signal.SIGTERM)) -> Iterator["SchedulerSignalCancellationAdapter"]:
        previous: dict[int, object] = {}
        for signum in signals:
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, self.request_shutdown)
        try:
            yield self
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)


@dataclass(frozen=True, repr=False)
class _StaleCandidate:
    record: Mapping[str, object] = field(repr=False, compare=False)
    snapshot: RecordSnapshot = field(repr=False, compare=False)

    def __repr__(self) -> str:
        return "_StaleCandidate(record_omitted=True, snapshot_omitted=True)"


@dataclass(frozen=True, repr=False)
class SchedulerOperationalControlsResult:
    """Runtime result with only a bounded content-free public projection."""

    status: OperationalStatus
    mode: OperationalMode | str
    stale_recovery_status: StaleRecoveryStatus = "not_invoked"
    stale_recovery_enabled: bool = False
    stale_recovery_attempted: bool = False
    stale_recovery_applied: bool = False
    scheduler_round_invoked: bool = False
    scheduler_policy_result: SchedulerPolicyRoundResult | None = field(default=None, repr=False, compare=False)
    stale_recovery_result: RelayMEMSLPQueueStateTransitionResult | None = field(default=None, repr=False, compare=False)
    cancelled: bool = False
    shutdown_requested: bool = False
    unsafe: bool = False
    bounded_reason_ids: tuple[str, ...] = ()
    schema_version: str = field(default=OPERATIONS_RESULT_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if self.status not in _OPERATIONAL_STATUSES:
            raise ValueError("scheduler_operational_status_invalid")
        if self.mode not in {"disabled", "dry_run", "apply", "invalid"}:
            raise ValueError("scheduler_operational_mode_invalid")
        if self.stale_recovery_status not in _STALE_RECOVERY_STATUSES:
            raise ValueError("scheduler_stale_recovery_status_invalid")
        for name in (
            "stale_recovery_enabled",
            "stale_recovery_attempted",
            "stale_recovery_applied",
            "scheduler_round_invoked",
            "cancelled",
            "shutdown_requested",
            "unsafe",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError("scheduler_operational_bool_invalid")
        if self.scheduler_policy_result is not None and type(self.scheduler_policy_result) is not SchedulerPolicyRoundResult:
            raise TypeError("exact_scheduler_policy_result_required")
        if self.stale_recovery_result is not None and type(self.stale_recovery_result) is not RelayMEMSLPQueueStateTransitionResult:
            raise TypeError("exact_stale_recovery_result_required")
        object.__setattr__(
            self,
            "bounded_reason_ids",
            _reason_ids(self.bounded_reason_ids, maximum=MAX_OPERATION_REASON_IDS),
        )

    def __repr__(self) -> str:
        return (
            "SchedulerOperationalControlsResult("
            f"status={self.status!r}, mode={self.mode!r}, "
            f"stale_recovery_status={self.stale_recovery_status!r}, "
            f"scheduler_round_invoked={self.scheduler_round_invoked!r}, "
            "private_results_omitted=True)"
        )

    def projection(self) -> Mapping[str, object]:
        policy = self.scheduler_policy_result
        policy_projection = policy.projection() if policy is not None else None
        return {
            "schema_version": OPERATIONS_PROJECTION_SCHEMA,
            "status": self.status,
            "mode": self.mode,
            "stale_recovery_status": self.stale_recovery_status,
            "stale_recovery_enabled": self.stale_recovery_enabled,
            "stale_recovery_attempted": self.stale_recovery_attempted,
            "stale_recovery_applied": self.stale_recovery_applied,
            "scheduler_round_invoked": self.scheduler_round_invoked,
            "scheduler_policy_status": policy.status if policy is not None else "not_invoked",
            "scheduler_round_status": (
                policy_projection.get("round_status") if type(policy_projection) is dict else "not_invoked"
            ),
            "cancelled": self.cancelled,
            "shutdown_requested": self.shutdown_requested,
            "unsafe": self.unsafe,
            "bounded_reason_ids": list(self.bounded_reason_ids),
        }


def run_relaymem_slp_scheduler_operational_controls_once(
    *,
    config: RelayLMConfig,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None = None,
    now: datetime | None = None,
    policy_state: SchedulerPolicyState | None = None,
    cancellation: SchedulerCancellationToken | CancellationProbe | None = None,
    fault_injector: FaultInjector | None = None,
) -> SchedulerOperationalControlsResult:
    """Run one bounded O1E operational-control invocation and return immediately."""

    if type(config) is not RelayLMConfig:
        return _result("invalid_input", "invalid", reasons=("exact_relaylm_config_required",), unsafe=True)
    if registry is not None and type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _result("invalid_input", "invalid", reasons=("exact_source_registry_required",), unsafe=True)
    if now is not None and not _valid_now(now):
        return _result("invalid_input", "invalid", reasons=("scheduler_operational_now_invalid",), unsafe=True)
    if policy_state is not None and type(policy_state) is not SchedulerPolicyState:
        return _result("invalid_input", "invalid", reasons=("exact_scheduler_policy_state_required",), unsafe=True)
    if fault_injector is not None and not callable(fault_injector):
        return _result("invalid_input", "invalid", reasons=("scheduler_operational_fault_injector_invalid",), unsafe=True)
    token = _coerce_cancellation(cancellation)
    if token is None and cancellation is not None:
        return _result("invalid_input", "invalid", reasons=("scheduler_cancellation_probe_required",), unsafe=True)

    mode, stale_mode, config_reasons = validate_scheduler_operational_controls_config(config)
    if config_reasons:
        return _result("invalid_config", "invalid", reasons=config_reasons)
    if token is not None and token.requested():
        return _cancelled("cancelled_before_start", mode)
    if mode == "disabled":
        return _result("disabled", mode, reasons=("scheduler_operational_controls_disabled",))

    exact_now = datetime.now(timezone.utc) if now is None else now
    stale_status: StaleRecoveryStatus = "stale_recovery_disabled"
    stale_result: RelayMEMSLPQueueStateTransitionResult | None = None
    stale_attempted = False
    stale_applied = False

    try:
        _fault(fault_injector, "before_stale_recovery")
    except Exception:
        return _result("unexpected_failure", mode, reasons=("scheduler_operational_fault_before_stale_recovery",), unsafe=True)
    if token is not None and token.requested():
        return _cancelled("cancelled_before_stale_recovery", mode)

    if stale_mode != "disabled":
        stale_status, stale_result = _recover_one_stale_claim(
            config=config,
            mode=stale_mode,
            now=exact_now,
            fault_injector=fault_injector,
        )
        stale_attempted = stale_status in {"stale_recovery_dry_run_ready", "stale_recovery_attempted", "stale_recovery_failed"}
        stale_applied = bool(stale_result and stale_result.transition_applied)
        if stale_status == "stale_recovery_failed":
            return _result(
                "unexpected_failure",
                mode,
                stale_status=stale_status,
                stale_enabled=True,
                stale_attempted=stale_attempted,
                stale_applied=stale_applied,
                stale_result=stale_result,
                reasons=("scheduler_stale_recovery_failed",),
                unsafe=True,
            )

    try:
        _fault(fault_injector, "after_stale_recovery_before_scheduler_round")
    except Exception:
        return _result("unexpected_failure", mode, reasons=("scheduler_operational_fault_before_scheduler_round",), unsafe=True)
    if token is not None and token.requested():
        return _result(
            "cancelled_before_scheduler_round",
            mode,
            stale_status=stale_status,
            stale_enabled=stale_mode != "disabled",
            stale_attempted=stale_attempted,
            stale_applied=stale_applied,
            stale_result=stale_result,
            cancelled=True,
            reasons=("scheduler_cancelled_before_round",),
        )

    try:
        policy_result = run_relaymem_slp_scheduler_round_once_with_policy(
            config=config,
            registry=registry,
            now=exact_now,
            policy_state=policy_state,
            fault_injector=fault_injector,
        )
    except Exception:
        return _result("unexpected_failure", mode, reasons=("scheduler_operational_round_failed",), unsafe=True)
    if type(policy_result) is not SchedulerPolicyRoundResult:
        return _result("unexpected_failure", mode, reasons=("scheduler_operational_round_result_invalid",), unsafe=True)

    if token is not None and token.requested():
        return _result(
            "cancelled_after_scheduler_round",
            mode,
            stale_status=stale_status,
            stale_enabled=stale_mode != "disabled",
            stale_attempted=stale_attempted,
            stale_applied=stale_applied,
            stale_result=stale_result,
            policy_result=policy_result,
            scheduler_invoked=True,
            cancelled=True,
            reasons=("scheduler_cancelled_after_round",),
            unsafe=policy_result.unsafe,
        )
    try:
        _fault(fault_injector, "before_operational_projection_return")
    except Exception:
        return _result("unexpected_failure", mode, reasons=("scheduler_operational_fault_before_return",), unsafe=True)

    return _result(
        "dry_run_ready" if mode == "dry_run" else "completed",
        mode,
        stale_status=stale_status,
        stale_enabled=stale_mode != "disabled",
        stale_attempted=stale_attempted,
        stale_applied=stale_applied,
        stale_result=stale_result,
        policy_result=policy_result,
        scheduler_invoked=True,
        reasons=("scheduler_operational_controls_completed",),
        unsafe=policy_result.unsafe,
    )


def validate_scheduler_operational_controls_config(config: RelayLMConfig) -> tuple[str, str, tuple[str, ...]]:
    if type(config) is not RelayLMConfig:
        return "invalid", "invalid", ("exact_relaylm_config_required",)
    op_fields = (
        "relaymem_local_scheduler_operational_controls_enabled",
        "relaymem_local_scheduler_operational_controls_dry_run_only",
        "relaymem_local_scheduler_operational_controls_apply_enabled",
    )
    stale_fields = (
        "relaymem_local_scheduler_stale_recovery_enabled",
        "relaymem_local_scheduler_stale_recovery_dry_run_only",
        "relaymem_local_scheduler_stale_recovery_apply_enabled",
    )
    for name in (*op_fields, *stale_fields):
        if type(getattr(config, name, None)) is not bool:
            return "invalid", "invalid", ("scheduler_operational_gate_must_be_bool",)
    mode = _mode_from_triple(tuple(getattr(config, name) for name in op_fields))
    stale_mode = _mode_from_triple(tuple(getattr(config, name) for name in stale_fields))
    if mode is None:
        return "invalid", "invalid", ("invalid_scheduler_operational_gate_combination",)
    if stale_mode is None:
        return "invalid", "invalid", ("invalid_scheduler_stale_recovery_gate_combination",)
    if mode == "disabled" and stale_mode != "disabled":
        return "invalid", "invalid", ("stale_recovery_requires_operational_controls",)
    if stale_mode == "apply" and mode != "apply":
        return "invalid", "invalid", ("stale_recovery_apply_requires_operational_apply",)
    limit = getattr(config, "relaymem_local_scheduler_stale_recovery_max_scan_entries", None)
    if type(limit) is not int or not 1 <= limit <= MAX_STALE_SCAN_ENTRIES:
        return "invalid", "invalid", ("scheduler_stale_recovery_scan_limit_invalid",)
    if mode == "dry_run" and any(
        getattr(config, name, False)
        for name in (
            "relaymem_local_scheduler_policy_apply_enabled",
            "relaymem_local_scheduler_apply_enabled",
            "relaymem_local_worker_apply_enabled",
            "relaymem_slp_durable_finalization_apply_enabled",
        )
    ):
        return "invalid", "invalid", ("operational_dry_run_lower_apply_enabled",)
    return mode, stale_mode, ()


def _recover_one_stale_claim(
    *,
    config: RelayLMConfig,
    mode: OperationalMode,
    now: datetime,
    fault_injector: FaultInjector | None,
) -> tuple[StaleRecoveryStatus, RelayMEMSLPQueueStateTransitionResult | None]:
    try:
        candidate, status, reasons = _discover_one_stale_claim(
            queue_root=config.relaymem_slp_queue_root,
            now=now,
            max_entries=config.relaymem_local_scheduler_stale_recovery_max_scan_entries,
            fault_injector=fault_injector,
        )
    except Exception:
        return "stale_recovery_failed", None
    if status == "unsafe":
        return "stale_recovery_failed", None
    if candidate is None:
        return "stale_recovery_no_candidate", None
    record = candidate.record
    try:
        _fault(fault_injector, "before_b3_stale_recovery_transition")
        request = RelayMEMSLPQueueTransitionRequest(
            transition_kind="stale_recovery",
            job_id=str(record["job_id"]),
            dispatch_idempotency_key=str(record["dispatch_idempotency_key"]),
            expected_record_revision=int(record["record_revision"]),
            expected_state="claimed",
            claim_generation=int(record["claim_generation"]),
            lease_token=str(record["lease_token"]),
        )
        result = transition_relaymem_slp_queue_state(
            request,
            queue_root=config.relaymem_slp_queue_root,
            enabled=True,
            dry_run_only=mode == "dry_run",
            apply_enabled=mode == "apply",
        )
    except Exception:
        return "stale_recovery_failed", None
    if result.status == "dry_run_ready":
        return "stale_recovery_dry_run_ready", result
    if result.status == "applied":
        return "stale_recovery_attempted", result
    return "stale_recovery_failed", result


def _discover_one_stale_claim(
    *,
    queue_root: str | None,
    now: datetime,
    max_entries: int,
    fault_injector: FaultInjector | None,
) -> tuple[_StaleCandidate | None, str, tuple[str, ...]]:
    if not _valid_now(now) or type(max_entries) is not int or not 1 <= max_entries <= MAX_STALE_SCAN_ENTRIES:
        return None, "unsafe", ("stale_recovery_discovery_input_invalid",)
    root_fd, root_reasons = open_queue_root(queue_root)
    if root_fd is None:
        return None, "unsafe", tuple(root_reasons)
    candidates: list[tuple[str, RecordSnapshot]] = []
    try:
        lock_error = acquire_queue_lock(root_fd, exclusive=False)
        if lock_error == "queue_lock_busy":
            return None, "no_candidate", ("queue_lock_busy",)
        if lock_error:
            return None, "unsafe", (lock_error,)
        try:
            scanned = 0
            try:
                iterator = os.scandir(root_fd)
            except OSError:
                return None, "unsafe", ("stale_recovery_scan_failed",)
            with iterator:
                for entry in iterator:
                    _fault(fault_injector, "during_stale_recovery_scan")
                    scanned += 1
                    if scanned > max_entries:
                        return None, "unsafe", ("stale_recovery_scan_limit_exceeded",)
                    filename = entry.name
                    if type(filename) is not str or _QUEUE_FILENAME_RE.fullmatch(filename) is None:
                        continue
                    snapshot, status, reasons = read_record_snapshot(root_fd, filename)
                    if snapshot is None or status != "ok":
                        return None, "unsafe", tuple(reasons or ("stale_recovery_record_invalid",))
                    record = snapshot.record
                    if record.get("state") != "claimed":
                        continue
                    expiry = parse_timestamp(record.get("lease_expires_at"))
                    if expiry is None:
                        return None, "unsafe", ("stale_recovery_lease_expiry_invalid",)
                    if expiry <= now:
                        candidates.append((filename, snapshot))
        finally:
            release_queue_lock(root_fd)
    finally:
        os.close(root_fd)
    if not candidates:
        return None, "no_candidate", ()
    candidates.sort(key=lambda item: item[0])
    return _StaleCandidate(candidates[0][1].record, candidates[0][1]), "selected", ()


def _mode_from_triple(triple: tuple[bool, bool, bool]) -> OperationalMode | None:
    if triple == (False, True, False):
        return "disabled"
    if triple == (True, True, False):
        return "dry_run"
    if triple == (True, False, True):
        return "apply"
    return None


def _coerce_cancellation(value: SchedulerCancellationToken | CancellationProbe | None) -> SchedulerCancellationToken | None:
    if value is None:
        return None
    if type(value) is SchedulerCancellationToken:
        return value
    if callable(value):
        return SchedulerCancellationToken(value)
    return None


def _cancelled(status: OperationalStatus, mode: str) -> SchedulerOperationalControlsResult:
    return _result(status, mode, cancelled=True, reasons=("scheduler_cancelled",))


def _result(
    status: OperationalStatus,
    mode: str,
    *,
    stale_status: StaleRecoveryStatus = "not_invoked",
    stale_enabled: bool = False,
    stale_attempted: bool = False,
    stale_applied: bool = False,
    stale_result: RelayMEMSLPQueueStateTransitionResult | None = None,
    policy_result: SchedulerPolicyRoundResult | None = None,
    scheduler_invoked: bool = False,
    cancelled: bool = False,
    shutdown_requested: bool = False,
    unsafe: bool = False,
    reasons: Sequence[str],
) -> SchedulerOperationalControlsResult:
    return SchedulerOperationalControlsResult(
        status=status,
        mode=mode,
        stale_recovery_status=stale_status,
        stale_recovery_enabled=stale_enabled,
        stale_recovery_attempted=stale_attempted,
        stale_recovery_applied=stale_applied,
        stale_recovery_result=stale_result,
        scheduler_policy_result=policy_result,
        scheduler_round_invoked=scheduler_invoked,
        cancelled=cancelled,
        shutdown_requested=shutdown_requested,
        unsafe=unsafe,
        bounded_reason_ids=_reason_ids(reasons, maximum=MAX_OPERATION_REASON_IDS),
    )


def _reason_ids(values: Sequence[str], *, maximum: int) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        values = ("scheduler_operational_reason_invalid",)
    output: list[str] = []
    for value in values:
        reason = value if type(value) is str and _REASON_RE.fullmatch(value) else "scheduler_operational_reason_invalid"
        if reason not in output:
            output.append(reason)
        if len(output) >= maximum:
            break
    if not output:
        output.append("scheduler_operational_status")
    return tuple(output)


def _valid_now(value: object) -> bool:
    return bool(type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None)


def _fault(fault_injector: FaultInjector | None, seam: str) -> None:
    if fault_injector is not None:
        fault_injector(seam)


__all__ = [
    "OPERATIONS_PROJECTION_SCHEMA",
    "OPERATIONS_RESULT_SCHEMA",
    "SchedulerCancellationToken",
    "SchedulerOperationalControlsResult",
    "SchedulerSignalCancellationAdapter",
    "run_relaymem_slp_scheduler_operational_controls_once",
    "validate_scheduler_operational_controls_config",
]
