"""Detached payload rendering for the Phase 5-C4a apply contract."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from relaylm.client_history_exclusion_apply_v1_prepare import (
    PreparedClientHistoryExclusionApplyV1,
)
from relaylm.client_instruction_source import strip_relaylm_control
from relaylm.request_compiler import (
    render_compiled_context_blocks_runtime_private,
)


@dataclass(frozen=True, repr=False)
class RenderedClientHistoryExclusionApplyV1:
    payload: dict[str, Any]
    message_count: int


def render_client_history_exclusion_apply_v1(
    prepared: PreparedClientHistoryExclusionApplyV1,
) -> RenderedClientHistoryExclusionApplyV1 | None:
    """Create a detached payload from the prepared typed state."""

    try:
        messages = render_compiled_context_blocks_runtime_private(
            blocks=prepared.replaced_blocks,
            recent_messages=[
                deepcopy(dict(prepared.validated.current_user_message))
            ],
        )
    except Exception:
        return None
    payload = deepcopy(
        strip_relaylm_control(prepared.validated.compiled_payload)
    )
    payload["messages"] = messages
    return RenderedClientHistoryExclusionApplyV1(
        payload=payload,
        message_count=len(messages),
    )
