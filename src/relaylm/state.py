from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class StateRecord:
    """One accepted current-state record."""

    state_id: str
    state_class: str
    key: str
    value: Any
    sources: tuple[str, ...] = ()
    status: str = "active"
    valid_from: str | None = None
    valid_to: str | None = None

    def __post_init__(self) -> None:
        if not self.state_id.strip():
            raise ValueError("state_id must not be empty")
        if not self.state_class.strip():
            raise ValueError("state_class must not be empty")
        if not self.key.strip():
            raise ValueError("state key must not be empty")


@dataclass(frozen=True, slots=True)
class CanonicalState:
    """The accepted current understanding for a character."""

    format_version: int = 1
    states: tuple[StateRecord, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.format_version != 1:
            raise ValueError(f"unsupported state format_version: {self.format_version}")
