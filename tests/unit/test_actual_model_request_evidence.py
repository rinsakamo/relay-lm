from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import AsyncIterator

import httpx
import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import (
    ActualModelCognitionPassRequests,
    ActualModelRunManifest,
)
from relaylm.actual_model_execution import run_actual_model_scenario_definition
from relaylm.actual_model_execution_artifacts import (
    ActualModelExecutionArtifactError,
    load_actual_model_execution_mapping,
    write_actual_model_execution_result,
)
from relaylm.actual_model_request_evidence import (
    ActualModelRequestEvidence,
    ActualModelRequestEvidenceRecorder,
)
from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionStructuredOutputMode,
)
from relaylm.cognition_execution_evidence import (
    BUFFERED_EXECUTION_PATH,
    CognitionExecutionEvidenceIdentity,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderProtocolError,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


_REPO_ROOT = Path(__file__).parents[2]
_SCENARIO_SET_PATH = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "scenario_sets"
    / "foundation-v1.json"
)
_FIXTURE_ROOT = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "characters"
    / "foundation-v1"
)


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# Eval\nBe grounded."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(
            StateRecord(
                state_id="state-1",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=("event-old",),
            ),
        ),
        context=(
            ContextItem(
                content="Earlier assistant response",
                sources=("event-assistant",),
                actor="assistant",
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "いまの入力"},
            event_id="event-now",
            timestamp="2026-08-30T00:00:00+00:00",
        ),
    )


def _recorder() -> ActualModelRequestEvidenceRecorder:
    return ActualModelRequestEvidenceRecorder(
        execution_id="amx-" + "a" * 64,
        run_id="amr-" + "b" * 64,
        scenario_id="request-evidence-v1",
        scenario_revision="sha256:scenario-revision",
        provider_identity="provider-v1",
        adapter_identity="openai_compatible",
    )


def _two_pass_provider(
    handler,
    *,
    api_key: str | None = None,
    decoding_config: OpenAICompatibleDecodingConfig | None = None,
    decoding_capabilities: OpenAICompatibleDecodingCapabilities | None = None,
) -> OpenAICompatibleTwoPassProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAICompatibleTwoPassProvider(
        base_url="http://provider.test/v1",
        model="gemma-test",
        api_key=api_key,
        decoding_config=decoding_config,
        decoding_capabilities=decoding_capabilities,
        http_client=client,
    )


def _single_pass_provider(handler) -> OpenAICompatibleProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAICompatibleProvider(
        base_url="http://provider.test/v1",
        model="gemma-test",
        http_client=client,
    )


def _conversation_response(content: str = "pass one response") -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}}]},
    )


def _single_pass_response(content: str = "single response") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "utterance": content,
                                "state_candidates": [],
                                "continuity_candidates": [],
                            },
                            ensure_ascii=False,
                        )
                    },
                    "finish_reason": "stop",
                }
            ]
        },
    )


def _empty_extraction_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"state_candidates": [], "continuity_candidates": []}
                        )
                    },
                    "finish_reason": "stop",
                }
            ]
        },
    )


class _StaticSSEStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


class _DelegateProvider:
    def __init__(self, delegate: OpenAICompatibleTwoPassProvider) -> None:
        self._delegate = delegate

    async def generate_conversation(self, cognitive_input: CognitiveInput) -> object:
        return await self._delegate.generate_conversation(cognitive_input)


def _sse_chunk(*, content: str, finish_reason: str | None = None) -> bytes:
    return (
        "data: "
        + json.dumps(
            {
                "choices": [
                    {
                        "delta": {"content": content},
                        "finish_reason": finish_reason,
                    }
                ]
            },
            ensure_ascii=False,
        )
        + "\n\n"
    ).encode("utf-8")


def test_buffered_single_pass_request_is_captured_at_transport_boundary() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return _single_pass_response()

    async def run() -> tuple[ActualModelRequestEvidence, ...]:
        provider = _single_pass_provider(handler)
        recorder = _recorder()
        try:
            with recorder.capture(turn_index=1, pass_identity="single_pass"):
                await provider.generate(_cognitive_input())
        finally:
            await provider.aclose()
        return recorder.records

    records = asyncio.run(run())
    assert len(records) == 1
    assert records[0].pass_identity == "single_pass"
    assert records[0].request_body == seen[0]
    assert records[0].request_body["stream"] is False


