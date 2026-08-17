from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path

import pytest

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.events import Event
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    EventRetrievalBudget,
    MemoryRetrievalBudget,
    run_user_turn,
    run_user_turn_streaming,
    run_user_turn_streaming_with_retrieval_diagnostics,
    run_user_turn_with_retrieval_diagnostics,
)


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "MEMORY.md").write_text(
        "# Coffee one\n\ncoffee alpha\n\n# Coffee two\n\ncoffee beta\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    character.append_event(
        Event.create(
            type="message",
            actor="user",
            payload={"content": "coffee first"},
            event_id="prior-user-1",
            timestamp="2026-08-17T09:00:00+00:00",
        )
    )
    character.append_event(
        Event.create(
            type="message",
            actor="assistant",
            payload={"content": "coffee reply"},
            event_id="prior-assistant-1",
            timestamp="2026-08-17T09:01:00+00:00",
        )
    )
    return character


class BufferedProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput(response="ok")


class StreamingProvider:
    def __init__(self) -> None:
        self.stream_calls = 0
        self.inputs: list[CognitiveInput] = []

    async def stream_generate(
        self, cognitive_input: CognitiveInput, emit_response_delta
    ) -> CognitiveOutput:
        self.stream_calls += 1
        self.inputs.append(cognitive_input)
        await emit_response_delta("ok")
        return CognitiveOutput(response="ok")


class CountingProvider(BufferedProvider):
    pass


def test_opt_in_turn_diagnostics_connect_configured_budgets_to_selector_observations(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    provider = BufferedProvider()
    memory_budget = MemoryRetrievalBudget(max_chunks=1, max_chars=1_000)
    event_budget = EventRetrievalBudget(max_events=1, max_chars=1_000)

    observed = asyncio.run(
        run_user_turn_with_retrieval_diagnostics(
            character=character,
            provider=provider,
            content="coffee",
            memory_budget=memory_budget,
            event_budget=event_budget,
        )
    )

    assert provider.calls == 1
    assert observed.turn.response == "ok"
    assert observed.retrieval.memory is not None
    assert observed.retrieval.memory.budget == memory_budget
    assert observed.retrieval.memory.selector.positive_candidate_count == 2
    assert observed.retrieval.memory.selector.selected_count == 1
    assert observed.retrieval.memory.selector.chunk_budget_pressure is True
    assert observed.retrieval.event is not None
    assert observed.retrieval.event.budget == event_budget
    assert observed.retrieval.event.selector.positive_candidate_count == 2
    assert observed.retrieval.event.selector.selected_count == 1
    assert observed.retrieval.event.selector.event_budget_pressure is True

    payload = asdict(observed.retrieval)
    serialized = repr(payload)
    assert "prior-user-1" not in serialized
    assert "prior-assistant-1" not in serialized
    assert "coffee alpha" not in serialized
    assert "coffee beta" not in serialized
    assert "memory/MEMORY.md" not in serialized


def test_buffered_and_streaming_diagnostics_share_retrieval_preparation_semantics(
    tmp_path: Path,
) -> None:
    buffered = _make_character(tmp_path / "buffered")
    streaming = _make_character(tmp_path / "streaming")
    buffered_provider = BufferedProvider()
    streaming_provider = StreamingProvider()
    memory_budget = MemoryRetrievalBudget(max_chunks=1, max_chars=1_000)
    event_budget = EventRetrievalBudget(max_events=1, max_chars=1_000)
    emitted: list[str] = []

    buffered_result = asyncio.run(
        run_user_turn_with_retrieval_diagnostics(
            character=buffered,
            provider=buffered_provider,
            content="coffee",
            memory_budget=memory_budget,
            event_budget=event_budget,
        )
    )
    streaming_result = asyncio.run(
        run_user_turn_streaming_with_retrieval_diagnostics(
            character=streaming,
            provider=streaming_provider,
            content="coffee",
            emit_response_delta=lambda delta: _record_delta(emitted, delta),
            memory_budget=memory_budget,
            event_budget=event_budget,
        )
    )

    assert buffered_provider.calls == 1
    assert streaming_provider.stream_calls == 1
    assert emitted == ["ok"]
    assert buffered_result.retrieval == streaming_result.retrieval
    assert buffered_provider.inputs[0].memory == streaming_provider.inputs[0].memory
    assert [event.id for event in buffered_provider.inputs[0].event_evidence] == [
        event.id for event in streaming_provider.inputs[0].event_evidence
    ]


async def _record_delta(target: list[str], delta: str) -> None:
    target.append(delta)


def test_non_diagnostic_turn_does_not_enable_retrieval_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    character = _make_character(tmp_path)
    provider = CountingProvider()

    def fail_if_called(**_kwargs):
        raise AssertionError("diagnostic selector must remain opt-in")

    monkeypatch.setattr(
        "relaylm.turn.select_memory_chunks_with_diagnostics",
        fail_if_called,
        raising=False,
    )

    result = asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="coffee",
            memory_budget=MemoryRetrievalBudget(max_chunks=1, max_chars=1_000),
        )
    )

    assert result.response == "ok"
    assert provider.calls == 1


def test_streaming_empty_input_keeps_value_error_precedence(tmp_path: Path) -> None:
    character = _make_character(tmp_path)

    with pytest.raises(ValueError, match="user content must not be empty"):
        asyncio.run(
            run_user_turn_streaming(
                character=character,
                provider=BufferedProvider(),
                content="   ",
                emit_response_delta=lambda delta: _record_delta([], delta),
            )
        )

    events = list(CharacterDirectory(tmp_path).iter_events())
    assert [event.id for event in events] == ["prior-user-1", "prior-assistant-1"]


def test_retrieval_diagnostic_failure_keeps_user_event_only_and_skips_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    character = _make_character(tmp_path)
    provider = CountingProvider()

    def fail_retrieval(**_kwargs):
        raise RuntimeError("retrieval failed")

    monkeypatch.setattr(
        "relaylm.turn.select_memory_chunks_with_diagnostics",
        fail_retrieval,
        raising=False,
    )

    with pytest.raises(RuntimeError, match="retrieval failed"):
        asyncio.run(
            run_user_turn_with_retrieval_diagnostics(
                character=character,
                provider=provider,
                content="coffee",
                memory_budget=MemoryRetrievalBudget(max_chunks=1, max_chars=1_000),
            )
        )

    assert provider.calls == 0
    events = list(CharacterDirectory(tmp_path).iter_events())
    assert [event.actor for event in events] == ["user", "assistant", "user"]
    assert CharacterDirectory(tmp_path).load_state().states == ()
