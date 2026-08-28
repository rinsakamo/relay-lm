from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.server import create_app
from relaylm.state import CanonicalState
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    run_user_turn_streaming,
    run_user_turn_streaming_with_cognitive_budget_diagnostics,
    run_user_turn_streaming_with_retrieval_diagnostics,
)


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _profiles(character: CharacterDirectory, provider: object) -> CognitiveProfileRegistry:
    return CognitiveProfileRegistry(
        (
            CognitiveProfileRuntime(
                name="relaylm",
                package=CognitivePackageDirectory(character.root),
                provider=provider,
                physical_model="stream-admission-test-model",
            ),
        )
    )


class _NonCallableStreamingProvider:
    stream_generate = object()

    def __init__(self) -> None:
        self.generate_calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.generate_calls += 1
        return CognitiveOutput(response="unexpected")


async def _discard_delta(_: str) -> None:
    return None


def test_openai_stream_rejects_non_callable_provider_before_turn_preparation(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    provider = _NonCallableStreamingProvider()
    app = create_app(profiles=_profiles(character, provider))

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relaylm",
                "stream": True,
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "streaming is not available for the configured cognitive provider"
    }
    assert provider.generate_calls == 0
    assert list(CharacterDirectory(tmp_path).iter_events()) == []


def test_streaming_turn_rejects_non_callable_provider_before_user_event(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)

    with pytest.raises(TypeError, match="provider does not support cognitive streaming"):
        asyncio.run(
            run_user_turn_streaming(
                character=character,
                provider=_NonCallableStreamingProvider(),
                content="hello",
                emit_response_delta=_discard_delta,
            )
        )

    assert list(CharacterDirectory(tmp_path).iter_events()) == []


def test_streaming_retrieval_diagnostics_reject_non_callable_before_preparation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    character = _make_character(tmp_path)

    def fail_if_prepared(**_kwargs):
        raise AssertionError("retrieval preparation must not run")

    monkeypatch.setattr("relaylm.turn._prepare_user_turn", fail_if_prepared)

    with pytest.raises(TypeError, match="provider does not support cognitive streaming"):
        asyncio.run(
            run_user_turn_streaming_with_retrieval_diagnostics(
                character=character,
                provider=_NonCallableStreamingProvider(),
                content="hello",
                emit_response_delta=_discard_delta,
            )
        )


def test_streaming_budget_diagnostics_reject_non_callable_before_preparation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    character = _make_character(tmp_path)

    def fail_if_prepared(**_kwargs):
        raise AssertionError("budget preparation must not run")

    monkeypatch.setattr("relaylm.turn._enforce_budgeted_user_turn", fail_if_prepared)

    with pytest.raises(TypeError, match="provider does not support cognitive streaming"):
        asyncio.run(
            run_user_turn_streaming_with_cognitive_budget_diagnostics(
                character=character,
                provider=_NonCallableStreamingProvider(),
                content="hello",
                emit_response_delta=_discard_delta,
                cognitive_budget=cast(CognitiveBudgetRuntimeConfig, object()),
            )
        )
