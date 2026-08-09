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
import relaylm.shared_assessment.runtime as shared_assessment_runtime
from relaylm.evidence.space import derive_evidence_space_id
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.evidence.user_input import capture_managed_user_input
from relaylm.shared_assessment.models import (
    SharedAssessmentProposal,
    derive_shared_assessment_id,
)
from relaylm.shared_assessment.runtime import (
    build_shared_assessment_formation_receipt,
    commit_shared_assessment_revision,
    prepare_shared_assessment_pass,
    resolve_shared_assessment_gate,
)

NOW = datetime(2026, 7, 22, 8, 0, 0, tzinfo=timezone.utc)
EVIDENCE_SPACE_ID = derive_evidence_space_id(
    workspace_or_tenant_ref="relaylm-local",
    character_id="char1",
    memory_namespace="ns1",
    session_id="sess1",
)
ASSESSMENT_ID = derive_shared_assessment_id(EVIDENCE_SPACE_ID, "assessment-1")
DECISION_INPUT_DIGEST = "a" * 64

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
    session_id: str = "sess1",
):
    return capture_managed_user_input(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id=session_id,
        current_user_text=text,
        fail_closed_reasons=(),
        operation_idempotency_key=key,
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_user_input",
            session_id=session_id,
            issued_at=now.isoformat(),
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
        assessment_id=ASSESSMENT_ID,
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


def test_revision_bound_blocks_successor_without_corrupting_current(
    monkeypatch, store
) -> None:
    _captures, bundle = _bundle(store)
    monkeypatch.setattr(
        shared_assessment_runtime, "MAX_SHARED_ASSESSMENT_REVISIONS", 1
    )
    first = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="bounded-revision-1",
        apply_enabled=True,
        now=NOW,
    )
    assert first.status == "committed"

    blocked = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(expected=1, text="must not become revision two"),
        operation_idempotency_key="bounded-revision-2",
        apply_enabled=True,
        now=NOW + timedelta(seconds=1),
    )
    assert blocked.status == "fail_closed"
    assert blocked.blocked_reasons == (
        "shared_assessment_revision_index_bound_exceeded",
    )
    with store.transaction(bundle.evidence_space_id) as tx:
        receipt = build_shared_assessment_formation_receipt(
            tx=tx,
            evidence_space_id=bundle.evidence_space_id,
            assessment_id=ASSESSMENT_ID,
            assessment_revision=1,
            decision_id="bounded-revision-decision",
            decision_input_digest=DECISION_INPUT_DIGEST,
            decided_at=NOW + timedelta(seconds=2),
        )
    assert receipt.status == "ready"


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
    with store.transaction(captures[0].evidence_space_id) as tx:
        receipt = build_shared_assessment_formation_receipt(
            tx=tx,
            evidence_space_id=captures[0].evidence_space_id,
            assessment_id=ASSESSMENT_ID,
            assessment_revision=1,
            decision_id="decision-1",
            decision_input_digest=DECISION_INPUT_DIGEST,
            decided_at=NOW,
        )
    assert receipt.status == "ready"
    assert receipt.receipt is not None
    payload = receipt.receipt.to_dict()
    assert payload["assessment_authorization_receipt"] == {
        "current_revision_at_decision": 1,
        "lifecycle_state_at_decision": "active",
        "authorization_state_at_decision": "current_admitted",
    }
    assert "supported_content" not in payload
    assert payload["decision_id"] == "decision-1"
    assert payload["decision_input_digest"] == DECISION_INPUT_DIGEST
    assert receipt.receipt.is_self_authenticating()
    assert "character" not in json.dumps(payload, sort_keys=True)
    receipt_dir = (
        store.root
        / captures[0].evidence_space_id
        / "records"
        / "shared_assessment_formation_receipt"
    )
    assert not receipt_dir.exists()
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
    with store.transaction(captures[0].evidence_space_id) as tx:
        receipt = build_shared_assessment_formation_receipt(
            tx=tx,
            evidence_space_id=captures[0].evidence_space_id,
            assessment_id=ASSESSMENT_ID,
            assessment_revision=1,
            decision_id="stale-decision",
            decision_input_digest=DECISION_INPUT_DIGEST,
            decided_at=NOW + timedelta(seconds=2),
        )
    assert receipt.status == "fail_closed"
    assert receipt.blocked_reasons == (
        "shared_assessment_receipt_target_not_current_admitted",
    )


