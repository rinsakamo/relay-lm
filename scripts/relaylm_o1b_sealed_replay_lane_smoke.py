#!/usr/bin/env python3
"""O1B bounded sealed-record discovery, reread, delegation, and race smoke."""
from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import relaylm_i1gc_durable_finalization_replay_smoke as gc  # noqa: E402
from relaylm.relaymem_slp_durable_finalization_replay import (  # noqa: E402
    completion_filename,
)
from relaylm.relaymem_slp_scheduler_contract import (  # noqa: E402
    LaneOutcome,
    SchedulerGates,
    aggregate_scheduler_round,
)
import relaylm.relaymem_slp_scheduler_replay_lane as lane_module  # noqa: E402
from relaylm.relaymem_slp_scheduler_replay_lane import (  # noqa: E402
    build_relaymem_slp_scheduler_replay_lane_node_result,
    run_relaymem_slp_scheduler_replay_lane_once,
)

LEAK_CANARY = "O1B_PRIVATE_EXCEPTION_CANARY_DO_NOT_LEAK"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def gates(*, mode: str = "apply", replay: bool = True, queue: bool = True) -> SchedulerGates:
    triple = {
        "disabled": (False, True, False),
        "dry_run": (True, True, False),
        "apply": (True, False, True),
    }[mode]
    return SchedulerGates(
        enabled=triple[0],
        dry_run_only=triple[1],
        apply_enabled=triple[2],
        replay_lane_enabled=replay,
        queue_lane_enabled=queue,
    )


def run(config, *, scheduler=None, limit=None, registry=None, fault=None):
    return run_relaymem_slp_scheduler_replay_lane_once(
        config=config,
        gates=scheduler or gates(),
        registry=registry,
        discovery_max_entries=limit,
        fault_injector=fault,
    )


def fake_delegate(status: str, *, mutation: bool = False):
    return SimpleNamespace(
        status=status,
        projection=SimpleNamespace(
            source_created=mutation,
            queue_created=False,
            completion_created=False,
        ),
        private_text=gc.gb.USER_CANARY,
    )


def rendered(value: object) -> str:
    payload = value.to_log_dict() if hasattr(value, "to_log_dict") else value
    return repr(value) + "\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def assert_content_free(value: object, locator: str | None = None) -> None:
    text = rendered(value)
    forbidden = [
        gc.gb.USER_CANARY,
        gc.gb.ASSISTANT_CANARY,
        gc.gb.NAMESPACE_CANARY,
        gc.gb.RUN_ID,
        gc.gb.SESSION_ID,
        gc.gb.REQUEST_ID,
        LEAK_CANARY,
        "slp-job-v0:",
        "slp-dispatch-v0:",
        "finalization",
    ]
    if locator:
        forbidden.append(locator)
    for token in forbidden:
        require(token not in text, (token, text))


def test_gates_and_safe_no_work() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root)
        finalization = root / "finalization"

        disabled = run(config, scheduler=gates(mode="disabled"))
        require(not disabled.enabled and not disabled.attempted, disabled)
        require(not any(finalization.iterdir()), disabled)

        lane_disabled = run(config, scheduler=gates(replay=False))
        require(not lane_disabled.enabled and not lane_disabled.attempted, lane_disabled)

        invalid = SchedulerGates(
            enabled=True,
            dry_run_only=True,
            apply_enabled=True,
            replay_lane_enabled=True,
            queue_lane_enabled=True,
        )
        invalid_result = run(config, scheduler=invalid)
        require(invalid_result.status == "dependency_unavailable", invalid_result)
        require(not invalid_result.attempted, invalid_result)

        missing_dependency = SchedulerGates(
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
            replay_lane_enabled=True,
            queue_lane_enabled=True,
            required_dependency_available=False,
        )
        dependency = run(config, scheduler=missing_dependency)
        require(dependency.status == "dependency_unavailable", dependency)
        require(not dependency.attempted, dependency)

        empty = run(config)
        require(empty.status == "no_eligible_work", empty)
        require(empty.attempted and not empty.candidate_observed, empty)

        base, _, _ = gc.gb._records()
        result = gc.gb._store(finalization).publish_base(base)
        require(result.status == "published_new", result)
        incomplete = run(config)
        require(incomplete.status == "no_eligible_work", incomplete)
        require(incomplete.candidate_observed and not incomplete.candidate_selected, incomplete)


