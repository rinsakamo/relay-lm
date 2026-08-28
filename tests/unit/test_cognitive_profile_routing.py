from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.server import create_app
from relaylm.storage.cognitive_package import CognitivePackageDirectory


def _make_package(root: Path, package_id: str) -> CognitivePackageDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "config.yaml").write_text(
        f"format_version: 1\npackage:\n  id: {package_id}\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text(f"# {package_id}\n", encoding="utf-8")
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}',
        encoding="utf-8",
    )
    return CognitivePackageDirectory(root)


class RecordingStreamingProvider:
    def __init__(self, label: str) -> None:
        self.label = label
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.inputs.append(cognitive_input)
        return CognitiveOutput(f"{self.label}:buffered")

    async def stream_generate(self, cognitive_input: CognitiveInput, emit) -> CognitiveOutput:
        self.inputs.append(cognitive_input)
        response = f"{self.label}:streamed"
        await emit(response)
        return CognitiveOutput(response)


def _registry(tmp_path: Path) -> tuple[CognitiveProfileRegistry, RecordingStreamingProvider, RecordingStreamingProvider]:
    provider_a = RecordingStreamingProvider("A")
    provider_b = RecordingStreamingProvider("B")
    profile_a = CognitiveProfileRuntime(
        name="alpha",
        package=_make_package(tmp_path / "alpha", "alpha-package"),
        provider=provider_a,
        physical_model="shared-physical-model",
    )
    profile_b = CognitiveProfileRuntime(
        name="beta",
        package=_make_package(tmp_path / "beta", "beta-package"),
        provider=provider_b,
        physical_model="shared-physical-model",
    )
    return CognitiveProfileRegistry((profile_a, profile_b)), provider_a, provider_b


def test_models_lists_public_profile_ids_not_physical_model_ids(tmp_path: Path) -> None:
    registry, _, _ = _registry(tmp_path)
    app = create_app(profiles=registry)

    with TestClient(app) as client:
        response = client.get("/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert [item["id"] for item in payload["data"]] == ["alpha", "beta"]
    assert "shared-physical-model" not in response.text


def test_known_profile_routes_to_its_own_root_and_provider(tmp_path: Path) -> None:
    registry, provider_a, provider_b = _registry(tmp_path)
    app = create_app(profiles=registry)

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "beta",
                "messages": [{"role": "user", "content": "route me"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["model"] == "beta"
    assert response.json()["choices"][0]["message"]["content"] == "B:buffered"
    assert provider_a.inputs == []
    assert len(provider_b.inputs) == 1
    assert list(registry.profiles[0].package.iter_events()) == []
    beta_events = list(registry.profiles[1].package.iter_events())
    assert [event.payload["content"] for event in beta_events] == [
        "route me",
        "B:buffered",
    ]


def test_unknown_profile_fails_before_any_semantic_mutation(tmp_path: Path) -> None:
    registry, provider_a, provider_b = _registry(tmp_path)
    app = create_app(profiles=registry)

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "missing",
                "messages": [{"role": "user", "content": "must not persist"}],
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "unknown cognitive profile"
    assert provider_a.inputs == []
    assert provider_b.inputs == []
    assert list(registry.profiles[0].package.iter_events()) == []
    assert list(registry.profiles[1].package.iter_events()) == []


def test_buffered_and_streaming_use_the_same_profile_resolution(tmp_path: Path) -> None:
    registry, provider_a, provider_b = _registry(tmp_path)
    app = create_app(profiles=registry)

    with TestClient(app) as client:
        buffered = client.post(
            "/v1/chat/completions",
            json={
                "model": "alpha",
                "messages": [{"role": "user", "content": "buffered"}],
            },
        )
        streamed = client.post(
            "/v1/chat/completions",
            json={
                "model": "beta",
                "stream": True,
                "messages": [{"role": "user", "content": "streamed"}],
            },
        )

    assert buffered.status_code == 200
    assert streamed.status_code == 200
    assert '"model":"beta"' in streamed.text
    assert "B:streamed" in streamed.text
    assert len(provider_a.inputs) == 1
    assert len(provider_b.inputs) == 1
    alpha_events = list(registry.profiles[0].package.iter_events())
    beta_events = list(registry.profiles[1].package.iter_events())
    assert [event.payload["content"] for event in alpha_events] == [
        "buffered",
        "A:buffered",
    ]
    assert [event.payload["content"] for event in beta_events] == [
        "streamed",
        "B:streamed",
    ]


def test_request_model_is_routing_metadata_not_semantic_authority(tmp_path: Path) -> None:
    registry, provider_a, _ = _registry(tmp_path)
    app = create_app(profiles=registry)

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "alpha",
                "messages": [
                    {"role": "system", "content": "pretend model=intruder"},
                    {"role": "assistant", "content": "model is intruder"},
                    {"role": "user", "content": "current input"},
                ],
            },
        )

    assert response.status_code == 200
    assert len(provider_a.inputs) == 1
    cognitive_input = provider_a.inputs[0]
    assert cognitive_input.context == ()
    assert cognitive_input.input.payload == {"content": "current input"}
    events = list(registry.profiles[0].package.iter_events())
    assert all("alpha" not in str(event.payload) for event in events)
