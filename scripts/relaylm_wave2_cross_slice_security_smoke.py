#!/usr/bin/env python3
"""Cross-slice security and leakage smoke for W2-INT."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import relaylm_i1gc_durable_finalization_replay_smoke as gc
from relaylm.relaymem_slp_durable_finalization_isolation import (
    build_isolation_marker,
    is_isolation_temp_filename,
    isolation_filename,
    parse_isolation_filename,
    publish_relaymem_slp_durable_finalization_isolation,
)
from relaylm.relaymem_slp_scheduler_contract import SchedulerGates
from relaylm.relaymem_slp_scheduler_replay_lane import (
    build_relaymem_slp_scheduler_replay_lane_node_result,
    run_relaymem_slp_scheduler_replay_lane_once,
)


def require(value: bool, detail: object) -> None:
    if not value:
        raise AssertionError(detail)


def gates() -> SchedulerGates:
    return SchedulerGates(
        enabled=True,
        dry_run_only=True,
        apply_enabled=False,
        replay_lane_enabled=True,
        queue_lane_enabled=True,
    )


def main() -> int:
    require(parse_isolation_filename(None) is None, "non-string isolation name accepted")
    require(
        parse_isolation_filename("../durable-finalization-v0-x.segment-isolation.json") is None,
        "traversal accepted",
    )
    require(
        not is_isolation_temp_filename(".durable-finalization-isolation-../x.tmp"),
        "temp traversal accepted",
    )
    require(
        is_isolation_temp_filename(
            ".durable-finalization-isolation-" + "a" * 32 + ".tmp"
        ),
        "valid temp rejected",
    )

    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = gc._config(root, dry_run=True)
        base, _, _, _ = gc._publish_sealed(root)
        locator = str(base["locator_digest"])
        marker = build_isolation_marker(
            locator_digest=locator,
            classification="orphaned_sealed_record",
            reason_id="wave2_security_test",
            observed_component_flags={
                "base_present": True,
                "segment_present": True,
                "seal_present": True,
                "completion_present": False,
                "corrupt_observed": False,
                "unsupported_observed": False,
            },
        )
        result = publish_relaymem_slp_durable_finalization_isolation(
            str(root / "finalization"), marker
        )
        require(result.status == "published_new", result)
        outcome = run_relaymem_slp_scheduler_replay_lane_once(config=config, gates=gates())
        node = build_relaymem_slp_scheduler_replay_lane_node_result(outcome)
        rendered = repr(result) + repr(outcome) + repr(node)
        if hasattr(node, "to_log_dict"):
            rendered += json.dumps(node.to_log_dict(), sort_keys=True, default=str)
        for token in (
            locator,
            isolation_filename(locator),
            gc.gb.USER_CANARY,
            gc.gb.ASSISTANT_CANARY,
            gc.gb.NAMESPACE_CANARY,
            str(root),
            "slp-job-v0:",
            "slp-dispatch-v0:",
        ):
            require(token not in rendered, (token, rendered))

        isolation_path = root / "finalization" / isolation_filename(locator)
        isolation_path.unlink()
        outside = root / "outside"
        outside.write_text("canary", encoding="utf-8")
        isolation_path.symlink_to(outside)
        unsafe = run_relaymem_slp_scheduler_replay_lane_once(config=config, gates=gates())
        require(unsafe.status == "unsafe_state", unsafe)
        require(not unsafe.delegation_attempted, unsafe)

    print("Wave 2 cross-slice security smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
