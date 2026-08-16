from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Event:
    """One persisted occurrence/provenance record."""

    id: str
    type: str
    actor: str
    timestamp: str
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("event id must not be empty")
        if not self.type.strip():
            raise ValueError("event type must not be empty")
        if not self.actor.strip():
            raise ValueError("event actor must not be empty")
        if not self.timestamp.strip():
            raise ValueError("event timestamp must not be empty")

    @classmethod
    def create(
        cls,
        *,
        type: str,
        actor: str,
        payload: dict[str, Any],
        event_id: str | None = None,
        timestamp: str | None = None,
    ) -> "Event":
        return cls(
            id=event_id or str(uuid4()),
            type=type,
            actor=actor,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            payload=dict(payload),
        )
