"""Finalize a prepared Contract 1E response into Contract 1A/1B/1D records."""
from __future__ import annotations

from datetime import datetime, timezone

from relaylm.evidence_capture_attempt import CaptureAttemptLog
from relaylm.evidence_common import AuthorityChangeSetRef, PrincipalRef, canonical_digest, dedupe
from relaylm.evidence_governance import build_least_privilege_grant, initialize_admitted_governance
from relaylm.evidence_manifest import (
    build_canonical_source_manifest,
    build_managed_runtime_provenance,
    build_private_direct_audience,
    build_protected_text_part,
    build_source_occurrence_time,
)
from relaylm.evidence_response_binding import (
    ResponseCaptureLog,
    build_assistant_response_binding,
    build_payload_binding_attestation,
)
from relaylm.evidence_response_result import EvidenceResponseCaptureResult
from relaylm.evidence_response_session import (
    PreparedResponseCapture,
    STREAM_KEY,
    derive_id,
)
from relaylm.evidence_source_event import (
    SOURCE_EVENT_SCHEMA,
    ManagedResponseIdentity,
    SourceEvent,
    build_admitted_admission_decision,
    build_valid_validation_bundle,
)
from relaylm.evidence_store import EvidenceStoreTransaction
from relaylm.evidence_validation_artifacts import (
    build_validation_artifact_events,
    build_validation_artifact_identities,
)
from relaylm.evidence_streams import (
    CaptureSequenceLog,
    compute_coverage_checkpoint,
    derive_participant_change_partition_id,
    reserve_and_complete_authority_change_set,
)


def finalize_response_capture(
    prepared: PreparedResponseCapture,
    *,
    completion_extent: str,
    termination_cause: str,
    finalized_at: str | None = None,
) -> EvidenceResponseCaptureResult:
    final_time = finalized_at or datetime.now(timezone.utc).isoformat()
    if prepared.invalid_reason is not None:
        prepared.abandon(prepared.invalid_reason, final_time)
        return EvidenceResponseCaptureResult(
            status="fail_closed",
            blocked_reasons=(prepared.invalid_reason,),
            evidence_space_id=prepared.descriptor.evidence_space_id,
            persisted=prepared.apply_enabled,
        )
    accepted_text = prepared.accepted_text
    if not accepted_text or not prepared.accepted_ranges:
        return terminalize_no_output(prepared, terminal_at=final_time)
    if termination_cause == "normal" and completion_extent != "response_complete":
        return EvidenceResponseCaptureResult(
            status="fail_closed",
            blocked_reasons=("assistant_response_completion_axes_invalid",),
            evidence_space_id=prepared.descriptor.evidence_space_id,
        )
    if prepared.apply_enabled and prepared.store is not None:
        try:
            with prepared.store.transaction(prepared.descriptor.evidence_space_id) as tx:
                return _finalize_locked(
                    tx=tx,
                    prepared=prepared,
                    accepted_text=accepted_text,
                    completion_extent=completion_extent,
                    termination_cause=termination_cause,
                    finalized_at=final_time,
                )
        except RuntimeError as exc:
            return EvidenceResponseCaptureResult(
                status="integrity_conflict",
                blocked_reasons=(str(exc),),
                evidence_space_id=prepared.descriptor.evidence_space_id,
            )
    return _finalize_locked(
        tx=None,
        prepared=prepared,
        accepted_text=accepted_text,
        completion_extent=completion_extent,
        termination_cause=termination_cause,
        finalized_at=final_time,
    )