def test_streaming_single_pass_request_is_captured_at_transport_boundary() -> None:
    wire = json.dumps(
        {
            "utterance": "streamed response",
            "state_candidates": [],
            "continuity_candidates": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_StaticSSEStream(
                [
                    _sse_chunk(content=wire, finish_reason="stop"),
                    b"data: [DONE]\n\n",
                ]
            ),
        )

    async def run() -> tuple[tuple[ActualModelRequestEvidence, ...], list[str]]:
        provider = _single_pass_provider(handler)
        recorder = _recorder()
        emitted: list[str] = []

        async def emit(content: str) -> None:
            emitted.append(content)

        try:
            with recorder.capture(turn_index=2, pass_identity="single_pass"):
                await provider.stream_generate(_cognitive_input(), emit)
        finally:
            await provider.aclose()
        return recorder.records, emitted

    records, emitted = asyncio.run(run())
    assert len(records) == 1
    assert records[0].request_body["stream"] is True
    assert "".join(emitted) == "streamed response"


def test_buffered_pass1_exact_request_evidence_is_captured_at_transport_boundary() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        assert body["stream"] is False
        return _conversation_response()

    async def run() -> tuple[ActualModelRequestEvidence, ...]:
        provider = _two_pass_provider(handler)
        recorder = _recorder()
        try:
            with recorder.capture(turn_index=1, pass_identity="pass1"):
                await provider.generate_conversation(
                    _cognitive_input(),
                    pass_request=CognitionPassRequest(),
                )
        finally:
            await provider.aclose()
        return recorder.records

    records = asyncio.run(run())
    assert len(records) == 1
    assert records[0].request_body == seen[0]
    assert records[0].pass_identity == "pass1"
    assert records[0].request_body["model"] == "gemma-test"
    assert records[0].request_body["messages"][1]["content"].startswith(
        "<COGNITIVE_INPUT>\n"
    )
    assert '"event_id":"event-now"' in records[0].request_body["messages"][1]["content"]


def test_buffered_pass2_exact_request_evidence_includes_serialized_input_and_schema() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        assert body["stream"] is False
        return _empty_extraction_response()

    async def run() -> tuple[ActualModelRequestEvidence, ...]:
        provider = _two_pass_provider(handler)
        recorder = _recorder()
        try:
            with recorder.capture(turn_index=3, pass_identity="pass2"):
                await provider.generate_extraction(
                    CognitionExtractionInput(
                        cognitive_input=_cognitive_input(),
                        assistant_response="pass one response",
                    ),
                    pass_request=CognitionPassRequest(
                        structured_output_mode=CognitionStructuredOutputMode.NATIVE
                    ),
                )
        finally:
            await provider.aclose()
        return recorder.records

    records = asyncio.run(run())
    assert len(records) == 1
    body = records[0].request_body
    assert body == seen[0]
    assert records[0].pass_identity == "pass2"
    assert body["messages"][1]["content"].startswith("<COGNITIVE_INPUT>\n")
    assert '"event_id":"event-now"' in body["messages"][1]["content"]
    assert body["response_format"]["type"] == "json_schema"
    assert "pass one response" in body["messages"][1]["content"]


def test_streaming_pass1_exact_request_evidence_is_captured_at_transport_boundary() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_StaticSSEStream(
                [
                    _sse_chunk(content="streamed response", finish_reason="stop"),
                    b"data: [DONE]\n\n",
                ]
            ),
        )

    async def run() -> tuple[tuple[ActualModelRequestEvidence, ...], list[str]]:
        provider = _two_pass_provider(handler)
        recorder = _recorder()
        emitted: list[str] = []

        async def emit(content: str) -> None:
            emitted.append(content)

        try:
            with recorder.capture(turn_index=2, pass_identity="pass1"):
                await provider.stream_generate_conversation(
                    _cognitive_input(),
                    emit,
                    pass_request=CognitionPassRequest(),
                )
        finally:
            await provider.aclose()
        return recorder.records, emitted

    records, emitted = asyncio.run(run())
    assert emitted == ["streamed response"]
    assert len(records) == 1
    assert records[0].pass_identity == "pass1"
    assert records[0].request_body["stream"] is True


