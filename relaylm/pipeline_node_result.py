"""Diagnostics-only result shape for RelayLM pipeline steps.

Phase 4.5 uses this module to record what happened at a pipeline node without
changing runtime routing, backend forwarding, response handling, or RelayRUN
checkpoint behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal


PipelineNodeStatus = Literal[
    "applied",
    "skipped",
    "blocked",
    "failed",
    "diagnostic_only",
]


@dataclass(frozen=True)
class PipelineNodeResult:
    """Record one pipeline node outcome without deciding the next route."""

    node_name: str
    status: PipelineNodeStatus
    decision: str | None = None
    blocked_reasons: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def to_log_dict(self) -> dict[str, Any]:
        """Return a detached JSON-friendly diagnostics representation."""

        return {
            "node_name": self.node_name,
            "status": self.status,
            "decision": self.decision,
            "blocked_reasons": list(self.blocked_reasons),
            "diagnostics": dict(self.diagnostics),
            "artifacts": [dict(artifact) for artifact in self.artifacts],
        }


def build_pipeline_node_result(
    *,
    node_name: str,
    status: PipelineNodeStatus,
    decision: str | None = None,
    blocked_reasons: Sequence[str] | None = None,
    diagnostics: Mapping[str, Any] | None = None,
    artifacts: Sequence[Mapping[str, Any]] | None = None,
) -> PipelineNodeResult:
    """Build a detached diagnostics-only pipeline node result.

    Inputs are copied so later mutation of caller-owned containers does not
    replace the top-level record fields. This helper does not perform routing,
    fallback, retry, short-circuit, response mutation, or backend control.
    """

    return PipelineNodeResult(
        node_name=str(node_name),
        status=status,
        decision=str(decision) if decision is not None else None,
        blocked_reasons=[str(reason) for reason in (blocked_reasons or ())],
        diagnostics=dict(diagnostics or {}),
        artifacts=[dict(artifact) for artifact in (artifacts or ())],
    )
