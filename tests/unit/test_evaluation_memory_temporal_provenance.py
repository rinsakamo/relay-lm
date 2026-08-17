from __future__ import annotations

import asyncio

from relaylm.evaluation_memory_temporal_provenance import (
    evaluate_memory_temporal_provenance,
)


def test_memory_temporal_provenance_component() -> None:
    result = asyncio.run(evaluate_memory_temporal_provenance())

    assert result.scenario_id == "memory_temporal_provenance"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "temporal_scope_is_closed_and_unknown_is_first_class",
        "provenance_sources_are_typed_event_or_state_only",
        "classified_authority_requires_typed_provenance",
        "provenance_requires_stable_memory_and_derivation_identity",
        "unknown_scope_may_preserve_provenance_without_promotion",
        "invalid_and_untyped_provenance_inputs_are_rejected",
    }
    assert {check.boundary for check in result.checks} == {"memory_provenance"}
    assert result.metrics == {
        "temporal_scope_count": 3,
        "provenance_source_kind_count": 2,
        "classified_scope_count": 2,
        "valid_source_count": 2,
        "invalid_input_rejection_count": 10,
    }
