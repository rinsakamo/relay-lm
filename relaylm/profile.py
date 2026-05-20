"""Character profile file loading placeholders for RelayLM MVP-2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from relaylm.compiler import ContextBlock, build_placeholder_persona_blocks
from relaylm.config import RelayLMConfig
from relaylm.routing import ResolvedRoute


@dataclass(frozen=True)
class ProfileFiles:
    common_runtime_policy: Path
    soul: Path
    output_policy: Path
    room_anchor: Path


@dataclass(frozen=True)
class ProfileTexts:
    common_runtime_policy: str
    soul: str
    output_policy: str
    room_anchor: str


class ProfileConfigurationError(ValueError):
    """Raised when route/profile config cannot resolve profile files."""


def read_text_file(path: str | Path) -> str:
    file_path = Path(path)
    return file_path.read_text(encoding="utf-8").strip()


def load_profile_texts(files: ProfileFiles) -> ProfileTexts:
    return ProfileTexts(
        common_runtime_policy=read_text_file(files.common_runtime_policy),
        soul=read_text_file(files.soul),
        output_policy=read_text_file(files.output_policy),
        room_anchor=read_text_file(files.room_anchor),
    )


def resolve_profile_files(config: RelayLMConfig, route: ResolvedRoute) -> ProfileFiles:
    if not route.character_id:
        raise ProfileConfigurationError(
            f"RelayLM route {route.route_model} does not define character_id."
        )

    character = config.characters.get(route.character_id)
    if character is None:
        raise ProfileConfigurationError(
            f"RelayLM route {route.route_model} references missing character: {route.character_id}"
        )

    common_runtime_policy = character.common_runtime_policy or config.common_runtime_policy
    if common_runtime_policy is None:
        raise ProfileConfigurationError(
            f"RelayLM character {route.character_id} does not define common_runtime_policy "
            "and no top-level common_runtime_policy is configured."
        )

    return ProfileFiles(
        common_runtime_policy=Path(common_runtime_policy),
        soul=Path(character.soul),
        output_policy=Path(character.output_policy),
        room_anchor=Path(character.room_anchor),
    )


def build_profile_blocks(files: ProfileFiles) -> list[ContextBlock]:
    texts = load_profile_texts(files)
    return build_placeholder_persona_blocks(
        common_runtime_policy=texts.common_runtime_policy,
        soul=texts.soul,
        output_policy=texts.output_policy,
        room_anchor=texts.room_anchor,
    )
