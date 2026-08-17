from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.event_retrieval import EventDiscoveryIndex, select_event_evidence
from relaylm.events import Event
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory


def _event(
    event_id: str,
    content: str,
    *,
    event_type: str = "message",
    timestamp: str = "2026-08-17T00:00:00+00:00",
) -> Event:
    return Event(
        id=event_id,
        type=event_type,
        actor="user",
        timestamp=timestamp,
        payload={"content": content},
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


class CountingDiscoveryIndex(EventDiscoveryIndex):
    def __init__(self, events: tuple[Event, ...]) -> None:
        super().__init__(events)
        self.event_reads = 0

    def event_at(self, index: int) -> Event:
        self.event_reads += 1
        return super().event_at(index)


def test_indexed_selection_preserves_existing_selector_semantics() -> None:
    older = _event("older", "Coffee preference changed.")
    irrelevant = _event("irrelevant", "Rin visited Fukuoka.")
    oversized = _event("oversized", "Coffee preference " + "details " * 20)
    newer = _event("newer", "Preference for coffee was confirmed.")
    current = _event("current", "Coffee preference coffee current.")
    events = (older, irrelevant, oversized, newer, current)
    source = EventDiscoveryIndex(events)

    selected = select_event_evidence(
        events=source,
        query="coffee preference",
        max_events=2,
        max_chars=len(older.payload["content"]) + len(newer.payload["content"]),
        exclude_event_ids=(current.id,),
    )

    assert selected == (older, newer)


def test_indexed_selection_does_not_inspect_the_full_validated_snapshot() -> None:
    irrelevant = tuple(
        _event(f"irrelevant-{index}", f"unrelated note {index}")
        for index in range(1000)
    )
    older = _event("older", "Coffee note.")
    newer = _event("newer", "Coffee update.")
    source = CountingDiscoveryIndex((*irrelevant, older, newer))
    source.event_reads = 0

    selected = select_event_evidence(
        events=source,
        query="coffee",
        max_events=1,
        max_chars=100,
    )

    assert selected == (newer,)
    assert source.event_reads == 2


def test_character_directory_extends_derived_discovery_on_owned_append(tmp_path: Path) -> None:
    memory = tmp_path / "memory"
    memory.mkdir(parents=True)
    first = _event("first", "Coffee note.")
    (memory / "events.jsonl").write_text(_event_line(first), encoding="utf-8")
    character = CharacterDirectory(tmp_path)

    source = character.event_retrieval_source()
    second = _event("second", "Coffee update.")
    character.append_event(second)

    selected = select_event_evidence(
        events=character.event_retrieval_source(),
        query="coffee",
        max_events=1,
        max_chars=100,
    )

    assert character.event_retrieval_source() is source
    assert selected == (second,)


def test_external_mutation_revalidates_authority_before_rebuilding_discovery(tmp_path: Path) -> None:
    memory = tmp_path / "memory"
    memory.mkdir(parents=True)
    first = _event("first", "Coffee note.")
    events_path = memory / "events.jsonl"
    events_path.write_text(_event_line(first), encoding="utf-8")
    character = CharacterDirectory(tmp_path)

    initial_source = character.event_retrieval_source()
    events_path.write_text("not-json\n", encoding="utf-8")

    with pytest.raises(CharacterDataError, match="line 1"):
        character.event_retrieval_source()

    second = _event("second", "Coffee update.")
    events_path.write_text(_event_line(first) + _event_line(second), encoding="utf-8")
    rebuilt_source = character.event_retrieval_source()

    assert rebuilt_source is not initial_source
    assert select_event_evidence(
        events=rebuilt_source,
        query="coffee",
        max_events=1,
        max_chars=100,
    ) == (second,)


def test_reopen_rebuilds_discovery_from_authoritative_journal(tmp_path: Path) -> None:
    memory = tmp_path / "memory"
    memory.mkdir(parents=True)
    first = _event("first", "Coffee note.")
    (memory / "events.jsonl").write_text(_event_line(first), encoding="utf-8")

    first_character = CharacterDirectory(tmp_path)
    first_source = first_character.event_retrieval_source()
    reopened_character = CharacterDirectory(tmp_path)
    reopened_source = reopened_character.event_retrieval_source()

    assert reopened_source is not first_source
    assert select_event_evidence(
        events=reopened_source,
        query="coffee",
        max_events=1,
        max_chars=100,
    ) == (first,)
