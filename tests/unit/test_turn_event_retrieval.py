from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.events import Event
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    EventRetrievalBudget,
    MemoryRetrievalBudget,
    run_user_turn,
    run_user_turn_streaming,
)


_MEMORY = """# Memory

## Coffee

Rin likes coffee.
"""


def _make_character(
    root: Path,
    *,
    cls: type[CharacterDirectory] = CharacterDirectory,
) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe grounded.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}\n', encoding="utf-8"
    )
    (root / "memory" / "MEMORY.md").write_text(_MEMORY, encoding="utf-8")
    return cls(root)


def _append_message(character: CharacterDirectory, content: str, *, actor: str = "user") -> Event:
    event = Event.create(type="message", actor=actor, payload={"content": content})
    character.append_event(event)
    return event


class RecordingProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput("ok")


class RecordingStreamingProvider(RecordingProvider):
    async def stream_generate(self, cognitive_input, emit_response_delta):
        self.calls += 1
        self.inputs.append(cognitive_input)
        await emit_response_delta("ok")
        return CognitiveOutput("ok")


class CountingCharacter(CharacterDirectory):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.iter_events_calls = 0

    def iter_events(self):
        self.iter_events_calls += 1
        return super().iter_events()


def test_buffered_turn_retrieves_older_relevant_event_under_explicit_budget(tmp_path: Path) -> None:
    character = _make_character(tmp_path, cls=CountingCharacter)
    assert isinstance(character, CountingCharacter)
    coffee = _append_message(character, "Rin mentioned coffee before.")
    for index in range(7):
        _append_message(character, f"unrelated weather note {index}")
    provider = RecordingProvider()

    result = asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="What did I say about coffee?",
            event_budget=EventRetrievalBudget(max_events=1, max_chars=200),
        )
    )

    assert provider.calls == 1
    supplied = provider.inputs[0]
    assert [item.event_id for item in supplied.event_evidence] == [coffee.id]
    assert supplied.event_evidence[0].content == "Rin mentioned coffee before."
    assert result.user_event.id not in {item.event_id for item in supplied.event_evidence}
    assert coffee.id not in {
        source for item in supplied.context for source in item.sources
    }
    assert character.iter_events_calls == 2


def test_streaming_turn_uses_same_explicit_event_retrieval_path(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    coffee = _append_message(character, "Coffee preference was discussed.")
    provider = RecordingStreamingProvider()
    emitted: list[str] = []

    async def emit(delta: str) -> None:
        emitted.append(delta)

    asyncio.run(
        run_user_turn_streaming(
            character=character,
            provider=provider,
            content="Coffee history?",
            emit_response_delta=emit,
            event_budget=EventRetrievalBudget(max_events=1, max_chars=200),
        )
    )

    assert provider.calls == 1
    assert emitted == ["ok"]
    assert [item.event_id for item in provider.inputs[0].event_evidence] == [coffee.id]


def test_omitted_event_budget_preserves_empty_event_evidence(tmp_path: Path) -> None:
    character = _make_character(tmp_path, cls=CountingCharacter)
    assert isinstance(character, CountingCharacter)
    _append_message(character, "Coffee preference was discussed.")
    provider = RecordingProvider()

    asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="Coffee history?",
        )
    )

    assert provider.calls == 1
    assert provider.inputs[0].event_evidence == ()
    assert character.iter_events_calls == 2


def test_zero_event_budget_selects_no_event_evidence(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    _append_message(character, "Coffee preference was discussed.")
    provider = RecordingProvider()

    asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="Coffee history?",
            event_budget=EventRetrievalBudget(max_events=0, max_chars=200),
        )
    )

    assert provider.calls == 1
    assert provider.inputs[0].event_evidence == ()


def test_memory_and_event_retrieval_remain_distinct_layers(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    coffee = _append_message(character, "Coffee preference was discussed.")
    provider = RecordingProvider()

    asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="What do you remember about coffee?",
            memory_budget=MemoryRetrievalBudget(max_chunks=1, max_chars=200),
            event_budget=EventRetrievalBudget(max_events=1, max_chars=200),
        )
    )

    supplied = provider.inputs[0]
    assert len(supplied.memory) == 1
    assert supplied.memory[0].location == "memory/MEMORY.md#memory/coffee"
    assert [item.event_id for item in supplied.event_evidence] == [coffee.id]


def test_event_retrieval_budget_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="event max_events must not be negative"):
        EventRetrievalBudget(max_events=-1, max_chars=100)
    with pytest.raises(ValueError, match="event max_chars must not be negative"):
        EventRetrievalBudget(max_events=1, max_chars=-1)
