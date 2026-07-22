"""ASM-1 Shared Assessment runtime acceptance and safety tests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from evidence_test_support import route_snapshot
from relaylm.config import RelayLMConfig
from relaylm.evidence_store import EvidenceRecordStore
from relaylm.evidence_user_input import capture_managed_user_input
from relaylm.shared_assessment import SharedAssessmentProposal
from relaylm.shared_assessment_runtime import (
    commit_shared_assessment_revision,
    issue_shared_assessment_formation_receipt,
    prepare_shared_assessment_pass,
    resolve_shared_assessment_gate,
)

NOW = datetime(2026, 7, 22, 8, 0, 0, tzinfo=timezone.utc)

BASE_CONFIG = dict(
    backends={
        "local": {
            "type": "openai_compatible",
            "base_url": "http://127.0.0.1:8000/v1",
        }
    },
    model_routes={"relaylm-default": {"backend": "local", "mode": "memory_light"}},
)


@pytest.fixture()
def store(tmp_path: Path) -> EvidenceRecordStore:
    return EvidenceRecordStore(str(tmp_path / "evidence"))


def _capture(
    store: EvidenceRecordStore,
    *,
    key: str = "source-1",
    text: str = "I have been tired lately.",
    now: datetime = NOW,
):
    return capture_managed_user_input(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        current_user_text=text,
        fail_closed_reasons=(),
        operation_idempotency_key=key,
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_user_input", issued_at=now.isoformat()
        ),
        now=now,
    )


def _bundle(store: EvidenceRecordStore, *, count: int = 1):
    captures = tuple(
        _capture(store, key=f"source-{index}", text=f"statement {index}")
        for index in range(count)
    )
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captures[0].evidence_space_id,
        source_event_ids=tuple(item.source_event_id for item in captures),
        assessment_pass_id="assessment-pass-1",
        now=NOW,
    )
    assert result.status == "ready", result.blocked_reasons
    assert result.bundle is not None
    return captures, result.bundle


def _proposal(*, expected=None, text="The user reported a current condition."):
    return SharedAssessmentProposal(
        assessment_id="assessment-1",
        supported_content=text,
        support_state="supported",
        uncertainty=("exact_duration_unknown",),
        temporal_state="current",
        governance_revision="shared-assessment-policy-v1",
        expected_current_revision_or_null=expected,
    )


def test_pass_bundle_is_character_independent_and_exactly_evidence_authorized(store) -> None:
    captures, bundle = _bundle(store, count=2)
    payload = bundle.to_dict()
    assert bundle.is_self_authenticating()
    assert [item.source_event_id for item in bundle.evidence_refs] == [
        item.source_event_id for item in captures
    ]
    assert [item.source_origin for item in bundle.evidence_refs] == ["user", "user"]
    assert all(item.authorization_state == "current_admitted" for item in bundle.evidence_refs)
    assert [item.text for item in bundle.parts] == ["statement 0", "statement 1"]
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for forbidden in (
        "character_id",
        "soul_revision",
        "relationship_id",
        "scene_id",
        "emotion",
        "style",
        "subjective_meaning",
    ):
        assert forbidden not in serialized


def test_missing_or_cross_space_source_fails_closed(store) -> None:
    captured = _capture(store)
    missing = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captured.evidence_space_id,
        source_event_ids=("sourceevent_missing",),
        assessment_pass_id="pass-missing",
        now=NOW,
    )
    assert missing.status == "fail_closed"
    assert "shared_assessment_source_event_missing_or_invalid" in missing.blocked_reasons

    other = _capture(
        store,
        key="other-source",
        text="other",
        now=NOW + timedelta(seconds=1),
    )
    cross = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id="evsp_wrong",
        source_event_ids=(other.source_event_id,),
        assessment_pass_id="pass-cross",
        now=NOW,
    )
    assert cross.status == "fail_closed"


def test_expired_evidence_authority_fails_closed(store) -> None:
    captured = _capture(store)
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captured.evidence_space_id,
        source_event_ids=(captured.source_event_id,),
        assessment_pass_id="pass-expired",
        now=NOW + timedelta(days=31),
    )
    assert result.status == "fail_closed"
    assert any("deadline_expired" in reason for reason in result.blocked_reasons)


def test_first_revision_and_single_current_selector_commit_atomically(store) -> None:
    captures, bundle = _bundle(store)
    result = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="commit-1",
        apply_enabled=True,
        now=NOW,
    )
    assert result.status == "committed"
    assert result.persisted is True
    assert result.revision is not None
    assert result.current_state is not None
    assert result.revision.assessment_revision == 1
    assert result.revision.supersedes_assessment_revision_or_null is None
    assert result.revision.character_independent is True
    assert result.current_state.current_revision == 1

    state_files = list(
        (store.root / captures[0].evidence_space_id / "logs" / "shared_assessment_current_state").glob("*.json")
    )
    assert len(state_files) == 1
    assert len(json.loads(state_files[0].read_text())) == 1


def test_revision_and_selector_match_contract_schema(store) -> None:
    _captures, bundle = _bundle(store)
    committed = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="schema-commit",
        apply_enabled=True,
        now=NOW,
    )
    assert committed.revision is not None and committed.current_state is not None
    schema = json.loads(
        Path("docs/contracts/schemas/subjective-mem-v1/relaylm-subjective-mem-v1.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    validator.validate(
        {"records": [committed.revision.to_dict(), committed.current_state.to_dict()]}
    )


def test_retry_is_idempotent_and_conflicting_retry_is_rejected(store) -> None:
    _captures, bundle = _bundle(store)
    first = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="same-operation",
        apply_enabled=True,
        now=NOW,
    )
    retry = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="same-operation",
        apply_enabled=True,
        now=NOW,
    )
    conflict = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(text="different supported content"),
        operation_idempotency_key="same-operation",
        apply_enabled=True,
        now=NOW,
    )
    assert first.status == "committed"
    assert retry.status == "duplicate_existing"
    assert retry.revision == first.revision
    assert conflict.status == "integrity_conflict"


def test_consecutive_revision_requires_exact_expected_current_revision(store) -> None:
    _captures, bundle = _bundle(store)
    first = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="revision-1",
        apply_enabled=True,
        now=NOW,
    )
    assert first.status == "committed"
    stale = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(expected=None, text="stale output"),
        operation_idempotency_key="revision-stale",
        apply_enabled=True,
        now=NOW + timedelta(seconds=1),
    )
    assert stale.status == "fail_closed"
    assert stale.blocked_reasons == ("shared_assessment_expected_current_revision_stale",)

    second = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(expected=1, text="refined supported content"),
        operation_idempotency_key="revision-2",
        apply_enabled=True,
        now=NOW + timedelta(seconds=2),
    )
    assert second.status == "committed"
    assert second.revision is not None
    assert second.revision.assessment_revision == 2
    assert second.revision.supersedes_assessment_revision_or_null == 1


def test_dry_run_validates_without_shared_assessment_write(store) -> None:
    captures, bundle = _bundle(store)
    result = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="dry-run",
        apply_enabled=False,
        now=NOW,
    )
    assert result.status == "dry_run_ready"
    assert result.persisted is False
    space = store.root / captures[0].evidence_space_id
    assert not (space / "records" / "shared_assessment_revision").exists()
    assert not (space / "logs" / "shared_assessment_current_state").exists()


def test_formation_receipt_is_exact_current_and_content_free(store) -> None:
    captures, bundle = _bundle(store)
    committed = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="commit-for-receipt",
        apply_enabled=True,
        now=NOW,
    )
    assert committed.status == "committed"
    receipt = issue_shared_assessment_formation_receipt(
        store=store,
        evidence_space_id=captures[0].evidence_space_id,
        assessment_id="assessment-1",
        assessment_revision=1,
        operation_idempotency_key="receipt-1",
        now=NOW,
    )
    assert receipt.status == "issued"
    assert receipt.receipt is not None
    payload = receipt.receipt.to_dict()
    assert payload["assessment_authorization_receipt"] == {
        "current_revision_at_decision": 1,
        "lifecycle_state_at_decision": "active",
        "authorization_state_at_decision": "current_admitted",
    }
    assert "supported_content" not in payload
    assert "character" not in json.dumps(payload, sort_keys=True)
    assert not (
        store.root
        / captures[0].evidence_space_id
        / "records"
        / "subjective_mem_revision"
    ).exists()


def test_prior_revision_cannot_receive_new_receipt_after_successor(store) -> None:
    captures, bundle = _bundle(store)
    first = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="first",
        apply_enabled=True,
        now=NOW,
    )
    assert first.status == "committed"
    second = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(expected=1, text="new current assessment"),
        operation_idempotency_key="second",
        apply_enabled=True,
        now=NOW + timedelta(seconds=1),
    )
    assert second.status == "committed"
    receipt = issue_shared_assessment_formation_receipt(
        store=store,
        evidence_space_id=captures[0].evidence_space_id,
        assessment_id="assessment-1",
        assessment_revision=1,
        operation_idempotency_key="stale-receipt",
        now=NOW + timedelta(seconds=2),
    )
    assert receipt.status == "fail_closed"
    assert receipt.blocked_reasons == (
        "shared_assessment_receipt_target_not_current_admitted",
    )


def test_duplicate_current_selector_fails_closed(store) -> None:
    _captures, bundle = _bundle(store)
    state_key = "asmstate_" + __import__("hashlib").sha256(b"assessment-1").hexdigest()
    store.write_log(
        evidence_space_id=bundle.evidence_space_id,
        log_kind="shared_assessment_current_state",
        key=state_key,
        events=({"schema": "bad"}, {"schema": "bad"}),
    )
    result = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="duplicate-state",
        apply_enabled=True,
        now=NOW,
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "shared_assessment_duplicate_or_corrupt_current_state",
    )


def test_default_off_and_apply_gate_reuses_absolute_evidence_root(tmp_path: Path) -> None:
    default = RelayLMConfig(**BASE_CONFIG)
    gate = resolve_shared_assessment_gate(default)
    assert gate.enabled is False
    assert gate.store is None

    with pytest.raises(ValidationError):
        RelayLMConfig(
            **BASE_CONFIG,
            shared_assessment_enabled=True,
            shared_assessment_dry_run_only=False,
            shared_assessment_apply_enabled=True,
            evidence_data_root=None,
        )
    config = RelayLMConfig(
        **BASE_CONFIG,
        shared_assessment_enabled=True,
        shared_assessment_dry_run_only=False,
        shared_assessment_apply_enabled=True,
        evidence_data_root=str(tmp_path / "evidence"),
    )
    gate = resolve_shared_assessment_gate(config)
    assert gate.enabled is True
    assert gate.apply_enabled is True
    assert gate.store is not None


def test_user_and_assistant_evidence_share_one_character_independent_pass(store) -> None:
    from relaylm.evidence_response_capture import (
        capture_managed_assistant_response_nonstream,
    )

    user = _capture(store, key="user-turn", text="I feel tired.")
    assistant = capture_managed_assistant_response_nonstream(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="response-1",
        delivery_cohort_id="cohort-1",
        request_source_event_ids=(user.source_event_id,),
        assistant_visible_text="You said you feel tired.",
        operation_idempotency_key="assistant-turn",
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_assistant_response", issued_at=NOW.isoformat()
        ),
        now=NOW,
    )
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=user.evidence_space_id,
        source_event_ids=(user.source_event_id, assistant.source_event_id),
        assessment_pass_id="mixed-pass",
        now=NOW,
    )
    assert result.status == "ready", result.blocked_reasons
    assert result.bundle is not None
    assert [item.source_origin for item in result.bundle.evidence_refs] == [
        "user",
        "assistant",
    ]


def test_reprepared_equivalent_pass_is_idempotent_for_same_operation(store) -> None:
    captures, first_bundle = _bundle(store)
    first = commit_shared_assessment_revision(
        store=store,
        bundle=first_bundle,
        proposal=_proposal(),
        operation_idempotency_key="reprepared-operation",
        apply_enabled=True,
        now=NOW,
    )
    assert first.status == "committed"
    prepared_again = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captures[0].evidence_space_id,
        source_event_ids=(captures[0].source_event_id,),
        assessment_pass_id="different-ephemeral-pass-id",
        now=NOW + timedelta(seconds=1),
    )
    assert prepared_again.status == "ready"
    assert prepared_again.bundle is not None
    assert prepared_again.bundle.bundle_digest != first_bundle.bundle_digest
    retry = commit_shared_assessment_revision(
        store=store,
        bundle=prepared_again.bundle,
        proposal=_proposal(),
        operation_idempotency_key="reprepared-operation",
        apply_enabled=True,
        now=NOW + timedelta(seconds=1),
    )
    assert retry.status == "duplicate_existing"
    assert retry.revision == first.revision


def test_product_knowledge_derived_source_is_excluded_from_personal_assessment(store) -> None:
    captured = _capture(store)
    source_path = (
        store.root
        / captured.evidence_space_id
        / "records"
        / "source_event"
        / f"{captured.source_event_id}.json"
    )
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    raw["provenance_snapshot"]["source_material_classes"] = [
        "product_knowledge_derived"
    ]
    source_path.write_text(
        json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captured.evidence_space_id,
        source_event_ids=(captured.source_event_id,),
        assessment_pass_id="product-knowledge-pass",
        now=NOW,
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "shared_assessment_product_knowledge_forbidden",
    )


def test_pass_and_result_diagnostics_do_not_expose_protected_text(store) -> None:
    _captures, bundle = _bundle(store)
    prepared = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=bundle.evidence_space_id,
        source_event_ids=tuple(item.source_event_id for item in bundle.evidence_refs),
        assessment_pass_id="diagnostic-pass",
        now=NOW,
    )
    assert prepared.status == "ready"
    assert "statement 0" not in repr(prepared)
    assert "statement 0" not in json.dumps(prepared.to_log_dict(), sort_keys=True)
    committed = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(text="protected assessment text"),
        operation_idempotency_key="diagnostic-commit",
        apply_enabled=False,
        now=NOW,
    )
    assert committed.status == "dry_run_ready"
    assert "protected assessment text" not in repr(committed)
    assert "protected assessment text" not in json.dumps(
        committed.to_log_dict(), sort_keys=True
    )


def test_malformed_proposal_and_tampered_bundle_fail_closed(store) -> None:
    from dataclasses import replace

    _captures, bundle = _bundle(store)
    malformed = SharedAssessmentProposal(
        assessment_id="assessment-1",
        supported_content="content",
        support_state="supported",
        uncertainty=[],  # type: ignore[arg-type]
        temporal_state="current",
        governance_revision="shared-assessment-policy-v1",
        expected_current_revision_or_null=False,  # type: ignore[arg-type]
    )
    malformed_result = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=malformed,
        operation_idempotency_key="malformed-proposal",
        apply_enabled=True,
        now=NOW,
    )
    assert malformed_result.status == "fail_closed"
    assert "shared_assessment_uncertainty_invalid" in malformed_result.blocked_reasons
    assert (
        "shared_assessment_expected_current_revision_invalid"
        in malformed_result.blocked_reasons
    )

    tampered_part = replace(bundle.parts[0], text="tampered text")
    tampered = replace(bundle, parts=(tampered_part,))
    tampered_result = commit_shared_assessment_revision(
        store=store,
        bundle=tampered,
        proposal=_proposal(),
        operation_idempotency_key="tampered-bundle",
        apply_enabled=True,
        now=NOW,
    )
    assert tampered_result.status == "fail_closed"
    assert "shared_assessment_pass_part_digest_invalid" in tampered_result.blocked_reasons


def test_enabled_dry_run_also_requires_evidence_root(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        RelayLMConfig(
            **BASE_CONFIG,
            shared_assessment_enabled=True,
            shared_assessment_dry_run_only=True,
            shared_assessment_apply_enabled=False,
            evidence_data_root=None,
        )
    config = RelayLMConfig(
        **BASE_CONFIG,
        shared_assessment_enabled=True,
        shared_assessment_dry_run_only=True,
        shared_assessment_apply_enabled=False,
        evidence_data_root=str(tmp_path / "evidence"),
    )
    gate = resolve_shared_assessment_gate(config)
    assert gate.enabled is True
    assert gate.dry_run_only is True
    assert gate.apply_enabled is False
    assert gate.store is not None