def test_delegate_needs_no_capture_installation_or_client_replacement() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return _conversation_response("delegated response")

    async def run() -> tuple[tuple[ActualModelRequestEvidence, ...], bool]:
        provider = _two_pass_provider(handler)
        original_client = provider._client
        delegated = _DelegateProvider(provider)
        recorder = _recorder()
        try:
            with recorder.capture(turn_index=1, pass_identity="pass1"):
                await delegated.generate_conversation(_cognitive_input())
            return recorder.records, provider._client is original_client
        finally:
            await provider.aclose()

    records, client_unchanged = asyncio.run(run())
    assert len(records) == 1
    assert records[0].request_body["model"] == "gemma-test"
    assert client_unchanged is True


def test_no_request_evidence_is_captured_outside_active_scope() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return _conversation_response()

    async def run() -> tuple[ActualModelRequestEvidence, ...]:
        provider = _two_pass_provider(handler)
        recorder = _recorder()
        try:
            await provider.generate_conversation(_cognitive_input())
        finally:
            await provider.aclose()
        return recorder.records

    assert asyncio.run(run()) == ()


def test_request_evidence_preserves_generation_controls_realized_by_provider() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["temperature"] == 0.0
        assert body["top_p"] == 1.0
        assert body["seed"] == 17
        assert body["max_tokens"] == 41
        return _conversation_response("controlled response")

    async def run() -> tuple[ActualModelRequestEvidence, ...]:
        provider = _two_pass_provider(
            handler,
            decoding_config=OpenAICompatibleDecodingConfig(
                temperature=0.2,
                top_p=0.8,
                seed=17,
                max_output_tokens=99,
            ),
            decoding_capabilities=OpenAICompatibleDecodingCapabilities(
                supported_controls=frozenset(
                    {"temperature", "top_p", "seed", "max_output_tokens"}
                )
            ),
        )
        recorder = _recorder()
        try:
            with recorder.capture(turn_index=1, pass_identity="pass1"):
                await provider.generate_conversation(
                    _cognitive_input(),
                    pass_request=CognitionPassRequest(
                        temperature=0.0,
                        top_p=1.0,
                        max_output_tokens=41,
                    ),
                )
        finally:
            await provider.aclose()
        return recorder.records

    body = asyncio.run(run())[0].request_body
    assert body["temperature"] == 0.0
    assert body["top_p"] == 1.0
    assert body["seed"] == 17
    assert body["max_tokens"] == 41


def test_request_evidence_is_bound_to_execution_scenario_turn_and_pass() -> None:
    recorder = _recorder()
    record = recorder.record(
        turn_index=7,
        pass_identity="pass2",
        request_body={
            "model": "gemma-test",
            "messages": [{"role": "user", "content": "exact"}],
            "stream": False,
        },
    )

    mapping = record.to_mapping()
    assert mapping["execution_id"] == "amx-" + "a" * 64
    assert mapping["run_id"] == "amr-" + "b" * 64
    assert mapping["scenario"] == {
        "id": "request-evidence-v1",
        "revision": "sha256:scenario-revision",
    }
    assert mapping["turn_index"] == 7
    assert mapping["pass"] == "pass2"


def test_request_material_changes_body_hash_and_stable_evidence_id() -> None:
    common = {
        "execution_id": "amx-" + "a" * 64,
        "run_id": "amr-" + "b" * 64,
        "scenario_id": "request-evidence-v1",
        "scenario_revision": "sha256:scenario-revision",
        "turn_index": 1,
        "pass_identity": "pass1",
        "request_ordinal": 1,
        "provider_identity": "provider-v1",
        "adapter_identity": "openai_compatible",
    }
    first = ActualModelRequestEvidence.create(
        **common,
        request_body={"model": "gemma-test", "messages": [], "stream": False},
    )
    second = ActualModelRequestEvidence.create(
        **common,
        request_body={"model": "gemma-test", "messages": [], "stream": True},
    )
    assert first.request_body_sha256 != second.request_body_sha256
    assert first.evidence_id != second.evidence_id


