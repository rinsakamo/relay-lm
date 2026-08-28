from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

import yaml

from relaylm.character import CharacterConfig
from relaylm.event_retrieval import EventDiscoveryIndex
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, StateRecord


class CharacterDataError(ValueError):
    """Raised when a Character Package contains invalid persisted data."""


class StateRevisionConflictError(CharacterDataError):
    """Raised when conditional persistence observes a changed State authority."""


_STATE_WRITE_LOCKS_GUARD = Lock()
_STATE_WRITE_LOCKS: dict[str, Any] = {}


class CharacterDirectory:
    """Filesystem-backed access to one portable Character Package."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._event_cache: tuple[Event, ...] = ()
        self._event_id_cache: set[str] = set()
        self._event_cache_signature: tuple[int, int, int, int] | None = None
        self._event_cache_loaded = False
        self._event_discovery_index: EventDiscoveryIndex | None = None
        self._event_discovery_signature: tuple[int, int, int, int] | None = None

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
                format_version=_required_int(raw, "format_version", "config.yaml: format_version"),
                character_id=_required_string(character, "id", "config.yaml: character.id"),
                name=_required_string(character, "name", "config.yaml: character.name"),
            )
        except (TypeError, ValueError) as exc:
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
        self._ensure_event_cache()
        return iter(self._event_cache)

    def event_retrieval_source(self) -> EventDiscoveryIndex:
        """Return derived lexical discovery tied to the validated Journal snapshot."""

        self._ensure_event_cache()
        if (
            self._event_discovery_index is None
            or self._event_discovery_signature != self._event_cache_signature
        ):
            self._event_discovery_index = EventDiscoveryIndex(self._event_cache)
            self._event_discovery_signature = self._event_cache_signature
        return self._event_discovery_index

    def _ensure_event_cache(self) -> None:
        signature = self._events_signature()
        if not self._event_cache_loaded or signature != self._event_cache_signature:
            snapshot = self._read_events_snapshot()
            signature_after_read = self._events_signature()
            if signature_after_read != signature:
                snapshot = self._read_events_snapshot()
                signature_after_read = self._events_signature()
            self._event_cache = snapshot
            self._event_id_cache = {event.id for event in snapshot}
            self._event_cache_signature = signature_after_read
            self._event_cache_loaded = True

    def _read_events_snapshot(self) -> tuple[Event, ...]:
        try:
            handle = self.events_path.open("r", encoding="utf-8")
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise CharacterDataError(f"cannot read events.jsonl: {exc}") from exc

        events: list[Event] = []
        event_ids: set[str] = set()
        with handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(
                        line,
                        object_pairs_hook=_reject_duplicate_json_object_members,
                        parse_constant=_reject_non_finite_json_number,
                    )
                    event = _event_from_mapping(raw)
                except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                    raise CharacterDataError(
                        f"events.jsonl line {line_number}: {exc}"
                    ) from exc
                if event.id in event_ids:
                    raise CharacterDataError(
                        f"events.jsonl line {line_number}: duplicate event id {event.id!r}"
                    )
                event_ids.add(event.id)
                events.append(event)
        return tuple(events)

    def _events_signature(self) -> tuple[int, int, int, int] | None:
        try:
            stat = self.events_path.stat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise CharacterDataError(f"cannot stat events.jsonl: {exc}") from exc
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)

    def append_event(self, event: Event) -> None:
        if not isinstance(event.payload, dict):
            raise CharacterDataError("event payload must be an object")
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self._ensure_event_cache()
        signature_before_append = self._events_signature()
        if signature_before_append != self._event_cache_signature:
            self._ensure_event_cache()
            signature_before_append = self._events_signature()
        if event.id in self._event_id_cache:
            raise CharacterDataError(f"cannot append events.jsonl: duplicate event id {event.id!r}")
        can_extend_cache = (
            self._event_cache_loaded
            and self._event_cache_signature == signature_before_append
        )
        can_extend_discovery = (
            can_extend_cache
            and self._event_discovery_index is not None
            and self._event_discovery_signature == signature_before_append
        )
        payload = {
            "id": event.id,
            "type": event.type,
            "actor": event.actor,
            "timestamp": event.timestamp,
            "payload": event.payload,
        }
        try:
            serialized = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.write("\n")
        except (OSError, TypeError, ValueError) as exc:
            raise CharacterDataError(f"cannot append events.jsonl: {exc}") from exc

        signature_after_append = None
        if can_extend_cache:
            try:
                signature_after_append = self._events_signature()
            except CharacterDataError:
                can_extend_cache = False

        if can_extend_cache:
            self._event_cache = (*self._event_cache, event)
            self._event_id_cache.add(event.id)
            self._event_cache_signature = signature_after_append
            if can_extend_discovery:
                assert self._event_discovery_index is not None
                self._event_discovery_index.append(event)
                self._event_discovery_signature = signature_after_append
            else:
                self._event_discovery_index = None
                self._event_discovery_signature = None
        else:
            self._event_cache = ()
            self._event_id_cache = set()
            self._event_cache_signature = None
            self._event_cache_loaded = False
            self._event_discovery_index = None
            self._event_discovery_signature = None

    def load_memory_markdown(self) -> str | None:
        try:
            return self.memory_markdown_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise CharacterDataError(f"cannot read MEMORY.md: {exc}") from exc

    def save_memory_markdown(
        self,
        content: str,
        *,
        expected_state_revision: str | None = None,
    ) -> bool:
        if expected_state_revision is None:
            return self._save_memory_markdown(content)
        with _state_write_lock(self.state_path):
            self._require_state_revision(expected_state_revision)
            return self._save_memory_markdown(content)

    def _save_memory_markdown(self, content: str) -> bool:
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
        state, _ = self.load_state_with_revision()
        return state

    def load_state_with_revision(self) -> tuple[CanonicalState, str]:
        """Load State with an opaque content revision for conditional persistence."""

        with _state_write_lock(self.state_path):
            content = self._read_state_text()
            if content is None:
                return CanonicalState(), _state_revision(None)
            return self._parse_state_text(content), _state_revision(content)

    def _read_state_text(self) -> str | None:
        try:
            return self.state_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise CharacterDataError(f"cannot read state.json: {exc}") from exc

    def _parse_state_text(self, content: str) -> CanonicalState:
        try:
            raw = json.loads(
                content,
                object_pairs_hook=_reject_duplicate_json_object_members,
                parse_constant=_reject_non_finite_json_number,
            )
        except ValueError as exc:
            raise CharacterDataError(f"cannot read state.json: {exc}") from exc

        if not isinstance(raw, dict):
            raise CharacterDataError("state.json must contain a JSON object")
        if "states" not in raw:
            raise CharacterDataError("state.json: states is required")
        states_raw = raw["states"]
        if not isinstance(states_raw, list):
            raise CharacterDataError("state.json: states must be an array")
        try:
            records = tuple(_state_record_from_mapping(item) for item in states_raw)
            return CanonicalState(
                format_version=_required_int(raw, "format_version", "state.json: format_version"),
                states=records,
            )
        except (TypeError, ValueError, KeyError) as exc:
            if isinstance(exc, CharacterDataError):
                raise
            raise CharacterDataError(f"state.json: {exc}") from exc

    def _require_state_revision(self, expected_revision: str) -> None:
        current_revision = _state_revision(self._read_state_text())
        if current_revision != expected_revision:
            raise StateRevisionConflictError("state revision changed before persistence")

    def save_state(
        self,
        state: CanonicalState,
        *,
        expected_revision: str | None = None,
    ) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        payload = {
            "format_version": state.format_version,
            "states": [_state_record_to_mapping(record) for record in state.states],
        }
        temporary = self.state_path.with_name(f".{self.state_path.name}.tmp")
        with _state_write_lock(self.state_path):
            if expected_revision is not None:
                self._require_state_revision(expected_revision)
            try:
                temporary.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
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


def _state_write_lock(path: Path):
    key = os.path.abspath(os.fspath(path))
    with _STATE_WRITE_LOCKS_GUARD:
        lock = _STATE_WRITE_LOCKS.get(key)
        if lock is None:
            lock = Lock()
            _STATE_WRITE_LOCKS[key] = lock
        return lock


def _state_revision(content: str | None) -> str:
    if content is None:
        return "absent"
    digest = sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _reject_non_finite_json_number(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _reject_duplicate_json_object_members(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object member: {key}")
        result[key] = value
    return result


def _required_int(mapping: dict[str, Any], key: str, label: str) -> int:
    if key not in mapping:
        raise CharacterDataError(f"{label} is required")
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise CharacterDataError(f"{label} must be an integer")
    return value


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
    allowed_fields = {
        "state_id",
        "state_class",
        "key",
        "value",
        "status",
        "sources",
        "valid_from",
        "valid_to",
    }
    unexpected_fields = set(raw) - allowed_fields
    if unexpected_fields:
        raise CharacterDataError(
            "state record contains unsupported fields: "
            + ", ".join(sorted(unexpected_fields))
        )
    if "value" not in raw:
        raise CharacterDataError("state.value is required")
    if "sources" not in raw:
        raise CharacterDataError("state.sources is required")
    sources = raw["sources"]
    if (
        not isinstance(sources, list)
        or not sources
        or not all(isinstance(item, str) and item.strip() for item in sources)
    ):
        raise CharacterDataError(
            "state record sources must be a non-empty array of non-empty strings"
        )
    status = _required_string(raw, "status", "state.status")
    return StateRecord(
        state_id=_required_string(raw, "state_id", "state.state_id"),
        state_class=_required_string(raw, "state_class", "state.state_class"),
        key=_required_string(raw, "key", "state.key"),
        value=raw["value"],
        sources=tuple(sources),
        status=status,
        valid_from=_optional_string(raw.get("valid_from"), "state.valid_from"),
        valid_to=_optional_string(raw.get("valid_to"), "state.valid_to"),
    )


def _state_record_to_mapping(record: StateRecord) -> dict[str, Any]:
    if (
        not record.sources
        or not all(isinstance(item, str) and item.strip() for item in record.sources)
    ):
        raise CharacterDataError(
            "state record sources must be a non-empty array of non-empty strings"
        )
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
