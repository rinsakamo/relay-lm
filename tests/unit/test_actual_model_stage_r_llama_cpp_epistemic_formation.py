from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest

import relaylm.actual_model_stage_r_llama_cpp_epistemic_formation as host
from relaylm.actual_model_epistemic_formation_diagnostic import (
    build_t2_epistemic_formation_input,
)
from relaylm.actual_model_stage_r_semantics import (
    CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH,
    load_current_stage_r_scenario_set,
    load_stage_r_semantic_authority,
)
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.providers.llama_cpp_reasoning import LlamaCppReasoningCapabilityAttestation
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity
from relaylm.storage.filesystem import CharacterDirectory


REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _input():
    authority = load_stage_r_semantic_authority(
        REPO_ROOT / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
    )
    scenario_set = load_current_stage_r_scenario_set(
        repo_root=REPO_ROOT,
        authority=authority,
    )
    fixture = CharacterDirectory(REPO_ROOT / "evaluation/actual_model/characters/foundation-v1")
    return build_t2_epistemic_formation_input(
        identity=fixture.load_identity(),
        state=fixture.load_state(),
        scenario=scenario_set.scenario("continuity-lifecycle-v1").scenario,
        scenario_set_revision=authority.scenario_set_revision,
    )


def _provider(tmp_path: Path, client: httpx.AsyncClient, counter: RecordingCounter):
    return host.EpistemicFormationLlamaProvider(
        base_url="http://llama.test/v1",
        model="gemma-local",
        http_client=client,
        llama_cpp_reasoning_capability=LlamaCppReasoningCapabilityAttestation(
            request_model="gemma-local",
            enable_thinking_supported=True,
        ),
        input_counter=counter,
        observation_root=tmp_path / "completion",
        raw_observation_root=tmp_path / "raw",
        request_body_root=tmp_path / "requests",
    )


def test_provider_posts_counted_final_body_and_retains_raw_output(tmp_path: Path) -> None:
    cognitive_input = _input()
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
                                {
                                    "items": [
                                        {
                                            "subject_span": "それの中身",
                                            "unknown_evidence_span": "まだ開けていない",
                                            "source_event_id": cognitive_input.input.id,
                                        }
                                    ]
                                },
                                ensure_ascii=False,
                            )
                        },
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

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider(tmp_path, client, counter)
            try:
                return await provider.generate_epistemic_formation(
                    cognitive_input,
                    pass_request=CognitionPassRequest(
                        reasoning_mode=CognitionReasoningMode.OFF,
                        structured_output_mode=CognitionStructuredOutputMode.NATIVE,
                    ),
                ), provider
            except Exception:
                await provider.aclose()
                raise

    output, provider = asyncio.run(run())
    assert len(seen) == 1
    assert counter.seen == seen
    body = seen[0]
    assert body["reasoning_effort"] == "none"
    assert body["stream"] is False
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert len(output.items) == 1
    assert output.completion.reasoning_tokens == 0
    prompt = body["messages"][0]["content"] + body["messages"][1]["content"]
    instruction = prompt.split("</CURRENT_INPUT>\n\n", 1)[-1]
    for term in (
        "unresolved",
        "open_question",
        "Continuity",
        "continuity_candidate",
        "set",
        "resolve",
        "blue_box",
        "box_contents_question",
    ):
        assert term not in instruction

    request_artifacts = sorted((tmp_path / "requests").glob("*.json"))
    raw_artifacts = sorted((tmp_path / "raw").glob("*.json"))
    assert len(request_artifacts) == 1
    assert len(raw_artifacts) == 1
    assert json.loads(request_artifacts[0].read_text(encoding="utf-8")) == body
    raw = json.loads(raw_artifacts[0].read_text(encoding="utf-8"))
    assert raw["raw_completion"]["content"]
    assert raw["semantic_review"] == "not_run"
    assert len(provider.input_count_artifacts) == 1
    assert len(provider.completion_artifacts) == 1
    asyncio.run(provider.aclose())


def test_invalid_native_output_is_retained_before_protocol_failure(tmp_path: Path) -> None:
    cognitive_input = _input()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": '{"items":[],"extra":true}'},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    async def run() -> tuple[Path, ...]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider(tmp_path, client, RecordingCounter())
            try:
                with pytest.raises(ProviderProtocolError):
                    await provider.generate_epistemic_formation(
                        cognitive_input,
                        pass_request=CognitionPassRequest(
                            reasoning_mode=CognitionReasoningMode.OFF,
                            structured_output_mode=CognitionStructuredOutputMode.NATIVE,
                        ),
                    )
                return tuple(provider.raw_observation_artifacts)
            finally:
                await provider.aclose()

    raw_paths = asyncio.run(run())
    assert len(raw_paths) == 1
    raw = json.loads(raw_paths[0].read_text(encoding="utf-8"))
    assert raw["raw_completion"]["content"] == '{"items":[],"extra":true}'
    assert raw["semantic_review"] == "not_run"


def test_host_preflight_failure_does_not_construct_provider_or_call_server(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server_log = tmp_path / "server.log"
    server_log.write_text("", encoding="utf-8")
    monkeypatch.setattr(host, "_require_clean_repo", lambda _repo_root: None)
    monkeypatch.setattr(host, "_git_identity", lambda _repo_root: ("a" * 40, "b" * 40))
    monkeypatch.setattr(host, "_frozen_core_fingerprint", lambda _repo_root: "sha256:" + "c" * 64)

    def fail_preflight(**_kwargs):
        raise host.LlamaCppStageRQualificationError("test preflight stop")

    monkeypatch.setattr(host, "_prepare_physical_condition", fail_preflight)
    result = host.main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--provider-base-url",
            "http://127.0.0.1:1234/v1",
            "--request-model",
            "gemma-local",
            "--artifact-path",
            str(tmp_path / "model.gguf"),
            "--llama-upstream-revision",
            "d" * 40,
            "--llama-version",
            "0.0-test",
            "--expected-build-number",
            "1",
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
    )
    assert result == 2
    summary = json.loads(
        (tmp_path / "artifacts" / "epistemic-formation-t2-summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["diagnostic_generation_count"] == 0
    assert summary["t3_generation_count"] == 0
