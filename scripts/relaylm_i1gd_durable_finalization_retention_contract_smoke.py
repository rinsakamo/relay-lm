"""Focused I1-GD capacity, exact-completion, and corruption smoke."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import relaylm_i1gb_durable_finalization_publication_smoke as gb
import relaylm_i1gc_durable_finalization_replay_smoke as gc
import relaylm_i1gd_durable_finalization_retention_smoke as gd
from relaylm.relaymem_slp_durable_finalization_isolation import isolation_filename
from relaylm.relaymem_slp_durable_finalization_record import (
    base_filename,
    build_segment_record,
    canonical_json_bytes,
    seal_filename,
)
from relaylm.relaymem_slp_durable_finalization_replay import completion_filename
from relaylm.relaymem_slp_durable_finalization_retention import (
    maintain_relaymem_slp_durable_finalization_retention,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def test_disabled_without_root() -> None:
    with TemporaryDirectory() as directory:
        config = gd._config(
            Path(directory), enabled=False, dry=True, apply=False
        ).model_copy(
            update={"relaymem_slp_durable_finalization_root": None}
        )
        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.status == "disabled", result)
        require(result.blocked_count == 0, result)


def test_logical_record_capacity_is_non_mutating() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root, orphan=1).model_copy(
            update={"relaymem_slp_durable_finalization_max_record_count": 1}
        )
        first, _, _, _ = gd._publish_base(
            root,
            request_id="request-i1gd-capacity-one",
        )
        finalization = gd._finalization_root(config)
        gd._write_distinct_known_locator(
            finalization,
            str(first["locator_digest"]),
        )
        gd._age_all(finalization)
        before = gd._snapshot(finalization)
        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.status == "capacity_exceeded", result)
        require(result.capacity_exceeded, result)
        require(result.processed_record_count == 0, result)
        require(gd._snapshot(finalization) == before, result)


def test_completion_requires_exact_reconstructed_proof() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root, completed=1)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        replayed = gc._replay(config, locator)
        require(replayed.status == "completed", replayed)
        finalization = gd._finalization_root(config)
        marker_path = finalization / completion_filename(locator)
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        marker["protected_source_integrity_digest"] = "f" * 64
        marker["completion_digest"] = hashlib.sha256(
            canonical_json_bytes(
                {
                    key: value
                    for key, value in marker.items()
                    if key != "completion_digest"
                }
            )
        ).hexdigest()
        marker_path.write_bytes(canonical_json_bytes(marker))
        gd._age_all(finalization)

        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.status == "blocked", result)
        require(
            "durable_finalization_completion_identity_collision"
            in result.reason_ids,
            result,
        )
        require((finalization / base_filename(locator)).is_file(), result)
        require((finalization / seal_filename(locator)).is_file(), result)
        require(marker_path.is_file(), result)
        require(not (finalization / isolation_filename(locator)).exists(), result)


def test_known_corrupt_and_unsupported_isolate_before_cleanup() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root)
        finalization = gd._finalization_root(config)
        locator = "c" * 64
        unsupported = finalization / base_filename(locator)
        unsupported.write_bytes(
            canonical_json_bytes(
                {"schema_version": "relaymem.slp_durable_finalization.v999"}
            )
        )
        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.status == "maintenance_complete", result)
        require(result.isolated_count == 1, result)
        require(result.cleaned_component_count == 1, result)
        require(not unsupported.exists(), result)
        require((finalization / isolation_filename(locator)).is_file(), result)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root)
        finalization = gd._finalization_root(config)
        locator = "d" * 64
        corrupt = finalization / base_filename(locator)
        corrupt.write_bytes(b'{"schema_version":"a","schema_version":"b"}')
        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.status == "maintenance_complete", result)
        require(result.isolated_count == 1, result)
        require(result.cleaned_component_count == 1, result)
        require(not corrupt.exists(), result)
        require((finalization / isolation_filename(locator)).is_file(), result)


def test_impossible_known_combinations_isolate() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root)
        base, _, _, store = gd._publish_base(
            root,
            request_id="request-i1gd-segment-without-base",
        )
        locator = str(base["locator_digest"])
        segment = build_segment_record(
            base=base,
            sequence=0,
            previous_segment_digest=gb.ZERO_DIGEST,
            content=b"orphan",
        )
        require(store.publish_segment(segment).status == "published_new", segment)
        finalization = gd._finalization_root(config)
        (finalization / base_filename(locator)).unlink()
        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.status == "maintenance_complete", result)
        require(
            (finalization / isolation_filename(locator)).is_file(),
            result,
        )
        require(
            not list(
                finalization.glob(
                    f"durable-finalization-v0-{locator}.segment-[0-9]*.json"
                )
            ),
            result,
        )

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        replayed = gc._replay(config, locator)
        require(replayed.status == "completed", replayed)
        finalization = gd._finalization_root(config)
        (finalization / seal_filename(locator)).unlink()
        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.status == "maintenance_complete", result)
        require((finalization / isolation_filename(locator)).is_file(), result)
        require(not (finalization / completion_filename(locator)).exists(), result)


def test_hardlink_and_fifo_are_non_mutating() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gd._config(root, orphan=1)
        base, _, _, _ = gd._publish_base(root)
        locator = str(base["locator_digest"])
        finalization = gd._finalization_root(config)
        os.link(
            finalization / base_filename(locator),
            finalization / "hardlink-canary",
        )
        before = gd._snapshot(finalization)
        result = maintain_relaymem_slp_durable_finalization_retention(config=config)
        require(result.status == "blocked", result)
        require(gd._snapshot(finalization) == before, result)
        require(not (finalization / isolation_filename(locator)).exists(), result)

    if hasattr(os, "mkfifo"):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config = gd._config(root)
            finalization = gd._finalization_root(config)
            locator = "e" * 64
            fifo = finalization / base_filename(locator)
            os.mkfifo(fifo)
            before = gd._snapshot(finalization)
            result = maintain_relaymem_slp_durable_finalization_retention(
                config=config
            )
            require(result.status == "blocked", result)
            require(gd._snapshot(finalization) == before, result)


def main() -> int:
    test_disabled_without_root()
    test_logical_record_capacity_is_non_mutating()
    test_completion_requires_exact_reconstructed_proof()
    test_known_corrupt_and_unsupported_isolate_before_cleanup()
    test_impossible_known_combinations_isolate()
    test_hardlink_and_fifo_are_non_mutating()
    print("relaylm I1-GD retention contract smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
