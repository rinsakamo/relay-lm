from __future__ import annotations

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionStructuredOutputMode,
)
from relaylm.crystallization import CrystallizationInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.lm_studio_reasoning import (
    attest_lm_studio_reasoning_capabilities,
)
from relaylm.providers.openai_compatible import _request_body as _single_request_body
from relaylm.providers.openai_compatible_crystallization import (
    _request_body as _crystallization_request_body,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.openai_compatible_two_pass import (
    _conversation_request_body,
    _extraction_request_body,
)
from relaylm.state import CanonicalState, STATE_CLASS_DEFINITIONS


def _models_response() -> dict[str, object]:
    return {
        "models": [
            {
                "type": "llm",
                "key": "google/gemma-4-12b",
                "capabilities": {
                    "reasoning": {
                        "allowed_options": ["off", "on"],
                        "default": "on",
                    }
                },
                "loaded_instances": [
                    {
                        "id": "gemma-live-1",
                        "config": {"context_length": 8192},
                    }
                ],
            }
        ]
    }


def _capability():
    return attest_lm_studio_reasoning_capabilities(
        models_response=_models_response(),
        request_model="google/gemma-4-12b",
        loaded_instance_id="gemma-live-1",
    )


def _event() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "hello"},
        event_id="evt-now",
        timestamp="2026-09-06T00:00:00+00:00",
    )


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=_event(),
    )


def _assert_explicit_off(body: dict[str, object]) -> None:
    assert body["reasoning_effort"] == "off"
    assert "reasoning_tokens" not in body
    assert "thinking_token_budget" not in body
    assert "chat_template_kwargs" not in body


def test_lm_studio_single_pass_serializes_explicit_reasoning_off() -> None:
    body = _single_request_body(
        model="google/gemma-4-12b",
        cognitive_input=_cognitive_input(),
        stream=False,
        reasoning_request=OpenAICompatibleReasoningRequest(mode="off"),
        lm_studio_reasoning_capability=_capability(),
    )

    _assert_explicit_off(body)


def test_lm_studio_two_pass_serializes_explicit_reasoning_off_on_both_passes() -> None:
    cognitive_input = _cognitive_input()
    capability = _capability()
    reasoning = OpenAICompatibleReasoningRequest(mode="off")

    pass1 = _conversation_request_body(
        model="google/gemma-4-12b",
        cognitive_input=cognitive_input,
        stream=False,
        decoding={},
        reasoning_request=reasoning,
        lm_studio_reasoning_capability=capability,
    )
    pass2 = _extraction_request_body(
        model="google/gemma-4-12b",
        extraction_input=CognitionExtractionInput(
            cognitive_input=cognitive_input,
            assistant_response="hello",
        ),
        decoding={},
        reasoning_request=reasoning,
        lm_studio_reasoning_capability=capability,
        structured_output_mode=CognitionStructuredOutputMode.NATIVE,
    )

    _assert_explicit_off(pass1)
    _assert_explicit_off(pass2)
    assert "response_format" not in pass1
    assert pass2["response_format"]["type"] == "json_schema"  # type: ignore[index]


def test_lm_studio_crystallization_serializes_explicit_reasoning_off() -> None:
    body = _crystallization_request_body(
        model="google/gemma-4-12b",
        crystallization_input=CrystallizationInput(
            identity=Identity("# ReLM\nBe kind."),
            state=CanonicalState(),
            events=(_event(),),
        ),
        reasoning_request=OpenAICompatibleReasoningRequest(mode="off"),
        lm_studio_reasoning_capability=_capability(),
    )

    _assert_explicit_off(body)
    assert body["response_format"]["type"] == "json_schema"  # type: ignore[index]
