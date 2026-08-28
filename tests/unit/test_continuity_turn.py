from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.continuity import ContinuityCandidate, ContinuityContext, ContinuityItem
from relaylm.server import create_app
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime, run_user_turn, run_user_turn_streaming


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}', encoding="utf-8"
    )
    return CharacterDirectory(root)


class _BufferedContinuityProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(
            response="その『最初の案』の続きを見よう。",
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="referent",
                    key="draft.current",
                    value="the first draft",
                    sources=(cognitive_input.input.id,),
                    epistemic_role="assistant_inference",
                ),
            ),
        )


class _InspectContinuityInputProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput(response="了解。")


class _EmptyContinuityProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(response="了解。")


class _StreamingContinuityProvider:
    def __init__(self, runtime: ContinuityRuntime) -> None:
        self.runtime = runtime
        self.stream_calls = 0
        self.revisions_during_stream: list[int] = []

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("streamed ordinary turn must not call buffered generate")

    async def stream_generate(self, cognitive_input: CognitiveInput, emit) -> CognitiveOutput:
        self.stream_calls += 1
        self.revisions_during_stream.append(self.runtime.context.revision)
        await emit("続き")
        self.revisions_during_stream.append(self.runtime.context.revision)
        await emit("を進めよう。")
        return CognitiveOutput(
            response="続きを進めよう。",
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="active_task",
                    key="task.current",
                    value="continue the draft",
                    sources=(cognitive_input.input.id,),
                    epistemic_role="assistant_commitment",
                ),
            ),
        )


def test_buffered_turn_accepts_continuity_from_exactly_one_semantic_generation(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    provider = _BufferedContinuityProvider()
    runtime = ContinuityRuntime(
        context=ContinuityContext(max_items=3),
        lifetime_revisions=4,
    )

    result = asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="最初の案を直そう",
            continuity_runtime=runtime,
        )
    )

    assert provider.calls == 1
    assert runtime.context.revision == 1
    assert len(runtime.context.items) == 1
    item = runtime.context.items[0]
    assert item.kind == "referent"
    assert item.key == "draft.current"
    assert item.value == "the first draft"
    assert item.sources == (result.user_event.id,)
    assert result.continuity is not None
    assert result.continuity.context is runtime.context
    assert result.continuity.decisions[0].action == "admit"
    assert result.state.states == ()
    assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == [
        "user",
        "assistant",
    ]


def test_turn_projects_preexisting_accepted_continuity_before_advancing_lifecycle(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    provider = _InspectContinuityInputProvider()
    retained = ContinuityItem(
        item_id="continuity:1:1",
        kind="referent",
        key="draft.current",
        value={"entity": "the blue draft"},
        sources=("accepted-source",),
        epistemic_role="user_assertion",
        accepted_revision=1,
        expires_revision=5,
    )
    runtime = ContinuityRuntime(
        context=ContinuityContext(max_items=3, revision=1, items=(retained,)),
        lifetime_revisions=4,
    )

    result = asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="その続きはどうする？",
            continuity_runtime=runtime,
        )
    )

    assert provider.calls == 1
    assert len(provider.inputs[0].context) == 1
    projected = provider.inputs[0].context[0]
    assert json.loads(projected.content) == {
        "continuity": {
            "epistemic_role": "user_assertion",
            "key": "draft.current",
            "kind": "referent",
            "value": {"entity": "the blue draft"},
        }
    }
    assert projected.sources == ("accepted-source",)
    assert projected.actor is None
    assert runtime.context.revision == 2
    assert result.continuity is not None
    assert result.continuity.context is runtime.context


def test_streamed_turn_commits_continuity_only_after_one_stream_generation(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    runtime = ContinuityRuntime(
        context=ContinuityContext(max_items=3),
        lifetime_revisions=4,
    )
    provider = _StreamingContinuityProvider(runtime)
    emitted: list[str] = []

    async def emit(text: str) -> None:
        emitted.append(text)

    result = asyncio.run(
        run_user_turn_streaming(
            character=character,
            provider=provider,
            content="この作業を続けよう",
            emit_response_delta=emit,
            continuity_runtime=runtime,
        )
    )

    assert provider.stream_calls == 1
    assert provider.revisions_during_stream == [0, 0]
    assert "".join(emitted) == "続きを進めよう。"
    assert runtime.context.revision == 1
    assert runtime.context.items[0].kind == "active_task"
    assert runtime.context.items[0].key == "task.current"
    assert result.continuity is not None
    assert result.continuity.decisions[0].action == "admit"


def test_configured_runtime_advances_lifecycle_even_when_output_has_no_candidates(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    provider = _EmptyContinuityProvider()
    retained = ContinuityItem(
        item_id="continuity:0:1",
        kind="unresolved",
        key="question.current",
        value="which draft?",
        sources=("old-event",),
        epistemic_role="assistant_inference",
        accepted_revision=0,
        expires_revision=2,
    )
    runtime = ContinuityRuntime(
        context=ContinuityContext(max_items=2, revision=0, items=(retained,)),
        lifetime_revisions=3,
    )

    first = asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="まだ考えてる",
            continuity_runtime=runtime,
        )
    )
    assert runtime.context.revision == 1
    assert runtime.context.items == (retained,)
    assert first.continuity is not None
    assert first.continuity.expired_item_ids == ()

    second = asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="次に進もう",
            continuity_runtime=runtime,
        )
    )
    assert provider.calls == 2
    assert runtime.context.revision == 2
    assert runtime.context.items == ()
    assert second.continuity is not None
    assert second.continuity.expired_item_ids == (retained.item_id,)


def test_continuity_candidates_are_not_silently_dropped_without_runtime(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    provider = _BufferedContinuityProvider()

    with pytest.raises(RuntimeError, match="continuity candidates require an explicit runtime"):
        asyncio.run(
            run_user_turn(
                character=character,
                provider=provider,
                content="この案の続きをお願い",
            )
        )

    assert provider.calls == 1
    assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == ["user"]
    assert CharacterDirectory(tmp_path).load_state().states == ()


def test_continuity_runtime_requires_explicit_positive_lifetime() -> None:
    with pytest.raises(ValueError, match="lifetime_revisions must be positive"):
        ContinuityRuntime(
            context=ContinuityContext(max_items=2),
            lifetime_revisions=0,
        )


def test_openai_app_threads_explicit_runtime_without_owning_budget_policy(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    provider = _BufferedContinuityProvider()
    runtime = ContinuityRuntime(
        context=ContinuityContext(max_items=2),
        lifetime_revisions=3,
    )
    profile = CognitiveProfileRuntime(
        name="relaylm",
        package=CognitivePackageDirectory(character.root),
        provider=provider,
        physical_model="continuity-test-model",
        continuity_runtime=runtime,
    )
    app = create_app(profiles=CognitiveProfileRegistry((profile,)))

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relaylm",
                "messages": [{"role": "user", "content": "最初の案を直そう"}],
            },
        )

    assert response.status_code == 200
    assert provider.calls == 1
    assert runtime.context.revision == 1
    assert runtime.context.items[0].key == "draft.current"
