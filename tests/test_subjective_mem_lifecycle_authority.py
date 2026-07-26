"""Shared Subjective MEM lifecycle predecessor authority tests."""
from __future__ import annotations

from dataclasses import replace
import inspect

from relaylm._subjective_mem_commit_io import PLATFORM_REVISION
from relaylm.evidence_common import canonical_digest
from relaylm.evidence_space import (
    build_bootstrap_evidence_space_descriptor,
    derive_evidence_space_id,
)
from relaylm.subjective_mem import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemFormationSnapshot,
    SubjectiveMemRevision,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
)
from relaylm.subjective_mem_commit import ST1_RECEIPT_SCHEMA
from relaylm.subjective_mem_lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
)
import relaylm.subjective_mem_lifecycle_authority as authority_module
from relaylm.subjective_mem_lifecycle_authority import (
    SubjectiveMemPredecessorExpectation,
    load_subjective_mem_predecessor_authority_locked,
)
from relaylm.subjective_mem_markdown import (
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
        formation_stage="primary",
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
) -> tuple[
    SubjectiveMemRevision,
    dict[tuple[str, str], dict[str, object]],
    SubjectiveMemPredecessorExpectation,
]:
    revision = _revision(operation=operation, lifecycle_state=to_state)
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
        "from_formation_stage": revision.formation_stage,
        "to_formation_stage": revision.formation_stage,
        "authorized_by": "user_management",
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
        "authorization_class": "user_management",
        "authorization_id": "authorization-1",
        "reason_category": f"user_requested_{operation}",
        "policy_revision": LIFECYCLE_POLICY_REVISION,
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


def test_shared_authority_has_no_operation_runtime_dependency() -> None:
    source = inspect.getsource(authority_module)
    assert "subjective_mem_lifecycle_runtime import" not in source
    assert "subjective_mem_forget_runtime import" not in source
    assert "subjective_mem_pin_runtime import" not in source
    assert "subjective_mem_restore_runtime import" not in source
