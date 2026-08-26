from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.actual_model_evaluation import ActualModelCognitionPassRequests
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionStructuredOutputMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.runtime_config import RuntimeConfigErrorCode
from relaylm.runtime_config_loader import (
    RuntimeConfigResolutionError,
    _parse_cognition_pass,
)
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
            payload={"content": "コーヒーが好き。"},
            event_id="evt-now",
            timestamp="2026-08-26T00:00:00+00:00",
        ),
    )


def _empty_extraction_wire() -> dict[str, object]:
    return {
        "state_candidates": [],
        "continuity_candidates": [],
    }


def _run_extraction(mode: CognitionStructuredOutputMode | None) -> dict[str, object]:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                _empty_extraction_wire(),
                                ensure_ascii=False,
                            )
                        }
                    }
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
                    assistant_response="コーヒーが好きなんだね。",
                ),
                pass_request=(
                    CognitionPassRequest(structured_output_mode=mode)
                    if mode is not None
                    else None
                ),
            )

    asyncio.run(run())
    assert len(seen) == 1
    return seen[0]


def test_default_and_plain_pass2_keep_relaylm_owned_message_json_path() -> None:
    default_body = _run_extraction(None)
    plain_body = _run_extraction(CognitionStructuredOutputMode.PLAIN)

    assert "response_format" not in default_body
    assert "response_format" not in plain_body


def test_native_pass2_sends_strict_schema_for_direct_candidate_wire() -> None:
    body = _run_extraction(CognitionStructuredOutputMode.NATIVE)

    response_format = body["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    json_schema = response_format["json_schema"]
    assert json_schema["name"] == "relaylm_structured_cognition_output"
    assert json_schema["strict"] is True

    schema = json_schema["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "state_candidates",
        "continuity_candidates",
    ]
    assert "turn_interpretation" not in schema["properties"]
    assert schema["properties"]["state_candidates"]["items"]["properties"]["op"][
        "enum"
    ] == ["set", "remove"]
    assert schema["properties"]["continuity_candidates"]["items"]["properties"][
        "kind"
    ]["enum"] == ["active_task", "referent", "unresolved"]


def test_auto_pass2_stays_plain_without_affirmative_native_capability() -> None:
    body = _run_extraction(CognitionStructuredOutputMode.AUTO)

    assert "response_format" not in body


def test_pass2_prompt_contains_semantics_and_examples_without_scaffold() -> None:
    body = _run_extraction(CognitionStructuredOutputMode.NATIVE)
    prompt = body["messages"][1]["content"]

    assert '"state_class":"user.preference","key":"coffee","op":"set","value":"likes"' in prompt
    assert '"state_class":"user.preference","key":"preferred_beverage","op":"set","value":"coffee"' in prompt
    assert '"state_class":"user.preference","key":"coffee","op":"remove","value":null' in prompt
    assert '"sources":["evt-now"]' in prompt
    assert "examples demonstrate representation only" in prompt
    assert "never copy example values" in prompt
    assert "turn_interpretation" not in prompt
    for removed_field in (
        "`user_meaning`",
        "`change_signals`",
        "`self_meaning`",
        "`assistant_effects`",
        "`continuity_signals`",
    ):
        assert removed_field not in prompt


def test_runtime_config_accepts_pass2_structured_output_mode() -> None:
    request = _parse_cognition_pass(
        {"structured_output_mode": "native"},
        "runtime.cognition.pass2",
    )

    assert request.structured_output_mode is CognitionStructuredOutputMode.NATIVE


def test_runtime_config_rejects_structured_output_mode_on_pass1() -> None:
    with pytest.raises(RuntimeConfigResolutionError) as caught:
        _parse_cognition_pass(
            {"structured_output_mode": "native"},
            "runtime.cognition.pass1",
        )

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_COMBINATION
    assert caught.value.field == "runtime.cognition.pass1.structured_output_mode"


def test_runtime_config_rejects_unknown_pass2_structured_output_mode() -> None:
    with pytest.raises(RuntimeConfigResolutionError) as caught:
        _parse_cognition_pass(
            {"structured_output_mode": "maybe"},
            "runtime.cognition.pass2",
        )

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_VALUE
    assert caught.value.field == "runtime.cognition.pass2.structured_output_mode"


def test_actual_model_pass_request_identity_records_structured_output_mode() -> None:
    mapping = ActualModelCognitionPassRequests.two_pass(
        pass1=CognitionPassRequest(),
        pass2=CognitionPassRequest(
            structured_output_mode=CognitionStructuredOutputMode.NATIVE
        ),
    ).to_mapping()

    assert mapping["pass1"]["structured_output_mode"] is None
    assert mapping["pass2"]["structured_output_mode"] == "native"
