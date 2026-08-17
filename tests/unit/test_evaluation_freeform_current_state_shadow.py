from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_freeform_current_state_shadow as evaluation_module
from relaylm.evaluation_freeform_current_state_shadow import (
    evaluate_freeform_current_state_shadow,
)


def test_freeform_current_state_shadow_component_uses_real_compiler_api() -> None:
    with patch.object(
        evaluation_module,
        "compile_cognitive_input",
        wraps=evaluation_module.compile_cognitive_input,
    ) as compiler:
        result = asyncio.run(evaluate_freeform_current_state_shadow())

    assert compiler.call_count == 7
    assert result.scenario_id == "freeform_current_state_shadow"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "explicit_current_conflict_suppressed",
        "explicit_current_match_retained",
        "now_form_conflict_suppressed",
        "prefixed_current_phrase_retained",
        "historical_freeform_retained",
        "omitted_key_freeform_retained",
        "boolean_freeform_not_expanded",
    }
    assert {check.boundary for check in result.checks} == {"context_compiler"}
    assert result.metrics == {
        "case_count": 7,
        "suppressed_case_count": 2,
        "retained_case_count": 5,
        "scalar_current_claim_count": 3,
    }
