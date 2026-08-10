"""Shared Subjective MEM lifecycle predecessor authority tests."""
from __future__ import annotations

from dataclasses import replace
import inspect

from relaylm.subjective_mem.commit_io import PLATFORM_REVISION
from relaylm.evidence.common import canonical_digest
from relaylm.evidence.space import (
    build_bootstrap_evidence_space_descriptor,
    derive_evidence_space_id,
)
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemFormationSnapshot,
    SubjectiveMemRevision,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
)
from relaylm.subjective_mem.commit import ST1_RECEIPT_SCHEMA
from relaylm.subjective_mem_consolidate import (
    CONSOLIDATE_AUTHORIZATION_CLASS,
    CONSOLIDATE_OPERATION_FAMILY,
    CONSOLIDATE_POLICY_REVISION,
    CONSOLIDATE_REASON_CATEGORY,
)
from relaylm.subjective_mem.lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
)
import relaylm.subjective_mem.lifecycle_authority as authority_module
from relaylm.subjective_mem.lifecycle_authority import (
    SubjectiveMemPredecessorExpectation,
    load_subjective_mem_predecessor_authority_locked,
    subjective_mem_committed_authorization_ref,
    validate_subjective_mem_committed_authorization,
    validate_subjective_mem_committed_receipt,
)
from relaylm.subjective_mem.markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
)

SPACE = derive_evidence_space_id(
    workspace_or_tenant_ref="workspace-1",
    character_id="char-1",
    memory_namespace="subjective",
    session_id="session-1",
)
CHARACTER = SubjectiveMemCharacterAuthority(
    workspace_or_tenant_ref="workspace-1",
    character_id="char-1",
    authority_revision="authority-v1",
)
PAGE_DIGEST = "sha256:" + "a" * 64
STATE_DIGEST = "b" * 64
AT = "2026-07-26T01:00:00+00:00"


class _Transaction:
    def __init__(self, records: dict[tuple[str, str], dict[str, object]]) -> None:
        self.records = records

    def read_record(
        self, *, record_kind: str, record_id: str
    ) -> dict[str, object] | None:
        return self.records.get((record_kind, record_id))


def _descriptor() -> dict[str, object]:
    descriptor, reasons = build_bootstrap_evidence_space_descriptor(
        workspace_or_tenant_ref=CHARACTER.workspace_or_tenant_ref,
        character_id=CHARACTER.character_id,
        memory_namespace="subjective",
        session_id="session-1",
        created_at=AT,
    )
    assert descriptor is not None, reasons
    assert descriptor.evidence_space_id == SPACE
    return descriptor.to_dict()


def _revision(
    *,
    operation: str,
    lifecycle_state: str,
    revision: int = 2,
    formation_stage: str = "primary",
) -> SubjectiveMemRevision:
    return SubjectiveMemRevision(
        memory_id="memory-1",
        character_id=CHARACTER.character_id,
        assessment_id="assessment-1",
        assessment_revision=1,
        grounded_content="grounded",
        grounded_content_digest="c" * 64,
        subjective_meaning="meaning",
        memory_kind="episodic",
        scope_binding=SubjectiveMemScopeBinding(),
        formation_snapshot=SubjectiveMemFormationSnapshot(
            soul_revision="soul-v1",
            memory_policy_revision="memory-policy-v1",
            boundary_revision="boundary-v1",
            scene_policy_revision_or_null=None,
            relationship_revision_or_null=None,
            formation_schema_version="formation-v1",
            model_revision="model-v1",
        ),
        strength=SubjectiveMemStrength(
            grounded_confidence=1.0,
            subjective_conviction=0.8,
            salience="medium",
            reinforcement_count=1,
            strength_basis="assessment_support",
        ),
        decision_id=f"{operation}-transition-1",
        created_at=AT,
        memory_revision=revision,
        formation_stage=formation_stage,
        lifecycle_state=lifecycle_state,
        retrieval_visible=lifecycle_state in {"active", "pinned"},
        predecessor_revision_or_null=revision - 1,
        authorization_kind="lifecycle_transition",
    )


