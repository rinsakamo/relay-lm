"""SM-1 bounded Subjective MEM create runtime tests."""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from evidence_test_support import route_snapshot
from relaylm.config import RelayLMConfig
from relaylm.evidence.common import canonical_digest
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.evidence.user_input import capture_managed_user_input
from relaylm.shared_assessment.models import SharedAssessmentProposal, derive_shared_assessment_id
from relaylm.shared_assessment.runtime import (
    commit_shared_assessment_revision,
    prepare_shared_assessment_pass,
)
from relaylm.subjective_mem.models import (
    SubjectiveMemCreateProposal,
    SubjectiveMemFormationSnapshot,
    SubjectiveMemProposalBoundary,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
    resolve_subjective_mem_character_authority,
)
from relaylm.subjective_mem_runtime import (
    create_subjective_mem,
    resolve_subjective_mem_create_gate,
)

NOW = datetime(2026, 7, 23, 1, 0, 0, tzinfo=timezone.utc)
BASE_CONFIG = dict(
    backends={
        "local": {
            "type": "openai_compatible",
            "base_url": "http://127.0.0.1:8000/v1",
        }
    },
    model_routes={"relaylm-default": {"backend": "local", "mode": "memory_light"}},
    characters={
        "char1": {
            "soul": "examples/profiles/default/SOUL.md",
            "output_policy": "examples/profiles/default/style.md",
        },
        "char2": {
            "soul": "examples/profiles/default/SOUL.md",
            "output_policy": "examples/profiles/default/style.md",
        },
    },
)


CHARACTER_CONFIG = RelayLMConfig.model_validate(BASE_CONFIG)


@pytest.fixture()
def store(tmp_path: Path) -> EvidenceRecordStore:
    return EvidenceRecordStore(str(tmp_path / "evidence"))


def _asm_ready(store: EvidenceRecordStore):
    captured = capture_managed_user_input(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess-sm1",
        current_user_text="I felt relieved after the appointment.",
        fail_closed_reasons=(),
        operation_idempotency_key="sm1-source",
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_user_input",
            session_id="sess-sm1",
            issued_at=NOW.isoformat(),
        ),
        now=NOW,
    )
    assert captured.status == "admitted", captured
    prepared = prepare_shared_assessment_pass(
        store=store,
        evidence_space_id=captured.evidence_space_id,
        source_event_ids=(captured.source_event_id,),
        assessment_pass_id="sm1-assessment-pass",
        now=NOW,
    )
    assert prepared.status == "ready", prepared.blocked_reasons
    assert prepared.bundle is not None
    assessment_id = derive_shared_assessment_id(
        captured.evidence_space_id, "sm1-assessment"
    )
    committed = commit_shared_assessment_revision(
        store=store,
        bundle=prepared.bundle,
        proposal=SharedAssessmentProposal(
            assessment_id=assessment_id,
            supported_content="The user reported feeling relieved after the appointment.",
            support_state="supported",
            uncertainty=("appointment_type_unknown",),
            temporal_state="historical",
            governance_revision="shared-assessment-policy-v1",
            expected_current_revision_or_null=None,
        ),
        operation_idempotency_key="sm1-assessment-commit",
        apply_enabled=True,
        now=NOW,
    )
    assert committed.status == "committed", committed.blocked_reasons
    assert committed.revision is not None and committed.current_state is not None
    return captured, committed.revision, committed.current_state


def _proposal(*, meaning: str = "I remember this as a moment when the user felt safe again."):
    return SubjectiveMemCreateProposal(
        subjective_meaning=meaning,
        memory_kind="episodic",
        scope_binding=SubjectiveMemScopeBinding(),
        formation_snapshot=SubjectiveMemFormationSnapshot(
            soul_revision="soul-revision-opaque-1",
            memory_policy_revision="memory-policy-v1",
            boundary_revision="boundary-v1",
            scene_policy_revision_or_null=None,
            relationship_revision_or_null=None,
            formation_schema_version="subjective-mem-v1",
            model_revision="caller-proposal-model-v1",
        ),
        strength=SubjectiveMemStrength(
            grounded_confidence=0.8,
            subjective_conviction=0.7,
            salience="medium",
            reinforcement_count=0,
            strength_basis="subjective_interpretation",
        ),
        boundary=SubjectiveMemProposalBoundary(),
    )