def test_duplicate_current_selector_fails_closed(store) -> None:
    _captures, bundle = _bundle(store)
    state_key = "asmstate_" + __import__("hashlib").sha256(ASSESSMENT_ID.encode("utf-8")).hexdigest()
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
    from relaylm.evidence.response_capture import (
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
        assessment_id=ASSESSMENT_ID,
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

def _record_path(store: EvidenceRecordStore, evidence_space_id: str, kind: str, record_id: str) -> Path:
    return store.root / evidence_space_id / "records" / kind / f"{record_id}.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )


def test_assessment_identity_is_bound_to_one_evidence_space(store) -> None:
    assert len(ASSESSMENT_ID.split("_")[1]) == 32
    _captures, first_bundle = _bundle(store)
    first = commit_shared_assessment_revision(
        store=store,
        bundle=first_bundle,
        proposal=_proposal(),
        operation_idempotency_key="space-one",
        apply_enabled=True,
        now=NOW,
    )
    assert first.status == "committed"
    other = _capture(
        store,
        key="space-two-source",
        text="other session",
        session_id="sess2",
        now=NOW,
    )
    prepared = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=other.evidence_space_id,
        source_event_ids=(other.source_event_id,),
        assessment_pass_id="space-two-pass",
        now=NOW,
    )
    assert prepared.bundle is not None
    blocked = commit_shared_assessment_revision(
        store=store,
        bundle=prepared.bundle,
        proposal=_proposal(),
        operation_idempotency_key="space-two-commit",
        apply_enabled=True,
        now=NOW,
    )
    assert blocked.status == "fail_closed"
    assert "shared_assessment_id_evidence_space_mismatch" in blocked.blocked_reasons


def test_source_manifest_must_match_admission_digest(store) -> None:
    captured = _capture(store)
    source_path = _record_path(
        store, captured.evidence_space_id, "source_event", captured.source_event_id
    )
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["canonical_source_manifest"]["manifest_extensions"] = {"tampered": True}
    from relaylm.evidence.common import canonical_digest

    source["canonical_source_manifest_digest"] = canonical_digest(
        source["canonical_source_manifest"]
    )
    _write_json(source_path, source)
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captured.evidence_space_id,
        source_event_ids=(captured.source_event_id,),
        assessment_pass_id="manifest-admission-mismatch",
        now=NOW,
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "shared_assessment_source_admission_manifest_mismatch",
    )


def test_validation_artifact_manifest_binding_is_required(store) -> None:
    captured = _capture(store)
    source = json.loads(
        _record_path(
            store, captured.evidence_space_id, "source_event", captured.source_event_id
        ).read_text(encoding="utf-8")
    )
    attempt = json.loads(
        next(
            (
                store.root
                / captured.evidence_space_id
                / "logs"
                / "capture_attempt"
            ).glob("*.json")
        ).read_text(encoding="utf-8")
    )
    admission_id = next(
        event["operation_payload"]["admission_decision_id"]
        for event in attempt
        if event.get("operation") == "bind_admission"
    )
    admission = json.loads(
        _record_path(
            store, captured.evidence_space_id, "admission_decision", admission_id
        ).read_text(encoding="utf-8")
    )
    validation = json.loads(
        _record_path(
            store,
            captured.evidence_space_id,
            "validation_bundle",
            admission["validation_bundle_id_or_null"],
        ).read_text(encoding="utf-8")
    )
    derived_id = validation["active_artifact_refs"][0]
    event_id = "artifactevent_" + derived_id.removeprefix("derivedartifact_")
    artifact_path = _record_path(
        store, captured.evidence_space_id, "source_derived_artifact_event", event_id
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["operation_payload"]["input_digest"] = "f" * 64
    _write_json(artifact_path, artifact)
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captured.evidence_space_id,
        source_event_ids=(source["source_event_id"],),
        assessment_pass_id="artifact-tamper",
        now=NOW,
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "shared_assessment_validation_artifacts_invalid",
    )


