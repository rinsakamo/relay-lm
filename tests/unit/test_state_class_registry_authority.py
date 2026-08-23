from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from relaylm.cognitive import CognitiveOutput
from relaylm.events import Event
from relaylm.state import CanonicalState, StateCandidate
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


def test_unsupported_persisted_state_class_fails_before_provider_generation(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    character.state_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "states": [
                    {
                        "state_id": "state-unsupported",
                        "state_class": "user.future_magic",
                        "key": "favorite_spell",
                        "value": "teleport",
                        "status": "active",
                        "sources": ["evt-old"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    provider = _RecordingProvider()

    with pytest.raises(CharacterDataError, match="unsupported state_class"):
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


def test_unsupported_candidate_class_still_reaches_validator_rejection() -> None:
    event = Event.create(
        type="message",
        actor="user",
        payload={"content": "I can teleport"},
        event_id="evt-now",
        timestamp="2026-08-23T00:00:00+00:00",
    )
    candidate = StateCandidate.set(
        state_class="user.future_magic",
        key="favorite_spell",
        value="teleport",
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "unsupported_state_class"
    assert result.state == CanonicalState()