def _character(character_id: str = "char1"):
    authority, reasons = resolve_subjective_mem_character_authority(
        CHARACTER_CONFIG,
        workspace_or_tenant_ref="relaylm-local",
        character_id=character_id,
    )
    assert authority is not None and not reasons
    return authority


def _create(store, captured, revision, state, **overrides):
    kwargs = dict(
        store=store,
        evidence_space_id=captured.evidence_space_id,
        character_config=CHARACTER_CONFIG,
        character_authority=_character(),
        assessment_revision=revision,
        assessment_current_state=state,
        proposal=_proposal(),
        operation_idempotency_key="sm1-create-operation",
        apply_enabled=True,
        decided_at=NOW,
        observed_at=NOW,
    )
    kwargs.update(overrides)
    return create_subjective_mem(**kwargs)


def test_create_commits_exact_bidirectional_prepared_result(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    result = _create(store, captured, assessment_revision, assessment_state)
    assert result.status == "committed", result.blocked_reasons
    assert result.persisted is True
    assert all(
        item is not None
        for item in (
            result.decision,
            result.revision,
            result.current_state,
            result.prepared_manifest,
            result.formation_receipt,
        )
    )
    decision = result.decision
    revision = result.revision
    state = result.current_state
    manifest = result.prepared_manifest
    receipt = result.formation_receipt
    assert decision is not None and revision is not None and state is not None
    assert manifest is not None and receipt is not None
    assert decision.result_memory_id == revision.memory_id
    assert revision.decision_id == decision.decision_id
    assert receipt.decision_id == decision.decision_id
    assert state.memory_id == revision.memory_id
    assert state.to_dict()["mutation_state"] == "prepared"
    assert state.to_dict()["retrieval_eligible"] is False
    assert revision.to_dict()["retrieval_visible"] is True
    assert revision.grounded_content == assessment_revision.supported_content
    assert revision.grounded_content_digest == assessment_revision.supported_content_digest
    assert manifest.to_dict()["canonical_markdown_published"] is False
    assert manifest.to_dict()["commit_receipt_present"] is False
    assert list(store.root.rglob("*.md")) == []


def test_target_schema_accepts_decision_revision_and_current_state(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    result = _create(store, captured, assessment_revision, assessment_state)
    assert result.decision and result.revision and result.current_state
    schema = json.loads(
        Path(
            "docs/contracts/schemas/subjective-mem-v1/relaylm-subjective-mem-v1.schema.json"
        ).read_text()
    )
    Draft202012Validator(schema).validate(
        {
            "records": [
                result.decision.to_dict(),
                result.revision.to_dict(),
                result.current_state.to_dict(),
            ]
        }
    )


def test_same_input_retry_is_exact_and_changed_input_conflicts(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    first = _create(store, captured, assessment_revision, assessment_state)
    retry = _create(store, captured, assessment_revision, assessment_state)
    assert first.status == "committed"
    assert retry.status == "duplicate_existing"
    assert retry.decision == first.decision
    assert retry.revision == first.revision
    assert retry.current_state == first.current_state
    conflict = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        proposal=_proposal(meaning="A different subjective interpretation."),
    )
    assert conflict.status == "integrity_conflict"
    assert conflict.blocked_reasons == (
        "subjective_mem_operation_idempotency_conflict",
    )


def test_retry_rejects_operation_bundle_redirection(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    first = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="redirect-source",
    )
    second = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="redirect-target",
    )
    assert first.status == second.status == "committed"
    assert first.decision is not None and second.decision is not None

    operation_paths = list(
        (
            store.root
            / captured.evidence_space_id
            / "records"
            / "subjective_mem_operation"
        ).glob("*.json")
    )
    operations = {
        json.loads(path.read_text())["decision_id"]: path
        for path in operation_paths
    }
    source_path = operations[first.decision.decision_id]
    target_path = operations[second.decision.decision_id]
    source = json.loads(source_path.read_text())
    target = json.loads(target_path.read_text())
    for key in (
        "decision_id",
        "receipt_id",
        "memory_id",
        "prepared_revision_record_id",
        "prepared_revision_digest",
        "prepared_manifest_id",
        "prepared_manifest_digest",
        "current_state_key",
    ):
        source[key] = target[key]
    source_path.write_text(json.dumps(source), encoding="utf-8")

    retry = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="redirect-source",
    )
    assert retry.status == "fail_closed"
    assert retry.blocked_reasons == (
        "subjective_mem_operation_result_identity_invalid",
    )


