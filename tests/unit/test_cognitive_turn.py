from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.context import compile_cognitive_input
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import run_user_turn
from relaylm.validation import apply_state_candidates


def _make_character(root: Path, *, state: CanonicalState | None = None) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(state or CanonicalState())
    return character


class SetPreferenceProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput(
            response="紅茶が好きなんだね。覚えておくね。",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="tea",
                    value="likes",
                    sources=(cognitive_input.input.id,),
                ),
            ),
        )


class RemovePreferenceProvider:
    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        return CognitiveOutput(
            response="分かった。今は紅茶が好きという理解にはしないね。",
            state_candidates=(
                StateCandidate.remove(
                    state_class="user.preference",
                    key="tea",
                    sources=(cognitive_input.input.id,),
                ),
            ),
        )


class BadSourceProvider:
    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        return CognitiveOutput(
            response="了解。",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.fact",
                    key="residence_location",
                    value="Hokkaido",
                    sources=("invented-event-id",),
                ),
            ),
        )


class FailingProvider:
    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        raise RuntimeError("provider failed")


def test_context_compiler_without_recent_events_keeps_context_empty() -> None:
    current = Event.create(
        type="message",
        actor="user",
        payload={"content": "hello"},
        event_id="current",
        timestamp="2026-08-16T12:00:00+00:00",
    )
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="s1",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=("old-user-event",),
            ),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\n"),
        state=state,
        current_event=current,
    )

    assert compiled.input is current
    assert compiled.state == ()
    assert compiled.context == ()


def test_context_compiler_preserves_actor_provenance_and_excludes_current() -> None:
    prior_user = Event.create(
        type="message",
        actor="user",
        payload={"content": "AとBで迷ってる"},
        event_id="prior-user",
        timestamp="2026-08-16T11:58:00+00:00",
    )
    prior_assistant = Event.create(
        type="message",
        actor="assistant",
        payload={"content": "持ち運び重視？"},
        event_id="prior-assistant",
        timestamp="2026-08-16T11:59:00+00:00",
    )
    current = Event.create(
        type="message",
        actor="user",
        payload={"content": "うん"},
        event_id="current",
        timestamp="2026-08-16T12:00:00+00:00",
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\n"),
        state=CanonicalState(),
        current_event=current,
        recent_events=(prior_user, prior_assistant, current),
    )

    assert [(item.actor, item.content, item.sources) for item in compiled.context] == [
        ("user", "AとBで迷ってる", ("prior-user",)),
        ("assistant", "持ち運び重視？", ("prior-assistant",)),
    ]
    assert all("current" not in item.sources for item in compiled.context)


def test_context_budget_does_not_orphan_assistant_exchange() -> None:
    prior_user = Event.create(
        type="message",
        actor="user",
        payload={"content": "long-user-turn"},
        event_id="prior-user",
        timestamp="2026-08-16T11:57:00+00:00",
    )
    prior_assistant = Event.create(
        type="message",
        actor="assistant",
        payload={"content": "reply"},
        event_id="prior-assistant",
        timestamp="2026-08-16T11:58:00+00:00",
    )
    recent_user = Event.create(
        type="message",
        actor="user",
        payload={"content": "new"},
        event_id="recent-user",
        timestamp="2026-08-16T11:59:00+00:00",
    )
    current = Event.create(
        type="message",
        actor="user",
        payload={"content": "current"},
        event_id="current",
        timestamp="2026-08-16T12:00:00+00:00",
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\n"),
        state=CanonicalState(),
        current_event=current,
        recent_events=(prior_user, prior_assistant, recent_user, current),
        max_working_context_events=3,
        max_working_context_chars=len("new") + len("reply"),
    )

    assert [(item.actor, item.content) for item in compiled.context] == [
        ("user", "new"),
    ]


def test_context_compiler_zero_working_budget_preserves_relevant_state_and_current_event() -> None:
    current = Event.create(
        type="message",
        actor="user",
        payload={"content": "tea"},
        event_id="current",
        timestamp="2026-08-16T12:00:00+00:00",
    )
    initial = StateRecord(
        state_id="s1",
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=("old",),
    )
    prior = Event.create(
        type="message",
        actor="assistant",
        payload={"content": "prior"},
        event_id="prior",
        timestamp="2026-08-16T11:59:00+00:00",
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\n"),
        state=CanonicalState(states=(initial,)),
        current_event=current,
        recent_events=(prior, current),
        max_working_context_events=0,
    )

    assert compiled.state == (initial,)
    assert compiled.context == ()
    assert compiled.input is current


