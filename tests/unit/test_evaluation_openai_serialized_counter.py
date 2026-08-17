from __future__ import annotations

import asyncio

from relaylm.evaluation_openai_serialized_counter import (
    evaluate_openai_serialized_counter,
)


def test_openai_serialized_counter_component() -> None:
    result = asyncio.run(evaluate_openai_serialized_counter())

    assert result.scenario_id == "openai_serialized_counter"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "counter_matches_buffered_model_input_shape",
        "counter_implements_serialized_counter_protocol",
        "caller_supplied_count_is_preserved",
        "invalid_configuration_and_untyped_result_are_rejected",
    }
    assert {check.boundary for check in result.checks} == {"provider_adapter"}
    assert result.metrics == {
        "provider_generation_count": 1,
        "counting_callback_count": 2,
        "stream_field_exclusion_count": 1,
        "invalid_input_rejection_count": 3,
    }
