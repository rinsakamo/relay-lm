"""Request-local PipelineContext for RelayLM."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from relaylm.routing import ResolvedRoute


@dataclass
class PipelineContext:
    """Carry immutable input and mutable forwarding payload state."""

    request_id: str
    run_id: str
    original_payload: Mapping[str, Any]
    forwarded_payload: dict[str, Any]
    route: ResolvedRoute
    stream_enabled: bool
    last_mutating_step: str | None = None

    def replace_forwarded_payload(
        self,
        new_payload: Mapping[str, Any],
        mutating_step: str,
    ) -> None:
        self.forwarded_payload = dict(new_payload)
        self.last_mutating_step = mutating_step
