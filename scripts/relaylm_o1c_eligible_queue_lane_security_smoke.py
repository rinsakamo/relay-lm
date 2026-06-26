"""Security and fail-closed smoke for O1C eligible queue-lane discovery."""
from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import relaylm.relaymem_slp_queue_candidate as candidate_helper
import relaylm.relaymem_slp_scheduler_queue_lane as queue_lane
from relaylm.relaymem_slp_queue_record import (
    FILENAME_PREFIX,
    MAX_RECORD_BYTES,
    record_filename,
)
from relaylm.relaymem_slp_scheduler_contract import SchedulerGates
from relaylm.relaymem_slp_scheduler_queue_lane import (
    run_relaymem_slp_scheduler_queue_lane_once,
)

from _relaylm_o0_local_worker_support import (
    assert_content_free,
    build_config,
    prepare_scoped_store,
    produce,
)
from relaylm_phase6c1_primary_worker_test_support import require

CANARY_EXCEPTION = "CANARY_O1C_EXCEPTION_DO_NOT_LEAK"
CANARY_NAMESPACE = "CANARY_O1C_NAMESPACE_DO_NOT_LEAK"
CANARY_PATH = "/CANARY/O1C/PATH/DO/NOT/LEAK"


def gates() -> SchedulerGates:
    return SchedulerGates(
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        replay_lane_enabled=True,
        queue_lane_enabled=True,
        required_dependency_available=True,
        supported_schema=True,
    )


def canonical_name(digit: str = "0") -> str:
    return f"{FILENAME_PREFIX}{digit * 64}.json"


def fake_c2(*, status: str = "dry_run_ready", reason_ids: tuple[str, ...] = ()):
    return SimpleNamespace(
        status=status,
        claim_attempted=True,
        claim_performed=False,
        source_prepared=False,
        restart_rehydrated=False,
        worker_invoked=False,
        worker_status=None,
        queue_transition_performed=False,
        retryable=False,
        terminal=False,
        cleanup_required=False,
        reason_ids=reason_ids,
        private_canary=CANARY_EXCEPTION,
        private_path=CANARY_PATH,
    )


def run(config: object, **kwargs: object):
    return run_relaymem_slp_scheduler_queue_lane_once(
        config=config,  # type: ignore[arg-type]
        gates=gates(),
        **kwargs,
    )


def discovery_bound_and_nonrecursive() -> None:
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
        for index in range(4):
            (queue_root / f"ignored-{index}").write_text("ignored", encoding="utf-8")
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
            discovery_max_entries=2,
        )
        with patch.object(queue_lane, "execute_one_queued_relaymem_slp_primary_job") as c2:
            result = run(config)
        require(result.status == "unsafe_state" and result.unsafe, result)
        require("queue_discovery_limit_exceeded" in result.bounded_reason_ids, result)
        require(not c2.called, "partial inventory delegated C2")
        require(source_path.exists(), "cap failure consumed protected source")

    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        nested = queue_root / "nested"
        nested.mkdir()
        (nested / canonical_name()).write_bytes(b"{malformed")
        config = build_config(
            queue_root,
            Path(protected_dir),
            Path(memory_dir),
            "character/default",
        )
        result = run(config)
        require(result.status == "no_eligible_work", result)
        require(not result.candidate_selected, result)


def unsafe_record_objects() -> None:
    payloads = (
        (b"\xff\xfe", "queue_record_malformed_utf8"),
        (b"{not-json", "queue_record_malformed_json"),
        (b"x" * (MAX_RECORD_BYTES + 1), "queue_record_size_exceeded"),
    )
    for payload, reason in payloads:
        with (
            TemporaryDirectory() as queue_dir,
            TemporaryDirectory() as protected_dir,
            TemporaryDirectory() as memory_dir,
        ):
            queue_root = Path(queue_dir)
            path = queue_root / canonical_name()
            path.write_bytes(payload)
            config = build_config(
                queue_root,
                Path(protected_dir),
                Path(memory_dir),
                "character/default",
            )
            with patch.object(queue_lane, "execute_one_queued_relaymem_slp_primary_job") as c2:
                result = run(config)
            require(result.status == "unsafe_state", (reason, result))
            require(reason in result.bounded_reason_ids, (reason, result))
            require(not c2.called, (reason, "unsafe record delegated"))
            require(path.read_bytes() == payload, "unsafe record was repaired")

    for kind in ("directory", "fifo"):
        with (
            TemporaryDirectory() as queue_dir,
            TemporaryDirectory() as protected_dir,
            TemporaryDirectory() as memory_dir,
        ):
            queue_root = Path(queue_dir)
            path = queue_root / canonical_name()
            if kind == "directory":
                path.mkdir()
            else:
                os.mkfifo(path)
            config = build_config(
                queue_root,
                Path(protected_dir),
                Path(memory_dir),
                "character/default",
            )
            result = run(config)
            require(result.status == "unsafe_state", (kind, result))
            require("queue_record_unexpected_file_type" in result.bounded_reason_ids, result)


