from __future__ import annotations

import asyncio
import json

import httpx
import pytest

import relaylm.providers as providers
from relaylm.providers.openai_compatible_crystallization import (
    STATE_CANDIDATE_WIRE_SCHEMA,
)
from relaylm.crystallization import CrystallizationInput, CrystallizationOutput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.state import CanonicalState, STATE_CLASS_DEFINITIONS, StateRecord


def _provider_type():
    provider_type = getattr(providers, "OpenAICompatibleCrystallizer", None)
    assert provider_type is not None, "CRY1 OpenAI-compatible crystallizer is not implemented"
    return provider_type


def _crystallization_input() -> CrystallizationInput:
    return CrystallizationInput(
        identity=Identity("# ReLM\nBe kind and grounded."),
        state=CanonicalState(
            states=(
                StateRecord(
                    state_id="state-name",
                    state_class="user.identity",
                    key="name",
                    value="Yuto",
                    sources=("evt-user-name",),
                    valid_from="2026-08-19T00:00:00+00:00",
                ),
            )
        ),
        events=(
            Event.create(
                type="message",
                actor="user",
                payload={"content": "ユウじゃなくてユウトだよ"},
                event_id="evt-user-name",
                timestamp="2026-08-19T00:00:00+00:00",
            ),
            Event.create(
                type="message",
                actor="assistant",
                payload={"content": "ユウトだね。覚えたよ。"},
                event_id="evt-assistant-name",
                timestamp="2026-08-19T00:00:01+00:00",
            ),
        ),
        prior_memory=(
            "# Memory\n\n## Name\n\n"
            "The user was previously recorded as Yuu.\n"
        ),
    )


def _all_capabilities() -> OpenAICompatibleDecodingCapabilities:
    return OpenAICompatibleDecodingCapabilities(
        supported_controls=frozenset({"temperature", "top_p", "seed"})
    )


def test_state_candidate_wire_schema_pairs_operation_and_value() -> None:
    schema = STATE_CANDIDATE_WIRE_SCHEMA

    branches = schema["anyOf"]
    assert len(branches) == 2

    by_op = {
        branch["properties"]["op"]["enum"][0]: branch
        for branch in branches
    }
    assert set(by_op) == {"set", "remove"}

    expected_required = ["state_class", "key", "op", "value", "sources"]
    for branch in branches:
        assert branch["type"] == "object"
        assert branch["additionalProperties"] is False
        assert branch["required"] == expected_required
        assert branch["properties"]["state_class"] == {
            "type": "string",
            "enum": list(STATE_CLASS_DEFINITIONS),
        }
        assert branch["properties"]["key"] == {"type": "string", "minLength": 1}
        assert branch["properties"]["sources"] == {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "minLength": 1},
        }

    set_value = by_op["set"]["properties"]["value"]
    assert by_op["set"]["properties"]["op"] == {"type": "string", "enum": ["set"]}
    assert by_op["remove"]["properties"]["op"] == {
        "type": "string",
        "enum": ["remove"],
    }
    assert set_value == {
        "anyOf": [
            {"type": "string"},
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["semantic", "degree_hint"],
                "properties": {
                    "semantic": {"type": "string", "minLength": 1},
                    "degree_hint": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
            },
        ]
    }
    assert by_op["remove"]["properties"]["value"] == {"type": "null"}