def _expectation(receipt: dict[str, object]) -> SubjectiveMemPredecessorExpectation:
    return SubjectiveMemPredecessorExpectation(
        receipt_id=str(receipt["receipt_id"]),
        receipt_digest=str(receipt["receipt_digest"]),
        current_state_digest=STATE_DIGEST,
        page_id="page-1",
        block_id="block-2",
        page_digest=PAGE_DIGEST,
        revision_schema=SUBJECTIVE_MEM_REVISION_SCHEMA,
        page_schema=PAGE_SCHEMA,
        block_schema=LIFECYCLE_BLOCK_SCHEMA,
        renderer_revision=RENDERER_REVISION,
        partition_revision=PAGE_PARTITION_REVISION,
        platform_revision=PLATFORM_REVISION,
    )


def _lifecycle_records(
    *,
    operation: str,
    from_state: str,
    to_state: str,
    from_stage: str = "primary",
    to_stage: str | None = None,
    authorization_class: str = "user_management",
    reason_category: str | None = None,
    policy_revision: str = LIFECYCLE_POLICY_REVISION,
) -> tuple[
    SubjectiveMemRevision,
    dict[tuple[str, str], dict[str, object]],
    SubjectiveMemPredecessorExpectation,
]:
    to_stage = to_stage or from_stage
    revision = _revision(
        operation=operation, lifecycle_state=to_state, formation_stage=to_stage
    )
    transition = {
        "schema": LIFECYCLE_TRANSITION_SCHEMA,
        "transition_id": revision.authorization_id,
        "character_id": revision.character_id,
        "memory_id": revision.memory_id,
        "from_revision": revision.memory_revision - 1,
        "to_revision": revision.memory_revision,
        "operation": operation,
        "from_lifecycle_state": from_state,
        "to_lifecycle_state": to_state,
        "from_formation_stage": from_stage,
        "to_formation_stage": to_stage,
        "authorized_by": authorization_class,
        "committed_at": AT,
    }
    receipt_body = {
        "schema": LIFECYCLE_RECEIPT_SCHEMA,
        "receipt_id": f"{operation}-receipt-1",
        "intent_id": f"{operation}-intent-1",
        "intent_digest": "d" * 64,
        "operation_id": f"{operation}-operation-1",
        "operation_kind": operation,
        "operation_outcome": "committed",
        "input_digest": "e" * 64,
        "evidence_space_id": SPACE,
        "character_id": CHARACTER.character_id,
        "memory_ref": {
            "memory_id": revision.memory_id,
            "memory_revision": revision.memory_revision,
        },
        "predecessor_revision": revision.memory_revision - 1,
        "transition_id": revision.authorization_id,
        "authorization_class": authorization_class,
        "authorization_id": "authorization-1",
        "reason_category": reason_category or f"user_requested_{operation}",
        "policy_revision": policy_revision,
        "revision_schema": SUBJECTIVE_MEM_REVISION_SCHEMA,
        "page_schema": PAGE_SCHEMA,
        "block_schema": LIFECYCLE_BLOCK_SCHEMA,
        "renderer_revision": RENDERER_REVISION,
        "partition_revision": PAGE_PARTITION_REVISION,
        "platform_revision": PLATFORM_REVISION,
        "page_id": "page-1",
        "successor_block_id": "block-2",
        "pre_image_digest": "sha256:" + "f" * 64,
        "post_image_digest": PAGE_DIGEST,
        "successor_revision_digest": canonical_digest(revision.to_dict()),
        "current_state_digest": STATE_DIGEST,
        "projection_state": "rebuild_required",
        "ordinary_retrieval_wired": False,
        "finalized_at": AT,
    }
    receipt = {
        **receipt_body,
        "receipt_digest": canonical_digest(receipt_body),
    }
    records = {
        ("evidence_space_descriptor", "revision-1"): _descriptor(),
        ("subjective_mem_lifecycle_receipt", str(receipt["receipt_id"])): receipt,
        ("subjective_mem_lifecycle_transition", revision.authorization_id): transition,
    }
    return revision, records, _expectation(receipt)


def _load(
    revision: SubjectiveMemRevision,
    records: dict[tuple[str, str], dict[str, object]],
    expectation: SubjectiveMemPredecessorExpectation,
):
    return load_subjective_mem_predecessor_authority_locked(
        tx=_Transaction(records),  # type: ignore[arg-type]
        evidence_space_id=SPACE,
        character_authority=CHARACTER,
        predecessor=revision,
        expectation=expectation,
    )


