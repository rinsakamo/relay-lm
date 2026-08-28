from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from relaylm.api.openai import create_openai_router
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.state import StateCandidate
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.storage.filesystem import CharacterDirectory


def _make_character(root: Path) -> None:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# ReLM\n\nBe kind and remember only grounded continuity.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}', encoding="utf-8"
    )


def _make_app(*, character: CharacterDirectory, provider: object) -> FastAPI:
    app = FastAPI()
    profile = CognitiveProfileRuntime(
        name="relaylm",
        package=CognitivePackageDirectory(character.root),
        provider=provider,
        physical_model="integration-test-model",
    )
    app.include_router(
        create_openai_router(profiles=CognitiveProfileRegistry((profile,)))
    )
    return app


class FirstSessionProvider:
    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        return CognitiveOutput(
            response="紅茶が好きって覚えておくね。",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="tea",
                    value="likes",
                    sources=(cognitive_input.input.id,),
                ),
            ),
        )


class RestartedSessionProvider:
    def __init__(self) -> None:
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.inputs.append(cognitive_input)
        return CognitiveOutput(response="うん。紅茶が好きって覚えてるよ。")


def test_restart_uses_relaylm_owned_state_and_events_without_client_history(
    tmp_path: Path,
) -> None:
    _make_character(tmp_path)

    first_app = _make_app(
        character=CharacterDirectory(tmp_path),
        provider=FirstSessionProvider(),
    )
    with TestClient(first_app) as client:
        first = client.post(
            "/v1/chat/completions",
            json={
                "model": "relaylm",
                "messages": [
                    {"role": "user", "content": "紅茶が好き。覚えておいて"}
                ],
            },
        )

    assert first.status_code == 200

    persisted = CharacterDirectory(tmp_path)
    assert [
        (record.state_class, record.key, record.value)
        for record in persisted.load_state().states
    ] == [("user.preference", "tea", "likes")]
    persisted_events = list(persisted.iter_events())
    assert [event.actor for event in persisted_events] == ["user", "assistant"]

    restarted_provider = RestartedSessionProvider()
    restarted_app = _make_app(
        character=CharacterDirectory(tmp_path),
        provider=restarted_provider,
    )
    with TestClient(restarted_app) as client:
        followup = client.post(
            "/v1/chat/completions",
            json={
                "model": "relaylm",
                "messages": [
                    {
                        "role": "user",
                        "content": "前に話した好きな飲み物、覚えてる？",
                    }
                ],
            },
        )

    assert followup.status_code == 200
    assert followup.json()["choices"][0]["message"]["content"] == (
        "うん。紅茶が好きって覚えてるよ。"
    )
    assert len(restarted_provider.inputs) == 1

    restarted_input = restarted_provider.inputs[0]
    assert [
        (record.state_class, record.key, record.value)
        for record in restarted_input.state
    ] == [("user.preference", "tea", "likes")]
    assert [(item.actor, item.content) for item in restarted_input.context] == [
        ("user", "紅茶が好き。覚えておいて"),
        ("assistant", "紅茶が好きって覚えておくね。"),
    ]
    assert restarted_input.input.payload["content"] == (
        "前に話した好きな飲み物、覚えてる？"
    )
    assert {source for item in restarted_input.context for source in item.sources} == {
        event.id for event in persisted_events
    }
