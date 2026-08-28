from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.server import create_app
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.storage.filesystem import CharacterDirectory


class RecordingProvider:
    def __init__(self) -> None:
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.inputs.append(cognitive_input)
        return CognitiveOutput("ok")


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nNever invent history.\n", encoding="utf-8")
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
                physical_model="operator-test-model",
            ),
        )
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (("temperature", 0.2), ("max_tokens", 12)),
)
def test_chat_completions_rejects_unsupported_top_level_controls(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    provider = RecordingProvider()
    app = create_app(profiles=_profiles(_make_character(tmp_path), provider))

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relaylm",
                "messages": [{"role": "user", "content": "hi"}],
                field: value,
            },
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(
        item["loc"] == ["body", field] and item["type"] == "extra_forbidden"
        for item in detail
    )
    assert provider.inputs == []
