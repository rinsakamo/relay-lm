from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CharacterConfig:
    """Stable identity metadata for a Character Package."""

    format_version: int
    character_id: str
    name: str

    def __post_init__(self) -> None:
        if self.format_version != 1:
            raise ValueError(f"unsupported character format_version: {self.format_version}")
        if not self.character_id.strip():
            raise ValueError("character.id must be a non-empty string")
        if not self.name.strip():
            raise ValueError("character.name must be a non-empty string")
