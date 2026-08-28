from __future__ import annotations

import asyncio
import json

import httpx
import pytest

import relaylm.providers as providers
from relaylm.providers.openai_compatible_crystallization import (
    STATE_CANDIDATE_WIRE_SCHEMA,
    SYSTEM_INSTRUCTION,
    parse_crystallization_wire_output,
)
from relaylm.crystallization import CrystallizationInput, CrystallizationOutput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_provenance import MemoryTemporalScope
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


def _memory_wire(content: str = "Durable memory.") -> dict[str, object]:
    return {
        "memory_units": [{
            "heading": "Memory",
            "content": content,
            "temporal_scope": "unknown",
            "sources": [],
        }],
        "state_candidates": [],
    }


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


def test_system_instruction_retires_completed_transient_state_without_completion_value() -> None:
    assert (
        "When Canonical State contains a temporary active task or goal and later user "
        "Event evidence explicitly establishes completion, cancellation, or that it "
        "should no longer remain a future goal"
    ) in SYSTEM_INSTRUCTION
    assert "do not replace its active value with durable semantic `completed`" in SYSTEM_INSTRUCTION
    assert "prefer `remove` for that exact existing `state_class + key`" in SYSTEM_INSTRUCTION
    assert "preserve the Event history" in SYSTEM_INSTRUCTION
    assert (
        "omit short-lived task mechanics from long-horizon MEMORY unless the event "
        "has independently durable significance"
    ) in SYSTEM_INSTRUCTION


def test_system_instruction_preserves_value_representation_and_limits_degree_hint() -> None:
    assert (
        "When correcting an existing exact `state_class + key`, preserve the existing "
        "plain-string versus degree-hint representation form"
    ) in SYSTEM_INSTRUCTION
    assert "unless supplied current evidence materially requires new or changed comparative/intensity semantics" in SYSTEM_INSTRUCTION
    assert "Never introduce `degree_hint` as confidence, evidence strength, importance, or stylistic emphasis" in SYSTEM_INSTRUCTION
    assert "Avoid false precision" in SYSTEM_INSTRUCTION
    assert (
        "A categorical current-value correction represented adequately by a string "
        "should remain a string unless actual semantic evidence requires a graded representation"
    ) in SYSTEM_INSTRUCTION


def test_system_instruction_keeps_memory_units_stable_across_organization() -> None:
    assert (
        "Organize MEMORY around stable semantic units rather than transient wording or "
        "arbitrary heading choices"
    ) in SYSTEM_INSTRUCTION
    assert (
        "When current and historical aspects of one concept are both durable, keep "
        "their semantic units and stable logical identities coherent across updates"
    ) in SYSTEM_INSTRUCTION
    assert "do not split or merge them solely because of Markdown organization" in SYSTEM_INSTRUCTION


@pytest.mark.parametrize("forbidden_key", ["memory_id", "derivation_id"])
def test_model_cannot_supply_persistent_memory_identity(forbidden_key: str) -> None:
    wire = _memory_wire()
    wire["memory_units"][0][forbidden_key] = "model-invented"  # type: ignore[index]

    with pytest.raises(ProviderProtocolError, match="exactly heading, content"):
        parse_crystallization_wire_output(
            wire,
            allowed_source_ids=frozenset(),
        )


def test_provider_makes_one_nonstreaming_strict_request_and_returns_crystallization_output() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        wire = {
            "memory_units": [{
                "heading": "User identity",
                "content": "The user's current name is Yuto; an earlier Yuu form was corrected.",
                "temporal_scope": "current",
                "sources": [{"kind": "event", "reference_id": "evt-user-name"}],
            }],
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
    assert schema["required"] == ["memory_units", "state_candidates"]  # type: ignore[index]
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

    assert output.memory_units[0].heading == "User identity"
    assert output.memory_units[0].temporal_scope is MemoryTemporalScope.CURRENT
    assert output.memory_units[0].sources[0].reference_id == "evt-user-name"
    assert output.state_candidates[0].state_class == "user.identity"
    assert output.state_candidates[0].key == "name"
    assert output.state_candidates[0].value == "Yuto"
    assert output.state_candidates[0].sources == ("evt-user-name",)


def test_remove_null_normalizes_to_semantic_remove_without_value() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        wire = {
            "memory_units": [{
                "heading": "History",
                "content": "The cancelled commitment is historical.",
                "temporal_scope": "historical",
                "sources": [],
            }],
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
            "memory_units": [{
                "heading": "Preferences",
                "content": "Coffee is strongly preferred.",
                "temporal_scope": "unknown",
                "sources": [],
            }],
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
        {"memory_units": [], "state_candidates": []},
        {**_memory_wire(), "unexpected": True},
        {"memory_units": [{"heading": "x", "content": "x", "temporal_scope": "unknown", "sources": []}], "continuity_candidates": []},
        {
            **_memory_wire(),
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
            **_memory_wire(),
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
            **_memory_wire(),
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
            **_memory_wire(),
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
            **_memory_wire(),
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
        wire = _memory_wire()
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


@pytest.mark.parametrize(
    "choices",
    [
        [],
        [
            {"message": {"content": json.dumps(_memory_wire())}},
            {"message": {"content": json.dumps(_memory_wire())}},
        ],
    ],
    ids=["zero", "multiple"],
)
def test_provider_rejects_non_singleton_choice_cardinality(
    choices: list[object],
) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"choices": choices})

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
