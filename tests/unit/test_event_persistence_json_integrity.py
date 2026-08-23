from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from relaylm.events import Event
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory


_EVENT_TIMESTAMP = "2026-08-23T00:00:00+00:00"


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_event_journal_load_rejects_non_standard_numeric_constants(
    tmp_path: Path,
    constant: str,
) -> None:
    memory = tmp_path / "memory"
    memory.mkdir(parents=True)
    (memory / "events.jsonl").write_text(
        "{"
        '"id":"event-1",'
        '"type":"message",'
        '"actor":"user",'
        f'"timestamp":"{_EVENT_TIMESTAMP}",'
        f'"payload":{{"content":"hello","score":{constant}}}'
        "}\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(tmp_path)

    with pytest.raises(
        CharacterDataError,
        match=r"events\.jsonl line 1: non-finite JSON number is not allowed",
    ):
        tuple(character.iter_events())


@pytest.mark.parametrize(
    "event_json",
    [
        (
            "{"
            '"id":"event-1",'
            '"type":"message",'
            '"actor":"assistant",'
            '"actor":"user",'
            f'"timestamp":"{_EVENT_TIMESTAMP}",'
            '"payload":{"content":"hello"}'
            "}\n"
        ),
        (
            "{"
            '"id":"event-1",'
            '"type":"message",'
            '"actor":"user",'
            f'"timestamp":"{_EVENT_TIMESTAMP}",'
            '"payload":{"content":"first","content":"second"}'
            "}\n"
        ),
    ],
)
def test_event_journal_load_rejects_duplicate_json_object_members(
    tmp_path: Path,
    event_json: str,
) -> None:
    memory = tmp_path / "memory"
    memory.mkdir(parents=True)
    (memory / "events.jsonl").write_text(event_json, encoding="utf-8")
    character = CharacterDirectory(tmp_path)

    with pytest.raises(
        CharacterDataError,
        match=r"events\.jsonl line 1: duplicate JSON object member",
    ):
        tuple(character.iter_events())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_append_event_rejects_non_finite_payload_without_mutating_journal_or_snapshot(
    tmp_path: Path,
    value: float,
) -> None:
    character = CharacterDirectory(tmp_path)
    original = Event(
        id="event-1",
        type="message",
        actor="user",
        timestamp=_EVENT_TIMESTAMP,
        payload={"content": "hello", "score": 1.0},
    )
    character.append_event(original)
    snapshot_before = tuple(character.iter_events())
    discovery_before = character.event_retrieval_source()
    journal_before = character.events_path.read_text(encoding="utf-8")

    rejected = Event(
        id="event-2",
        type="message",
        actor="user",
        timestamp=_EVENT_TIMESTAMP,
        payload={"content": "bad", "score": value},
    )

    with pytest.raises(CharacterDataError, match="cannot append events.jsonl"):
        character.append_event(rejected)

    assert character.events_path.read_text(encoding="utf-8") == journal_before
    assert tuple(character.iter_events()) == snapshot_before
    assert character.event_retrieval_source() is discovery_before


@pytest.mark.parametrize("payload", [[], "not-an-object", 7])
def test_append_event_rejects_non_object_payload_without_mutating_journal_or_snapshot(
    tmp_path: Path,
    payload: Any,
) -> None:
    character = CharacterDirectory(tmp_path)
    original = Event(
        id="event-1",
        type="message",
        actor="user",
        timestamp=_EVENT_TIMESTAMP,
        payload={"content": "hello"},
    )
    character.append_event(original)
    snapshot_before = tuple(character.iter_events())
    discovery_before = character.event_retrieval_source()
    journal_before = character.events_path.read_text(encoding="utf-8")

    rejected = Event(
        id="event-2",
        type="message",
        actor="user",
        timestamp=_EVENT_TIMESTAMP,
        payload=payload,
    )

    with pytest.raises(CharacterDataError, match="event payload must be an object"):
        character.append_event(rejected)

    assert character.events_path.read_text(encoding="utf-8") == journal_before
    assert tuple(character.iter_events()) == snapshot_before
    assert character.event_retrieval_source() is discovery_before


def test_event_journal_preserves_finite_numeric_payload_values(tmp_path: Path) -> None:
    character = CharacterDirectory(tmp_path)
    event = Event(
        id="event-1",
        type="message",
        actor="user",
        timestamp=_EVENT_TIMESTAMP,
        payload={"content": "hello", "score": 1.25},
    )

    character.append_event(event)

    reloaded = CharacterDirectory(tmp_path)
    assert tuple(reloaded.iter_events()) == (event,)
