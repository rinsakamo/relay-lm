"""I1-GD bounded retention, isolation, cleanup, and leakage smoke."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import relaylm_i1gb_durable_finalization_publication_smoke as gb
import relaylm_i1gc_durable_finalization_replay_smoke as gc
from relaylm.config import RelayLMConfig
from relaylm.relaymem_slp_durable_finalization_fence import (
    acquire_relaymem_slp_durable_finalization_fence,
)
from relaylm.relaymem_slp_durable_finalization_isolation import (
    build_isolation_marker,
    isolation_filename,
    publish_relaymem_slp_durable_finalization_isolation,
    read_relaymem_slp_durable_finalization_isolation,
)
from relaylm.relaymem_slp_durable_finalization_record import (
    base_filename,
    canonical_json_bytes,
    seal_filename,
)
from relaylm.relaymem_slp_durable_finalization_retention import (
    maintain_relaymem_slp_durable_finalization_retention,
)
from relaylm.relaymem_slp_durable_finalization_replay import completion_filename

LEAK_CANARY = "CANARY_I1GD_EXCEPTION_DO_NOT_LEAK"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _config(
    root: Path,
    *,
    enabled: bool = True,
    dry: bool = False,
    apply: bool = True,
    completed: int = 60,
    orphan: int = 60,
    isolated: int = 60,
    max_per_pass: int = 64,
    timeout_ms: int = 5000,
) -> RelayLMConfig:
    base = gc._config(root)
    return base.model_copy(update={
        "relaymem_slp_durable_finalization_retention_enabled": enabled,
        "relaymem_slp_durable_finalization_retention_dry_run_only": dry,
        "relaymem_slp_durable_finalization_retention_apply_enabled": apply,
        "relaymem_slp_durable_finalization_completed_retention_seconds": completed,
        "relaymem_slp_durable_finalization_orphan_grace_seconds": orphan,
        "relaymem_slp_durable_finalization_isolated_retention_seconds": isolated,
        "relaymem_slp_durable_finalization_cleanup_max_records_per_pass": max_per_pass,
        "relaymem_slp_durable_finalization_cleanup_timeout_ms": timeout_ms,
    })


def _finalization_root(config: RelayLMConfig) -> Path:
    return Path(str(config.relaymem_slp_durable_finalization_root))


def _snapshot(root: Path) -> tuple[tuple[str, int, int], ...]:
    rows: list[tuple[str, int, int]] = []
    for path in sorted(root.iterdir()):
        info = path.lstat()
        rows.append((path.name, info.st_mode, info.st_size))
    return tuple(rows)


def _age_all(root: Path, seconds: int = 3600) -> None:
    old = time.time() - seconds
    for path in root.iterdir():
        if path.is_file() or path.is_symlink():
            os.utime(path, (old, old), follow_symlinks=False)


def _publish_base(root: Path, *, request_id: str = gb.REQUEST_ID):
    base, segments, seal = gb._records(request_id=request_id)
    store = gb._store(root / "finalization")
    require(store.publish_base(base).status == "published_new", base)
    return base, segments, seal, store


def _assert_content_free(value: object, locator: str) -> None:
    rendered = repr(value) + "\n" + json.dumps(
        value.to_log_dict(), ensure_ascii=False, sort_keys=True, default=str
    )
    for private in (
        gb.USER_CANARY,
        gb.ASSISTANT_CANARY,
        gb.NAMESPACE_CANARY,
        gb.RUN_ID,
        gb.SESSION_ID,
        gb.REQUEST_ID,
        locator,
        LEAK_CANARY,
        "slp-job-v0:",
        "slp-dispatch-v0:",
        "/private/runtime/path",
    ):
        require(private not in rendered, (private, rendered))


def test_gates_and_dry_run() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        disabled = _config(root, enabled=False, dry=True, apply=False)
        result = maintain_relaymem_slp_durable_finalization_retention(config=disabled)
        require(result.status == "disabled", result)

        base, _, _, _ = _publish_base(root)
        finalization = _finalization_root(disabled)
        _age_all(finalization)
        before = _snapshot(finalization)
        dry = _config(root, enabled=True, dry=True, apply=False, orphan=1)
        result = maintain_relaymem_slp_durable_finalization_retention(config=dry)
        require(result.status == "dry_run_ready", result)
        require(_snapshot(finalization) == before, (before, _snapshot(finalization)))
        _assert_content_free(result, str(base["locator_digest"]))

        incomplete_gate = _config(root, enabled=True, dry=False, apply=False)
        result = maintain_relaymem_slp_durable_finalization_retention(
            config=incomplete_gate
        )
        require(result.status == "blocked", result)
        require(_snapshot(finalization) == before, (before, _snapshot(finalization)))


def test_incomplete_orphan_and_isolation_lifecycle() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root, orphan=60, isolated=60)
        base, _, _, _ = _publish_base(root)
        locator = str(base["locator_digest"])
        finalization = _finalization_root(config)

        fresh = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(fresh.status == "maintenance_complete", fresh)
        require(fresh.retained_count == 1, fresh)
        require((finalization / base_filename(locator)).is_file(), fresh)

        _age_all(finalization)
        expired = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(expired.status == "maintenance_complete", expired)
        require(expired.isolated_count == 1, expired)
        require(expired.cleaned_component_count == 1, expired)
        marker = finalization / isolation_filename(locator)
        require(marker.is_file(), expired)
        require(not (finalization / base_filename(locator)).exists(), expired)
        reread = read_relaymem_slp_durable_finalization_isolation(
            str(finalization), locator
        )
        require(reread.status == "loaded", reread)

        again = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(again.status == "maintenance_complete", again)
        require(marker.is_file(), again)

        _age_all(finalization)
        removed = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(removed.status == "maintenance_complete", removed)
        require(removed.removed_isolation_count == 1, removed)
        require(not marker.exists(), removed)
        lock_name = f".durable-finalization-replay-v0-{locator}.lock"
        require((finalization / lock_name).is_file(), removed)


def test_sealed_pending_and_complete_retention() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root, completed=60, orphan=1)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        finalization = _finalization_root(config)
        _age_all(finalization)
        sealed = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(sealed.status == "maintenance_complete", sealed)
        require(sealed.retained_count == 1, sealed)
        require(not (finalization / isolation_filename(locator)).exists(), sealed)
        require((finalization / seal_filename(locator)).is_file(), sealed)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root, completed=60)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        replayed = gc._replay(config, locator)
        require(replayed.status == "completed", replayed)
        finalization = _finalization_root(config)

        retained = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(retained.status == "maintenance_complete", retained)
        require(retained.retained_count == 1, retained)
        require(replayed.projection.completion_present, replayed)

        _age_all(finalization)
        cleaned = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(cleaned.status == "maintenance_complete", cleaned)
        require(cleaned.isolated_count == 1, cleaned)
        require(cleaned.cleaned_component_count >= 3, cleaned)
        require((finalization / isolation_filename(locator)).is_file(), cleaned)
        require(not (finalization / completion_filename(locator)).exists(), cleaned)
        require(any(Path(str(config.relaymem_slp_queue_root)).iterdir()), cleaned)
        require(any(Path(str(config.relaymem_slp_protected_source_root)).iterdir()), cleaned)


def test_crash_convergence_and_replay_exclusion() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root, completed=1)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        replayed = gc._replay(config, locator)
        require(replayed.status == "completed", replayed)
        finalization = _finalization_root(config)
        _age_all(finalization)

        def crash(stage: str) -> None:
            if stage == "after_isolation_publish_before_reread":
                raise RuntimeError(LEAK_CANARY)

        try:
            maintain_relaymem_slp_durable_finalization_retention(
                config=config,
                fault_injector=crash,
            )
        except RuntimeError as error:
            require(str(error) == LEAK_CANARY, error)
        else:
            raise AssertionError("fault_not_injected")
        require((finalization / isolation_filename(locator)).is_file(), locator)
        require((finalization / seal_filename(locator)).is_file(), locator)

        blocked_replay = gc._replay(config, locator)
        require(blocked_replay.status in {"corrupt", "blocked"}, blocked_replay)
        require(not blocked_replay.projection.source_created, blocked_replay)
        require(not blocked_replay.projection.queue_created, blocked_replay)

        converged = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(converged.status == "maintenance_complete", converged)
        require(converged.cleaned_component_count >= 3, converged)
        require((finalization / isolation_filename(locator)).is_file(), converged)
        _assert_content_free(converged, locator)


def test_isolation_duplicate_collision() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root)
        finalization = _finalization_root(config)
        locator = "a" * 64
        flags = {
            "base_present": True,
            "segment_present": False,
            "seal_present": False,
            "completion_present": False,
            "corrupt_observed": False,
            "unsupported_observed": False,
        }
        marker = build_isolation_marker(
            locator_digest=locator,
            classification="expired_incomplete_orphan",
            reason_id="incomplete_orphan_expired",
            observed_component_flags=flags,
        )
        first = publish_relaymem_slp_durable_finalization_isolation(
            str(finalization), marker
        )
        second = publish_relaymem_slp_durable_finalization_isolation(
            str(finalization), marker
        )
        require(first.status == "published_new", first)
        require(second.status == "duplicate_existing", second)
        conflict = dict(marker)
        conflict["reason_id"] = "corrupt_known_record"
        conflict["isolation_digest"] = hashlib.sha256(
            canonical_json_bytes({
                key: value
                for key, value in conflict.items()
                if key != "isolation_digest"
            })
        ).hexdigest()
        third = publish_relaymem_slp_durable_finalization_isolation(
            str(finalization), conflict
        )
        require(third.status == "collision", third)


def test_shared_fence_and_unsafe_object() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root, orphan=1)
        base, _, _, _ = _publish_base(root)
        locator = str(base["locator_digest"])
        finalization = _finalization_root(config)
        _age_all(finalization)
        fence, busy, reasons = acquire_relaymem_slp_durable_finalization_fence(
            str(finalization), locator
        )
        require(fence is not None and not busy and not reasons, reasons)
        try:
            result = maintain_relaymem_slp_durable_finalization_retention(
                config=config
            )
            require(result.lock_busy_count == 1, result)
            require((finalization / base_filename(locator)).is_file(), result)
        finally:
            fence.close()

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root, orphan=1)
        finalization = _finalization_root(config)
        locator = "b" * 64
        target = finalization / "target"
        target.write_text("unsafe", encoding="utf-8")
        unsafe = finalization / base_filename(locator)
        unsafe.symlink_to(target)
        before = _snapshot(finalization)
        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.status == "blocked", result)
        require(result.blocked_count == 1, result)
        require(_snapshot(finalization) == before, (before, _snapshot(finalization)))


def test_bounded_pass_and_future_clock() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = _config(root, orphan=1, max_per_pass=1)
        first, _, _, _ = _publish_base(root, request_id="request-i1gd-one")
        second, _, _, _ = _publish_base(root, request_id="request-i1gd-two")
        finalization = _finalization_root(config)
        _age_all(finalization)
        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.processed_record_count == 1, result)
        require(result.bounded_record_count == 2, result)
        markers = list(finalization.glob("*.segment-isolation.json"))
        require(len(markers) == 1, markers)

        remaining_locator = (
            str(second["locator_digest"])
            if str(first["locator_digest"]) in markers[0].name
            else str(first["locator_digest"])
        )
        future_path = finalization / base_filename(remaining_locator)
        future = time.time() + 3600
        os.utime(future_path, (future, future))
        blocked = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(blocked.status == "blocked", blocked)
        require(future_path.is_file(), blocked)


def main() -> int:
    test_gates_and_dry_run()
    test_incomplete_orphan_and_isolation_lifecycle()
    test_sealed_pending_and_complete_retention()
    test_crash_convergence_and_replay_exclusion()
    test_isolation_duplicate_collision()
    test_shared_fence_and_unsafe_object()
    test_bounded_pass_and_future_clock()
    print("relaylm I1-GD durable-finalization retention smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
