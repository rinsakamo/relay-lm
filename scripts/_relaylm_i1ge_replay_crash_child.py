#!/usr/bin/env python3
"""Replay-only I1-GE child using public durable-finalization replay seams."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from pathlib import Path
import sys
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import _relaylm_i1ge_crash_child as base  # noqa: E402
import relaylm._relaymem_slp_durable_finalization_replay_impl as replay_impl  # noqa: E402
import relaylm.relaymem_slp_durable_finalization_replay as replay_public  # noqa: E402
import relaylm_i1gc_durable_finalization_replay_smoke as gc  # noqa: E402

EXIT_CODES = base.EXIT_CODES


def _run_replay(root: Path, seam: str) -> None:
    config = gc._config(root)
    locator = base._locator(root)
    fault_stage = {
        "after_record_fence_acquisition_before_canonical_reread": "after_lock_before_reread",
        "after_exact_c1_5_reread_before_b2": "after_source_commit_before_queue",
        "after_downstream_verification_before_completion_marker": "after_queue_commit_before_completion",
        "after_completion_reread_before_caller_return": "after_completion_publish_before_return",
    }.get(seam)

    def fault(stage: str) -> None:
        if stage == fault_stage:
            base._crash(seam)

    with ExitStack() as stack:
        if seam == "after_exact_finalized_turn_reconstruction":
            original = replay_public._reconstruct_source

            def reconstructed(*args: Any, **kwargs: Any):
                result = original(*args, **kwargs)
                if result[0] is not None:
                    base._crash(seam)
                return result

            stack.enter_context(
                patch.object(replay_public, "_reconstruct_source", new=reconstructed)
            )

        if seam in {"during_c1_5_publication", "after_c1_5_publication_before_canonical_reread"}:
            original = replay_impl.RelayMEMSLPDurableProtectedSourceStore.persist

            def source_persist(self: Any, *args: Any, **kwargs: Any):
                if seam == "during_c1_5_publication":
                    base._crash(seam)
                result = original(self, *args, **kwargs)
                base._crash(seam)
                return result

            stack.enter_context(
                patch.object(
                    replay_impl.RelayMEMSLPDurableProtectedSourceStore,
                    "persist",
                    new=source_persist,
                )
            )

        if seam in {"during_b2_publication", "after_b2_publication_before_canonical_reread"}:
            original = replay_public.apply_relaymem_slp_runtime_enqueue

            def queue_apply(*args: Any, **kwargs: Any):
                if seam == "during_b2_publication":
                    base._crash(seam)
                result = original(*args, **kwargs)
                base._crash(seam)
                return result

            stack.enter_context(
                patch.object(
                    replay_public,
                    "apply_relaymem_slp_runtime_enqueue",
                    new=queue_apply,
                )
            )

        if seam == "after_exact_b2_reread_before_downstream_verification":
            original = replay_impl._inspect_queue
            calls = 0

            def inspect_queue(*args: Any, **kwargs: Any):
                nonlocal calls
                result = original(*args, **kwargs)
                calls += 1
                if calls >= 2:
                    base._crash(seam)
                return result

            stack.enter_context(patch.object(replay_impl, "_inspect_queue", new=inspect_queue))

        if seam in {
            "during_completion_marker_publication",
            "after_completion_marker_publication_before_canonical_reread",
        }:
            original = replay_public._rename_noreplace

            def completion_rename(
                root_fd: int,
                temporary: str,
                final: str,
            ) -> str:
                if seam == "during_completion_marker_publication":
                    base._crash(seam)
                result = original(root_fd, temporary, final)
                if result == "published":
                    base._crash(seam)
                return result

            stack.enter_context(
                patch.object(replay_public, "_rename_noreplace", new=completion_rename)
            )

        gc._replay(config, locator, fault=fault if fault_stage else None)
    raise AssertionError(("fault_seam_not_reached", seam))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("--root", required=True)
    parser.add_argument("--seam")
    parser.add_argument("--result-name", default="result")
    args = parser.parse_args()

    if args.action != "replay-crash":
        base.main()
        return
    if args.seam not in EXIT_CODES:
        raise AssertionError(("unknown_seam", args.seam))
    _run_replay(Path(args.root).resolve(), str(args.seam))


if __name__ == "__main__":
    main()
