"""Phase 5-C4a runtime selection helpers."""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from relaylm.client_history_exclusion_preflight import (
    ClientHistoryExclusionPreflightResult,
)
from relaylm.client_instruction_identity import ClientInstructionIdentityResult

if TYPE_CHECKING:
    from relaylm.pipeline_context import PipelineContext


_INSTRUCTION_ROLES = frozenset({"system", "developer"})


def request_uses_instruction_bearing_v1(
    pipeline_context: PipelineContext,
) -> bool:
    """Select v1 from typed metadata, with a bounded role fallback."""

    preflight = pipeline_context.client_history_exclusion_preflight_result
    if (
        isinstance(preflight, ClientHistoryExclusionPreflightResult)
        and preflight.instruction_message_count > 0
    ):
        return True

    identity_result = pipeline_context.client_instruction_identity_result
    if (
        isinstance(identity_result, ClientInstructionIdentityResult)
        and identity_result.identity is not None
        and bool(identity_result.identity.candidates)
    ):
        return True

    messages = pipeline_context.original_payload.get("messages")
    return bool(
        isinstance(messages, list)
        and any(
            isinstance(message, Mapping)
            and message.get("role") in _INSTRUCTION_ROLES
            for message in messages
        )
    )
