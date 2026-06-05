"""RelayRUN diagnostics skeleton for runtime orchestration metadata.

This module is intentionally side-effect free. It builds metadata-only artifacts
that can be attached to diagnostics or traces without mutating payloads,
changing backend forwarding, or writing checkpoints.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
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

RUNTIME_CHECKPOINT_NODE_SEQUENCE: tuple[str, ...] = (
    "request_received",
    "relayscn",
    "relayref",
    "relaymem_retrieval",
    "relaymem_runtime_ctx",
    "token_budget_truncation",
    "backend_forward",
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
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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


def build_relayrun_checkpoint_persistence_plan(
    *,
    run_id: str,
    turn_id: str | None = None,
    request_id: str | None = None,
    target_root: str = ".relayrun/checkpoints",
    checkpoint_persisted: bool = False,
) -> dict[str, Any]:
    """Build a diagnostics-only preview for future checkpoint persistence.

    The plan is intentionally side-effect free: it does not create directories,
    write checkpoint files, allow resume, or apply recovery transitions. When a
    durable turn identifier is not available yet, the request id is used only as
    the preview path segment so diagnostics can show a stable intended shape.
    """

    preview_turn_id = turn_id or request_id or "turn_unknown"
    safe_target_root = target_root.rstrip("/") or ".relayrun/checkpoints"
    target_path_preview = f"{safe_target_root}/{run_id}/{preview_turn_id}.json"

    return {
        "schema_version": "relayrun.checkpoint_persistence_plan.v0",
        "diagnostics_only": True,
        "write_allowed": False,
        "checkpoint_persisted": bool(checkpoint_persisted),
        "target_root": safe_target_root,
        "target_path_preview": target_path_preview,
        "run_id": run_id,
        "turn_id": preview_turn_id,
        "blocked_reasons": [
            "checkpoint_persistence_not_implemented",
            "checkpoint_write_disabled",
        ],
        "resume_allowed_after_persist": False,
    }


def build_relayrun_checkpoint_writer_preflight(
    *,
    target_root: str,
    target_path_preview: str,
) -> dict[str, Any]:
    """Build diagnostics-only checkpoint writer preflight metadata.

    This helper only describes the future writer gates. It must not create
    directories, write checkpoint files, include backend payload/content text,
    enable resume/retry, or apply recovery transitions.
    """

    path_segments = target_path_preview.split("/")
    root_segments = target_root.split("/")
    path_traversal_detected = ".." in path_segments or ".." in root_segments
    absolute_path_detected = target_path_preview.startswith("/") or target_root.startswith(
        "/"
    )

    return {
        "schema_version": "relayrun.checkpoint_writer_preflight.v0",
        "diagnostics_only": True,
        "write_allowed": False,
        "preflight_passed": False,
        "checkpoint_write_attempted": False,
        "directory_creation_attempted": False,
        "target_root": target_root,
        "target_path_preview": target_path_preview,
        "path_safety": {
            "root_relative": not absolute_path_detected,
            "path_traversal_detected": path_traversal_detected,
            "absolute_path_detected": absolute_path_detected,
        },
        "content_policy": {
            "content_free": True,
            "backend_payload_included": False,
            "response_text_included": False,
            "raw_user_message_included": False,
        },
        "blocked_reasons": [
            "checkpoint_writer_not_implemented",
            "checkpoint_write_disabled",
        ],
        "future_writer_required_gates": [
            "explicit_config_enabled",
            "safe_target_root",
            "content_free_payload",
            "atomic_write",
            "idempotent_run_turn_key",
        ],
    }



def build_relayrun_resume_preflight(
    *,
    resume_preflight_enabled: bool = False,
    resume_dry_run_only: bool = True,
    checkpoint_path: str | None = None,
    checkpoint_root: str = ".relayrun/checkpoints",
) -> dict[str, Any]:
    """Build diagnostics-only resume readiness metadata.

    This helper may read and validate a candidate checkpoint envelope when
    explicitly enabled, but it never applies resume, retry, or recovery
    transitions.
    """

    blocked_reasons = ["resume_not_implemented"]
    if not resume_preflight_enabled:
        blocked_reasons.append("resume_disabled")
    if resume_dry_run_only:
        blocked_reasons.append("resume_dry_run_only")

    artifact: dict[str, Any] = {
        "schema_version": "relayrun.resume_preflight.v0",
        "diagnostics_only": True,
        "resume_allowed": False,
        "resume_attempted": False,
        "resume_applied": False,
        "checkpoint_read_attempted": False,
        "checkpoint_read_ok": False,
        "checkpoint_schema_valid": False,
        "content_free": None,
        "source_checkpoint_path": None,
        "blocked_reasons": blocked_reasons,
        "future_resume_required_gates": [
            "explicit_config_enabled",
            "valid_checkpoint_schema",
            "content_free_checkpoint",
            "safe_resume_mode",
            "user_or_policy_confirmation",
        ],
    }

    if not checkpoint_path:
        return artifact

    artifact["source_checkpoint_path"] = checkpoint_path
    checkpoint_root_path = Path(checkpoint_root)
    candidate_path = Path(checkpoint_path)
    if candidate_path.is_absolute() or checkpoint_root_path.is_absolute():
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["resume_checkpoint_absolute_path_detected"]
        )
        return artifact
    if ".." in candidate_path.parts or ".." in checkpoint_root_path.parts:
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["resume_checkpoint_path_traversal_detected"]
        )
        return artifact

    try:
        root_resolved = checkpoint_root_path.resolve()
        candidate_resolved = candidate_path.resolve()
        if (
            candidate_resolved != root_resolved
            and root_resolved not in candidate_resolved.parents
        ):
            artifact["blocked_reasons"] = _append_unique_reasons(
                artifact["blocked_reasons"], ["resume_checkpoint_outside_root"]
            )
            return artifact
    except OSError:
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["resume_checkpoint_path_resolution_failed"]
        )
        return artifact

    if not resume_preflight_enabled:
        return artifact

    artifact["checkpoint_read_attempted"] = True
    try:
        raw = candidate_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["resume_checkpoint_missing"]
        )
        return artifact
    except OSError as exc:
        artifact["read_error_type"] = exc.__class__.__name__
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["resume_checkpoint_read_failed"]
        )
        return artifact

    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError:
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["resume_checkpoint_malformed_json"]
        )
        return artifact

    artifact["checkpoint_read_ok"] = True
    if (
        not isinstance(envelope, dict)
        or envelope.get("schema_version") != "relayrun.checkpoint_envelope.v0"
    ):
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["resume_checkpoint_schema_invalid"]
        )
        return artifact

    artifact["checkpoint_schema_valid"] = True
    content_free = (
        envelope.get("content_free") is True and _is_checkpoint_content_free(envelope)
    )
    artifact["content_free"] = content_free
    if not content_free:
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["resume_checkpoint_content_policy_failed"]
        )

    return artifact


def _checkpoint_content_policy() -> dict[str, bool]:
    return {
        "content_free_only": True,
        "raw_user_message_included": False,
        "backend_payload_included": False,
        "response_text_included": False,
        "snippet_text_included": False,
    }


def _path_has_symlink_parent(path: Path) -> bool:
    """Return whether an existing configured path ancestor is a symlink."""

    for parent in path.parents:
        if parent == Path("."):
            continue
        if parent.is_symlink():
            return True
    return False


def build_relayrun_checkpoint_index_diagnostics(
    *,
    checkpoint_root: str = ".relayrun/checkpoints",
    index_enabled: bool = False,
    dry_run_only: bool = True,
    max_files: int = 100,
) -> dict[str, Any]:
    """Build safe checkpoint index/listing diagnostics.

    The index is diagnostics-only. It scans only explicitly enabled,
    non-dry-run checkpoint roots, indexes only content-free checkpoint envelope
    metadata, and never applies resume/retry/recovery behavior.
    """

    safe_max_files = max(1, int(max_files))
    root_path = str(checkpoint_root or ".relayrun/checkpoints")
    root = Path(root_path)
    blocked_reasons: list[str] = []
    if not index_enabled:
        blocked_reasons.append("checkpoint_index_disabled")
    if dry_run_only:
        blocked_reasons.append("checkpoint_index_dry_run_only")
    absolute_path_detected = root.is_absolute()
    path_traversal_detected = ".." in root.parts
    symlink_root_detected = root.is_symlink()
    symlink_parent_detected = _path_has_symlink_parent(root)
    if absolute_path_detected:
        blocked_reasons.append("checkpoint_index_absolute_root")
    if symlink_root_detected:
        blocked_reasons.append("checkpoint_index_symlink_root")
    if symlink_parent_detected:
        blocked_reasons.append("checkpoint_index_symlink_parent")
    if path_traversal_detected:
        blocked_reasons.append("checkpoint_index_path_traversal_detected")

    artifact: dict[str, Any] = {
        "schema_version": "relayrun.checkpoint_index.v0",
        "diagnostics_only": True,
        "index_enabled": bool(index_enabled),
        "dry_run_only": bool(dry_run_only),
        "scan_attempted": False,
        "root_path": root_path,
        "root_exists": root.exists(),
        "scanned_files": 0,
        "indexed_checkpoints": [],
        "blocked_files": [],
        "truncated": False,
        "blocked_reasons": blocked_reasons,
        "path_safety": {
            "root_relative": not absolute_path_detected,
            "absolute_path_detected": absolute_path_detected,
            "symlink_root_detected": symlink_root_detected,
            "symlink_parent_detected": symlink_parent_detected,
            "path_traversal_detected": path_traversal_detected,
        },
        "content_policy": _checkpoint_content_policy(),
    }

    if blocked_reasons:
        return artifact

    try:
        root_resolved = root.resolve()
    except OSError:
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["checkpoint_index_root_resolution_failed"]
        )
        return artifact

    if not root.exists():
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["checkpoint_index_root_missing"]
        )
        return artifact
    if not root.is_dir():
        artifact["blocked_reasons"] = _append_unique_reasons(
            artifact["blocked_reasons"], ["checkpoint_index_root_not_directory"]
        )
        return artifact

    artifact["scan_attempted"] = True
    for candidate in root.rglob("*.json"):
        if artifact["scanned_files"] >= safe_max_files:
            artifact["truncated"] = True
            artifact["blocked_reasons"] = _append_unique_reasons(
                artifact["blocked_reasons"], ["checkpoint_index_truncated"]
            )
            break
        if not candidate.is_file() and not candidate.is_symlink():
            continue
        artifact["scanned_files"] += 1
        blocked_file = _build_checkpoint_index_file_summary(
            candidate=candidate,
            root=root,
            root_resolved=root_resolved,
        )
        if "blocked_reasons" in blocked_file:
            artifact["blocked_files"].append(blocked_file)
        else:
            artifact["indexed_checkpoints"].append(blocked_file)

    return artifact


def _checkpoint_index_relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _build_checkpoint_index_file_summary(
    *,
    candidate: Path,
    root: Path,
    root_resolved: Path,
) -> dict[str, Any]:
    checkpoint_path = _checkpoint_index_relative_path(candidate, root)
    blocked_reasons: list[str] = []
    if candidate.suffix != ".json":
        blocked_reasons.append("checkpoint_index_non_json_file")
    if candidate.is_symlink():
        blocked_reasons.append("checkpoint_index_symlink_blocked")
    if ".." in candidate.parts:
        blocked_reasons.append("checkpoint_index_path_traversal_detected")

    try:
        candidate_resolved = candidate.resolve()
        if (
            candidate_resolved != root_resolved
            and root_resolved not in candidate_resolved.parents
        ):
            blocked_reasons.append("checkpoint_index_file_outside_root")
    except OSError:
        blocked_reasons.append("checkpoint_index_file_resolution_failed")

    if blocked_reasons:
        return {
            "checkpoint_path": checkpoint_path,
            "blocked_reasons": _append_unique_reasons([], blocked_reasons),
        }

    try:
        raw = candidate.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "checkpoint_path": checkpoint_path,
            "blocked_reasons": ["checkpoint_index_file_read_failed"],
            "read_error_type": exc.__class__.__name__,
        }

    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "checkpoint_path": checkpoint_path,
            "blocked_reasons": ["checkpoint_index_malformed_json"],
        }

    if (
        not isinstance(envelope, dict)
        or envelope.get("schema_version") != "relayrun.checkpoint_envelope.v0"
    ):
        return {
            "checkpoint_path": checkpoint_path,
            "blocked_reasons": ["checkpoint_index_schema_invalid"],
        }

    content_free = (
        envelope.get("content_free") is True and _is_checkpoint_content_free(envelope)
    )
    if not content_free:
        return {
            "checkpoint_path": checkpoint_path,
            "blocked_reasons": ["checkpoint_index_content_policy_failed"],
        }

    node_statuses = envelope.get("node_statuses")
    if not isinstance(node_statuses, list):
        node_statuses = []
    blocked = envelope.get("blocked_reasons")
    if not isinstance(blocked, list):
        blocked = []
    summary = {
        "checkpoint_path": checkpoint_path,
        "run_id": envelope.get("run_id")
        if isinstance(envelope.get("run_id"), str)
        else None,
        "turn_id": envelope.get("turn_id")
        if isinstance(envelope.get("turn_id"), str)
        else None,
        "route_model": envelope.get("route_model")
        if isinstance(envelope.get("route_model"), str)
        else None,
        "backend_name": envelope.get("backend_name")
        if isinstance(envelope.get("backend_name"), str)
        else None,
        "run_status": envelope.get("run_status")
        if isinstance(envelope.get("run_status"), str)
        else None,
        "checkpoint_persisted": envelope.get("checkpoint_persisted") is True,
        "node_count": len(node_statuses),
        "blocked_reason_count": len(blocked),
        "content_free": True,
    }
    if isinstance(envelope.get("created_at"), str):
        summary["created_at"] = envelope.get("created_at")
    return summary


def build_relayrun_recovery_transition_artifact(
    *,
    node_statuses: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    recovery_transition_enabled: bool = False,
    recovery_transition_dry_run_only: bool = True,
    resume_mode: ResumeMode = "none",
) -> dict[str, Any]:
    """Build diagnostics-only recovery transition metadata.

    This artifact proposes a future orchestration transition only. It must not
    create user-visible output, mutate payloads, apply resume/retry, or apply
    recovery transitions.
    """

    safe_nodes = [node for node in (node_statuses or ()) if isinstance(node, dict)]
    source_node = None
    for node in safe_nodes:
        if node.get("node_status") in {"failed", "blocked"}:
            source_node = str(node.get("node_name") or "unknown")
            break

    proposed_transition_type = "none"
    next_node = None
    required_user_action = None
    if source_node == "backend_forward":
        proposed_transition_type = "retry_safe_node"
        next_node = "backend_forward"
    elif source_node == "relayref":
        proposed_transition_type = "ask_user_confirmation"
        next_node = "waiting_user"
        required_user_action = "clarify_reference"
    elif source_node in {"relayscn", "relaymem_retrieval", "relaymem_runtime_ctx"}:
        proposed_transition_type = "context_repair"
        next_node = "waiting_user"
        required_user_action = "confirm_context_repair"
    elif source_node is not None:
        proposed_transition_type = "explain_blocked_state"
        next_node = "waiting_user"
        required_user_action = "review_blocked_state"

    blocked_reasons = ["recovery_transition_not_implemented"]
    if not recovery_transition_enabled:
        blocked_reasons.append("recovery_transition_disabled")
    if recovery_transition_dry_run_only:
        blocked_reasons.append("recovery_transition_dry_run_only")

    return {
        "schema_version": "relayrun.recovery_transition.v0",
        "diagnostics_only": True,
        "user_visible": False,
        "apply_allowed": False,
        "applied": False,
        "transition_created": False,
        "proposed_transition_type": proposed_transition_type,
        "source_node": source_node,
        "next_node": next_node,
        "resume_mode": resume_mode,
        "required_user_action": required_user_action,
        "blocked_reasons": blocked_reasons,
        "safety": {
            "passes_through_output_pipeline": True,
            "direct_user_output_allowed": False,
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
        },
    }


def build_relayrun_waiting_user_contract(
    *,
    waiting_user_contract_enabled: bool = False,
    waiting_user_contract_dry_run_only: bool = True,
    resume_preflight: dict[str, Any] | None = None,
    recovery_transition_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build diagnostics-only waiting-user contract metadata.

    The contract structures possible user-confirmation needs for future
    orchestration only. It never emits direct user-visible output, applies
    resume/retry/recovery, or mutates backend payloads.
    """

    safe_resume_preflight = (
        _copy_jsonable_mapping(resume_preflight)
        if isinstance(resume_preflight, dict)
        else None
    )
    safe_recovery_transition = (
        _copy_jsonable_mapping(recovery_transition_artifact)
        if isinstance(recovery_transition_artifact, dict)
        else None
    )
    transition_type = (
        safe_recovery_transition.get("proposed_transition_type")
        if isinstance(safe_recovery_transition, dict)
        else None
    )
    source_node = (
        safe_recovery_transition.get("source_node")
        if isinstance(safe_recovery_transition, dict)
        else None
    )

    waiting_user_required = False
    waiting_user_reason = None
    allowed_user_actions: list[str] = []
    if transition_type == "context_repair":
        waiting_user_required = True
        waiting_user_reason = "recovery_context_repair"
        allowed_user_actions = ["confirm_context", "provide_clarification"]
    elif transition_type == "ask_user_confirmation":
        waiting_user_required = True
        waiting_user_reason = "unresolved_reference"
        allowed_user_actions = ["provide_clarification"]
    elif transition_type == "retry_safe_node" and source_node == "backend_forward":
        waiting_user_required = True
        waiting_user_reason = "backend_error_recovery_confirmation"
        allowed_user_actions = ["confirm_retry", "cancel_recovery"]

    blocked_reasons: list[str] = []
    if not waiting_user_contract_enabled:
        blocked_reasons.append("waiting_user_contract_disabled")
    if waiting_user_contract_dry_run_only:
        blocked_reasons.append("waiting_user_contract_dry_run_only")
    if waiting_user_required:
        blocked_reasons.append("waiting_user_apply_not_implemented")

    return {
        "schema_version": "relayrun.waiting_user_contract.v0",
        "diagnostics_only": True,
        "user_visible": False,
        "apply_allowed": False,
        "applied": False,
        "waiting_user_required": waiting_user_required,
        "waiting_user_reason": waiting_user_reason,
        "source_node": source_node,
        "source_artifacts": {
            "resume_preflight": safe_resume_preflight,
            "recovery_transition_artifact": safe_recovery_transition,
        },
        "allowed_user_actions": allowed_user_actions,
        "blocked_reasons": blocked_reasons,
        "safety": {
            "direct_user_output_allowed": False,
            "passes_through_output_pipeline_required": True,
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
        },
    }


