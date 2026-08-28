from __future__ import annotations

from dataclasses import dataclass

from relaylm.character import CharacterConfig
from relaylm.storage.filesystem import (
    CharacterDataError,
    CharacterDirectory,
    _required_int,
    _required_string,
)


CognitivePackageDataError = CharacterDataError


@dataclass(frozen=True, slots=True)
class CognitivePackageConfig:
    """Stable metadata required by the general Cognitive Package boundary."""

    format_version: int
    package_id: str

    def __post_init__(self) -> None:
        if self.format_version != 1:
            raise ValueError(
                f"unsupported cognitive package format_version: {self.format_version}"
            )
        if not self.package_id.strip():
            raise ValueError("package.id must be a non-empty string")


class CognitivePackageDirectory(CharacterDirectory):
    """Filesystem-backed access to one portable Cognitive Package root.

    The inherited persistence implementation is intentionally shared with the
    existing Character Package adapter so State, Event, MEMORY, duplicate-key,
    and stale-write fail-closed semantics cannot diverge by package role.
    """

    def load_config(self) -> CognitivePackageConfig:
        raw = self._load_yaml_mapping(self.config_path)
        has_package = "package" in raw
        has_character = "character" in raw
        if has_package == has_character:
            raise CognitivePackageDataError(
                "config.yaml must define exactly one package or character identity mapping"
            )

        package = raw.get("package")
        character = raw.get("character")
        if has_package and not isinstance(package, dict):
            raise CognitivePackageDataError("config.yaml: package must be a mapping")
        if has_character and not isinstance(character, dict):
            raise CognitivePackageDataError("config.yaml: character must be a mapping")

        try:
            format_version = _required_int(
                raw,
                "format_version",
                "config.yaml: format_version",
            )
            if has_package:
                assert isinstance(package, dict)
                package_id = _required_string(
                    package,
                    "id",
                    "config.yaml: package.id",
                )
            else:
                assert isinstance(character, dict)
                character_config = CharacterConfig(
                    format_version=format_version,
                    character_id=_required_string(
                        character,
                        "id",
                        "config.yaml: character.id",
                    ),
                    name=_required_string(
                        character,
                        "name",
                        "config.yaml: character.name",
                    ),
                )
                package_id = character_config.character_id
            return CognitivePackageConfig(
                format_version=format_version,
                package_id=package_id,
            )
        except (TypeError, ValueError) as exc:
            if isinstance(exc, CognitivePackageDataError):
                raise
            raise CognitivePackageDataError(f"config.yaml: {exc}") from exc
