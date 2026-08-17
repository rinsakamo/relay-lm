from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory
from relaylm.turn import MemoryRetrievalBudget, run_user_turn, run_user_turn_streaming


_MEMORY = """# Memory

## Coffee

Rin likes coffee.

## Travel

Rin visited Fukuoka last year.
"""


def _make_character(root: Path, *, cls: type[CharacterDirectory] = CharacterDirectory) -> CharacterDirectory:
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


class ExplodingMemoryReadCharacter(CharacterDirectory):
    def load_memory_markdown(self) -> str | None:
        raise AssertionError("MEMORY.md must not be read without an explicit budget")


class FailingMemoryReadCharacter(CharacterDirectory):
    def load_memory_markdown(self) -> str | None:
        raise CharacterDataError("cannot read MEMORY.md: intentional failure")


def test_buffered_turn_projects_relevant_memory_under_explicit_budget(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = RecordingProvider()

    asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="What do you remember about coffee?",
            memory_budget=MemoryRetrievalBudget(max_chunks=1, max_chars=200),
        )
    )

    assert provider.calls == 1
    supplied = provider.inputs[0]
    assert supplied.context == ()
    assert len(supplied.memory) == 1
    assert supplied.memory[0].content == "## Coffee\n\nRin likes coffee."
    assert supplied.memory[0].location == "memory/MEMORY.md#memory/coffee"


def test_streaming_turn_uses_same_explicit_memory_retrieval_path(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = RecordingStreamingProvider()
    emitted: list[str] = []

    async def emit(delta: str) -> None:
        emitted.append(delta)

    asyncio.run(
        run_user_turn_streaming(
            character=character,
            provider=provider,
            content="Coffee memory?",
            emit_response_delta=emit,
            memory_budget=MemoryRetrievalBudget(max_chunks=1, max_chars=200),
        )
    )

    assert provider.calls == 1
    assert emitted == ["ok"]
    assert len(provider.inputs[0].memory) == 1
    assert provider.inputs[0].memory[0].location == "memory/MEMORY.md#memory/coffee"


def test_omitted_memory_budget_preserves_no_read_behavior(tmp_path: Path) -> None:
    character = _make_character(tmp_path, cls=ExplodingMemoryReadCharacter)
    provider = RecordingProvider()

    asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="What do you remember about coffee?",
        )
    )

    assert provider.calls == 1
    assert provider.inputs[0].memory == ()


def test_memory_read_failure_keeps_user_event_but_skips_provider_and_state(tmp_path: Path) -> None:
    character = _make_character(tmp_path, cls=FailingMemoryReadCharacter)
    provider = RecordingProvider()

    with pytest.raises(CharacterDataError, match="intentional failure"):
        asyncio.run(
            run_user_turn(
                character=character,
                provider=provider,
                content="What do you remember about coffee?",
                memory_budget=MemoryRetrievalBudget(max_chunks=1, max_chars=200),
            )
        )

    assert provider.calls == 0
    reopened = CharacterDirectory(tmp_path)
    assert [event.actor for event in reopened.iter_events()] == ["user"]
    assert reopened.load_state().states == ()
