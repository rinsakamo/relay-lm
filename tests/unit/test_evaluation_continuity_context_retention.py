from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_continuity_context_retention as evaluation_module
from relaylm.evaluation_continuity_context_retention import (
    evaluate_continuity_context_retention,
)


def test_continuity_context_retention_component_uses_real_compiler_apis() -> None:
    with (
        patch.object(
            evaluation_module,
            "compile_cognitive_input",
            wraps=evaluation_module.compile_cognitive_input,
        ) as compiler,
        patch.object(
            evaluation_module,
            "compile_cognitive_input_with_diagnostics",
            wraps=evaluation_module.compile_cognitive_input_with_diagnostics,
        ) as diagnostic_compiler,
    ):
        result = asyncio.run(evaluate_continuity_context_retention())

    assert compiler.call_count == 3
    assert diagnostic_compiler.call_count == 1
    assert result.scenario_id == "continuity_context_retention"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "referent_unresolved_survive_zero_recent_budget",
        "continuity_preserves_sources_roles_and_actor_boundary",
        "continuity_precedes_recent_working_context_without_reordering",
        "diagnostic_projection_preserves_four_layer_authority",
        "empty_continuity_preserves_empty_zero_budget_context",
    }
    assert {check.boundary for check in result.checks} == {"context_compiler"}
    assert result.metrics == {
        "accepted_continuity_input_count": 2,
        "zero_budget_projected_count": 2,
        "recent_working_context_count": 2,
        "diagnostic_layer_count": 4,
        "empty_projection_count": 0,
    }
