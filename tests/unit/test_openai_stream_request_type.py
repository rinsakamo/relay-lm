from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.server import create_app
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.storage.filesystem import CharacterDirectory


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}', encoding="utf-8"
    )
    return CharacterDirectory(root)


def _profiles(character: CharacterDirectory, provider: object) -> CognitiveProfileRegistry:
    return CognitiveProfileRegistry(
        (
            CognitiveProfileRuntime(
                name="relaylm",
                package=CognitivePackageDirectory(character.root),
                provider=provider,
                physical_model="stream-request-test-model",
            ),
        )
    )


class StreamingProvider:
    def __init__(self) -> None:
        self.buffered_calls = 0
        self.streaming_calls = 0

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.buffered_calls += 1
        return CognitiveOutput("buffered")

    async def stream_generate(self, cognitive_input, emit_response_delta):
        self.streaming_calls += 1
        await emit_response_delta("streamed")
        return CognitiveOutput("streamed")


@pytest.mark.parametrize("stream_value", ["yes", "false", 1, 0])
def test_non_boolean_stream_values_fail_request_validation_before_turn(
    tmp_path: Path,
    stream_value: object,
) -> None:
    provider = StreamingProvider()
    app = create_app(profiles=_profiles(_make_character(tmp_path), provider))

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relaylm",
                "stream": stream_value,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

    assert response.status_code == 422
    assert provider.buffered_calls == 0
    assert provider.streaming_calls == 0
    assert list(CharacterDirectory(tmp_path).iter_events()) == []


@pytest.mark.parametrize("payload", [{}, {"stream": False}])
def test_omitted_or_false_stream_remains_buffered(
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    provider = StreamingProvider()
    app = create_app(profiles=_profiles(_make_character(tmp_path), provider))
    body = {
        "model": "relaylm",
        "messages": [{"role": "user", "content": "hi"}],
        **payload,
    }

    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=body)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["choices"][0]["message"]["content"] == "buffered"
    assert provider.buffered_calls == 1
    assert provider.streaming_calls == 0


def test_explicit_true_stream_remains_streaming(tmp_path: Path) -> None:
    provider = StreamingProvider()
    app = create_app(profiles=_profiles(_make_character(tmp_path), provider))

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relaylm",
                "stream": True,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"content":"streamed"' in response.text
    assert '"finish_reason":"stop"' in response.text
    assert response.text.endswith("data: [DONE]\n\n")
    assert provider.buffered_calls == 0
    assert provider.streaming_calls == 1
