from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_degree_state_memory_authority as evaluation_module
from relaylm.evaluation_degree_state_memory_authority import (
    evaluate_degree_state_memory_authority,
)


def test_degree_state_memory_authority_component_uses_real_context_compiler() -> None:
    with patch.object(
        evaluation_module,
        "compile_cognitive_input",
        wraps=evaluation_module.compile_cognitive_input,
    ) as compiler:
        result = asyncio.run(evaluate_degree_state_memory_authority())

    assert compiler.call_count == 7
    assert result.scenario_id == "degree_state_memory_authority"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "stale_explicit_degree_suppressed",
        "matching_explicit_degree_retained",
        "missing_degree_not_inferred_as_conflict",
        "matching_number_does_not_rescue_semantic_conflict",
        "inline_same_line_degree_is_authoritative",
        "inline_key_does_not_borrow_other_key_degree",
        "unaddressed_historical_degree_prose_retained",
    }
    assert {check.boundary for check in result.checks} == {"context_compiler"}
    assert result.metrics == {
        "case_count": 7,
        "retained_case_count": 4,
        "suppressed_case_count": 3,
    }