def test_forget_hidden_predecessor_is_exact_authority() -> None:
    revision, records, expectation = _lifecycle_records(
        operation="forget",
        from_state="active",
        to_state="hidden",
    )
    authority, reasons = _load(revision, records, expectation)
    assert authority is not None, reasons
    assert authority.receipt["operation_kind"] == "forget"
    assert len(authority.record_bindings) == 3


def test_restore_active_predecessor_is_accepted_for_later_operations() -> None:
    revision, records, expectation = _lifecycle_records(
        operation="restore",
        from_state="hidden",
        to_state="active",
    )
    authority, reasons = _load(revision, records, expectation)
    assert authority is not None, reasons
    assert authority.authorization_record["operation"] == "restore"


def test_operation_and_lifecycle_direction_must_match() -> None:
    revision, records, expectation = _lifecycle_records(
        operation="forget",
        from_state="active",
        to_state="hidden",
    )
    receipt_key = ("subjective_mem_lifecycle_receipt", expectation.receipt_id)
    receipt = dict(records[receipt_key])
    body = dict(receipt)
    body.pop("receipt_digest")
    body["operation_kind"] = "restore"
    records[receipt_key] = {**body, "receipt_digest": canonical_digest(body)}
    expectation = replace(
        expectation,
        receipt_digest=str(records[receipt_key]["receipt_digest"]),
    )

    authority, reasons = _load(revision, records, expectation)
    assert authority is None
    assert reasons == ("subjective_mem_lifecycle_current_receipt_not_exact",)


def test_tampered_receipt_fails_before_authorization_lookup() -> None:
    revision, records, expectation = _lifecycle_records(
        operation="restore",
        from_state="hidden",
        to_state="active",
    )
    receipt_key = ("subjective_mem_lifecycle_receipt", expectation.receipt_id)
    records[receipt_key]["page_id"] = "other-page"

    authority, reasons = _load(revision, records, expectation)
    assert authority is None
    assert reasons == (
        "subjective_mem_lifecycle_current_receipt_missing_or_corrupt",
    )


def test_transition_must_bind_exact_revision_and_receipt() -> None:
    revision, records, expectation = _lifecycle_records(
        operation="restore",
        from_state="hidden",
        to_state="active",
    )
    transition_key = (
        "subjective_mem_lifecycle_transition",
        revision.authorization_id,
    )
    records[transition_key]["to_revision"] = 99

    authority, reasons = _load(revision, records, expectation)
    assert authority is None
    assert reasons == (
        "subjective_mem_lifecycle_predecessor_authority_not_exact",
    )


def test_create_predecessor_remains_supported() -> None:
    revision = replace(
        _revision(operation="create", lifecycle_state="active"),
        memory_revision=1,
        predecessor_revision_or_null=None,
        decision_id="decision-1",
        authorization_kind="formation_decision",
    )
    decision = {
        "decision_id": revision.authorization_id,
        "character_id": revision.character_id,
        "result_memory_ref_or_null": {
            "memory_id": revision.memory_id,
            "memory_revision": 1,
        }
    }
    receipt_body = {
        "schema": ST1_RECEIPT_SCHEMA,
        "receipt_id": "create-receipt-1",
        "operation_kind": "create",
        "operation_outcome": "committed",
        "evidence_space_id": SPACE,
        "character_id": CHARACTER.character_id,
        "memory_ref": {"memory_id": revision.memory_id, "memory_revision": 1},
        "decision_id": revision.authorization_id,
        "target_page_id": "page-1",
        "memory_block_id": "block-2",
        "post_image_digest": PAGE_DIGEST,
        "current_state_digest": STATE_DIGEST,
        "renderer_revision": RENDERER_REVISION,
        "partition_revision": PAGE_PARTITION_REVISION,
        "platform_revision": PLATFORM_REVISION,
    }
    receipt = {**receipt_body, "receipt_digest": canonical_digest(receipt_body)}
    records = {
        ("evidence_space_descriptor", "revision-1"): _descriptor(),
        ("subjective_mem_st1_commit_receipt", "create-receipt-1"): receipt,
        ("subjective_mem_decision", "decision-1"): decision,
    }

    authority, reasons = _load(revision, records, _expectation(receipt))
    assert authority is not None, reasons
    assert authority.authorization_kind == "subjective_mem_decision"


