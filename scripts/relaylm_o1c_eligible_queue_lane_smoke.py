"""Functional smoke for O1C eligible B2/B3 queue-lane discovery."""
from __future__ import annotations

from datetime import datetime, timezone
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import relaylm.relaymem_slp_scheduler_queue_lane as queue_lane
from relaylm.relaymem_slp_queue_record import (
    canonical_json_bytes,
    format_timestamp,
    record_filename,
)
from relaylm.relaymem_slp_scheduler_contract import SchedulerGates
from relaylm.relaymem_slp_scheduler_queue_lane import (
    run_relaymem_slp_scheduler_queue_lane_once,
)

from _relaylm_o0_local_worker_support import (
    build_config,
    prepare_scoped_store,
    produce,
)
from relaylm_phase6c1_primary_worker_test_support import read_record, require


def scheduler_gates(
    mode: str = "apply",
    *,
    queue_enabled: bool = True,
    replay_enabled: bool = True,
    dependency: bool = True,
) -> SchedulerGates:
    triple = {
        "disabled": (False, True, False),
        "dry_run": (True, True, False),
        "apply": (True, False, True),
        "invalid": (True, True, True),
    }[mode]
    return SchedulerGates(
        enabled=triple[0],
        dry_run_only=triple[1],
        apply_enabled=triple[2],
        replay_lane_enabled=replay_enabled,
        queue_lane_enabled=queue_enabled,
        required_dependency_available=dependency,
        supported_schema=True,
    )


def fake_c2(
    status: str,
    *,
    claim_performed: bool = False,
    worker_invoked: bool = False,
    worker_status: str | None = None,
    queue_transition_performed: bool = False,
    retryable: bool = False,
    terminal: bool = False,
    cleanup_required: bool = False,
):
    return SimpleNamespace(
        status=status,
        claim_attempted=True,
        claim_performed=claim_performed,
        source_prepared=worker_invoked,
        restart_rehydrated=worker_invoked,
        worker_invoked=worker_invoked,
        worker_status=worker_status,
        queue_transition_performed=queue_transition_performed,
        retryable=retryable,
        terminal=terminal,
        cleanup_required=cleanup_required,
        reason_ids=(),
    )


def gates_and_empty_inventory() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        config = build_config(
            Path(queue_dir),
            Path(protected_dir),
            Path(memory_dir),
            "character/default",
        )
        with patch.object(queue_lane, "discover_relaymem_slp_queue_candidate") as discover:
            disabled = run_relaymem_slp_scheduler_queue_lane_once(
                config=config,
                gates=scheduler_gates("disabled"),
            )
            require(not disabled.enabled and not disabled.attempted, disabled)
            require(not discover.called, "disabled scheduler scanned queue")

            lane_disabled = run_relaymem_slp_scheduler_queue_lane_once(
                config=config,
                gates=scheduler_gates("apply", queue_enabled=False),
            )
            require(not lane_disabled.enabled and not lane_disabled.attempted, lane_disabled)
            require(not discover.called, "disabled queue lane scanned queue")

        invalid = run_relaymem_slp_scheduler_queue_lane_once(
            config=config,
            gates=scheduler_gates("invalid"),
        )
        require(invalid.status == "failed" and not invalid.attempted, invalid)

        wrong_type = run_relaymem_slp_scheduler_queue_lane_once(
            config=config,
            gates=object(),  # type: ignore[arg-type]
        )
        require(wrong_type.status == "failed" and not wrong_type.attempted, wrong_type)

        lower_disabled = config.model_copy(
            update={
                "relaymem_local_worker_enabled": False,
                "relaymem_local_worker_dry_run_only": True,
                "relaymem_local_worker_apply_enabled": False,
            }
        )
        with patch.object(queue_lane, "discover_relaymem_slp_queue_candidate") as discover:
            result = run_relaymem_slp_scheduler_queue_lane_once(
                config=lower_disabled,
                gates=scheduler_gates("apply"),
            )
            require(result.status == "failed" and not result.attempted, result)
            require(not discover.called, "lower disabled gate scanned queue")

        empty = run_relaymem_slp_scheduler_queue_lane_once(
            config=config,
            gates=scheduler_gates("apply"),
        )
        require(empty.status == "no_eligible_work", empty)
        require(empty.attempted and empty.no_immediate_work, empty)