def test_selection_delegation_and_completion() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        outcome = run(config)
        require(outcome.status == "completed", outcome)
        require(outcome.delegation_attempted and outcome.delegation_completed, outcome)
        require(outcome.terminal_for_candidate and outcome.mutation_may_have_occurred, outcome)
        require(
            (root / "finalization" / completion_filename(locator)).is_file(),
            outcome,
        )
        node = build_relaymem_slp_scheduler_replay_lane_node_result(outcome)
        assert_content_free(outcome, locator)
        assert_content_free(node, locator)

        complete_only = run(config)
        require(complete_only.status == "no_eligible_work", complete_only)
        require(not complete_only.delegation_attempted, complete_only)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        base, _, _, _ = gc._publish_sealed(root)
        before = gc._snapshot(root)
        dry = run(config, scheduler=gates(mode="dry_run"))
        require(dry.status == "delegated", dry)
        require(dry.delegation_attempted and dry.delegation_completed, dry)
        require(not dry.mutation_may_have_occurred and dry.no_immediate_work, dry)
        require(gc._snapshot(root) == before, (before, gc._snapshot(root)))

        queue_no_work = LaneOutcome(
            lane_kind="queue",
            status="no_eligible_work",
            enabled=True,
            attempted=True,
            candidate_observed=False,
            candidate_selected=False,
            canonical_reread_performed=False,
            delegation_attempted=False,
            delegation_completed=False,
            mutation_may_have_occurred=False,
            no_immediate_work=True,
            future_work_hint_present=False,
            contention_observed=False,
            retryable=False,
            unsafe=False,
            terminal_for_candidate=False,
        )
        round_result = aggregate_scheduler_round(
            gates=gates(mode="dry_run"),
            invocation_order=("replay", "queue"),
            replay_lane=dry,
            queue_lane=queue_no_work,
        )
        require(round_result.disposition == "idle", round_result)
        require(round_result.work_units_completed == 1, round_result)

        # A scheduler dry-run never elevates an apply-configured I1-GC.
        apply_config = gc._config(Path(directory) / "apply")
        gc._publish_sealed(Path(directory) / "apply")
        blocked = run(apply_config, scheduler=gates(mode="dry_run"))
        require(blocked.status == "dependency_unavailable", blocked)
        require(not blocked.delegation_attempted, blocked)

        disabled_config = config.model_copy(update={
            "relaymem_slp_durable_finalization_enabled": False,
            "relaymem_slp_durable_finalization_dry_run_only": True,
            "relaymem_slp_durable_finalization_apply_enabled": False,
        })
        disabled_delegate = run(disabled_config, scheduler=gates(mode="apply"))
        require(disabled_delegate.status == "dependency_unavailable", disabled_delegate)
        require(disabled_delegate.delegation_completed, disabled_delegate)


def test_deterministic_selection_and_single_delegate() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        first, _, _, _ = gc._publish_sealed(root, request_id="o1b-request-a")
        with patch.object(gc.gb, "RUN_ID", f"{gc.gb.RUN_ID}-o1b-b"):
            second, _, _, _ = gc._publish_sealed(root, request_id="o1b-request-b")
        expected = min(str(first["locator_digest"]), str(second["locator_digest"]))
        calls: list[str] = []

        def delegate(config_value, *, locator_digest, registry, fault_injector=None):
            calls.append(locator_digest)
            return fake_delegate("dry_run_ready")

        with patch.object(
            lane_module,
            "replay_relaymem_slp_durable_finalization_record",
            side_effect=delegate,
        ):
            outcome = run(config, scheduler=gates(mode="dry_run"))
        require(outcome.status == "delegated", outcome)
        require(calls == [expected], calls)

        calls.clear()
        with patch.object(
            lane_module,
            "replay_relaymem_slp_durable_finalization_record",
            side_effect=RuntimeError(LEAK_CANARY),
        ):
            failed = run(config, scheduler=gates(mode="dry_run"))
        require(failed.status == "failed", failed)
        require(failed.delegation_attempted and not failed.delegation_completed, failed)
        assert_content_free(failed, expected)


