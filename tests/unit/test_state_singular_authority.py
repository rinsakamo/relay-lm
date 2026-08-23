from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.state import CanonicalState, StateRecord
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory
from relaylm.turn import run_user_turn


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    return CharacterDirectory(root)


class RecordingProvider:
    def __init__(self) -> None:
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.inputs.append(cognitive_input)
        return CognitiveOutput(response="了解。")


def test_duplicate_active_persisted_state_fails_before_provider_generation(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    duplicate_state = {
        "format_version": 1,
        "states": [
            {
                "state_id": "state-tokyo",
                "state_class": "user.fact",
                "key": "residence_location",
                "value": "Tokyo",
                "status": "active",
                "sources": ["evt-tokyo"],
            },
            {
                "state_id": "state-osaka",
                "state_class": "user.fact",
                "key": "residence_location",
                "value": "Osaka",
                "status": "active",
                "sources": ["evt-osaka"],
            },
        ],
    }
    character.state_path.write_text(
        json.dumps(duplicate_state, ensure_ascii=False),
        encoding="utf-8",
    )
    provider = RecordingProvider()

    with pytest.raises(
        CharacterDataError,
        match=r"duplicate active state slot: user\.fact/residence_location",
    ):
        asyncio.run(
            run_user_turn(
                character=character,
                provider=provider,
                content="今どこに住んでると思う？",
            )
        )

    assert provider.inputs == []
    assert tuple(character.iter_events()) == ()


def test_non_current_record_may_share_exact_slot_with_current_record() -> None:
    historical = StateRecord(
        state_id="state-old",
        state_class="user.fact",
        key="residence_location",
        value="Tokyo",
        status="active",
        sources=("evt-old",),
        valid_to="2026-08-01T00:00:00+00:00",
    )
    current = StateRecord(
        state_id="state-current",
        state_class="user.fact",
        key="residence_location",
        value="Osaka",
        status="active",
        sources=("evt-current",),
    )

    state = CanonicalState(states=(historical, current))

    assert state.states == (historical, current)
