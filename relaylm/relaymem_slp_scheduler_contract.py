"""Pure O1A two-lane scheduler-round contract.

This module contains no filesystem, clock, sleep, queue, replay, worker, or
configuration integration.  It validates already-bounded lane outcomes and
produces a deterministic content-free scheduler result/projection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Final, Literal, Mapping, Sequence

ROUND_RESULT_SCHEMA: Final = "relaylm.local_scheduler_round_result.v0"
ROUND_PROJECTION_SCHEMA: Final = "relaylm.local_scheduler_round_projection.v0"
LANE_RESULT_SCHEMA: Final = "relaylm.local_scheduler_lane_result.v0"
MAX_REASON_IDS_PER_LANE: Final = 8
MAX_ROUND_REASON_IDS: Final = 16
_REASON_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

LaneKind = Literal["replay", "queue"]
Disposition = Literal["stop", "run_next_round", "idle"]
SchedulerStatus = Literal[
    "disabled",
    "invalid_input",
    "invalid_configuration",
    "round_completed",
    "partial_progress",
    "idle",
    "blocked",
    "unsafe_state",
    "unexpected_failure",
]
ReplayLaneStatus = Literal[
    "dependency_unavailable",
    "no_eligible_work",
    "busy",
    "candidate_changed",
    "delegated",
    "completed",
    "already_complete",
    "not_replayable",
    "isolated",
    "unsafe_state",
    "failed",
]
QueueLaneStatus = Literal[
    "no_eligible_work",
    "future_retry_only",
    "busy",
    "candidate_changed",
    "dry_run_ready",
    "delegated",
    "executed",
    "retry_released",
    "terminal",
    "cleanup_required",
    "unsafe_state",
    "failed",
]
LaneStatus = ReplayLaneStatus | QueueLaneStatus

REPLAY_LANE_STATUSES: Final = frozenset(
    {
        "dependency_unavailable",
        "no_eligible_work",
        "busy",
        "candidate_changed",
        "delegated",
        "completed",
        "already_complete",
        "not_replayable",
        "isolated",
        "unsafe_state",
        "failed",
    }
)
QUEUE_LANE_STATUSES: Final = frozenset(
    {
        "no_eligible_work",
        "future_retry_only",
        "busy",
        "candidate_changed",
        "dry_run_ready",
        "delegated",
        "executed",
        "retry_released",
        "terminal",
        "cleanup_required",
        "unsafe_state",
        "failed",
    }
)

_PROGRESS_STATUSES: Final = frozenset(
    {"completed", "already_complete", "dry_run_ready", "executed", "retry_released", "terminal"}
)
_FAILURE_STATUSES: Final = frozenset({"dependency_unavailable", "failed", "unsafe_state", "isolated"})
_IMMEDIATE_RETRY_STATUSES: Final = frozenset({"candidate_changed"})
_IDLE_STATUSES: Final = frozenset(
    {
        "no_eligible_work",
        "future_retry_only",
        "busy",
        "not_replayable",
        "cleanup_required",
        "failed",
        "dependency_unavailable",
        "unsafe_state",
        "isolated",
        "delegated",
    }
)


def _require_exact_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name}_must_be_bool")
    return value


def _validate_reason_ids(values: Sequence[str], *, maximum: int, name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name}_must_be_sequence")
    result = tuple(values)
    if len(result) > maximum:
        raise ValueError(f"{name}_too_many")
    if len(set(result)) != len(result):
        raise ValueError(f"{name}_duplicate")
    for value in result:
        if type(value) is not str or _REASON_RE.fullmatch(value) is None:
            raise ValueError(f"{name}_invalid")
    return result


@dataclass(frozen=True)
class SchedulerGates:
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    replay_lane_enabled: bool
    queue_lane_enabled: bool
    required_dependency_available: bool = True
    supported_schema: bool = True

    def __post_init__(self) -> None:
        for name in (
            "enabled",
            "dry_run_only",
            "apply_enabled",
            "replay_lane_enabled",
            "queue_lane_enabled",
            "required_dependency_available",
            "supported_schema",
        ):
            _require_exact_bool(name, getattr(self, name))

    @property
    def mode(self) -> Literal["disabled", "dry_run", "apply", "invalid"]:
        triple = (self.enabled, self.dry_run_only, self.apply_enabled)
        if triple == (False, True, False):
            return "disabled"
        if triple == (True, True, False):
            return "dry_run"
        if triple == (True, False, True):
            return "apply"
        return "invalid"

    def validation_reason_ids(self) -> tuple[str, ...]:
        if not self.supported_schema:
            return ("unsupported_scheduler_schema",)
        if self.mode == "invalid":
            return ("invalid_scheduler_gate_combination",)
        if self.enabled and not (self.replay_lane_enabled or self.queue_lane_enabled):
            return ("no_scheduler_lane_enabled",)
        if self.enabled and not self.required_dependency_available:
            return ("required_dependency_unavailable",)
        return ()


@dataclass(frozen=True)
class LaneOutcome:
    lane_kind: LaneKind
    status: LaneStatus
    enabled: bool
    attempted: bool
    candidate_observed: bool
    candidate_selected: bool
    canonical_reread_performed: bool
    delegation_attempted: bool
    delegation_completed: bool
    mutation_may_have_occurred: bool
    no_immediate_work: bool
    future_work_hint_present: bool
    contention_observed: bool
    retryable: bool
    unsafe: bool
    terminal_for_candidate: bool
    bounded_reason_ids: tuple[str, ...] = ()
    private_delegate_result: object = field(default=None, repr=False, compare=False)
    schema_version: str = field(default=LANE_RESULT_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if self.lane_kind not in {"replay", "queue"}:
            raise ValueError("unknown_lane_kind")
        allowed = REPLAY_LANE_STATUSES if self.lane_kind == "replay" else QUEUE_LANE_STATUSES
        if type(self.status) is not str or self.status not in allowed:
            raise ValueError("unknown_lane_status")
        for name in (
            "enabled",
            "attempted",
            "candidate_observed",
            "candidate_selected",
            "canonical_reread_performed",
            "delegation_attempted",
            "delegation_completed",
            "mutation_may_have_occurred",
            "no_immediate_work",
            "future_work_hint_present",
            "contention_observed",
            "retryable",
            "unsafe",
            "terminal_for_candidate",
        ):
            _require_exact_bool(name, getattr(self, name))
        object.__setattr__(
            self,
            "bounded_reason_ids",
            _validate_reason_ids(
                self.bounded_reason_ids,
                maximum=MAX_REASON_IDS_PER_LANE,
                name="lane_reason_ids",
            ),
        )
        if not self.enabled and self.attempted:
            raise ValueError("disabled_lane_cannot_be_attempted")
        if self.delegation_completed and not self.delegation_attempted:
            raise ValueError("delegation_completion_requires_attempt")
        if self.delegation_attempted and not self.attempted:
            raise ValueError("delegation_requires_lane_attempt")
        if self.candidate_selected and not self.candidate_observed:
            raise ValueError("selected_candidate_requires_observation")
        if self.canonical_reread_performed and not self.candidate_selected:
            raise ValueError("canonical_reread_requires_selection")
        if self.delegation_attempted and not self.canonical_reread_performed:
            raise ValueError("delegation_requires_canonical_reread")
        if self.status in {"no_eligible_work", "future_retry_only"} and self.delegation_attempted:
            raise ValueError("nondelegating_status_attempted_delegation")
        if self.status == "busy" and self.delegation_attempted and self.lane_kind != "replay":
            raise ValueError("queue_busy_cannot_follow_delegation")
        if self.status in _PROGRESS_STATUSES and not self.delegation_completed:
            raise ValueError("progress_status_requires_completed_delegation")
        if self.status == "candidate_changed" and not self.candidate_selected:
            raise ValueError("candidate_changed_requires_selection")
        if self.status == "future_retry_only" and not self.future_work_hint_present:
            raise ValueError("future_retry_requires_private_hint")
        if self.status == "busy" and not self.contention_observed:
            raise ValueError("busy_requires_contention")
        if self.status in {"unsafe_state", "isolated"} and not self.unsafe:
            raise ValueError("unsafe_status_requires_unsafe_flag")
        if self.no_immediate_work and self.status in _PROGRESS_STATUSES:
            raise ValueError("progress_cannot_report_no_immediate_work")


@dataclass(frozen=True)
class SchedulerRoundResult:
    status: SchedulerStatus
    disposition: Disposition
    replay_lane: LaneOutcome | None = field(repr=False)
    queue_lane: LaneOutcome | None = field(repr=False)
    work_units_attempted: int
    work_units_completed: int
    idle_recommended: bool
    immediate_next_round_recommended: bool
    future_work_hint_present: bool
    retryable: bool
    unsafe: bool
    bounded_reason_ids: tuple[str, ...]
    schema_version: str = field(default=ROUND_RESULT_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if self.status not in {
            "disabled",
            "invalid_input",
            "invalid_configuration",
            "round_completed",
            "partial_progress",
            "idle",
            "blocked",
            "unsafe_state",
            "unexpected_failure",
        }:
            raise ValueError("unknown_scheduler_status")
        if self.disposition not in {"stop", "run_next_round", "idle"}:
            raise ValueError("unknown_scheduler_disposition")
        if type(self.work_units_attempted) is not int or not 0 <= self.work_units_attempted <= 2:
            raise ValueError("invalid_work_units_attempted")
        if type(self.work_units_completed) is not int or not 0 <= self.work_units_completed <= self.work_units_attempted:
            raise ValueError("invalid_work_units_completed")
        for name in (
            "idle_recommended",
            "immediate_next_round_recommended",
            "future_work_hint_present",
            "retryable",
            "unsafe",
        ):
            _require_exact_bool(name, getattr(self, name))
        if self.idle_recommended != (self.disposition == "idle"):
            raise ValueError("idle_projection_mismatch")
        if self.immediate_next_round_recommended != (self.disposition == "run_next_round"):
            raise ValueError("next_round_projection_mismatch")
        object.__setattr__(
            self,
            "bounded_reason_ids",
            _validate_reason_ids(
                self.bounded_reason_ids,
                maximum=MAX_ROUND_REASON_IDS,
                name="round_reason_ids",
            ),
        )

    def projection(self) -> Mapping[str, object]:
        replay = self.replay_lane
        queue = self.queue_lane
        return {
            "schema_version": ROUND_PROJECTION_SCHEMA,
            "status": self.status,
            "disposition": self.disposition,
            "replay_lane_enabled": bool(replay and replay.enabled),
            "replay_lane_attempted": bool(replay and replay.attempted),
            "replay_lane_status": replay.status if replay else "not_invoked",
            "replay_candidate_selected": bool(replay and replay.candidate_selected),
            "replay_delegated": bool(replay and replay.delegation_attempted),
            "replay_completed": bool(replay and replay.delegation_completed),
            "queue_lane_enabled": bool(queue and queue.enabled),
            "queue_lane_attempted": bool(queue and queue.attempted),
            "queue_lane_status": queue.status if queue else "not_invoked",
            "queue_candidate_selected": bool(queue and queue.candidate_selected),
            "queue_delegated": bool(queue and queue.delegation_attempted),
            "queue_completed": bool(queue and queue.delegation_completed),
            "work_units_attempted": self.work_units_attempted,
            "work_units_completed": self.work_units_completed,
            "idle_recommended": self.idle_recommended,
            "immediate_next_round_recommended": self.immediate_next_round_recommended,
            "future_work_hint_present": self.future_work_hint_present,
            "retryable": self.retryable,
            "unsafe": self.unsafe,
            "bounded_reason_ids": list(self.bounded_reason_ids),
        }


def aggregate_scheduler_round(
    *,
    gates: SchedulerGates,
    invocation_order: Sequence[LaneKind],
    replay_lane: LaneOutcome | None,
    queue_lane: LaneOutcome | None,
) -> SchedulerRoundResult:
    """Validate one already-bounded round and derive a content-free result.

    The function never invokes a lane.  ``invocation_order`` is explicit so the
    contract smoke can prove that a caller did not invert or duplicate the v0
    replay-then-queue order.
    """

    reasons = gates.validation_reason_ids()
    if reasons:
        if replay_lane is not None or queue_lane is not None or tuple(invocation_order):
            raise ValueError("scheduler_level_failure_must_precede_lane_invocation")
        status: SchedulerStatus = (
            "invalid_configuration"
            if reasons[0] in {"invalid_scheduler_gate_combination", "no_scheduler_lane_enabled"}
            else "blocked"
        )
        return SchedulerRoundResult(
            status=status,
            disposition="stop",
            replay_lane=None,
            queue_lane=None,
            work_units_attempted=0,
            work_units_completed=0,
            idle_recommended=False,
            immediate_next_round_recommended=False,
            future_work_hint_present=False,
            retryable=False,
            unsafe=status != "invalid_configuration",
            bounded_reason_ids=reasons,
        )

    if gates.mode == "disabled":
        if replay_lane is not None or queue_lane is not None or tuple(invocation_order):
            raise ValueError("disabled_scheduler_must_not_invoke_lanes")
        return SchedulerRoundResult(
            status="disabled",
            disposition="stop",
            replay_lane=None,
            queue_lane=None,
            work_units_attempted=0,
            work_units_completed=0,
            idle_recommended=False,
            immediate_next_round_recommended=False,
            future_work_hint_present=False,
            retryable=False,
            unsafe=False,
            bounded_reason_ids=("scheduler_disabled",),
        )

    expected_order: tuple[LaneKind, ...] = tuple(
        lane
        for lane, enabled in (
            ("replay", gates.replay_lane_enabled),
            ("queue", gates.queue_lane_enabled),
        )
        if enabled
    )
    if tuple(invocation_order) != expected_order:
        raise ValueError("invalid_lane_invocation_order")

    if gates.replay_lane_enabled != (replay_lane is not None):
        raise ValueError("replay_lane_presence_mismatch")
    if gates.queue_lane_enabled != (queue_lane is not None):
        raise ValueError("queue_lane_presence_mismatch")
    if replay_lane is not None and (replay_lane.lane_kind != "replay" or not replay_lane.enabled):
        raise ValueError("invalid_replay_lane_result")
    if queue_lane is not None and (queue_lane.lane_kind != "queue" or not queue_lane.enabled):
        raise ValueError("invalid_queue_lane_result")

    lanes = tuple(lane for lane in (replay_lane, queue_lane) if lane is not None)
    attempted = sum(1 for lane in lanes if lane.delegation_attempted)
    completed = sum(1 for lane in lanes if lane.delegation_completed)
    if attempted > 2 or completed > 2:
        raise AssertionError("round_work_unit_bound_exceeded")

    progress = any(
        lane.status in _PROGRESS_STATUSES
        or lane.mutation_may_have_occurred
        or lane.status in _IMMEDIATE_RETRY_STATUSES
        for lane in lanes
    )
    failures = tuple(lane for lane in lanes if lane.status in _FAILURE_STATUSES)
    unsafe = any(lane.unsafe for lane in lanes)
    future_hint = any(lane.future_work_hint_present for lane in lanes)
    retryable = any(lane.retryable for lane in lanes)

    if progress:
        disposition: Disposition = "run_next_round"
    else:
        if not all(lane.no_immediate_work or lane.status in _IDLE_STATUSES for lane in lanes):
            raise ValueError("lane_outcome_has_no_disposition")
        disposition = "idle"

    if unsafe:
        status = "unsafe_state"
    elif completed and failures:
        status = "partial_progress"
    elif completed and progress:
        status = "round_completed"
    elif failures and not retryable:
        status = "blocked"
    else:
        status = "idle"

    combined_reasons: list[str] = []
    for lane in lanes:
        for reason in lane.bounded_reason_ids:
            if reason not in combined_reasons:
                combined_reasons.append(reason)
    combined = _validate_reason_ids(
        combined_reasons,
        maximum=MAX_ROUND_REASON_IDS,
        name="round_reason_ids",
    )

    return SchedulerRoundResult(
        status=status,
        disposition=disposition,
        replay_lane=replay_lane,
        queue_lane=queue_lane,
        work_units_attempted=attempted,
        work_units_completed=completed,
        idle_recommended=disposition == "idle",
        immediate_next_round_recommended=disposition == "run_next_round",
        future_work_hint_present=future_hint,
        retryable=retryable,
        unsafe=unsafe,
        bounded_reason_ids=combined,
    )
