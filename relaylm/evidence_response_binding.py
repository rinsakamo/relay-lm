"""Contract 1E assistant-response reservation, observation, and binding helpers."""
from __future__ import annotations

from dataclasses import dataclass, field

from relaylm.evidence_common import (
    build_runtime_authority,
    canonical_digest,
    ev1_policy_snapshot_ref,
    utf8_text_digest,
)
from relaylm.evidence_manifest import OccurrenceAudienceSnapshot

RESERVATION_SCHEMA = "relaylm.assistant_response_capture_reservation.v1"
CAPTURE_EVENT_SCHEMA = "relaylm.assistant_response_capture_event.v1"
BINDING_SCHEMA = "relaylm.assistant_response_binding.v1"
PAYLOAD_ATTESTATION_SCHEMA = "relaylm.protected_payload_binding_attestation.v1"


def _request_refs(
    request_source_event_ids: tuple[str, ...], operation_idempotency_key: str
) -> tuple[dict[str, str], ...]:
    if request_source_event_ids:
        return tuple(
            {
                "ref_kind": "source_event",
                "ref_id": source_id,
                "request_role": (
                    "triggering_input" if index == 0 else "additional_current_input"
                ),
            }
            for index, source_id in enumerate(dict.fromkeys(request_source_event_ids))
        )
    return (
        {
            "ref_kind": "capture_attempt",
            "ref_id": "captureattempt_"
            + canonical_digest(
                {
                    "operation_idempotency_key": operation_idempotency_key,
                    "role": "triggering_input",
                }
            ),
            "request_role": "triggering_input",
        },
    )


def build_response_capture_reservation(
    *,
    response_capture_reservation_id: str,
    response_id: str,
    run_id: str,
    turn_id_or_null: str | None,
    evidence_space_id: str,
    route_capture_grant_snapshot_ref: str,
    capture_stream_id: str,
    capture_stream_epoch_id: str,
    capture_sequence: int,
    delivery_cohort_id: str,
    audience: OccurrenceAudienceSnapshot,
    request_source_event_ids: tuple[str, ...],
    reserved_at: str,
    operation_idempotency_key: str,
) -> dict[str, object]:
    principal, scope = build_runtime_authority(
        scope_kind="runtime_finalization_authority",
        allowed_operations=(
            "capture_attempt_begin_content",
            "capture_attempt_bind_admission",
            "capture_attempt_finalize_candidate",
            "capture_attempt_mark_abandoned",
            "capture_attempt_recover",
            "capture_attempt_reserve",
            "capture_attempt_terminal_no_source",
            "response_capture_reserve",
            "response_emission_begin",
            "response_output_observe",
            "response_finalize",
            "response_terminal_no_output",
            "response_mark_abandoned",
            "response_recover_finalization",
        ),
        evidence_space_id=evidence_space_id,
        issued_at=reserved_at,
    )
    refs = _request_refs(request_source_event_ids, operation_idempotency_key)
    return {
        "schema": RESERVATION_SCHEMA,
        "response_capture_reservation_id": response_capture_reservation_id,
        "response_id": response_id,
        "run_id": run_id,
        "turn_id_or_null": turn_id_or_null,
        "evidence_space_id": evidence_space_id,
        "route_capture_grant_snapshot_ref": route_capture_grant_snapshot_ref,
        "capture_stream_id": capture_stream_id,
        "capture_stream_epoch_id": capture_stream_epoch_id,
        "capture_sequence": capture_sequence,
        "delivery_cohort_id": delivery_cohort_id,
        "configured_occurrence_audience": audience.to_dict(),
        "delivery_cohort_audience": audience.to_dict(),
        "audience_policy_basis_ref": "relaylm.evidence_policy.v1",
        "request_source_refs": list(refs),
        "reservation_state": "reserved",
        "reserved_at": reserved_at,
        "reservation_idempotency_key": (
            f"{operation_idempotency_key}:response-reservation"
        ),
        "runtime_principal_ref": principal.to_dict(),
        "runtime_finalization_authority_scope": scope.to_dict(),
        "policy_snapshot_ref": ev1_policy_snapshot_ref().to_dict(),
    }


