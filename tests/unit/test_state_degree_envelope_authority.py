from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from relaylm.cognitive import CognitiveOutput
from relaylm.events import Event
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory
from relaylm.turn import run_user_turn
from relaylm.validation import apply_state_candidates


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    return CharacterDirectory(root)


class _RecordingProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs = []

    async def generate(self, cognitive_input):
        self.calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput(response="ok")


@pytest.mark.parametrize(
    "value",
    [
        {"semantic": "likes"},
        {"semantic": "likes", "degree_hint": 0.85, "extra": True},
        {"semantic": "", "degree_hint": 0.85},
        {"semantic": "likes", "degree_hint": True},
        {"semantic": "likes", "degree_hint": float("inf")},
        {"semantic": "likes", "degree_hint": 1.1},
    ],
)
def test_malformed_persisted_degree_envelope_fails_before_provider_generation(
    tmp_path: Path,
    value: dict[str, object],
) -> None:
    character = _make_character(tmp_path)
    character.state_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "states": [
                    {
                        "state_id": "state-degree",
                        "state_class": "user.preference",
                        "key": "tea",
                        "value": value,
                        "status": "active",
                        "sources": ["evt-old"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    provider = _RecordingProvider()

    with pytest.raises(CharacterDataError, match="invalid degree hint value"):
        asyncio.run(
            run_user_turn(
                character=character,
                provider=provider,
                content="hello",
            )
        )

    assert provider.calls == 0
    assert provider.inputs == []
    assert list(character.iter_events()) == []


def test_valid_degree_envelope_and_non_reserved_mapping_remain_valid() -> None:
    degree = StateRecord(
        state_id="state-degree",
        state_class="user.preference",
        key="tea",
        value={"semantic": "likes", "degree_hint": 0.85},
        sources=("evt-old",),
    )
    ordinary_mapping = StateRecord(
        state_id="state-map",
        state_class="user.fact",
        key="profile",
        value={"nickname": "Rin"},
        sources=("evt-old",),
    )

    assert degree.value == {"semantic": "likes", "degree_hint": 0.85}
    assert ordinary_mapping.value == {"nickname": "Rin"}


def test_malformed_degree_candidate_still_reaches_validator_rejection() -> None:
    event = Event.create(
        type="message",
        actor="user",
        payload={"content": "I like tea a lot"},
        event_id="evt-now",
        timestamp="2026-08-23T00:00:00+00:00",
    )
    candidate = StateCandidate.set(
        state_class="user.preference",
        key="tea",
        value={"semantic": "likes", "degree_hint": True},
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "invalid_degree_hint_value"
    assert result.state == CanonicalState()