def test_persisted_grant_issuer_authority_is_not_synthesized(store) -> None:
    captured = _capture(store)
    source = json.loads(
        _record_path(
            store, captured.evidence_space_id, "source_event", captured.source_event_id
        ).read_text(encoding="utf-8")
    )
    attempt = json.loads(
        next(
            (
                store.root
                / captured.evidence_space_id
                / "logs"
                / "capture_attempt"
            ).glob("*.json")
        ).read_text(encoding="utf-8")
    )
    admission_id = next(
        event["operation_payload"]["admission_decision_id"]
        for event in attempt
        if event.get("operation") == "bind_admission"
    )
    admission = json.loads(
        _record_path(
            store, captured.evidence_space_id, "admission_decision", admission_id
        ).read_text(encoding="utf-8")
    )
    governance_path = _record_path(
        store,
        captured.evidence_space_id,
        "governance_event",
        admission["initial_governance_event_id_or_null"],
    )
    governance = json.loads(governance_path.read_text(encoding="utf-8"))
    grants = governance["operation_payload"]["initial_access_grants"]
    shared_grant = next(grant for grant in grants if grant["purpose"] == "shared_assessment_read")
    shared_grant["issued_by_principal_ref"]["principal_id"] = "tampered"
    _write_json(governance_path, governance)
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captured.evidence_space_id,
        source_event_ids=(source["source_event_id"],),
        assessment_pass_id="grant-authority-tamper",
        now=NOW,
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == ("shared_assessment_access_grant_invalid",)


def test_embedded_grant_must_equal_canonical_grant_record(store) -> None:
    captured = _capture(store)
    grant_dir = store.root / captured.evidence_space_id / "records" / "access_grant"
    grant_path = next(
        path
        for path in grant_dir.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8"))["purpose"]
        == "shared_assessment_read"
    )
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    grant["destination_class_constraint"] = "tampered"
    _write_json(grant_path, grant)
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captured.evidence_space_id,
        source_event_ids=(captured.source_event_id,),
        assessment_pass_id="standalone-grant-tamper",
        now=NOW,
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "shared_assessment_access_grant_record_mismatch",
    )


def test_operation_record_cannot_be_repointed_to_another_revision(store) -> None:
    _captures, bundle = _bundle(store)
    first = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="repoint-first",
        apply_enabled=True,
        now=NOW,
    )
    second = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(expected=1, text="revision two"),
        operation_idempotency_key="repoint-second",
        apply_enabled=True,
        now=NOW + timedelta(seconds=1),
    )
    assert first.status == second.status == "committed"
    operation_id = "asmop_" + __import__("hashlib").sha256(b"repoint-first").hexdigest()
    operation_path = _record_path(
        store, bundle.evidence_space_id, "shared_assessment_operation", operation_id
    )
    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    revision_two_id = "asmrev_" + __import__("hashlib").sha256(
        f"{ASSESSMENT_ID}\0{2}".encode("utf-8")
    ).hexdigest()
    operation["assessment_revision"] = 2
    operation["revision_record_id"] = revision_two_id
    operation["committed_at"] = (NOW + timedelta(seconds=1)).isoformat()
    _write_json(operation_path, operation)
    retry = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="repoint-first",
        apply_enabled=True,
        now=NOW + timedelta(seconds=2),
    )
    assert retry.status == "fail_closed"
    assert retry.blocked_reasons == (
        "shared_assessment_operation_result_crosslink_invalid",
    )


def test_temporal_monotonicity_and_naive_clocks_fail_closed(store) -> None:
    _captures, bundle = _bundle(store)
    naive_prepare = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=bundle.evidence_space_id,
        source_event_ids=tuple(ref.source_event_id for ref in bundle.evidence_refs),
        assessment_pass_id="naive-prepare",
        now=datetime(2026, 7, 22, 8, 0, 0),
    )
    assert naive_prepare.status == "fail_closed"
    first = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(),
        operation_idempotency_key="time-first",
        apply_enabled=True,
        now=NOW + timedelta(seconds=2),
    )
    assert first.status == "committed"
    backwards = commit_shared_assessment_revision(
        store=store,
        bundle=bundle,
        proposal=_proposal(expected=1, text="backwards"),
        operation_idempotency_key="time-backwards",
        apply_enabled=True,
        now=NOW + timedelta(seconds=1),
    )
    assert backwards.status == "fail_closed"
    assert backwards.blocked_reasons == (
        "shared_assessment_temporal_non_monotonic",
    )
    with store.transaction(bundle.evidence_space_id) as tx:
        naive_receipt = build_shared_assessment_formation_receipt(
            tx=tx,
            evidence_space_id=bundle.evidence_space_id,
            assessment_id=ASSESSMENT_ID,
            assessment_revision=1,
            decision_id="naive-decision",
            decision_input_digest=DECISION_INPUT_DIGEST,
            decided_at=datetime(2026, 7, 22, 8, 0, 0),
        )
    assert naive_receipt.status == "fail_closed"


