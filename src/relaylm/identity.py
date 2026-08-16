from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Identity:
    """Human-authored stable character identity loaded from SOUL.md."""

    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("SOUL.md must not be empty")
