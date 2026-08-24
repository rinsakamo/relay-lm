from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ActualModelScenario,
    ExplicitBudgetConfiguration,
    run_actual_model_scenario,
)
from relaylm.cognition_execution_evidence import (
    BUFFERED_EXECUTION_PATH,
    CognitionExecutionEvidenceIdentity,
)
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Eval\n\nBe grounded.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: actual-eval\n  name: Eval\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _manifest() -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="a" * 40,
        character_fixture_id="actual-eval",
        character_fixture_revision="sha256:fixture-v1",
        provider_identity="openai-compatible-v1",
        adapter_identity="openai-compatible-two-pass-v1",
        model_artifact="model@sha256:111",
        tokenizer_identity="tokenizer-v1",
        effective_context_window=1616,
        decoding_configuration=(("temperature", 0.0), ("top_p", 1.0)),
        seed=None,
        structured_output_schema_version="relaylm-structured-cognition-output-v1",
        scenario_set_version="protocol-diagnostic-v1",
        condition_id="reference_baseline",
        budgets=ExplicitBudgetConfiguration(),
        execution_path="buffered",
        provider_capabilities=("state_candidates", "continuity_candidates"),
        cognition_execution=CognitionExecutionEvidenceIdentity.two_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        ),
    )


def _empty_extraction_wire() -> dict[str, object]:
    return {
        "turn_interpretation": {
            "user_meaning": [],
            "change_signals": [],
            "self_meaning": [],
            "assistant_effects": [],
            "unresolved": [],
            "continuity_signals": [],
        },
        "state_candidates": [],
        "continuity_candidates": [],
    }


def test_failed_pass2_retains_http_200_protocol_diagnostic_without_reusing_prior_turn(
    tmp_path: Path,
) -> None:
    extraction_calls = 0
    malformed_content = '{"turn_interpretation":'
    malformed_envelope = json.dumps(
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": malformed_content},
                }
            ],
            "usage": {
                "prompt_tokens": 1540,
                "completion_tokens": 76,
                "total_tokens": 1616,
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal extraction_calls
        body = json.loads(request.content)
        prompt = body["messages"][1]["content"]
        if "<PASS>\nCONVERSATION" in prompt:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "了解。"},
                        }
                    ]
                },
            )
        if "<PASS>\nEXTRACTION" in prompt:
            extraction_calls += 1
            if extraction_calls == 1:
                return httpx.Response(
                    200,
                    json={
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "content": json.dumps(
                                        _empty_extraction_wire(),
                                        ensure_ascii=False,
                                    )
                                },
                            }
                        ]
                    },
                )
            return httpx.Response(
                200,
                content=malformed_envelope.encode("utf-8"),
                headers={"content-type": "application/json"},
            )
        raise AssertionError(prompt)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://vllm.test/v1",
                model="gemma",
                http_client=client,
            )
            return await run_actual_model_scenario(
                character=_make_character(tmp_path),
                provider=provider,
                manifest=_manifest(),
                scenario=ActualModelScenario(
                    scenario_id="pass2-protocol-diagnostic-v1",
                    family="state_candidate_quality",
                    version="1",
                    turns=("first", "second"),
                ),
            )

    evidence = asyncio.run(run())

    first = evidence.turns[0].cognition_execution
    assert first is not None
    assert first.pass2_status == "committed"
    assert first.pass2_protocol_failure is None

    second = evidence.turns[1].cognition_execution
    assert second is not None
    assert second.pass2_status == "failed"
    assert second.pass2_failure_reason == "pass2_failed"
    diagnostic = second.pass2_protocol_failure
    assert diagnostic is not None
    assert diagnostic.http_status == 200
    assert diagnostic.response_text == malformed_envelope
    assert diagnostic.message_content == malformed_content
    assert diagnostic.finish_reason == "stop"
    assert diagnostic.usage == {
        "prompt_tokens": 1540,
        "completion_tokens": 76,
        "total_tokens": 1616,
    }
    assert diagnostic.exception_chain[0]["type"] == "ProviderProtocolError"
    assert diagnostic.exception_chain[0]["message"] == (
        "provider extraction content is not valid JSON"
    )
    assert diagnostic.exception_chain[1]["type"] == "JSONDecodeError"