def test_request_evidence_never_contains_authentication_material() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return _conversation_response("safe response")

    async def run() -> tuple[ActualModelRequestEvidence, ...]:
        provider = _two_pass_provider(handler, api_key="super-secret-api-key")
        recorder = _recorder()
        try:
            with recorder.capture(turn_index=1, pass_identity="pass1"):
                await provider.generate_conversation(_cognitive_input())
        finally:
            await provider.aclose()
        return recorder.records

    records = asyncio.run(run())
    serialized = json.dumps(records[0].to_mapping(), ensure_ascii=False)
    assert "super-secret-api-key" not in serialized
    assert "Authorization" not in serialized
    assert "headers" not in records[0].to_mapping()


def test_attempted_request_remains_available_and_annotated_when_provider_fails() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "provider unavailable"})

    async def run() -> tuple[ActualModelRequestEvidence, ...]:
        provider = _two_pass_provider(handler)
        recorder = _recorder()
        try:
            with recorder.capture(turn_index=2, pass_identity="pass2"):
                with pytest.raises(ProviderProtocolError):
                    await provider.generate_extraction(
                        CognitionExtractionInput(
                            cognitive_input=_cognitive_input(),
                            assistant_response="pass one response",
                        )
                    )
        finally:
            await provider.aclose()
        return recorder.records

    records = asyncio.run(run())
    assert len(records) == 1
    assert records[0].attempted is True
    assert records[0].failure_exception_type == "ProviderProtocolError"
    assert records[0].failure_exception_message is not None
    assert "status=503" in records[0].failure_exception_message


def test_request_evidence_source_has_no_runtime_client_replacement() -> None:
    source = (
        _REPO_ROOT / "src" / "relaylm" / "actual_model_request_evidence.py"
    ).read_text(encoding="utf-8")
    evaluation = (
        _REPO_ROOT / "src" / "relaylm" / "actual_model_evaluation.py"
    ).read_text(encoding="utf-8")
    joined = source + "\n" + evaluation
    assert "install_model_facing_request_capture" not in joined
    assert "_CapturingAsyncClient" not in joined
    assert 'setattr(current, "_client"' not in joined
    assert "setattr(current, '_client'" not in joined


def test_historical_execution_artifact_remains_loadable(tmp_path: Path) -> None:
    legacy = tmp_path / "historical.json"
    legacy.write_text(
        json.dumps(
            {
                "format_version": 1,
                "execution_id": "amx-historical",
                "evidence": {"format_version": 1, "turns": []},
            }
        ),
        encoding="utf-8",
    )
    assert load_actual_model_execution_mapping(legacy)["execution_id"] == "amx-historical"


def _two_pass_execution_manifest() -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="a" * 40,
        character_fixture_id="actual-model-foundation-v1",
        character_fixture_revision=character_fixture_revision(_FIXTURE_ROOT),
        provider_identity="provider-v1",
        adapter_identity="openai_compatible",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v1",
        condition_id="request-evidence-test",
        execution_path=BUFFERED_EXECUTION_PATH,
        provider_capabilities=("state_candidates",),
        cognition_execution=CognitionExecutionEvidenceIdentity.two_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        ),
        cognition_pass_requests=ActualModelCognitionPassRequests.two_pass(
            pass1=CognitionPassRequest(),
            pass2=CognitionPassRequest(),
        ),
    )


