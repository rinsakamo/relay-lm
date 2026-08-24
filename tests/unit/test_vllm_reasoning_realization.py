from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from relaylm.actual_model_targets import load_actual_model_repository_snapshot_target
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import _request_body
from relaylm.providers.openai_compatible_cognition import (
    describe_openai_compatible_cognition_capabilities,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningApplicationStatus,
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.openai_compatible_two_pass import (
    _conversation_request_body,
    _extraction_request_body,
)
from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityStatus,
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
)
from relaylm.providers.vllm_reasoning_realization import (
    VLLMReasoningRealizationError,
    realize_vllm_reasoning_request,
)
from relaylm.state import STATE_CLASS_DEFINITIONS


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)


def _capability():
    target = load_actual_model_repository_snapshot_target(TARGET_PATH)
    backend = attest_vllm_backend(
        request_model="gemma-4-12B-it-qat-w4a16",
        version_response={"version": "0.27.1"},
        models_response={
            "object": "list",
            "data": [
                {
                    "id": "gemma-4-12B-it-qat-w4a16",
                    "object": "model",
                    "root": "/tmp/relaylm-unsloth-w4a16-model",
                    "max_model_len": 1024,
                }
            ],
        },
    )

    def probe(controls, *, activation=False, template=()):
        return VLLMReasoningProbeEvidence(
            wire_controls=controls,
            http_status=200,
            accepted=True,
            effect_proven=True,
            repeatable=True,
            activation_applied=activation,
            template_kwargs=template,
        )

    return attest_vllm_reasoning_capabilities(
        backend_attestation=backend,
        target=target,
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=probe(VLLMReasoningWireControls(reasoning_effort="none")),
        bounded_probe=probe(
            VLLMReasoningWireControls(thinking_token_budget=64),
            activation=True,
            template=(("enable_thinking", True),),
        ),
    )


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "hello"},
            event_id="evt-now",
            timestamp="2026-08-20T00:00:00+00:00",
        ),
    )


def test_realizer_maps_exact_off_and_bounded_wire_from_one_serializer() -> None:
    capability = _capability()

    off = realize_vllm_reasoning_request(
        request=OpenAICompatibleReasoningRequest(mode="off"),
        capability=capability,
    )
    bounded = realize_vllm_reasoning_request(
        request=OpenAICompatibleReasoningRequest(mode="bounded", token_budget=64),
        capability=capability,
    )

    assert off.application.status is OpenAICompatibleReasoningApplicationStatus.APPLIED
    assert off.to_request_fields() == {"reasoning_effort": "none"}
    assert off.application.to_mapping() == {
        "status": "applied",
        "requested": {"mode": "off"},
        "wire_fields": {"reasoning_effort": "none"},
    }
    assert bounded.application.status is OpenAICompatibleReasoningApplicationStatus.APPLIED
    assert bounded.to_request_fields() == {
        "thinking_token_budget": 64,
        "chat_template_kwargs": {"enable_thinking": True},
    }
    assert bounded.application.to_mapping() == {
        "status": "applied",
        "requested": {"mode": "bounded", "token_budget": 64},
        "wire_fields": {
            "chat_template_kwargs.enable_thinking": True,
            "thinking_token_budget": 64,
        },
    }
    assert bounded.to_mapping()["resolved"] == {
        "chat_template_kwargs.enable_thinking": True,
        "thinking_token_budget": 64,
    }


def test_realizer_omits_reasoning_without_request_and_rejects_unattested_or_conflicting_controls() -> None:
    capability = _capability()
    omitted = realize_vllm_reasoning_request(
        request=OpenAICompatibleReasoningRequest(),
        capability=capability,
    )
    assert omitted.application.status is OpenAICompatibleReasoningApplicationStatus.OMITTED
    assert omitted.to_request_fields() == {}

    with pytest.raises(VLLMReasoningRealizationError, match="enable_thinking"):
        realize_vllm_reasoning_request(
            request=OpenAICompatibleReasoningRequest(mode="off"),
            capability=capability,
            existing_chat_template_kwargs={"enable_thinking": True},
        )

    with pytest.raises(ValueError, match="bounded reasoning requires"):
        realize_vllm_reasoning_request(
            request=OpenAICompatibleReasoningRequest(mode="bounded"),
            capability=capability,
        )


def test_ordinary_and_two_pass_builders_carry_each_resolved_request_independently() -> None:
    capability = _capability()
    cognitive_input = _cognitive_input()
    off_request = OpenAICompatibleReasoningRequest(mode="off")
    bounded_request = OpenAICompatibleReasoningRequest(mode="bounded", token_budget=64)

    ordinary = _request_body(
        model="gemma-4-12B-it-qat-w4a16",
        cognitive_input=cognitive_input,
        stream=False,
        reasoning_request=off_request,
        vllm_reasoning_capability=capability,
    )
    ordinary_stream = _request_body(
        model="gemma-4-12B-it-qat-w4a16",
        cognitive_input=cognitive_input,
        stream=True,
        reasoning_request=off_request,
        vllm_reasoning_capability=capability,
    )
    conversation = _conversation_request_body(
        model="gemma-4-12B-it-qat-w4a16",
        cognitive_input=cognitive_input,
        stream=False,
        decoding={},
        reasoning_request=off_request,
        vllm_reasoning_capability=capability,
    )
    extraction = _extraction_request_body(
        model="gemma-4-12B-it-qat-w4a16",
        extraction_input=CognitionExtractionInput(
            cognitive_input=cognitive_input,
            assistant_response="hello",
        ),
        decoding={},
        reasoning_request=bounded_request,
        vllm_reasoning_capability=capability,
    )

    for body in (ordinary, ordinary_stream, conversation):
        assert body["reasoning_effort"] == "none"
        assert "thinking_token_budget" not in body
        assert "chat_template_kwargs" not in body
    assert extraction["thinking_token_budget"] == 64
    assert extraction["chat_template_kwargs"] == {"enable_thinking": True}
    assert ordinary["reasoning_effort"] == ordinary_stream["reasoning_effort"]
    extraction_prompt = extraction["messages"][1]["content"]
    assert '<PASS_1_RESPONSE_JSON>\n{"content":"hello"}\n</PASS_1_RESPONSE_JSON>' in extraction_prompt


def test_body_builder_fails_closed_before_wire_for_unattested_capability() -> None:
    capability = replace(
        _capability(),
        reasoning_off=replace(
            _capability().reasoning_off,
            status=VLLMReasoningCapabilityStatus.ACCEPTED_BUT_EFFECT_UNPROVEN,
        ),
    )
    with pytest.raises(VLLMReasoningRealizationError, match="semantically attested"):
        _request_body(
            model="gemma-4-12B-it-qat-w4a16",
            cognitive_input=_cognitive_input(),
            stream=False,
            reasoning_request=OpenAICompatibleReasoningRequest(mode="off"),
            vllm_reasoning_capability=capability,
        )


def test_provider_cognition_facts_promote_only_attested_vllm_controls() -> None:
    source = SimpleNamespace(
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset()
        ),
        vllm_reasoning_capability=_capability(),
    )

    facts = describe_openai_compatible_cognition_capabilities(source)

    assert facts.reasoning_modes == ("bounded", "off")
    assert facts.bounded_reasoning_budget is True