def test_inventory_bounds_and_reread_changes() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        gc._publish_sealed(root)
        overflow = run(config, scheduler=gates(mode="dry_run"), limit=1)
        require(overflow.status == "unsafe_state", overflow)
        require(not overflow.candidate_selected and not overflow.delegation_attempted, overflow)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        gc._publish_sealed(root)
        (root / "finalization" / "unexpected-object").write_text("x", encoding="utf-8")
        unsafe = run(config, scheduler=gates(mode="dry_run"))
        require(unsafe.status == "unsafe_state", unsafe)
        require(not unsafe.delegation_attempted, unsafe)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        changed_once = False

        def complete_during_reread(stage: str) -> None:
            nonlocal changed_once
            if stage == "after_selection_before_reread" and not changed_once:
                changed_once = True
                direct = gc._replay(config, locator)
                require(direct.status == "completed", direct)

        changed = run(config, fault=complete_during_reread)
        require(changed.status == "candidate_changed", changed)
        require(not changed.delegation_attempted, changed)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        gc._publish_sealed(root)
        stages: list[str] = []

        def inject(stage: str) -> None:
            stages.append(stage)
            if stage == "after_reread_before_delegation":
                raise RuntimeError(LEAK_CANARY)

        failed = run(config, scheduler=gates(mode="dry_run"), fault=inject)
        require(failed.status == "failed", failed)
        require(not failed.delegation_attempted, failed)
        require("after_reread_before_delegation" in stages, stages)
        assert_content_free(failed)


def test_cross_process_busy_mapping() -> None:
    if not hasattr(multiprocessing, "get_context"):
        return
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        context = multiprocessing.get_context("fork")
        started = context.Event()
        release = context.Event()
        output = context.Queue()
        process = context.Process(
            target=gc._process_replay,
            args=(str(root), locator, started, release, output),
        )
        process.start()
        require(started.wait(20), "direct_i1gc_did_not_acquire_fence")
        try:
            busy = run(config)
            require(busy.status == "busy", busy)
            require(busy.contention_observed and busy.retryable, busy)
            require(busy.delegation_attempted and busy.delegation_completed, busy)
        finally:
            release.set()
            process.join(20)
        require(process.exitcode == 0, process.exitcode)
        require(output.get(timeout=5) == "completed", "direct_i1gc_failed")


def test_non_goals_and_fault_seams() -> None:
    source = (ROOT / "relaylm" / "relaymem_slp_scheduler_replay_lane.py").read_text("utf-8")
    for forbidden in (
        "time.sleep(",
        "while True",
        "execute_one_queued_relaymem_slp_primary_job",
        "transition_relaymem_slp_queue_state",
        "enqueue_relaymem_slp_durable_job(",
        "relaymem_slp_queue_root",
    ):
        require(forbidden not in source, forbidden)
    for stage in (
        "after_root_open_before_inventory",
        "during_inventory",
        "after_inventory_before_classification",
        "after_classification_before_selection",
        "after_selection_before_reread",
        "during_selected_reread",
        "after_reread_before_delegation",
        "after_delegation_before_lane_mapping",
    ):
        require(stage in source, stage)


def main() -> None:
    test_gates_and_safe_no_work()
    test_selection_delegation_and_completion()
    test_deterministic_selection_and_single_delegate()
    test_inventory_bounds_and_reread_changes()
    test_cross_process_busy_mapping()
    test_non_goals_and_fault_seams()
    print("RelayLM O1B sealed replay-lane smoke passed.")


if __name__ == "__main__":
    main()
