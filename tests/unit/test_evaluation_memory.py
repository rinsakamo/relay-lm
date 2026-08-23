from __future__ import annotations

import asyncio

from relaylm.evaluation_memory import (
    evaluate_memory_cognitive_projection,
    evaluate_memory_heading_retrieval,
    evaluate_ordinary_turn_memory_retrieval,
    evaluate_state_memory_authority_filter,
)


def test_memory_heading_retrieval_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_memory_heading_retrieval())

    assert result.scenario_id == "memory_heading_retrieval"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "memory_retrieval",
        "memory_budget",
    }
    assert result.metrics == {
        "relevant_selected_count": 1,
        "irrelevant_selected_count": 0,
        "oversized_selected_count": 1,
    }


def test_memory_cognitive_projection_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_memory_cognitive_projection())

    assert result.scenario_id == "memory_cognitive_projection"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "context_compiler",
        "provider_serialization",
        "event_provenance",
    }
    assert result.metrics == {
        "projected_memory_count": 1,
        "working_context_count": 0,
        "memory_location_source_leak_count": 0,
    }


def test_ordinary_turn_memory_retrieval_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_ordinary_turn_memory_retrieval())

    assert result.scenario_id == "ordinary_turn_memory_retrieval"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "ordinary_turn",
        "memory_retrieval",
        "persistence",
    }
    assert result.metrics == {
        "successful_provider_calls": 1,
        "selected_memory_count": 1,
        "default_memory_count": 0,
        "failed_retrieval_provider_calls": 0,
        "failed_retrieval_event_count": 1,
    }


def test_state_memory_authority_filter_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_state_memory_authority_filter())

    assert result.scenario_id == "state_memory_authority_filter"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "context_authority",
        "canonical_state",
    }
    assert result.metrics == {
        "stale_memory_count": 0,
        "compatible_memory_count": 1,
        "capped_state_memory_count": 0,
        "historical_memory_count": 1,
        "substring_conflict_memory_count": 0,
        "comparative_memory_count": 1,
        "preserved_tea_state_count": 1,
    }
