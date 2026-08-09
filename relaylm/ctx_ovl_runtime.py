"""OVL-1 participant-private runtime over governed EV-1 evidence.

The slice is process-local, bounded, rebuildable, non-durable, and fails
closed for shared, relationship, and quarantine partitions.
"""
from __future__ import annotations

import hashlib
import threading
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from relaylm.ctx_ovl_records import (
    _admit_candidate,
    _build_sync_event,
    _invalidate_source,
)
from relaylm.ctx_ovl_selection import (
    _build_context_selection,
    _inject_hint,
    _reflex_snapshot,
    _render_transient_hint,
    _select_overlays,
)
from relaylm.ctx_ovl_sync import CtxOvlSyncMode, _synchronize_partition
from relaylm.ctx_ovl_types import (
    CtxOvlRuntimeResult,
    _AuthorizedCandidate,
    _ParticipantPartitionState,
    _new_partition_state,
    evaluate_ctx_ovl_write_attempt,
)
from relaylm.evidence.common import canonical_digest, dedupe
from relaylm.evidence.space import (
    EvidenceSpaceDescriptor,
    build_bootstrap_evidence_space_descriptor,
)
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.evidence.streams import derive_participant_change_partition_id
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result

if TYPE_CHECKING:
    from relaylm.config import RelayLMConfig
    from relaylm.pipeline_context import PipelineContext
    from relaylm.routing import ResolvedRoute

_WORKSPACE_REF = "relaylm-local"


def derive_private_conversation_ref(route: "ResolvedRoute") -> str | None:
    """Return the same opaque private-conversation identity used by EV-1."""

    if not isinstance(route.user_id, str) or not route.user_id:
        return None
    if not isinstance(route.session_id, str) or not route.session_id:
        return None
    digest = hashlib.sha256(
        f"{route.user_id}\0{route.session_id}".encode("utf-8")
    ).hexdigest()
    return f"privateconversation_{digest}"