def test_retry_rejects_coordinated_prepared_body_rewrite(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    first = _create(store, captured, assessment_revision, assessment_state)
    assert first.status == "committed"
    assert first.decision and first.prepared_manifest

    space = store.root / captured.evidence_space_id
    operation_path = next(
        (space / "records" / "subjective_mem_operation").glob("*.json")
    )
    operation = json.loads(operation_path.read_text())
    revision_path = (
        space
        / "records"
        / "subjective_mem_prepared_revision"
        / f"{operation['prepared_revision_record_id']}.json"
    )
    revision = json.loads(revision_path.read_text())
    revision["subjective_meaning"] = "Coordinated but unauthorized rewrite."
    revision_path.write_text(json.dumps(revision), encoding="utf-8")
    revision_digest = canonical_digest(revision)

    manifest_path = (
        space
        / "records"
        / "subjective_mem_prepared_manifest"
        / f"{operation['prepared_manifest_id']}.json"
    )
    manifest = json.loads(manifest_path.read_text())
    manifest["prepared_revision_digest"] = revision_digest
    manifest_body = {
        key: value for key, value in manifest.items() if key != "manifest_digest"
    }
    manifest["manifest_digest"] = canonical_digest(manifest_body)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    operation["prepared_revision_digest"] = revision_digest
    operation["prepared_manifest_digest"] = manifest["manifest_digest"]
    operation_path.write_text(json.dumps(operation), encoding="utf-8")

    retry = _create(store, captured, assessment_revision, assessment_state)
    assert retry.status == "fail_closed"
    assert retry.blocked_reasons == (
        "subjective_mem_operation_result_input_mismatch",
    )


def test_dry_run_returns_prepared_result_without_persistence(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    result = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        apply_enabled=False,
        operation_idempotency_key="sm1-dry-run",
    )
    assert result.status == "dry_run_ready"
    assert result.persisted is False
    space = store.root / captured.evidence_space_id
    assert not (space / "records" / "subjective_mem_operation").exists()
    assert not (space / "records" / "subjective_mem_decision").exists()
    assert not (
        space / "records" / "shared_assessment_formation_receipt"
    ).exists()
    assert not (
        space / "records" / "subjective_mem_prepared_revision"
    ).exists()
    assert not (
        space / "records" / "subjective_mem_prepared_manifest"
    ).exists()
    assert not (space / "logs" / "subjective_mem_current_state").exists()


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"outcome": "reinforce"}, "subjective_mem_outcome_unsupported"),
        ({"candidate_memory_refs": (object(),)}, "subjective_mem_candidate_memory_refs_unsupported"),
        ({"similarity_granted_authority": True}, "subjective_mem_similarity_authority_forbidden"),
        ({"target_memory_ref_or_null": object()}, "subjective_mem_create_target_memory_forbidden"),
        ({"result_relation_id_or_null": "rel-1"}, "subjective_mem_create_relation_forbidden"),
        ({"hold_reason_or_null": "hold"}, "subjective_mem_create_hold_reason_forbidden"),
    ],
)
def test_non_create_shapes_fail_closed(store, overrides, reason) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    result = _create(store, captured, assessment_revision, assessment_state, **overrides)
    assert result.status == "fail_closed"
    assert reason in result.blocked_reasons