@dataclass
class ResponseCaptureLog:
    reservation: dict[str, object]
    events: list[dict[str, object]] = field(default_factory=list)

    def _append(
        self,
        operation: str,
        payload: dict[str, object],
        *,
        recorded_at: str,
        operation_idempotency_key: str,
    ) -> dict[str, object]:
        revision = len(self.events) + 1
        operation_authority = {
            "emission_begin": "response_emission_begin",
            "output_observed": "response_output_observe",
            "finalize": "response_finalize",
            "terminal_no_output": "response_terminal_no_output",
            "mark_abandoned": "response_mark_abandoned",
            "recover_finalization": "response_recover_finalization",
        }.get(operation)
        if operation_authority is None:
            raise ValueError("assistant_response_capture_operation_invalid")
        principal, scope = build_runtime_authority(
            scope_kind="runtime_finalization_authority",
            allowed_operations=(operation_authority,),
            evidence_space_id=str(self.reservation["evidence_space_id"]),
            issued_at=recorded_at,
        )
        event_id = "responsecaptureevent_" + canonical_digest(
            {
                "reservation_id": self.reservation[
                    "response_capture_reservation_id"
                ],
                "revision": revision,
                "operation": operation,
                "payload": payload,
                "idempotency_key": operation_idempotency_key,
            }
        )
        event = {
            "schema": CAPTURE_EVENT_SCHEMA,
            "response_capture_event_id": event_id,
            "response_capture_reservation_id": self.reservation[
                "response_capture_reservation_id"
            ],
            "response_revision": revision,
            "expected_previous_response_revision_or_null": (
                revision - 1 if revision > 1 else None
            ),
            "operation": operation,
            "operation_payload": payload,
            "operation_idempotency_key": (
                f"{operation_idempotency_key}:{operation}:{revision}"
            ),
            "recorded_at": recorded_at,
            "runtime_principal_ref": principal.to_dict(),
            "runtime_finalization_authority_scope": scope.to_dict(),
        }
        self.events.append(event)
        return event

    def emission_begin(
        self,
        *,
        first_output_accepted_at: str,
        protected_output_buffer_ref: str,
        operation_idempotency_key: str,
    ) -> dict[str, object]:
        del protected_output_buffer_ref
        return self._append(
            "emission_begin",
            {
                "first_output_unit_sequence": 0,
                "canonical_output_boundary_ref": (
                    "relaylm-managed-visible-output-boundary"
                ),
                "first_output_accepted_at": first_output_accepted_at,
            },
            recorded_at=first_output_accepted_at,
            operation_idempotency_key=operation_idempotency_key,
        )

    def output_observed(
        self,
        *,
        output_unit_sequence: int,
        start_byte: int,
        end_byte: int,
        observed_at: str,
        protected_output_buffer_ref: str,
        operation_idempotency_key: str,
    ) -> dict[str, object]:
        return self._append(
            "output_observed",
            {
                "output_unit_sequence": output_unit_sequence,
                "part_id": "part-0",
                "accepted_range": {
                    "unit": "utf8_byte",
                    "start_inclusive": start_byte,
                    "end_exclusive": end_byte,
                },
                "observation_basis": "accepted_by_canonical_output_boundary",
                "observed_at": observed_at,
                "protected_output_buffer_ref": protected_output_buffer_ref,
            },
            recorded_at=observed_at,
            operation_idempotency_key=operation_idempotency_key,
        )

    def finalize(
        self,
        *,
        binding: dict[str, object],
        finalized_at: str,
        operation_idempotency_key: str,
    ) -> dict[str, object]:
        return self._append(
            "finalize",
            {"assistant_response_binding": binding},
            recorded_at=finalized_at,
            operation_idempotency_key=operation_idempotency_key,
        )

    def terminal_no_output(
        self,
        *,
        reason: str,
        terminal_at: str,
        operation_idempotency_key: str,
    ) -> dict[str, object]:
        return self._append(
            "terminal_no_output",
            {"no_output_reason": reason, "terminal_at": terminal_at},
            recorded_at=terminal_at,
            operation_idempotency_key=operation_idempotency_key,
        )

    def mark_abandoned(
        self,
        *,
        abandon_reason: str,
        last_known_output_unit_sequence_or_null: int | None,
        recovery_case_ref: str,
        recorded_at: str,
        operation_idempotency_key: str,
    ) -> dict[str, object]:
        return self._append(
            "mark_abandoned",
            {
                "abandon_reason": abandon_reason,
                "last_known_output_unit_sequence_or_null": (
                    last_known_output_unit_sequence_or_null
                ),
                "recovery_case_ref": recovery_case_ref,
            },
            recorded_at=recorded_at,
            operation_idempotency_key=operation_idempotency_key,
        )


