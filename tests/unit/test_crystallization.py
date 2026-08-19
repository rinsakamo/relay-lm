from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.crystallization import (
    CrystallizationInput,
    CrystallizationOutput,
    run_crystallization,
)
from relaylm.events import Event
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.memory_provenance import MemoryTemporalScope, MemoryUnit
from relaylm.storage.filesystem import CharacterDirectory


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


class RecordingCrystallizer:
    def __init__(self) -> None:
        self.inputs: list[CrystallizationInput] = []
        self.calls = 0

    async def generate(self, crystallization_input: CrystallizationInput) -> CrystallizationOutput:
        self.calls += 1
        self.inputs.append(crystallization_input)
        source = crystallization_input.events[-1].id
        return CrystallizationOutput(
            memory_units=(
                MemoryUnit(
                    heading="Preferences",
                    content="Rin likes tea.\n\n<!-- relaylm-source: current -->",
                    temporal_scope=MemoryTemporalScope.UNKNOWN,
                ),
            ),
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="tea",
                    value="likes",
                    sources=(source,),
                ),
            ),
        )


def test_crystallization_writes_portable_memory_and_governs_state(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    old_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "昔の会話"},
        event_id="old",
        timestamp="2026-08-01T00:00:00+00:00",
    )
    current_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "紅茶が好き"},
        event_id="current",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    character.append_event(old_event)
    character.append_event(current_event)
    crystallizer = RecordingCrystallizer()

    result = asyncio.run(
        run_crystallization(
            character=character,
            crystallizer=crystallizer,
            max_events=1,
        )
    )

    assert crystallizer.calls == 1
    supplied = crystallizer.inputs[0]
    assert [event.id for event in supplied.events] == ["current"]
    assert supplied.prior_memory is None
    assert result.memory_changed is True
    assert result.decisions[0].action == "create"
    assert character.load_memory_markdown().startswith("# Memory")
    assert [
        (record.state_class, record.key, record.value)
        for record in character.load_state().states
    ] == [("user.preference", "tea", "likes")]


def test_crystallization_can_validate_state_provenance_outside_recent_snapshot(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    old_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "紅茶が好き"},
        event_id="old",
        timestamp="2026-08-01T00:00:00+00:00",
    )
    recent_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "今日は暑い"},
        event_id="recent",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    character.append_event(old_event)
    character.append_event(recent_event)
    character.save_state(
        CanonicalState(
            states=(
                StateRecord(
                    state_id="tea-state",
                    state_class="user.preference",
                    key="tea",
                    value="likes tea (紅茶)",
                    sources=("old",),
                ),
            )
        )
    )

    class CleanupCrystallizer:
        async def generate(self, crystallization_input: CrystallizationInput) -> CrystallizationOutput:
            assert [event.id for event in crystallization_input.events] == ["recent"]
            return CrystallizationOutput(
                memory_units=(
                    MemoryUnit(
                        heading="Preferences",
                        content="Rin likes tea.",
                        temporal_scope=MemoryTemporalScope.UNKNOWN,
                    ),
                ),
                state_candidates=(
                    StateCandidate.set(
                        state_class="user.preference",
                        key="tea",
                        value="likes",
                        sources=("old",),
                    ),
                ),
            )

    result = asyncio.run(
        run_crystallization(
            character=character,
            crystallizer=CleanupCrystallizer(),
            max_events=1,
        )
    )

    assert result.decisions[0].status == "accepted"
    assert result.decisions[0].action == "replace"
    assert character.load_state().states[0].value == "likes"


def test_unchanged_crystallization_is_stable_without_memory_or_state_churn(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    event = Event.create(
        type="message",
        actor="user",
        payload={"content": "紅茶が好き"},
        event_id="current",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    character.append_event(event)
    crystallizer = RecordingCrystallizer()

    first = asyncio.run(run_crystallization(character=character, crystallizer=crystallizer))
    second = asyncio.run(run_crystallization(character=character, crystallizer=crystallizer))

    assert first.memory_changed is True
    assert second.memory_changed is False
    assert second.decisions[0].status == "noop"
    assert len(character.load_state().states) == 1
    assert crystallizer.inputs[1].prior_memory == character.load_memory_markdown()
