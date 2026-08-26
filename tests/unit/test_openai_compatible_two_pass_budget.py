from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import pytest

from relaylm.actual_model_targets import load_actual_model_repository_snapshot_target
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionReasoningMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleTwoPassSerializedInputCounter,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
)
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
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
            VLLMReasoningWireControls(thinking_token_budget=16),
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
            timestamp="2026-08-21T00:00:00+00:00",
        ),
    )


def test_two_pass_counter_matches_production_pass_requests_exactly() -> None:
    counted: list[dict[str, Any]] = []
    sent: list[dict[str, Any]] = []

    def count_input(model_input: Mapping[str, Any]) -> SerializedInputTokenCount:
        counted.append(dict(model_input))
        return SerializedInputTokenCount(
            total_input_tokens=321 + len(counted),
            required_input_framing_tokens=123,
            mode=TokenCountMode.EXACT,
        )

    capability = _capability()
    decoding_capabilities = OpenAICompatibleDecodingCapabilities(
        frozenset({"temperature", "top_p"})
    )
    counter = OpenAICompatibleTwoPassSerializedInputCounter(
        model="gemma-4-12B-it-qat-w4a16",
        count_input=count_input,
        decoding_capabilities=decoding_capabilities,
        vllm_reasoning_capability=capability,
    )
    cognitive_input = _cognitive_input()
    extraction_input = CognitionExtractionInput(
        cognitive_input=cognitive_input,
        assistant_response="hello back",
    )
    pass1 = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=0,
        top_p=1,
    )
    pass2 = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.BOUNDED,
        reasoning_budget=16,
        temperature=0,
        top_p=1,
    )

    pass1_count = counter.count_conversation_input(
        cognitive_input,
        pass_request=pass1,
    )
    pass2_count = counter.count_extraction_input(
        extraction_input,
        pass_request=pass2,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        if len(sent) == 1:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "hello back"}}]},
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "state_candidates": [],
                                    "continuity_candidates": [],
                                }
                            )
                        }
                    }
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma-4-12B-it-qat-w4a16",
                decoding_capabilities=decoding_capabilities,
                vllm_reasoning_capability=capability,
                http_client=client,
            )
            conversation = await provider.generate_conversation(
                cognitive_input,
                pass_request=pass1,
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=cognitive_input,
                    assistant_response=conversation.response,
                ),
                pass_request=pass2,
            )

    asyncio.run(run())

    assert len(counted) == 2
    assert len(sent) == 2
    assert counted == [
        {key: value for key, value in body.items() if key != "stream"}
        for body in sent
    ]
    assert pass1_count.total_input_tokens == 322
    assert pass2_count.total_input_tokens == 323
    assert counted[0]["reasoning_effort"] == "none"
    assert "response_format" not in counted[0]
    assert counted[1]["thinking_token_budget"] == 16
    assert counted[1]["chat_template_kwargs"] == {"enable_thinking": True}
    assert "response_format" not in counted[1]


def test_two_pass_counter_makes_no_network_request_and_rejects_untyped_count() -> None:
    calls = 0

    def count_input(_: Mapping[str, Any]) -> SerializedInputTokenCount:
        nonlocal calls
        calls += 1
        return SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=4,
            mode=TokenCountMode.EXACT,
        )

    counter = OpenAICompatibleTwoPassSerializedInputCounter(
        model="gemma",
        count_input=count_input,
    )
    cognitive_input = _cognitive_input()

    assert counter.count_conversation_input(cognitive_input).total_input_tokens == 10
    assert calls == 1

    invalid = OpenAICompatibleTwoPassSerializedInputCounter(
        model="gemma",
        count_input=lambda _: 10,  # type: ignore[arg-type,return-value]
    )
    with pytest.raises(TypeError, match="SerializedInputTokenCount"):
        invalid.count_conversation_input(cognitive_input)
