"""Shared content-free fixtures for O1D1 smoke scripts."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from typing import Callable, Iterator

from relaylm.config import RelayLMConfig
from relaylm.relaymem_slp_scheduler_contract import LaneOutcome
from relaylm import relaymem_slp_scheduler_round as round_module

CANARY = "O1D1_PRIVATE_CONTENT_CANARY_61a4e7"
PATH_CANARY = "/private/o1d1/root/never-project"
RAW_EXCEPTION_CANARY = "O1D1_RAW_EXCEPTION_CANARY_82d5c1"
FORBIDDEN = (
    CANARY,
    PATH_CANARY,
    RAW_EXCEPTION_CANARY,
    "user_text",
    "assistant_text",
    "protected_source",
    "visible_response",
    "memory_title",
    "memory_summary",
    "memory_body",
    "namespace",
    "character_id",
    "run_id",
    "session_id",
    "turn_id",
    "job_id",
    "dispatch_id",
    "locator",
    "lineage",
    "queue_filename",
    "root",
    "path",
    "claim_owner",
    "lease_token",
    "generation",
    "revision",
    "retry_not_before",
    "completion_timestamp",
    "digest",
    "fingerprint",
    "raw_exception",
    "private_delegate_result",
)


def config_data(**updates: object) -> dict[str, object]:
    data: dict[str, object] = {
        "backends": {
            "local": {
                "type": "openai_compatible",
                "base_url": "http://127.0.0.1:1234/v1",
            }
        },
        "model_routes": {"relaylm-default": {"backend": "local"}},
    }
    data.update(updates)
    return data


def make_config(**updates: object) -> RelayLMConfig:
    return RelayLMConfig.model_validate(config_data(**updates))


def scheduler_config(
    *,
    mode: str = "dry_run",
    replay: bool = True,
    queue: bool = True,
    **updates: object,
) -> RelayLMConfig:
    triples = {
        "disabled": (False, True, False),
        "dry_run": (True, True, False),
        "apply": (True, False, True),
    }
    enabled, dry_run_only, apply_enabled = triples[mode]
    return make_config(
        relaymem_local_scheduler_enabled=enabled,
        relaymem_local_scheduler_dry_run_only=dry_run_only,
        relaymem_local_scheduler_apply_enabled=apply_enabled,
        relaymem_local_scheduler_replay_lane_enabled=replay,
        relaymem_local_scheduler_queue_lane_enabled=queue,
        **updates,
    )


def _lane(
    lane_kind: str,
    status: str,
    *,
    attempted: bool = True,
    candidate_observed: bool = False,
    candidate_selected: bool = False,
    reread: bool = False,
    delegated: bool = False,
    completed: bool = False,
    mutation: bool = False,
    no_work: bool = False,
    future: bool = False,
    contention: bool = False,
    retryable: bool = False,
    unsafe: bool = False,
    terminal: bool = False,
    reason: str,
    private: object = None,
) -> LaneOutcome:
    return LaneOutcome(
        lane_kind=lane_kind,
        status=status,
        enabled=True,
        attempted=attempted,
        candidate_observed=candidate_observed,
        candidate_selected=candidate_selected,
        canonical_reread_performed=reread,
        delegation_attempted=delegated,
        delegation_completed=completed,
        mutation_may_have_occurred=mutation,
        no_immediate_work=no_work,
        future_work_hint_present=future,
        contention_observed=contention,
        retryable=retryable,
        unsafe=unsafe,
        terminal_for_candidate=terminal,
        bounded_reason_ids=(reason,),
        private_delegate_result=private,
    )


def replay_no_work() -> LaneOutcome:
    return _lane("replay", "no_eligible_work", no_work=True, reason="replay_no_work")


def queue_no_work() -> LaneOutcome:
    return _lane("queue", "no_eligible_work", no_work=True, reason="queue_no_work")


def replay_completed(private: object = None) -> LaneOutcome:
    return _lane(
        "replay",
        "completed",
        candidate_observed=True,
        candidate_selected=True,
        reread=True,
        delegated=True,
        completed=True,
        mutation=True,
        terminal=True,
        reason="replay_completed",
        private=private,
    )


def queue_terminal(private: object = None) -> LaneOutcome:
    return _lane(
        "queue",
        "terminal",
        candidate_observed=True,
        candidate_selected=True,
        reread=True,
        delegated=True,
        completed=True,
        mutation=True,
        terminal=True,
        reason="queue_terminal",
        private=private,
    )


def replay_busy() -> LaneOutcome:
    return _lane(
        "replay",
        "busy",
        candidate_observed=True,
        no_work=True,
        contention=True,
        retryable=True,
        reason="replay_busy",
    )


def queue_busy() -> LaneOutcome:
    return _lane(
        "queue",
        "busy",
        no_work=True,
        contention=True,
        retryable=True,
        reason="queue_busy",
    )


def replay_candidate_changed() -> LaneOutcome:
    return _lane(
        "replay",
        "candidate_changed",
        candidate_observed=True,
        candidate_selected=True,
        reread=True,
        retryable=True,
        reason="replay_candidate_changed",
    )


def queue_future_retry() -> LaneOutcome:
    return _lane(
        "queue",
        "future_retry_only",
        candidate_observed=True,
        no_work=True,
        future=True,
        retryable=True,
        reason="future_retry_only",
        private={"retry_not_before": "2099-01-01T00:00:00Z"},
    )


def replay_isolated() -> LaneOutcome:
    return _lane(
        "replay",
        "isolated",
        candidate_observed=True,
        candidate_selected=True,
        reread=True,
        no_work=True,
        unsafe=True,
        reason="replay_candidate_isolated",
    )


def queue_unsafe() -> LaneOutcome:
    return _lane(
        "queue",
        "unsafe_state",
        candidate_observed=True,
        no_work=True,
        unsafe=True,
        reason="queue_state_unsafe",
    )


@contextmanager
def patched_lanes(
    replay: Callable[..., LaneOutcome],
    queue: Callable[..., LaneOutcome],
) -> Iterator[None]:
    previous_replay = round_module.run_relaymem_slp_scheduler_replay_lane_once
    previous_queue = round_module.run_relaymem_slp_scheduler_queue_lane_once
    round_module.run_relaymem_slp_scheduler_replay_lane_once = replay
    round_module.run_relaymem_slp_scheduler_queue_lane_once = queue
    try:
        yield
    finally:
        round_module.run_relaymem_slp_scheduler_replay_lane_once = previous_replay
        round_module.run_relaymem_slp_scheduler_queue_lane_once = previous_queue


def assert_safe_projection(result: object) -> str:
    projection = result.projection()
    encoded = json.dumps(projection, ensure_ascii=True, sort_keys=True)
    lowered = encoded.lower()
    assert all(token.lower() not in lowered for token in FORBIDDEN), encoded
    assert all(token.lower() not in repr(result).lower() for token in FORBIDDEN), repr(result)
    return encoded


def write_marker(path: Path) -> None:
    path.write_text("content-free-marker\n", encoding="utf-8")
