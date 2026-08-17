from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_continuity_turn as evaluation_module
from relaylm.evaluation_continuity_turn import evaluate_continuity_turn


def test_continuity_turn_component_uses_real_turn_apis() -> None:
    with (
        patch.object(
            evaluation_module,
            "run_user_turn",
            wraps=evaluation_module.run_user_turn,
        ) as buffered,
        patch.object(
            evaluation_module,
            "run_user_turn_streaming",
            wraps=evaluation_module.run_user_turn_streaming,
        ) as streamed,
    ):
        result = asyncio.run(evaluate_continuity_turn())

    assert buffered.call_count == 3
    assert streamed.call_count == 1
    assert result.scenario_id == "continuity_turn"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "buffered_single_generation_commits_continuity",
        "streaming_commits_only_after_completion",
        "empty_candidates_advance_configured_runtime",
        "missing_runtime_rejects_before_assistant_commit",
    }
    assert {check.boundary for check in result.checks} == {
        "turn_runtime",
        "provider",
    }
    assert result.metrics == {
        "buffered_provider_calls": 1,
        "stream_provider_calls": 1,
        "empty_provider_calls": 1,
        "missing_runtime_provider_calls": 1,
        "stream_delta_count": 2,
    }
