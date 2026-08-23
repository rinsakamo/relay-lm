from __future__ import annotations

import asyncio

from relaylm.evaluation_persistence import evaluate_persistence_integrity


def test_persistence_integrity_evaluation_round_trips_and_fails_closed() -> None:
    result = asyncio.run(evaluate_persistence_integrity())

    assert result.scenario_id == "persistence_integrity"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "event_journal",
        "canonical_state",
        "filesystem",
    }
    assert result.metrics == {
        "round_trip_event_count": 1,
        "round_trip_state_count": 1,
        "malformed_failure_count": 2,
    }