def symlink_hardlink_and_root_security() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as target_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        target = Path(target_dir) / "target.json"
        target.write_bytes(b"{}")
        (queue_root / canonical_name()).symlink_to(target)
        config = build_config(
            queue_root,
            Path(protected_dir),
            Path(memory_dir),
            "character/default",
        )
        result = run(config)
        require(result.status == "unsafe_state", result)
        require("queue_record_symlink_blocked" in result.bounded_reason_ids, result)

    with (
        TemporaryDirectory() as parent_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        parent = Path(parent_dir)
        actual = parent / "actual"
        actual.mkdir()
        linked = parent / "queue-link"
        linked.symlink_to(actual, target_is_directory=True)
        config = build_config(
            linked.absolute(),
            Path(protected_dir),
            Path(memory_dir),
            "character/default",
        )
        result = run(config)
        require(result.status == "unsafe_state", result)
        require("queue_root_symlink_blocked" in result.bounded_reason_ids, result)

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
        canonical = queue_root / record_filename(str(queued["dispatch_idempotency_key"]))
        os.link(canonical, queue_root / "nonmatching-hardlink")
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        result = run(config)
        require(result.status == "unsafe_state", result)
        require("queue_record_hardlink_count_invalid" in result.bounded_reason_ids, result)
        require(source_path.exists(), "hardlink failure consumed source")


def lock_behavior() -> None:
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
        with patch.object(candidate_helper, "acquire_queue_lock", return_value="queue_lock_busy"):
            busy = run(config)
        require(busy.status == "busy", busy)
        require(busy.contention_observed and not busy.delegation_attempted, busy)

        with patch.object(candidate_helper, "acquire_queue_lock", return_value="queue_lock_failed"):
            failed = run(config)
        require(failed.status == "unsafe_state" and failed.unsafe, failed)
        require("queue_lock_failed" in failed.bounded_reason_ids, failed)


def canonical_reread_race() -> None:
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
        original = queue_lane.discover_relaymem_slp_queue_candidate

        def replace_after_selection(*args: object, **kwargs: object):
            discovered = original(*args, **kwargs)
            require(discovered.candidate is not None, discovered)
            replacement = path.with_name(path.name + ".replacement")
            replacement.write_bytes(path.read_bytes())
            os.replace(replacement, path)
            return discovered

        with (
            patch.object(
                queue_lane,
                "discover_relaymem_slp_queue_candidate",
                replace_after_selection,
            ),
            patch.object(queue_lane, "execute_one_queued_relaymem_slp_primary_job") as c2,
        ):
            result = run(config)
        require(result.status == "candidate_changed", result)
        require(result.candidate_selected and result.canonical_reread_performed, result)
        require(not c2.called, "changed candidate delegated")
        require(source_path.exists(), "reread race consumed source")


def scope_and_leakage() -> None:
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
        namespace = str(queued["namespace"])
        ambiguous = build_config(
            queue_root,
            protected_root,
            memory_root,
            namespace,
            extra_character_id="second-character",
        )
        with patch.object(queue_lane, "execute_one_queued_relaymem_slp_primary_job") as c2:
            result = run(ambiguous)
        require(result.status == "failed", result)
        require("local_worker_character_scope_ambiguous" in result.bounded_reason_ids, result)
        require(not c2.called, "ambiguous scope delegated")
        require(source_path.exists(), "ambiguous scope consumed source")

        exact = build_config(
            queue_root,
            protected_root,
            memory_root,
            namespace,
            mode="dry_run",
        )
        with patch.object(
            queue_lane,
            "execute_one_queued_relaymem_slp_primary_job",
            return_value=fake_c2(),
        ):
            projected = run(exact)
        require(projected.status == "dry_run_ready", projected)
        assert_content_free(
            projected,
            CANARY_EXCEPTION,
            CANARY_NAMESPACE,
            CANARY_PATH,
            namespace,
            str(queue_root),
            str(source_path),
            str(queued["job_id"]),
            str(queued["dispatch_idempotency_key"]),
        )
        private = projected.private_delegate_result
        require(CANARY_EXCEPTION not in repr(private), "private C2 result leaked")

        relative = exact.model_copy(update={"relaymem_slp_queue_root": "../queue"})
        invalid = run(relative)
        require(invalid.status == "unsafe_state", invalid)
        require(CANARY_PATH not in repr(invalid), "invalid root leaked")


def fault_seams_are_bounded() -> None:
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
        call_count = 0

        def delegated(_: object):
            nonlocal call_count
            call_count += 1
            return fake_c2()

        def inject(seam: str) -> None:
            if seam == "after_c2_before_lane_mapping":
                raise RuntimeError(CANARY_EXCEPTION)

        with patch.object(
            queue_lane,
            "execute_one_queued_relaymem_slp_primary_job",
            delegated,
        ):
            result = run(config, fault_injector=inject)
        require(result.status == "failed", result)
        require(call_count == 1, "fault caused C2 retry or fallback")
        require(result.delegation_attempted and not result.delegation_completed, result)
        require(CANARY_EXCEPTION not in repr(result), "fault exception leaked")


def main() -> int:
    discovery_bound_and_nonrecursive()
    unsafe_record_objects()
    symlink_hardlink_and_root_security()
    lock_behavior()
    canonical_reread_race()
    scope_and_leakage()
    fault_seams_are_bounded()
    print("O1C eligible queue-lane security smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
