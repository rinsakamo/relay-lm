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


@pytest.mark.parametrize("key", ["likes", " DISLIKES ", "Preference"])
def test_persisted_generic_preference_key_fails_before_provider_generation(
    tmp_path: Path,
    key: str,
) -> None:
    character = _make_character(tmp_path)
    character.state_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "states": [
                    {
                        "state_id": "state-generic-preference",
                        "state_class": "user.preference",
                        "key": key,
                        "value": "tea",
                        "status": "active",
                        "sources": ["evt-old"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    provider = _RecordingProvider()

    with pytest.raises(CharacterDataError, match="generic preference key"):
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


def test_specific_preference_key_and_same_key_on_other_class_remain_valid() -> None:
    preference = StateRecord(
        state_id="state-preference",
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=("evt-old",),
    )
    fact = StateRecord(
        state_id="state-fact",
        state_class="user.fact",
        key="likes",
        value=3,
        sources=("evt-old",),
    )

    assert preference.key == "tea"
    assert fact.key == "likes"


def test_generic_preference_candidate_still_reaches_validator_rejection() -> None:
    event = Event.create(
        type="message",
        actor="user",
        payload={"content": "I like tea"},
        event_id="evt-now",
        timestamp="2026-08-23T00:00:00+00:00",
    )
    candidate = StateCandidate.set(
        state_class="user.preference",
        key=" LIKES ",
        value="tea",
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "generic_preference_key"
    assert result.state == CanonicalState()
