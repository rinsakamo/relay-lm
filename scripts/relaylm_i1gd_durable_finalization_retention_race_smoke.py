"""Focused I1-GD partial-stream, crash, and cross-process race smoke."""
from __future__ import annotations

import multiprocessing
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import relaylm_i1gb_durable_finalization_publication_smoke as gb
import relaylm_i1gc_durable_finalization_replay_smoke as gc
import relaylm_i1gd_durable_finalization_retention_smoke as gd
from relaylm.relaymem_slp_durable_finalization_fence import (
    acquire_relaymem_slp_durable_finalization_fence,
)
from relaylm.relaymem_slp_durable_finalization_isolation import isolation_filename
from relaylm.relaymem_slp_durable_finalization_record import (
    base_filename,
    seal_filename,
    segment_filename,
)
from relaylm.relaymem_slp_durable_finalization_replay import completion_filename
from relaylm.relaymem_slp_durable_finalization_retention import (
    maintain_relaymem_slp_durable_finalization_retention,
)


class InjectedCrash(RuntimeError):
    pass


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def test_fresh_and_expired_partial_stream() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root, orphan=60, isolated=3600)
        base, segments, _ = gb._records(
            contents=("partial-one", "partial-two"),
            request_id="request-i1gd-partial-stream",
        )
        locator = str(base["locator_digest"])
        store = gb._store(gd._finalization_root(config))
        require(store.publish_base(base).status == "published_new", base)
        require(store.publish_segment(segments[0]).status == "published_new", segments[0])

        fresh = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(fresh.status == "maintenance_complete", fresh)
        require(fresh.retained_count == 1, fresh)
        finalization = gd._finalization_root(config)
        require((finalization / base_filename(locator)).is_file(), fresh)
        require((finalization / segment_filename(locator, 0)).is_file(), fresh)

        gd._age_all(finalization)
        expired = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(expired.status == "maintenance_complete", expired)
        require(expired.isolated_count == 1, expired)
        require(expired.cleaned_component_count == 2, expired)
        require((finalization / isolation_filename(locator)).is_file(), expired)
        require(not (finalization / base_filename(locator)).exists(), expired)
        require(not (finalization / segment_filename(locator, 0)).exists(), expired)


def test_partial_component_cleanup_crash_converges() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root, completed=1, isolated=3600)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        replayed = gc._replay(config, locator)
        require(replayed.status == "completed", replayed)
        finalization = gd._finalization_root(config)
        gd._age_all(finalization)
        cleanup_calls = 0

        def crash(stage: str) -> None:
            nonlocal cleanup_calls
            if stage == "during_component_cleanup":
                cleanup_calls += 1
                if cleanup_calls == 2:
                    raise InjectedCrash(stage)

        try:
            maintain_relaymem_slp_durable_finalization_retention(
                config=config,
                fault_injector=crash,
            )
        except InjectedCrash:
            pass
        else:
            raise AssertionError("partial_cleanup_crash_not_injected")

        require((finalization / isolation_filename(locator)).is_file(), locator)
        require(not (finalization / base_filename(locator)).exists(), locator)
        require((finalization / seal_filename(locator)).is_file(), locator)
        require((finalization / completion_filename(locator)).is_file(), locator)

        converged = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(converged.status == "maintenance_complete", converged)
        require(converged.cleaned_component_count == 2, converged)
        require(not (finalization / seal_filename(locator)).exists(), converged)
        require(not (finalization / completion_filename(locator)).exists(), converged)
        require((finalization / isolation_filename(locator)).is_file(), converged)


def test_marker_delete_crash_converges_by_canonical_reread() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root, orphan=1, isolated=1)
        base, _, _, _ = gd._publish_base(
            root,
            request_id="request-i1gd-marker-delete-crash",
        )
        locator = str(base["locator_digest"])
        finalization = gd._finalization_root(config)
        gd._age_all(finalization)
        isolated = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(isolated.isolated_count == 1, isolated)
        marker = finalization / isolation_filename(locator)
        require(marker.is_file(), isolated)
        gd._age_all(finalization)

        def crash(stage: str) -> None:
            if stage == "after_isolation_marker_delete_before_directory_fsync":
                raise InjectedCrash(stage)

        try:
            maintain_relaymem_slp_durable_finalization_retention(
                config=config,
                fault_injector=crash,
            )
        except InjectedCrash:
            pass
        else:
            raise AssertionError("marker_delete_crash_not_injected")
        require(not marker.exists(), marker)

        converged = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(converged.status == "maintenance_complete", converged)
        require(converged.processed_record_count == 0, converged)


def test_post_isolation_republication_is_blocked() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root, orphan=1, isolated=3600)
        base, _, _, store = gd._publish_base(
            root,
            request_id="request-i1gd-post-isolation-republish",
        )
        locator = str(base["locator_digest"])
        finalization = gd._finalization_root(config)
        gd._age_all(finalization)
        isolated = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(isolated.isolated_count == 1, isolated)
        marker = finalization / isolation_filename(locator)
        require(marker.is_file(), isolated)

        republished = store.publish_base(base)
        require(republished.status == "published_new", republished)
        base_path = finalization / base_filename(locator)
        marker_mtime = marker.stat().st_mtime_ns
        newer = (marker_mtime + 2_000_000_000) / 1_000_000_000
        os.utime(base_path, (newer, newer))

        blocked = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(blocked.status == "blocked", blocked)
        require(
            "durable_finalization_component_newer_than_isolation"
            in blocked.reason_ids,
            blocked,
        )
        require(base_path.is_file(), blocked)
        require(marker.is_file(), blocked)


def _hold_fence(
    root: str,
    locator: str,
    ready: multiprocessing.synchronize.Event,
    release: multiprocessing.synchronize.Event,
    outcome: multiprocessing.queues.Queue,
) -> None:
    fence, busy, reasons = acquire_relaymem_slp_durable_finalization_fence(
        root,
        locator,
    )
    outcome.put((fence is not None, busy, reasons))
    if fence is None:
        ready.set()
        return
    try:
        ready.set()
        release.wait(10)
    finally:
        fence.close()


def test_cross_process_same_locator_contention() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root, orphan=1)
        base, _, _, _ = gd._publish_base(
            root,
            request_id="request-i1gd-cross-process-fence",
        )
        locator = str(base["locator_digest"])
        finalization = gd._finalization_root(config)
        gd._age_all(finalization)

        context = multiprocessing.get_context("fork")
        ready = context.Event()
        release = context.Event()
        outcome = context.Queue()
        process = context.Process(
            target=_hold_fence,
            args=(str(finalization), locator, ready, release, outcome),
        )
        process.start()
        require(ready.wait(10), "child_fence_not_ready")
        acquired, busy, reasons = outcome.get(timeout=10)
        require(acquired and not busy and not reasons, (acquired, busy, reasons))
        try:
            blocked = maintain_relaymem_slp_durable_finalization_retention(
                config=config
            )
            require(blocked.lock_busy_count == 1, blocked)
            require((finalization / base_filename(locator)).is_file(), blocked)
        finally:
            release.set()
            process.join(10)
            if process.is_alive():
                process.terminate()
                process.join(5)
        require(process.exitcode == 0, process.exitcode)


def main() -> int:
    test_fresh_and_expired_partial_stream()
    test_partial_component_cleanup_crash_converges()
    test_marker_delete_crash_converges_by_canonical_reread()
    test_post_isolation_republication_is_blocked()
    test_cross_process_same_locator_contention()
    print("relaylm I1-GD retention race smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