def test_turn_calls_provider_once_and_persists_state(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = SetPreferenceProvider()

    result = asyncio.run(
        run_user_turn(character=character, provider=provider, content="紅茶が好き")
    )

    assert provider.calls == 1
    assert result.response.startswith("紅茶")
    assert len(result.state.states) == 1
    assert result.state.states[0].state_class == "user.preference"
    assert result.state.states[0].key == "tea"
    assert result.state.states[0].value == "likes"
    assert result.decisions[0].action == "create"
    assert CharacterDirectory(tmp_path).load_state() == result.state
    events = list(CharacterDirectory(tmp_path).iter_events())
    assert [event.actor for event in events] == ["user", "assistant"]


def test_second_turn_receives_prior_relaylm_events_as_working_context(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = SetPreferenceProvider()

    asyncio.run(run_user_turn(character=character, provider=provider, content="紅茶が好き"))
    asyncio.run(run_user_turn(character=character, provider=provider, content="それに合うお菓子は？"))

    supplied = provider.inputs[1]
    assert [(item.actor, item.content) for item in supplied.context] == [
        ("user", "紅茶が好き"),
        ("assistant", "紅茶が好きなんだね。覚えておくね。"),
    ]
    assert supplied.state[0].key == "tea"
    assert supplied.input.payload["content"] == "それに合うお菓子は？"


def test_next_turn_receives_relevant_accepted_state_without_prior_events(tmp_path: Path) -> None:
    initial = StateRecord(
        state_id="s1",
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=("old-event",),
    )
    character = _make_character(tmp_path, state=CanonicalState(states=(initial,)))
    provider = SetPreferenceProvider()

    asyncio.run(run_user_turn(character=character, provider=provider, content="tea again"))

    supplied = provider.inputs[0]
    assert supplied.state == (initial,)
    assert supplied.context == ()
    assert supplied.input.payload["content"] == "tea again"


def test_same_value_is_noop(tmp_path: Path) -> None:
    initial = StateRecord(
        state_id="s1",
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=("old-event",),
    )
    character = _make_character(tmp_path, state=CanonicalState(states=(initial,)))
    provider = SetPreferenceProvider()

    result = asyncio.run(
        run_user_turn(character=character, provider=provider, content="紅茶が好き")
    )

    assert result.decisions[0].status == "noop"
    assert result.state.states == (initial,)


def test_remove_closes_current_state_by_removing_it_from_current_view(tmp_path: Path) -> None:
    initial = StateRecord(
        state_id="s1",
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=("old-event",),
    )
    character = _make_character(tmp_path, state=CanonicalState(states=(initial,)))

    result = asyncio.run(
        run_user_turn(
            character=character,
            provider=RemovePreferenceProvider(),
            content="もう紅茶が好きってわけじゃないよ",
        )
    )

    assert result.decisions[0].action == "remove"
    assert result.state.states == ()
    assert CharacterDirectory(tmp_path).load_state().states == ()


def test_unknown_source_rejects_state_but_preserves_response(tmp_path: Path) -> None:
    character = _make_character(tmp_path)

    result = asyncio.run(
        run_user_turn(
            character=character,
            provider=BadSourceProvider(),
            content="今日は寒いね",
        )
    )

    assert result.response == "了解。"
    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "unknown_source"
    assert CharacterDirectory(tmp_path).load_state().states == ()


def test_validator_requires_current_evidence_for_change() -> None:
    old_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "昔は東京に住んでいた"},
        event_id="old",
        timestamp="2026-08-01T00:00:00+00:00",
    )
    current_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "こんにちは"},
        event_id="current",
        timestamp="2026-08-16T00:00:00+00:00",
    )
    candidate = StateCandidate.set(
        state_class="user.fact",
        key="residence_location",
        value="Tokyo",
        sources=("old",),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={"old": old_event, "current": current_event},
        required_source_ids=frozenset({"current"}),
    )

    assert result.decisions[0].reason == "missing_current_evidence"
    assert result.state.states == ()


def test_provider_failure_records_user_event_but_no_assistant_or_state(tmp_path: Path) -> None:
    character = _make_character(tmp_path)

    with pytest.raises(RuntimeError, match="provider failed"):
        asyncio.run(
            run_user_turn(
                character=character,
                provider=FailingProvider(),
                content="届いてる？",
            )
        )

    events = list(CharacterDirectory(tmp_path).iter_events())
    assert [event.actor for event in events] == ["user"]
    assert CharacterDirectory(tmp_path).load_state().states == ()