def build_relayrun_recovery_apply_preflight(
    *,
    recovery_apply_preflight_enabled: bool = False,
    recovery_apply_dry_run_only: bool = True,
    recovery_transition_artifact: dict[str, Any] | None = None,
    waiting_user_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build diagnostics-only recovery transition apply preflight metadata.

    This preflight fixes the future apply gates for recovery transitions. It is
    intentionally non-applying: no resume, retry, recovery transition, backend
    payload mutation, or direct user-visible output is attempted here.
    """

    safe_recovery_transition = (
        _copy_jsonable_mapping(recovery_transition_artifact)
        if isinstance(recovery_transition_artifact, dict)
        else None
    )
    safe_waiting_user_contract = (
        _copy_jsonable_mapping(waiting_user_contract)
        if isinstance(waiting_user_contract, dict)
        else None
    )
    source_transition_type = "none"
    if isinstance(safe_recovery_transition, dict):
        transition_value = safe_recovery_transition.get("proposed_transition_type")
        if isinstance(transition_value, str) and transition_value:
            source_transition_type = transition_value

    waiting_user_required = False
    waiting_user_reason = None
    if isinstance(safe_waiting_user_contract, dict):
        waiting_user_required = safe_waiting_user_contract.get("waiting_user_required") is True
        reason_value = safe_waiting_user_contract.get("waiting_user_reason")
        if isinstance(reason_value, str):
            waiting_user_reason = reason_value

    required_gates = [
        "explicit_config_enabled",
        "dry_run_only_false",
        "recovery_transition_artifact_present",
        "waiting_user_contract_present",
        "scene_policy_allows_recovery_output",
        "output_pipeline_required",
        "user_confirmation_if_required",
    ]

    blocked_reasons: list[str] = ["recovery_apply_not_implemented"]
    if not recovery_apply_preflight_enabled:
        blocked_reasons.append("recovery_apply_disabled")
    if recovery_apply_dry_run_only:
        blocked_reasons.append("recovery_apply_dry_run_only")
    if safe_recovery_transition is None:
        blocked_reasons.append("recovery_transition_artifact_missing")
    if safe_waiting_user_contract is None:
        blocked_reasons.append("waiting_user_contract_missing")
    if waiting_user_required:
        blocked_reasons.append("waiting_user_confirmation_required")

    return {
        "schema_version": "relayrun.recovery_apply_preflight.v0",
        "diagnostics_only": True,
        "user_visible": False,
        "apply_allowed": False,
        "apply_attempted": False,
        "applied": False,
        "source_transition_type": source_transition_type,
        "waiting_user_required": waiting_user_required,
        "waiting_user_reason": waiting_user_reason,
        "source_artifacts": {
            "recovery_transition_artifact": safe_recovery_transition,
            "waiting_user_contract": safe_waiting_user_contract,
        },
        "required_gates": required_gates,
        "blocked_reasons": blocked_reasons,
        "safety": {
            "direct_user_output_allowed": False,
            "passes_through_output_pipeline_required": True,
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
            "contains_prompt_text": False,
        },
    }


def build_relayrun_recovery_response_draft(
    *,
    recovery_response_draft_enabled: bool = False,
    recovery_response_draft_dry_run_only: bool = True,
    recovery_apply_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a diagnostics-only recovery response draft artifact.

    RelayRUN does not finalize character-facing text. The draft only provides
    content-free instructions for a future output pipeline and never mutates
    backend payloads or response bodies.
    """

    safe_apply_preflight = (
        _copy_jsonable_mapping(recovery_apply_preflight)
        if isinstance(recovery_apply_preflight, dict)
        else None
    )
    source_transition_type = "none"
    waiting_user_required = False
    if isinstance(safe_apply_preflight, dict):
        transition_value = safe_apply_preflight.get("source_transition_type")
        if isinstance(transition_value, str) and transition_value:
            source_transition_type = transition_value
        waiting_user_required = safe_apply_preflight.get("waiting_user_required") is True

    suggested_message_kind = "none"
    draft_prompt_for_output_pipeline = None
    if source_transition_type == "context_repair":
        suggested_message_kind = "context_repair_prompt"
        draft_prompt_for_output_pipeline = (
            "Ask the user to confirm or restate the current context before continuing."
        )
    elif source_transition_type == "ask_user_confirmation":
        suggested_message_kind = "ask_clarification"
        draft_prompt_for_output_pipeline = (
            "Ask the user to clarify the unresolved reference before using memory or continuing."
        )
    elif source_transition_type == "retry_safe_node":
        suggested_message_kind = "explain_backend_error"
        draft_prompt_for_output_pipeline = (
            "Explain that the backend request failed and ask whether to retry."
        )
    elif source_transition_type == "explain_blocked_state":
        suggested_message_kind = "confirm_recovery"
        draft_prompt_for_output_pipeline = (
            "Ask the user to confirm how to proceed from the blocked recovery state."
        )

    blocked_reasons: list[str] = ["recovery_response_draft_not_implemented"]
    if not recovery_response_draft_enabled:
        blocked_reasons.append("recovery_response_draft_disabled")
    if recovery_response_draft_dry_run_only:
        blocked_reasons.append("recovery_response_draft_dry_run_only")
    if safe_apply_preflight is None:
        blocked_reasons.append("recovery_apply_preflight_missing")

    return {
        "schema_version": "relayrun.recovery_response_draft.v0",
        "diagnostics_only": True,
        "draft_only": True,
        "user_visible": False,
        "apply_allowed": False,
        "applied": False,
        "source_transition_type": source_transition_type,
        "waiting_user_required": waiting_user_required,
        "suggested_message_kind": suggested_message_kind,
        "draft_prompt_for_output_pipeline": draft_prompt_for_output_pipeline,
        "source_artifacts": {
            "recovery_apply_preflight": safe_apply_preflight,
        },
        "blocked_reasons": blocked_reasons,
        "safety": {
            "direct_user_output_allowed": False,
            "final_text_generated": False,
            "passes_through_output_pipeline_required": True,
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
            "contains_prompt_text": False,
        },
    }


def build_relayrun_visible_recovery_response_preflight(
    *,
    visible_recovery_preflight_enabled: bool = False,
    visible_recovery_dry_run_only: bool = True,
    recovery_response_draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build diagnostics-only visible recovery response preflight metadata.

    This preflight fixes the future full-output-pipeline requirements for any
    user-visible recovery response. RelayRUN still does not finalize text, apply
    recovery, mutate backend payloads, or mutate response bodies.
    """

    safe_recovery_response_draft = (
        _copy_jsonable_mapping(recovery_response_draft)
        if isinstance(recovery_response_draft, dict)
        else None
    )
    source_message_kind = "none"
    if isinstance(safe_recovery_response_draft, dict):
        message_kind = safe_recovery_response_draft.get("suggested_message_kind")
        if isinstance(message_kind, str) and message_kind:
            source_message_kind = message_kind

    required_pipeline_nodes = [
        "input_side_relayscn",
        "input_side_relayemo",
        "relayctx_repack",
        "main_llm_or_recovery_generator",
        "relayctx_unpack",
        "return_side_relayemo",
        "output_side_relayscn",
    ]
    blocked_reasons: list[str] = [
        "visible_recovery_not_implemented",
        "output_pipeline_not_executed",
    ]
    if not visible_recovery_preflight_enabled:
        blocked_reasons.append("visible_recovery_disabled")
    if visible_recovery_dry_run_only:
        blocked_reasons.append("visible_recovery_dry_run_only")
    if safe_recovery_response_draft is None:
        blocked_reasons.append("recovery_response_draft_missing")

    return {
        "schema_version": "relayrun.visible_recovery_response_preflight.v0",
        "diagnostics_only": True,
        "user_visible_allowed": False,
        "apply_allowed": False,
        "apply_attempted": False,
        "applied": False,
        "final_text_generated": False,
        "source_recovery_response_draft_present": safe_recovery_response_draft is not None,
        "source_message_kind": source_message_kind,
        "required_pipeline_nodes": required_pipeline_nodes,
        "pipeline_preflight": {
            "relayscn_required": True,
            "relayemo_required": True,
            "relayctx_repack_required": True,
            "relayctx_unpack_required": True,
            "output_side_relayscn_required": True,
            "main_llm_or_recovery_generator_required": True,
        },
        "source_artifacts": {
            "recovery_response_draft": safe_recovery_response_draft,
        },
        "blocked_reasons": blocked_reasons,
        "safety": {
            "direct_user_output_allowed": False,
            "run_direct_text_finalization_allowed": False,
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
            "contains_prompt_text": False,
            "contains_final_text": False,
        },
    }


def _project_recovery_response_draft_for_generator(
    recovery_response_draft: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(recovery_response_draft, dict):
        return {"present": False}

    return {
        "present": True,
        "schema_version": recovery_response_draft.get("schema_version"),
        "diagnostics_only": recovery_response_draft.get("diagnostics_only"),
        "draft_only": recovery_response_draft.get("draft_only"),
        "source_transition_type": recovery_response_draft.get("source_transition_type"),
        "waiting_user_required": recovery_response_draft.get("waiting_user_required"),
        "suggested_message_kind": recovery_response_draft.get("suggested_message_kind"),
        "apply_allowed": recovery_response_draft.get("apply_allowed"),
        "applied": recovery_response_draft.get("applied"),
    }


def _project_visible_recovery_preflight_for_generator(
    visible_recovery_response_preflight: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(visible_recovery_response_preflight, dict):
        return {"present": False}

    blocked_reasons = visible_recovery_response_preflight.get("blocked_reasons")
    required_pipeline_nodes = visible_recovery_response_preflight.get("required_pipeline_nodes")
    pipeline_preflight = visible_recovery_response_preflight.get("pipeline_preflight")

    return {
        "present": True,
        "schema_version": visible_recovery_response_preflight.get("schema_version"),
        "diagnostics_only": visible_recovery_response_preflight.get("diagnostics_only"),
        "user_visible_allowed": visible_recovery_response_preflight.get("user_visible_allowed"),
        "apply_allowed": visible_recovery_response_preflight.get("apply_allowed"),
        "apply_attempted": visible_recovery_response_preflight.get("apply_attempted"),
        "applied": visible_recovery_response_preflight.get("applied"),
        "final_text_generated": visible_recovery_response_preflight.get("final_text_generated"),
        "source_message_kind": visible_recovery_response_preflight.get("source_message_kind"),
        "source_recovery_response_draft_present": visible_recovery_response_preflight.get(
            "source_recovery_response_draft_present"
        ),
        "blocked_reasons": [str(reason) for reason in blocked_reasons]
        if isinstance(blocked_reasons, list)
        else [],
        "pipeline_preflight": dict(pipeline_preflight)
        if isinstance(pipeline_preflight, dict)
        else {},
        "required_pipeline_nodes": [str(node) for node in required_pipeline_nodes]
        if isinstance(required_pipeline_nodes, list)
        else [],
    }


def build_relayrun_recovery_response_generator_artifact(
    *,
    recovery_response_generator_enabled: bool = False,
    recovery_response_generator_dry_run_only: bool = True,
    recovery_response_draft: dict[str, Any] | None = None,
    visible_recovery_response_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build diagnostics-only recovery response generator contract metadata.

    This artifact models whether a future generator may turn content-free
    recovery intent into user-facing recovery text. It does not invoke a
    generator, create final text, mutate backend payloads, or mutate response
    bodies. Source artifacts are projected to metadata-only fields so draft
    prompts and nested artifacts are not embedded.
    """

    recovery_response_draft_projection = _project_recovery_response_draft_for_generator(
        recovery_response_draft
    )
    visible_preflight_projection = _project_visible_recovery_preflight_for_generator(
        visible_recovery_response_preflight
    )

    source_message_kind = "none"
    draft_kind = recovery_response_draft_projection.get("suggested_message_kind")
    if isinstance(draft_kind, str) and draft_kind:
        source_message_kind = draft_kind

    allowed_message_intent_map = {
        "none": "none",
        "ask_clarification": "clarify_unresolved_reference",
        "context_repair_prompt": "confirm_or_restate_context",
        "explain_backend_error": "explain_backend_error_and_ask_retry",
        "confirm_recovery": "ask_how_to_proceed_from_blocked_state",
    }
    allowed_message_intent = allowed_message_intent_map.get(source_message_kind, "none")

    waiting_user_required = recovery_response_draft_projection.get("waiting_user_required") is True

    blocked_reasons: list[str] = ["recovery_response_generator_not_implemented"]
    if not recovery_response_generator_enabled:
        blocked_reasons.append("recovery_response_generator_disabled")
    if recovery_response_generator_dry_run_only:
        blocked_reasons.append("recovery_response_generator_dry_run_only")
    if recovery_response_draft_projection.get("present") is not True:
        blocked_reasons.append("recovery_response_draft_missing")
    if visible_preflight_projection.get("present") is not True:
        blocked_reasons.append("visible_recovery_preflight_missing")
    if visible_preflight_projection.get("present") is True:
        if visible_preflight_projection.get("user_visible_allowed") is False:
            blocked_reasons.append("visible_recovery_not_allowed")
        visible_blocked_reasons = visible_preflight_projection.get("blocked_reasons")
        if (
            isinstance(visible_blocked_reasons, list)
            and "output_pipeline_not_executed" in visible_blocked_reasons
        ):
            blocked_reasons.append("output_pipeline_not_executed")
    if waiting_user_required:
        blocked_reasons.append("waiting_user_confirmation_required")
    blocked_reasons.append("content_policy_not_verified")

    return {
        "schema_version": "relayrun.recovery_response_generator.v0",
        "diagnostics_only": True,
        "generator_allowed": False,
        "generator_attempted": False,
        "generated_text_present": False,
        "output_pipeline_required": True,
        "user_visible_allowed": False,
        "final_text_generated": False,
        "source_message_kind": source_message_kind,
        "allowed_message_intent": allowed_message_intent,
        "source_artifacts": {
            "recovery_response_draft": recovery_response_draft_projection,
            "visible_recovery_response_preflight": visible_preflight_projection,
        },
        "blocked_reasons": blocked_reasons,
        "safety": {
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
            "contains_prompt_text": False,
            "contains_snippet_text": False,
            "contains_final_text": False,
            "direct_user_output_allowed": False,
            "run_direct_text_finalization_allowed": False,
            "backend_payload_mutation_allowed": False,
            "response_body_mutation_allowed": False,
        },
    }


def _project_recovery_response_generator_for_output_gate(
    recovery_response_generator: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(recovery_response_generator, dict):
        return {"present": False}

    blocked_reasons = recovery_response_generator.get("blocked_reasons")
    safety = recovery_response_generator.get("safety")

    return {
        "present": True,
        "schema_version": recovery_response_generator.get("schema_version"),
        "diagnostics_only": recovery_response_generator.get("diagnostics_only"),
        "generator_allowed": recovery_response_generator.get("generator_allowed"),
        "generator_attempted": recovery_response_generator.get("generator_attempted"),
        "generated_text_present": recovery_response_generator.get("generated_text_present"),
        "output_pipeline_required": recovery_response_generator.get("output_pipeline_required"),
        "user_visible_allowed": recovery_response_generator.get("user_visible_allowed"),
        "final_text_generated": recovery_response_generator.get("final_text_generated"),
        "source_message_kind": recovery_response_generator.get("source_message_kind"),
        "allowed_message_intent": recovery_response_generator.get("allowed_message_intent"),
        "waiting_user_required": _recovery_response_generator_waiting_user_required(
            recovery_response_generator
        ),
        "blocked_reasons": [str(reason) for reason in blocked_reasons]
        if isinstance(blocked_reasons, list)
        else [],
        "safety": dict(safety) if isinstance(safety, dict) else {},
    }


def _recovery_response_generator_waiting_user_required(
    recovery_response_generator: dict[str, Any],
) -> bool:
    source_artifacts = recovery_response_generator.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        return False
    recovery_response_draft = source_artifacts.get("recovery_response_draft")
    if not isinstance(recovery_response_draft, dict):
        return False
    return recovery_response_draft.get("waiting_user_required") is True


def _project_visible_recovery_preflight_for_output_gate(
    visible_recovery_response_preflight: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(visible_recovery_response_preflight, dict):
        return {"present": False}

    blocked_reasons = visible_recovery_response_preflight.get("blocked_reasons")
    pipeline_preflight = visible_recovery_response_preflight.get("pipeline_preflight")
    required_pipeline_nodes = visible_recovery_response_preflight.get("required_pipeline_nodes")

    return {
        "present": True,
        "schema_version": visible_recovery_response_preflight.get("schema_version"),
        "diagnostics_only": visible_recovery_response_preflight.get("diagnostics_only"),
        "user_visible_allowed": visible_recovery_response_preflight.get("user_visible_allowed"),
        "apply_allowed": visible_recovery_response_preflight.get("apply_allowed"),
        "apply_attempted": visible_recovery_response_preflight.get("apply_attempted"),
        "applied": visible_recovery_response_preflight.get("applied"),
        "final_text_generated": visible_recovery_response_preflight.get("final_text_generated"),
        "source_message_kind": visible_recovery_response_preflight.get("source_message_kind"),
        "output_pipeline_required": visible_recovery_response_preflight.get("output_pipeline_required"),
        "blocked_reasons": [str(reason) for reason in blocked_reasons]
        if isinstance(blocked_reasons, list)
        else [],
        "pipeline_preflight": dict(pipeline_preflight)
        if isinstance(pipeline_preflight, dict)
        else {},
        "required_pipeline_nodes": [str(node) for node in required_pipeline_nodes]
        if isinstance(required_pipeline_nodes, list)
        else [],
    }


def build_relayrun_output_relayscn_recovery_gate_artifact(
    *,
    output_relayscn_recovery_gate_enabled: bool = False,
    output_relayscn_recovery_gate_dry_run_only: bool = True,
    recovery_response_generator: dict[str, Any] | None = None,
    visible_recovery_response_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build diagnostics-only output-side RelaySCN recovery gate metadata.

    This artifact models a future output-side scene/safety gate for visible
    recovery. It does not execute RelaySCN, produce final text, mutate backend
    payloads, mutate response bodies, apply visible output, retry, or resume.
    Source artifacts are metadata-only projections with nested source artifacts
    and raw prompt/text fields omitted.
    """

    generator_projection = _project_recovery_response_generator_for_output_gate(
        recovery_response_generator
    )
    visible_preflight_projection = _project_visible_recovery_preflight_for_output_gate(
        visible_recovery_response_preflight
    )

    source_message_kind = "none"
    generator_kind = generator_projection.get("source_message_kind")
    if isinstance(generator_kind, str) and generator_kind:
        source_message_kind = generator_kind

    allowed_message_intent = "none"
    generator_intent = generator_projection.get("allowed_message_intent")
    if isinstance(generator_intent, str) and generator_intent:
        allowed_message_intent = generator_intent

    generator_allowed = generator_projection.get("generator_allowed") is True
    generated_text_present = generator_projection.get("generated_text_present") is True
    waiting_user_required = generator_projection.get("waiting_user_required") is True

    blocked_reasons: list[str] = [
        "output_relayscn_recovery_gate_not_implemented",
        "output_pipeline_not_executed",
    ]
    if not output_relayscn_recovery_gate_enabled:
        blocked_reasons.append("output_relayscn_recovery_gate_disabled")
    if output_relayscn_recovery_gate_dry_run_only:
        blocked_reasons.append("output_relayscn_recovery_gate_dry_run_only")
    if generator_projection.get("present") is not True:
        blocked_reasons.append("recovery_response_generator_missing")
    if visible_preflight_projection.get("present") is not True:
        blocked_reasons.append("visible_recovery_preflight_missing")
    if not generator_allowed:
        blocked_reasons.append("recovery_response_generator_not_allowed")
    if not generated_text_present:
        blocked_reasons.append("generated_text_missing")
    if waiting_user_required:
        blocked_reasons.append("waiting_user_confirmation_required")
    blocked_reasons.append("content_policy_not_verified")

    return {
        "schema_version": "relayrun.output_relayscn_recovery_gate.v0",
        "diagnostics_only": True,
        "gate_allowed": False,
        "gate_attempted": False,
        "gate_passed": False,
        "user_visible_allowed": False,
        "final_text_generated": False,
        "output_pipeline_required": True,
        "source_message_kind": source_message_kind,
        "allowed_message_intent": allowed_message_intent,
        "scene_gate_required": True,
        "output_side_relayscn_required": True,
        "source_artifacts": {
            "recovery_response_generator": generator_projection,
            "visible_recovery_response_preflight": visible_preflight_projection,
        },
        "blocked_reasons": blocked_reasons,
        "safety": {
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
            "contains_prompt_text": False,
            "contains_snippet_text": False,
            "contains_final_text": False,
            "direct_user_output_allowed": False,
            "run_direct_text_finalization_allowed": False,
            "backend_payload_mutation_allowed": False,
            "response_body_mutation_allowed": False,
        },
    }


def _project_output_relayscn_recovery_gate_for_visible_apply(
    output_relayscn_recovery_gate: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(output_relayscn_recovery_gate, dict):
        return {"present": False}

    blocked_reasons = output_relayscn_recovery_gate.get("blocked_reasons")
    safety = output_relayscn_recovery_gate.get("safety")

    return {
        "present": True,
        "schema_version": output_relayscn_recovery_gate.get("schema_version"),
        "diagnostics_only": output_relayscn_recovery_gate.get("diagnostics_only"),
        "gate_allowed": output_relayscn_recovery_gate.get("gate_allowed"),
        "gate_attempted": output_relayscn_recovery_gate.get("gate_attempted"),
        "gate_passed": output_relayscn_recovery_gate.get("gate_passed"),
        "user_visible_allowed": output_relayscn_recovery_gate.get("user_visible_allowed"),
        "final_text_generated": output_relayscn_recovery_gate.get("final_text_generated"),
        "output_pipeline_required": output_relayscn_recovery_gate.get("output_pipeline_required"),
        "source_message_kind": output_relayscn_recovery_gate.get("source_message_kind"),
        "allowed_message_intent": output_relayscn_recovery_gate.get("allowed_message_intent"),
        "scene_gate_required": output_relayscn_recovery_gate.get("scene_gate_required"),
        "output_side_relayscn_required": output_relayscn_recovery_gate.get(
            "output_side_relayscn_required"
        ),
        "blocked_reasons": [str(reason) for reason in blocked_reasons]
        if isinstance(blocked_reasons, list)
        else [],
        "safety": dict(safety) if isinstance(safety, dict) else {},
    }


def build_relayrun_visible_recovery_apply_preflight_artifact(
    *,
    visible_recovery_apply_preflight_enabled: bool = False,
    visible_recovery_apply_preflight_dry_run_only: bool = True,
    output_relayscn_recovery_gate: dict[str, Any] | None = None,
    recovery_response_generator: dict[str, Any] | None = None,
    visible_recovery_response_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build diagnostics-only visible recovery response apply preflight metadata.

    This artifact records whether a future visible recovery response apply could
    mutate the response body. It does not apply visible output, mutate response
    bodies, mutate backend payloads, generate final text, execute a generator,
    retry, or resume. Source artifacts are projected to metadata only.
    """

    gate_projection = _project_output_relayscn_recovery_gate_for_visible_apply(
        output_relayscn_recovery_gate
    )
    generator_projection = _project_recovery_response_generator_for_output_gate(
        recovery_response_generator
    )
    visible_preflight_projection = _project_visible_recovery_preflight_for_output_gate(
        visible_recovery_response_preflight
    )

    source_message_kind = "none"
    gate_kind = gate_projection.get("source_message_kind")
    generator_kind = generator_projection.get("source_message_kind")
    if isinstance(gate_kind, str) and gate_kind:
        source_message_kind = gate_kind
    elif isinstance(generator_kind, str) and generator_kind:
        source_message_kind = generator_kind

    allowed_message_intent = "none"
    gate_intent = gate_projection.get("allowed_message_intent")
    generator_intent = generator_projection.get("allowed_message_intent")
    if isinstance(gate_intent, str) and gate_intent:
        allowed_message_intent = gate_intent
    elif isinstance(generator_intent, str) and generator_intent:
        allowed_message_intent = generator_intent

    gate_passed = gate_projection.get("gate_passed") is True
    gate_user_visible_allowed = gate_projection.get("user_visible_allowed") is True
    generated_text_present = generator_projection.get("generated_text_present") is True
    generator_allowed = generator_projection.get("generator_allowed") is True
    visible_user_visible_allowed = visible_preflight_projection.get("user_visible_allowed") is True
    waiting_user_required = generator_projection.get("waiting_user_required") is True

    blocked_reasons: list[str] = [
        "visible_recovery_apply_not_implemented",
        "response_body_mutation_not_implemented",
        "output_pipeline_not_executed",
    ]
    if not visible_recovery_apply_preflight_enabled:
        blocked_reasons.append("visible_recovery_apply_preflight_disabled")
    if visible_recovery_apply_preflight_dry_run_only:
        blocked_reasons.append("visible_recovery_apply_preflight_dry_run_only")
    if gate_projection.get("present") is not True:
        blocked_reasons.append("output_relayscn_recovery_gate_missing")
    if generator_projection.get("present") is not True:
        blocked_reasons.append("recovery_response_generator_missing")
    if visible_preflight_projection.get("present") is not True:
        blocked_reasons.append("visible_recovery_preflight_missing")
    if not gate_passed:
        blocked_reasons.append("output_relayscn_recovery_gate_not_passed")
    if not gate_user_visible_allowed:
        blocked_reasons.append("output_relayscn_user_visible_not_allowed")
    if not generated_text_present:
        blocked_reasons.append("generated_text_missing")
    if not generator_allowed:
        blocked_reasons.append("recovery_response_generator_not_allowed")
    if not visible_user_visible_allowed:
        blocked_reasons.append("visible_recovery_not_allowed")
    if waiting_user_required:
        blocked_reasons.append("waiting_user_confirmation_required")
    blocked_reasons.append("content_policy_not_verified")

    return {
        "schema_version": "relayrun.visible_recovery_apply_preflight.v0",
        "diagnostics_only": True,
        "apply_allowed": False,
        "apply_attempted": False,
        "applied": False,
        "response_body_mutation_allowed": False,
        "backend_payload_mutation_allowed": False,
        "user_visible_allowed": False,
        "final_text_generated": False,
        "output_pipeline_required": True,
        "output_side_relayscn_gate_required": True,
        "source_message_kind": source_message_kind,
        "allowed_message_intent": allowed_message_intent,
        "source_artifacts": {
            "output_relayscn_recovery_gate": gate_projection,
            "recovery_response_generator": generator_projection,
            "visible_recovery_response_preflight": visible_preflight_projection,
        },
        "blocked_reasons": blocked_reasons,
        "safety": {
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
            "contains_prompt_text": False,
            "contains_snippet_text": False,
            "contains_final_text": False,
            "direct_user_output_allowed": False,
            "run_direct_text_finalization_allowed": False,
            "backend_payload_mutation_allowed": False,
            "response_body_mutation_allowed": False,
        },
    }


def _project_waiting_user_contract_for_user_action(
    waiting_user_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(waiting_user_contract, dict):
        return {"present": False}

    blocked_reasons = waiting_user_contract.get("blocked_reasons")
    allowed_user_actions = waiting_user_contract.get("allowed_user_actions")
    safety = waiting_user_contract.get("safety")

    return {
        "present": True,
        "schema_version": waiting_user_contract.get("schema_version"),
        "diagnostics_only": waiting_user_contract.get("diagnostics_only"),
        "user_visible": waiting_user_contract.get("user_visible"),
        "apply_allowed": waiting_user_contract.get("apply_allowed"),
        "applied": waiting_user_contract.get("applied"),
        "waiting_user_required": waiting_user_contract.get("waiting_user_required"),
        "waiting_user_reason": waiting_user_contract.get("waiting_user_reason"),
        "source_node": waiting_user_contract.get("source_node"),
        "allowed_user_actions": [str(action) for action in allowed_user_actions]
        if isinstance(allowed_user_actions, list)
        else [],
        "blocked_reasons": [str(reason) for reason in blocked_reasons]
        if isinstance(blocked_reasons, list)
        else [],
        "safety": dict(safety) if isinstance(safety, dict) else {},
    }


def _project_visible_recovery_apply_preflight_for_user_action(
    visible_recovery_apply_preflight: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(visible_recovery_apply_preflight, dict):
        return {"present": False}

    blocked_reasons = visible_recovery_apply_preflight.get("blocked_reasons")
    safety = visible_recovery_apply_preflight.get("safety")

    return {
        "present": True,
        "schema_version": visible_recovery_apply_preflight.get("schema_version"),
        "diagnostics_only": visible_recovery_apply_preflight.get("diagnostics_only"),
        "apply_allowed": visible_recovery_apply_preflight.get("apply_allowed"),
        "apply_attempted": visible_recovery_apply_preflight.get("apply_attempted"),
        "applied": visible_recovery_apply_preflight.get("applied"),
        "response_body_mutation_allowed": visible_recovery_apply_preflight.get(
            "response_body_mutation_allowed"
        ),
        "backend_payload_mutation_allowed": visible_recovery_apply_preflight.get(
            "backend_payload_mutation_allowed"
        ),
        "user_visible_allowed": visible_recovery_apply_preflight.get("user_visible_allowed"),
        "final_text_generated": visible_recovery_apply_preflight.get("final_text_generated"),
        "output_pipeline_required": visible_recovery_apply_preflight.get("output_pipeline_required"),
        "output_side_relayscn_gate_required": visible_recovery_apply_preflight.get(
            "output_side_relayscn_gate_required"
        ),
        "source_message_kind": visible_recovery_apply_preflight.get("source_message_kind"),
        "allowed_message_intent": visible_recovery_apply_preflight.get("allowed_message_intent"),
        "blocked_reasons": [str(reason) for reason in blocked_reasons]
        if isinstance(blocked_reasons, list)
        else [],
        "safety": dict(safety) if isinstance(safety, dict) else {},
    }


def _user_action_required_kind(
    *,
    waiting_user_reason: str,
    source_message_kind: str,
) -> str:
    waiting_reason_map = {
        "unresolved_reference": "clarify_reference",
        "recovery_scene": "confirm_context_repair",
        "recovery_context_repair": "confirm_context_repair",
        "backend_error": "confirm_retry",
        "backend_error_recovery_confirmation": "confirm_retry",
    }
    if waiting_user_reason in waiting_reason_map:
        return waiting_reason_map[waiting_user_reason]

    message_kind_map = {
        "ask_clarification": "clarify_reference",
        "context_repair_prompt": "confirm_context_repair",
        "explain_backend_error": "confirm_retry",
        "confirm_recovery": "choose_recovery_action",
    }
    return message_kind_map.get(source_message_kind, "none")


def build_relayrun_user_action_contract_artifact(
    *,
    user_action_dry_run_enabled: bool = False,
    user_action_dry_run_only: bool = True,
    waiting_user_contract: dict[str, Any] | None = None,
    visible_recovery_apply_preflight: dict[str, Any] | None = None,
    output_relayscn_recovery_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build diagnostics-only future user action contract metadata.

    This contract models future confirmation, clarification, and retry-choice
    actions. It does not parse or apply user actions, resume, retry, apply
    visible recovery, mutate response bodies, mutate backend payloads, or create
    user-visible recovery output.
    """

    waiting_projection = _project_waiting_user_contract_for_user_action(
        waiting_user_contract
    )
    visible_apply_projection = _project_visible_recovery_apply_preflight_for_user_action(
        visible_recovery_apply_preflight
    )
    gate_projection = _project_output_relayscn_recovery_gate_for_visible_apply(
        output_relayscn_recovery_gate
    )

    source_waiting_user_reason = "none"
    reason_value = waiting_projection.get("waiting_user_reason")
    if isinstance(reason_value, str) and reason_value:
        source_waiting_user_reason = reason_value

    source_message_kind = "none"
    gate_kind = gate_projection.get("source_message_kind")
    visible_apply_kind = visible_apply_projection.get("source_message_kind")
    if isinstance(gate_kind, str) and gate_kind:
        source_message_kind = gate_kind
    elif isinstance(visible_apply_kind, str) and visible_apply_kind:
        source_message_kind = visible_apply_kind

    allowed_message_intent = "none"
    gate_intent = gate_projection.get("allowed_message_intent")
    visible_apply_intent = visible_apply_projection.get("allowed_message_intent")
    if isinstance(gate_intent, str) and gate_intent:
        allowed_message_intent = gate_intent
    elif isinstance(visible_apply_intent, str) and visible_apply_intent:
        allowed_message_intent = visible_apply_intent

    required_action_kind = _user_action_required_kind(
        waiting_user_reason=source_waiting_user_reason,
        source_message_kind=source_message_kind,
    )
    waiting_user_flag_required = waiting_projection.get("waiting_user_required") is True
    visible_apply_blocked_reasons = visible_apply_projection.get("blocked_reasons")
    visible_apply_waiting_required = (
        isinstance(visible_apply_blocked_reasons, list)
        and "waiting_user_confirmation_required" in visible_apply_blocked_reasons
    )
    user_action_required = (
        waiting_user_flag_required
        or visible_apply_waiting_required
        or required_action_kind != "none"
    )
    accepted_action_kinds = [
        "clarify_reference",
        "confirm_context_repair",
        "confirm_retry",
        "choose_recovery_action",
        "cancel_recovery",
    ]

    blocked_reasons: list[str] = ["user_action_api_not_implemented"]
    if not user_action_dry_run_enabled:
        blocked_reasons.append("user_action_dry_run_disabled")
    if user_action_dry_run_only:
        blocked_reasons.append("user_action_dry_run_only")
    if waiting_projection.get("present") is not True:
        blocked_reasons.append("waiting_user_contract_missing")
    if visible_apply_projection.get("present") is not True:
        blocked_reasons.append("visible_recovery_apply_preflight_missing")
    if gate_projection.get("present") is not True:
        blocked_reasons.append("output_relayscn_recovery_gate_missing")
    if user_action_required:
        blocked_reasons.append("waiting_user_action_required")
    if visible_apply_projection.get("apply_allowed") is False:
        blocked_reasons.append("visible_recovery_apply_not_allowed")
    blocked_reasons.append("content_policy_not_verified")

    return {
        "schema_version": "relayrun.user_action_contract.v0",
        "diagnostics_only": True,
        "user_action_required": user_action_required,
        "user_action_allowed": False,
        "user_action_attempted": False,
        "user_action_applied": False,
        "resume_allowed": False,
        "retry_allowed": False,
        "visible_recovery_apply_allowed": False,
        "response_body_mutation_allowed": False,
        "backend_payload_mutation_allowed": False,
        "source_waiting_user_reason": source_waiting_user_reason,
        "source_message_kind": source_message_kind,
        "allowed_message_intent": allowed_message_intent,
        "required_action_kind": required_action_kind,
        "accepted_action_kinds": accepted_action_kinds,
        "source_artifacts": {
            "waiting_user_contract": waiting_projection,
            "visible_recovery_apply_preflight": visible_apply_projection,
            "output_relayscn_recovery_gate": gate_projection,
        },
        "blocked_reasons": blocked_reasons,
        "safety": {
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
            "contains_prompt_text": False,
            "contains_snippet_text": False,
            "contains_final_text": False,
            "direct_user_output_allowed": False,
            "run_direct_text_finalization_allowed": False,
            "backend_payload_mutation_allowed": False,
            "response_body_mutation_allowed": False,
        },
    }


def build_runtime_checkpoint_dry_run_artifact(
    *,
    request_id: str,
    route_model: str | None = None,
    backend_name: str | None = None,
    character_id: str | None = None,
    stream_enabled: bool | None = None,
    turn_id: str | None = None,
    run_id: str | None = None,
    node_statuses: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    blocked_reasons: list[str] | tuple[str, ...] | None = None,
    stream_started: bool | None = None,
    first_token_sent: bool | None = None,
    resume_allowed: bool = False,
    resume_mode: ResumeMode = "none",
    checkpoint_persisted: bool = False,
    checkpoint_target_root: str = ".relayrun/checkpoints",
    checkpoint_index_enabled: bool = False,
    checkpoint_index_dry_run_only: bool = True,
    checkpoint_index_max_files: int = 100,
    resume_preflight_enabled: bool = False,
    resume_dry_run_only: bool = True,
    recovery_transition_enabled: bool = False,
    recovery_transition_dry_run_only: bool = True,
    waiting_user_contract_enabled: bool = False,
    waiting_user_contract_dry_run_only: bool = True,
    recovery_apply_preflight_enabled: bool = False,
    recovery_apply_dry_run_only: bool = True,
    recovery_response_draft_enabled: bool = False,
    recovery_response_draft_dry_run_only: bool = True,
    visible_recovery_preflight_enabled: bool = False,
    visible_recovery_dry_run_only: bool = True,
    recovery_response_generator_enabled: bool = False,
    recovery_response_generator_dry_run_only: bool = True,
    output_relayscn_recovery_gate_enabled: bool = False,
    output_relayscn_recovery_gate_dry_run_only: bool = True,
    visible_recovery_apply_preflight_enabled: bool = False,
    visible_recovery_apply_preflight_dry_run_only: bool = True,
    user_action_dry_run_enabled: bool = False,
    user_action_dry_run_only: bool = True,
    recovery_transition_created: bool = False,
    applied: bool = False,
) -> dict[str, Any]:
    """Build the request-path RelayRUN runtime checkpoint dry-run artifact.

    This artifact is metadata-only. It must not write checkpoint files, mutate
    forwarded payloads, enable resume, or create recovery transitions yet.
    """

    safe_nodes = []
    for node in node_statuses or ():
        if isinstance(node, dict):
            safe_nodes.append(dict(node))

    safe_blocked_reasons = [str(reason) for reason in (blocked_reasons or ())]
    safe_run_id = run_id or new_run_id()
    checkpoint_persistence_plan = build_relayrun_checkpoint_persistence_plan(
        run_id=safe_run_id,
        turn_id=turn_id,
        request_id=request_id,
        target_root=checkpoint_target_root,
        checkpoint_persisted=checkpoint_persisted,
    )
    checkpoint_writer_preflight = build_relayrun_checkpoint_writer_preflight(
        target_root=checkpoint_persistence_plan["target_root"],
        target_path_preview=checkpoint_persistence_plan["target_path_preview"],
    )
    resume_preflight = build_relayrun_resume_preflight(
        resume_preflight_enabled=resume_preflight_enabled,
        resume_dry_run_only=resume_dry_run_only,
        checkpoint_path=None,
        checkpoint_root=checkpoint_target_root,
    )
    checkpoint_index = build_relayrun_checkpoint_index_diagnostics(
        checkpoint_root=checkpoint_target_root,
        index_enabled=checkpoint_index_enabled,
        dry_run_only=checkpoint_index_dry_run_only,
        max_files=checkpoint_index_max_files,
    )
    recovery_transition_artifact = build_relayrun_recovery_transition_artifact(
        node_statuses=safe_nodes,
        recovery_transition_enabled=recovery_transition_enabled,
        recovery_transition_dry_run_only=recovery_transition_dry_run_only,
        resume_mode=resume_mode,
    )
    waiting_user_contract = build_relayrun_waiting_user_contract(
        waiting_user_contract_enabled=waiting_user_contract_enabled,
        waiting_user_contract_dry_run_only=waiting_user_contract_dry_run_only,
        resume_preflight=resume_preflight,
        recovery_transition_artifact=recovery_transition_artifact,
    )
    recovery_apply_preflight = build_relayrun_recovery_apply_preflight(
        recovery_apply_preflight_enabled=recovery_apply_preflight_enabled,
        recovery_apply_dry_run_only=recovery_apply_dry_run_only,
        recovery_transition_artifact=recovery_transition_artifact,
        waiting_user_contract=waiting_user_contract,
    )
    recovery_response_draft = build_relayrun_recovery_response_draft(
        recovery_response_draft_enabled=recovery_response_draft_enabled,
        recovery_response_draft_dry_run_only=recovery_response_draft_dry_run_only,
        recovery_apply_preflight=recovery_apply_preflight,
    )
    visible_recovery_response_preflight = build_relayrun_visible_recovery_response_preflight(
        visible_recovery_preflight_enabled=visible_recovery_preflight_enabled,
        visible_recovery_dry_run_only=visible_recovery_dry_run_only,
        recovery_response_draft=recovery_response_draft,
    )
    recovery_response_generator = build_relayrun_recovery_response_generator_artifact(
        recovery_response_generator_enabled=recovery_response_generator_enabled,
        recovery_response_generator_dry_run_only=recovery_response_generator_dry_run_only,
        recovery_response_draft=recovery_response_draft,
        visible_recovery_response_preflight=visible_recovery_response_preflight,
    )
    output_relayscn_recovery_gate = build_relayrun_output_relayscn_recovery_gate_artifact(
        output_relayscn_recovery_gate_enabled=output_relayscn_recovery_gate_enabled,
        output_relayscn_recovery_gate_dry_run_only=output_relayscn_recovery_gate_dry_run_only,
        recovery_response_generator=recovery_response_generator,
        visible_recovery_response_preflight=visible_recovery_response_preflight,
    )
    visible_recovery_apply_preflight = build_relayrun_visible_recovery_apply_preflight_artifact(
        visible_recovery_apply_preflight_enabled=visible_recovery_apply_preflight_enabled,
        visible_recovery_apply_preflight_dry_run_only=visible_recovery_apply_preflight_dry_run_only,
        output_relayscn_recovery_gate=output_relayscn_recovery_gate,
        recovery_response_generator=recovery_response_generator,
        visible_recovery_response_preflight=visible_recovery_response_preflight,
    )
    user_action_contract = build_relayrun_user_action_contract_artifact(
        user_action_dry_run_enabled=user_action_dry_run_enabled,
        user_action_dry_run_only=user_action_dry_run_only,
        waiting_user_contract=waiting_user_contract,
        visible_recovery_apply_preflight=visible_recovery_apply_preflight,
        output_relayscn_recovery_gate=output_relayscn_recovery_gate,
    )

    return {
        "schema_version": "relayrun.runtime_checkpoint.v0",
        "diagnostics_only": True,
        "applied": bool(applied),
        "run_id": safe_run_id,
        "request_id": request_id,
        "turn_id": turn_id,
        "route_model": route_model,
        "backend_name": backend_name,
        "character_id": character_id,
        "stream_enabled": stream_enabled,
        "run_status": "diagnostics_only",
        "node_sequence": list(RUNTIME_CHECKPOINT_NODE_SEQUENCE),
        "node_statuses": safe_nodes,
        "stream_started": stream_started,
        "first_token_sent": first_token_sent,
        "resume_allowed": bool(resume_allowed),
        "resume_mode": resume_mode,
        "resume_preflight": resume_preflight,
        "checkpoint_persisted": bool(checkpoint_persisted),
        "checkpoint_write_attempted": False,
        "checkpoint_writer_failed": False,
        "persisted_path": None,
        "persisted_bytes": None,
        "content_free": True,
        "checkpoint_persistence_plan": checkpoint_persistence_plan,
        "checkpoint_writer_preflight": checkpoint_writer_preflight,
        "checkpoint_index": checkpoint_index,
        "recovery_transition_artifact": recovery_transition_artifact,
        "waiting_user_contract": waiting_user_contract,
        "recovery_apply_preflight": recovery_apply_preflight,
        "recovery_response_draft": recovery_response_draft,
        "visible_recovery_response_preflight": visible_recovery_response_preflight,
        "recovery_response_generator": recovery_response_generator,
        "output_relayscn_recovery_gate": output_relayscn_recovery_gate,
        "visible_recovery_apply_preflight": visible_recovery_apply_preflight,
        "user_action_contract": user_action_contract,
        "recovery_transition_created": bool(recovery_transition_created),
        "blocked_reasons": safe_blocked_reasons,
    }


def _copy_jsonable_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _append_unique_reasons(existing: Any, reasons: list[str]) -> list[str]:
    merged = [str(reason) for reason in existing or ()]
    for reason in reasons:
        if reason not in merged:
            merged.append(reason)
    return merged


def _set_checkpoint_persistence_plan_state(
    artifact: dict[str, Any],
    *,
    write_allowed: bool,
    checkpoint_persisted: bool,
    checkpoint_write_attempted: bool,
    persisted_path: str | None = None,
    blocked_reasons: list[str] | None = None,
) -> None:
    plan = artifact.get("checkpoint_persistence_plan")
    if not isinstance(plan, dict):
        return

    stale_reasons = {
        "checkpoint_persistence_not_implemented",
        "checkpoint_write_disabled",
    }
    current_reasons = [
        str(reason)
        for reason in plan.get("blocked_reasons", [])
        if str(reason) not in stale_reasons
    ]
    plan["write_allowed"] = bool(write_allowed)
    plan["checkpoint_persisted"] = bool(checkpoint_persisted)
    plan["checkpoint_write_attempted"] = bool(checkpoint_write_attempted)
    if persisted_path is not None:
        plan["persisted_path"] = persisted_path
        plan["target_path_preview"] = persisted_path
    else:
        plan.pop("persisted_path", None)
    plan["blocked_reasons"] = _append_unique_reasons(
        current_reasons, [str(reason) for reason in (blocked_reasons or [])]
    )
    plan["resume_allowed_after_persist"] = False


def _checkpoint_envelope_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    preflight = artifact.get("checkpoint_writer_preflight")
    if not isinstance(preflight, dict):
        preflight = {}
    return {
        "schema_version": "relayrun.checkpoint_envelope.v0",
        "diagnostics_only": True,
        "content_free": True,
        "run_id": artifact.get("run_id"),
        "request_id": artifact.get("request_id"),
        "turn_id": artifact.get("turn_id"),
        "route_model": artifact.get("route_model"),
        "backend_name": artifact.get("backend_name"),
        "character_id": artifact.get("character_id"),
        "stream_enabled": artifact.get("stream_enabled"),
        "run_status": artifact.get("run_status"),
        "node_sequence": artifact.get("node_sequence") or [],
        "node_statuses": artifact.get("node_statuses") or [],
        "blocked_reasons": artifact.get("blocked_reasons") or [],
        "checkpoint_persisted": False,
        "checkpoint_persistence_plan": artifact.get("checkpoint_persistence_plan"),
        "checkpoint_writer_preflight": {
            "schema_version": preflight.get("schema_version"),
            "diagnostics_only": preflight.get("diagnostics_only"),
            "write_allowed": preflight.get("write_allowed"),
            "preflight_passed": preflight.get("preflight_passed"),
            "checkpoint_write_attempted": preflight.get("checkpoint_write_attempted"),
            "directory_creation_attempted": preflight.get("directory_creation_attempted"),
            "target_root": preflight.get("target_root"),
            "target_path_preview": preflight.get("target_path_preview"),
            "path_safety": preflight.get("path_safety"),
            "content_policy": preflight.get("content_policy"),
            "blocked_reasons": preflight.get("blocked_reasons") or [],
            "future_writer_required_gates": preflight.get("future_writer_required_gates") or [],
        },
    }


def _is_checkpoint_content_free(envelope: dict[str, Any]) -> bool:
    forbidden_keys = {
        "backend_payload",
        "messages",
        "raw_messages",
        "raw_user_message",
        "response_text",
        "prompt",
        "prompt_text",
        "snippet_text",
        "page_body",
        "full_page_body",
        "raw_user_content",
        "user_content",
        "backend_response_text",
        "api_key",
    }

    def walk(value: Any) -> bool:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key) in forbidden_keys:
                    return False
                if not walk(item):
                    return False
        elif isinstance(value, list):
            return all(walk(item) for item in value)
        return True

    return walk(envelope)


def write_relayrun_checkpoint_if_enabled(
    artifact: dict[str, Any],
    *,
    write_enabled: bool = False,
    dry_run_only: bool = True,
) -> dict[str, Any]:
    """Persist a content-free RelayRUN checkpoint envelope when gates allow it.

    The default path is diagnostics-only and does not write files or create
    directories. Even when enabled, this writer stores only a content-free
    envelope and uses a no-overwrite temp-file-then-rename flow.
    """

    updated = _copy_jsonable_mapping(artifact)
    preflight = updated.get("checkpoint_writer_preflight")
    if not isinstance(preflight, dict):
        return updated

    target_root = str(preflight.get("target_root") or ".relayrun/checkpoints")
    target_path_preview = str(preflight.get("target_path_preview") or "")
    path_safety = preflight.get("path_safety")
    if not isinstance(path_safety, dict):
        path_safety = {}
    content_policy = preflight.get("content_policy")
    if not isinstance(content_policy, dict):
        content_policy = {}

    blocked_reasons: list[str] = []
    if not write_enabled:
        blocked_reasons.append("checkpoint_write_disabled")
    if dry_run_only:
        blocked_reasons.append("checkpoint_dry_run_only")
    if path_safety.get("path_traversal_detected") is True:
        blocked_reasons.append("checkpoint_path_traversal_detected")
    if path_safety.get("absolute_path_detected") is True:
        blocked_reasons.append("checkpoint_absolute_path_detected")
    if content_policy.get("content_free") is not True:
        blocked_reasons.append("checkpoint_content_policy_failed")

    target_root_path = Path(target_root)
    target_path = Path(target_path_preview)
    if target_root_path.is_absolute() or target_path.is_absolute():
        blocked_reasons.append("checkpoint_absolute_path_detected")
    if ".." in target_root_path.parts or ".." in target_path.parts:
        blocked_reasons.append("checkpoint_path_traversal_detected")

    try:
        root_resolved = target_root_path.resolve()
        target_resolved = target_path.resolve()
        if target_resolved != root_resolved and root_resolved not in target_resolved.parents:
            blocked_reasons.append("checkpoint_target_outside_root")
    except OSError:
        blocked_reasons.append("checkpoint_path_resolution_failed")

    envelope = _checkpoint_envelope_from_artifact(updated)
    content_free = _is_checkpoint_content_free(envelope)
    if not content_free:
        blocked_reasons.append("checkpoint_content_policy_failed")

    preflight["content_policy"] = dict(content_policy)
    preflight["content_policy"]["content_free"] = content_free
    preflight["checkpoint_write_attempted"] = bool(write_enabled and not dry_run_only)
    preflight["write_allowed"] = False
    preflight["preflight_passed"] = False
    preflight["directory_creation_attempted"] = False
    preflight["blocked_reasons"] = _append_unique_reasons([], blocked_reasons)
    updated["checkpoint_write_attempted"] = preflight["checkpoint_write_attempted"]
    updated["checkpoint_persisted"] = False
    updated["checkpoint_writer_failed"] = False
    updated["persisted_path"] = None
    updated["persisted_bytes"] = None
    updated["content_free"] = content_free
    _set_checkpoint_persistence_plan_state(
        updated,
        write_allowed=False,
        checkpoint_persisted=False,
        checkpoint_write_attempted=preflight["checkpoint_write_attempted"],
        blocked_reasons=blocked_reasons,
    )

    if blocked_reasons:
        return updated

    persisted_path = target_path.as_posix()
    _set_checkpoint_persistence_plan_state(
        updated,
        write_allowed=True,
        checkpoint_persisted=True,
        checkpoint_write_attempted=True,
        persisted_path=persisted_path,
        blocked_reasons=[],
    )
    preflight["write_allowed"] = True
    preflight["preflight_passed"] = True
    preflight["directory_creation_attempted"] = True
    envelope = _checkpoint_envelope_from_artifact(updated)
    envelope["checkpoint_persisted"] = True
    envelope["checkpoint_writer_preflight"]["write_allowed"] = True
    envelope["checkpoint_writer_preflight"]["preflight_passed"] = True
    envelope["checkpoint_writer_preflight"]["checkpoint_write_attempted"] = True
    envelope["checkpoint_writer_preflight"]["directory_creation_attempted"] = True
    envelope["checkpoint_writer_preflight"]["blocked_reasons"] = []
    data = (json.dumps(envelope, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    temp_path = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.tmp")

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with temp_path.open("xb") as f:
            f.write(data)
        try:
            os.link(temp_path, target_path)
        except FileExistsError:
            preflight["write_allowed"] = False
            preflight["preflight_passed"] = False
            preflight["blocked_reasons"] = _append_unique_reasons(
                preflight.get("blocked_reasons"), ["checkpoint_file_exists"]
            )
            _set_checkpoint_persistence_plan_state(
                updated,
                write_allowed=False,
                checkpoint_persisted=False,
                checkpoint_write_attempted=True,
                blocked_reasons=["checkpoint_file_exists"],
            )
            return updated
        finally:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass
    except Exception as exc:  # noqa: BLE001 - writer failure must stay diagnostics-only.
        updated["checkpoint_writer_failed"] = True
        preflight["write_allowed"] = False
        preflight["preflight_passed"] = False
        preflight["writer_error_type"] = exc.__class__.__name__
        preflight["blocked_reasons"] = _append_unique_reasons(
            preflight.get("blocked_reasons"), ["checkpoint_writer_failed"]
        )
        _set_checkpoint_persistence_plan_state(
            updated,
            write_allowed=False,
            checkpoint_persisted=False,
            checkpoint_write_attempted=preflight["checkpoint_write_attempted"],
            blocked_reasons=["checkpoint_writer_failed"],
        )
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass
        return updated

    updated["checkpoint_persisted"] = True
    updated["persisted_path"] = persisted_path
    updated["persisted_bytes"] = len(data)
    updated["content_free"] = True
    preflight["checkpoint_persisted"] = True
    preflight["persisted_path"] = persisted_path
    preflight["persisted_bytes"] = len(data)
    preflight["content_free"] = True
    return updated
