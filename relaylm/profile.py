"""Character profile file loading placeholders for RelayLM MVP-2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from relaylm.compiler import ContextBlock, build_placeholder_persona_blocks


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


def build_profile_blocks(files: ProfileFiles) -> list[ContextBlock]:
    texts = load_profile_texts(files)
    return build_placeholder_persona_blocks(
        common_runtime_policy=texts.common_runtime_policy,
        soul=texts.soul,
        output_policy=texts.output_policy,
        room_anchor=texts.room_anchor,
    )
