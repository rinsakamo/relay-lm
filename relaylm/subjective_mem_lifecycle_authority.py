"""Shared exact predecessor authority for committed Subjective MEM revisions.

This module is storage-neutral and operation-neutral.  It validates the one
committed receipt and authorization record that make an exact canonical revision
eligible to be the predecessor of a later lifecycle operation.  Operation owners
retain proposal, transition-direction, successor, and publication authority.

``validate_subjective_mem_committed_receipt``,
``subjective_mem_committed_authorization_ref``, and
``validate_subjective_mem_committed_authorization`` are the storage-neutral
validation stages.  ``load_subjective_mem_predecessor_authority_locked`` is the
Evidence-store-bound reader that sequences them; a caller that already holds the
exact records — such as the RT-1B retrieval projection builder — calls the same
stages directly so exactly one committed-authority evaluator exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from relaylm.evidence.common import canonical_digest
from relaylm.evidence.space import EvidenceSpaceDescriptor
from relaylm.evidence.store import EvidenceStoreTransaction
from relaylm.subjective_mem.models import (
    SubjectiveMemCharacterAuthority,
    SubjectiveMemRevision,
)
from relaylm.subjective_mem.commit import ST1_RECEIPT_SCHEMA
from relaylm.subjective_mem_consolidate import (
    CONSOLIDATE_AUTHORIZATION_CLASS,
    CONSOLIDATE_OPERATION_FAMILY,
    CONSOLIDATE_POLICY_REVISION,
    CONSOLIDATE_REASON_CATEGORY,
)
from relaylm.subjective_mem_lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
)
from relaylm.subjective_mem_lifecycle_engine import RecordBinding


@dataclass(frozen=True)
class SubjectiveMemCommittedOperationSpec:
    """Exact committed semantics one accepted lifecycle operation must carry.

    ``from_formation_stage`` and ``to_formation_stage`` are ``None`` for every
    operation that preserves its predecessor's formation stage.  An operation
    that names them declares the only stage change it is allowed to have made,
    and both ends are still compared against the exact committed revision.
    ``authorization_class`` and ``reason_category`` are ``None`` when the
    operation owner, not this shared authority, bounds its accepted authority.
    """

    from_lifecycle_state: str
    to_lifecycle_state: str
    policy_revision: str
    from_formation_stage: str | None = None
    to_formation_stage: str | None = None
    authorization_class: str | None = None
    reason_category: str | None = None


COMMITTED_LIFECYCLE_OPERATIONS = MappingProxyType(
    {
        "correct": SubjectiveMemCommittedOperationSpec(
            "active", "active", LIFECYCLE_POLICY_REVISION
        ),
        "forget": SubjectiveMemCommittedOperationSpec(
            "active", "hidden", LIFECYCLE_POLICY_REVISION
        ),
        "pin": SubjectiveMemCommittedOperationSpec(
            "active", "pinned", LIFECYCLE_POLICY_REVISION
        ),
        "unpin": SubjectiveMemCommittedOperationSpec(
            "pinned", "active", LIFECYCLE_POLICY_REVISION
        ),
        "restore": SubjectiveMemCommittedOperationSpec(
            "hidden", "active", LIFECYCLE_POLICY_REVISION
        ),
        CONSOLIDATE_OPERATION_FAMILY: SubjectiveMemCommittedOperationSpec(
            "active",
            "active",
            CONSOLIDATE_POLICY_REVISION,
            from_formation_stage="primary",
            to_formation_stage="secondary",
            authorization_class=CONSOLIDATE_AUTHORIZATION_CLASS,
            reason_category=CONSOLIDATE_REASON_CATEGORY,
        ),
    }
)


def _operation_spec(operation: object) -> SubjectiveMemCommittedOperationSpec | None:
    return (
        COMMITTED_LIFECYCLE_OPERATIONS.get(operation)
        if isinstance(operation, str)
        else None
    )


def _formation_stages(
    spec: SubjectiveMemCommittedOperationSpec, predecessor: SubjectiveMemRevision
) -> tuple[str, str]:
    return (
        spec.from_formation_stage or predecessor.formation_stage,
        spec.to_formation_stage or predecessor.formation_stage,
    )


@dataclass(frozen=True)
class SubjectiveMemPredecessorExpectation:
    receipt_id: str
    receipt_digest: str
    current_state_digest: str
    page_id: str
    block_id: str
    page_digest: str
    revision_schema: str
    page_schema: str
    block_schema: str
    renderer_revision: str
    partition_revision: str
    platform_revision: str


@dataclass(frozen=True)
class SubjectiveMemPredecessorAuthority:
    receipt_kind: str
    receipt: dict[str, object]
    authorization_kind: str
    authorization_record: dict[str, object]
    record_bindings: tuple[RecordBinding, ...]


def load_subjective_mem_predecessor_authority_locked(
    *,
    tx: EvidenceStoreTransaction,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    predecessor: SubjectiveMemRevision,
    expectation: SubjectiveMemPredecessorExpectation,
) -> tuple[SubjectiveMemPredecessorAuthority | None, tuple[str, ...]]:
    """Load and validate the exact authority chain for one current predecessor."""

    descriptor, reasons = _evidence_space_descriptor(
        tx=tx,
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
    )
    if descriptor is None:
        return None, reasons
    receipt_kind = (
        "subjective_mem_st1_commit_receipt"
        if predecessor.memory_revision == 1
        else "subjective_mem_lifecycle_receipt"
    )
    receipt = tx.read_record(
        record_kind=receipt_kind,
        record_id=expectation.receipt_id,
    )
    reasons = validate_subjective_mem_committed_receipt(
        receipt=receipt,
        evidence_space_id=evidence_space_id,
        character_id=character_authority.character_id,
        predecessor=predecessor,
        expectation=expectation,
    )
    if reasons:
        return None, reasons
    assert isinstance(receipt, dict)
    authorization_kind, authorization_id = subjective_mem_committed_authorization_ref(
        predecessor=predecessor,
        receipt=receipt,
    )
    if authorization_id is None:
        return None, ("subjective_mem_lifecycle_predecessor_authority_missing",)
    authorization = tx.read_record(
        record_kind=authorization_kind,
        record_id=authorization_id,
    )
    reasons = validate_subjective_mem_committed_authorization(
        authorization=authorization,
        receipt=receipt,
        predecessor=predecessor,
    )
    if reasons:
        return None, reasons
    assert isinstance(authorization, dict)
    bindings: tuple[RecordBinding, ...] = (
        ("evidence_space_descriptor", "revision-1", descriptor),
        (receipt_kind, expectation.receipt_id, receipt),
        (authorization_kind, authorization_id, authorization),
    )
    return (
        SubjectiveMemPredecessorAuthority(
            receipt_kind=receipt_kind,
            receipt=receipt,
            authorization_kind=authorization_kind,
            authorization_record=authorization,
            record_bindings=bindings,
        ),
        (),
    )


def _evidence_space_descriptor(
    *,
    tx: EvidenceStoreTransaction,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    raw = tx.read_record(
        record_kind="evidence_space_descriptor",
        record_id="revision-1",
    )
    try:
        descriptor = (
            EvidenceSpaceDescriptor.from_dict(raw) if isinstance(raw, dict) else None
        )
    except (KeyError, TypeError, ValueError):
        descriptor = None
    if (
        descriptor is None
        or descriptor.to_dict() != raw
        or descriptor.evidence_space_id != evidence_space_id
        or descriptor.workspace_or_tenant_ref
        != character_authority.workspace_or_tenant_ref
        or descriptor.isolation_mode != "private_conversation"
        or descriptor.retired_at_or_null is not None
    ):
        return None, (
            "subjective_mem_lifecycle_evidence_space_authority_mismatch",
        )
    return raw, ()


def validate_subjective_mem_committed_receipt(
    *,
    receipt: object,
    evidence_space_id: str,
    character_id: str,
    predecessor: SubjectiveMemRevision,
    expectation: SubjectiveMemPredecessorExpectation,
) -> tuple[str, ...]:
    """Return the exactness reasons for one committed receipt, storage-neutrally."""

    if not _self_digest_exact(receipt, "receipt_digest"):
        return ("subjective_mem_lifecycle_current_receipt_missing_or_corrupt",)
    assert isinstance(receipt, dict)
    common = _common_receipt_exact(
        receipt=receipt,
        evidence_space_id=evidence_space_id,
        character_id=character_id,
        predecessor=predecessor,
        expectation=expectation,
    )
    if not common:
        return ("subjective_mem_lifecycle_current_receipt_not_exact",)
    if predecessor.memory_revision == 1:
        valid = (
            receipt.get("schema") == ST1_RECEIPT_SCHEMA
            and receipt.get("operation_kind") == "create"
            and receipt.get("target_page_id") == expectation.page_id
            and receipt.get("memory_block_id") == expectation.block_id
            and receipt.get("decision_id") == predecessor.authorization_id
        )
    else:
        valid = _lifecycle_receipt_exact(
            receipt=receipt,
            predecessor=predecessor,
            expectation=expectation,
        )
    return () if valid else ("subjective_mem_lifecycle_current_receipt_not_exact",)


def _common_receipt_exact(
    *,
    receipt: dict[str, object],
    evidence_space_id: str,
    character_id: str,
    predecessor: SubjectiveMemRevision,
    expectation: SubjectiveMemPredecessorExpectation,
) -> bool:
    memory_ref = receipt.get("memory_ref")
    return (
        receipt.get("operation_outcome") == "committed"
        and receipt.get("receipt_digest") == expectation.receipt_digest
        and receipt.get("evidence_space_id") == evidence_space_id
        and receipt.get("character_id") == character_id
        and isinstance(memory_ref, dict)
        and memory_ref.get("memory_id") == predecessor.memory_id
        and memory_ref.get("memory_revision") == predecessor.memory_revision
        and receipt.get("post_image_digest") == expectation.page_digest
        and receipt.get("current_state_digest") == expectation.current_state_digest
        and receipt.get("renderer_revision") == expectation.renderer_revision
        and receipt.get("partition_revision") == expectation.partition_revision
        and receipt.get("platform_revision") == expectation.platform_revision
    )


def _lifecycle_receipt_exact(
    *,
    receipt: dict[str, object],
    predecessor: SubjectiveMemRevision,
    expectation: SubjectiveMemPredecessorExpectation,
) -> bool:
    spec = _operation_spec(receipt.get("operation_kind"))
    if spec is None:
        return False
    return (
        receipt.get("schema") == LIFECYCLE_RECEIPT_SCHEMA
        and spec.to_lifecycle_state == predecessor.lifecycle_state
        and (
            spec.authorization_class is None
            or receipt.get("authorization_class") == spec.authorization_class
        )
        and (
            spec.reason_category is None
            or receipt.get("reason_category") == spec.reason_category
        )
        and receipt.get("predecessor_revision")
        == predecessor.memory_revision - 1
        and receipt.get("transition_id") == predecessor.authorization_id
        and receipt.get("successor_revision_digest")
        == canonical_digest(predecessor.to_dict())
        and receipt.get("page_id") == expectation.page_id
        and receipt.get("successor_block_id") == expectation.block_id
        and receipt.get("revision_schema") == expectation.revision_schema
        and receipt.get("page_schema") == expectation.page_schema
        and receipt.get("block_schema") == expectation.block_schema
        and receipt.get("policy_revision") == spec.policy_revision
    )


def subjective_mem_committed_authorization_ref(
    *,
    predecessor: SubjectiveMemRevision,
    receipt: dict[str, object],
) -> tuple[str, str | None]:
    """Return the authorization record kind and identity the receipt names."""

    if predecessor.memory_revision == 1:
        identifier = receipt.get("decision_id")
        return (
            "subjective_mem_decision",
            identifier if isinstance(identifier, str) and identifier else None,
        )
    identifier = receipt.get("transition_id")
    return (
        "subjective_mem_lifecycle_transition",
        identifier if isinstance(identifier, str) and identifier else None,
    )


def validate_subjective_mem_committed_authorization(
    *,
    authorization: object,
    receipt: dict[str, object],
    predecessor: SubjectiveMemRevision,
) -> tuple[str, ...]:
    """Return the exactness reasons for the authorizing decision or transition."""

    if not isinstance(authorization, dict):
        return ("subjective_mem_lifecycle_predecessor_authority_missing",)
    if predecessor.memory_revision == 1:
        result_ref = authorization.get("result_memory_ref_or_null")
        valid = (
            predecessor.authorization_kind == "formation_decision"
            and receipt.get("decision_id") == predecessor.authorization_id
            and authorization.get("decision_id") == predecessor.authorization_id
            and authorization.get("character_id") == predecessor.character_id
            and isinstance(result_ref, dict)
            and result_ref.get("memory_id") == predecessor.memory_id
            and result_ref.get("memory_revision") == 1
        )
    else:
        valid = _lifecycle_authorization_exact(
            transition=authorization,
            receipt=receipt,
            predecessor=predecessor,
        )
    return () if valid else (
        "subjective_mem_lifecycle_predecessor_authority_not_exact",
    )


def _lifecycle_authorization_exact(
    *,
    transition: dict[str, object],
    receipt: dict[str, object],
    predecessor: SubjectiveMemRevision,
) -> bool:
    operation = receipt.get("operation_kind")
    spec = _operation_spec(operation)
    if spec is None:
        return False
    from_stage, to_stage = _formation_stages(spec, predecessor)
    expected_visible = predecessor.lifecycle_state in {"active", "pinned"}
    return (
        predecessor.authorization_kind == "lifecycle_transition"
        and predecessor.retrieval_visible is expected_visible
        and transition.get("schema") == LIFECYCLE_TRANSITION_SCHEMA
        and transition.get("transition_id") == predecessor.authorization_id
        and transition.get("transition_id") == receipt.get("transition_id")
        and transition.get("character_id") == predecessor.character_id
        and transition.get("memory_id") == predecessor.memory_id
        and transition.get("from_revision") == predecessor.memory_revision - 1
        and transition.get("to_revision") == predecessor.memory_revision
        and transition.get("operation") == operation
        and transition.get("from_lifecycle_state") == spec.from_lifecycle_state
        and transition.get("to_lifecycle_state") == spec.to_lifecycle_state
        and transition.get("to_lifecycle_state") == predecessor.lifecycle_state
        and transition.get("from_formation_stage") == from_stage
        and transition.get("to_formation_stage") == to_stage
        and to_stage == predecessor.formation_stage
        and transition.get("authorized_by") == receipt.get("authorization_class")
        and transition.get("committed_at") == receipt.get("finalized_at")
    )


def _self_digest_exact(raw: object, field: str) -> bool:
    if not isinstance(raw, dict):
        return False
    digest = raw.get(field)
    if not isinstance(digest, str):
        return False
    body = dict(raw)
    body.pop(field, None)
    return digest == canonical_digest(body)
