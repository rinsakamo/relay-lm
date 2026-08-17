from __future__ import annotations

import asyncio

from relaylm.evaluation import (
    evaluate_boolean_state_memory_authority,
    evaluate_cjk_retrieval_relevance,
    evaluate_degree_state_memory_authority,
    evaluate_distinct_query_feature_relevance,
    evaluate_retrieval_aggregate_diagnostics,
)


def test_boolean_state_memory_authority_evaluation_checks_bounded_authority_cases() -> None:
    result = asyncio.run(evaluate_boolean_state_memory_authority())

    assert result.scenario_id == "boolean_state_memory_authority"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "opposite_boolean_suppressed",
        "current_boolean_retained",
        "unaddressed_history_retained",
    }
    assert {check.boundary for check in result.checks} == {"context_compiler"}
    assert result.metrics == {
        "input_memory_count": 3,
        "selected_memory_count": 2,
        "suppressed_memory_count": 1,
    }


def test_retrieval_aggregate_diagnostics_evaluation_checks_runtime_arithmetic() -> None:
    result = asyncio.run(evaluate_retrieval_aggregate_diagnostics())

    assert result.scenario_id == "retrieval_aggregate_diagnostics"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "enabled_layers_aggregated",
        "configured_character_budget_aggregated",
        "selected_character_usage_aggregated",
        "pressure_flags_aggregated",
        "zero_layer_aggregate_is_empty",
        "provider_called_once_per_turn",
    }
    assert {check.boundary for check in result.checks} == {
        "turn_diagnostics",
        "provider",
    }
    assert result.metrics["provider_calls"] == 2
    assert result.metrics["enabled_layer_count"] == 2
    assert result.metrics["configured_character_budget_total"] == 2000
    assert result.metrics["zero_enabled_layer_count"] == 0


def test_cjk_retrieval_relevance_evaluation_checks_shared_selector_semantics() -> None:
    result = asyncio.run(evaluate_cjk_retrieval_relevance())

    assert result.scenario_id == "cjk_retrieval_relevance"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "memory_cjk_match",
        "memory_unrelated_omitted",
        "memory_diagnostic_selection_equivalent",
        "event_cjk_match",
        "event_iterable_indexed_equivalent",
        "event_diagnostic_selection_equivalent",
        "latin_substring_protection",
    }
    assert {check.boundary for check in result.checks} == {
        "memory_retrieval",
        "event_retrieval",
    }
    assert result.metrics == {
        "memory_selected_count": 1,
        "event_selected_count": 1,
        "indexed_event_selected_count": 1,
    }


def test_distinct_query_feature_relevance_evaluation_checks_shared_set_semantics() -> None:
    result = asyncio.run(evaluate_distinct_query_feature_relevance())

    assert result.scenario_id == "distinct_query_feature_relevance"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "memory_distinct_overlap_wins",
        "event_distinct_overlap_wins",
        "event_iterable_indexed_equivalent",
        "index_candidate_scores_deduplicate_query_features",
    }
    assert {check.boundary for check in result.checks} == {
        "memory_retrieval",
        "event_retrieval",
        "event_discovery_index",
    }
    assert result.metrics == {
        "memory_selected_count": 1,
        "event_selected_count": 1,
        "indexed_event_selected_count": 1,
        "direct_index_candidate_count": 2,
    }


def test_degree_state_memory_authority_evaluation_checks_reserved_degree_cases() -> None:
    result = asyncio.run(evaluate_degree_state_memory_authority())

    assert result.scenario_id == "degree_state_memory_authority"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "stale_heading_degree_suppressed",
        "matching_heading_degree_retained",
        "matching_number_does_not_rescue_semantic_conflict",
        "inline_degree_is_same_line_scoped",
        "other_key_degree_not_borrowed",
        "unaddressed_degree_history_retained",
    }
    assert {check.boundary for check in result.checks} == {"context_compiler"}
    assert result.metrics == {
        "input_memory_count": 6,
        "selected_memory_count": 3,
        "suppressed_memory_count": 3,
    }