def _capture_assistant_for_hardening(store, *, suffix: str):
    from relaylm.evidence.response_capture import (
        capture_managed_assistant_response_nonstream,
    )

    user = _capture(store, key=f"assistant-hardening-user-{suffix}")
    assistant = capture_managed_assistant_response_nonstream(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id=f"assistant-hardening-response-{suffix}",
        delivery_cohort_id=f"assistant-hardening-cohort-{suffix}",
        request_source_event_ids=(user.source_event_id,),
        assistant_visible_text="Canonical assistant output.",
        operation_idempotency_key=f"assistant-hardening-{suffix}",
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_assistant_response",
            issued_at=NOW.isoformat(),
        ),
        now=NOW,
    )
    return user, assistant


def test_assistant_response_binding_digest_is_required(store) -> None:
    user, assistant = _capture_assistant_for_hardening(store, suffix="binding")
    source_path = _record_path(
        store, user.evidence_space_id, "source_event", assistant.source_event_id
    )
    source = json.loads(source_path.read_text(encoding="utf-8"))
    binding_id = source["assistant_response_binding_ref_or_null"]
    binding_path = _record_path(
        store, user.evidence_space_id, "assistant_response_binding", binding_id
    )
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    binding["canonical_binding_digest"] = "f" * 64
    _write_json(binding_path, binding)
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=user.evidence_space_id,
        source_event_ids=(assistant.source_event_id,),
        assessment_pass_id="assistant-binding-tamper",
        now=NOW,
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "shared_assessment_assistant_response_binding_invalid",
    )


def test_assistant_finalization_artifact_is_exactly_bound(store) -> None:
    user, assistant = _capture_assistant_for_hardening(store, suffix="artifact")
    source = json.loads(
        _record_path(
            store, user.evidence_space_id, "source_event", assistant.source_event_id
        ).read_text(encoding="utf-8")
    )
    attempt = json.loads(
        _record_path(
            store,
            user.evidence_space_id,
            "capture_attempt",
            source["capture_attempt_id"],
        ).read_text(encoding="utf-8")
    ) if False else json.loads(
        (
            store.root
            / user.evidence_space_id
            / "logs"
            / "capture_attempt"
            / f"{source['capture_attempt_id']}.json"
        ).read_text(encoding="utf-8")
    )
    admission_id = next(
        event["operation_payload"]["admission_decision_id"]
        for event in attempt
        if event.get("operation") == "bind_admission"
    )
    admission = json.loads(
        _record_path(
            store, user.evidence_space_id, "admission_decision", admission_id
        ).read_text(encoding="utf-8")
    )
    validation = json.loads(
        _record_path(
            store,
            user.evidence_space_id,
            "validation_bundle",
            admission["validation_bundle_id_or_null"],
        ).read_text(encoding="utf-8")
    )
    gate_index = next(
        index
        for index, requirement in enumerate(validation["gate_requirements"])
        if requirement["gate_kind"] == "assistant_finalization"
    )
    derived_id = validation["active_artifact_refs"][gate_index]
    event_id = "artifactevent_" + derived_id.removeprefix("derivedartifact_")
    artifact_path = _record_path(
        store,
        user.evidence_space_id,
        "source_derived_artifact_event",
        event_id,
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["operation_payload"]["input_digest"] = "e" * 64
    _write_json(artifact_path, artifact)
    result = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=user.evidence_space_id,
        source_event_ids=(assistant.source_event_id,),
        assessment_pass_id="assistant-artifact-tamper",
        now=NOW,
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "shared_assessment_validation_artifacts_invalid",
    )
