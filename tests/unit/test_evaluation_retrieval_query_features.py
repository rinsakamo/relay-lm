from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_retrieval_query_features as evaluation_module
from relaylm.evaluation_retrieval_query_features import (
    evaluate_retrieval_query_features,
)


def test_retrieval_query_feature_component_uses_real_retrieval_apis() -> None:
    with (
        patch.object(
            evaluation_module,
            "select_memory_chunks",
            wraps=evaluation_module.select_memory_chunks,
        ) as memory_selector,
        patch.object(
            evaluation_module,
            "select_event_evidence",
            wraps=evaluation_module.select_event_evidence,
        ) as event_selector,
    ):
        result = asyncio.run(evaluate_retrieval_query_features())

    assert memory_selector.call_count == 1
    assert event_selector.call_count == 2
    assert result.scenario_id == "retrieval_query_features"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "memory_repetition_does_not_outweigh_distinct_overlap",
        "event_repetition_does_not_outweigh_distinct_overlap",
        "event_indexed_iterable_selection_converges",
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
        "indexed_candidate_count": 2,
        "indexed_max_score": 2,
    }
