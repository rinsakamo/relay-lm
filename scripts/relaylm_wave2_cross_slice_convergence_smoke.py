#!/usr/bin/env python3
"""Permanent W2-INT functional convergence smoke."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import relaylm_i1gc_durable_finalization_replay_smoke as gc
import relaylm.relaymem_slp_scheduler_queue_lane as queue_lane_module
from _relaylm_o0_local_worker_support import build_config, prepare_scoped_store
from relaylm.relaymem_slp_durable_finalization_isolation import (
    ISOLATION_MAX_BYTES,
    build_isolation_marker,
    isolation_filename,
    parse_isolation_filename,
    publish_relaymem_slp_durable_finalization_isolation,
)
from relaylm.relaymem_slp_scheduler_contract import SchedulerGates, aggregate_scheduler_round
from relaylm.relaymem_slp_scheduler_queue_lane import run_relaymem_slp_scheduler_queue_lane_once
from relaylm.relaymem_slp_scheduler_replay_lane import run_relaymem_slp_scheduler_replay_lane_once


def require(value: bool, detail: object) -> None:
    if not value:
        raise AssertionError(detail)


def gates(mode: str = "apply") -> SchedulerGates:
    triple = {"dry_run": (True, True, False), "apply": (True, False, True)}[mode]
    return SchedulerGates(
        enabled=triple[0],
        dry_run_only=triple[1],
        apply_enabled=triple[2],
        replay_lane_enabled=True,
        queue_lane_enabled=True,
    )


def marker(locator: str) -> dict[str, object]:
    return build_isolation_marker(
        locator_digest=locator,
        classification="orphaned_sealed_record",
        reason_id="wave2_integration_test",
        observed_component_flags={
            "base_present": True,
            "segment_present": True,
            "seal_present": True,
            "completion_present": False,
            "corrupt_observed": False,
            "unsupported_observed": False,
        },
    )


def test_authority_and_isolation_race() -> None:
    replay_source = (ROOT / "relaylm/relaymem_slp_scheduler_replay_lane.py").read_text("utf-8")
    fence_source = (ROOT / "relaylm/relaymem_slp_durable_finalization_fence.py").read_text("utf-8")
    require("import importlib" not in replay_source, "optional isolation import remains")
    require("_isolation_module" not in replay_source, "isolation fallback remains")
    require("parse_isolation_filename" in replay_source, "authoritative isolation parser not reused")
    require("isolation_filename(locator)" in fence_source, "fence copied isolation filename")
    require("_acquire_fence" in fence_source, "shared I1-GC fence missing")
    require(ISOLATION_MAX_BYTES > 0, ISOLATION_MAX_BYTES)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        published = publish_relaymem_slp_durable_finalization_isolation(
            str(root / "finalization"), marker(locator)
        )
        require(published.status == "published_new", published)
        outcome = run_relaymem_slp_scheduler_replay_lane_once(
            config=config, gates=gates("dry_run")
        )
        require(outcome.status == "no_eligible_work", outcome)
        require(not outcome.delegation_attempted, outcome)
        require(parse_isolation_filename(isolation_filename(locator)) == locator, locator)
        direct = gc._replay(config, locator)
        require(direct.status not in {"completed", "exact_duplicate"}, direct)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        injected = False

        def isolate(stage: str) -> None:
            nonlocal injected
            if stage == "after_selection_before_reread" and not injected:
                injected = True
                result = publish_relaymem_slp_durable_finalization_isolation(
                    str(root / "finalization"), marker(locator)
                )
                require(result.status == "published_new", result)

        outcome = run_relaymem_slp_scheduler_replay_lane_once(
            config=config, gates=gates("dry_run"), fault_injector=isolate
        )
        require(outcome.status in {"candidate_changed", "isolated"}, outcome)
        require(outcome.canonical_reread_performed and not outcome.delegation_attempted, outcome)


def test_same_round_independent_discovery() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        queue_root = root / "queue"
        source_root = root / "source"
        memory_root = root / "memory"
        finalization_root = root / "finalization"
        for path in (queue_root, source_root, memory_root, finalization_root):
            path.mkdir(parents=True, exist_ok=True)
        prepare_scoped_store(memory_root)
        base, seal, _, _ = gc._publish_sealed(root)
        namespace = str(seal["durable_job"]["namespace"])
        config = build_config(queue_root, source_root, memory_root, namespace, mode="apply")
        config = config.model_copy(
            update={
                "relaymem_slp_durable_finalization_root": str(finalization_root.resolve()),
                "relaymem_slp_durable_finalization_enabled": True,
                "relaymem_slp_durable_finalization_dry_run_only": False,
                "relaymem_slp_durable_finalization_apply_enabled": True,
                "relaymem_slp_runtime_enqueue_enabled": True,
                "relaymem_slp_runtime_enqueue_dry_run_only": False,
                "relaymem_slp_runtime_enqueue_apply_enabled": True,
            }
        )
        replay = run_relaymem_slp_scheduler_replay_lane_once(config=config, gates=gates("apply"))
        require(replay.status == "completed", replay)
        require(replay.delegation_completed, replay)
        signature = inspect.signature(run_relaymem_slp_scheduler_queue_lane_once)
        require("replay_lane" not in signature.parameters, signature)
        queue = run_relaymem_slp_scheduler_queue_lane_once(config=config, gates=gates("dry_run"))
        require(queue.status == "dry_run_ready", queue)
        require(queue.delegation_completed, queue)
        round_result = aggregate_scheduler_round(
            gates=gates("dry_run"),
            invocation_order=("replay", "queue"),
            replay_lane=replay,
            queue_lane=queue,
        )
        require(round_result.work_units_attempted <= 2, round_result)
        projection = json.dumps(round_result.projection(), sort_keys=True)
        private = [
            str(base["locator_digest"]),
            "slp-job-v0:",
            "slp-dispatch-v0:",
            gc.gb.USER_CANARY,
            gc.gb.ASSISTANT_CANARY,
            namespace,
            str(queue_root),
            str(source_root),
            str(finalization_root),
        ]
        rendered = repr(replay) + repr(queue) + repr(round_result) + projection
        for token in private:
            require(token not in rendered, (token, rendered))


def test_o1c_mapping_and_non_goals() -> None:
    fake = type(
        "Fake",
        (),
        {
            "status": "source_retryable",
            "claim_performed": True,
            "worker_invoked": False,
            "queue_transition_performed": False,
            "terminal": False,
            "cleanup_required": False,
            "retryable": True,
            "worker_status": None,
            "reason_ids": (),
        },
    )()
    private = queue_lane_module.QueueLanePrivateState()
    mapped = queue_lane_module._map_c2_result(fake, private)
    require(mapped.status == "failed", mapped)
    scheduler_source = (ROOT / "relaylm/relaymem_slp_scheduler_contract.py").read_text("utf-8")
    for forbidden in ("os.", "time.sleep(", "while True", "pathlib", "execute_one_queued"):
        require(forbidden not in scheduler_source, forbidden)
    queue_source = (ROOT / "relaylm/relaymem_slp_scheduler_queue_lane.py").read_text("utf-8")
    o0_source = (ROOT / "relaylm/local_worker_once.py").read_text("utf-8")
    require("relaymem_slp_queue_candidate" in queue_source, "O1C shared helper missing")
    require("relaymem_slp_queue_candidate" in o0_source, "O0 shared helper missing")


def main() -> int:
    test_authority_and_isolation_race()
    test_same_round_independent_discovery()
    test_o1c_mapping_and_non_goals()
    print("Wave 2 cross-slice convergence smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
