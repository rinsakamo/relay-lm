from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from relaylm.actual_model_targets import load_actual_model_repository_snapshot_target
from relaylm.actual_model_vllm_counter import VLLMServingTokenizerCounter
from relaylm.actual_model_vllm_host import (
    acquire_vllm_reasoning_capability,
    load_vllm_reasoning_probe_proof,
)
from relaylm.budget_enforcement import TokenCountMode
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionPassRequest, CognitionReasoningMode
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleTwoPassSerializedInputCounter,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
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


def test_vllm_exact_counter_accepts_provider_hard_output_limit_without_tokenizing_it() -> None:
    target = load_actual_model_repository_snapshot_target(TARGET_PATH)
    proof = load_vllm_reasoning_probe_proof(PROOF_PATH)
    capability = acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_live_fetch,
    )
    observed: list[dict[str, Any]] = []

    def post_json(_: str, payload: Mapping[str, Any], __: str | None) -> object:
        body = dict(payload)
        observed.append(body)
        messages = body["messages"]
        assert isinstance(messages, list)
        has_content = any(
            isinstance(message, Mapping) and bool(message.get("content"))
            for message in messages
        )
        return {
            "count": 900 if has_content else 100,
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
    counter = OpenAICompatibleTwoPassSerializedInputCounter(
        model=REQUEST_MODEL,
        count_input=serving_counter.count_input,
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            frozenset({"max_output_tokens"})
        ),
        vllm_reasoning_capability=capability,
        evidence_identity=serving_counter.evidence_identity,
    )

    counted = counter.count_conversation_input(
        _cognitive_input(),
        pass_request=CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.OFF,
            max_output_tokens=64,
        ),
    )

    assert counted.total_input_tokens == 900
    assert counted.required_input_framing_tokens == 100
    assert counted.mode is TokenCountMode.EXACT
    assert len(observed) == 2
    assert all("max_tokens" not in payload for payload in observed)
