"""SM-1 one-shot Subjective MEM create transaction.

This module consumes an exact current-admitted ASM-1 revision and commits one
formation receipt, one decision, one prepared revision, one prepared manifest,
one singleton current-state selector, and one durable idempotency result in the
same caller-owned Evidence transaction. It never publishes canonical Markdown
and never exposes the prepared revision to ordinary Retrieval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from relaylm.evidence.common import canonical_digest, sha256_hex
from relaylm.evidence.space import EvidenceSpaceDescriptor
from relaylm.evidence.store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.shared_assessment.models import (
    SHARED_ASSESSMENT_FORMATION_RECEIPT_SCHEMA,
    SharedAssessmentCurrentState,
    SharedAssessmentFormationAuthorizationReceipt,
    SharedAssessmentRevision,
)
from relaylm.shared_assessment.runtime import (
    build_shared_assessment_formation_receipt,
    shared_assessment_current_state_key,
    shared_assessment_formation_receipt_id,
    shared_assessment_revision_record_id,
)
from relaylm.subjective_mem_reformation import (
    check_subjective_mem_reformation_locked,
)
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_PREPARED_MANIFEST_SCHEMA,
    SubjectiveMemAssessmentAuthorizationProjection,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCreateProposal,
    SubjectiveMemCurrentState,
    SubjectiveMemDecision,
    SubjectiveMemFormationSnapshot,
    SubjectiveMemPreparedManifest,
    SubjectiveMemRevision,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
    resolve_subjective_mem_character_authority,
    validate_subjective_mem_create_inputs,
    validate_subjective_mem_crosslinks,
)

CreateStatus = Literal[
    "disabled",
    "dry_run_ready",
    "committed",
    "duplicate_existing",
    "duplicate_finalized",
    "fail_closed",
    "integrity_conflict",
]

@dataclass(frozen=True)
class SubjectiveMemOperationIdentity:
    character_authority_digest: str
    namespace_digest: str
    operation_key_digest: str
    operation_slot_id: str
    operation_id: str


def derive_subjective_mem_operation_identity(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    operation_idempotency_key: str,
) -> SubjectiveMemOperationIdentity:
    if not _token(evidence_space_id):
        raise ValueError("subjective_mem_evidence_space_id_invalid")
    if type(character_authority) is not SubjectiveMemCharacterAuthority:
        raise ValueError("subjective_mem_character_authority_invalid")
    if not _token(operation_idempotency_key, 256):
        raise ValueError("subjective_mem_operation_idempotency_key_invalid")
    character_authority_digest = canonical_digest(character_authority.to_dict())
    namespace_digest = canonical_digest(
        {
            "evidence_space_id": evidence_space_id,
            "character_authority_digest": character_authority_digest,
        }
    )
    operation_key_digest = sha256_hex(operation_idempotency_key.encode("utf-8"))
    return SubjectiveMemOperationIdentity(
        character_authority_digest=character_authority_digest,
        namespace_digest=namespace_digest,
        operation_key_digest=operation_key_digest,
        operation_slot_id=_opaque(
            "smkey", f"{namespace_digest}\0{operation_key_digest}"
        ),
        operation_id=_opaque(
            "smop", f"{namespace_digest}\0{operation_key_digest}"
        ),
    )


@dataclass(frozen=True)
class SubjectiveMemCreateGate:
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    store: EvidenceRecordStore | None


def resolve_subjective_mem_create_gate(config: object) -> SubjectiveMemCreateGate:
    enabled = bool(getattr(config, "subjective_mem_create_enabled", False))
    dry_run_only = bool(
        getattr(config, "subjective_mem_create_dry_run_only", True)
    )
    apply_enabled = bool(
        getattr(config, "subjective_mem_create_apply_enabled", False)
    )
    if not enabled:
        return SubjectiveMemCreateGate(False, True, False, None)
    root = getattr(config, "evidence_data_root", None)
    if not isinstance(root, str) or not root:
        return SubjectiveMemCreateGate(True, dry_run_only, False, None)
    try:
        store = EvidenceRecordStore(root)
    except ValueError:
        store = None
    return SubjectiveMemCreateGate(
        True,
        dry_run_only,
        apply_enabled and not dry_run_only and store is not None,
        store,
    )

@dataclass(frozen=True)
class SubjectiveMemPersistedBundle:
    formation_receipt: SharedAssessmentFormationAuthorizationReceipt
    decision: SubjectiveMemDecision
    revision: SubjectiveMemRevision = field(repr=False)
    prepared_manifest: SubjectiveMemPreparedManifest
    current_state: SubjectiveMemCurrentState


@dataclass(frozen=True)
class SubjectiveMemCreateResult:
    status: CreateStatus
    decision: SubjectiveMemDecision | None = None
    revision: SubjectiveMemRevision | None = field(default=None, repr=False)
    current_state: SubjectiveMemCurrentState | None = None
    prepared_manifest: SubjectiveMemPreparedManifest | None = None
    formation_receipt: SharedAssessmentFormationAuthorizationReceipt | None = None
    finalization_id: str | None = None
    canonical_page_id: str | None = None
    canonical_block_id: str | None = None
    blocked_reasons: tuple[str, ...] = ()
    persisted: bool = False

    def to_log_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "blocked_reasons": list(self.blocked_reasons),
            "decision_id": self.decision.decision_id if self.decision else None,
            "memory_id": self.revision.memory_id if self.revision else None,
            "assessment_id": self.decision.assessment_id if self.decision else None,
            "assessment_revision": (
                self.decision.assessment_revision if self.decision else None
            ),
            "result_revision": 1 if self.revision else None,
            "scope_kind": (
                self.revision.scope_binding.scope_kind if self.revision else None
            ),
            "memory_kind": self.revision.memory_kind if self.revision else None,
            "prepared": (
                self.current_state is not None
                and self.current_state.mutation_state == "prepared"
            ),
            "finalization_id": self.finalization_id,
            "canonical_page_id": self.canonical_page_id,
            "canonical_block_id": self.canonical_block_id,
            "persisted": self.persisted,
            "retrieval_eligible": (
                self.current_state.retrieval_eligible if self.current_state else False
            ),
            "canonical_published": self.status == "duplicate_finalized",
            "content_free": True,
        }

class _FinalizedOperationRetry(RuntimeError):
    def __init__(self, result: SubjectiveMemCreateResult) -> None:
        super().__init__("subjective_mem_finalized_operation_retry")
        self.result = result


def create_subjective_mem(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_config: object,
    character_authority: SubjectiveMemCharacterAuthority,
    assessment_revision: SharedAssessmentRevision,
    assessment_current_state: SharedAssessmentCurrentState,
    proposal: SubjectiveMemCreateProposal,
    operation_idempotency_key: str,
    apply_enabled: bool,
    decided_at: datetime,
    observed_at: datetime | None = None,
    outcome: str = "create",
    candidate_memory_refs: tuple[object, ...] = (),
    similarity_granted_authority: bool = False,
    target_memory_ref_or_null: object | None = None,
    result_relation_id_or_null: str | None = None,
    hold_reason_or_null: str | None = None,
) -> SubjectiveMemCreateResult:
    """Validate and atomically prepare one revision-1 create result."""

    reasons = list(
        validate_subjective_mem_create_inputs(
            character_authority=character_authority,
            assessment_revision=assessment_revision,
            assessment_current_state=assessment_current_state,
            proposal=proposal,
        )
    )
    if type(store) is not EvidenceRecordStore:
        reasons.append("subjective_mem_store_invalid")
    if type(character_authority) is SubjectiveMemCharacterAuthority:
        resolved_authority, authority_reasons = (
            resolve_subjective_mem_character_authority(
                character_config,
                workspace_or_tenant_ref=(
                    character_authority.workspace_or_tenant_ref
                ),
                character_id=character_authority.character_id,
            )
        )
        reasons.extend(authority_reasons)
        if resolved_authority != character_authority:
            reasons.append("subjective_mem_character_authority_not_exact_current")
    if not _token(evidence_space_id):
        reasons.append("subjective_mem_evidence_space_id_invalid")
    if not _token(operation_idempotency_key, 256):
        reasons.append("subjective_mem_operation_idempotency_key_invalid")
    if type(apply_enabled) is not bool:
        reasons.append("subjective_mem_apply_mode_invalid")
    if outcome != "create":
        reasons.append("subjective_mem_outcome_unsupported")
    if type(candidate_memory_refs) is not tuple or candidate_memory_refs:
        reasons.append("subjective_mem_candidate_memory_refs_unsupported")
    if similarity_granted_authority is not False:
        reasons.append("subjective_mem_similarity_authority_forbidden")
    if target_memory_ref_or_null is not None:
        reasons.append("subjective_mem_create_target_memory_forbidden")
    if result_relation_id_or_null is not None:
        reasons.append("subjective_mem_create_relation_forbidden")
    if hold_reason_or_null is not None:
        reasons.append("subjective_mem_create_hold_reason_forbidden")
    try:
        current_time = _utc(decided_at)
        observed_time = _utc(
            observed_at if observed_at is not None else datetime.now(timezone.utc)
        )
        if current_time > observed_time:
            reasons.append("subjective_mem_decision_time_in_future")
    except (TypeError, ValueError):
        reasons.append("subjective_mem_clock_invalid")
        current_time = None
    if reasons:
        return SubjectiveMemCreateResult(
            "fail_closed", blocked_reasons=tuple(dict.fromkeys(reasons))
        )
    assert current_time is not None

    identity = derive_subjective_mem_operation_identity(
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        operation_idempotency_key=operation_idempotency_key,
    )
    character_authority_digest = identity.character_authority_digest
    namespace_digest = identity.namespace_digest
    operation_key_digest = identity.operation_key_digest
    operation_slot_id = identity.operation_slot_id
    operation_id = identity.operation_id
    decision_id = _opaque("smdec", operation_id)
    memory_id = _opaque("smem", f"{namespace_digest}\0{decision_id}")
    prepared_revision_record_id = _opaque("smprev", f"{memory_id}\0revision-1")
    prepared_manifest_id = _opaque("smprep", prepared_revision_record_id)
    state_key = _opaque("smstate", f"{namespace_digest}\0{memory_id}")
    transaction_id = _opaque("smtx", operation_id)

    decision_input_digest = canonical_digest(
        {
            "character_authority": character_authority.to_dict(),
            "evidence_space_id": evidence_space_id,
            "assessment_revision": assessment_revision.to_dict(),
            "assessment_current_state": assessment_current_state.to_dict(),
            "proposal": proposal.to_dict(),
            "operation_idempotency_key_digest": operation_key_digest,
            "outcome": "create",
            "candidate_memory_refs": [],
            "similarity_granted_authority": False,
            "target_memory_ref_or_null": None,
            "result_relation_id_or_null": None,
            "hold_reason_or_null": None,
            "decision_id": decision_id,
            "memory_id": memory_id,
            "decided_at": current_time.isoformat(),
        }
    )
    receipt_id = shared_assessment_formation_receipt_id(
        decision_id, decision_input_digest
    )
    decision = SubjectiveMemDecision(
        decision_id=decision_id,
        character_id=character_authority.character_id,
        assessment_id=assessment_revision.assessment_id,
        assessment_revision=assessment_revision.assessment_revision,
        supported_content_digest=assessment_revision.supported_content_digest,
        assessment_authorization_receipt=(
            SubjectiveMemAssessmentAuthorizationProjection(
                current_revision_at_decision=(
                    assessment_current_state.current_revision
                ),
                lifecycle_state_at_decision=(
                    assessment_current_state.lifecycle_state
                ),
                authorization_state_at_decision=(
                    assessment_current_state.authorization_state
                ),
            )
        ),
        scope_binding=proposal.scope_binding,
        result_memory_id=memory_id,
        decided_at=current_time.isoformat(),
    )
    revision = SubjectiveMemRevision(
        memory_id=memory_id,
        character_id=character_authority.character_id,
        assessment_id=assessment_revision.assessment_id,
        assessment_revision=assessment_revision.assessment_revision,
        grounded_content=assessment_revision.supported_content,
        grounded_content_digest=assessment_revision.supported_content_digest,
        subjective_meaning=proposal.subjective_meaning,
        memory_kind=proposal.memory_kind,
        scope_binding=proposal.scope_binding,
        formation_snapshot=proposal.formation_snapshot,
        strength=proposal.strength,
        decision_id=decision_id,
        created_at=current_time.isoformat(),
    )
    current_state = SubjectiveMemCurrentState(
        memory_state_id=state_key,
        memory_id=memory_id,
        character_id=character_authority.character_id,
        updated_at=current_time.isoformat(),
    )
    manifest = SubjectiveMemPreparedManifest(
        prepared_manifest_id=prepared_manifest_id,
        prepared_revision_record_id=prepared_revision_record_id,
        prepared_revision_digest=canonical_digest(revision.to_dict()),
        decision_id=decision_id,
        memory_id=memory_id,
        character_id=character_authority.character_id,
        prepared_at=current_time.isoformat(),
    )

    try:
        with store.transaction(evidence_space_id) as tx:
            existing_operation = tx.read_record(
                record_kind="subjective_mem_operation",
                record_id=operation_slot_id,
            )
            if existing_operation is not None:
                existing_result = _resolve_existing_operation(
                    tx=tx,
                    existing=existing_operation,
                    expected_operation_slot_id=operation_slot_id,
                    expected_operation_id=operation_id,
                    expected_operation_key_digest=operation_key_digest,
                    expected_input_digest=decision_input_digest,
                    expected_evidence_space_id=evidence_space_id,
                    expected_character_id=character_authority.character_id,
                    expected_character_authority_digest=character_authority_digest,
                    expected_scope_binding_digest=canonical_digest(
                        proposal.scope_binding.to_dict()
                    ),
                    expected_transaction_id=transaction_id,
                    expected_decision_id=decision_id,
                    expected_receipt_id=receipt_id,
                    expected_memory_id=memory_id,
                    expected_prepared_revision_record_id=(
                        prepared_revision_record_id
                    ),
                    expected_prepared_manifest_id=prepared_manifest_id,
                    expected_current_state_key=state_key,
                    expected_decision=decision,
                    expected_revision=revision,
                    expected_manifest=manifest,
                    expected_current_state=current_state,
                )
                if existing_result.status == "duplicate_finalized":
                    raise _FinalizedOperationRetry(existing_result)
                return existing_result

            exact_reasons = _validate_exact_assessment_inputs(
                tx=tx,
                evidence_space_id=evidence_space_id,
                workspace_or_tenant_ref=(
                    character_authority.workspace_or_tenant_ref
                ),
                assessment_revision=assessment_revision,
                assessment_current_state=assessment_current_state,
            )
            if exact_reasons:
                return SubjectiveMemCreateResult(
                    "fail_closed", blocked_reasons=exact_reasons
                )

            reformation = check_subjective_mem_reformation_locked(
                tx=tx,
                evidence_space_id=evidence_space_id,
                character_id=character_authority.character_id,
                grounded_content_digest=assessment_revision.supported_content_digest,
                subjective_meaning=proposal.subjective_meaning,
                memory_kind=proposal.memory_kind,
                scope_binding=proposal.scope_binding,
            )
            if not reformation.allowed:
                return SubjectiveMemCreateResult(
                    "fail_closed",
                    blocked_reasons=(
                        reformation.blocked_reasons
                        or ("subjective_mem_reformation_check_failed",)
                    ),
                )

            receipt_result = build_shared_assessment_formation_receipt(
                tx=tx,
                evidence_space_id=evidence_space_id,
                assessment_id=assessment_revision.assessment_id,
                assessment_revision=assessment_revision.assessment_revision,
                decision_id=decision_id,
                decision_input_digest=decision_input_digest,
                decided_at=current_time,
            )
            if receipt_result.status != "ready" or receipt_result.receipt is None:
                return SubjectiveMemCreateResult(
                    "fail_closed", blocked_reasons=receipt_result.blocked_reasons
                )
            receipt = receipt_result.receipt
            if (
                receipt.receipt_id != receipt_id
                or receipt.decision_input_digest != decision_input_digest
            ):
                return SubjectiveMemCreateResult(
                    "fail_closed",
                    blocked_reasons=(
                        "subjective_mem_formation_receipt_binding_invalid",
                    ),
                )
            crosslink_reasons = validate_subjective_mem_crosslinks(
                receipt=receipt,
                decision=decision,
                revision=revision,
                current_state=current_state,
                manifest=manifest,
            )
            if crosslink_reasons:
                return SubjectiveMemCreateResult(
                    "fail_closed", blocked_reasons=crosslink_reasons
                )
            collision_reasons = _preflight_new_identity(
                tx=tx,
                receipt_id=receipt.receipt_id,
                decision_id=decision_id,
                prepared_revision_record_id=prepared_revision_record_id,
                prepared_manifest_id=prepared_manifest_id,
                state_key=state_key,
                expected_current_state=current_state,
            )
            if collision_reasons:
                return SubjectiveMemCreateResult(
                    "integrity_conflict", blocked_reasons=collision_reasons
                )
            if not apply_enabled:
                return SubjectiveMemCreateResult(
                    "dry_run_ready",
                    decision=decision,
                    revision=revision,
                    current_state=current_state,
                    prepared_manifest=manifest,
                    formation_receipt=receipt,
                    persisted=False,
                )

            operation_record = {
                "schema": "relaylm.subjective_mem_operation.v1",
                "operation_slot_id": operation_slot_id,
                "operation_id": operation_id,
                "operation_idempotency_key_digest": operation_key_digest,
                "decision_input_digest": decision_input_digest,
                "transaction_id": transaction_id,
                "evidence_space_id": evidence_space_id,
                "character_id": character_authority.character_id,
                "character_authority_digest": character_authority_digest,
                "scope_binding_digest": canonical_digest(
                    proposal.scope_binding.to_dict()
                ),
                "outcome": "create",
                "decision_id": decision_id,
                "receipt_id": receipt.receipt_id,
                "memory_id": memory_id,
                "memory_revision": 1,
                "prepared_revision_record_id": prepared_revision_record_id,
                "prepared_revision_digest": canonical_digest(revision.to_dict()),
                "prepared_manifest_id": prepared_manifest_id,
                "prepared_manifest_digest": manifest.to_dict()["manifest_digest"],
                "current_state_key": state_key,
                "mutation_state": "prepared",
                "retrieval_eligible": False,
                "canonical_publication": False,
                "st1_finalization_required": True,
                "committed_at": current_time.isoformat(),
            }
            commit = tx.commit(
                transaction_id=transaction_id,
                records=(
                    (
                        "shared_assessment_formation_receipt",
                        receipt.receipt_id,
                        receipt.to_dict(),
                    ),
                    (
                        "subjective_mem_decision",
                        decision_id,
                        decision.to_dict(),
                    ),
                    (
                        "subjective_mem_prepared_revision",
                        prepared_revision_record_id,
                        revision.to_dict(),
                    ),
                    (
                        "subjective_mem_prepared_manifest",
                        prepared_manifest_id,
                        manifest.to_dict(),
                    ),
                    (
                        "subjective_mem_operation",
                        operation_slot_id,
                        operation_record,
                    ),
                ),
                logs=(
                    (
                        "subjective_mem_current_state",
                        state_key,
                        (current_state.to_dict(),),
                    ),
                ),
            )
            if commit.status == "collision":
                return SubjectiveMemCreateResult(
                    "integrity_conflict", blocked_reasons=commit.reasons
                )
            if commit.status not in {"created", "duplicate_existing"}:
                return SubjectiveMemCreateResult(
                    "fail_closed", blocked_reasons=commit.reasons
                )
            return SubjectiveMemCreateResult(
                "committed" if commit.status == "created" else "duplicate_existing",
                decision=decision,
                revision=revision,
                current_state=current_state,
                prepared_manifest=manifest,
                formation_receipt=receipt,
                persisted=True,
            )
    except _FinalizedOperationRetry as retry:
        workspace_root = getattr(
            character_config, "subjective_mem_workspace_root", None
        )
        if not isinstance(workspace_root, str) or not workspace_root:
            return SubjectiveMemCreateResult(
                "fail_closed",
                blocked_reasons=(
                    "subjective_mem_finalization_workspace_unavailable",
                ),
            )
        from relaylm.subjective_mem.commit_runtime import (
            validate_finalized_subjective_mem_operation,
        )

        validation = validate_finalized_subjective_mem_operation(
            store=store,
            evidence_space_id=evidence_space_id,
            character_config=character_config,
            character_authority=character_authority,
            workspace_root=workspace_root,
            sm1_operation_idempotency_key=operation_idempotency_key,
        )
        if (
            validation.status != "duplicate_finalized"
            or validation.current_state is None
            or validation.finalization_id is None
            or validation.page_id is None
            or validation.block_id is None
        ):
            return SubjectiveMemCreateResult(
                "fail_closed",
                blocked_reasons=validation.blocked_reasons
                or ("subjective_mem_finalization_unverifiable",),
            )
        prior = retry.result
        return SubjectiveMemCreateResult(
            "duplicate_finalized",
            decision=prior.decision,
            revision=prior.revision,
            current_state=validation.current_state,
            prepared_manifest=prior.prepared_manifest,
            formation_receipt=prior.formation_receipt,
            finalization_id=validation.finalization_id,
            canonical_page_id=validation.page_id,
            canonical_block_id=validation.block_id,
            persisted=True,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return SubjectiveMemCreateResult(
            "fail_closed", blocked_reasons=("subjective_mem_store_unavailable",)
        )


def _validate_exact_assessment_inputs(
    *,
    tx: EvidenceStoreTransaction,
    evidence_space_id: str,
    workspace_or_tenant_ref: str,
    assessment_revision: SharedAssessmentRevision,
    assessment_current_state: SharedAssessmentCurrentState,
) -> tuple[str, ...]:
    raw_descriptor = tx.read_record(
        record_kind="evidence_space_descriptor", record_id="revision-1"
    )
    try:
        descriptor = (
            EvidenceSpaceDescriptor.from_dict(raw_descriptor)
            if isinstance(raw_descriptor, dict)
            else None
        )
    except (KeyError, TypeError, ValueError):
        descriptor = None
    if (
        descriptor is None
        or descriptor.to_dict() != raw_descriptor
        or descriptor.evidence_space_id != evidence_space_id
        or descriptor.workspace_or_tenant_ref != workspace_or_tenant_ref
        or descriptor.isolation_mode != "private_conversation"
        or descriptor.descriptor_revision != 1
        or descriptor.retired_at_or_null is not None
    ):
        return ("subjective_mem_evidence_space_authority_mismatch",)
    raw_revision = tx.read_record(
        record_kind="shared_assessment_revision",
        record_id=shared_assessment_revision_record_id(
            assessment_revision.assessment_id,
            assessment_revision.assessment_revision,
        ),
    )
    if raw_revision != assessment_revision.to_dict():
        return ("subjective_mem_assessment_revision_not_exact_stored",)
    raw_state = tx.read_log(
        log_kind="shared_assessment_current_state",
        key=shared_assessment_current_state_key(assessment_revision.assessment_id),
    )
    if raw_state != [assessment_current_state.to_dict()]:
        return ("subjective_mem_assessment_current_state_not_exact_stored",)
    return ()


def _preflight_new_identity(
    *,
    tx: EvidenceStoreTransaction,
    receipt_id: str,
    decision_id: str,
    prepared_revision_record_id: str,
    prepared_manifest_id: str,
    state_key: str,
    expected_current_state: SubjectiveMemCurrentState,
) -> tuple[str, ...]:
    checks = (
        ("shared_assessment_formation_receipt", receipt_id),
        ("subjective_mem_decision", decision_id),
        ("subjective_mem_prepared_revision", prepared_revision_record_id),
        ("subjective_mem_prepared_manifest", prepared_manifest_id),
    )
    if any(tx.read_record(record_kind=kind, record_id=record_id) is not None for kind, record_id in checks):
        return ("subjective_mem_identity_already_reserved_without_operation",)
    if tx.read_log(log_kind="subjective_mem_current_state", key=state_key) not in (None, []):
        return ("subjective_mem_current_state_already_exists",)
    uniqueness_reasons = _validate_current_state_uniqueness(
        tx=tx,
        expected_key=state_key,
        expected_current_state=expected_current_state,
        require_expected=False,
    )
    if uniqueness_reasons:
        return uniqueness_reasons
    return ()


def _validate_current_state_uniqueness(
    *,
    tx: EvidenceStoreTransaction,
    expected_key: str,
    expected_current_state: SubjectiveMemCurrentState,
    require_expected: bool,
) -> tuple[str, ...]:
    try:
        logs = tx.list_logs(
            log_kind="subjective_mem_current_state",
            limit=4096,
        )
    except (RuntimeError, TypeError, ValueError):
        return ("subjective_mem_current_state_inventory_unavailable",)

    matches: list[tuple[str, list[dict]]] = []
    for key, events in logs:
        if any(
            item.get("character_id") == expected_current_state.character_id
            and item.get("memory_id") == expected_current_state.memory_id
            for item in events
        ):
            matches.append((key, events))

    if not require_expected:
        return (
            ("subjective_mem_duplicate_logical_current_state",)
            if matches
            else ()
        )
    if len(matches) != 1:
        return ("subjective_mem_duplicate_logical_current_state",)
    key, events = matches[0]
    if key != expected_key or events != [expected_current_state.to_dict()]:
        return ("subjective_mem_duplicate_logical_current_state",)
    return ()


def _resolve_existing_operation(
    *,
    tx: EvidenceStoreTransaction,
    existing: dict,
    expected_operation_slot_id: str,
    expected_operation_id: str,
    expected_operation_key_digest: str,
    expected_input_digest: str,
    expected_evidence_space_id: str,
    expected_character_id: str,
    expected_character_authority_digest: str,
    expected_scope_binding_digest: str,
    expected_transaction_id: str,
    expected_decision_id: str,
    expected_receipt_id: str,
    expected_memory_id: str,
    expected_prepared_revision_record_id: str,
    expected_prepared_manifest_id: str,
    expected_current_state_key: str,
    expected_decision: SubjectiveMemDecision,
    expected_revision: SubjectiveMemRevision,
    expected_manifest: SubjectiveMemPreparedManifest,
    expected_current_state: SubjectiveMemCurrentState,
) -> SubjectiveMemCreateResult:
    required = {
        "schema",
        "operation_slot_id",
        "operation_id",
        "operation_idempotency_key_digest",
        "decision_input_digest",
        "transaction_id",
        "evidence_space_id",
        "character_id",
        "character_authority_digest",
        "scope_binding_digest",
        "outcome",
        "decision_id",
        "receipt_id",
        "memory_id",
        "memory_revision",
        "prepared_revision_record_id",
        "prepared_revision_digest",
        "prepared_manifest_id",
        "prepared_manifest_digest",
        "current_state_key",
        "mutation_state",
        "retrieval_eligible",
        "canonical_publication",
        "st1_finalization_required",
        "committed_at",
    }
    if set(existing) != required or existing.get("schema") != "relaylm.subjective_mem_operation.v1":
        return SubjectiveMemCreateResult(
            "fail_closed", blocked_reasons=("subjective_mem_operation_record_corrupt",)
        )
    if (
        existing.get("operation_slot_id") != expected_operation_slot_id
        or existing.get("operation_id") != expected_operation_id
        or existing.get("operation_idempotency_key_digest")
        != expected_operation_key_digest
        or existing.get("evidence_space_id") != expected_evidence_space_id
        or existing.get("character_id") != expected_character_id
        or existing.get("character_authority_digest")
        != expected_character_authority_digest
        or existing.get("scope_binding_digest")
        != expected_scope_binding_digest
        or existing.get("transaction_id") != expected_transaction_id
    ):
        return SubjectiveMemCreateResult(
            "fail_closed", blocked_reasons=("subjective_mem_operation_scope_mismatch",)
        )
    if existing.get("decision_input_digest") != expected_input_digest:
        return SubjectiveMemCreateResult(
            "integrity_conflict",
            blocked_reasons=("subjective_mem_operation_idempotency_conflict",),
        )
    if (
        existing.get("decision_id") != expected_decision_id
        or existing.get("receipt_id") != expected_receipt_id
        or existing.get("memory_id") != expected_memory_id
        or existing.get("prepared_revision_record_id")
        != expected_prepared_revision_record_id
        or existing.get("prepared_manifest_id")
        != expected_prepared_manifest_id
        or existing.get("current_state_key") != expected_current_state_key
    ):
        return SubjectiveMemCreateResult(
            "fail_closed",
            blocked_reasons=("subjective_mem_operation_result_identity_invalid",),
        )
    if (
        existing.get("memory_revision") != 1
        or existing.get("mutation_state") != "prepared"
        or existing.get("retrieval_eligible") is not False
        or existing.get("canonical_publication") is not False
        or existing.get("st1_finalization_required") is not True
        or existing.get("outcome") != "create"
    ):
        return SubjectiveMemCreateResult(
            "fail_closed", blocked_reasons=("subjective_mem_operation_result_invalid",)
        )
    receipt_raw = tx.read_record(
        record_kind="shared_assessment_formation_receipt",
        record_id=str(existing["receipt_id"]),
    )
    decision_raw = tx.read_record(
        record_kind="subjective_mem_decision",
        record_id=str(existing["decision_id"]),
    )
    revision_raw = tx.read_record(
        record_kind="subjective_mem_prepared_revision",
        record_id=str(existing["prepared_revision_record_id"]),
    )
    manifest_raw = tx.read_record(
        record_kind="subjective_mem_prepared_manifest",
        record_id=str(existing["prepared_manifest_id"]),
    )
    state_raw = tx.read_log(
        log_kind="subjective_mem_current_state",
        key=str(existing["current_state_key"]),
    )
    parsed = _parse_existing_bundle(
        receipt_raw=receipt_raw,
        decision_raw=decision_raw,
        revision_raw=revision_raw,
        manifest_raw=manifest_raw,
        state_raw=state_raw,
    )
    if parsed is None:
        return SubjectiveMemCreateResult(
            "fail_closed", blocked_reasons=("subjective_mem_operation_result_corrupt",)
        )
    receipt, decision, revision, manifest, current_state = parsed
    uniqueness_reasons = _validate_current_state_uniqueness(
        tx=tx,
        expected_key=expected_current_state_key,
        expected_current_state=current_state,
        require_expected=True,
    )
    if uniqueness_reasons:
        return SubjectiveMemCreateResult(
            "fail_closed", blocked_reasons=uniqueness_reasons
        )
    finalized_current_state = (
        current_state.memory_state_id == expected_current_state.memory_state_id
        and current_state.memory_id == expected_current_state.memory_id
        and current_state.character_id == expected_current_state.character_id
        and current_state.mutation_state == "none"
        and current_state.retrieval_eligible is True
    )
    prepared_current_state = (
        current_state.to_dict() == expected_current_state.to_dict()
    )
    if (
        decision.to_dict() != expected_decision.to_dict()
        or revision.to_dict() != expected_revision.to_dict()
        or manifest.to_dict() != expected_manifest.to_dict()
        or not (prepared_current_state or finalized_current_state)
    ):
        return SubjectiveMemCreateResult(
            "fail_closed",
            blocked_reasons=("subjective_mem_operation_result_input_mismatch",),
        )
    assessment_raw = tx.read_record(
        record_kind="shared_assessment_revision",
        record_id=shared_assessment_revision_record_id(
            revision.assessment_id, revision.assessment_revision
        ),
    )
    if (
        not isinstance(assessment_raw, dict)
        or assessment_raw.get("assessment_id") != revision.assessment_id
        or assessment_raw.get("assessment_revision")
        != revision.assessment_revision
        or assessment_raw.get("supported_content") != revision.grounded_content
        or assessment_raw.get("supported_content_digest")
        != revision.grounded_content_digest
    ):
        return SubjectiveMemCreateResult(
            "fail_closed",
            blocked_reasons=("subjective_mem_operation_grounding_invalid",),
        )
    if (
        canonical_digest(revision.to_dict()) != existing["prepared_revision_digest"]
        or manifest.to_dict()["manifest_digest"] != existing["prepared_manifest_digest"]
        or decision.decision_id != existing["decision_id"]
        or receipt.receipt_id != existing["receipt_id"]
        or receipt.decision_input_digest != expected_input_digest
        or revision.memory_id != existing["memory_id"]
        or decision.decided_at != existing["committed_at"]
    ):
        return SubjectiveMemCreateResult(
            "fail_closed", blocked_reasons=("subjective_mem_operation_result_crosslink_invalid",)
        )
    reasons = validate_subjective_mem_crosslinks(
        receipt=receipt,
        decision=decision,
        revision=revision,
        current_state=expected_current_state,
        manifest=manifest,
    )
    if reasons:
        return SubjectiveMemCreateResult("fail_closed", blocked_reasons=reasons)
    return SubjectiveMemCreateResult(
        "duplicate_finalized" if finalized_current_state else "duplicate_existing",
        decision=decision,
        revision=revision,
        current_state=current_state,
        prepared_manifest=manifest,
        formation_receipt=receipt,
        finalization_id=(
            _opaque("st1fin", expected_operation_id)
            if finalized_current_state
            else None
        ),
        persisted=True,
    )


def _parse_existing_bundle(*, receipt_raw, decision_raw, revision_raw, manifest_raw, state_raw):
    if not all(isinstance(item, dict) for item in (receipt_raw, decision_raw, revision_raw, manifest_raw)):
        return None
    if not isinstance(state_raw, list) or len(state_raw) != 1 or not isinstance(state_raw[0], dict):
        return None
    try:
        if receipt_raw["schema"] != SHARED_ASSESSMENT_FORMATION_RECEIPT_SCHEMA:
            return None
        receipt = SharedAssessmentFormationAuthorizationReceipt(
            schema=receipt_raw["schema"],
            receipt_id=receipt_raw["receipt_id"],
            assessment_id=receipt_raw["assessment_id"],
            assessment_revision=receipt_raw["assessment_revision"],
            supported_content_digest=receipt_raw["supported_content_digest"],
            current_revision_at_decision=receipt_raw["assessment_authorization_receipt"]["current_revision_at_decision"],
            lifecycle_state_at_decision=receipt_raw["assessment_authorization_receipt"]["lifecycle_state_at_decision"],
            authorization_state_at_decision=receipt_raw["assessment_authorization_receipt"]["authorization_state_at_decision"],
            evidence_authority_snapshot_digests=tuple(receipt_raw["evidence_authority_snapshot_digests"]),
            decision_id=receipt_raw["decision_id"],
            decision_input_digest=receipt_raw["decision_input_digest"],
            issued_at=receipt_raw["issued_at"],
            receipt_digest=receipt_raw["receipt_digest"],
        )
        if receipt.to_dict() != receipt_raw or not receipt.is_self_authenticating():
            return None
        assessment = decision_raw["assessment_ref"]
        result_ref = decision_raw["result_memory_ref_or_null"]
        decision = SubjectiveMemDecision(
            decision_id=decision_raw["decision_id"],
            character_id=decision_raw["character_id"],
            assessment_id=assessment["assessment_id"],
            assessment_revision=assessment["assessment_revision"],
            supported_content_digest=assessment["supported_content_digest"],
            assessment_authorization_receipt=(
                SubjectiveMemAssessmentAuthorizationProjection(
                    **decision_raw["assessment_authorization_receipt"]
                )
            ),
            scope_binding=SubjectiveMemScopeBinding(**decision_raw["scope_binding"]),
            result_memory_id=result_ref["memory_id"],
            decided_at=decision_raw["decided_at"],
        )
        if decision.to_dict() != decision_raw:
            return None
        grounded = revision_raw["grounded_assessment_ref"]
        snapshot = SubjectiveMemFormationSnapshot(**revision_raw["formation_snapshot"])
        strength = SubjectiveMemStrength(**revision_raw["strength"])
        revision = SubjectiveMemRevision(
            memory_id=revision_raw["memory_id"],
            character_id=revision_raw["character_id"],
            assessment_id=grounded["assessment_id"],
            assessment_revision=grounded["assessment_revision"],
            grounded_content=revision_raw["grounded_content"],
            grounded_content_digest=revision_raw["grounded_content_digest"],
            subjective_meaning=revision_raw["subjective_meaning"],
            memory_kind=revision_raw["memory_kind"],
            scope_binding=SubjectiveMemScopeBinding(**revision_raw["scope_binding"]),
            formation_snapshot=snapshot,
            strength=strength,
            decision_id=revision_raw["authorization_ref"]["authority_id"],
            created_at=revision_raw["created_at"],
        )
        if revision.to_dict() != revision_raw:
            return None
        current = state_raw[0]
        current_state = SubjectiveMemCurrentState(
            memory_state_id=current["memory_state_id"],
            memory_id=current["memory_id"],
            character_id=current["character_id"],
            updated_at=current["updated_at"],
            mutation_state=current["mutation_state"],
            retrieval_eligible=current["retrieval_eligible"],
        )
        if current_state.to_dict() != current:
            return None
        if manifest_raw["schema"] != SUBJECTIVE_MEM_PREPARED_MANIFEST_SCHEMA:
            return None
        manifest = SubjectiveMemPreparedManifest(
            prepared_manifest_id=manifest_raw["prepared_manifest_id"],
            prepared_revision_record_id=manifest_raw["prepared_revision_record_id"],
            prepared_revision_digest=manifest_raw["prepared_revision_digest"],
            decision_id=manifest_raw["decision_id"],
            memory_id=manifest_raw["memory_ref"]["memory_id"],
            character_id=manifest_raw["character_id"],
            prepared_at=manifest_raw["prepared_at"],
        )
        if manifest.to_dict() != manifest_raw:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return receipt, decision, revision, manifest, current_state


def load_subjective_mem_persisted_bundle(
    *, tx: EvidenceStoreTransaction, operation: dict
) -> tuple[SubjectiveMemPersistedBundle | None, tuple[str, ...]]:
    required_ids = (
        "receipt_id",
        "decision_id",
        "prepared_revision_record_id",
        "prepared_manifest_id",
        "current_state_key",
    )
    if not isinstance(operation, dict) or any(
        not _token(operation.get(name)) for name in required_ids
    ):
        return None, ("subjective_mem_operation_result_identity_invalid",)
    parsed = _parse_existing_bundle(
        receipt_raw=tx.read_record(
            record_kind="shared_assessment_formation_receipt",
            record_id=str(operation["receipt_id"]),
        ),
        decision_raw=tx.read_record(
            record_kind="subjective_mem_decision",
            record_id=str(operation["decision_id"]),
        ),
        revision_raw=tx.read_record(
            record_kind="subjective_mem_prepared_revision",
            record_id=str(operation["prepared_revision_record_id"]),
        ),
        manifest_raw=tx.read_record(
            record_kind="subjective_mem_prepared_manifest",
            record_id=str(operation["prepared_manifest_id"]),
        ),
        state_raw=tx.read_log(
            log_kind="subjective_mem_current_state",
            key=str(operation["current_state_key"]),
        ),
    )
    if parsed is None:
        return None, ("subjective_mem_operation_result_corrupt",)
    receipt, decision, revision, manifest, current_state = parsed
    return (
        SubjectiveMemPersistedBundle(
            formation_receipt=receipt,
            decision=decision,
            revision=revision,
            prepared_manifest=manifest,
            current_state=current_state,
        ),
        (),
    )


def validate_subjective_mem_current_state_uniqueness(
    *,
    tx: EvidenceStoreTransaction,
    expected_key: str,
    expected_current_state: SubjectiveMemCurrentState,
    require_expected: bool = True,
) -> tuple[str, ...]:
    return _validate_current_state_uniqueness(
        tx=tx,
        expected_key=expected_key,
        expected_current_state=expected_current_state,
        require_expected=require_expected,
    )


def _opaque(prefix: str, value: str) -> str:
    return f"{prefix}_{sha256_hex(value.encode('utf-8'))}"


def _token(value: object, max_length: int = 128) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= max_length and all(
        ch not in value for ch in ("/", "\\", "\x00")
    )


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("subjective_mem_naive_datetime_forbidden")
    return value.astimezone(timezone.utc)


__all__ = [
    "SubjectiveMemCreateGate",
    "SubjectiveMemCreateResult",
    "SubjectiveMemOperationIdentity",
    "SubjectiveMemPersistedBundle",
    "create_subjective_mem",
    "derive_subjective_mem_operation_identity",
    "load_subjective_mem_persisted_bundle",
    "resolve_subjective_mem_create_gate",
    "validate_subjective_mem_current_state_uniqueness",
]
