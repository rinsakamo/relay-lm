from __future__ import annotations

import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    _request_body,
    parse_wire_output,
)
from relaylm.state import STATE_CLASS_DEFINITIONS


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# Eval\nBe grounded."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "紅茶が好き"},
            event_id="evt-now",
            timestamp="2026-08-21T00:00:00+00:00",
        ),
    )


def test_single_pass_request_does_not_require_provider_native_structured_output() -> None:
    body = _request_body(
        model="gemma",
        cognitive_input=_cognitive_input(),
        stream=False,
    )

    assert "response_format" not in body
    system = body["messages"][0]["content"]
    assert "RelayLM combined cognitive IR contract" in system
    assert "RelayLM, not the provider, owns parsing" in system


def test_single_pass_rejects_extra_top_level_ir_fields() -> None:
    with pytest.raises(ProviderProtocolError, match="exactly utterance"):
        parse_wire_output(
            {
                "utterance": "覚えておくね。",
                "state_candidates": [],
                "continuity_candidates": [],
                "metadata": {"unexpected": True},
            }
        )


def test_single_pass_rejects_extra_state_candidate_ir_fields() -> None:
    with pytest.raises(ProviderProtocolError, match=r"state_candidates\[0\].*exactly"):
        parse_wire_output(
            {
                "utterance": "覚えておくね。",
                "state_candidates": [
                    {
                        "state_class": "user.preference",
                        "key": "drink",
                        "op": "set",
                        "value": "tea",
                        "sources": ["evt-now"],
                        "confidence": 0.99,
                    }
                ],
                "continuity_candidates": [],
            }
        )