def _finalize_locked(
    *,
    tx: EvidenceStoreTransaction | None,
    prepared: PreparedResponseCapture,
    accepted_text: str,
    completion_extent: str,
    termination_cause: str,
    finalized_at: str,
) -> EvidenceResponseCaptureResult:
    source_event_id = derive_id(
        "sourceevent", prepared.operation_idempotency_key, "source_event"
    )
    existing_source = (
        tx.read_record(record_kind="source_event", record_id=source_event_id)
        if tx is not None
        else None
    )
    part, part_reasons = build_protected_text_part(
        accepted_text,
        part_origin="assistant_authored",
        part_derivation_class="model_generated",
    )
    if part is None:
        return EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(part_reasons)
        )
    manifest, manifest_reasons = build_canonical_source_manifest(
        occurrence_kind="assistant_response", parts=(part,)
    )
    if manifest is None:
        return EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(manifest_reasons)
        )
    manifest_digest = manifest.digest()
    if existing_source is not None:
        if existing_source.get("canonical_source_manifest_digest") != manifest_digest:
            return EvidenceResponseCaptureResult(
                status="integrity_conflict",
                blocked_reasons=("source_event_integrity_conflict",),
                evidence_space_id=prepared.descriptor.evidence_space_id,
                source_event_id=source_event_id,
            )
        return EvidenceResponseCaptureResult(
            status="admitted",
            evidence_space_id=prepared.descriptor.evidence_space_id,
            source_event_id=source_event_id,
            admission_decision_id=derive_id(
                "admdecision", prepared.operation_idempotency_key, "admission"
            ),
            persisted=True,
        )

    reservation = (
        tx.read_record(
            record_kind="response_capture_reservation",
            record_id=prepared.response_capture_reservation_id,
        )
        if tx is not None
        else _dry_run_reservation(prepared)
    )
    if reservation is None:
        return EvidenceResponseCaptureResult(
            status="fail_closed",
            blocked_reasons=("assistant_response_reservation_missing",),
            evidence_space_id=prepared.descriptor.evidence_space_id,
        )
    response_events = (
        tx.read_log(
            log_kind="response_capture", key=prepared.response_capture_reservation_id
        ) or []
        if tx is not None
        else []
    )
    if any(event.get("operation") in {"finalize", "terminal_no_output"} for event in response_events):
        return EvidenceResponseCaptureResult(
            status="integrity_conflict",
            blocked_reasons=("assistant_response_capture_terminal_conflict",),
            evidence_space_id=prepared.descriptor.evidence_space_id,
        )
    if any(event.get("operation") == "mark_abandoned" for event in response_events):
        return EvidenceResponseCaptureResult(
            status="fail_closed",
            blocked_reasons=("assistant_response_capture_abandoned",),
            evidence_space_id=prepared.descriptor.evidence_space_id,
        )
    response_log = ResponseCaptureLog(reservation, list(response_events))
    binding_id = derive_id(
        "assistantbinding", prepared.operation_idempotency_key, "binding"
    )
    binding = build_assistant_response_binding(
        assistant_response_binding_id=binding_id,
        reservation=reservation,
        accepted_text=accepted_text,
        accepted_ranges=tuple(prepared.accepted_ranges),
        completion_extent=completion_extent,
        termination_cause=termination_cause,
        first_output_accepted_at=prepared.first_output_accepted_at or finalized_at,
        finalized_at=finalized_at,
        finalization_idempotency_key=(
            f"{prepared.operation_idempotency_key}:response-finalize"
        ),
    )
    response_log.finalize(
        binding=binding,
        finalized_at=finalized_at,
        operation_idempotency_key=prepared.operation_idempotency_key,
    )

    sequence_events = (
        tx.read_log(log_kind="capture_sequence", key=STREAM_KEY) or []
        if tx is not None
        else []
    )
    sequence_log = CaptureSequenceLog.from_events(
        prepared.stream_descriptor, list(sequence_events)
    )
    if tx is None:
        sequence_log.reserve(
            capture_attempt_id=prepared.capture_attempt_id,
            recorded_at=prepared.reserved_at,
            operation_idempotency_key=prepared.operation_idempotency_key,
        )
    attempt_events = (
        tx.read_log(log_kind="capture_attempt", key=prepared.capture_attempt_id) or []
        if tx is not None
        else []
    )
    attempt = _rebuild_attempt(prepared, attempt_events)
    if not attempt_events:
        ok, reasons = attempt.reserve(
            capture_stream_kind="managed_assistant_output",
            stream_direction="outbound",
            recorded_at=prepared.reserved_at,
            operation_idempotency_key=prepared.operation_idempotency_key,
            response_capture_reservation_ref_or_null=(
                prepared.response_capture_reservation_id
            ),
        )
        if not ok:
            return EvidenceResponseCaptureResult(
                status="fail_closed", blocked_reasons=dedupe(reasons)
            )
    admission_decision_id = derive_id(
        "admdecision", prepared.operation_idempotency_key, "admission"
    )
    governance_event_id = derive_id(
        "governanceevent", prepared.operation_idempotency_key, "governance"
    )
    validation_identities = build_validation_artifact_identities(
        operation_idempotency_key=prepared.operation_idempotency_key,
        gate_kinds=("canonicalization", "integrity", "assistant_finalization"),
    )
    validation_bundle = build_valid_validation_bundle(
        validation_bundle_id=derive_id(
            "valbundle", prepared.operation_idempotency_key, "validation_bundle"
        ),
        validation_bundle_revision_id=derive_id(
            "valbundlerev",
            prepared.operation_idempotency_key,
            "validation_bundle_revision",
        ),
        capture_attempt_id=prepared.capture_attempt_id,
        source_event_id=source_event_id,
        evidence_space_id=prepared.descriptor.evidence_space_id,
        recorded_at=finalized_at,
        gate_kinds=tuple(item.gate_kind for item in validation_identities),
        gate_artifact_refs=tuple(
            (item.gate_kind, item.derived_artifact_id)
            for item in validation_identities
        ),
    )
    ok, reasons = attempt.finalize_candidate(
        preallocated_source_event_id=source_event_id,
        canonical_source_manifest=manifest.to_dict(),
        canonical_source_manifest_digest=manifest_digest,
        validation_bundle_id=validation_bundle.validation_bundle_id,
        validation_bundle_revision=validation_bundle.bundle_revision,
        recorded_at=finalized_at,
        operation_idempotency_key=prepared.operation_idempotency_key,
    )
    if not ok:
        return EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(reasons)
        )

    change_partition_id = derive_participant_change_partition_id(
        evidence_space_id=prepared.descriptor.evidence_space_id,
        participant_ref=prepared.descriptor.controller_principal_ref,
    )
    projection_log = (
        tx.read_log(log_kind="change_projection", key=change_partition_id) or []
        if tx is not None
        else []
    )
    change_coverage_log = (
        tx.read_log(log_kind="change_coverage_checkpoint", key=change_partition_id) or []
        if tx is not None
        else []
    )
    authoritative_mutation_refs = [
        {
            "record_kind": "source_event",
            "record_id": source_event_id,
            "record_revision_or_null": None,
        },
        {
            "record_kind": "admission_decision",
            "record_id": admission_decision_id,
            "record_revision_or_null": None,
        },
        {
            "record_kind": "governance_event",
            "record_id": governance_event_id,
            "record_revision_or_null": 1,
        },
    ]
    authoritative_mutation_refs.extend(
        {
            "record_kind": "source_derived_artifact_event",
            "record_id": item.artifact_event_id,
            "record_revision_or_null": 1,
        }
        for item in validation_identities
    )
    change_result, change_reasons = reserve_and_complete_authority_change_set(
        change_set_id=derive_id(
            "changeset", prepared.operation_idempotency_key, "change_set"
        ),
        change_kind="source_admitted",
        evidence_space_id=prepared.descriptor.evidence_space_id,
        participant_ref=prepared.descriptor.controller_principal_ref,
        authoritative_mutation_refs=tuple(authoritative_mutation_refs),
        recorded_at=finalized_at,
        partition_sequence=len(projection_log),
        change_coverage_revision=len(change_coverage_log) + 1,
        expected_previous_change_coverage_revision_or_null=(
            len(change_coverage_log) if change_coverage_log else None
        ),
        partition_descriptor_issued_at=prepared.descriptor.created_at,
        existing_projection_events=tuple(projection_log),
    )
    if change_result is None:
        return EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(change_reasons)
        )
    change_ref = AuthorityChangeSetRef(
        change_set_id=change_result.change_set_id,
        change_projection_plan_digest=change_result.change_projection_plan_digest,
    )
    validation_artifacts = build_validation_artifact_events(
        identities=validation_identities,
        evidence_space_id=prepared.descriptor.evidence_space_id,
        source_event_id=source_event_id,
        canonical_manifest_digest=manifest_digest,
        assistant_response_binding_id_or_null=binding_id,
        assistant_response_binding_digest_or_null=str(
            binding["canonical_binding_digest"]
        ),
        authority_change_set_ref=change_ref,
        recorded_at=finalized_at,
        operation_idempotency_key=prepared.operation_idempotency_key,
    )

    occurrence_time, occurrence_reasons = build_source_occurrence_time(
        parsed_instant=finalized_at
    )
    audience, audience_reasons = build_private_direct_audience(
        participant_refs=(prepared.descriptor.controller_principal_ref,)
    )
    provenance, provenance_reasons = build_managed_runtime_provenance(
        source_material_class="assistant_generation"
    )
    if occurrence_time is None or audience is None or provenance is None:
        return EvidenceResponseCaptureResult(
            status="fail_closed",
            blocked_reasons=dedupe(
                (*occurrence_reasons, *audience_reasons, *provenance_reasons)
            ),
        )
    assistant_ref = PrincipalRef(
        principal_kind="assistant",
        principal_id="assistant_" + canonical_digest({
            "evidence_space_id": prepared.descriptor.evidence_space_id,
            "managed_route": True,
        }),
        authority_domain_ref="relaylm-local",
    )
    payload_binding_id = derive_id(
        "payloadbinding", prepared.operation_idempotency_key, "payload_binding"
    )
    storage_binding_ref = derive_id(
        "storagebinding", prepared.operation_idempotency_key, "payload_storage"
    )
    attestation = build_payload_binding_attestation(
        payload_binding_attestation_id=payload_binding_id,
        source_event_id=source_event_id,
        part_id=part.part_id,
        content_digest=str(part.content_digest_or_null),
        storage_binding_ref=storage_binding_ref,
        evidence_space_id=prepared.descriptor.evidence_space_id,
        attested_at=finalized_at,
    )
    source_event = SourceEvent(
        schema=SOURCE_EVENT_SCHEMA,
        source_event_id=source_event_id,
        evidence_space_id=prepared.descriptor.evidence_space_id,
        evidence_space_descriptor_revision=prepared.descriptor.descriptor_revision,
        capture_attempt_id=prepared.capture_attempt_id,
        capture_stream_epoch_id=prepared.stream_descriptor.capture_stream_epoch_id,
        capture_sequence=prepared.capture_sequence,
        route_capture_grant_snapshot_ref=prepared.route_snapshot.route_binding_id,
        received_at=finalized_at,
        observed_at=finalized_at,
        capture_channel="managed_assistant_text",
        source_role="assistant_response",
        origin_kind="assistant",
        producer_principal_ref=assistant_ref,
        authenticated_account_ref_or_null=None,
        represented_speaker_ref_or_null=assistant_ref,
        speaker_identity_status="not_applicable",
        source_occurrence_time=occurrence_time,
        configured_occurrence_audience=audience,
        scene_occurrence_ref_or_null=None,
        conversation_ref_or_null=prepared.session_id,
        canonical_source_manifest=manifest,
        canonical_source_manifest_digest=manifest_digest,
        protected_payload_binding_attestation_ids=(payload_binding_id,),
        source_replay_identity=ManagedResponseIdentity(
            response_id=prepared.response_id,
            delivery_cohort_id=prepared.delivery_cohort_id,
            response_finalization_idempotency_key=str(
                binding["finalization_idempotency_key"]
            ),
            canonical_response_binding_digest=str(binding["canonical_binding_digest"]),
        ),
        assistant_response_binding_ref_or_null=binding_id,
        provenance_snapshot=provenance,
        authority_change_set_ref=change_ref,
    )
    admission = build_admitted_admission_decision(
        admission_decision_id=admission_decision_id,
        capture_attempt_id=prepared.capture_attempt_id,
        evidence_space_id=prepared.descriptor.evidence_space_id,
        operation_idempotency_key=prepared.operation_idempotency_key,
        route_capture_grant_snapshot_ref=prepared.route_snapshot.route_binding_id,
        decided_at=finalized_at,
        manifest_digest=manifest_digest,
        validation_bundle=validation_bundle,
        source_event_id=source_event_id,
        initial_governance_event_id=governance_event_id,
        authority_change_set_ref=change_ref,
        reason_code="admitted_managed_assistant_response",
    )
    ok, reasons = attempt.bind_admission(
        admission_decision_id=admission_decision_id,
        recorded_at=finalized_at,
        operation_idempotency_key=prepared.operation_idempotency_key,
    )
    if not ok:
        return EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(reasons)
        )

    grants = []
    for purpose in (
        "relayctx_evidence_read",
        "shared_assessment_read",
        "relayref_observation_read",
    ):
        grant, grant_reasons = build_least_privilege_grant(
            grant_id=derive_id(
                "accessgrant", prepared.operation_idempotency_key, f"grant:{purpose}"
            ),
            source_event_id=source_event_id,
            evidence_space_id=prepared.descriptor.evidence_space_id,
            purpose=purpose,
            admission_decision_id=admission_decision_id,
            validation_bundle_revision=validation_bundle.bundle_revision,
            issued_at=finalized_at,
        )
        if grant is None:
            return EvidenceResponseCaptureResult(
                status="fail_closed", blocked_reasons=dedupe(grant_reasons)
            )
        grants.append(grant)
    final_dt = datetime.fromisoformat(finalized_at.replace("Z", "+00:00"))
    access_until = final_dt.timestamp() + 30 * 24 * 60 * 60
    purge_due = access_until + 7 * 24 * 60 * 60
    _state, governance_event = initialize_admitted_governance(
        governance_event_id=governance_event_id,
        source_event_id=source_event_id,
        evidence_space_id=prepared.descriptor.evidence_space_id,
        part_ids=(part.part_id,),
        grants=tuple(grants),
        access_until=datetime.fromtimestamp(access_until, tz=timezone.utc).isoformat(),
        purge_due_at=datetime.fromtimestamp(purge_due, tz=timezone.utc).isoformat(),
        authority_change_set_ref=change_ref,
        recorded_at=finalized_at,
        operation_idempotency_key=prepared.operation_idempotency_key,
    )
    ok, reasons = sequence_log.terminalize_admission(
        sequence=prepared.capture_sequence,
        capture_attempt_id=prepared.capture_attempt_id,
        admission_decision_id=admission_decision_id,
        terminal_outcome="admitted",
        recorded_at=finalized_at,
        operation_idempotency_key=prepared.operation_idempotency_key,
    )
    if not ok:
        return EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(reasons)
        )
    coverage_log = (
        tx.read_log(log_kind="coverage_checkpoint", key=STREAM_KEY) or []
        if tx is not None
        else []
    )
    coverage = compute_coverage_checkpoint(
        prepared.stream_descriptor,
        sequence_log.events,
        updated_at=finalized_at,
        operation_idempotency_key=prepared.operation_idempotency_key,
        previous_checkpoint=coverage_log[-1] if coverage_log else None,
    )

    if tx is not None:
        records = [
            ("assistant_response_binding", binding_id, binding),
            ("payload_binding_attestation", payload_binding_id, attestation),
            ("source_event", source_event_id, source_event.to_dict()),
            ("admission_decision", admission_decision_id, admission.to_dict()),
            ("validation_bundle", validation_bundle.validation_bundle_id, validation_bundle.to_dict()),
            *(
                (
                    "source_derived_artifact_event",
                    str(event["artifact_event_id"]),
                    event,
                )
                for event in validation_artifacts
            ),
            ("governance_event", governance_event_id, governance_event.to_dict()),
            ("change_partition_descriptor", str(change_result.partition_descriptor["change_partition_id"]), change_result.partition_descriptor),
            ("change_projection_event", str(change_result.projection_event["projection_event_id"]), change_result.projection_event),
            ("source_projection_registry_event", str(change_result.registry_event["registry_event_id"]), change_result.registry_event),
        ]
        records.extend(("access_grant", grant.grant_id, grant.to_dict()) for grant in grants)
        commit = tx.commit(
            transaction_id=derive_id(
                "evidencetx", prepared.operation_idempotency_key, "response-finalize"
            ),
            records=records,
            logs=(
                ("response_capture", prepared.response_capture_reservation_id, response_log.events),
                ("capture_attempt", prepared.capture_attempt_id, attempt.events),
                ("capture_sequence", STREAM_KEY, sequence_log.events),
                ("coverage_checkpoint", STREAM_KEY, [*coverage_log, coverage.to_dict()]),
                ("change_set", change_result.change_set_id, [change_result.plan_event, change_result.mark_complete_event]),
                ("change_projection", change_partition_id, [*projection_log, change_result.projection_event]),
                ("change_coverage_checkpoint", change_partition_id, [*change_coverage_log, change_result.change_coverage_checkpoint]),
            ),
            payloads=((storage_binding_ref, {
                "media_type": "text/plain; charset=utf-8",
                "content_digest": part.content_digest_or_null,
                "text": accepted_text,
            }),),
        )
        if commit.status == "collision":
            return EvidenceResponseCaptureResult(
                status="integrity_conflict",
                blocked_reasons=commit.reasons,
                evidence_space_id=prepared.descriptor.evidence_space_id,
                source_event_id=source_event_id,
            )
        if commit.status not in {"created", "duplicate_existing"}:
            return EvidenceResponseCaptureResult(
                status="fail_closed",
                blocked_reasons=commit.reasons,
                evidence_space_id=prepared.descriptor.evidence_space_id,
            )
    return EvidenceResponseCaptureResult(
        status="admitted" if prepared.apply_enabled else "dry_run_ready",
        evidence_space_id=prepared.descriptor.evidence_space_id,
        source_event_id=source_event_id,
        admission_decision_id=admission_decision_id,
        persisted=prepared.apply_enabled,
    )


