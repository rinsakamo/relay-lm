from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

import yaml

from relaylm.character import CharacterConfig
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, StateRecord


class CharacterDataError(ValueError):
    """Raised when a Character Package contains invalid persisted data."""


class CharacterDirectory:
    """Filesystem-backed access to one portable Character Package."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @property
    def config_path(self) -> Path:
        return self.root / "config.yaml"

    @property
    def soul_path(self) -> Path:
        return self.root / "SOUL.md"

    @property
    def memory_path(self) -> Path:
        return self.root / "memory"

    @property
    def events_path(self) -> Path:
        return self.memory_path / "events.jsonl"

    @property
    def state_path(self) -> Path:
        return self.memory_path / "state.json"

    @property
    def memory_markdown_path(self) -> Path:
        return self.memory_path / "MEMORY.md"

    def load_config(self) -> CharacterConfig:
        raw = self._load_yaml_mapping(self.config_path)
        character = raw.get("character")
        if not isinstance(character, dict):
            raise CharacterDataError("config.yaml: character must be a mapping")
        try:
            return CharacterConfig(
                format_version=int(raw["format_version"]),
                character_id=_required_string(character, "id", "config.yaml: character.id"),
                name=_required_string(character, "name", "config.yaml: character.name"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, CharacterDataError):
                raise
            raise CharacterDataError(f"config.yaml: {exc}") from exc

    def load_identity(self) -> Identity:
        try:
            content = self.soul_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CharacterDataError(f"cannot read SOUL.md: {exc}") from exc
        try:
            return Identity(content=content)
        except ValueError as exc:
            raise CharacterDataError(str(exc)) from exc

    def iter_events(self) -> Iterator[Event]:
        try:
            handle = self.events_path.open("r", encoding="utf-8")
        except FileNotFoundError:
            return
        except OSError as exc:
            raise CharacterDataError(f"cannot read events.jsonl: {exc}") from exc

        with handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                    yield _event_from_mapping(raw)
                except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                    raise CharacterDataError(
                        f"events.jsonl line {line_number}: {exc}"
                    ) from exc

    def append_event(self, event: Event) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        payload = {
            "id": event.id,
            "type": event.type,
            "actor": event.actor,
            "timestamp": event.timestamp,
            "payload": event.payload,
        }
        try:
            with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
                handle.write("\n")
        except (OSError, TypeError, ValueError) as exc:
            raise CharacterDataError(f"cannot append events.jsonl: {exc}") from exc

    def load_memory_markdown(self) -> str | None:
        try:
            return self.memory_markdown_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise CharacterDataError(f"cannot read MEMORY.md: {exc}") from exc

    def save_memory_markdown(self, content: str) -> bool:
        if not content.strip():
            raise CharacterDataError("MEMORY.md must not be empty")
        current = self.load_memory_markdown()
        if current == content:
            return False

        self.memory_path.mkdir(parents=True, exist_ok=True)
        temporary = self.memory_markdown_path.with_name(f".{self.memory_markdown_path.name}.tmp")
        try:
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, self.memory_markdown_path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise CharacterDataError(f"cannot write MEMORY.md: {exc}") from exc
        return True

    def load_state(self) -> CanonicalState:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return CanonicalState()
        except (OSError, json.JSONDecodeError) as exc:
            raise CharacterDataError(f"cannot read state.json: {exc}") from exc

        if not isinstance(raw, dict):
            raise CharacterDataError("state.json must contain a JSON object")
        states_raw = raw.get("states", [])
        if not isinstance(states_raw, list):
            raise CharacterDataError("state.json: states must be an array")
        try:
            records = tuple(_state_record_from_mapping(item) for item in states_raw)
            return CanonicalState(
                format_version=int(raw.get("format_version", 1)),
                states=records,
            )
        except (TypeError, ValueError, KeyError) as exc:
            if isinstance(exc, CharacterDataError):
                raise
            raise CharacterDataError(f"state.json: {exc}") from exc

    def save_state(self, state: CanonicalState) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        payload = {
            "format_version": state.format_version,
            "states": [_state_record_to_mapping(record) for record in state.states],
        }
        temporary = self.state_path.with_name(f".{self.state_path.name}.tmp")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, self.state_path)
        except (OSError, TypeError, ValueError) as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise CharacterDataError(f"cannot write state.json: {exc}") from exc

    @staticmethod
    def _load_yaml_mapping(path: Path) -> dict[str, Any]:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise CharacterDataError(f"cannot read config.yaml: {exc}") from exc
        if not isinstance(raw, dict):
            raise CharacterDataError("config.yaml must contain a mapping")
        return raw


def _required_string(mapping: dict[str, Any], key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CharacterDataError(f"{label} must be a non-empty string")
    return value


def _event_from_mapping(raw: Any) -> Event:
    if not isinstance(raw, dict):
        raise CharacterDataError("event must be an object")
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise CharacterDataError("event payload must be an object")
    return Event(
        id=_required_string(raw, "id", "event.id"),
        type=_required_string(raw, "type", "event.type"),
        actor=_required_string(raw, "actor", "event.actor"),
        timestamp=_required_string(raw, "timestamp", "event.timestamp"),
        payload=dict(payload),
    )


def _state_record_from_mapping(raw: Any) -> StateRecord:
    if not isinstance(raw, dict):
        raise CharacterDataError("state record must be an object")
    sources = raw.get("sources", [])
    if not isinstance(sources, list) or not all(isinstance(item, str) for item in sources):
        raise CharacterDataError("state record sources must be an array of strings")
    return StateRecord(
        state_id=_required_string(raw, "state_id", "state.state_id"),
        state_class=_required_string(raw, "state_class", "state.state_class"),
        key=_required_string(raw, "key", "state.key"),
        value=raw.get("value"),
        sources=tuple(sources),
        status=str(raw.get("status", "active")),
        valid_from=_optional_string(raw.get("valid_from"), "state.valid_from"),
        valid_to=_optional_string(raw.get("valid_to"), "state.valid_to"),
    )


def _state_record_to_mapping(record: StateRecord) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "state_id": record.state_id,
        "state_class": record.state_class,
        "key": record.key,
        "value": record.value,
        "status": record.status,
        "sources": list(record.sources),
    }
    if record.valid_from is not None:
        payload["valid_from"] = record.valid_from
    if record.valid_to is not None:
        payload["valid_to"] = record.valid_to
    return payload


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CharacterDataError(f"{label} must be a string or null")
    return value
