from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.actual_model_stage_r_lm_studio_fixed_continuity_slots import (
    FIXED_SLOT_EXTRACTION_SCHEMA,
    FIXED_SLOT_SCHEMA_NAME,
    FixedContinuitySlotDiagnosticProvider,
    _fixed_slot_request_body,
    _parse_fixed_slot_wire,
)
from relaylm.actual_model_stage_r_lm_studio_semantic_first import (
    _declared_reasoning_capability,
)
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionCompletionMetadata,
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.state import STATE_CLASS_DEFINITIONS


_KINDS = ("referent", "unresolved", "active_task")


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe precise."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "The author is still unknown; keep checking."},
            event_id="evt-now",
            timestamp="2026-09-09T00:00:00+00:00",
        ),
    )


def _transition(kind: str) -> dict[str, object]:
    return {
        "kind": kind,
        "key": "document_author",
        "op": "set",
        "value": "author not yet known",
        "sources": ["evt-now"],
        "epistemic_role": "user_assertion",
    }


def _wire(*, unresolved_decision: str = "emit") -> dict[str, object]:
    return {
        "state_candidates": [],
        "continuity_decisions": {
            "referent": {"decision": "none", "transitions": []},
            "unresolved": {
                "decision": unresolved_decision,
                "transitions": (
                    [_transition("unresolved")]
                    if unresolved_decision == "emit"
                    else []
                ),
            },
            "active_task": {"decision": "none", "transitions": []},
        },
    }


def test_schema_requires_one_explicit_slot_for_each_continuity_kind() -> None:
    decisions = FIXED_SLOT_EXTRACTION_SCHEMA["properties"]["continuity_decisions"]
    assert decisions["required"] == list(_KINDS)
    assert decisions["additionalProperties"] is False

    for kind in _KINDS:
        slot = decisions["properties"][kind]
        assert slot["required"] == ["decision", "transitions"]
        assert slot["properties"]["decision"]["enum"] == ["none", "emit"]
        transition = slot["properties"]["transitions"]["items"]
        assert transition["properties"]["kind"]["enum"] == [kind]


def test_parser_flattens_emit_slots_into_existing_continuity_candidate_grammar() -> None:
    output, decisions = _parse_fixed_slot_wire(
        wire=_wire(),
        completion=CognitionCompletionMetadata(
            finish_reason="stop",
            reasoning_tokens=0,
        ),
    )

    assert output.state_candidates == ()
    assert len(output.continuity_candidates) == 1
    candidate = output.continuity_candidates[0]
    assert candidate.kind == "unresolved"
    assert candidate.key == "document_author"
    assert candidate.op == "set"
    assert candidate.value == "author not yet known"
    assert candidate.sources == ("evt-now",)
    assert candidate.epistemic_role == "user_assertion"
    assert decisions["referent"] == {"decision": "none", "transitions": []}


def test_parser_rejects_none_with_hidden_transition() -> None:
    wire = _wire(unresolved_decision="none")
    wire["continuity_decisions"]["unresolved"]["transitions"] = [
        _transition("unresolved")
    ]
    with pytest.raises(
        ProviderProtocolError,
        match="none decision must have empty transitions",
    ):
        _parse_fixed_slot_wire(
            wire=wire,
            completion=CognitionCompletionMetadata(),
        )


def test_parser_rejects_transition_in_wrong_kind_slot() -> None:
    wire = _wire()
    wire["continuity_decisions"]["unresolved"]["transitions"] = [
        _transition("active_task")
    ]
    with pytest.raises(
        ProviderProtocolError,
        match="transition kind must match its containing slot",
    ):
        _parse_fixed_slot_wire(
            wire=wire,
            completion=CognitionCompletionMetadata(),
        )


def test_request_replaces_only_top_level_transport_with_fixed_slots(tmp_path) -> None:
    provider = FixedContinuitySlotDiagnosticProvider(
        base_url="http://lm.test/v1",
        model="gemma",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda _: None)),
        lm_studio_reasoning_capability=_declared_reasoning_capability(
            request_model="gemma",
            loaded_instance_id="gemma",
            reasoning_options="off,on",
            reasoning_default="on",
        ),
        completion_observation_root=tmp_path / "completion",
        slot_observation_root=tmp_path / "slots",
    )
    try:
        body = _fixed_slot_request_body(
            provider=provider,
            extraction_input=CognitionExtractionInput(
                cognitive_input=_cognitive_input(),
                assistant_response="I will keep that open question in mind.",
            ),
            pass_request=CognitionPassRequest(
                reasoning_mode=CognitionReasoningMode.OFF,
                structured_output_mode=CognitionStructuredOutputMode.NATIVE,
            ),
            reasoning_request=None,
            vllm_reasoning_capability=None,
            lm_studio_reasoning_capability=None,
        )
    finally:
        asyncio.run(provider.aclose())

    response_format = body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == FIXED_SLOT_SCHEMA_NAME
    assert response_format["json_schema"]["schema"] == FIXED_SLOT_EXTRACTION_SCHEMA
    assert body["reasoning_effort"] == "none"

    prompt = body["messages"][1]["content"]
    assert "FIXED-SLOT DIAGNOSTIC TRANSPORT:" in prompt
    assert "Emit `state_candidates`, then `continuity_decisions`" in prompt
    assert '"continuity_candidates":[]' not in prompt
    assert "blue_box" not in prompt
    assert "box_contents_question" not in prompt


def test_provider_uses_fixed_slots_but_returns_existing_extraction_output(tmp_path) -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": json.dumps(_wire())},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                    "completion_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    async def run() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = FixedContinuitySlotDiagnosticProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
                lm_studio_reasoning_capability=_declared_reasoning_capability(
                    request_model="gemma",
                    loaded_instance_id="gemma",
                    reasoning_options="off,on",
                    reasoning_default="on",
                ),
                completion_observation_root=tmp_path / "completion",
                slot_observation_root=tmp_path / "slots",
            )
            try:
                return await provider.generate_extraction(
                    CognitionExtractionInput(
                        cognitive_input=_cognitive_input(),
                        assistant_response="I will keep that open question in mind.",
                    ),
                    pass_request=CognitionPassRequest(
                        reasoning_mode=CognitionReasoningMode.OFF,
                        structured_output_mode=CognitionStructuredOutputMode.NATIVE,
                    ),
                )
            finally:
                await provider.aclose()

    output = asyncio.run(run())
    assert len(seen) == 1
    assert seen[0]["response_format"]["json_schema"]["name"] == FIXED_SLOT_SCHEMA_NAME
    assert len(output.continuity_candidates) == 1
    assert output.continuity_candidates[0].kind == "unresolved"
    assert output.completion.reasoning_tokens == 0

    slot_files = sorted((tmp_path / "slots").glob("*.json"))
    completion_files = sorted((tmp_path / "completion").glob("*.json"))
    assert len(slot_files) == 1
    assert len(completion_files) == 1
    slot_observation = json.loads(slot_files[0].read_text(encoding="utf-8"))
    assert slot_observation["originating_event_id"] == "evt-now"
    assert slot_observation["continuity_decisions"]["unresolved"]["decision"] == "emit"
