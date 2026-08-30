from __future__ import annotations

from dataclasses import dataclass

from relaylm.character import CharacterConfig
from relaylm.cognitive import KnowledgeItem
from relaylm.storage.filesystem import (
    CharacterDataError,
    CharacterDirectory,
    _required_int,
    _required_string,
)


CognitivePackageDataError = CharacterDataError

KNOWLEDGE_MAX_FILES = 32
KNOWLEDGE_MAX_FILE_BYTES = 64 * 1024
KNOWLEDGE_MAX_TOTAL_BYTES = 256 * 1024
_KNOWLEDGE_SUFFIXES = frozenset({".md", ".txt"})


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

    @property
    def knowledge_path(self):
        return self.root / "knowledge"

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

    def load_knowledge(self) -> tuple[KnowledgeItem, ...]:
        """Load the optional bounded read-only package knowledge catalog."""

        root = self.knowledge_path
        if not root.exists():
            return ()
        if root.is_symlink():
            raise CognitivePackageDataError("knowledge directory must not be a symlink")
        if not root.is_dir():
            raise CognitivePackageDataError("knowledge must be a directory")

        paths = sorted(
            root.rglob("*"),
            key=lambda path: path.relative_to(self.root).as_posix(),
        )
        files = []
        for path in paths:
            if path.is_symlink():
                raise CognitivePackageDataError(
                    f"knowledge asset must not be a symlink: {path.relative_to(self.root).as_posix()}"
                )
            if path.is_dir():
                continue
            if not path.is_file():
                raise CognitivePackageDataError(
                    f"knowledge asset must be a regular file: {path.relative_to(self.root).as_posix()}"
                )
            files.append(path)

        if len(files) > KNOWLEDGE_MAX_FILES:
            raise CognitivePackageDataError(
                f"knowledge file count exceeds limit {KNOWLEDGE_MAX_FILES}"
            )

        total_bytes = 0
        items: list[KnowledgeItem] = []
        for path in files:
            location = path.relative_to(self.root).as_posix()
            if path.suffix.lower() not in _KNOWLEDGE_SUFFIXES:
                raise CognitivePackageDataError(
                    f"unsupported knowledge asset type: {location}"
                )
            try:
                payload = path.read_bytes()
            except OSError as exc:
                raise CognitivePackageDataError(
                    f"cannot read knowledge asset {location}: {exc}"
                ) from exc
            size = len(payload)
            if size > KNOWLEDGE_MAX_FILE_BYTES:
                raise CognitivePackageDataError(
                    f"knowledge asset exceeds per-file byte limit: {location}"
                )
            total_bytes += size
            if total_bytes > KNOWLEDGE_MAX_TOTAL_BYTES:
                raise CognitivePackageDataError("knowledge total byte limit exceeded")
            try:
                content = payload.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise CognitivePackageDataError(
                    f"knowledge asset is not valid UTF-8: {location}"
                ) from exc
            if "\x00" in content:
                raise CognitivePackageDataError(
                    f"knowledge asset contains NUL text: {location}"
                )
            try:
                items.append(KnowledgeItem(content=content, location=location))
            except ValueError as exc:
                raise CognitivePackageDataError(
                    f"invalid knowledge asset {location}: {exc}"
                ) from exc
        return tuple(items)
