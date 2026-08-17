from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_continuity_active_task as evaluation_module
from relaylm.evaluation_continuity_active_task import (
    evaluate_continuity_active_task_retention,
)


def test_continuity_active_task_component_uses_real_compiler_apis() -> None:
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
        result = asyncio.run(evaluate_continuity_active_task_retention())

    assert compiler.call_count == 2
    assert diagnostic_compiler.call_count == 1
    assert result.scenario_id == "continuity_active_task_retention"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "active_task_survives_zero_recent_budget",
        "active_task_preserves_sources_role_and_actor_boundary",
        "initial_continuity_kinds_preserve_accepted_order",
        "active_task_diagnostics_preserve_four_layer_authority",
    }
    assert {check.boundary for check in result.checks} == {"context_compiler"}
    assert result.metrics == {
        "active_task_input_count": 1,
        "zero_budget_projected_count": 1,
        "ordered_continuity_count": 3,
        "diagnostic_layer_count": 4,
    }
