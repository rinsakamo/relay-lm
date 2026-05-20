"""Dry-run profile compilation planning for RelayLM MVP-2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from relaylm.compiler import compile_profile_messages_with_system_fallback
from relaylm.config import RelayLMConfig
from relaylm.profile import (
    ProfileConfigurationError,
    build_profile_blocks,
    resolve_profile_files,
)
from relaylm.routing import ResolvedRoute


@dataclass(frozen=True)
class ProfileCompilePlan:
    enabled: bool
    route_model: str
    character_id: str | None
    compiled_block_count: int = 0
    compiled_message_count: int = 0
    incoming_message_count: int = 0
    incoming_system_message_count: int = 0
    fallback_reason: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_profile_compile_plan(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
    incoming_messages: list[dict[str, Any]],
) -> ProfileCompilePlan:
    """Build a dry-run profile compilation plan without mutating request payloads."""

    try:
        profile_files = resolve_profile_files(config, route)
        blocks = build_profile_blocks(profile_files)
        compiled_messages = compile_profile_messages_with_system_fallback(
            blocks,
            incoming_messages,
        )
    except (FileNotFoundError, ProfileConfigurationError) as exc:
        return ProfileCompilePlan(
            enabled=False,
            route_model=route.route_model,
            character_id=route.character_id,
            incoming_message_count=len(incoming_messages),
            incoming_system_message_count=_count_system_messages(incoming_messages),
            fallback_reason=exc.__class__.__name__,
        )

    return ProfileCompilePlan(
        enabled=True,
        route_model=route.route_model,
        character_id=route.character_id,
        compiled_block_count=len(blocks),
        compiled_message_count=len(compiled_messages),
        incoming_message_count=len(incoming_messages),
        incoming_system_message_count=_count_system_messages(incoming_messages),
        fallback_reason=None,
    )


def _count_system_messages(messages: list[dict[str, Any]]) -> int:
    return sum(1 for message in messages if message.get("role") == "system")