def terminalize_no_output(
    prepared: PreparedResponseCapture, *, terminal_at: str
) -> EvidenceResponseCaptureResult:
    if prepared.accepted_ranges:
        return EvidenceResponseCaptureResult(
            status="fail_closed",
            blocked_reasons=("assistant_response_no_output_after_observation",),
            evidence_space_id=prepared.descriptor.evidence_space_id,
        )
    if prepared.apply_enabled and prepared.store is not None:
        try:
            with prepared.store.transaction(prepared.descriptor.evidence_space_id) as tx:
                reservation = tx.read_record(
                    record_kind="response_capture_reservation",
                    record_id=prepared.response_capture_reservation_id,
                )
                if reservation is None:
                    return EvidenceResponseCaptureResult(
                        status="fail_closed",
                        blocked_reasons=("assistant_response_reservation_missing",),
                    )
                response_events = tx.read_log(
                    log_kind="response_capture", key=prepared.response_capture_reservation_id
                ) or []
                if any(event.get("operation") in {"finalize", "terminal_no_output"} for event in response_events):
                    return EvidenceResponseCaptureResult(
                        status="terminal_no_output",
                        evidence_space_id=prepared.descriptor.evidence_space_id,
                        persisted=True,
                    )
                response_log = ResponseCaptureLog(reservation, list(response_events))
                response_log.terminal_no_output(
                    reason="safe_output_empty",
                    terminal_at=terminal_at,
                    operation_idempotency_key=prepared.operation_idempotency_key,
                )
                attempt_events = tx.read_log(
                    log_kind="capture_attempt", key=prepared.capture_attempt_id
                ) or []
                attempt = _rebuild_attempt(prepared, attempt_events)
                ok, reasons = attempt.terminal_no_source(
                    terminal_reason="assistant_output_not_emitted",
                    recorded_at=terminal_at,
                    operation_idempotency_key=prepared.operation_idempotency_key,
                )
                if not ok:
                    return EvidenceResponseCaptureResult(
                        status="fail_closed", blocked_reasons=dedupe(reasons)
                    )
                terminal_event_id = str(attempt.events[-1]["capture_attempt_event_id"])
                sequence_events = tx.read_log(
                    log_kind="capture_sequence", key=STREAM_KEY
                ) or []
                sequence_log = CaptureSequenceLog.from_events(
                    prepared.stream_descriptor, list(sequence_events)
                )
                ok, reasons = sequence_log.terminalize_no_source(
                    sequence=prepared.capture_sequence,
                    capture_attempt_id=prepared.capture_attempt_id,
                    terminal_reason="assistant_output_not_emitted",
                    recorded_at=terminal_at,
                    operation_idempotency_key=prepared.operation_idempotency_key,
                    capture_attempt_terminal_event_id=terminal_event_id,
                )
                if not ok:
                    return EvidenceResponseCaptureResult(
                        status="fail_closed", blocked_reasons=dedupe(reasons)
                    )
                checkpoints = tx.read_log(
                    log_kind="coverage_checkpoint", key=STREAM_KEY
                ) or []
                coverage = compute_coverage_checkpoint(
                    prepared.stream_descriptor,
                    sequence_log.events,
                    updated_at=terminal_at,
                    operation_idempotency_key=prepared.operation_idempotency_key,
                    previous_checkpoint=checkpoints[-1] if checkpoints else None,
                )
                commit = tx.commit(
                    transaction_id=derive_id(
                        "evidencetx", prepared.operation_idempotency_key, "response-no-output"
                    ),
                    records=(),
                    logs=(
                        ("response_capture", prepared.response_capture_reservation_id, response_log.events),
                        ("capture_attempt", prepared.capture_attempt_id, attempt.events),
                        ("capture_sequence", STREAM_KEY, sequence_log.events),
                        ("coverage_checkpoint", STREAM_KEY, [*checkpoints, coverage.to_dict()]),
                    ),
                )
                if commit.status not in {"created", "duplicate_existing"}:
                    return EvidenceResponseCaptureResult(
                        status="fail_closed", blocked_reasons=commit.reasons
                    )
        except RuntimeError as exc:
            return EvidenceResponseCaptureResult(
                status="integrity_conflict", blocked_reasons=(str(exc),)
            )
    return EvidenceResponseCaptureResult(
        status="terminal_no_output",
        evidence_space_id=prepared.descriptor.evidence_space_id,
        persisted=prepared.apply_enabled,
    )


