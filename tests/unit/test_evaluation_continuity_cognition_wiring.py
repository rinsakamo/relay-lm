from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_continuity_cognition_wiring as evaluation_module
from relaylm.evaluation_continuity_cognition_wiring import (
    evaluate_continuity_cognition_wiring,
)


def test_continuity_cognition_wiring_component_uses_real_turn_apis() -> None:
    with (
        patch.object(
            evaluation_module,
            "run_user_turn",
            wraps=evaluation_module.run_user_turn,
        ) as buffered,
        patch.object(
            evaluation_module,
            "run_user_turn_with_retrieval_diagnostics",
            wraps=evaluation_module.run_user_turn_with_retrieval_diagnostics,
        ) as buffered_diagnostics,
        patch.object(
            evaluation_module,
            "run_user_turn_streaming",
            wraps=evaluation_module.run_user_turn_streaming,
        ) as streamed,
        patch.object(
            evaluation_module,
            "run_user_turn_streaming_with_retrieval_diagnostics",
            wraps=evaluation_module.run_user_turn_streaming_with_retrieval_diagnostics,
        ) as streamed_diagnostics,
    ):
        result = asyncio.run(evaluate_continuity_cognition_wiring())

    assert buffered.call_count == 1
    assert buffered_diagnostics.call_count == 1
    assert streamed.call_count == 1
    assert streamed_diagnostics.call_count == 1
    assert result.scenario_id == "continuity_cognition_wiring"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "buffered_provider_sees_pre_generation_continuity",
        "buffered_diagnostics_uses_same_continuity_snapshot",
        "streaming_keeps_snapshot_stable_until_completion",
        "streaming_diagnostics_uses_same_continuity_snapshot",
    }
    assert {check.boundary for check in result.checks} == {"turn_runtime"}
    assert result.metrics == {
        "ordinary_turn_variant_count": 4,
        "buffered_provider_call_count": 2,
        "stream_provider_call_count": 2,
        "projected_continuity_observation_count": 4,
        "post_generation_revision_count": 4,
    }