class _CtxOvlRegistry:
    """Process-local state; never serialized and rebuilt from governed evidence."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.partitions: dict[tuple[str, str], _ParticipantPartitionState] = {}


_registry_lock = threading.Lock()
_registries: dict[str, _CtxOvlRegistry] = {}


def _registry_for(config: "RelayLMConfig") -> _CtxOvlRegistry:
    key = str(config.evidence_data_root or "ctx_ovl_no_evidence_root")
    with _registry_lock:
        registry = _registries.get(key)
        if registry is None:
            registry = _CtxOvlRegistry()
            _registries[key] = registry
        return registry


def reset_ctx_ovl_runtime_cache() -> None:
    """Test/operator helper: emulate process-local overlay loss before rebuild."""

    with _registry_lock:
        _registries.clear()


def prepare_ctx_ovl_before_user_capture(
    *,
    config: "RelayLMConfig",
    pipeline_context: "PipelineContext",
    resolved_scope: Mapping[str, object],
    evidence_store: EvidenceRecordStore | None,
    evaluated_at: datetime | None = None,
) -> PipelineNodeResult | None:
    """Synchronize/select prior evidence and optionally inject one hint.

    Dry-run executes the same governed reads, authorization, catch-up/rebuild,
    TTL, and selection logic on a detached state copy. It differs only by not
    mutating the process-local registry or the backend-bound payload.
    """

    if not bool(config.ctx_ovl_enabled):
        return None
    route = pipeline_context.route
    gate_reasons = dedupe((
        *_config_gate_reasons(config),
        *_route_gate_reasons(route, resolved_scope),
    ))
    if gate_reasons:
        return _node_result(
            "ctx_ovl_prepare",
            CtxOvlRuntimeResult(
                status="fail_closed", blocked_reasons=gate_reasons
            ),
        )
    if evidence_store is None:
        return _node_result(
            "ctx_ovl_prepare",
            CtxOvlRuntimeResult(
                status="fail_closed",
                blocked_reasons=("ctx_ovl_evidence_store_required",),
            ),
        )

    now = _utc(evaluated_at)
    identity, reasons = _resolve_identity(route, now)
    if identity is None:
        return _node_result(
            "ctx_ovl_prepare",
            CtxOvlRuntimeResult(status="fail_closed", blocked_reasons=reasons),
        )
    (
        private_session_ref,
        descriptor,
        change_partition_id,
        participant_partition_id,
    ) = identity
    registry = _registry_for(config)
    key = (private_session_ref, participant_partition_id)
    dry_run = bool(config.ctx_ovl_dry_run_only) or not bool(
        config.ctx_ovl_apply_enabled
    )
    with registry.lock:
        existing = registry.partitions.get(key)
        working_existing = deepcopy(existing) if dry_run else existing
        mode: CtxOvlSyncMode = (
            "rebuild" if working_existing is None else "catch_up"
        )
        state, sync = _synchronize_partition(
            existing=working_existing,
            tx_store=evidence_store,
            descriptor=descriptor,
            session_id=private_session_ref,
            participant_partition_id=participant_partition_id,
            change_partition_id=change_partition_id,
            evaluated_at=now,
            mode=mode,
            request_id=pipeline_context.request_id,
        )
        if state is not None and not dry_run:
            registry.partitions[key] = state
        if state is None or sync.status == "fail_closed":
            return _node_result("ctx_ovl_prepare", sync)

        selected, selection_reasons = _select_overlays(
            state, evaluated_at=now
        )
        if selection_reasons:
            return _node_result(
                "ctx_ovl_prepare",
                CtxOvlRuntimeResult(
                    status="fail_closed",
                    blocked_reasons=selection_reasons,
                    sync_mode=sync.sync_mode,
                    sync_outcome=sync.sync_outcome,
                    admitted_count=sync.admitted_count,
                    omitted_count=sync.omitted_count,
                    reflex_snapshot=_reflex_snapshot(state, "unknown"),
                ),
            )
        if selected:
            state.last_selection = _build_context_selection(
                state, selected=selected, evaluated_at=now
            )
        if dry_run:
            return _node_result(
                "ctx_ovl_prepare",
                CtxOvlRuntimeResult(
                    status="dry_run_ready",
                    blocked_reasons=("ctx_ovl_apply_not_enabled",),
                    sync_mode=sync.sync_mode,
                    sync_outcome=sync.sync_outcome,
                    selected_count=len(selected),
                    admitted_count=sync.admitted_count,
                    omitted_count=sync.omitted_count,
                    payload_injection_applied=False,
                    reflex_snapshot=_reflex_snapshot(state, "fresh"),
                ),
            )

        applied = False
        if selected:
            rendered = _render_transient_hint(selected)
            mutated, mutation_reasons = _inject_hint(
                pipeline_context.forwarded_payload, rendered
            )
            if mutated is None:
                return _node_result(
                    "ctx_ovl_prepare",
                    CtxOvlRuntimeResult(
                        status="fail_closed",
                        blocked_reasons=mutation_reasons,
                        sync_mode=sync.sync_mode,
                        sync_outcome=sync.sync_outcome,
                        selected_count=len(selected),
                        admitted_count=sync.admitted_count,
                        omitted_count=sync.omitted_count,
                        reflex_snapshot=_reflex_snapshot(state, "unknown"),
                    ),
                )
            pipeline_context.replace_forwarded_payload(
                mutated, "ctx_ovl_participant_private"
            )
            applied = True
        result = CtxOvlRuntimeResult(
            status="applied",
            sync_mode=sync.sync_mode,
            sync_outcome=sync.sync_outcome,
            selected_count=len(selected),
            admitted_count=sync.admitted_count,
            omitted_count=sync.omitted_count,
            payload_injection_applied=applied,
            reflex_snapshot=_reflex_snapshot(state, "fresh"),
        )
        return _node_result("ctx_ovl_prepare", result)


def refresh_ctx_ovl_after_user_capture(
    *,
    config: "RelayLMConfig",
    pipeline_context: "PipelineContext",
    resolved_scope: Mapping[str, object],
    evidence_store: EvidenceRecordStore | None,
    evaluated_at: datetime | None = None,
) -> PipelineNodeResult | None:
    """Admit newly committed user evidence for future requests, never this one."""

    if not bool(config.ctx_ovl_enabled):
        return None
    capture = pipeline_context.evidence_user_input_capture_result
    if capture is None:
        return None
    if capture.status not in {"admitted", "dry_run_ready"}:
        return _node_result(
            "ctx_ovl_admit_current",
            CtxOvlRuntimeResult(
                status="fail_closed",
                blocked_reasons=("ctx_ovl_current_source_not_admitted",),
            ),
        )
    if evidence_store is None:
        return _node_result(
            "ctx_ovl_admit_current",
            CtxOvlRuntimeResult(
                status="fail_closed",
                blocked_reasons=("ctx_ovl_evidence_store_required",),
            ),
        )
    route_reasons = dedupe((
        *_config_gate_reasons(config),
        *_route_gate_reasons(pipeline_context.route, resolved_scope),
    ))
    if route_reasons:
        return _node_result(
            "ctx_ovl_admit_current",
            CtxOvlRuntimeResult(
                status="fail_closed", blocked_reasons=route_reasons
            ),
        )

    now = _utc(evaluated_at)
    identity, reasons = _resolve_identity(pipeline_context.route, now)
    if identity is None:
        return _node_result(
            "ctx_ovl_admit_current",
            CtxOvlRuntimeResult(status="fail_closed", blocked_reasons=reasons),
        )
    (
        private_session_ref,
        descriptor,
        change_partition_id,
        participant_partition_id,
    ) = identity
    registry = _registry_for(config)
    key = (private_session_ref, participant_partition_id)
    dry_run = bool(config.ctx_ovl_dry_run_only) or not bool(
        config.ctx_ovl_apply_enabled
    )
    with registry.lock:
        existing = registry.partitions.get(key)
        working_existing = deepcopy(existing) if dry_run else existing
        state, sync = _synchronize_partition(
            existing=working_existing,
            tx_store=evidence_store,
            descriptor=descriptor,
            session_id=private_session_ref,
            participant_partition_id=participant_partition_id,
            change_partition_id=change_partition_id,
            evaluated_at=now,
            mode="current_source" if working_existing is not None else "rebuild",
            request_id=pipeline_context.request_id,
        )
        if state is not None and not dry_run:
            registry.partitions[key] = state
        if dry_run and sync.status == "applied":
            sync = CtxOvlRuntimeResult(
                status="dry_run_ready",
                blocked_reasons=("ctx_ovl_apply_not_enabled",),
                sync_mode=sync.sync_mode,
                sync_outcome=sync.sync_outcome,
                admitted_count=sync.admitted_count,
                omitted_count=sync.omitted_count,
                reflex_snapshot=sync.reflex_snapshot,
            )
        return _node_result("ctx_ovl_admit_current", sync)


def _config_gate_reasons(config: "RelayLMConfig") -> tuple[str, ...]:
    """Fence OVL-1 from analyzers and the legacy CTX writer it cannot order yet."""

    if bool(config.ctx_ovl_dry_run_only) or not bool(config.ctx_ovl_apply_enabled):
        return ()
    reasons: list[str] = []
    if bool(config.relayemo_enabled):
        reasons.append("ctx_ovl_apply_conflicts_with_relayemo_analysis")
    if bool(config.relayctx_short_term_runtime_injection_apply_enabled):
        reasons.append("ctx_ovl_apply_conflicts_with_legacy_relayctx_injection")
    return dedupe(reasons)


def _route_gate_reasons(
    route: "ResolvedRoute", resolved_scope: Mapping[str, object]
) -> tuple[str, ...]:
    reasons: list[str] = []
    if route.mode_applied == "pass_through":
        reasons.append("ctx_ovl_pass_through_unsupported")
    if not isinstance(route.user_id, str) or not route.user_id:
        reasons.append("ctx_ovl_participant_identity_required")
    if not isinstance(route.session_id, str) or not route.session_id:
        reasons.append("ctx_ovl_session_identity_required")
    if route.room_id is not None or route.scene_id is not None:
        reasons.append("ctx_ovl_non_participant_partition_unsupported_in_ovl1")
    for key in ("user_id", "session_id", "room_id", "scene_id"):
        if resolved_scope.get(key) != getattr(route, key):
            reasons.append(f"ctx_ovl_route_scope_conflict:{key}")
    return dedupe(reasons)


def _resolve_identity(
    route: "ResolvedRoute", now: datetime
) -> tuple[
    tuple[str, EvidenceSpaceDescriptor, str, str] | None,
    tuple[str, ...],
]:
    private_session_ref = derive_private_conversation_ref(route)
    if private_session_ref is None:
        return None, ("ctx_ovl_private_conversation_identity_unavailable",)
    descriptor, descriptor_reasons = build_bootstrap_evidence_space_descriptor(
        workspace_or_tenant_ref=_WORKSPACE_REF,
        character_id=route.character_id or "",
        memory_namespace=route.memory_namespace or "",
        session_id=private_session_ref,
        created_at=now.isoformat(),
    )
    if descriptor is None:
        return None, tuple(
            f"ctx_ovl:{reason}" for reason in descriptor_reasons
        )
    participant = descriptor.controller_principal_ref
    change_partition_id = derive_participant_change_partition_id(
        evidence_space_id=descriptor.evidence_space_id,
        participant_ref=participant,
    )
    participant_partition_id = "ctxovlparticipant_" + canonical_digest(
        {
            "session_id": private_session_ref,
            "participant_id": participant.principal_id,
        }
    )
    return (
        private_session_ref,
        descriptor,
        change_partition_id,
        participant_partition_id,
    ), ()


def _node_result(
    node_name: str, result: CtxOvlRuntimeResult
) -> PipelineNodeResult:
    status = {
        "applied": "applied",
        "dry_run_ready": "diagnostic_only",
        "fail_closed": "blocked",
        "integrity_conflict": "failed",
    }.get(result.status, "diagnostic_only")
    diagnostics = result.to_log_dict()
    return build_pipeline_node_result(
        node_name=node_name,
        status=status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=diagnostics,
        artifacts=(
            {
                "artifact_name": node_name,
                "schema_version": diagnostics["schema_version"],
                "content_free": True,
                "present": True,
            },
        ),
    )


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("ctx_ovl_evaluated_at_timezone_required")
    return current.astimezone(timezone.utc)


__all__ = [
    "CtxOvlRuntimeResult",
    "_AuthorizedCandidate",
    "_admit_candidate",
    "_build_context_selection",
    "_build_sync_event",
    "_invalidate_source",
    "_new_partition_state",
    "_reflex_snapshot",
    "_select_overlays",
    "derive_private_conversation_ref",
    "evaluate_ctx_ovl_write_attempt",
    "prepare_ctx_ovl_before_user_capture",
    "refresh_ctx_ovl_after_user_capture",
    "reset_ctx_ovl_runtime_cache",
]
