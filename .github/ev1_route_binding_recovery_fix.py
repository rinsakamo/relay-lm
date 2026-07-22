from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected fragment not found in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/evidence_response_session.py",
    '''    expected = {
        "response_id": response_id,
        "delivery_cohort_id": delivery_cohort_id,
        "evidence_space_id": descriptor.evidence_space_id,
        "route_capture_grant_snapshot_ref": route_snapshot.route_binding_id,
        "capture_stream_id": stream_descriptor.capture_stream_id,
        "capture_stream_epoch_id": stream_descriptor.capture_stream_epoch_id,
    }
    if any(reservation.get(key) != value for key, value in expected.items()):
        return None, ("assistant_response_reservation_integrity_conflict",)
''',
    '''    expected = {
        "response_id": response_id,
        "delivery_cohort_id": delivery_cohort_id,
        "evidence_space_id": descriptor.evidence_space_id,
        "capture_stream_id": stream_descriptor.capture_stream_id,
        "capture_stream_epoch_id": stream_descriptor.capture_stream_epoch_id,
    }
    if any(reservation.get(key) != value for key, value in expected.items()):
        return None, ("assistant_response_reservation_integrity_conflict",)
    persisted_route_ref = reservation.get("route_capture_grant_snapshot_ref")
    if not isinstance(persisted_route_ref, str) or not persisted_route_ref:
        return None, ("assistant_response_reservation_shape_invalid",)
    persisted_route_payload = tx.read_record(
        record_kind="route_capture_grant_snapshot", record_id=persisted_route_ref
    )
    persisted_route_snapshot, persisted_route_reasons = (
        build_managed_conversation_route_snapshot(
            snapshot_payload=persisted_route_payload,
            evidence_space_id=descriptor.evidence_space_id,
            capture_profile="managed_assistant_response",
        )
    )
    if persisted_route_snapshot is None or persisted_route_reasons:
        return None, ("assistant_response_route_snapshot_recovery_invalid",)
    if (
        persisted_route_snapshot.route_binding_id != persisted_route_ref
        or persisted_route_snapshot.route_contract_ref != route_snapshot.route_contract_ref
        or persisted_route_snapshot.route_contract_revision
        != route_snapshot.route_contract_revision
        or persisted_route_snapshot.route_contract_snapshot_digest
        != route_snapshot.route_contract_snapshot_digest
        or persisted_route_snapshot.evidence_space_id != route_snapshot.evidence_space_id
        or persisted_route_snapshot.capture_profile != route_snapshot.capture_profile
    ):
        return None, ("assistant_response_reservation_integrity_conflict",)
''',
)
replace_once(
    "relaylm/evidence_response_session.py",
    "        route_snapshot=route_snapshot,\n        stream_descriptor=stream_descriptor,\n        capture_attempt_id=capture_attempt_id,\n        capture_sequence=sequence,\n        response_capture_reservation_id=str(reservation[\"response_capture_reservation_id\"]),\n",
    "        route_snapshot=persisted_route_snapshot,\n        stream_descriptor=stream_descriptor,\n        capture_attempt_id=capture_attempt_id,\n        capture_sequence=sequence,\n        response_capture_reservation_id=str(reservation[\"response_capture_reservation_id\"]),\n",
)
replace_once(
    "tests/test_evidence_contract_integrity.py",
    "from relaylm.evidence_response_session import derive_id\n",
    "from relaylm.evidence_response_session import derive_id, prepare_response_capture\n",
)
replace_once(
    "tests/test_evidence_contract_integrity.py",
    '''    assert len(source["protected_payload_binding_attestation_ids"]) == 1


def test_stream_dry_run_hands_off_first_chunk_and_finalizes_diagnostics(tmp_path) -> None:
''',
    '''    assert len(source["protected_payload_binding_attestation_ids"]) == 1


def test_response_recovery_reuses_persisted_route_snapshot_across_validation_times(
    tmp_path,
) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    operation_key = "assistant-route-recovery"
    prepared, reasons = prepare_response_capture(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="response-recovery",
        delivery_cohort_id="cohort-recovery",
        request_source_event_ids=(),
        operation_idempotency_key=operation_key,
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_assistant_response",
            issued_at=NOW.isoformat(),
        ),
        now=NOW,
    )
    assert prepared is not None and not reasons
    ok, observe_reasons = prepared.observe("visible answer", NOW.isoformat())
    assert ok and not observe_reasons

    recovered = capture_managed_assistant_response_nonstream(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="response-recovery",
        delivery_cohort_id="cohort-recovery",
        request_source_event_ids=(),
        assistant_visible_text="visible answer",
        operation_idempotency_key=operation_key,
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_assistant_response",
            issued_at=(NOW + timedelta(seconds=5)).isoformat(),
        ),
        now=NOW + timedelta(seconds=5),
    )
    assert recovered.status == "admitted"
    assert recovered.source_event_id is not None


def test_stream_dry_run_hands_off_first_chunk_and_finalizes_diagnostics(tmp_path) -> None:
''',
)
