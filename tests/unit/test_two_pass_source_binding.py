from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.state import STATE_CLASS_DEFINITIONS


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "最近コーヒーを飲んでる"},
            event_id="evt-now",
            timestamp="2026-08-23T00:00:00+00:00",
        ),
    )


def _empty_turn_interpretation() -> dict[str, list[str]]:
    return {
        "user_meaning": [],
        "change_signals": [],
        "self_meaning": [],
        "assistant_effects": [],
        "unresolved": [],
        "continuity_signals": [],
    }


@pytest.mark.parametrize(
    ("collection", "candidate"),
    (
        (
            "state_candidates",
            {
                "state_class": "user.preference",
                "key": "coffee",
                "op": "set",
                "value": "likes",
                "sources": ["evt-now", "evt-hidden"],
            },
        ),
        (
            "continuity_candidates",
            {
                "kind": "active_task",
                "key": "coffee_followup",
                "op": "set",
                "value": "ask about coffee",
                "sources": ["evt-now", "evt-hidden"],
                "epistemic_role": "user_assertion",
            },
        ),
    ),
)
def test_two_pass_extraction_rejects_candidate_sources_absent_from_originating_input(
    collection: str,
    candidate: dict[str, object],
) -> None:
    wire: dict[str, object] = {
        "turn_interpretation": _empty_turn_interpretation(),
        "state_candidates": [],
        "continuity_candidates": [],
    }
    wire[collection] = [candidate]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(wire, ensure_ascii=False)}}
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response="了解。",
                )
            )

    with pytest.raises(ProviderProtocolError, match="absent from CognitiveInput"):
        asyncio.run(run())