def test_execution_artifact_traverses_to_exact_pass_requests_without_filename_guessing(
    tmp_path: Path,
) -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if "<PASS>\nCONVERSATION" in body["messages"][1]["content"]:
            return _conversation_response("pass one")
        return _empty_extraction_response()

    async def run():
        provider = _two_pass_provider(handler)
        try:
            return await run_actual_model_scenario_definition(
                scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
                scenario_id="response-persona-correction-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "workspace",
                provider=provider,
                manifest=_two_pass_execution_manifest(),
            )
        finally:
            await provider.aclose()

    result = asyncio.run(run())
    path = write_actual_model_execution_result(
        result=result,
        artifact_root=tmp_path / "artifacts",
    )
    loaded = load_actual_model_execution_mapping(path)
    loaded_turn = loaded["evidence"]["turns"][0]
    requests = loaded_turn["request_evidence"]
    assert [item["pass"] for item in requests] == ["pass1", "pass2"]
    assert [item["request_body"] for item in requests] == seen[:2]
    for item in requests:
        assert item["execution_id"] == loaded["execution_id"]
        assert item["run_id"] == loaded["evidence"]["run_id"]
        assert item["scenario"] == {
            "id": "response-persona-correction-v1",
            "revision": result.plan.scenario_set_revision,
        }
    assert '"event_id":"' in requests[0]["request_body"]["messages"][1]["content"]

    missing_request_turn = replace(result.evidence.turns[0], request_evidence=())
    missing_request_result = replace(
        result,
        evidence=replace(
            result.evidence,
            turns=(missing_request_turn, *result.evidence.turns[1:]),
        ),
    )
    with pytest.raises(
        ActualModelExecutionArtifactError,
        match="missing the exact canonical provider request evidence",
    ):
        write_actual_model_execution_result(
            result=missing_request_result,
            artifact_root=tmp_path / "missing-request-artifacts",
        )

    assert write_actual_model_execution_result(
        result=result,
        artifact_root=tmp_path / "artifacts",
    ) == path
    first_request, second_request = result.evidence.turns[0].request_evidence
    changed_request = ActualModelRequestEvidence.create(
        execution_id=first_request.execution_id,
        run_id=first_request.run_id,
        scenario_id=first_request.scenario_id,
        scenario_revision=first_request.scenario_revision,
        turn_index=first_request.turn_index,
        pass_identity=first_request.pass_identity,
        request_ordinal=first_request.request_ordinal,
        provider_identity=first_request.provider_identity,
        adapter_identity=first_request.adapter_identity,
        request_body={**first_request.request_body, "stream": True},
    )
    changed_turn = replace(
        result.evidence.turns[0],
        request_evidence=(changed_request, second_request),
    )
    conflicting = replace(
        result,
        evidence=replace(
            result.evidence,
            turns=(changed_turn, *result.evidence.turns[1:]),
        ),
    )
    with pytest.raises(
        ActualModelExecutionArtifactError,
        match="distinct replicate_id",
    ):
        write_actual_model_execution_result(
            result=conflicting,
            artifact_root=tmp_path / "artifacts",
        )


def test_failed_pass1_attempt_is_persisted_without_fabricating_completion(
    tmp_path: Path,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "provider unavailable"})

    async def run():
        provider = _two_pass_provider(handler)
        try:
            return await run_actual_model_scenario_definition(
                scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
                scenario_id="response-persona-correction-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "workspace",
                provider=provider,
                manifest=_two_pass_execution_manifest(),
            )
        finally:
            await provider.aclose()

    result = asyncio.run(run())
    assert result.evidence.turns == ()
    assert result.evidence.request_failure is not None
    path = write_actual_model_execution_result(
        result=result,
        artifact_root=tmp_path / "artifacts",
    )
    loaded = load_actual_model_execution_mapping(path)
    failure = loaded["evidence"]["request_failure"]
    assert failure["pass"] == "pass1"
    assert len(failure["request_evidence"]) == 1
    assert failure["request_evidence"][0]["execution_id"] == loaded["execution_id"]


def test_failed_pass2_attempt_keeps_prior_and_failing_requests_without_fabricating_proposals(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        body = json.loads(request.content)
        if calls == 1:
            assert "<PASS>\nCONVERSATION" in body["messages"][1]["content"]
            return _conversation_response("pass one")
        return httpx.Response(503, json={"error": "provider unavailable"})

    async def run():
        provider = _two_pass_provider(handler)
        try:
            return await run_actual_model_scenario_definition(
                scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
                scenario_id="response-persona-correction-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "workspace",
                provider=provider,
                manifest=_two_pass_execution_manifest(),
            )
        finally:
            await provider.aclose()

    result = asyncio.run(run())
    assert len(result.evidence.turns) == 1
    turn = result.evidence.turns[0]
    assert [item.pass_identity for item in turn.request_evidence] == ["pass1", "pass2"]
    assert turn.cognition_execution is not None
    assert turn.cognition_execution.pass2_status == "failed"
    assert turn.raw_model.response == "pass one"
    path = write_actual_model_execution_result(
        result=result,
        artifact_root=tmp_path / "artifacts",
    )
    loaded = load_actual_model_execution_mapping(path)
    loaded_requests = loaded["evidence"]["turns"][0]["request_evidence"]
    assert [item["pass"] for item in loaded_requests] == ["pass1", "pass2"]
