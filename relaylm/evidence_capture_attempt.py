"""RouteCaptureGrantSnapshot v1 and CaptureAttemptEvent v1 (Contract 1A).

``CaptureAttemptLog`` is an in-process, append-only builder for one capture
attempt's event chain. It enforces the exact resolver rules from Contract 1A
(gap-free revisions, ``reserve -> begin_content? -> finalize_candidate ->
bind_admission`` or ``reserve -> terminal_no_source``, terminal states are
immutable) and returns the accumulated events for the caller to persist via
``evidence_store``. EV-1 does not implement the ``mark_abandoned_recoverable``
/ ``recover_abandoned`` detour: a request lives for one process lifetime, so
cross-process capture-attempt recovery is out of scope for this slice (see
the PR's documented limitations).
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field

from relaylm.evidence_common import (
    AuthorityScope,
    PrincipalRef,
    build_runtime_authority,
    dedupe,
    new_opaque_id,
)

ROUTE_SNAPSHOT_SCHEMA = "relaylm.route_capture_grant_snapshot.v1"
CAPTURE_ATTEMPT_SCHEMA = "relaylm.capture_attempt_event.v1"

ROUTE_MODES = frozenset(
    {
        "managed_conversation",
        "explicit_pass_through",
        "tool_transaction",
        "authorized_import",
        "governed_system",
    }
)
CAPTURE_PROFILES = frozenset(
    {
        "managed_user_input",
        "managed_assistant_response",
        "pass_through_explicit_opt_in",
        "tool_transaction_evidence",
        "authorized_import_evidence",
        "governed_system_evidence",
    }
)
_MANAGED_CONVERSATION_PROFILES = frozenset(
    {"managed_user_input", "managed_assistant_response"}
)

CAPTURE_CHANNELS = frozenset(
    {
        "managed_text",
        "managed_voice_input",
        "managed_assistant_text",
        "tool_result",
        "sensor",
        "authorized_import",
        "governed_system",
        "pass_through_opt_in",
    }
)
SOURCE_ROLES = frozenset(
    {
        "user_input",
        "assistant_response",
        "tool_result",
        "tool_action",
        "sensor_result",
        "imported_source",
        "system_source",
    }
)

# Closed cross-field matrix (capture_profile -> stream_kind/direction/source_role/channel).
_CAPTURE_MATRIX: dict[str, dict[str, object]] = {
    "managed_user_input": {
        "capture_stream_kind": "managed_user_input",
        "stream_direction": "inbound",
        "source_role": "user_input",
        "capture_channels": {"managed_text", "managed_voice_input"},
    },
    "managed_assistant_response": {
        "capture_stream_kind": "managed_assistant_output",
        "stream_direction": "outbound",
        "source_role": "assistant_response",
        "capture_channels": {"managed_assistant_text"},
    },
}


@dataclass(frozen=True)
class RouteCaptureGrantSnapshot:
    schema: str
    route_binding_id: str
    route_contract_ref: str
    route_contract_revision: int
    route_contract_snapshot_digest: str
    evidence_space_id: str
    route_mode: str
    capture_profile: str
    allowed_origin_kinds: tuple[str, ...]
    allowed_capture_stream_kinds: tuple[str, ...]
    allowed_stream_directions: tuple[str, ...]
    effective_from: str
    expires_at_or_null: str | None
    revocation_revision_observed: int
    validated_at: str
    validator_principal_ref: PrincipalRef
    validator_authority_scope: AuthorityScope

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "route_binding_id": self.route_binding_id,
            "route_contract_ref": self.route_contract_ref,
            "route_contract_revision": self.route_contract_revision,
            "route_contract_snapshot_digest": self.route_contract_snapshot_digest,
            "evidence_space_id": self.evidence_space_id,
            "route_mode": self.route_mode,
            "capture_profile": self.capture_profile,
            "allowed_origin_kinds": list(self.allowed_origin_kinds),
            "allowed_capture_stream_kinds": list(self.allowed_capture_stream_kinds),
            "allowed_stream_directions": list(self.allowed_stream_directions),
            "effective_from": self.effective_from,
            "expires_at_or_null": self.expires_at_or_null,
            "revocation_revision_observed": self.revocation_revision_observed,
            "validated_at": self.validated_at,
            "validator_principal_ref": self.validator_principal_ref.to_dict(),
            "validator_authority_scope": self.validator_authority_scope.to_dict(),
        }


def build_managed_conversation_route_snapshot(
    *,
    snapshot_payload: Mapping[str, object] | None,
    evidence_space_id: str,
    capture_profile: str,
) -> tuple[RouteCaptureGrantSnapshot | None, tuple[str, ...]]:
    """Validate a route-owned immutable snapshot without issuing authority."""

    if snapshot_payload is None:
        return None, ("route_capture_grant_snapshot_missing",)
    try:
        from relaylm.evidence_space import _authority_scope_from_dict

        snapshot = RouteCaptureGrantSnapshot(
            schema=str(snapshot_payload["schema"]),
            route_binding_id=str(snapshot_payload["route_binding_id"]),
            route_contract_ref=str(snapshot_payload["route_contract_ref"]),
            route_contract_revision=int(snapshot_payload["route_contract_revision"]),
            route_contract_snapshot_digest=str(
                snapshot_payload["route_contract_snapshot_digest"]
            ),
            evidence_space_id=str(snapshot_payload["evidence_space_id"]),
            route_mode=str(snapshot_payload["route_mode"]),
            capture_profile=str(snapshot_payload["capture_profile"]),
            allowed_origin_kinds=tuple(snapshot_payload["allowed_origin_kinds"]),
            allowed_capture_stream_kinds=tuple(
                snapshot_payload["allowed_capture_stream_kinds"]
            ),
            allowed_stream_directions=tuple(
                snapshot_payload["allowed_stream_directions"]
            ),
            effective_from=str(snapshot_payload["effective_from"]),
            expires_at_or_null=snapshot_payload["expires_at_or_null"],
            revocation_revision_observed=int(
                snapshot_payload["revocation_revision_observed"]
            ),
            validated_at=str(snapshot_payload["validated_at"]),
            validator_principal_ref=PrincipalRef(
                **snapshot_payload["validator_principal_ref"]
            ),
            validator_authority_scope=_authority_scope_from_dict(
                snapshot_payload["validator_authority_scope"]
            ),
        )
    except (KeyError, TypeError, ValueError):
        return None, ("route_capture_grant_snapshot_shape_invalid",)
    reasons: list[str] = []
    if snapshot.schema != ROUTE_SNAPSHOT_SCHEMA:
        reasons.append("route_capture_grant_snapshot_schema_invalid")
    if snapshot.evidence_space_id != evidence_space_id:
        reasons.append("route_capture_grant_snapshot_cross_space")
    if snapshot.route_mode != "managed_conversation":
        reasons.append("route_capture_grant_snapshot_mode_invalid")
    if snapshot.capture_profile != capture_profile:
        reasons.append("route_capture_grant_snapshot_profile_mismatch")
    if snapshot.validated_at < snapshot.effective_from:
        reasons.append("route_capture_grant_snapshot_not_effective")
    if (
        snapshot.expires_at_or_null is not None
        and snapshot.validated_at >= snapshot.expires_at_or_null
    ):
        reasons.append("route_capture_grant_snapshot_expired")
    if snapshot.revocation_revision_observed < 0:
        reasons.append("route_capture_grant_snapshot_revocation_invalid")
    return (snapshot if not reasons else None), dedupe(reasons)


def validate_route_snapshot_for_capture(
    snapshot: RouteCaptureGrantSnapshot,
    *,
    evidence_space_id: str,
    capture_profile: str,
    capture_channel: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if type(snapshot) is not RouteCaptureGrantSnapshot:
        return ("route_capture_grant_snapshot_missing",)
    if snapshot.evidence_space_id != evidence_space_id:
        reasons.append("route_capture_grant_snapshot_cross_space")
    if snapshot.route_mode != "managed_conversation":
        reasons.append("route_capture_grant_snapshot_mode_invalid")
    if snapshot.capture_profile != capture_profile:
        reasons.append("route_capture_grant_snapshot_profile_mismatch")
    expected = _CAPTURE_MATRIX.get(capture_profile)
    if expected is None:
        reasons.append("route_capture_grant_snapshot_profile_unsupported")
    elif capture_channel not in expected["capture_channels"]:
        reasons.append("route_capture_grant_snapshot_channel_invalid")
    if snapshot.expires_at_or_null is not None and snapshot.expires_at_or_null <= snapshot.validated_at:
        reasons.append("route_capture_grant_snapshot_expired")
    return dedupe(reasons)


# --- CaptureAttemptEvent lifecycle -----------------------------------------

_OPERATIONS_ORDER = (
    "reserve",
    "begin_content",
    "finalize_candidate",
    "bind_admission",
)
_TERMINAL_OPERATIONS = frozenset({"bind_admission", "terminal_no_source"})


@dataclass
class CaptureAttemptLog:
    """Builder/validator for one capture attempt's append-only event chain.

    ``evidence_space_id``/``capture_stream_epoch_id``/``capture_sequence``/
    ``route_capture_grant_snapshot_ref``/``capture_channel``/``source_role``
    are attempt-invariant context required on every ``CaptureAttemptEvent``
    record by the schema; they are fixed at construction time (after the
    Contract 1D capture sequence has already been reserved -- the contract's
    ``reserve`` payload rule requires "sequence MUST already be reserved by
    Contract 1D" before a CaptureAttempt can reference it).
    """

    evidence_space_id: str
    capture_stream_epoch_id: str
    capture_sequence: int
    route_capture_grant_snapshot_ref: str
    capture_channel: str
    source_role: str
    capture_attempt_id: str = field(default_factory=lambda: new_opaque_id("captureattempt"))
    events: list[dict[str, object]] = field(default_factory=list)
    _state: str = field(default="unstarted", init=False)
    _revision: int = field(default=0, init=False)

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return self._state in _TERMINAL_OPERATIONS

    def _issuer(
        self, *, allowed_operations: tuple[str, ...], recorded_at: str
    ) -> tuple[dict[str, object], dict[str, object]]:
        principal, scope = build_runtime_authority(
            scope_kind="evidence_operator",
            allowed_operations=allowed_operations,
            evidence_space_id=self.evidence_space_id,
            issued_at=recorded_at,
        )
        return principal.to_dict(), scope.to_dict()

    def _append(
        self,
        operation: str,
        payload: dict[str, object],
        *,
        recorded_at: str,
        operation_idempotency_key: str,
        allowed_operation: str,
    ) -> tuple[bool, tuple[str, ...]]:
        if self.is_terminal:
            return False, ("capture_attempt_already_terminal",)
        expected_next = {
            "unstarted": {"reserve"},
            "reserve": {"begin_content", "finalize_candidate", "terminal_no_source"},
            "begin_content": {"finalize_candidate", "terminal_no_source"},
            "finalize_candidate": {"bind_admission"},
        }.get(self._state, set())
        if operation not in expected_next:
            return False, ("capture_attempt_operation_out_of_order",)
        self._revision += 1
        issuer_principal_ref, issuer_authority_scope = self._issuer(
            allowed_operations=(allowed_operation,), recorded_at=recorded_at
        )
        self.events.append(
            {
                "schema": CAPTURE_ATTEMPT_SCHEMA,
                "capture_attempt_event_id": new_opaque_id("captureevent"),
                "capture_attempt_id": self.capture_attempt_id,
                "attempt_revision": self._revision,
                "expected_previous_attempt_revision_or_null": (
                    self._revision - 1 if self._revision > 1 else None
                ),
                "evidence_space_id": self.evidence_space_id,
                "capture_stream_epoch_id": self.capture_stream_epoch_id,
                "capture_sequence": self.capture_sequence,
                "route_capture_grant_snapshot_ref": self.route_capture_grant_snapshot_ref,
                "capture_channel": self.capture_channel,
                "source_role": self.source_role,
                "operation": operation,
                "operation_payload": payload,
                "recorded_at": recorded_at,
                "operation_idempotency_key": operation_idempotency_key,
                "authority_principal_ref": issuer_principal_ref,
                "authority_scope": issuer_authority_scope,
            }
        )
        self._state = operation
        return True, ()

    def reserve(
        self,
        *,
        capture_stream_kind: str,
        stream_direction: str,
        recorded_at: str,
        operation_idempotency_key: str,
        response_capture_reservation_ref_or_null: str | None = None,
    ) -> tuple[bool, tuple[str, ...]]:
        # Content-free and deterministic per attempt -- not a real temporary
        # storage handle (EV-1 does not stage pre-admission payload bytes
        # under a separate temporary-handle authority), just a stable opaque
        # correlation token satisfying the schema's required field.
        temporary_control_ref = "tmpctl_" + hashlib.sha256(
            f"{self.capture_attempt_id}\0temporary_control".encode("utf-8")
        ).hexdigest()
        return self._append(
            "reserve",
            {
                "capture_stream_kind": capture_stream_kind,
                "stream_direction": stream_direction,
                "temporary_control_ref": temporary_control_ref,
                "response_capture_reservation_ref_or_null": (
                    response_capture_reservation_ref_or_null
                ),
            },
            recorded_at=recorded_at,
            operation_idempotency_key=f"{operation_idempotency_key}:reserve",
            allowed_operation="capture_attempt_reserve",
        )

    def finalize_candidate(
        self,
        *,
        preallocated_source_event_id: str,
        canonical_source_manifest: dict[str, object],
        canonical_source_manifest_digest: str,
        validation_bundle_id: str,
        validation_bundle_revision: int,
        recorded_at: str,
        operation_idempotency_key: str,
    ) -> tuple[bool, tuple[str, ...]]:
        temporary_payload_part_handles = [
            {
                "part_id": part["part_id"],
                "temporary_payload_handle": "tmphandle_"
                + hashlib.sha256(
                    f"{self.capture_attempt_id}\0{part['part_id']}".encode("utf-8")
                ).hexdigest(),
            }
            for part in canonical_source_manifest["parts"]
        ]
        return self._append(
            "finalize_candidate",
            {
                "preallocated_source_event_id_or_null": preallocated_source_event_id,
                "canonical_source_manifest": canonical_source_manifest,
                "canonical_source_manifest_digest": canonical_source_manifest_digest,
                "temporary_payload_part_handles": temporary_payload_part_handles,
                "validation_bundle_id": validation_bundle_id,
                "validation_bundle_revision": validation_bundle_revision,
                "finalization_basis_ref": "relaylm.managed_chat_completions_route",
            },
            recorded_at=recorded_at,
            operation_idempotency_key=f"{operation_idempotency_key}:finalize_candidate",
            allowed_operation="capture_attempt_finalize_candidate",
        )

    def bind_admission(
        self, *, admission_decision_id: str, recorded_at: str, operation_idempotency_key: str
    ) -> tuple[bool, tuple[str, ...]]:
        return self._append(
            "bind_admission",
            {"admission_decision_id": admission_decision_id},
            recorded_at=recorded_at,
            operation_idempotency_key=f"{operation_idempotency_key}:bind_admission",
            allowed_operation="capture_attempt_bind_admission",
        )

    def terminal_no_source(
        self, *, terminal_reason: str, recorded_at: str, operation_idempotency_key: str
    ) -> tuple[bool, tuple[str, ...]]:
        if self.is_terminal:
            return False, ("capture_attempt_already_terminal",)
        if self._state not in {"unstarted", "reserve", "begin_content"}:
            return False, ("capture_attempt_operation_out_of_order",)
        self._revision += 1
        issuer_principal_ref, issuer_authority_scope = self._issuer(
            allowed_operations=("capture_attempt_terminal_no_source",), recorded_at=recorded_at
        )
        self.events.append(
            {
                "schema": CAPTURE_ATTEMPT_SCHEMA,
                "capture_attempt_event_id": new_opaque_id("captureevent"),
                "capture_attempt_id": self.capture_attempt_id,
                "attempt_revision": self._revision,
                "expected_previous_attempt_revision_or_null": (
                    self._revision - 1 if self._revision > 1 else None
                ),
                "evidence_space_id": self.evidence_space_id,
                "capture_stream_epoch_id": self.capture_stream_epoch_id,
                "capture_sequence": self.capture_sequence,
                "route_capture_grant_snapshot_ref": self.route_capture_grant_snapshot_ref,
                "capture_channel": self.capture_channel,
                "source_role": self.source_role,
                "operation": "terminal_no_source",
                "operation_payload": {
                    "terminal_reason": terminal_reason,
                    "terminal_at": recorded_at,
                },
                "recorded_at": recorded_at,
                "operation_idempotency_key": f"{operation_idempotency_key}:terminal_no_source",
                "authority_principal_ref": issuer_principal_ref,
                "authority_scope": issuer_authority_scope,
            }
        )
        self._state = "terminal_no_source"
        return True, ()


__all__ = [
    "CAPTURE_ATTEMPT_SCHEMA",
    "CAPTURE_CHANNELS",
    "CAPTURE_PROFILES",
    "ROUTE_MODES",
    "ROUTE_SNAPSHOT_SCHEMA",
    "SOURCE_ROLES",
    "CaptureAttemptLog",
    "RouteCaptureGrantSnapshot",
    "build_managed_conversation_route_snapshot",
    "validate_route_snapshot_for_capture",
]
