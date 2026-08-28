from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.providers.openai_compatible import ProviderProtocolError
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
                physical_model="stream-preflight-test-model",
            ),
        )
    )


class _ImmediateProtocolFailureProvider:
    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("stream=true must not use buffered generate")

    async def stream_generate(self, _: CognitiveInput, emit) -> CognitiveOutput:
        raise ProviderProtocolError("upstream failed before first delta")


class _UnusedStreamingProvider:
    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("invalid package must fail before provider generation")

    async def stream_generate(self, _: CognitiveInput, emit) -> CognitiveOutput:
        raise AssertionError("invalid package must fail before provider streaming")


def _stream_request() -> dict[str, object]:
    return {
        "model": "relaylm",
        "stream": True,
        "messages": [{"role": "user", "content": "hello"}],
    }


def test_pre_emission_provider_failure_returns_http_502(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    app = create_app(
        profiles=_profiles(character, _ImmediateProtocolFailureProvider())
    )

    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=_stream_request())

    assert response.status_code == 502
    assert response.json() == {"detail": "upstream cognitive provider failed"}
    assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == ["user"]


def test_pre_emission_character_failure_returns_http_500(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    app = create_app(profiles=_profiles(character, _UnusedStreamingProvider()))
    (tmp_path / "SOUL.md").unlink()

    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=_stream_request())

    assert response.status_code == 500
    assert response.json() == {"detail": "cognitive package is invalid"}
    assert list(CharacterDirectory(tmp_path).iter_events()) == []
