from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from relaylm.actual_model_targets import load_actual_model_repository_snapshot_target
from relaylm.actual_model_vllm_host import (
    acquire_vllm_reasoning_capability,
    load_vllm_reasoning_probe_proof,
)
from relaylm.budget_enforcement import TokenCountMode
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
from relaylm.state import STATE_CLASS_DEFINITIONS
from relaylm.actual_model_vllm_counter import (
    VLLMServingTokenizerCounter,
    VLLMServingTokenizerCounterError,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)
PROOF_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "attestations"
    / "gemma-4-12b-it-qat-w4a16-vllm-reasoning-v1.json"
)
SNAPSHOT_ROOT = "/tmp/relaylm-unsloth-w4a16-model"
REQUEST_MODEL = "gemma-4-12B-it-qat-w4a16"


def _live_fetch(url: str, _: str | None) -> object:
    if url.endswith("/version"):
        return {"version": "0.27.1"}
    if url.endswith("/v1/models"):
        return {
            "object": "list",
            "data": [
                {
                    "id": REQUEST_MODEL,
                    "object": "model",
                    "root": SNAPSHOT_ROOT,
                    "max_model_len": 1024,
                }
            ],
        }
    raise AssertionError(f"unexpected identity URL: {url}")


def _target_and_capability():
    target = load_actual_model_repository_snapshot_target(TARGET_PATH)
    proof = load_vllm_reasoning_probe_proof(PROOF_PATH)
    capability = acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_live_fetch,
    )
    return target, capability


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


def test_vllm_serving_counter_counts_current_off_and_bounded_requests_via_tokenize() -> None:
    target, capability = _target_and_capability()
    observed: list[tuple[str, dict[str, Any]]] = []

    def post_json(url: str, payload: Mapping[str, Any], _: str | None) -> object:
        body = dict(payload)
        observed.append((url, body))
        messages = body["messages"]
        assert isinstance(messages, list)
        has_content = any(
            isinstance(message, Mapping) and bool(message.get("content"))
            for message in messages
        )
        count = 900 if has_content else 100
        return {
            "count": count,
            "max_model_len": 1024,
            "tokens": [],
            "token_strs": None,
        }

    serving_counter = VLLMServingTokenizerCounter(
        base_url="http://127.0.0.1:8000/v1",
        target=target,
        reasoning_capability=capability,
        expected_max_model_len=1024,
        post_json=post_json,
    )
    decoding_capabilities = OpenAICompatibleDecodingCapabilities(
        frozenset({"temperature", "top_p"})
    )
    counter = OpenAICompatibleTwoPassSerializedInputCounter(
        model=REQUEST_MODEL,
        count_input=serving_counter.count_input,
        decoding_capabilities=decoding_capabilities,
        vllm_reasoning_capability=capability,
        evidence_identity=serving_counter.evidence_identity,
    )
    cognitive_input = _cognitive_input()

    pass1 = counter.count_conversation_input(
        cognitive_input,
        pass_request=CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.OFF,
            temperature=0,
            top_p=1,
        ),
    )
    pass2 = counter.count_extraction_input(
        CognitionExtractionInput(
            cognitive_input=cognitive_input,
            assistant_response="hello back",
        ),
        pass_request=CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.BOUNDED,
            reasoning_budget=16,
            temperature=0,
            top_p=1,
        ),
    )

    assert pass1.total_input_tokens == 900
    assert pass1.required_input_framing_tokens == 100
    assert pass1.mode is TokenCountMode.EXACT
    assert pass2.total_input_tokens == 900
    assert pass2.required_input_framing_tokens == 100
    assert pass2.mode is TokenCountMode.EXACT
    assert serving_counter.evidence_identity.mode is TokenCountMode.EXACT
    assert serving_counter.evidence_identity.tokenizer_identity == target.tokenizer_identity

    assert len(observed) == 4
    assert all(url == "http://127.0.0.1:8000/tokenize" for url, _ in observed)
    full_pass1 = observed[0][1]
    framing_pass1 = observed[1][1]
    full_pass2 = observed[2][1]
    framing_pass2 = observed[3][1]

    assert full_pass1["model"] == REQUEST_MODEL
    assert full_pass1["chat_template_kwargs"] == {
        "enable_thinking": False,
        "reasoning_effort": "none",
    }
    assert full_pass2["chat_template_kwargs"] == {"enable_thinking": True}
    for payload in (full_pass1, framing_pass1, full_pass2, framing_pass2):
        assert "temperature" not in payload
        assert "top_p" not in payload
        assert "reasoning_effort" not in payload
        assert "thinking_token_budget" not in payload
        assert "response_format" not in payload
        assert payload["add_generation_prompt"] is True
        assert payload["return_token_strs"] is False
    assert all(not message["content"] for message in framing_pass1["messages"])
    assert all(not message["content"] for message in framing_pass2["messages"])


def test_vllm_serving_counter_fails_closed_on_drift_and_unknown_shape() -> None:
    target, capability = _target_and_capability()

    with pytest.raises(VLLMServingTokenizerCounterError, match="max_model_len"):
        VLLMServingTokenizerCounter(
            base_url="http://127.0.0.1:8000/v1",
            target=target,
            reasoning_capability=capability,
            expected_max_model_len=2048,
            post_json=lambda *_: {},
        )

    def drifted_post(_: str, __: Mapping[str, Any], ___: str | None) -> object:
        return {
            "count": 10,
            "max_model_len": 2048,
            "tokens": [],
            "token_strs": None,
        }

    counter = VLLMServingTokenizerCounter(
        base_url="http://127.0.0.1:8000/v1",
        target=target,
        reasoning_capability=capability,
        expected_max_model_len=1024,
        post_json=drifted_post,
    )
    with pytest.raises(VLLMServingTokenizerCounterError, match="max_model_len"):
        counter.count_input(
            {
                "model": REQUEST_MODEL,
                "messages": [{"role": "user", "content": "hello"}],
            }
        )

    with pytest.raises(VLLMServingTokenizerCounterError, match="unsupported"):
        counter.count_input(
            {
                "model": REQUEST_MODEL,
                "messages": [{"role": "user", "content": "hello"}],
                "arbitrary_backend_knob": True,
            }
        )
