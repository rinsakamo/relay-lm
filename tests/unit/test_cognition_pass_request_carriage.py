from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExecutionCapabilityError,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionReasoningMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
)
from relaylm.actual_model_targets import load_actual_model_repository_snapshot_target
from relaylm.state import CanonicalState, STATE_CLASS_DEFINITIONS
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import run_user_turn
from relaylm.two_pass_turn import (
    CognitionExecutionRuntime,
    run_user_turn_two_pass,
    run_user_turn_two_pass_streaming,
)


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


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _empty_turn_interpretation() -> dict[str, list[str]]:
    return {
        "user_meaning": [],
        "change_signals": [],
        "self_meaning": [],
        "assistant_effects": [],
        "unresolved": [],
        "continuity_signals": [],
    }


def _completion(schema_name: str) -> dict[str, object]:
    if schema_name == "relaylm_cognitive_output":
        content = {
            "utterance": "hello",
            "state_candidates": [],
            "continuity_candidates": [],
        }
    elif schema_name == "relaylm_structured_cognition_output":
        content = {
            "turn_interpretation": _empty_turn_interpretation(),
            "state_candidates": [],
            "continuity_candidates": [],
        }
    else:
        raise AssertionError(schema_name)
    return {"choices": [{"message": {"content": json.dumps(content)}}]}


def test_openai_provider_carries_resolved_pass_request_to_exact_vllm_wire() -> None:
    async def run() -> None:
        bodies: list[dict[str, object]] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            bodies.append(body)
            return httpx.Response(200, json=_completion("relaylm_cognitive_output"))

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = OpenAICompatibleProvider(
            base_url="http://provider.test/v1",
            model="gemma-4-12B-it-qat-w4a16",
            decoding_config=OpenAICompatibleDecodingConfig(
                temperature=0.7,
                top_p=0.9,
                seed=7,
            ),
            decoding_capabilities=OpenAICompatibleDecodingCapabilities(
                frozenset({"temperature", "top_p", "seed"})
            ),
            vllm_reasoning_capability=_capability(),
            http_client=client,
        )
        try:
            await provider.generate(
                _cognitive_input(),
                pass_request=CognitionPassRequest(
                    reasoning_mode=CognitionReasoningMode.OFF,
                    temperature=0,
                    top_p=1,
                ),
            )
        finally:
            await client.aclose()

        assert len(bodies) == 1
        body = bodies[0]
        assert "response_format" not in body
        assert "RelayLM combined cognitive IR contract" in body["messages"][0]["content"]
        assert body["reasoning_effort"] == "none"
        assert "chat_template_kwargs" not in body
        assert "thinking_token_budget" not in body
        assert body["temperature"] == 0
        assert body["top_p"] == 1
        assert body["seed"] == 7

    asyncio.run(run())


def test_two_pass_provider_carries_distinct_pass1_and_pass2_requests() -> None:
    async def run() -> None:
        bodies: list[dict[str, object]] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            bodies.append(body)
            if len(bodies) == 1:
                return httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": "hello"}}]},
                )
            return httpx.Response(
                200,
                json=_completion("relaylm_structured_cognition_output"),
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = OpenAICompatibleTwoPassProvider(
            base_url="http://provider.test/v1",
            model="gemma-4-12B-it-qat-w4a16",
            decoding_capabilities=OpenAICompatibleDecodingCapabilities(
                frozenset({"temperature", "top_p"})
            ),
            vllm_reasoning_capability=_capability(),
            http_client=client,
        )
        cognitive_input = _cognitive_input()
        try:
            conversation = await provider.generate_conversation(
                cognitive_input,
                pass_request=CognitionPassRequest(
                    reasoning_mode=CognitionReasoningMode.OFF,
                    temperature=0,
                    top_p=1,
                ),
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=cognitive_input,
                    assistant_response=conversation.response,
                ),
                pass_request=CognitionPassRequest(
                    reasoning_mode=CognitionReasoningMode.BOUNDED,
                    reasoning_budget=64,
                    temperature=0,
                    top_p=1,
                ),
            )
        finally:
            await client.aclose()

        assert "response_format" not in bodies[0]
        assert "response_format" not in bodies[1]
        assert bodies[0]["reasoning_effort"] == "none"
        assert "thinking_token_budget" not in bodies[0]
        assert bodies[1]["thinking_token_budget"] == 64
        assert bodies[1]["chat_template_kwargs"] == {"enable_thinking": True}
        assert "reasoning_effort" not in bodies[1]

    asyncio.run(run())


