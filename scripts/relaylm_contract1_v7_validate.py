#!/usr/bin/env python3
"""Validate RelayLM Contract 1 v7 schemas, fixtures, and cross-record invariants."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


def canonical_bytes(value: Any) -> bytes:
    # Fixtures use the RFC-8785-compatible JSON subset: no floats, no duplicate
    # keys, UTF-8, sorted object keys, and compact separators.
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest_obj(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ContractValidator:
    def __init__(self, bundle_path: Path) -> None:
        self.bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        self.defs: dict[str, Any] = {}
        schema_dir = bundle_path.parent
        for part_path in sorted(schema_dir.glob("relaylm-contract1-v7.part-*.schema.json")):
            part = json.loads(part_path.read_text(encoding="utf-8"))
            overlap = set(self.defs) & set(part.get("$defs", {}))
            if overlap:
                raise ValueError(f"duplicate schema definitions across parts: {sorted(overlap)}")
            self.defs.update(part.get("$defs", {}))
        referenced = set(self.bundle.get("$defs", {}))
        if referenced != set(self.defs):
            raise ValueError(
                "bundle/part definition mismatch: "
                f"missing={sorted(referenced - set(self.defs))}, "
                f"extra={sorted(set(self.defs) - referenced)}"
            )
        self.schema_map: dict[str, str] = {}
        for name, schema in self.defs.items():
            const = schema.get("properties", {}).get("schema", {}).get("const")
            if const:
                self.schema_map[const] = name
        self.format_checker = FormatChecker()

    def schema_validator(self, name: str) -> Draft202012Validator:
        schema = {"$ref": f"#/$defs/{name}", "$defs": self.defs}
        return Draft202012Validator(schema, format_checker=self.format_checker)

    def validate_fixture(self, fixture: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        records = fixture.get("records", [])
        if not isinstance(records, list):
            return ["fixture.records must be an array"]

        # Schema validation.
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                errors.append(f"record[{index}] is not an object")
                continue
            schema_id = record.get("schema")
            if not schema_id:
                errors.append(f"record[{index}] has no schema discriminator")
                continue
            name = self.schema_map.get(schema_id)
            if name is None:
                errors.append(f"record[{index}] has unknown schema {schema_id!r}")
                continue
            for error in self.schema_validator(name).iter_errors(record):
                path = "/".join(str(p) for p in error.absolute_path)
                errors.append(
                    f"schema {schema_id} record[{index}]"
                    f"{'/' + path if path else ''}: {error.message}"
                )

        errors.extend(self._custom_checks(fixture))
        return errors

    def _custom_checks(self, fixture: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        records: list[dict[str, Any]] = [
            r for r in fixture.get("records", []) if isinstance(r, dict)
        ]

        by_schema: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            by_schema[record.get("schema", "")].append(record)

        manifests = {
            digest_obj(r): r
            for r in by_schema["relaylm.canonical_source_manifest.v1"]
        }
        bindings = {
            r["assistant_response_binding_id"]: r
            for r in by_schema["relaylm.assistant_response_binding.v1"]
            if "assistant_response_binding_id" in r
        }
        reservations = {
            r["response_capture_reservation_id"]: r
            for r in by_schema[
                "relaylm.assistant_response_capture_reservation.v1"
            ]
            if "response_capture_reservation_id" in r
        }
        payload_bindings = {
            r["payload_binding_attestation_id"]: r
            for r in by_schema["relaylm.protected_payload_binding_attestation.v1"]
            if "payload_binding_attestation_id" in r
        }
        source_events = {
            r["source_event_id"]: r
            for r in by_schema["relaylm.source_event.v1"]
            if "source_event_id" in r
        }
        admissions = {
            r["admission_decision_id"]: r
            for r in by_schema["relaylm.evidence_admission_decision.v1"]
            if "admission_decision_id" in r
        }

        # Canonical manifest and SourceEvent checks.
        response_identity_seen: dict[tuple[str, str], str] = {}
        for source in by_schema["relaylm.source_event.v1"]:
            actual = digest_obj(source.get("canonical_source_manifest"))
            if actual != source.get("canonical_source_manifest_digest"):
                errors.append(
                    f"SourceEvent {source.get('source_event_id')}: "
                    "canonical source manifest digest mismatch"
                )
            parts = source.get("canonical_source_manifest", {}).get("parts", [])
            part_ids = [p.get("part_id") for p in parts]
            if len(part_ids) != len(set(part_ids)):
                errors.append(
                    f"SourceEvent {source.get('source_event_id')}: duplicate part IDs"
                )

            expected_bindings: dict[str, str] = {}
            for part in parts:
                if part.get("initial_disposition") in {"protected", "quarantine_only"}:
                    digest = part.get("content_digest_or_null")
                    expected_bindings[part["part_id"]] = digest
            actual_binding_ids = source.get("protected_payload_binding_attestation_ids", [])
            actual_parts: dict[str, str] = {}
            for binding_id in actual_binding_ids:
                binding = payload_bindings.get(binding_id)
                if binding is None:
                    errors.append(
                        f"SourceEvent {source.get('source_event_id')}: "
                        f"missing payload binding attestation {binding_id}"
                    )
                    continue
                if binding.get("source_event_id") != source.get("source_event_id"):
                    errors.append(
                        f"payload binding {binding_id}: source_event_id mismatch"
                    )
                actual_parts[binding.get("part_id")] = binding.get("content_digest")
            if actual_parts != expected_bindings:
                errors.append(
                    f"SourceEvent {source.get('source_event_id')}: "
                    "payload binding attestation coverage/digest mismatch"
                )

            if source.get("source_role") == "assistant_response":
                binding_id = source.get("assistant_response_binding_ref_or_null")
                binding = bindings.get(binding_id)
                if binding is None:
                    errors.append(
                        f"assistant SourceEvent {source.get('source_event_id')}: "
                        "missing assistant response binding"
                    )
                identity = source.get("source_replay_identity", {})
                if identity.get("kind") != "managed_response_identity":
                    errors.append(
                        f"assistant SourceEvent {source.get('source_event_id')}: "
                        "wrong replay identity kind"
                    )
                else:
                    key = (
                        identity.get("response_id"),
                        identity.get("delivery_cohort_id"),
                    )
                    previous = response_identity_seen.get(key)
                    if previous and previous != source.get("source_event_id"):
                        errors.append(
                            f"managed response {key}: multiple SourceEvents "
                            f"{previous} and {source.get('source_event_id')}"
                        )
                    response_identity_seen[key] = source.get("source_event_id")
                    if binding:
                        if (
                            identity.get("canonical_response_binding_digest")
                            != binding.get("canonical_binding_digest")
                        ):
                            errors.append(
                                f"assistant SourceEvent {source.get('source_event_id')}: "
                                "response binding digest mismatch"
                            )
                        if source.get("canonical_source_manifest", {}).get(
                            "occurrence_kind"
                        ) != "assistant_response":
                            errors.append(
                                f"assistant SourceEvent {source.get('source_event_id')}: "
                                "manifest occurrence_kind mismatch"
                            )

        # Binding digest, range, and frozen-correlation checks.
        for binding in by_schema["relaylm.assistant_response_binding.v1"]:
            digest_input = {
                key: binding[key]
                for key in (
                    "response_id",
                    "run_id",
                    "turn_id_or_null",
                    "delivery_cohort_id",
                    "request_source_refs",
                    "canonical_output_parts",
                    "completion_extent",
                    "termination_cause",
                    "first_output_unit_sequence",
                    "last_output_unit_sequence",
                    "output_unit_count",
                    "finalization_idempotency_key",
                )
                if key in binding
            }
            if digest_obj(digest_input) != binding.get("canonical_binding_digest"):
                errors.append(
                    f"AssistantResponseBinding "
                    f"{binding.get('assistant_response_binding_id')}: "
                    "canonical binding digest mismatch"
                )
            if (
                binding.get("last_output_unit_sequence", -1)
                < binding.get("first_output_unit_sequence", 0)
            ):
                errors.append(
                    f"AssistantResponseBinding "
                    f"{binding.get('assistant_response_binding_id')}: "
                    "last output sequence precedes first"
                )
            expected_count = (
                binding.get("last_output_unit_sequence", 0)
                - binding.get("first_output_unit_sequence", 0)
                + 1
            )
            if binding.get("output_unit_count") != expected_count:
                errors.append(
                    f"AssistantResponseBinding "
                    f"{binding.get('assistant_response_binding_id')}: "
                    "output unit count is inconsistent"
                )
            for part in binding.get("canonical_output_parts", []):
                previous_end: int | None = None
                previous_unit: str | None = None
                for item in part.get("accepted_ranges", []):
                    start = item.get("start_inclusive")
                    end = item.get("end_exclusive")
                    unit = item.get("unit")
                    if not isinstance(start, int) or not isinstance(end, int):
                        continue
                    if end <= start:
                        errors.append(
                            f"AssistantResponseBinding "
                            f"{binding.get('assistant_response_binding_id')}: "
                            "accepted range is empty/reversed"
                        )
                    if previous_end is not None:
                        if unit != previous_unit:
                            errors.append(
                                f"AssistantResponseBinding "
                                f"{binding.get('assistant_response_binding_id')}: "
                                "mixed range units within one part"
                            )
                        elif start < previous_end:
                            errors.append(
                                f"AssistantResponseBinding "
                                f"{binding.get('assistant_response_binding_id')}: "
                                "accepted ranges overlap or are unsorted"
                            )
                    previous_end = end
                    previous_unit = unit

        # Reservation audience subset.
        for reservation in by_schema[
            "relaylm.assistant_response_capture_reservation.v1"
        ]:
            configured = reservation.get("configured_occurrence_audience", {})
            cohort = reservation.get("delivery_cohort_audience", {})
            configured_ids = {
                p.get("principal_id")
                for p in configured.get("participant_refs", [])
            }
            cohort_ids = {
                p.get("principal_id")
                for p in cohort.get("participant_refs", [])
            }
            if not cohort_ids.issubset(configured_ids):
                errors.append(
                    f"ResponseCaptureReservation "
                    f"{reservation.get('response_capture_reservation_id')}: "
                    "delivery cohort is not a configured-audience subset"
                )
            if configured.get("audience_class") != cohort.get("audience_class"):
                # A narrower private subset keeps the same class in v1.
                errors.append(
                    f"ResponseCaptureReservation "
                    f"{reservation.get('response_capture_reservation_id')}: "
                    "audience class mismatch"
                )

        # Delivery observations cannot target recipients outside the cohort.
        for observation in by_schema[
            "relaylm.assistant_delivery_observation_event.v1"
        ]:
            binding = bindings.get(
                observation.get("assistant_response_binding_id")
            )
            if binding is None:
                errors.append(
                    f"DeliveryObservation "
                    f"{observation.get('delivery_observation_event_id')}: "
                    "assistant response binding is missing"
                )
                continue
            if observation.get("delivery_cohort_id") != binding.get(
                "delivery_cohort_id"
            ):
                errors.append(
                    f"DeliveryObservation "
                    f"{observation.get('delivery_observation_event_id')}: "
                    "delivery cohort ID differs from binding"
                )
            reservation = reservations.get(
                binding.get("response_capture_reservation_id")
            )
            if reservation is None:
                errors.append(
                    f"DeliveryObservation "
                    f"{observation.get('delivery_observation_event_id')}: "
                    "response capture reservation is missing"
                )
                continue

            selector = observation.get("recipient_selector", {})
            if selector.get("kind") == "exact_participants":
                cohort_ids = {
                    principal.get("principal_id")
                    for principal in reservation.get(
                        "delivery_cohort_audience", {}
                    ).get("participant_refs", [])
                }
                selected_ids = {
                    principal.get("principal_id")
                    for principal in selector.get("participant_refs", [])
                }
                if not selected_ids.issubset(cohort_ids):
                    errors.append(
                        f"DeliveryObservation "
                        f"{observation.get('delivery_observation_event_id')}: "
                        "recipient selector is outside the delivery cohort"
                    )

        # Admission and reason checks.
        for decision in by_schema["relaylm.evidence_admission_decision.v1"]:
            if decision.get("primary_reason_code") not in decision.get(
                "reason_codes", []
            ):
                errors.append(
                    f"AdmissionDecision {decision.get('admission_decision_id')}: "
                    "primary reason not in reason_codes"
                )
            outcome = decision.get("outcome")
            if outcome in {"admitted", "quarantined"}:
                source_id = decision.get("source_event_id_or_null")
                if source_id not in source_events:
                    errors.append(
                        f"AdmissionDecision {decision.get('admission_decision_id')}: "
                        "referenced SourceEvent missing"
                    )
            elif decision.get("source_event_id_or_null") is not None:
                errors.append(
                    f"AdmissionDecision {decision.get('admission_decision_id')}: "
                    "non-source outcome carries source_event_id"
                )

        # Access grant and retention checks.
        for grant in by_schema["relaylm.evidence_access_grant.v1"]:
            selectors = grant.get("metadata_projection_selectors", [])
            if selectors != sorted(set(selectors)):
                errors.append(
                    f"AccessGrant {grant.get('grant_id')}: "
                    "metadata projection selectors must be sorted unique"
                )
            if "full_authorized_audit" in selectors and selectors != [
                "full_authorized_audit"
            ]:
                errors.append(
                    f"AccessGrant {grant.get('grant_id')}: "
                    "full_authorized_audit must be the only selector"
                )
            if (
                "full_authorized_audit" in selectors
                and grant.get("purpose")
                not in {"authorized_evidence_review", "recovery_read"}
            ):
                errors.append(
                    f"AccessGrant {grant.get('grant_id')}: "
                    "full audit used for an unauthorized purpose"
                )

        for state in by_schema["relaylm.evidence_governance_state.v1"]:
            retention = state.get("retention_state", {})
            access = retention.get("access_until_or_null")
            purge = retention.get("purge_due_at_or_null")
            if access and purge and parse_time(access) > parse_time(purge):
                errors.append("EvidenceGovernanceState: access deadline after purge")
            if state.get("record_access_state") == "purged":
                if any(
                    value not in {"purged", "non_content"}
                    for value in state.get("part_access_states", {}).values()
                ):
                    errors.append(
                        "EvidenceGovernanceState: purged record retains usable part state"
                    )

        # Access authorization watermark and time checks.
        for auth in by_schema[
            "relaylm.evidence_access_authorization_projection.v1"
        ]:
            keys = [
                (w.get("change_partition_id"), w.get("partition_epoch_id"))
                for w in auth.get("change_partition_watermarks", [])
            ]
            if len(keys) != len(set(keys)):
                errors.append(
                    f"AccessAuthorization {auth.get('access_authorization_id')}: "
                    "duplicate partition watermark key"
                )
            if parse_time(auth["not_after"]) <= parse_time(auth["issued_at"]):
                errors.append(
                    f"AccessAuthorization {auth.get('access_authorization_id')}: "
                    "not_after is not later than issued_at"
                )

        # Metadata correction allowlist.
        allowed_metadata_fields = {
            "represented_speaker_ref_or_null",
            "speaker_identity_status",
            "configured_occurrence_audience",
            "source_occurrence_time.parsed_instant_or_null",
            "source_occurrence_time.timezone_or_offset_or_null",
            "source_occurrence_time.trust",
            "provenance_snapshot.provenance_assurance",
            "provenance_snapshot.independence_status",
            "provenance_snapshot.independence_group_id_or_null",
            "provenance_snapshot.independence_basis_or_null",
        }
        for revision in by_schema["relaylm.source_metadata_revision.v1"]:
            corrected = set(revision.get("corrected_fields", {}))
            forbidden = corrected - allowed_metadata_fields
            if forbidden:
                errors.append(
                    f"SourceMetadataRevision "
                    f"{revision.get('metadata_revision_id')}: "
                    f"forbidden corrected fields {sorted(forbidden)}"
                )

        # Derived artifact lifecycle.
        artifact_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in by_schema["relaylm.source_derived_artifact_event.v1"]:
            artifact_groups[event.get("derived_artifact_id")].append(event)
        for artifact_id, chain in artifact_groups.items():
            chain.sort(key=lambda item: item.get("artifact_revision", 0))
            state = "absent"
            for event in chain:
                operation = event.get("operation")
                if operation == "create":
                    if state != "absent":
                        errors.append(
                            f"DerivedArtifact {artifact_id}: duplicate create"
                        )
                    state = "active"
                elif operation == "invalidate":
                    if state != "active":
                        errors.append(
                            f"DerivedArtifact {artifact_id}: "
                            "invalidate requires active state"
                        )
                    state = "invalidated"
                elif operation == "supersede":
                    if state != "active":
                        errors.append(
                            f"DerivedArtifact {artifact_id}: "
                            "supersede requires active state"
                        )
                    state = "superseded"
                elif operation == "revalidate":
                    if state != "invalidated":
                        errors.append(
                            f"DerivedArtifact {artifact_id}: "
                            "revalidate allowed only after invalidate"
                        )
                    state = "active"

        # Integrity failure must not leave an active content grant.
        for state in by_schema["relaylm.evidence_governance_state.v1"]:
            if state.get("integrity_state") == "failed":
                active = [
                    item.get("grant_id")
                    for item in state.get("grant_records", [])
                    if item.get("governance_lifecycle_state") == "granted"
                ]
                if active:
                    errors.append(
                        "EvidenceGovernanceState: integrity failed while "
                        f"grants remain granted {active}"
                    )

        # Quarantine existence must not leak as normal candidate availability.
        for projection in by_schema[
            "relaylm.evidence_authority_change_projection_event.v1"
        ]:
            if (
                projection.get("projection_event_kind") == "authority_change"
                and projection.get("change_kind_or_null") == "source_quarantined"
                and projection.get("projection_visibility_or_null")
                == "normal_consumer"
            ):
                errors.append(
                    f"Change projection {projection.get('projection_event_id')}: "
                    "quarantined source projected to a normal consumer"
                )

        # Event operation must be permitted by the embedded AuthorityScope.
        operation_requirements: dict[str, tuple[str, str | None]] = {
            "relaylm.route_capture_grant_snapshot.v1": (
                "validator_authority_scope",
                "route_snapshot_validate",
            ),
            "relaylm.evidence_admission_decision.v1": (
                "decider_authority_scope",
                "admission_decide",
            ),
            "relaylm.admission_review_decision.v1": (
                "reviewer_authority_scope_refs",
                None,
            ),
            "relaylm.admission_validation_bundle_revision.v1": (
                "authority_scope",
                None,
            ),
            "relaylm.evidence_governance_event.v1": (
                "authority_scope",
                None,
            ),
            "relaylm.source_metadata_revision.v1": (
                "authority_scope",
                "metadata_correct",
            ),
            "relaylm.source_lineage_relation_event.v1": (
                "authority_scope",
                None,
            ),
            "relaylm.source_derived_artifact_event.v1": (
                "mutation_authority_scope",
                None,
            ),
            "relaylm.source_capture_stream_descriptor.v1": (
                "issuer_authority_scope",
                None,
            ),
            "relaylm.capture_sequence_event.v1": (
                "issuer_authority_scope",
                None,
            ),
            "relaylm.source_capture_coverage_checkpoint.v1": (
                "issuer_authority_scope",
                "capture_coverage_advance",
            ),
            "relaylm.evidence_change_partition_descriptor.v1": (
                "issuer_authority_scope",
                None,
            ),
            "relaylm.evidence_authority_change_set_event.v1": (
                "issuer_authority_scope",
                None,
            ),
            "relaylm.evidence_authority_change_projection_event.v1": (
                None,
                None,
            ),
            "relaylm.source_projection_registry_event.v1": (
                "issuer_authority_scope",
                None,
            ),
            "relaylm.evidence_change_coverage_checkpoint.v1": (
                "issuer_authority_scope",
                "change_coverage_advance",
            ),
            "relaylm.assistant_response_capture_reservation.v1": (
                "runtime_finalization_authority_scope",
                "response_capture_reserve",
            ),
            "relaylm.assistant_response_capture_event.v1": (
                "runtime_finalization_authority_scope",
                None,
            ),
            "relaylm.assistant_delivery_observation_event.v1": (
                "observer_authority_scope",
                "response_output_observe",
            ),
            "relaylm.protected_payload_binding_attestation.v1": (
                "attester_authority_scope",
                "storage_binding_attest",
            ),
            "relaylm.evidence_access_grant.v1": (
                "issued_by_authority_scope",
                "grant_access",
            ),
        }

        capture_attempt_ops = {
            "reserve": "capture_attempt_reserve",
            "begin_content": "capture_attempt_begin_content",
            "finalize_candidate": "capture_attempt_finalize_candidate",
            "bind_admission": "capture_attempt_bind_admission",
            "terminal_no_source": "capture_attempt_terminal_no_source",
            "mark_abandoned_recoverable": "capture_attempt_mark_abandoned",
            "recover_abandoned": "capture_attempt_recover",
        }
        response_ops = {
            "emission_begin": "response_emission_begin",
            "output_observed": "response_output_observe",
            "finalize": "response_finalize",
            "terminal_no_output": "response_terminal_no_output",
            "mark_abandoned": "response_mark_abandoned",
            "recover_finalization": "response_recover_finalization",
        }
        sequence_ops = {
            "reserve": "capture_sequence_reserve",
            "terminalize_admission": "capture_sequence_terminalize_admission",
            "terminalize_no_source": "capture_sequence_terminalize_no_source",
            "mark_aborted_recoverable": "capture_sequence_mark_aborted",
            "recover_aborted": "capture_sequence_recover_aborted",
        }
        change_set_ops = {
            "plan": "change_set_plan",
            "mark_complete": "change_set_mark_complete",
            "mark_corrupt": "change_set_mark_corrupt",
        }
        registry_ops = {
            "initialize": "source_projection_registry_initialize",
            "add_partition": "source_projection_registry_add_partition",
            "retire_partition_visibility":
                "source_projection_registry_retire_visibility",
        }

        def required_operation(record: dict[str, Any]) -> str | None:
            schema_id = record.get("schema")
            if schema_id == "relaylm.capture_attempt_event.v1":
                return capture_attempt_ops.get(record.get("operation"))
            if schema_id == "relaylm.admission_validation_bundle_revision.v1":
                return (
                    "validation_bundle_create"
                    if record.get("bundle_revision") == 1
                    else "validation_bundle_revise"
                )
            if schema_id == "relaylm.evidence_governance_event.v1":
                return record.get("operation")
            if schema_id == "relaylm.source_lineage_relation_event.v1":
                operation = record.get("operation")
                return f"lineage_{operation}" if operation else None
            if schema_id == "relaylm.source_derived_artifact_event.v1":
                operation = record.get("operation")
                return f"artifact_{operation}" if operation else None
            if schema_id == "relaylm.source_capture_stream_descriptor.v1":
                status = record.get("stream_status")
                revision = record.get("descriptor_revision")
                if revision == 1:
                    return "capture_stream_create"
                return {
                    "sealed": "capture_stream_seal",
                    "retired": "capture_stream_retire",
                    "open": "capture_stream_rotate",
                }.get(status)
            if schema_id == "relaylm.capture_sequence_event.v1":
                return sequence_ops.get(record.get("operation"))
            if schema_id == "relaylm.evidence_change_partition_descriptor.v1":
                status = record.get("partition_status")
                revision = record.get("descriptor_revision")
                if revision == 1:
                    return "change_partition_create"
                return {
                    "sealed": "change_partition_seal",
                    "retired": "change_partition_retire",
                }.get(status)
            if schema_id == "relaylm.evidence_authority_change_set_event.v1":
                return change_set_ops.get(record.get("operation"))
            if schema_id == (
                "relaylm.evidence_authority_change_projection_event.v1"
            ):
                return (
                    "change_projection_abort"
                    if record.get("projection_event_kind")
                    == "change_projection_aborted"
                    else "change_projection_emit"
                )
            if schema_id == "relaylm.source_projection_registry_event.v1":
                return registry_ops.get(record.get("operation"))
            if schema_id == "relaylm.assistant_response_capture_event.v1":
                return response_ops.get(record.get("operation"))
            if schema_id == "relaylm.admission_review_decision.v1":
                return "admission_review_decide"
            return operation_requirements.get(schema_id, (None, None))[1]

        for record in records:
            schema_id = record.get("schema", "")
            required_op = required_operation(record)
            if required_op is None:
                continue

            scope_field = operation_requirements.get(
                schema_id, (None, None)
            )[0]

            # CaptureAttemptEvent is not in the static table because it shares
            # the generic authority_scope field with Contract 1A.
            if schema_id == "relaylm.capture_attempt_event.v1":
                scope_field = "authority_scope"
            elif schema_id == (
                "relaylm.evidence_authority_change_projection_event.v1"
            ):
                # Projection events intentionally carry no actor scope object in
                # v1. Their authority is validated by the partition issuer and
                # change-set/outbox boundary.
                continue

            if scope_field == "reviewer_authority_scope_refs":
                # Review decisions carry immutable scope references rather than
                # embedded scope bodies; exact resolution is a repository/runtime
                # integration check outside standalone fixtures.
                continue

            scope = record.get(scope_field) if scope_field else None
            if not isinstance(scope, dict):
                errors.append(
                    f"{schema_id}: missing embedded AuthorityScope "
                    f"for required operation {required_op}"
                )
                continue
            allowed = scope.get("allowed_operations", [])
            if required_op not in allowed:
                record_id = (
                    record.get("operation_idempotency_key")
                    or record.get("source_event_id")
                    or record.get("response_id")
                    or "<unknown>"
                )
                errors.append(
                    f"{schema_id} {record_id}: AuthorityScope does not allow "
                    f"operation {required_op}"
                )

        # Revision chains for append-only records.
        self._check_revision_chains(
            records,
            errors,
            schema_id="relaylm.capture_attempt_event.v1",
            id_field="capture_attempt_id",
            rev_field="attempt_revision",
            prev_field="expected_previous_attempt_revision_or_null",
        )
        self._check_revision_chains(
            records,
            errors,
            schema_id="relaylm.assistant_response_capture_event.v1",
            id_field="response_capture_reservation_id",
            rev_field="response_revision",
            prev_field="expected_previous_response_revision_or_null",
        )
        self._check_revision_chains(
            records,
            errors,
            schema_id="relaylm.capture_sequence_event.v1",
            id_field=("capture_stream_epoch_id", "capture_sequence"),
            rev_field="sequence_revision",
            prev_field="expected_previous_sequence_revision_or_null",
        )
        self._check_revision_chains(
            records,
            errors,
            schema_id="relaylm.evidence_authority_change_set_event.v1",
            id_field="change_set_id",
            rev_field="change_set_revision",
            prev_field="expected_previous_change_set_revision_or_null",
        )
        self._check_revision_chains(
            records,
            errors,
            schema_id="relaylm.source_projection_registry_event.v1",
            id_field="source_event_id",
            rev_field="registry_revision",
            prev_field="expected_previous_registry_revision_or_null",
        )
        self._check_revision_chains(
            records,
            errors,
            schema_id="relaylm.assistant_delivery_observation_event.v1",
            id_field="delivery_observation_series_id",
            rev_field="observation_revision",
            prev_field="expected_previous_observation_revision_or_null",
        )
        self._check_revision_chains(
            records,
            errors,
            schema_id="relaylm.evidence_governance_event.v1",
            id_field="source_event_id",
            rev_field="governance_revision",
            prev_field="expected_previous_governance_revision_or_null",
        )
        self._check_revision_chains(
            records,
            errors,
            schema_id="relaylm.source_metadata_revision.v1",
            id_field="source_event_id",
            rev_field="metadata_revision",
            prev_field="expected_previous_metadata_revision_or_null",
        )
        self._check_revision_chains(
            records,
            errors,
            schema_id="relaylm.source_derived_artifact_event.v1",
            id_field="derived_artifact_id",
            rev_field="artifact_revision",
            prev_field="expected_previous_artifact_revision_or_null",
        )

        # Change-set plan and completion.
        projections = {
            r.get("projection_event_id"): r
            for r in by_schema[
                "relaylm.evidence_authority_change_projection_event.v1"
            ]
        }
        plans: dict[str, dict[str, Any]] = {}
        for event in by_schema["relaylm.evidence_authority_change_set_event.v1"]:
            if event.get("operation") == "plan":
                payload = event.get("operation_payload", {})
                if digest_obj(payload.get("projection_plan", [])) != payload.get(
                    "projection_plan_digest"
                ):
                    errors.append(
                        f"AuthorityChangeSet {event.get('change_set_id')}: "
                        "projection plan digest mismatch"
                    )
                plans[event["change_set_id"]] = payload
            elif event.get("operation") == "mark_complete":
                payload = event.get("operation_payload", {})
                plan = plans.get(event.get("change_set_id"))
                if plan is None:
                    errors.append(
                        f"AuthorityChangeSet {event.get('change_set_id')}: "
                        "mark_complete has no plan"
                    )
                    continue
                completed_ids = payload.get("completed_projection_event_ids", [])
                if len(completed_ids) != len(plan.get("projection_plan", [])):
                    errors.append(
                        f"AuthorityChangeSet {event.get('change_set_id')}: "
                        "completed projection count differs from plan"
                    )
                for projection_id in completed_ids:
                    projection = projections.get(projection_id)
                    if projection is None:
                        errors.append(
                            f"AuthorityChangeSet {event.get('change_set_id')}: "
                            f"missing projection {projection_id}"
                        )
                    elif projection.get("projection_event_kind") != "authority_change":
                        errors.append(
                            f"AuthorityChangeSet {event.get('change_set_id')}: "
                            "abort counted as planned projection"
                        )

        # Registry references.
        for registry in by_schema["relaylm.source_projection_registry_event.v1"]:
            for entry in registry.get("partition_entries", []):
                if entry.get("first_projection_event_id") not in projections:
                    errors.append(
                        f"SourceProjectionRegistry "
                        f"{registry.get('source_event_id')}: "
                        "first projection event missing"
                    )

        # Scenario-level negative/absence guarantees.
        expectations = fixture.get("expectations", {})
        if expectations.get("contract1_record_count") == 0 and records:
            errors.append("scenario expected no Contract 1 records")
        if expectations.get("source_event_count") == 0 and by_schema[
            "relaylm.source_event.v1"
        ]:
            errors.append("scenario expected no SourceEvent")
        if expectations.get("admission_decision_count") == 0 and by_schema[
            "relaylm.evidence_admission_decision.v1"
        ]:
            errors.append("scenario expected no AdmissionDecision")
        forbidden = set(expectations.get("forbidden_contract1b_operations", []))
        if forbidden:
            actual = {
                event.get("operation")
                for event in by_schema["relaylm.evidence_governance_event.v1"]
            }
            overlap = forbidden & actual
            if overlap:
                errors.append(
                    f"scenario contains forbidden governance operations: "
                    f"{sorted(overlap)}"
                )

        return errors

    @staticmethod
    def _check_revision_chains(
        records: list[dict[str, Any]],
        errors: list[str],
        *,
        schema_id: str,
        id_field: str | tuple[str, ...],
        rev_field: str,
        prev_field: str,
    ) -> None:
        groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            if record.get("schema") != schema_id:
                continue
            if isinstance(id_field, tuple):
                key = tuple(record.get(field) for field in id_field)
            else:
                key = record.get(id_field)
            groups[key].append(record)
        for key, chain in groups.items():
            chain.sort(key=lambda r: r.get(rev_field, 0))
            expected = 1
            for record in chain:
                revision = record.get(rev_field)
                if revision != expected:
                    errors.append(
                        f"{schema_id} {key}: expected revision {expected}, "
                        f"found {revision}"
                    )
                    expected = revision if isinstance(revision, int) else expected
                previous = record.get(prev_field)
                expected_previous = None if revision == 1 else revision - 1
                if previous != expected_previous:
                    errors.append(
                        f"{schema_id} {key} revision {revision}: "
                        f"expected_previous should be {expected_previous}, "
                        f"found {previous}"
                    )
                expected += 1


def run(root: Path, verbose: bool = False) -> int:
    validator = ContractValidator(
        root / "docs" / "contracts" / "schemas" / "contract1-v7" / "relaylm-contract1-v7.bundle.schema.json"
    )
    valid_dir = root / "docs" / "contracts" / "fixtures" / "contract1-v7" / "valid"
    invalid_dir = root / "docs" / "contracts" / "fixtures" / "contract1-v7" / "invalid"
    failures: list[str] = []

    valid_count = 0
    for path in sorted(valid_dir.glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        errors = validator.validate_fixture(fixture)
        valid_count += 1
        if errors:
            failures.append(
                f"VALID fixture {path.name} failed:\n  "
                + "\n  ".join(errors)
            )
        elif verbose:
            print(f"PASS valid: {path.name}")

    invalid_count = 0
    for path in sorted(invalid_dir.glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        errors = validator.validate_fixture(fixture)
        invalid_count += 1
        if not errors:
            failures.append(
                f"INVALID fixture {path.name} unexpectedly passed"
            )
        elif verbose:
            print(f"PASS invalid rejected: {path.name}")
            for error in errors[:3]:
                print(f"  - {error}")

    if failures:
        print("\n\n".join(failures), file=sys.stderr)
        return 1

    print(
        f"Contract 1 v7 validation PASS: "
        f"{valid_count} valid fixtures accepted, "
        f"{invalid_count} invalid fixtures rejected, "
        f"{len(validator.defs)} schema definitions loaded."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    return run(args.root, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
