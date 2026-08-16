from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.events import Event
from relaylm.state import CanonicalState, StateRecord
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}\n', encoding="utf-8"
    )
    return CharacterDirectory(root)


def test_loads_config_and_soul(tmp_path: Path) -> None:
    character = _make_character(tmp_path)

    config = character.load_config()
    identity = character.load_identity()

    assert config.character_id == "relm"
    assert config.name == "ReLM"
    assert "Be kind and honest" in identity.content


def test_events_round_trip_across_reopen(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    event = Event.create(
        type="message",
        actor="user",
        payload={"content": "紅茶が好き"},
        event_id="evt-1",
        timestamp="2026-08-16T12:00:00+00:00",
    )

    character.append_event(event)
    reopened = CharacterDirectory(tmp_path)

    assert list(reopened.iter_events()) == [event]


def test_state_round_trip_across_reopen(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="state-1",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=("evt-1",),
                valid_from="2026-08-16T12:00:00+00:00",
            ),
        )
    )

    character.save_state(state)
    reopened = CharacterDirectory(tmp_path)

    assert reopened.load_state() == state
    assert not (tmp_path / "memory" / ".state.json.tmp").exists()


def test_missing_state_is_empty_state(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    (tmp_path / "memory" / "state.json").unlink()

    assert character.load_state() == CanonicalState()


def test_invalid_config_fails_closed(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  name: ReLM\n", encoding="utf-8"
    )

    with pytest.raises(CharacterDataError):
        character.load_config()


def test_invalid_event_line_reports_line_number(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    (tmp_path / "memory" / "events.jsonl").write_text(
        '{"id":"ok","type":"message","actor":"user","timestamp":"t","payload":{}}\nnot-json\n',
        encoding="utf-8",
    )

    with pytest.raises(CharacterDataError, match="line 2"):
        list(character.iter_events())