def test_unsupported_scope_and_strength_fail_closed(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    unsupported_scope = replace(
        _proposal(),
        scope_binding=SubjectiveMemScopeBinding(
            scope_kind="participant",
            participant_id_or_null="participant-1",
            audience_class="trusted_participant",
        ),
    )
    scope_result = _create(
        store, captured, assessment_revision, assessment_state, proposal=unsupported_scope
    )
    assert scope_result.status == "fail_closed"
    assert "subjective_mem_scope_unsupported" in scope_result.blocked_reasons

    invalid_strength = replace(
        _proposal(),
        strength=SubjectiveMemStrength(
            grounded_confidence=1.1,
            subjective_conviction=0.5,
            salience="medium",
            reinforcement_count=1,
            strength_basis="subjective_interpretation",
        ),
    )
    strength_result = _create(
        store, captured, assessment_revision, assessment_state, proposal=invalid_strength
    )
    assert strength_result.status == "fail_closed"
    assert "subjective_mem_strength_invalid" in strength_result.blocked_reasons


def test_exact_assessment_input_and_monotonic_time_are_required(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    altered_revision = replace(
        assessment_revision,
        supported_content="Altered grounded content.",
    )
    altered = _create(
        store,
        captured,
        altered_revision,
        assessment_state,
        operation_idempotency_key="altered-assessment",
    )
    assert altered.status == "fail_closed"
    assert altered.blocked_reasons == (
        "subjective_mem_assessment_revision_not_exact_stored",
    )

    backwards = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="backwards-time",
        decided_at=NOW - timedelta(seconds=1),
    )
    assert backwards.status == "fail_closed"
    assert "shared_assessment_temporal_non_monotonic" in backwards.blocked_reasons


def test_same_raw_operation_key_is_scoped_per_character(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    first = _create(store, captured, assessment_revision, assessment_state)
    cross = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        character_authority=_character("char2"),
    )
    assert first.status == cross.status == "committed"
    assert first.decision is not None and cross.decision is not None
    assert first.revision is not None and cross.revision is not None
    assert first.decision.decision_id != cross.decision.decision_id
    assert first.revision.memory_id != cross.revision.memory_id


def test_corrupt_prepared_revision_blocks_retry(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    first = _create(store, captured, assessment_revision, assessment_state)
    assert first.status == "committed" and first.prepared_manifest is not None
    record_id = first.prepared_manifest.prepared_revision_record_id
    path = (
        store.root
        / captured.evidence_space_id
        / "records"
        / "subjective_mem_prepared_revision"
        / f"{record_id}.json"
    )
    payload = json.loads(path.read_text())
    payload["grounded_content_digest"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    retry = _create(store, captured, assessment_revision, assessment_state)
    assert retry.status == "fail_closed"
    assert retry.blocked_reasons == ("subjective_mem_operation_result_corrupt",)


def test_public_diagnostics_are_content_free(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    result = _create(store, captured, assessment_revision, assessment_state)
    projected = json.dumps(result.to_log_dict(), ensure_ascii=False, sort_keys=True)
    assert result.revision is not None
    assert result.revision.grounded_content not in projected
    assert result.revision.subjective_meaning not in projected
    assert "sm1-create-operation" not in projected
    assert str(store.root) not in projected
    assert result.to_log_dict()["content_free"] is True


def test_default_off_and_config_gate_require_asm_apply(tmp_path: Path) -> None:
    default = RelayLMConfig.model_validate(BASE_CONFIG)
    gate = resolve_subjective_mem_create_gate(default)
    assert gate.enabled is False and gate.store is None

    root = str((tmp_path / "evidence").resolve())
    dry = RelayLMConfig.model_validate(
        {
            **BASE_CONFIG,
            "evidence_data_root": root,
            "shared_assessment_enabled": True,
            "shared_assessment_dry_run_only": True,
            "shared_assessment_apply_enabled": False,
            "subjective_mem_create_enabled": True,
            "subjective_mem_create_dry_run_only": True,
            "subjective_mem_create_apply_enabled": False,
        }
    )
    dry_gate = resolve_subjective_mem_create_gate(dry)
    assert dry_gate.enabled is True and dry_gate.apply_enabled is False
    assert dry_gate.store is not None

    with pytest.raises(ValidationError):
        RelayLMConfig.model_validate(
            {
                **BASE_CONFIG,
                "evidence_data_root": root,
                "shared_assessment_enabled": True,
                "shared_assessment_dry_run_only": True,
                "shared_assessment_apply_enabled": False,
                "subjective_mem_create_enabled": True,
                "subjective_mem_create_dry_run_only": False,
                "subjective_mem_create_apply_enabled": True,
            }
        )


def test_character_authority_resolution_and_workspace_fence(store) -> None:
    authority, reasons = resolve_subjective_mem_character_authority(
        CHARACTER_CONFIG,
        workspace_or_tenant_ref="relaylm-local",
        character_id="char1",
    )
    assert authority is not None and reasons == ()
    assert authority.character_id == "char1"
    assert authority.authority_revision.startswith("charauth_")

    changed_path_config = RelayLMConfig.model_validate(
        {
            **BASE_CONFIG,
            "characters": {
                **BASE_CONFIG["characters"],
                "char1": {
                    **BASE_CONFIG["characters"]["char1"],
                    "soul": "another/non-identity/SOUL.md",
                },
            },
        }
    )
    same_identity, same_identity_reasons = (
        resolve_subjective_mem_character_authority(
            changed_path_config,
            workspace_or_tenant_ref="relaylm-local",
            character_id="char1",
        )
    )
    assert same_identity_reasons == ()
    assert same_identity == authority

    missing, missing_reasons = resolve_subjective_mem_character_authority(
        CHARACTER_CONFIG,
        workspace_or_tenant_ref="relaylm-local",
        character_id="display-name-not-an-id",
    )
    assert missing is None
    assert missing_reasons == ("subjective_mem_character_unknown",)

    captured, assessment_revision, assessment_state = _asm_ready(store)
    wrong_workspace = replace(authority, workspace_or_tenant_ref="other-workspace")
    result = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        character_authority=wrong_workspace,
        operation_idempotency_key="wrong-workspace",
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "subjective_mem_character_authority_not_exact_current",
    )


def test_proposal_boundary_and_future_decision_time_fail_closed(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    product_proposal = replace(
        _proposal(),
        boundary=replace(
            SubjectiveMemProposalBoundary(), product_knowledge_excluded=False
        ),
    )
    product = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        proposal=product_proposal,
        operation_idempotency_key="product-knowledge",
    )
    assert product.status == "fail_closed"
    assert "subjective_mem_proposal_boundary_unattested" in product.blocked_reasons

    future = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="future-time",
        decided_at=NOW + timedelta(seconds=1),
        observed_at=NOW,
    )
    assert future.status == "fail_closed"
    assert future.blocked_reasons == ("subjective_mem_decision_time_in_future",)


def test_restricted_or_stale_assessment_selector_fails_closed(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    restricted = replace(
        assessment_state,
        lifecycle_state="restricted",
        authorization_state="restricted",
    )
    blocked = _create(
        store,
        captured,
        assessment_revision,
        restricted,
        operation_idempotency_key="restricted-assessment",
    )
    assert blocked.status == "fail_closed"
    assert "subjective_mem_assessment_not_exact_current_admitted" in blocked.blocked_reasons

    stale = replace(
        assessment_state,
        updated_at=(NOW + timedelta(seconds=1)).isoformat(),
    )
    stale_result = _create(
        store,
        captured,
        assessment_revision,
        stale,
        operation_idempotency_key="stale-selector",
        decided_at=NOW + timedelta(seconds=1),
        observed_at=NOW + timedelta(seconds=1),
    )
    assert stale_result.status == "fail_closed"
    assert stale_result.blocked_reasons == (
        "subjective_mem_assessment_current_state_not_exact_stored",
    )


def test_changed_time_or_authority_under_same_key_is_conflict(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    first = _create(store, captured, assessment_revision, assessment_state)
    assert first.status == "committed"

    changed_time = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        decided_at=NOW + timedelta(seconds=1),
        observed_at=NOW + timedelta(seconds=1),
    )
    assert changed_time.status == "integrity_conflict"

    changed_authority = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        character_authority=replace(
            _character(), authority_revision="charauth_changed"
        ),
    )
    assert changed_authority.status == "fail_closed"
    assert changed_authority.blocked_reasons == (
        "subjective_mem_character_authority_not_exact_current",
    )


@pytest.mark.parametrize(
    "case",
    [
        "decision_missing_result",
        "decision_result_revision_two",
        "decision_relation_result",
        "decision_hold_reason",
        "decision_similarity_authority",
        "revision_revision_two",
        "revision_predecessor",
        "revision_wrong_authority",
        "revision_wrong_character",
        "revision_wrong_scope",
        "revision_wrong_assessment",
        "revision_wrong_grounded_digest",
        "revision_secondary",
        "revision_bad_kind",
        "revision_bad_strength",
        "current_wrong_revision",
        "current_retrieval_eligible",
        "current_not_prepared",
        "duplicate_current_state",
        "receipt_wrong_decision",
    ],
)
def test_corrupt_persisted_decision_result_bundle_blocks_retry(store, case) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    first = _create(store, captured, assessment_revision, assessment_state)
    assert first.status == "committed"
    assert first.decision and first.prepared_manifest and first.formation_receipt

    space = store.root / captured.evidence_space_id
    decision_path = (
        space
        / "records"
        / "subjective_mem_decision"
        / f"{first.decision.decision_id}.json"
    )
    revision_path = (
        space
        / "records"
        / "subjective_mem_prepared_revision"
        / f"{first.prepared_manifest.prepared_revision_record_id}.json"
    )
    receipt_path = (
        space
        / "records"
        / "shared_assessment_formation_receipt"
        / f"{first.formation_receipt.receipt_id}.json"
    )
    current_paths = list(
        (space / "logs" / "subjective_mem_current_state").glob("*.json")
    )
    assert len(current_paths) == 1
    current_path = current_paths[0]

    if case.startswith("decision_"):
        payload = json.loads(decision_path.read_text())
        if case == "decision_missing_result":
            payload["result_memory_ref_or_null"] = None
        elif case == "decision_result_revision_two":
            payload["result_memory_ref_or_null"]["memory_revision"] = 2
        elif case == "decision_relation_result":
            payload["result_relation_id_or_null"] = "rel_corrupt"
        elif case == "decision_hold_reason":
            payload["hold_reason_or_null"] = "corrupt"
        elif case == "decision_similarity_authority":
            payload["similarity_granted_authority"] = True
        decision_path.write_text(json.dumps(payload), encoding="utf-8")
    elif case.startswith("revision_"):
        payload = json.loads(revision_path.read_text())
        if case == "revision_revision_two":
            payload["memory_revision"] = 2
        elif case == "revision_predecessor":
            payload["predecessor_revision_or_null"] = 1
        elif case == "revision_wrong_authority":
            payload["authorization_ref"]["authority_id"] = "smdec_wrong"
        elif case == "revision_wrong_character":
            payload["character_id"] = "char2"
        elif case == "revision_wrong_scope":
            payload["scope_binding"]["scope_kind"] = "participant"
            payload["scope_binding"]["participant_id_or_null"] = "participant-1"
            payload["scope_binding"]["audience_class"] = "trusted_participant"
        elif case == "revision_wrong_assessment":
            payload["grounded_assessment_ref"]["assessment_id"] = "asm_wrong"
        elif case == "revision_wrong_grounded_digest":
            payload["grounded_content_digest"] = "0" * 64
        elif case == "revision_secondary":
            payload["formation_stage"] = "secondary"
        elif case == "revision_bad_kind":
            payload["memory_kind"] = "invalid"
        elif case == "revision_bad_strength":
            payload["strength"]["grounded_confidence"] = 2.0
        revision_path.write_text(json.dumps(payload), encoding="utf-8")
    elif case.startswith("current_") or case == "duplicate_current_state":
        payload = json.loads(current_path.read_text())
        if case == "current_wrong_revision":
            payload[0]["current_revision"] = 2
        elif case == "current_retrieval_eligible":
            payload[0]["retrieval_eligible"] = True
        elif case == "current_not_prepared":
            payload[0]["mutation_state"] = "none"
        elif case == "duplicate_current_state":
            payload.append(dict(payload[0], memory_state_id="smstate_duplicate"))
        current_path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        payload = json.loads(receipt_path.read_text())
        payload["decision_id"] = "smdec_wrong"
        receipt_path.write_text(json.dumps(payload), encoding="utf-8")

    retry = _create(store, captured, assessment_revision, assessment_state)
    assert retry.status == "fail_closed"
    assert retry.blocked_reasons[0].startswith("subjective_mem_operation_")


def test_atomic_transaction_contains_complete_prepared_set_and_is_content_free(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    result = _create(store, captured, assessment_revision, assessment_state)
    assert result.status == "committed"
    space = store.root / captured.evidence_space_id
    journals = [
        json.loads(path.read_text())
        for path in (space / "transactions").glob("*.json")
    ]
    sm1 = [
        item
        for item in journals
        if any(
            write.get("category") == "subjective_mem_operation"
            for write in item.get("writes", [])
        )
    ]
    assert len(sm1) == 1
    assert sm1[0]["state"] == "committed"
    categories = {
        (write["kind"], write["category"])
        for write in sm1[0]["writes"]
    }
    assert categories == {
        ("record", "shared_assessment_formation_receipt"),
        ("record", "subjective_mem_decision"),
        ("record", "subjective_mem_prepared_revision"),
        ("record", "subjective_mem_prepared_manifest"),
        ("record", "subjective_mem_operation"),
        ("log", "subjective_mem_current_state"),
    }
    operation_files = list(
        (space / "records" / "subjective_mem_operation").glob("*.json")
    )
    assert len(operation_files) == 1
    operation_text = operation_files[0].read_text()
    assert assessment_revision.supported_content not in operation_text
    assert _proposal().subjective_meaning not in operation_text
    assert "sm1-create-operation" not in operation_text


def test_commit_failure_exposes_no_prepared_result(store, monkeypatch) -> None:
    from relaylm.evidence.store import EvidenceStoreResult, EvidenceStoreTransaction

    captured, assessment_revision, assessment_state = _asm_ready(store)

    def fail_commit(self, **kwargs):
        return EvidenceStoreResult("failed", ("test_injected_commit_failure",))

    monkeypatch.setattr(EvidenceStoreTransaction, "commit", fail_commit)
    result = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="injected-failure",
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == ("test_injected_commit_failure",)
    space = store.root / captured.evidence_space_id
    assert not (space / "records" / "subjective_mem_operation").exists()
    assert not (space / "records" / "subjective_mem_decision").exists()
    assert not (space / "logs" / "subjective_mem_current_state").exists()


def test_mid_commit_failure_recovers_one_exact_prepared_result(
    store, monkeypatch
) -> None:
    from relaylm.evidence.store import EvidenceStoreResult

    captured, assessment_revision, assessment_state = _asm_ready(store)
    original_apply = EvidenceRecordStore._apply_transaction_writes_unlocked
    injected = False

    def fail_after_two_writes(self, evidence_space_id, writes):
        nonlocal injected
        is_sm1 = any(
            item.category == "subjective_mem_operation" for item in writes
        )
        if is_sm1 and not injected:
            injected = True
            partial = original_apply(self, evidence_space_id, writes[:2])
            assert partial.status in {"created", "duplicate_existing"}
            return EvidenceStoreResult(
                "failed", ("test_injected_mid_commit_failure",)
            )
        return original_apply(self, evidence_space_id, writes)

    monkeypatch.setattr(
        EvidenceRecordStore,
        "_apply_transaction_writes_unlocked",
        fail_after_two_writes,
    )
    failed = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="mid-commit-failure",
    )
    assert failed.status == "fail_closed"
    assert failed.persisted is False
    assert failed.blocked_reasons == ("test_injected_mid_commit_failure",)

    space = store.root / captured.evidence_space_id
    sm1_journals = []
    for path in (space / "transactions").glob("*.json"):
        payload = json.loads(path.read_text())
        if any(
            write.get("category") == "subjective_mem_operation"
            for write in payload.get("writes", [])
        ):
            sm1_journals.append(payload)
    assert len(sm1_journals) == 1
    assert sm1_journals[0]["state"] == "prepared"
    assert not (space / "records" / "subjective_mem_operation").exists()
    assert not (space / "logs" / "subjective_mem_current_state").exists()

    reopened = EvidenceRecordStore(str(store.root))
    recovered = _create(
        reopened,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="mid-commit-failure",
    )
    assert recovered.status == "duplicate_existing"
    assert recovered.persisted is True
    final_journals = []
    for path in (space / "transactions").glob("*.json"):
        payload = json.loads(path.read_text())
        if any(
            write.get("category") == "subjective_mem_operation"
            for write in payload.get("writes", [])
        ):
            final_journals.append(payload)
    assert len(final_journals) == 1
    final_journal = final_journals[0]
    assert final_journal["state"] == "committed"


def test_restart_reopens_exact_prepared_idempotency_result(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    first = _create(store, captured, assessment_revision, assessment_state)
    assert first.status == "committed"
    reopened = EvidenceRecordStore(str(store.root))
    retry = _create(reopened, captured, assessment_revision, assessment_state)
    assert retry.status == "duplicate_existing"
    assert retry.decision == first.decision
    assert retry.revision == first.revision
    assert retry.current_state == first.current_state


def test_symlinked_root_is_not_resolved_for_apply(tmp_path: Path) -> None:
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    class Config:
        subjective_mem_create_enabled = True
        subjective_mem_create_dry_run_only = False
        subjective_mem_create_apply_enabled = True
        evidence_data_root = str(link)

    gate = resolve_subjective_mem_create_gate(Config())
    assert gate.enabled is True
    assert gate.apply_enabled is False
    assert gate.store is None


def test_sm1_has_no_normal_path_soul_slp_retrieval_or_primary_mem_wiring() -> None:
    runtime_source = Path("relaylm/subjective_mem_runtime.py").read_text()
    forbidden_imports = (
        "relaylm.soul",
        "relaylm.relaysoul",
        "relaylm.relaymem_slp",
        "relaylm.retrieval",
        "relaylm.memory_store",
    )
    assert all(name not in runtime_source for name in forbidden_imports)
    for path in Path("relaylm").glob("*.py"):
        if path.name in {
            "subjective_mem.py",
            "subjective_mem_runtime.py",
            "subjective_mem_commit.py",
            "subjective_mem_commit_runtime.py",
            "subjective_mem_markdown.py",
            "_subjective_mem_commit_io.py",
        }:
            continue
        assert "from relaylm.subjective_mem_runtime" not in path.read_text()
        assert "import relaylm.subjective_mem_runtime" not in path.read_text()



def test_foreign_current_state_key_blocks_new_apply(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    dry = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        apply_enabled=False,
        operation_idempotency_key="foreign-state-before-apply",
    )
    assert dry.status == "dry_run_ready"
    assert dry.current_state is not None
    foreign_key = "smstate_foreign_before_apply"
    foreign = {
        **dry.current_state.to_dict(),
        "memory_state_id": foreign_key,
    }
    written = store.write_log(
        evidence_space_id=captured.evidence_space_id,
        log_kind="subjective_mem_current_state",
        key=foreign_key,
        events=(foreign,),
    )
    assert written.status == "created"

    blocked = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="foreign-state-before-apply",
    )
    assert blocked.status == "integrity_conflict"
    assert blocked.blocked_reasons == (
        "subjective_mem_duplicate_logical_current_state",
    )
    space = store.root / captured.evidence_space_id
    assert not (space / "records" / "subjective_mem_operation").exists()


def test_foreign_current_state_key_blocks_retry(store) -> None:
    captured, assessment_revision, assessment_state = _asm_ready(store)
    first = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="foreign-state-after-apply",
    )
    assert first.status == "committed"
    assert first.current_state is not None
    foreign_key = "smstate_foreign_after_apply"
    foreign = {
        **first.current_state.to_dict(),
        "memory_state_id": foreign_key,
    }
    written = store.write_log(
        evidence_space_id=captured.evidence_space_id,
        log_kind="subjective_mem_current_state",
        key=foreign_key,
        events=(foreign,),
    )
    assert written.status == "created"

    retry = _create(
        store,
        captured,
        assessment_revision,
        assessment_state,
        operation_idempotency_key="foreign-state-after-apply",
    )
    assert retry.status == "fail_closed"
    assert retry.blocked_reasons == (
        "subjective_mem_duplicate_logical_current_state",
    )
