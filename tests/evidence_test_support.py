from __future__ import annotations

from relaylm.evidence_common import build_runtime_authority, canonical_digest
from relaylm.evidence_space import derive_evidence_space_id


def route_snapshot(
    *,
    capture_profile: str,
    character_id: str = "char1",
    memory_namespace: str = "ns1",
    session_id: str = "sess1",
    issued_at: str = "2026-07-21T12:00:00+00:00",
) -> dict[str, object]:
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref="relaylm-local",
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
    )
    digest = canonical_digest(
        {
            "route": "test-private-route",
            "evidence_space_id": evidence_space_id,
            "capture_profile": capture_profile,
        }
    )
    principal, scope = build_runtime_authority(
        scope_kind="route_configuration_authority",
        allowed_operations=("route_capture_snapshot_issue",),
        evidence_space_id=evidence_space_id,
        issued_at=issued_at,
    )
    return {
        "schema": "relaylm.route_capture_grant_snapshot.v1",
        "route_binding_id": "routebind_"
        + canonical_digest(
            {
                "route_contract_snapshot_digest": digest,
                "validated_at": issued_at,
            }
        ),
        "route_contract_ref": "relaylm.test_private_route",
        "route_contract_revision": 1,
        "route_contract_snapshot_digest": digest,
        "evidence_space_id": evidence_space_id,
        "route_mode": "managed_conversation",
        "capture_profile": capture_profile,
        "allowed_origin_kinds": [
            "participant" if capture_profile == "managed_user_input" else "assistant"
        ],
        "allowed_capture_stream_kinds": [
            "managed_user_input"
            if capture_profile == "managed_user_input"
            else "managed_assistant_output"
        ],
        "allowed_stream_directions": [
            "inbound" if capture_profile == "managed_user_input" else "outbound"
        ],
        "effective_from": issued_at,
        "expires_at_or_null": None,
        "revocation_revision_observed": 0,
        "validated_at": issued_at,
        "validator_principal_ref": principal.to_dict(),
        "validator_authority_scope": scope.to_dict(),
    }
