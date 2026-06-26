#!/usr/bin/env python3
"""Fresh-process I1-GE child used only by bounded crash-validation smokes."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from contextlib import ExitStack
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import time
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import relaylm.app as app_module  # noqa: E402
import relaylm._relaymem_slp_durable_finalization_replay_impl as replay_impl  # noqa: E402
import relaylm._relaymem_slp_durable_finalization_retention_impl as retention_impl  # noqa: E402
import relaylm.relaymem_slp_durable_finalization_store as store_module  # noqa: E402
import relaylm_i1gb_durable_finalization_app_smoke as app_smoke  # noqa: E402
import relaylm_i1gc_durable_finalization_replay_smoke as gc  # noqa: E402
import relaylm_i1gd_durable_finalization_retention_smoke as gd  # noqa: E402
import relaylm_o1b_sealed_replay_lane_smoke as o1b  # noqa: E402
from relaylm.app import create_app  # noqa: E402
from relaylm.relaymem_slp_durable_finalization_publication import (  # noqa: E402
    RelayMEMSLPDurableFinalizationStreamSession,
)
from relaylm.relaymem_slp_durable_finalization_retention import (  # noqa: E402
    maintain_relaymem_slp_durable_finalization_retention,
)

NONSTREAM_SEAMS = (
    "before_base_publication",
    "after_base_file_publication_before_canonical_reread",
    "after_base_reread_before_finalized_source_seal",
    "during_seal_no_clobber_publication",
    "after_seal_publication_before_canonical_reread",
    "after_seal_canonical_reread_before_http_body_release",
    "after_protected_body_release_before_normal_finalizer",
    "during_normal_finalizer_before_c1_5",
)
STREAM_SEAMS = (
    "after_stream_base_publication",
    "during_segment_no_clobber_publication",
    "after_segment_publication_before_canonical_reread",
    "after_segment_reread_before_corresponding_visible_yield",
    "after_protected_visible_segment_before_next_segment",
    "after_final_segment_before_seal",
    "during_final_seal_publication",
    "after_seal_reread_before_terminal_sse_completion",
    "after_terminal_visible_completion_before_normal_finalizer",
)
REPLAY_SEAMS = (
    "after_record_fence_acquisition_before_canonical_reread",
    "after_exact_finalized_turn_reconstruction",
    "during_c1_5_publication",
    "after_c1_5_publication_before_canonical_reread",
    "after_exact_c1_5_reread_before_b2",
    "during_b2_publication",
    "after_b2_publication_before_canonical_reread",
    "after_exact_b2_reread_before_downstream_verification",
    "after_downstream_verification_before_completion_marker",
    "during_completion_marker_publication",
    "after_completion_marker_publication_before_canonical_reread",
    "after_completion_reread_before_caller_return",
)
RETENTION_SEAMS = (
    "after_record_fence_before_root_mutation_lock",
    "after_fresh_reclassification_before_isolation",
    "during_isolation_marker_publication",
    "after_isolation_marker_reread_before_first_component_deletion",
    "between_known_component_deletions",
    "after_component_deletion_before_directory_fsync",
    "after_all_logical_components_removed_before_marker_horizon",
    "during_final_isolation_marker_deletion",
    "after_marker_deletion_before_caller_return",
)
ALL_SEAMS = NONSTREAM_SEAMS + STREAM_SEAMS + REPLAY_SEAMS + RETENTION_SEAMS
EXIT_CODES = {name: 70 + index for index, name in enumerate(ALL_SEAMS)}


def _crash(seam: str) -> None:
    os._exit(EXIT_CODES[seam])


def _result_path(root: Path, name: str) -> Path:
    return root / f".i1ge-{name}.json"


def _write_result(root: Path, name: str, status: str) -> None:
    _result_path(root, name).write_text(
        json.dumps({"status": status}, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _locator(root: Path) -> str:
    bases = sorted((root / "finalization").glob("durable-finalization-v0-*.base.json"))
    if len(bases) != 1:
        raise AssertionError(("exact_base_required", [path.name for path in bases]))
    name = bases[0].name
    return name[len("durable-finalization-v0-") : -len(".base.json")]


def _configure_app(root: Path, backend_port: int) -> Path:
    for name in ("queue", "source", "finalization"):
        (root / name).mkdir(parents=True, exist_ok=True)
    config = root / "config.yaml"
    app_smoke._write_config(
        config,
        backend_port=backend_port,
        mode="apply",
        queue_root=root / "queue",
        protected_root=root / "source",
        finalization_root=root / "finalization",
    )
    return config


def _rename_wrapper(seam: str):
    original = store_module._rename_noreplace

    def wrapped(root_fd: int, temporary: str, final: str) -> str:
        is_base = final.endswith(".base.json")
        is_segment = ".segment-" in final
        is_seal = final.endswith(".seal.json")
        before = (
            (seam == "during_seal_no_clobber_publication" and is_seal)
            or (seam == "during_segment_no_clobber_publication" and is_segment)
            or (seam == "during_final_seal_publication" and is_seal)
        )
        if before:
            _crash(seam)
        result = original(root_fd, temporary, final)
        after = (
            seam == "after_base_file_publication_before_canonical_reread" and is_base
        ) or (
            seam == "after_seal_publication_before_canonical_reread" and is_seal
        ) or (
            seam == "after_segment_publication_before_canonical_reread" and is_segment
        )
        if after and result == "published":
            _crash(seam)
        return result

    return wrapped


def _run_app(root: Path, seam: str, *, stream: bool) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), app_smoke._BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = _configure_app(root, int(server.server_address[1]))

    with ExitStack() as stack:
        if seam in {
            "after_base_file_publication_before_canonical_reread",
            "during_seal_no_clobber_publication",
            "after_seal_publication_before_canonical_reread",
            "during_segment_no_clobber_publication",
            "after_segment_publication_before_canonical_reread",
            "during_final_seal_publication",
        }:
            stack.enter_context(
                patch.object(store_module, "_rename_noreplace", new=_rename_wrapper(seam))
            )

        if seam == "before_base_publication":
            original = store_module.RelayMEMSLPDurableFinalizationStore.publish_base

            def publish_base_before(self: Any, value: object):
                del self, value
                _crash(seam)

            stack.enter_context(
                patch.object(
                    store_module.RelayMEMSLPDurableFinalizationStore,
                    "publish_base",
                    new=publish_base_before,
                )
            )
        elif seam == "after_base_reread_before_finalized_source_seal":
            original = store_module.RelayMEMSLPDurableFinalizationStore.publish_base

            def publish_base_after(self: Any, value: object):
                result = original(self, value)
                if result.status in {"published_new", "duplicate_existing"}:
                    _crash(seam)
                return result

            stack.enter_context(
                patch.object(
                    store_module.RelayMEMSLPDurableFinalizationStore,
                    "publish_base",
                    new=publish_base_after,
                )
            )

        if seam == "after_seal_canonical_reread_before_http_body_release":
            original_admit = app_module.admit_relaymem_slp_durable_finalization_nonstream

            def admit_after(*args: Any, **kwargs: Any):
                result = original_admit(*args, **kwargs)
                if result.status in {"published", "duplicate_existing"}:
                    _crash(seam)
                return result

            stack.enter_context(
                patch.object(
                    app_module,
                    "admit_relaymem_slp_durable_finalization_nonstream",
                    new=admit_after,
                )
            )

        if seam == "after_stream_base_publication":
            original_start = app_module.start_relaymem_slp_durable_finalization_stream

            def start_after(*args: Any, **kwargs: Any):
                session, result = original_start(*args, **kwargs)
                if session is not None and result.status in {"published", "duplicate_existing"}:
                    _crash(seam)
                return session, result

            stack.enter_context(
                patch.object(
                    app_module,
                    "start_relaymem_slp_durable_finalization_stream",
                    new=start_after,
                )
            )

        if seam == "after_segment_reread_before_corresponding_visible_yield":
            original_unit = RelayMEMSLPDurableFinalizationStreamSession.publish_content_unit

            def unit_after(self: Any, content_text: str) -> None:
                original_unit(self, content_text)
                _crash(seam)

            stack.enter_context(
                patch.object(
                    RelayMEMSLPDurableFinalizationStreamSession,
                    "publish_content_unit",
                    new=unit_after,
                )
            )

        if seam in {"after_final_segment_before_seal", "after_seal_reread_before_terminal_sse_completion"}:
            original_seal = RelayMEMSLPDurableFinalizationStreamSession.seal

            def seal_wrapped(self: Any):
                if seam == "after_final_segment_before_seal":
                    _crash(seam)
                result = original_seal(self)
                _crash(seam)
                return result

            stack.enter_context(
                patch.object(
                    RelayMEMSLPDurableFinalizationStreamSession,
                    "seal",
                    new=seal_wrapped,
                )
            )

        if seam in {"during_normal_finalizer_before_c1_5"}:
            def finalizer_crash(*args: Any, **kwargs: Any) -> None:
                del args, kwargs
                _crash(seam)

            stack.enter_context(
                patch.object(
                    app_module,
                    "run_relaymem_slp_runtime_enqueue_after_response",
                    new=finalizer_crash,
                )
            )

        visible_segments = 0

        async def before_send(message: dict[str, Any]) -> None:
            nonlocal visible_segments
            if message.get("type") != "http.response.body":
                return
            body = bytes(message.get("body", b""))
            if (
                seam == "after_protected_body_release_before_normal_finalizer"
                and body
            ):
                _crash(seam)
            if stream and b'"content"' in body:
                visible_segments += 1
                if (
                    seam == "after_protected_visible_segment_before_next_segment"
                    and visible_segments == 1
                ):
                    _crash(seam)
            if (
                seam == "after_terminal_visible_completion_before_normal_finalizer"
                and b"[DONE]" in body
            ):
                _crash(seam)

        app = create_app(str(config))
        asyncio.run(
            app_smoke._invoke_asgi(
                app,
                app_smoke._payload(stream=stream),
                before_send=before_send,
            )
        )
    server.shutdown()
    raise AssertionError(("fault_seam_not_reached", seam))


def _run_replay(root: Path, seam: str) -> None:
    config = gc._config(root)
    locator = _locator(root)
    fault_stage = {
        "after_record_fence_acquisition_before_canonical_reread": "after_lock_before_reread",
        "after_exact_c1_5_reread_before_b2": "after_source_commit_before_queue",
        "after_downstream_verification_before_completion_marker": "after_queue_commit_before_completion",
        "after_completion_reread_before_caller_return": "after_completion_publish_before_return",
    }.get(seam)

    def fault(stage: str) -> None:
        if stage == fault_stage:
            _crash(seam)

    with ExitStack() as stack:
        if seam == "after_exact_finalized_turn_reconstruction":
            original = replay_impl._reconstruct_source

            def reconstructed(*args: Any, **kwargs: Any):
                result = original(*args, **kwargs)
                if result[0] is not None:
                    _crash(seam)
                return result

            stack.enter_context(patch.object(replay_impl, "_reconstruct_source", new=reconstructed))

        if seam in {"during_c1_5_publication", "after_c1_5_publication_before_canonical_reread"}:
            original = replay_impl.RelayMEMSLPDurableProtectedSourceStore.persist

            def source_persist(self: Any, *args: Any, **kwargs: Any):
                if seam == "during_c1_5_publication":
                    _crash(seam)
                result = original(self, *args, **kwargs)
                _crash(seam)
                return result

            stack.enter_context(
                patch.object(
                    replay_impl.RelayMEMSLPDurableProtectedSourceStore,
                    "persist",
                    new=source_persist,
                )
            )

        if seam in {"during_b2_publication", "after_b2_publication_before_canonical_reread"}:
            original = replay_impl.apply_relaymem_slp_runtime_enqueue

            def queue_apply(*args: Any, **kwargs: Any):
                if seam == "during_b2_publication":
                    _crash(seam)
                result = original(*args, **kwargs)
                _crash(seam)
                return result

            stack.enter_context(
                patch.object(replay_impl, "apply_relaymem_slp_runtime_enqueue", new=queue_apply)
            )

        if seam == "after_exact_b2_reread_before_downstream_verification":
            original = replay_impl._inspect_queue
            calls = 0

            def inspect_queue(*args: Any, **kwargs: Any):
                nonlocal calls
                result = original(*args, **kwargs)
                calls += 1
                if calls >= 2:
                    _crash(seam)
                return result

            stack.enter_context(patch.object(replay_impl, "_inspect_queue", new=inspect_queue))

        if seam in {
            "during_completion_marker_publication",
            "after_completion_marker_publication_before_canonical_reread",
        }:
            original = replay_impl._publish_completion

            def publish_completion(*args: Any, **kwargs: Any):
                if seam == "during_completion_marker_publication":
                    _crash(seam)
                result = original(*args, **kwargs)
                _crash(seam)
                return result

            stack.enter_context(
                patch.object(replay_impl, "_publish_completion", new=publish_completion)
            )

        gc._replay(config, locator, fault=fault if fault_stage else None)
    raise AssertionError(("fault_seam_not_reached", seam))


def _run_retention(root: Path, seam: str) -> None:
    config = gd._config(root, completed=1, orphan=1, isolated=1)
    fault_stage = {
        "after_record_fence_before_root_mutation_lock": "after_lock_before_reread",
        "after_isolation_marker_reread_before_first_component_deletion": "after_isolation_reread_before_first_unlink",
        "after_component_deletion_before_directory_fsync": "after_component_cleanup_before_directory_fsync",
        "after_all_logical_components_removed_before_marker_horizon": "after_directory_fsync_before_return",
        "during_final_isolation_marker_deletion": "during_isolation_marker_delete",
        "after_marker_deletion_before_caller_return": "after_isolation_marker_delete_before_directory_fsync",
    }.get(seam)
    cleanup_calls = 0

    def fault(stage: str) -> None:
        nonlocal cleanup_calls
        if seam == "between_known_component_deletions" and stage == "during_component_cleanup":
            cleanup_calls += 1
            if cleanup_calls == 2:
                _crash(seam)
        if stage == fault_stage:
            _crash(seam)

    with ExitStack() as stack:
        if seam == "after_fresh_reclassification_before_isolation":
            original = retention_impl._apply_classified

            def apply_after_classification(*args: Any, **kwargs: Any):
                _crash(seam)
                return original(*args, **kwargs)

            stack.enter_context(
                patch.object(retention_impl, "_apply_classified", new=apply_after_classification)
            )
        if seam == "during_isolation_marker_publication":
            def isolation_publish(*args: Any, **kwargs: Any):
                del args, kwargs
                _crash(seam)

            stack.enter_context(
                patch.object(
                    retention_impl,
                    "publish_relaymem_slp_durable_finalization_isolation",
                    new=isolation_publish,
                )
            )
        maintain_relaymem_slp_durable_finalization_retention(
            config=config,
            fault_injector=fault,
        )
    raise AssertionError(("fault_seam_not_reached", seam))


def _prepare_sealed(root: Path) -> None:
    gc._config(root)
    gc._publish_sealed(root)
    _write_result(root, "prepare", "sealed")


def _prepare_complete_expired(root: Path) -> None:
    config = gd._config(root, completed=1, orphan=1, isolated=1)
    base, _, _, _ = gc._publish_sealed(root)
    result = gc._replay(config, str(base["locator_digest"]))
    if result.status not in {"completed", "exact_duplicate", "already_complete"}:
        raise AssertionError(result)
    gd._age_all(root / "finalization", 3600)
    _write_result(root, "prepare", "complete_expired")


def _prepare_isolated_expired(root: Path) -> None:
    _prepare_complete_expired(root)
    config = gd._config(root, completed=1, orphan=1, isolated=1)
    result = maintain_relaymem_slp_durable_finalization_retention(config=config)
    if result.status != "maintenance_complete":
        raise AssertionError(result)
    gd._age_all(root / "finalization", 3600)
    _write_result(root, "prepare", "isolated_expired")


def _recover(root: Path, name: str) -> None:
    config = gc._config(root)
    outcome = o1b.run(config)
    _write_result(root, name, outcome.status)
    if outcome.status not in {"completed", "no_eligible_work", "delegated", "busy"}:
        raise AssertionError(outcome)


def _replay_normal(root: Path, name: str) -> None:
    config = gc._config(root)
    result = gc._replay(config, _locator(root))
    _write_result(root, name, result.status)
    if result.status not in {"completed", "already_complete", "exact_duplicate", "replay_lock_busy"}:
        raise AssertionError(result)


def _retention_normal(root: Path, name: str) -> None:
    config = gd._config(root, completed=1, orphan=1, isolated=1)
    result = maintain_relaymem_slp_durable_finalization_retention(config=config)
    _write_result(root, name, result.status)
    if result.status not in {"maintenance_complete", "blocked"}:
        raise AssertionError(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "nonstream",
            "stream",
            "replay-crash",
            "retention-crash",
            "prepare-sealed",
            "prepare-complete-expired",
            "prepare-isolated-expired",
            "recover",
            "replay-normal",
            "retention-normal",
        ),
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--seam")
    parser.add_argument("--result-name", default="result")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    if args.action == "prepare-sealed":
        _prepare_sealed(root)
    elif args.action == "prepare-complete-expired":
        _prepare_complete_expired(root)
    elif args.action == "prepare-isolated-expired":
        _prepare_isolated_expired(root)
    elif args.action == "recover":
        _recover(root, args.result_name)
    elif args.action == "replay-normal":
        _replay_normal(root, args.result_name)
    elif args.action == "retention-normal":
        _retention_normal(root, args.result_name)
    else:
        if args.seam not in EXIT_CODES:
            raise AssertionError(("unknown_seam", args.seam))
        if args.action == "nonstream":
            _run_app(root, str(args.seam), stream=False)
        elif args.action == "stream":
            _run_app(root, str(args.seam), stream=True)
        elif args.action == "replay-crash":
            _run_replay(root, str(args.seam))
        else:
            _run_retention(root, str(args.seam))


if __name__ == "__main__":
    main()
