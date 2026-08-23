from __future__ import annotations

import asyncio

from relaylm.evaluation_event_evidence import evaluate_ordinary_turn_event_retrieval


def test_ordinary_turn_event_retrieval_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_ordinary_turn_event_retrieval())

    assert result.scenario_id == "ordinary_turn_event_retrieval"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "ordinary_turn",
        "event_retrieval",
        "event_provenance",
        "event_journal",
    }
    assert result.metrics == {
        "provider_calls": 1,
        "retrieved_event_count": 1,
        "current_duplicate_count": 0,
        "explicit_iter_events_calls": 2,
        "default_event_evidence_count": 0,
    }
