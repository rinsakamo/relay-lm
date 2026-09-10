from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest

import relaylm.actual_model_stage_r_llama_cpp_continuity_label_invariance as host
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity
from relaylm.state import STATE_CLASS_DEFINITIONS


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe precise."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(
            ContextItem(
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
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={
                "content": "Keep the literal word unresolved in this user Input."
            },
            event_id="evt-now",
            timestamp="2026-09-09T00:00:00+00:00",
        ),
    )


def _wire(*, op: str = "set", source: str = "evt-now") -> dict[str, object]:
    return {
        "state_candidates": [],
        "continuity_decisions": {
            "referent": {"decision": "none", "transitions": []},
            "open_question": {
                "decision": "emit",
                "transitions": [
                    {
                        "kind": "open_question",
                        "key": "document_author",
                        "op": op,
                        "value": None if op == "resolve" else "author not yet known",
                        "sources": [source],
                        "epistemic_role": "user_assertion",
                    }
                ],
            },
            "active_task": {"decision": "none", "transitions": []},
        },
    }


class RecordingCounter:
    evidence_identity = SerializedInputCounterIdentity(
        capability="test.llama.input",
        implementation="test-counter",
        version="1",
        mode=TokenCountMode.EXACT,
        tokenizer_identity="test-tokenizer",
    )

    def __init__(self) -> None:
        self.seen: list[dict[str, object]] = []

    def count_input(self, model_input: dict[str, object]) -> SerializedInputTokenCount:
        self.seen.append(copy.deepcopy(model_input))
        return SerializedInputTokenCount(
            total_input_tokens=100,
            required_input_framing_tokens=20,
            mode=TokenCountMode.EXACT,
        )


def test_llama_provider_counts_and_posts_the_actual_aliased_body(tmp_path: Path) -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
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

    counter = RecordingCounter()

    async def run() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = host.ContinuityLabelInvarianceLlamaProvider(
                base_url="http://llama.test/v1",
                model="gemma-local",
                http_client=client,
                llama_cpp_reasoning_capability=host.LlamaCppReasoningCapabilityAttestation(
                    request_model="gemma-local",
                    enable_thinking_supported=True,
                ),
                input_counter=counter,
                observation_root=tmp_path / "completion",
                label_observation_root=tmp_path / "labels",
            )
            try:
                return await provider.generate_extraction(
                    CognitionExtractionInput(
                        cognitive_input=_cognitive_input(),
                        assistant_response="Pass 1 retains unresolved as authored text.",
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
    assert counter.seen == seen
    body = seen[0]
    assert body["reasoning_effort"] == "none"
    assert body["stream"] is False
    assert body["response_format"]["json_schema"]["name"] == (
        "relaylm_continuity_label_invariance_diagnostic"
    )
    prompt = body["messages"][1]["content"]
    assert "open_question" in prompt
    assert "Keep the literal word unresolved in this user Input." in prompt
    assert "Pass 1 retains unresolved as authored text." in prompt
    assert len(output.continuity_candidates) == 1
    assert output.continuity_candidates[0].kind == "unresolved"
    assert output.completion.reasoning_tokens == 0

    label_files = sorted((tmp_path / "labels").glob("*.json"))
    completion_files = sorted((tmp_path / "completion").glob("*.json"))
    assert len(label_files) == 1
    assert len(completion_files) == 2
    label_observation = json.loads(label_files[0].read_text(encoding="utf-8"))
    assert label_observation["continuity_decisions"]["open_question"][
        "transitions"
    ][0]["kind"] == "open_question"
    assert all(label_files[0] != path for path in completion_files)


def test_llama_provider_rejects_invalid_source_after_shadow_translation(
    tmp_path: Path,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": json.dumps(_wire(source="evt-other"))},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = host.ContinuityLabelInvarianceLlamaProvider(
                base_url="http://llama.test/v1",
                model="gemma-local",
                http_client=client,
                llama_cpp_reasoning_capability=host.LlamaCppReasoningCapabilityAttestation(
                    request_model="gemma-local",
                    enable_thinking_supported=True,
                ),
                input_counter=RecordingCounter(),
                observation_root=tmp_path / "completion",
                label_observation_root=tmp_path / "labels",
            )
            try:
                with pytest.raises(ProviderProtocolError, match="source"):
                    await provider.generate_extraction(
                        CognitionExtractionInput(
                            cognitive_input=_cognitive_input(),
                            assistant_response="A response.",
                        ),
                        pass_request=CognitionPassRequest(
                            reasoning_mode=CognitionReasoningMode.OFF,
                            structured_output_mode=CognitionStructuredOutputMode.NATIVE,
                        ),
                    )
            finally:
                await provider.aclose()

    asyncio.run(run())
    assert not list((tmp_path / "labels").glob("*.json"))


def test_diagnostic_host_preflight_failure_never_reaches_provider_or_server(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server_log = tmp_path / "server.log"
    server_log.write_text("", encoding="utf-8")
    argv = [
        "--repo-root",
        str(tmp_path / "repo"),
        "--provider-base-url",
        "http://127.0.0.1:1234/v1",
        "--request-model",
        "gemma-local",
        "--artifact-path",
        str(tmp_path / "model.gguf"),
        "--llama-upstream-revision",
        "d" * 40,
        "--llama-version",
        "0.4.0-dev",
        "--expected-build-number",
        "10874",
        "--expected-context-window",
        "8192",
        "--expected-slots",
        "1",
        "--context-shift-disabled",
        "--server-log-path",
        str(server_log),
        "--workspace-root",
        str(tmp_path / "workspace"),
        "--artifact-root",
        str(tmp_path / "artifacts"),
    ]
    monkeypatch.setattr(host, "_require_clean_repo", lambda _root: None)
    monkeypatch.setattr(host, "_git_identity", lambda _root: ("a" * 40, "b" * 40))
    monkeypatch.setattr(host, "_frozen_core_fingerprint", lambda _root: "sha256:" + "c" * 64)

    def fail_preflight(**_kwargs: object) -> object:
        raise host.LlamaCppStageRQualificationError("preflight blocked")

    monkeypatch.setattr(host, "_prepare_physical_condition", fail_preflight)
    result = host.main(argv)

    assert result == 2
    summary = json.loads(
        (tmp_path / "artifacts" / "stage-r-llama-cpp-summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["diagnostic"] == host.DIAGNOSTIC_NAME
    assert summary["classification"] == "INFRA_INVALID"
    assert summary["semantic_execution_started"] is False