def _rebuild_attempt(
    prepared: PreparedResponseCapture, events: list[dict]
) -> CaptureAttemptLog:
    attempt = CaptureAttemptLog(
        evidence_space_id=prepared.descriptor.evidence_space_id,
        capture_stream_epoch_id=prepared.stream_descriptor.capture_stream_epoch_id,
        capture_sequence=prepared.capture_sequence,
        route_capture_grant_snapshot_ref=prepared.route_snapshot.route_binding_id,
        capture_channel="managed_assistant_text",
        source_role="assistant_response",
        capture_attempt_id=prepared.capture_attempt_id,
        events=list(events),
    )
    attempt._revision = len(events)  # type: ignore[attr-defined]
    attempt._state = str(events[-1]["operation"]) if events else "unstarted"  # type: ignore[attr-defined]
    return attempt


def _dry_run_reservation(prepared: PreparedResponseCapture) -> dict[str, object]:
    from relaylm.evidence_manifest import build_private_direct_audience
    from relaylm.evidence_response_binding import build_response_capture_reservation

    audience, _ = build_private_direct_audience(
        participant_refs=(prepared.descriptor.controller_principal_ref,)
    )
    assert audience is not None
    return build_response_capture_reservation(
        response_capture_reservation_id=prepared.response_capture_reservation_id,
        response_id=prepared.response_id,
        run_id=prepared.operation_idempotency_key.split(":", 1)[0],
        turn_id_or_null=prepared.operation_idempotency_key.split(":", 1)[0],
        evidence_space_id=prepared.descriptor.evidence_space_id,
        route_capture_grant_snapshot_ref=prepared.route_snapshot.route_binding_id,
        capture_stream_id=prepared.stream_descriptor.capture_stream_id,
        capture_stream_epoch_id=prepared.stream_descriptor.capture_stream_epoch_id,
        capture_sequence=prepared.capture_sequence,
        delivery_cohort_id=prepared.delivery_cohort_id,
        audience=audience,
        request_source_event_ids=prepared.request_source_event_ids,
        reserved_at=prepared.reserved_at,
        operation_idempotency_key=prepared.operation_idempotency_key,
    )


__all__ = ["finalize_response_capture", "terminalize_no_output"]
