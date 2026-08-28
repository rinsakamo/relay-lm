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
from relaylm.memory_provenance import (
    MemoryProvenanceSource,
    MemoryProvenanceSourceKind,
    MemoryTemporalScope,
    MemoryUnit,
)
from relaylm.storage.filesystem import CharacterDirectory, StateRevisionConflictError


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


def test_memory_event_provenance_is_bounded_to_crystallization_input(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    old_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "昔の出来事"},
        event_id="old",
        timestamp="2026-08-01T00:00:00+00:00",
    )
    recent_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "最近の出来事"},
        event_id="recent",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    character.append_event(old_event)
    character.append_event(recent_event)

    class OutOfWindowMemorySourceCrystallizer:
        async def generate(
            self,
            crystallization_input: CrystallizationInput,
        ) -> CrystallizationOutput:
            assert [event.id for event in crystallization_input.events] == ["recent"]
            return CrystallizationOutput(
                memory_units=(
                    MemoryUnit(
                        heading="History",
                        content="An older durable event remains readable.",
                        temporal_scope=MemoryTemporalScope.HISTORICAL,
                        sources=(
                            MemoryProvenanceSource(
                                kind=MemoryProvenanceSourceKind.EVENT,
                                reference_id="old",
                            ),
                        ),
                    ),
                ),
            )

    asyncio.run(
        run_crystallization(
            character=character,
            crystallizer=OutOfWindowMemorySourceCrystallizer(),
            max_events=1,
        )
    )

    memory = character.load_memory_markdown()
    assert memory is not None
    assert "An older durable event remains readable." in memory
    assert "relaylm-memory:v1" not in memory


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


def test_crystallization_rebases_non_conflicting_candidate_onto_newer_state(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    tea_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "紅茶が好き"},
        event_id="tea-old",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    residence_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "福岡に住んでいる"},
        event_id="residence-new",
        timestamp="2026-08-17T00:00:01+00:00",
    )
    tea_record = StateRecord(
        state_id="tea-state",
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=(tea_event.id,),
    )
    character.append_event(tea_event)
    character.save_state(CanonicalState(states=(tea_record,)))

    class BlockingCrystallizer:
        def __init__(self) -> None:
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def generate(
            self,
            crystallization_input: CrystallizationInput,
        ) -> CrystallizationOutput:
            assert crystallization_input.state.states == (tea_record,)
            self.started.set()
            await self.release.wait()
            return CrystallizationOutput(
                memory_units=(
                    MemoryUnit(
                        heading="Preferences",
                        content="Tea preferences were consolidated.",
                        temporal_scope=MemoryTemporalScope.UNKNOWN,
                    ),
                ),
                state_candidates=(
                    StateCandidate.set(
                        state_class="user.preference",
                        key="tea",
                        value="dislikes",
                        sources=(tea_event.id,),
                    ),
                ),
            )

    crystallizer = BlockingCrystallizer()

    async def scenario():
        task = asyncio.create_task(
            run_crystallization(character=character, crystallizer=crystallizer)
        )
        await crystallizer.started.wait()
        character.append_event(residence_event)
        character.save_state(
            CanonicalState(
                states=(
                    tea_record,
                    StateRecord(
                        state_id="residence-state",
                        state_class="user.fact",
                        key="residence_location",
                        value="Fukuoka",
                        sources=(residence_event.id,),
                    ),
                )
            )
        )
        crystallizer.release.set()
        return await task

    result = asyncio.run(scenario())
    current = {
        (record.state_class, record.key): record.value
        for record in character.load_state().states
    }

    assert result.decisions[0].status == "accepted"
    assert result.decisions[0].action == "replace"
    assert current[("user.preference", "tea")] == "dislikes"
    assert current[("user.fact", "residence_location")] == "Fukuoka"


def test_crystallization_rejects_candidate_for_slot_changed_while_in_flight(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    old_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "紅茶が好き"},
        event_id="tea-old",
        timestamp="2026-08-17T00:00:00+00:00",
    )
    new_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "今はコーヒーの方が好き"},
        event_id="tea-new",
        timestamp="2026-08-17T00:00:01+00:00",
    )
    old_record = StateRecord(
        state_id="tea-old-state",
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=(old_event.id,),
    )
    character.append_event(old_event)
    character.save_state(CanonicalState(states=(old_record,)))

    class BlockingCrystallizer:
        def __init__(self) -> None:
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def generate(
            self,
            crystallization_input: CrystallizationInput,
        ) -> CrystallizationOutput:
            self.started.set()
            await self.release.wait()
            return CrystallizationOutput(
                memory_units=(
                    MemoryUnit(
                        heading="Preferences",
                        content="Preference history was consolidated.",
                        temporal_scope=MemoryTemporalScope.UNKNOWN,
                    ),
                ),
                state_candidates=(
                    StateCandidate.set(
                        state_class="user.preference",
                        key="tea",
                        value="dislikes",
                        sources=(old_event.id,),
                    ),
                ),
            )

    crystallizer = BlockingCrystallizer()
    newer_state = CanonicalState(
        states=(
            StateRecord(
                state_id="tea-new-state",
                state_class="user.preference",
                key="tea",
                value="prefers coffee",
                sources=(new_event.id,),
            ),
        )
    )

    async def scenario():
        task = asyncio.create_task(
            run_crystallization(character=character, crystallizer=crystallizer)
        )
        await crystallizer.started.wait()
        character.append_event(new_event)
        character.save_state(newer_state)
        crystallizer.release.set()
        return await task

    result = asyncio.run(scenario())

    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "stale_state_slot"
    assert result.state == newer_state
    assert character.load_state() == newer_state


def test_crystallization_does_not_persist_memory_after_state_moves(
    tmp_path: Path,
) -> None:
    _make_character(tmp_path)
    newer_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "福岡に住んでいる"},
        event_id="residence-new",
        timestamp="2026-08-17T00:00:01+00:00",
    )
    newer_state = CanonicalState(
        states=(
            StateRecord(
                state_id="residence-state",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
                sources=(newer_event.id,),
            ),
        )
    )

    class StateMovingCharacterDirectory(CharacterDirectory):
        def __init__(self, root: Path) -> None:
            super().__init__(root)
            self.moved = False

        def save_memory_markdown(
            self,
            content: str,
            *,
            expected_state_revision: str | None = None,
        ) -> bool:
            if expected_state_revision is not None and not self.moved:
                self.moved = True
                self.append_event(newer_event)
                self.save_state(newer_state)
            return super().save_memory_markdown(
                content,
                expected_state_revision=expected_state_revision,
            )

    class MemoryOnlyCrystallizer:
        async def generate(
            self,
            crystallization_input: CrystallizationInput,
        ) -> CrystallizationOutput:
            return CrystallizationOutput(
                memory_units=(
                    MemoryUnit(
                        heading="Stable synthesis",
                        content="This must not persist against stale State.",
                        temporal_scope=MemoryTemporalScope.UNKNOWN,
                    ),
                ),
            )

    character = StateMovingCharacterDirectory(tmp_path)
    try:
        asyncio.run(
            run_crystallization(
                character=character,
                crystallizer=MemoryOnlyCrystallizer(),
            )
        )
    except StateRevisionConflictError:
        pass
    else:
        raise AssertionError("stale MEMORY persistence must fail closed")

    assert character.load_state() == newer_state
    assert character.load_memory_markdown() is None
