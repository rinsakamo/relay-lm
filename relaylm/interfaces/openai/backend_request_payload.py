"""OpenAI backend request payload projection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from relaylm.interfaces.openai.client_instruction_source import strip_relaylm_control

if TYPE_CHECKING:
    from relaylm.routing import ResolvedRoute


def build_backend_request_payload(
    payload: Mapping[str, Any],
    route: ResolvedRoute,
) -> dict[str, Any]:
    """Build one detached payload for the selected OpenAI-compatible backend."""

    backend_payload = (
        dict(payload)
        if route.mode_applied == "pass_through"
        else strip_relaylm_control(payload)
    )
    backend_payload["model"] = route.backend_model
    return backend_payload
