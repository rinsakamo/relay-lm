from __future__ import annotations

import asyncio

from relaylm.evaluation import evaluate_event_evidence_cognitive_projection


def test_event_evidence_cognitive_projection_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_event_evidence_cognitive_projection())

    assert result.scenario_id == "event_evidence_cognitive_projection"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "context_compiler",
        "provider_serialization",
        "event_provenance",
    }
    assert result.metrics == {
        "projected_evidence_count": 2,
        "serialized_evidence_count": 2,
        "current_input_duplicate_count": 0,
        "working_context_count": 0,
        "memory_count": 0,
    }
