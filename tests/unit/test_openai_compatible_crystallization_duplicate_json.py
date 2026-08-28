from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.crystallization import CrystallizationInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_crystallization import (
    OpenAICompatibleCrystallizer,
    parse_crystallization_chat_completion,
)
from relaylm.state import CanonicalState


def _input() -> CrystallizationInput:
    return CrystallizationInput(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        events=(
            Event.create(
                type="message",
                actor="user",
                payload={"content": "紅茶が好き"},
                event_id="evt-1",
                timestamp="2026-08-28T00:00:00+00:00",
            ),
        ),
    )


def _wire_text() -> str:
    return json.dumps(
        {
            "memory_units": [
                {
                    "heading": "Preferences",
                    "content": "The user likes tea.",
                    "temporal_scope": "unknown",
                    "sources": [],
                }
            ],
            "state_candidates": [],
        }
    )


def test_crystallizer_rejects_duplicate_members_in_provider_envelope() -> None:
    valid_choice = {"message": {"content": _wire_text()}}
    body = (
        '{"choices":[],"choices":['
        + json.dumps(valid_choice, separators=(",", ":"))
        + "]}"
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleCrystallizer(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            await provider.generate(_input())

    with pytest.raises(ProviderProtocolError, match="duplicate"):
        asyncio.run(run())


def test_crystallization_wire_rejects_duplicate_members_before_materialization() -> None:
    valid_unit = json.dumps(
        {
            "heading": "Preferences",
            "content": "The user likes tea.",
            "temporal_scope": "unknown",
            "sources": [],
        },
        separators=(",", ":"),
    )
    content = (
        '{"memory_units":[],"memory_units":['
        + valid_unit
        + '],"state_candidates":[]}'
    )
    envelope = {"choices": [{"message": {"content": content}}]}

    with pytest.raises(ProviderProtocolError, match="duplicate"):
        parse_crystallization_chat_completion(
            envelope,
            allowed_source_ids=frozenset(),
        )
