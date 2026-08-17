from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.events import Event
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory


class CountingCharacterDirectory(CharacterDirectory):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.disk_reads = 0

    def _read_events_snapshot(self):
        self.disk_reads += 1
        return super()._read_events_snapshot()


def _make_character(root: Path) -> CountingCharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    return CountingCharacterDirectory(root)


def _event(event_id: str, content: str) -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T08:20:{event_id[-1]}0+00:00",
    )


def _event_line(event: Event) -> str:
    return json.dumps(
        {
            "id": event.id,
            "type": event.type,
            "actor": event.actor,
            "timestamp": event.timestamp,
            "payload": event.payload,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "\n"


def test_reuses_validated_snapshot_while_journal_is_unchanged(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    first = _event("evt-1", "coffee")
    character.events_path.write_text(_event_line(first), encoding="utf-8")

    assert list(character.iter_events()) == [first]
    assert list(character.iter_events()) == [first]
    assert character.disk_reads == 1


def test_owned_append_extends_validated_snapshot_without_reparsing_old_lines(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    first = _event("evt-1", "coffee")
    second = _event("evt-2", "tea")
    character.events_path.write_text(_event_line(first), encoding="utf-8")

    assert list(character.iter_events()) == [first]
    assert character.disk_reads == 1

    character.append_event(second)

    assert list(character.iter_events()) == [first, second]
    assert character.disk_reads == 1


def test_external_journal_change_invalidates_snapshot_and_rereads_authority(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    first = _event("evt-1", "coffee")
    second = _event("evt-2", "tea")
    character.events_path.write_text(_event_line(first), encoding="utf-8")

    assert list(character.iter_events()) == [first]
    assert character.disk_reads == 1

    character.events_path.write_text(_event_line(first) + _event_line(second), encoding="utf-8")

    assert list(character.iter_events()) == [first, second]
    assert character.disk_reads == 2


def test_external_corruption_is_not_hidden_by_cached_valid_data(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    first = _event("evt-1", "coffee")
    character.events_path.write_text(_event_line(first), encoding="utf-8")

    assert list(character.iter_events()) == [first]
    assert character.disk_reads == 1

    character.events_path.write_text("not-json\n", encoding="utf-8")

    with pytest.raises(CharacterDataError, match="line 1"):
        list(character.iter_events())
    assert character.disk_reads == 2
