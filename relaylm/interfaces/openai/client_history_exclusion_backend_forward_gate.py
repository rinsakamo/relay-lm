"""Content-free backend-forward policy for client-history exclusion."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from relaylm.interfaces.openai.client_history_exclusion_apply_runtime import (
    ClientHistoryExclusionApplyRuntimeResult,
    client_history_exclusion_apply_blocks_backend,
    client_history_exclusion_apply_failure_reason,
)
from relaylm.routing import ResolvedRoute


@dataclass(frozen=True)
class ClientHistoryExclusionBackendForwardDecision:
    allowed: bool
    failure_reason: str | None = None


def decide_client_history_exclusion_backend_forward(
    *,
    route: ResolvedRoute,
    result: ClientHistoryExclusionApplyRuntimeResult | None,
    forwarded_payload: Mapping[str, object],
) -> ClientHistoryExclusionBackendForwardDecision:
    """Return one content-free allow/block decision before backend I/O."""

    blocked = client_history_exclusion_apply_blocks_backend(
        route,
        result,
        forwarded_payload=forwarded_payload,
    )
    if not blocked:
        return ClientHistoryExclusionBackendForwardDecision(allowed=True)
    return ClientHistoryExclusionBackendForwardDecision(
        allowed=False,
        failure_reason=client_history_exclusion_apply_failure_reason(result),
    )
