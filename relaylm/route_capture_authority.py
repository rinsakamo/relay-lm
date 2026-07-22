"""Route-owned Contract 1A capture-grant snapshot issuance for EV-1.

This module belongs to the managed-route boundary, not to Evidence admission.
Evidence code receives and validates the immutable snapshot; it never invents
route authority from content or from an implicit managed-mode assumption.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

from relaylm.evidence_common import build_runtime_authority, canonical_digest
from relaylm.routing import ResolvedRoute


def issue_managed_route_capture_snapshot(
    *,
    route: ResolvedRoute,
    resolved_scope: Mapping[str, object],
    evidence_space_id: str,
    capture_profile: str,
    issued_at: str | None = None,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    """Issue one immutable snapshot from the actual resolved server route."""

    reasons: list[str] = []
    if capture_profile not in {
        "managed_user_input",
        "managed_assistant_response",
    }:
        reasons.append("route_capture_profile_unsupported")
    if route.mode_applied == "pass_through":
        reasons.append("route_capture_pass_through_forbidden")
    if not isinstance(route.user_id, str) or not route.user_id:
        reasons.append("route_capture_private_user_required")
    if not isinstance(route.session_id, str) or not route.session_id:
        reasons.append("route_capture_private_session_required")
    if route.room_id is not None or route.scene_id is not None:
        reasons.append("route_capture_shared_scope_unsupported")
    for key in ("user_id", "session_id", "room_id", "scene_id"):
        resolved = resolved_scope.get(key)
        configured = getattr(route, key)
        if resolved != configured:
            reasons.append(f"route_capture_scope_conflict:{key}")
    if reasons:
        return None, tuple(dict.fromkeys(reasons))

    timestamp = issued_at or datetime.now(timezone.utc).isoformat()
    route_contract = {
        "route_model": route.route_model,
        "backend_name": route.backend_name,
        "backend_model": route.backend_model,
        "mode_applied": route.mode_applied,
        "character_id": route.character_id,
        "memory_namespace": route.memory_namespace,
        "cache_namespace": route.cache_namespace,
        "user_id": route.user_id,
        "user_type": route.user_type,
        "room_id": route.room_id,
        "scene_id": route.scene_id,
        "session_id": route.session_id,
        "capture_profile": capture_profile,
        "evidence_space_id": evidence_space_id,
    }
    snapshot_digest = canonical_digest(route_contract)
    route_binding_digest = canonical_digest(
        {
            "route_contract_snapshot_digest": snapshot_digest,
            "validated_at": timestamp,
        }
    )
    route_binding_id = f"routebind_{route_binding_digest}"
    origin = "participant" if capture_profile == "managed_user_input" else "assistant"
    stream_kind = (
        "managed_user_input"
        if capture_profile == "managed_user_input"
        else "managed_assistant_output"
    )
    direction = "inbound" if capture_profile == "managed_user_input" else "outbound"
    principal, scope = build_runtime_authority(
        scope_kind="route_configuration_authority",
        allowed_operations=("route_capture_snapshot_issue",),
        evidence_space_id=evidence_space_id,
        issued_at=timestamp,
    )
    return (
        {
            "schema": "relaylm.route_capture_grant_snapshot.v1",
            "route_binding_id": route_binding_id,
            "route_contract_ref": f"relaylm.model_route:{route.route_model}",
            "route_contract_revision": 1,
            "route_contract_snapshot_digest": snapshot_digest,
            "evidence_space_id": evidence_space_id,
            "route_mode": "managed_conversation",
            "capture_profile": capture_profile,
            "allowed_origin_kinds": [origin],
            "allowed_capture_stream_kinds": [stream_kind],
            "allowed_stream_directions": [direction],
            "effective_from": timestamp,
            "expires_at_or_null": None,
            "revocation_revision_observed": 0,
            "validated_at": timestamp,
            "validator_principal_ref": principal.to_dict(),
            "validator_authority_scope": scope.to_dict(),
        },
        (),
    )


__all__ = ["issue_managed_route_capture_snapshot"]
