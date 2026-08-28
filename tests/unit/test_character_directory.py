from __future__ import annotations

import json
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


@pytest.mark.parametrize(
    ("config_text", "duplicate_key"),
    [
        (
            "format_version: 1\n"
            "format_version: 1\n"
            "character:\n"
            "  id: relm\n"
            "  name: ReLM\n",
            "format_version",
        ),
        (
            "format_version: 1\n"
            "character:\n"
            "  id: relm\n"
            "  id: other\n"
            "  name: ReLM\n",
            "id",
        ),
    ],
)
def test_config_rejects_duplicate_yaml_mapping_keys(
    tmp_path: Path,
    config_text: str,
    duplicate_key: str,
) -> None:
    character = _make_character(tmp_path)
    character.config_path.write_text(config_text, encoding="utf-8")

    with pytest.raises(
        CharacterDataError,
        match=rf"duplicate YAML mapping key: {duplicate_key}",
    ):
        character.load_config()


def test_config_format_version_does_not_coerce_string_compatibility(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    (tmp_path / "config.yaml").write_text(
        'format_version: "1"\ncharacter:\n  id: relm\n  name: ReLM\n',
        encoding="utf-8",
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


def test_duplicate_event_id_fails_closed_with_duplicate_line_number(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    character.events_path.write_text(
        '\n'.join(
            [
                '{"id":"evt-1","type":"message","actor":"user","timestamp":"t1","payload":{"content":"first"}}',
                '{"id":"evt-1","type":"message","actor":"assistant","timestamp":"t2","payload":{"content":"second"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(CharacterDataError, match=r"events\.jsonl line 2: duplicate event id 'evt-1'"):
        list(character.iter_events())


def test_append_event_rejects_duplicate_id_without_mutating_journal(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    first = Event.create(
        type="message",
        actor="user",
        payload={"content": "first"},
        event_id="evt-1",
        timestamp="2026-08-16T12:00:00+00:00",
    )
    duplicate = Event.create(
        type="message",
        actor="assistant",
        payload={"content": "second"},
        event_id="evt-1",
        timestamp="2026-08-16T12:00:01+00:00",
    )

    character.append_event(first)
    before = character.events_path.read_text(encoding="utf-8")

    with pytest.raises(CharacterDataError, match=r"duplicate event id 'evt-1'"):
        character.append_event(duplicate)

    assert character.events_path.read_text(encoding="utf-8") == before
    assert list(character.iter_events()) == [first]


@pytest.mark.parametrize(
    "payload",
    [
        {"states": []},
        {"format_version": 1},
        {"format_version": "1", "states": []},
    ],
)
def test_existing_state_file_requires_explicit_versioned_shape(
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    character = _make_character(tmp_path)
    character.state_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CharacterDataError):
        character.load_state()


@pytest.mark.parametrize("missing_field", ["value", "status", "sources"])
def test_persisted_state_record_does_not_receive_compatibility_defaults(
    tmp_path: Path,
    missing_field: str,
) -> None:
    character = _make_character(tmp_path)
    record: dict[str, object] = {
        "state_id": "state-1",
        "state_class": "user.preference",
        "key": "tea",
        "value": "likes",
        "status": "active",
        "sources": ["evt-1"],
    }
    del record[missing_field]
    character.state_path.write_text(
        json.dumps({"format_version": 1, "states": [record]}),
        encoding="utf-8",
    )

    with pytest.raises(CharacterDataError):
        character.load_state()


@pytest.mark.parametrize("sources", [[], [""], ["   "]])
def test_persisted_state_record_requires_non_empty_provenance_sources(
    tmp_path: Path,
    sources: list[str],
) -> None:
    character = _make_character(tmp_path)
    record = {
        "state_id": "state-1",
        "state_class": "user.preference",
        "key": "tea",
        "value": "likes",
        "status": "active",
        "sources": sources,
    }
    character.state_path.write_text(
        json.dumps({"format_version": 1, "states": [record]}),
        encoding="utf-8",
    )

    with pytest.raises(CharacterDataError, match="sources"):
        character.load_state()


def test_persisted_state_record_rejects_unknown_fields(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    record = {
        "state_id": "state-1",
        "state_class": "user.preference",
        "key": "tea",
        "value": "likes",
        "status": "active",
        "sources": ["evt-1"],
        "confidence": 0.9,
    }
    character.state_path.write_text(
        json.dumps({"format_version": 1, "states": [record]}),
        encoding="utf-8",
    )

    with pytest.raises(CharacterDataError):
        character.load_state()


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_persisted_state_rejects_non_finite_json_numbers(
    tmp_path: Path,
    constant: str,
) -> None:
    character = _make_character(tmp_path)
    state_json = (
        '{"format_version":1,"states":[{'
        '"state_id":"state-1","state_class":"user.fact","key":"score",'
        f'"value":{constant},"status":"active","sources":["evt-1"]'
        "}]}"
    )
    character.state_path.write_text(state_json, encoding="utf-8")

    with pytest.raises(CharacterDataError):
        character.load_state()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_save_state_rejects_non_finite_numbers_without_replacing_authority(
    tmp_path: Path,
    value: float,
) -> None:
    character = _make_character(tmp_path)
    before = character.state_path.read_text(encoding="utf-8")
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="state-1",
                state_class="user.fact",
                key="score",
                value=value,
                sources=("evt-1",),
            ),
        )
    )

    with pytest.raises(CharacterDataError):
        character.save_state(state)

    assert character.state_path.read_text(encoding="utf-8") == before
    assert not (tmp_path / "memory" / ".state.json.tmp").exists()
