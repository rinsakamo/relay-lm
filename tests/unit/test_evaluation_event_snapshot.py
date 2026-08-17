from __future__ import annotations

import asyncio

from relaylm.evaluation import evaluate_event_snapshot_reuse


def test_event_snapshot_reuse_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_event_snapshot_reuse())

    assert result.scenario_id == "event_snapshot_reuse"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "event_journal",
        "filesystem_cache",
    }
    assert result.metrics == {
        "initial_disk_parse_count": 1,
        "post_append_disk_parse_count": 1,
        "post_external_change_disk_parse_count": 2,
        "post_corruption_disk_parse_count": 3,
    }