def future_retry_and_gate_intersection() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, _ = produce(queue_root, protected_root)
        path = queue_root / record_filename(str(queued["dispatch_idempotency_key"]))
        future_value = format_timestamp(datetime(2999, 1, 1, tzinfo=timezone.utc))
        future = dict(read_record(path))
        future["retry_not_before"] = future_value
        path.write_bytes(canonical_json_bytes(future))
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        result = run_relaymem_slp_scheduler_queue_lane_once(
            config=config,
            gates=scheduler_gates("apply"),
        )
        require(result.status == "future_retry_only", result)
        require(result.future_work_hint_present and not result.delegation_attempted, result)
        require(future_value not in repr(result), "future timestamp leaked from LaneOutcome")

        due = dict(future)
        due["retry_not_before"] = None
        path.write_bytes(canonical_json_bytes(due))
        captured: list[object] = []

        def capture(request: object):
            captured.append(request)
            return fake_c2("dry_run_ready")

        with patch.object(
            queue_lane,
            "execute_one_queued_relaymem_slp_primary_job",
            capture,
        ):
            scheduler_dry = run_relaymem_slp_scheduler_queue_lane_once(
                config=config,
                gates=scheduler_gates("dry_run"),
            )
            require(scheduler_dry.status == "dry_run_ready", scheduler_dry)
            require(getattr(captured[-1], "dry_run_only") is True, "scheduler dry-run elevated")

            lower_dry = config.model_copy(
                update={
                    "relaymem_local_worker_enabled": True,
                    "relaymem_local_worker_dry_run_only": True,
                    "relaymem_local_worker_apply_enabled": False,
                }
            )
            lower_result = run_relaymem_slp_scheduler_queue_lane_once(
                config=lower_dry,
                gates=scheduler_gates("apply"),
            )
            require(lower_result.status == "dry_run_ready", lower_result)
            require(getattr(captured[-1], "dry_run_only") is True, "lower dry-run elevated")

        apply_requests: list[object] = []

        def capture_apply(request: object):
            apply_requests.append(request)
            return fake_c2(
                "worker_completed",
                claim_performed=True,
                worker_invoked=True,
                worker_status="terminal_succeeded",
                queue_transition_performed=True,
                terminal=True,
            )

        with patch.object(
            queue_lane,
            "execute_one_queued_relaymem_slp_primary_job",
            capture_apply,
        ):
            first = run_relaymem_slp_scheduler_queue_lane_once(
                config=config,
                gates=scheduler_gates("apply"),
            )
            second = run_relaymem_slp_scheduler_queue_lane_once(
                config=config,
                gates=scheduler_gates("apply"),
            )
        require(first.status == second.status == "terminal", (first, second))
        require(len(apply_requests) == 2, "C2 delegation count")
        require(getattr(apply_requests[0], "apply_enabled") is True, "apply not propagated")
        require(
            getattr(apply_requests[0], "source_registry")
            is not getattr(apply_requests[1], "source_registry"),
            "source registry reused across delegations",
        )
        require(
            getattr(apply_requests[0], "queued_record") == due,
            "canonical reread record not passed exactly",
        )


def bounded_result_mapping_and_faults() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, _ = produce(queue_root, protected_root)
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        cases = (
            (fake_c2("claim_not_applied"), "candidate_changed"),
            (
                fake_c2(
                    "worker_completed",
                    claim_performed=True,
                    worker_invoked=True,
                    worker_status="retry_released",
                    queue_transition_performed=True,
                    retryable=True,
                ),
                "retry_released",
            ),
            (
                fake_c2(
                    "cleanup_required",
                    claim_performed=True,
                    worker_invoked=True,
                    worker_status="terminal_succeeded",
                    queue_transition_performed=True,
                    terminal=True,
                    cleanup_required=True,
                ),
                "cleanup_required",
            ),
            (fake_c2("source_retryable", claim_performed=True, retryable=True), "failed"),
            (fake_c2("source_blocked", claim_performed=True), "unsafe_state"),
            (fake_c2("worker_failed", claim_performed=True, worker_invoked=True), "failed"),
        )
        for fake, expected in cases:
            with patch.object(
                queue_lane,
                "execute_one_queued_relaymem_slp_primary_job",
                return_value=fake,
            ) as delegated:
                result = run_relaymem_slp_scheduler_queue_lane_once(
                    config=config,
                    gates=scheduler_gates("apply"),
                )
            require(result.status == expected, (expected, result))
            require(delegated.call_count == 1, (expected, delegated.call_count))
            require(result.delegation_completed, result)

        calls = 0

        def counted(_: object):
            nonlocal calls
            calls += 1
            return fake_c2("dry_run_ready")

        def fail_at(seam: str) -> None:
            if seam == "after_request_build_before_c2":
                raise RuntimeError("CANARY_O1C_FAULT")

        with patch.object(
            queue_lane,
            "execute_one_queued_relaymem_slp_primary_job",
            counted,
        ):
            faulted = run_relaymem_slp_scheduler_queue_lane_once(
                config=config,
                gates=scheduler_gates("apply"),
                fault_injector=fail_at,
            )
        require(faulted.status == "failed", faulted)
        require(calls == 0, "C2 called after pre-delegation fault")
        require("CANARY_O1C_FAULT" not in repr(faulted), "raw exception leaked")

        signature = inspect.signature(run_relaymem_slp_scheduler_queue_lane_once)
        require("character_id" not in signature.parameters, "public character assertion exposed")


def real_apply_terminal() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, source_path = produce(queue_root, protected_root)
        path = queue_root / record_filename(str(queued["dispatch_idempotency_key"]))
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        result = run_relaymem_slp_scheduler_queue_lane_once(
            config=config,
            gates=scheduler_gates("apply"),
        )
        require(result.status == "terminal", result)
        require(result.delegation_attempted and result.delegation_completed, result)
        require(result.mutation_may_have_occurred and result.terminal_for_candidate, result)
        require(read_record(path)["state"] == "succeeded", "terminal queue state")
        require(not source_path.exists(), "terminal protected source cleanup")


def main() -> int:
    gates_and_empty_inventory()
    future_retry_and_gate_intersection()
    bounded_result_mapping_and_faults()
    real_apply_terminal()
    print("O1C eligible queue-lane smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