def _consolidate_records(**changes: object):
    arguments: dict[str, object] = {
        "operation": CONSOLIDATE_OPERATION_FAMILY,
        "from_state": "active",
        "to_state": "active",
        "from_stage": "primary",
        "to_stage": "secondary",
        "authorization_class": CONSOLIDATE_AUTHORIZATION_CLASS,
        "reason_category": CONSOLIDATE_REASON_CATEGORY,
        "policy_revision": CONSOLIDATE_POLICY_REVISION,
    }
    return _lifecycle_records(**{**arguments, **changes})  # type: ignore[arg-type]


def test_committed_consolidate_secondary_predecessor_is_exact_authority() -> None:
    revision, records, expectation = _consolidate_records()
    authority, reasons = _load(revision, records, expectation)
    assert authority is not None, reasons
    assert revision.formation_stage == "secondary"
    assert authority.receipt["operation_kind"] == CONSOLIDATE_OPERATION_FAMILY
    assert authority.authorization_record["from_formation_stage"] == "primary"
    assert authority.authorization_record["to_formation_stage"] == "secondary"


def test_consolidate_requires_the_exact_consolidation_policy_revision() -> None:
    revision, records, expectation = _consolidate_records(
        policy_revision=LIFECYCLE_POLICY_REVISION
    )
    authority, reasons = _load(revision, records, expectation)
    assert authority is None
    assert reasons == ("subjective_mem_lifecycle_current_receipt_not_exact",)


def test_consolidate_requires_exact_policy_authorization_and_reason() -> None:
    for changes in (
        {"authorization_class": "user_management"},
        {"reason_category": "user_requested_consolidation"},
    ):
        revision, records, expectation = _consolidate_records(**changes)
        authority, reasons = _load(revision, records, expectation)
        assert authority is None, changes
        assert reasons == ("subjective_mem_lifecycle_current_receipt_not_exact",)


def test_consolidate_accepts_only_the_primary_to_secondary_stage_change() -> None:
    for changes in (
        {"from_stage": "secondary", "to_stage": "secondary"},
        {"from_stage": "primary", "to_stage": "primary"},
    ):
        revision, records, expectation = _consolidate_records(**changes)
        authority, reasons = _load(revision, records, expectation)
        assert authority is None, changes
        assert reasons == (
            "subjective_mem_lifecycle_predecessor_authority_not_exact",
        )


def test_formation_stage_change_is_rejected_for_every_other_operation() -> None:
    directions = {
        "correct": ("active", "active"),
        "forget": ("active", "hidden"),
        "pin": ("active", "pinned"),
        "unpin": ("pinned", "active"),
        "restore": ("hidden", "active"),
    }
    for operation, (from_state, to_state) in directions.items():
        revision, records, expectation = _lifecycle_records(
            operation=operation,
            from_state=from_state,
            to_state=to_state,
            from_stage="primary",
            to_stage="secondary",
        )
        authority, reasons = _load(revision, records, expectation)
        assert authority is None, operation
        assert reasons == (
            "subjective_mem_lifecycle_predecessor_authority_not_exact",
        )


def test_secondary_predecessor_is_accepted_by_later_lifecycle_operations() -> None:
    for operation, (from_state, to_state) in {
        "correct": ("active", "active"),
        "forget": ("active", "hidden"),
        "pin": ("active", "pinned"),
    }.items():
        revision, records, expectation = _lifecycle_records(
            operation=operation,
            from_state=from_state,
            to_state=to_state,
            from_stage="secondary",
        )
        authority, reasons = _load(revision, records, expectation)
        assert authority is not None, (operation, reasons)
        assert revision.formation_stage == "secondary"
        assert authority.authorization_record["to_formation_stage"] == "secondary"


def _records_of(records, expectation, revision):
    """Pull the exact receipt and authorization pair out of a record inventory."""

    receipt = records[("subjective_mem_lifecycle_receipt", expectation.receipt_id)]
    transition = records[
        ("subjective_mem_lifecycle_transition", revision.authorization_id)
    ]
    return receipt, transition


