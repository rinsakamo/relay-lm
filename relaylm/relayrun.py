"""RelayRUN diagnostics skeleton for runtime orchestration metadata.

This module is intentionally side-effect free. It builds metadata-only artifacts
that can be attached to diagnostics or traces without mutating payloads,
changing backend forwarding, or writing checkpoints.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
import uuid

RunNodeStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed",
    "blocked",
    "skipped",
    "waiting_user",
]

ResumeMode = Literal[
    "none",
    "continue",
    "retry_node",
    "restart_from_safe_point",
    "require_user_confirmation",
]

DEFAULT_RELAYRUN_NODE_SEQUENCE: tuple[str, ...] = (
    "request_parse",
    "route_resolve",
    "ctx_compile",
    "token_policy",
    "scope_resolution",
    "input_relayemo",
    "input_relayscn",
    "relayref",
    "relaymem_retrieval",
    "relaymem_runtime_injection",
    "token_budget_truncation",
    "diagnostics_build",
    "backend_forward",
    "response_trace",
)


@dataclass(frozen=True)
class RelayRunStreamState:
    stream_requested: bool = False
    backend_stream_opened: bool = False
    first_token_sent: bool = False
    recovery_response_allowed: bool = True

    def to_log_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelayRunNode:
    node_name: str
    node_status: RunNodeStatus = "pending"
    started_at: str | None = None
    completed_at: str | None = None
    fallback_reason: str | None = None
    blocked_reasons: tuple[str, ...] = ()
    input_artifact_id: str | None = None
    output_artifact_id: str | None = None
    diagnostics_only: bool = True
    schema_version: str = "relayrun-node-0"

    def to_log_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blocked_reasons"] = list(self.blocked_reasons)
        return data


@dataclass(frozen=True)
class RelayRunFallbackSummary:
    fallback_applied: bool = False
    from_mode: str | None = None
    to_mode: str | None = None
    node_name: str | None = None
    reason: str | None = None
    user_visible: bool = False

    def to_log_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelayRunArtifactLineage:
    input_payload_artifact_id: str | None = None
    compiled_request_artifact_id: str | None = None
    relayemo_artifact_id: str | None = None
    relayscn_artifact_id: str | None = None
    relayref_artifact_id: str | None = None
    relaymem_retrieval_artifact_id: str | None = None
    runtime_ctx_injection_artifact_id: str | None = None
    backend_response_artifact_id: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelayRunDiagnosticsArtifact:
    run_id: str
    request_id: str
    turn_id: str | None = None
    route_model: str | None = None
    backend_name: str | None = None
    character_id: str | None = None
    stream_enabled: bool | None = None
    run_status: str = "diagnostics_only"
    resume_allowed: bool = False
    resume_mode: ResumeMode = "none"
    node_sequence: tuple[str, ...] = DEFAULT_RELAYRUN_NODE_SEQUENCE
    nodes: tuple[RelayRunNode, ...] = field(default_factory=tuple)
    stream_state: RelayRunStreamState = field(default_factory=RelayRunStreamState)
    fallback_summary: RelayRunFallbackSummary = field(default_factory=RelayRunFallbackSummary)
    artifact_lineage: RelayRunArtifactLineage = field(default_factory=RelayRunArtifactLineage)
    recovery_transition_artifact: dict[str, Any] | None = None
    diagnostics_only: bool = True
    checkpoint_written: bool = False
    schema_version: str = "relayrun-diagnostics-0"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "request_id": self.request_id,
            "turn_id": self.turn_id,
            "route_model": self.route_model,
            "backend_name": self.backend_name,
            "character_id": self.character_id,
            "stream_enabled": self.stream_enabled,
            "run_status": self.run_status,
            "resume_allowed": self.resume_allowed,
            "resume_mode": self.resume_mode,
            "node_sequence": list(self.node_sequence),
            "nodes": [node.to_log_dict() for node in self.nodes],
            "stream_state": self.stream_state.to_log_dict(),
            "fallback_summary": self.fallback_summary.to_log_dict(),
            "artifact_lineage": self.artifact_lineage.to_log_dict(),
            "recovery_transition_artifact": self.recovery_transition_artifact,
            "diagnostics_only": self.diagnostics_only,
            "checkpoint_written": self.checkpoint_written,
            "created_at": self.created_at,
        }


def new_run_id() -> str:
    """Return a RelayRUN-scoped run identifier."""

    return f"run_{uuid.uuid4()}"


def build_initial_relayrun_artifact(
    *,
    request_id: str,
    run_id: str | None = None,
    turn_id: str | None = None,
    route_model: str | None = None,
    backend_name: str | None = None,
    character_id: str | None = None,
    stream_enabled: bool | None = None,
    stream_state: RelayRunStreamState | None = None,
) -> dict[str, Any]:
    """Build a metadata-only RelayRUN diagnostics artifact.

    The artifact is safe to attach to diagnostics before full app-level node
    wiring exists. It never writes files and never mutates runtime payloads.
    """

    artifact = RelayRunDiagnosticsArtifact(
        run_id=run_id or new_run_id(),
        request_id=request_id,
        turn_id=turn_id,
        route_model=route_model,
        backend_name=backend_name,
        character_id=character_id,
        stream_enabled=stream_enabled,
        stream_state=stream_state or RelayRunStreamState(
            stream_requested=bool(stream_enabled),
            recovery_response_allowed=True,
        ),
    )
    return artifact.to_log_dict()


def build_relayrun_node(
    *,
    node_name: str,
    node_status: RunNodeStatus = "pending",
    fallback_reason: str | None = None,
    blocked_reasons: list[str] | tuple[str, ...] | None = None,
    input_artifact_id: str | None = None,
    output_artifact_id: str | None = None,
) -> dict[str, Any]:
    """Build one metadata-only RelayRUN node record."""

    node = RelayRunNode(
        node_name=str(node_name),
        node_status=node_status,
        fallback_reason=fallback_reason,
        blocked_reasons=tuple(str(reason) for reason in (blocked_reasons or ())),
        input_artifact_id=input_artifact_id,
        output_artifact_id=output_artifact_id,
    )
    return node.to_log_dict()
