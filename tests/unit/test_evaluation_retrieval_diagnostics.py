from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_retrieval_diagnostics as evaluation_module
from relaylm.evaluation_retrieval_diagnostics import evaluate_retrieval_stage_diagnostics


def test_retrieval_stage_diagnostics_component_uses_real_selector_contracts() -> None:
    with (
        patch.object(
            evaluation_module,
            "select_memory_chunks",
            wraps=evaluation_module.select_memory_chunks,
        ) as plain_memory,
        patch.object(
            evaluation_module,
            "select_memory_chunks_with_diagnostics",
            wraps=evaluation_module.select_memory_chunks_with_diagnostics,
        ) as diagnostic_memory,
        patch.object(
            evaluation_module,
            "select_event_evidence",
            wraps=evaluation_module.select_event_evidence,
        ) as plain_events,
        patch.object(
            evaluation_module,
            "select_event_evidence_with_diagnostics",
            wraps=evaluation_module.select_event_evidence_with_diagnostics,
        ) as diagnostic_events,
    ):
        result = asyncio.run(evaluate_retrieval_stage_diagnostics())

    assert plain_memory.call_count == 1
    assert diagnostic_memory.call_count == 2
    assert plain_events.call_count == 1
    assert diagnostic_events.call_count == 2

    assert result.scenario_id == "retrieval_stage_diagnostics"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "memory_retrieval",
        "event_retrieval",
        "diagnostics",
    }
    assert result.metrics == {
        "memory_positive_candidate_count": 4,
        "memory_selected_count": 2,
        "memory_skipped_character_budget_count": 1,
        "memory_unadmitted_chunk_limit_count": 1,
        "event_input_event_count": 8,
        "event_excluded_event_count": 1,
        "event_ineligible_event_count": 2,
        "event_positive_candidate_count": 4,
        "event_selected_count": 2,
        "event_skipped_character_budget_count": 1,
        "event_unadmitted_event_limit_count": 1,
    }
    assert all("score" not in metric_name for metric_name in result.metrics)
