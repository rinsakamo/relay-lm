from __future__ import annotations

import json

import pytest

from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_two_pass import _parse_extraction_completion


def _envelope_with_continuity_signals(values: list[object]) -> dict[str, object]:
    wire = {
        "turn_interpretation": {
            "user_meaning": [],
            "change_signals": [],
            "self_meaning": [],
            "assistant_effects": [],
            "unresolved": [],
            "continuity_signals": values,
        },
        "state_candidates": [],
        "continuity_candidates": [],
    }
    return {
        "choices": [
            {
                "message": {"content": json.dumps(wire, ensure_ascii=False)},
                "finish_reason": "stop",
            }
        ]
    }


def test_extraction_treats_blank_only_interpretation_items_as_absent() -> None:
    output = _parse_extraction_completion(
        _envelope_with_continuity_signals(["", "   "])
    )

    assert output.state_candidates == ()
    assert output.continuity_candidates == ()


def test_extraction_still_rejects_non_string_interpretation_items() -> None:
    with pytest.raises(
        ProviderProtocolError,
        match="turn_interpretation.continuity_signals must contain strings",
    ):
        _parse_extraction_completion(_envelope_with_continuity_signals([123]))
