from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import pytest

from relaylm.actual_model_targets import load_actual_model_repository_snapshot_target
from relaylm.budget_enforcement import (
    SerializedCognitiveInputTokenCounter,
    SerializedInputTokenCount,
    TokenCountMode,
)
from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import CognitionPassRequest, CognitionReasoningMode
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleSerializedInputCounter,
    SerializedInputCounterIdentity,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
)
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(
            StateRecord(
                state_id="s1",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=("old",),
            ),
        ),
        context=(
            ContextItem(
                content="Earlier assistant utterance",
                sources=("evt-old",),
                actor="assistant",
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "紅茶が好き"},
            event_id="evt-now",
            timestamp="2026-08-17T00:00:00+00:00",
        ),
    )


def _vllm_reasoning_capability():
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


def test_counter_receives_same_model_input_shape_as_buffered_generation() -> None:
    counted: list[dict[str, Any]] = []
    sent: list[dict[str, Any]] = []

    def count_input(model_input: Mapping[str, Any]) -> SerializedInputTokenCount:
        counted.append(dict(model_input))
        return SerializedInputTokenCount(
            total_input_tokens=321,
            required_input_framing_tokens=123,
            mode=TokenCountMode.EXACT,
        )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        wire = {
            "utterance": "了解。",
            "state_candidates": [],
            "continuity_candidates": [],
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(wire, ensure_ascii=False)}}]},
        )

    cognitive_input = _cognitive_input()
    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=count_input,
    )
    count = counter.count_serialized_input(cognitive_input)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            await provider.generate(cognitive_input)

    asyncio.run(run())

    assert count.total_input_tokens == 321
    assert len(counted) == 1
    assert len(sent) == 1
    sent_model_input = {key: value for key, value in sent[0].items() if key != "stream"}
    assert counted[0] == sent_model_input
    assert "stream" not in counted[0]


def test_single_pass_counter_resolves_exact_pass_request_before_counting() -> None:
    counted: list[dict[str, Any]] = []

    def count_input(model_input: Mapping[str, Any]) -> SerializedInputTokenCount:
        counted.append(dict(model_input))
        return SerializedInputTokenCount(
            total_input_tokens=321,
            required_input_framing_tokens=123,
            mode=TokenCountMode.EXACT,
        )

    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma-4-12B-it-qat-w4a16",
        count_input=count_input,
        decoding_config=OpenAICompatibleDecodingConfig(
            temperature=0.7,
            top_p=0.9,
            seed=7,
        ),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            frozenset({"temperature", "top_p", "seed"})
        ),
        vllm_reasoning_capability=_vllm_reasoning_capability(),
    )

    counter.count_serialized_input(
        _cognitive_input(),
        pass_request=CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.OFF,
            temperature=0,
            top_p=1,
        ),
    )

    assert len(counted) == 1
    model_input = counted[0]
    assert model_input["reasoning_effort"] == "none"
    assert "thinking_token_budget" not in model_input
    assert "chat_template_kwargs" not in model_input
    assert model_input["temperature"] == 0
    assert model_input["top_p"] == 1
    assert model_input["seed"] == 7


def test_counter_is_a_serialized_cognitive_input_token_counter() -> None:
    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=lambda _: SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=4,
            mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
        ),
    )

    assert isinstance(counter, SerializedCognitiveInputTokenCounter)
    assert counter.count_serialized_input(_cognitive_input()).mode is TokenCountMode.CONSERVATIVE_ESTIMATE


def test_counting_performs_no_provider_http_request() -> None:
    network_calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("token counting must not call the provider")

    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=lambda _: SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=4,
            mode=TokenCountMode.EXACT,
        ),
    )

    counter.count_serialized_input(_cognitive_input())

    assert network_calls == 0
    assert handler is not None


def test_counter_rejects_missing_model_and_untyped_result() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        OpenAICompatibleSerializedInputCounter(
            model=" ",
            count_input=lambda _: SerializedInputTokenCount(
                total_input_tokens=1,
                required_input_framing_tokens=0,
                mode=TokenCountMode.EXACT,
            ),
        )

    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=lambda _: 10,  # type: ignore[arg-type,return-value]
    )
    with pytest.raises(TypeError, match="SerializedInputTokenCount"):
        counter.count_serialized_input(_cognitive_input())


def test_counter_rejects_result_mode_drift_from_evidence_identity() -> None:
    identity = SerializedInputCounterIdentity(
        capability="test.counter",
        implementation="test-counter",
        version="1",
        mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
        tokenizer_identity="gguf-embedded-tokenizer:sha256:test",
    )
    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=lambda _: SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=4,
            mode=TokenCountMode.EXACT,
        ),
        evidence_identity=identity,
    )

    with pytest.raises(ValueError, match="result mode"):
        counter.count_serialized_input(_cognitive_input())