def build_assistant_response_binding(
    *,
    assistant_response_binding_id: str,
    reservation: dict[str, object],
    accepted_text: str,
    accepted_ranges: tuple[tuple[int, int], ...],
    completion_extent: str,
    termination_cause: str,
    first_output_accepted_at: str,
    finalized_at: str,
    finalization_idempotency_key: str,
) -> dict[str, object]:
    if not accepted_ranges:
        raise ValueError("assistant_response_binding_requires_output")
    canonical_output_parts = [
        {
            "part_id": "part-0",
            "media_type": "text/plain; charset=utf-8",
            "content_representation": {
                "kind": "content_digest",
                "digest_algorithm": "sha256",
                "digest_value": utf8_text_digest(accepted_text),
            },
            "accepted_ranges": [
                {
                    "unit": "utf8_byte",
                    "start_inclusive": start,
                    "end_exclusive": end,
                }
                for start, end in accepted_ranges
            ],
        }
    ]
    digest_input = {
        "response_id": reservation["response_id"],
        "run_id": reservation["run_id"],
        "turn_id_or_null": reservation["turn_id_or_null"],
        "delivery_cohort_id": reservation["delivery_cohort_id"],
        "request_source_refs": reservation["request_source_refs"],
        "canonical_output_parts": canonical_output_parts,
        "completion_extent": completion_extent,
        "termination_cause": termination_cause,
        "first_output_unit_sequence": 0,
        "last_output_unit_sequence": len(accepted_ranges) - 1,
        "output_unit_count": len(accepted_ranges),
        "finalization_idempotency_key": finalization_idempotency_key,
    }
    principal, scope = build_runtime_authority(
        scope_kind="runtime_finalization_authority",
        allowed_operations=("response_finalize",),
        evidence_space_id=str(reservation["evidence_space_id"]),
        issued_at=finalized_at,
    )
    return {
        "schema": BINDING_SCHEMA,
        "assistant_response_binding_id": assistant_response_binding_id,
        "response_capture_reservation_id": reservation[
            "response_capture_reservation_id"
        ],
        **digest_input,
        "first_output_accepted_at": first_output_accepted_at,
        "finalized_at": finalized_at,
        "finalization_basis_ref": "relaylm-managed-visible-output-finalization",
        "runtime_principal_ref": principal.to_dict(),
        "runtime_finalization_authority_scope": scope.to_dict(),
        "canonical_binding_digest": canonical_digest(digest_input),
    }


def build_payload_binding_attestation(
    *,
    payload_binding_attestation_id: str,
    source_event_id: str,
    part_id: str,
    content_digest: str,
    storage_binding_ref: str,
    evidence_space_id: str,
    attested_at: str,
) -> dict[str, object]:
    principal, scope = build_runtime_authority(
        scope_kind="evidence_operator",
        allowed_operations=("storage_binding_attest",),
        evidence_space_id=evidence_space_id,
        issued_at=attested_at,
    )
    return {
        "schema": PAYLOAD_ATTESTATION_SCHEMA,
        "payload_binding_attestation_id": payload_binding_attestation_id,
        "source_event_id": source_event_id,
        "part_id": part_id,
        "content_digest": content_digest,
        "storage_binding_ref": storage_binding_ref,
        "storage_binding_schema": "relaylm.evidence_store_binding.v1",
        "storage_authority_ref": "relaylm.ev1.device_local_store",
        "attested_at": attested_at,
        "attester_principal_ref": principal.to_dict(),
        "attester_authority_scope": scope.to_dict(),
    }


__all__ = [
    "BINDING_SCHEMA",
    "CAPTURE_EVENT_SCHEMA",
    "PAYLOAD_ATTESTATION_SCHEMA",
    "RESERVATION_SCHEMA",
    "ResponseCaptureLog",
    "build_assistant_response_binding",
    "build_payload_binding_attestation",
    "build_response_capture_reservation",
]