def _validate_directly(receipt, authorization, revision, expectation):
    """Run the storage-neutral stages the way a caller holding records does."""

    reasons = validate_subjective_mem_committed_receipt(
        receipt=receipt,
        evidence_space_id=SPACE,
        character_id=CHARACTER.character_id,
        predecessor=revision,
        expectation=expectation,
    )
    if reasons:
        return reasons
    _kind, identifier = subjective_mem_committed_authorization_ref(
        predecessor=revision, receipt=receipt
    )
    if identifier is None:
        return ("subjective_mem_lifecycle_predecessor_authority_missing",)
    return validate_subjective_mem_committed_authorization(
        authorization=authorization, receipt=receipt, predecessor=revision
    )


def test_storage_neutral_stages_accept_the_exact_committed_pair() -> None:
    revision, records, expectation = _lifecycle_records(
        operation="forget", from_state="active", to_state="hidden"
    )
    receipt, transition = _records_of(records, expectation, revision)
    assert _validate_directly(receipt, transition, revision, expectation) == ()


def test_storage_neutral_stages_agree_with_the_locked_loader() -> None:
    cases = (
        {"operation_kind": "restore"},
        {"policy_revision": "relaylm.subjective_mem_other_policy.v1"},
        {"predecessor_revision": 99},
    )
    for changes in cases:
        revision, records, expectation = _lifecycle_records(
            operation="forget", from_state="active", to_state="hidden"
        )
        receipt_key = ("subjective_mem_lifecycle_receipt", expectation.receipt_id)
        body = {
            key: value
            for key, value in {**records[receipt_key], **changes}.items()
            if key != "receipt_digest"
        }
        receipt = {**body, "receipt_digest": canonical_digest(body)}
        records[receipt_key] = receipt
        expectation = replace(expectation, receipt_digest=str(receipt["receipt_digest"]))
        transition = records[
            ("subjective_mem_lifecycle_transition", revision.authorization_id)
        ]

        authority, locked_reasons = _load(revision, records, expectation)
        assert authority is None, changes
        assert locked_reasons == _validate_directly(
            receipt, transition, revision, expectation
        ), changes


def test_authorization_ref_names_the_decision_or_transition_record() -> None:
    revision, records, expectation = _lifecycle_records(
        operation="pin", from_state="active", to_state="pinned"
    )
    receipt, _transition = _records_of(records, expectation, revision)
    assert subjective_mem_committed_authorization_ref(
        predecessor=revision, receipt=receipt
    ) == ("subjective_mem_lifecycle_transition", revision.authorization_id)

    create = replace(
        _revision(operation="create", lifecycle_state="active"),
        memory_revision=1,
        predecessor_revision_or_null=None,
        decision_id="decision-1",
        authorization_kind="formation_decision",
    )
    assert subjective_mem_committed_authorization_ref(
        predecessor=create, receipt={"decision_id": "decision-1"}
    ) == ("subjective_mem_decision", "decision-1")
    assert subjective_mem_committed_authorization_ref(
        predecessor=create, receipt={}
    ) == ("subjective_mem_decision", None)


def test_storage_neutral_receipt_validation_needs_no_transaction() -> None:
    revision, records, expectation = _lifecycle_records(
        operation="forget", from_state="active", to_state="hidden"
    )
    receipt, transition = _records_of(records, expectation, revision)
    assert validate_subjective_mem_committed_receipt(
        receipt=receipt,
        evidence_space_id="another-space",
        character_id=CHARACTER.character_id,
        predecessor=revision,
        expectation=expectation,
    ) == ("subjective_mem_lifecycle_current_receipt_not_exact",)
    assert validate_subjective_mem_committed_authorization(
        authorization={**transition, "to_revision": 99},
        receipt=receipt,
        predecessor=revision,
    ) == ("subjective_mem_lifecycle_predecessor_authority_not_exact",)
    assert validate_subjective_mem_committed_receipt(
        receipt=None,
        evidence_space_id=SPACE,
        character_id=CHARACTER.character_id,
        predecessor=revision,
        expectation=expectation,
    ) == ("subjective_mem_lifecycle_current_receipt_missing_or_corrupt",)


def test_shared_authority_has_no_operation_runtime_dependency() -> None:
    source = inspect.getsource(authority_module)
    assert "subjective_mem.lifecycle_runtime import" not in source
    assert "subjective_mem_forget_runtime import" not in source
    assert "subjective_mem_pin_runtime import" not in source
    assert "subjective_mem_restore_runtime import" not in source
    assert "subjective_mem_consolidate_runtime" not in source