def test_provider_makes_one_nonstreaming_strict_request_and_returns_crystallization_output() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        wire = {
            "memory_markdown": (
                "# Memory\n\n## User identity\n\n"
                "The user's current name is Yuto; an earlier Yuu form was corrected.\n"
            ),
            "state_candidates": [
                {
                    "state_class": "user.identity",
                    "key": "name",
                    "op": "set",
                    "value": "Yuto",
                    "sources": ["evt-user-name"],
                }
            ],
        }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(wire, ensure_ascii=False)}}
                ]
            },
        )

    async def run() -> CrystallizationOutput:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider_type()(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            return await provider.generate(_crystallization_input())

    output = asyncio.run(run())

    assert len(seen) == 1
    body = seen[0]
    assert body["stream"] is False
    assert body["model"] == "gemma"
    response_format = body["response_format"]
    assert response_format["type"] == "json_schema"  # type: ignore[index]
    json_schema = response_format["json_schema"]  # type: ignore[index]
    assert json_schema["name"] == "relaylm_crystallization_output"  # type: ignore[index]
    assert json_schema["strict"] is True  # type: ignore[index]
    schema = json_schema["schema"]  # type: ignore[index]
    assert schema["additionalProperties"] is False  # type: ignore[index]
    assert schema["required"] == ["memory_markdown", "state_candidates"]  # type: ignore[index]
    assert "continuity_candidates" not in schema["properties"]  # type: ignore[index]

    messages = body["messages"]
    system_prompt = messages[0]["content"]  # type: ignore[index]
    assert "long-horizon" in system_prompt
    assert "not merely" in system_prompt
    assert "Identity is authoritative and immutable" in system_prompt
    assert "assistant-authored Events" in system_prompt
    assert "reuse its exact `state_class + key`" in system_prompt
    assert "Never invent Event IDs" in system_prompt

    sent = json.loads(messages[1]["content"])  # type: ignore[index]
    assert set(sent) == {"identity", "state", "events", "prior_memory"}
    assert sent["identity"] == {"content": "# ReLM\nBe kind and grounded."}
    assert sent["state"][0] == {
        "state_id": "state-name",
        "state_class": "user.identity",
        "key": "name",
        "value": "Yuto",
        "sources": ["evt-user-name"],
        "status": "active",
        "valid_from": "2026-08-19T00:00:00+00:00",
        "valid_to": None,
    }
    assert sent["events"][0] == {
        "id": "evt-user-name",
        "type": "message",
        "actor": "user",
        "timestamp": "2026-08-19T00:00:00+00:00",
        "payload": {"content": "ユウじゃなくてユウトだよ"},
    }
    assert sent["prior_memory"].startswith("# Memory")

    assert output.memory_markdown.startswith("# Memory")
    assert output.state_candidates[0].state_class == "user.identity"
    assert output.state_candidates[0].key == "name"
    assert output.state_candidates[0].value == "Yuto"
    assert output.state_candidates[0].sources == ("evt-user-name",)


def test_remove_null_normalizes_to_semantic_remove_without_value() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        wire = {
            "memory_markdown": "# Memory\n\nThe cancelled commitment is historical.\n",
            "state_candidates": [
                {
                    "state_class": "relationship.commitment",
                    "key": "next_meeting_date",
                    "op": "remove",
                    "value": None,
                    "sources": ["evt-user-name"],
                }
            ],
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(wire)}}]},
        )

    async def run() -> CrystallizationOutput:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider_type()(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            return await provider.generate(_crystallization_input())

    output = asyncio.run(run())

    candidate = output.state_candidates[0]
    assert candidate.op == "remove"
    assert not candidate.has_value


def test_degree_hint_value_is_preserved_exactly() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        wire = {
            "memory_markdown": "# Memory\n\nCoffee is strongly preferred.\n",
            "state_candidates": [
                {
                    "state_class": "user.preference",
                    "key": "coffee",
                    "op": "set",
                    "value": {"semantic": "likes", "degree_hint": 0.85},
                    "sources": ["evt-user-name"],
                }
            ],
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(wire)}}]},
        )

    async def run() -> CrystallizationOutput:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider_type()(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            return await provider.generate(_crystallization_input())

    output = asyncio.run(run())

    assert output.state_candidates[0].value == {
        "semantic": "likes",
        "degree_hint": 0.85,
    }


@pytest.mark.parametrize(
    "wire",
    [
        {"memory_markdown": "", "state_candidates": []},
        {"memory_markdown": "# Memory\n", "state_candidates": [], "unexpected": True},
        {"memory_markdown": "# Memory\n", "continuity_candidates": []},
        {
            "memory_markdown": "# Memory\n",
            "state_candidates": [
                {
                    "state_class": "not.a.state.class",
                    "key": "name",
                    "op": "set",
                    "value": "Yuto",
                    "sources": ["evt-user-name"],
                }
            ],
        },
        {
            "memory_markdown": "# Memory\n",
            "state_candidates": [
                {
                    "state_class": "user.identity",
                    "key": "name",
                    "op": "remove",
                    "value": "must-be-null",
                    "sources": ["evt-user-name"],
                }
            ],
        },
        {
            "memory_markdown": "# Memory\n",
            "state_candidates": [
                {
                    "state_class": "user.preference",
                    "key": "coffee",
                    "op": "set",
                    "value": {"semantic": "likes", "degree_hint": 1.5},
                    "sources": ["evt-user-name"],
                }
            ],
        },
        {
            "memory_markdown": "# Memory\n",
            "state_candidates": [
                {
                    "state_class": "user.identity",
                    "key": "name",
                    "op": "set",
                    "value": "Yuto",
                    "sources": [],
                }
            ],
        },
        {
            "memory_markdown": "# Memory\n",
            "state_candidates": [
                {
                    "state_class": "user.identity",
                    "key": "name",
                    "op": "set",
                    "value": "Yuto",
                    "sources": ["invented-event"],
                }
            ],
        },
    ],
)
def test_malformed_or_ungrounded_wire_fails_closed(wire: dict[str, object]) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(wire)}}]},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider_type()(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            await provider.generate(_crystallization_input())

    with pytest.raises((ProviderProtocolError, ValueError)):
        asyncio.run(run())

    assert calls == 1


def test_invalid_chat_completion_json_and_http_failure_do_not_retry() -> None:
    for response in (
        httpx.Response(200, content=b"not-json"),
        httpx.Response(503, text="down"),
    ):
        calls = 0

        def handler(_: httpx.Request, *, response: httpx.Response = response) -> httpx.Response:
            nonlocal calls
            calls += 1
            return response

        async def run() -> None:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                provider = _provider_type()(
                    base_url="http://lm.test/v1",
                    model="gemma",
                    http_client=client,
                )
                await provider.generate(_crystallization_input())

        with pytest.raises(ProviderProtocolError):
            asyncio.run(run())
        assert calls == 1


def test_explicit_decoding_controls_are_carried_exactly() -> None:
    seen: list[dict[str, object]] = []
    config = OpenAICompatibleDecodingConfig(
        temperature=0,
        top_p=0.9,
        seed=123,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        wire = {"memory_markdown": "# Memory\n", "state_candidates": []}
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(wire)}}]},
        )

    async def run() -> dict[str, int | float]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider_type()(
                base_url="http://lm.test/v1",
                model="gemma",
                decoding_config=config,
                decoding_capabilities=_all_capabilities(),
                http_client=client,
            )
            await provider.generate(_crystallization_input())
            return provider.effective_decoding_configuration

    effective = asyncio.run(run())

    assert len(seen) == 1
    assert seen[0]["stream"] is False
    assert seen[0]["temperature"] == 0
    assert seen[0]["top_p"] == 0.9
    assert seen[0]["seed"] == 123
    assert effective == {"temperature": 0, "top_p": 0.9, "seed": 123}