def test_pass_request_rejects_unsupported_max_output_before_network() -> None:
    async def run() -> None:
        calls = 0

        async def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            raise AssertionError("network must not be reached")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = OpenAICompatibleProvider(
            base_url="http://provider.test/v1",
            model="gemma-4-12B-it-qat-w4a16",
            vllm_reasoning_capability=_capability(),
            http_client=client,
        )
        try:
            with pytest.raises(
                CognitionExecutionCapabilityError,
                match="max_output_tokens",
            ):
                await provider.generate(
                    _cognitive_input(),
                    pass_request=CognitionPassRequest(max_output_tokens=128),
                )
        finally:
            await client.aclose()
        assert calls == 0

    asyncio.run(run())


class _SinglePassSpyProvider:
    def __init__(self) -> None:
        self.pass_requests: list[CognitionPassRequest | None] = []

    async def generate(self, cognitive_input, *, pass_request=None):
        self.pass_requests.append(pass_request)
        return CognitiveOutput(response="visible")


class _TwoPassSpyProvider:
    def __init__(self) -> None:
        self.pass1_requests: list[CognitionPassRequest | None] = []
        self.pass2_requests: list[CognitionPassRequest | None] = []

    async def generate_conversation(self, _, *, pass_request=None):
        self.pass1_requests.append(pass_request)
        return CognitionConversationOutput(response="visible")

    async def stream_generate_conversation(
        self,
        _,
        emit_response_delta,
        *,
        pass_request=None,
    ):
        self.pass1_requests.append(pass_request)
        await emit_response_delta("visible")
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(self, _, *, pass_request=None):
        self.pass2_requests.append(pass_request)
        return CognitionExtractionOutput()


def test_turn_runtime_passes_resolved_requests_to_single_and_two_pass_providers(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        single_character = _make_character(tmp_path / "single")
        single_provider = _SinglePassSpyProvider()
        off = CognitionPassRequest(reasoning_mode=CognitionReasoningMode.OFF)
        single = await run_user_turn(
            character=single_character,
            provider=single_provider,
            content="hello",
            pass_request=off,
        )
        assert single.response == "visible"
        assert single_provider.pass_requests == [off]

        two_character = _make_character(tmp_path / "two")
        two_provider = _TwoPassSpyProvider()
        bounded = CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.BOUNDED,
            reasoning_budget=64,
        )
        two = await run_user_turn_two_pass(
            character=two_character,
            provider=two_provider,
            content="hello",
            execution_runtime=CognitionExecutionRuntime(),
            pass1_request=off,
            pass2_request=bounded,
        )
        extraction = await two.extraction
        assert extraction.status.value == "committed"
        assert two_provider.pass1_requests == [off]
        assert two_provider.pass2_requests == [bounded]

        streaming_character = _make_character(tmp_path / "streaming")
        streaming_provider = _TwoPassSpyProvider()
        deltas: list[str] = []

        async def emit_response_delta(delta: str) -> None:
            deltas.append(delta)

        streaming = await run_user_turn_two_pass_streaming(
            character=streaming_character,
            provider=streaming_provider,
            content="hello",
            emit_response_delta=emit_response_delta,
            execution_runtime=CognitionExecutionRuntime(),
            pass1_request=off,
            pass2_request=bounded,
        )
        streaming_extraction = await streaming.extraction
        assert streaming.response == "visible"
        assert deltas == ["visible"]
        assert streaming_extraction.status.value == "committed"
        assert streaming_provider.pass1_requests == [off]
        assert streaming_provider.pass2_requests == [bounded]

    asyncio.run(run())
