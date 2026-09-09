from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.actual_model_stage_r_lm_studio_continuity_label_invariance import (
    LABEL_INVARIANCE_EXTRACTION_SCHEMA,
    LABEL_INVARIANCE_SCHEMA_NAME,
    SHADOW_OPEN_QUESTION_KIND,
    ContinuityLabelInvarianceDiagnosticProvider,
    _label_alias_request_body,
    _parse_label_alias_wire,
)
from relaylm.actual_model_stage_r_lm_studio_semantic_first import (
    _declared_reasoning_capability,
)
from relaylm.cognitive import CognitiveInput, ContextItem
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


_SHADOW_KINDS = ("referent", SHADOW_OPEN_QUESTION_KIND, "active_task")


def _accepted_unresolved_context() -> ContextItem:
    return ContextItem(
        content=json.dumps(
            {
                "continuity": {
                    "kind": "unresolved",
                    "key": "document_author",
                    "value": "author not yet known",
                    "epistemic_role": "user_assertion",
                }
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        sources=("evt-old",),
    )


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe precise."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(_accepted_unresolved_context(),),
        input=Event.create(
            type="message",
            actor="user",
            payload={
                "content": "Keep the literal word unresolved unchanged in user text."
            },
            event_id="evt-now",
            timestamp="2026-09-09T00:00:00+00:00",
        ),
    )


def _transition(kind: str = SHADOW_OPEN_QUESTION_KIND) -> dict[str, object]:
    return {
        "kind": kind,
        "key": "document_author",
        "op": "set",
        "value": "author not yet known",
        "sources": ["evt-now"],
        "epistemic_role": "user_assertion",
    }


def _wire() -> dict[str, object]:
    return {
        "state_candidates": [],
        "continuity_decisions": {
            "referent": {"decision": "none", "transitions": []},
            SHADOW_OPEN_QUESTION_KIND: {
                "decision": "emit",
                "transitions": [_transition()],
            },
            "active_task": {"decision": "none", "transitions": []},
        },
    }


def _provider(tmp_path) -> ContinuityLabelInvarianceDiagnosticProvider:
    return ContinuityLabelInvarianceDiagnosticProvider(
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


def test_schema_replaces_only_unresolved_slot_with_shadow_alias() -> None:
    decisions = LABEL_INVARIANCE_EXTRACTION_SCHEMA["properties"][
        "continuity_decisions"
    ]
    assert decisions["required"] == list(_SHADOW_KINDS)
    assert list(decisions["properties"]) == list(_SHADOW_KINDS)
    assert "unresolved" not in decisions["properties"]
    transition = decisions["properties"][SHADOW_OPEN_QUESTION_KIND]["properties"][
        "transitions"
    ]["items"]
    assert transition["properties"]["kind"]["enum"] == [SHADOW_OPEN_QUESTION_KIND]


def test_parser_maps_shadow_alias_back_to_canonical_unresolved() -> None:
    output, decisions = _parse_label_alias_wire(
        wire=_wire(),
        completion=CognitionCompletionMetadata(
            finish_reason="stop",
            reasoning_tokens=0,
        ),
    )

    assert len(output.continuity_candidates) == 1
    candidate = output.continuity_candidates[0]
    assert candidate.kind == "unresolved"
    assert candidate.key == "document_author"
    assert candidate.op == "set"
    assert decisions[SHADOW_OPEN_QUESTION_KIND]["decision"] == "emit"
    assert decisions[SHADOW_OPEN_QUESTION_KIND]["transitions"][0]["kind"] == (
        SHADOW_OPEN_QUESTION_KIND
    )


def test_parser_rejects_canonical_kind_inside_shadow_slot() -> None:
    wire = _wire()
    wire["continuity_decisions"][SHADOW_OPEN_QUESTION_KIND]["transitions"] = [
        _transition("unresolved")
    ]
    with pytest.raises(
        ProviderProtocolError,
        match="open_question transition kind must match",
    ):
        _parse_label_alias_wire(
            wire=wire,
            completion=CognitionCompletionMetadata(),
        )


def test_request_aliases_only_model_facing_continuity_coordinate(tmp_path) -> None:
    provider = _provider(tmp_path)
    try:
        body = _label_alias_request_body(
            provider=provider,
            extraction_input=CognitionExtractionInput(
                cognitive_input=_cognitive_input(),
                assistant_response="The literal word unresolved also stays in Pass 1.",
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

    assert body["reasoning_effort"] == "none"
    response_format = body["response_format"]
    assert response_format["json_schema"]["name"] == LABEL_INVARIANCE_SCHEMA_NAME
    assert (
        response_format["json_schema"]["schema"]
        == LABEL_INVARIANCE_EXTRACTION_SCHEMA
    )

    prompt = body["messages"][1]["content"]
    cognitive_text = prompt.split("<COGNITIVE_INPUT>\n", 1)[1].split(
        "\n</COGNITIVE_INPUT>", 1
    )[0]
    serialized = json.loads(cognitive_text)
    projected = json.loads(serialized["context"][0]["content"])
    assert projected["continuity"]["kind"] == SHADOW_OPEN_QUESTION_KIND
    assert serialized["input"]["content"] == (
        "Keep the literal word unresolved unchanged in user text."
    )

    pass_1 = prompt.split("<PASS_1_RESPONSE_JSON>\n", 1)[1].split(
        "\n</PASS_1_RESPONSE_JSON>", 1
    )[0]
    assert "unresolved" in pass_1
    static_instructions = prompt.split("</PASS_1_RESPONSE_JSON>\n\n", 1)[1]
    assert "`open_question`" in static_instructions
    assert "`open_question` set" in static_instructions
    assert "`unresolved`" not in static_instructions
    assert "blue_box" not in prompt
    assert "box_contents_question" not in prompt


def test_provider_returns_canonical_candidate_and_records_shadow_decision(
    tmp_path,
) -> None:
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
            provider = ContinuityLabelInvarianceDiagnosticProvider(
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
    assert seen[0]["response_format"]["json_schema"]["name"] == (
        LABEL_INVARIANCE_SCHEMA_NAME
    )
    assert len(output.continuity_candidates) == 1
    assert output.continuity_candidates[0].kind == "unresolved"
    assert output.completion.reasoning_tokens == 0

    slot_files = sorted((tmp_path / "slots").glob("*.json"))
    completion_files = sorted((tmp_path / "completion").glob("*.json"))
    assert len(slot_files) == 1
    assert len(completion_files) == 1
    observation = json.loads(slot_files[0].read_text(encoding="utf-8"))
    assert observation["shadow_alias"] == {"unresolved": SHADOW_OPEN_QUESTION_KIND}
    assert observation["continuity_decisions"][SHADOW_OPEN_QUESTION_KIND][
        "decision"
    ] == "emit"
