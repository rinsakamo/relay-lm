"""ST-1 caller-invoked canonical publication and durable finalization.

This module consumes exactly one persisted SM-1 create operation.  It publishes
one deterministic canonical Markdown page post-image and finalizes content-free
operations records.  It does not wire ordinary Retrieval, projections, queues,
workers, schedulers, lifecycle operations, or Primary MEM migration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from relaylm.subjective_mem.commit_io import (
    PLATFORM_REVISION,
    inspect_canonical_page,
    publish_canonical_page,
    read_immutable_rendered_artifact,
    secure_platform_supported,
    write_immutable_rendered_artifact,
)
from relaylm.evidence.common import canonical_digest, sha256_hex
from relaylm.evidence.store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.shared_assessment.runtime import shared_assessment_revision_record_id
from relaylm.subjective_mem.models import (
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
    resolve_subjective_mem_character_authority,
    validate_subjective_mem_crosslinks,
)
from relaylm.subjective_mem.commit import (
    ST1_INTENT_SCHEMA,
    SubjectiveMemCommitReceipt,
    SubjectiveMemFinalizationRecords,
    SubjectiveMemPublicationIntent,
    build_finalization_records,
)
from relaylm.subjective_mem.markdown import (
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    SubjectiveMemPagePlan,
    canonical_page_digest,
    parse_subjective_mem_page_bytes,
    plan_subjective_mem_page,
    subjective_mem_page_identity,
)
from relaylm.subjective_mem.create_runtime import (
    SubjectiveMemOperationIdentity,
    SubjectiveMemPersistedBundle,
    derive_subjective_mem_operation_identity,
    load_subjective_mem_persisted_bundle,
    validate_subjective_mem_current_state_uniqueness,
)

CommitStatus = Literal[
    "disabled",
    "dry_run_ready",
    "committed",
    "duplicate_finalized",
    "recovery_pending",
    "recovery_required",
    "lock_busy",
    "fail_closed",
    "integrity_conflict",
]
FaultInjector = Callable[[str], None]

_OPERATION_REQUIRED_FIELDS = frozenset(
    {
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
)


@dataclass(frozen=True)
class SubjectiveMemCommitGate:
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    store: EvidenceRecordStore | None
    workspace_root: str | None


@dataclass(frozen=True, repr=False)
class SubjectiveMemCommitResult:
    status: CommitStatus
    finalization_id: str | None = None
    receipt: SubjectiveMemCommitReceipt | None = None
    current_state: SubjectiveMemCurrentState | None = None
    page_id: str | None = None
    block_id: str | None = None
    memory_id: str | None = None
    blocked_reasons: tuple[str, ...] = ()
    recovery_outcome: str | None = None
    canonical_markdown_published: bool = False
    commit_receipt_present: bool = False
    persisted: bool = False
    _post_image_digest: str | None = field(default=None, repr=False, compare=False)

    def to_log_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "blocked_reasons": list(self.blocked_reasons),
            "finalization_id": self.finalization_id,
            "memory_id": self.memory_id,
            "page_id": self.page_id,
            "block_id": self.block_id,
            "memory_revision": 1 if self.memory_id else None,
            "mutation_state": (
                self.current_state.mutation_state if self.current_state else None
            ),
            "retrieval_eligible": (
                self.current_state.retrieval_eligible
                if self.current_state
                else False
            ),
            "canonical_markdown_published": self.canonical_markdown_published,
            "commit_receipt_present": self.commit_receipt_present,
            "projection_state": (
                "rebuild_required" if self.commit_receipt_present else None
            ),
            "ordinary_retrieval_wired": False,
            "recovery_outcome": self.recovery_outcome,
            "persisted": self.persisted,
            "content_free": True,
            "path_values_included": False,
            "digest_values_included": False,
            "raw_key_included": False,
            "exception_text_included": False,
        }


@dataclass(frozen=True)
class _LoadedOperation:
    operation: dict
    bundle: SubjectiveMemPersistedBundle
    finalization_id: str
    intent_id: str
    receipt_id: str


@dataclass
class _FinalizationOutcome:
    ok: bool = False
    duplicate: bool = False
    records: SubjectiveMemFinalizationRecords | None = None
    reasons: tuple[str, ...] = ()


def resolve_subjective_mem_commit_gate(config: object) -> SubjectiveMemCommitGate:
    enabled = getattr(config, "subjective_mem_commit_enabled", False)
    dry_run_only = getattr(config, "subjective_mem_commit_dry_run_only", True)
    requested_apply = getattr(
        config, "subjective_mem_commit_apply_enabled", False
    )
    triple = (enabled, dry_run_only, requested_apply)
    if any(type(item) is not bool for item in triple) or triple not in {
        (False, True, False),
        (True, True, False),
        (True, False, True),
    }:
        return SubjectiveMemCommitGate(bool(enabled), True, False, None, None)
    workspace_root = getattr(config, "subjective_mem_workspace_root", None)
    if not enabled:
        return SubjectiveMemCommitGate(False, True, False, None, None)
    evidence_root = getattr(config, "evidence_data_root", None)
    store = None
    if isinstance(evidence_root, str) and evidence_root:
        try:
            store = EvidenceRecordStore(evidence_root)
        except ValueError:
            store = None
    workspace_valid = (
        isinstance(workspace_root, str)
        and bool(workspace_root)
        and Path(workspace_root).is_absolute()
        and not any(part in {".", ".."} for part in Path(workspace_root).parts[1:])
    )
    sm1_triple = (
        getattr(config, "subjective_mem_create_enabled", False),
        getattr(config, "subjective_mem_create_dry_run_only", True),
        getattr(config, "subjective_mem_create_apply_enabled", False),
    )
    apply_enabled = (
        requested_apply
        and not dry_run_only
        and sm1_triple == (True, False, True)
        and store is not None
        and workspace_valid
        and secure_platform_supported()
    )
    return SubjectiveMemCommitGate(
        True,
        dry_run_only,
        apply_enabled,
        store,
        workspace_root if workspace_valid else None,
    )


def finalize_subjective_mem_create(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_config: object,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    sm1_operation_idempotency_key: str,
    apply_enabled: bool,
    finalized_at: datetime,
    observed_at: datetime | None = None,
    fault_injector: FaultInjector | None = None,
) -> SubjectiveMemCommitResult:
    """Publish or recover one exact SM-1 create operation."""

    reasons: list[str] = []
    if type(store) is not EvidenceRecordStore:
        reasons.append("subjective_mem_commit_store_invalid")
    if type(character_authority) is not SubjectiveMemCharacterAuthority:
        reasons.append("subjective_mem_commit_character_authority_invalid")
    else:
        resolved, authority_reasons = resolve_subjective_mem_character_authority(
            character_config,
            workspace_or_tenant_ref=character_authority.workspace_or_tenant_ref,
            character_id=character_authority.character_id,
        )
        reasons.extend(authority_reasons)
        if resolved != character_authority:
            reasons.append("subjective_mem_commit_character_authority_not_exact_current")
    if type(apply_enabled) is not bool:
        reasons.append("subjective_mem_commit_apply_mode_invalid")
    if type(workspace_root) is not str or not workspace_root:
        reasons.append("subjective_mem_commit_workspace_root_missing")
    elif not Path(workspace_root).is_absolute():
        reasons.append("subjective_mem_commit_workspace_root_not_absolute")
    elif not _configured_workspace_root_matches(
        character_config=character_config, workspace_root=workspace_root
    ):
        reasons.append("subjective_mem_commit_workspace_authority_changed")
    if fault_injector is not None and not callable(fault_injector):
        reasons.append("subjective_mem_commit_fault_injector_invalid")
    try:
        final_time = _utc(finalized_at)
        observed_time = _utc(
            observed_at if observed_at is not None else datetime.now(timezone.utc)
        )
        if final_time > observed_time:
            reasons.append("subjective_mem_commit_time_in_future")
    except (TypeError, ValueError):
        final_time = None
        reasons.append("subjective_mem_commit_clock_invalid")
    try:
        identity = derive_subjective_mem_operation_identity(
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            operation_idempotency_key=sm1_operation_idempotency_key,
        )
    except (TypeError, ValueError):
        identity = None
        reasons.append("subjective_mem_commit_operation_identity_invalid")
    if reasons:
        return _result("fail_closed", reasons=tuple(dict.fromkeys(reasons)))
    assert final_time is not None and identity is not None

    workspace_authority_digest = _workspace_authority_digest(
        workspace_root=workspace_root,
        character_authority=character_authority,
    )
    loaded, reasons = _load_operation_from_store(
        store=store,
        evidence_space_id=evidence_space_id,
        identity=identity,
        character_authority=character_authority,
    )
    if loaded is None:
        return _result(_reason_status(reasons), reasons=reasons)

    if loaded.bundle.current_state.mutation_state == "none":
        return _validate_finalized_after_unlock(
            store=store,
            evidence_space_id=evidence_space_id,
            loaded=loaded,
            workspace_root=workspace_root,
            workspace_authority_digest=workspace_authority_digest,
        )

    intent_raw = store.read_record(
        evidence_space_id=evidence_space_id,
        record_kind="subjective_mem_st1_intent",
        record_id=loaded.intent_id,
    )
    intent = _intent_from_dict(intent_raw) if intent_raw is not None else None
    if intent_raw is not None and intent is None:
        return _result(
            "fail_closed",
            loaded=loaded,
            reasons=("subjective_mem_commit_intent_corrupt",),
        )

    if intent is None:
        page_id, relative_path, partition = subjective_mem_page_identity(
            character_id=loaded.bundle.revision.character_id,
            memory_kind=loaded.bundle.revision.memory_kind,
        )
        inspected = inspect_canonical_page(
            workspace_root=workspace_root,
            character_id=character_authority.character_id,
            relative_path=relative_path,
        )
        if inspected.snapshot is None:
            return _result(
                "fail_closed", loaded=loaded, reasons=inspected.reasons
            )
        page_plan_result = plan_subjective_mem_page(
            revision=loaded.bundle.revision,
            existing_bytes=inspected.snapshot.data,
        )
        if page_plan_result.plan is None:
            return _result(
                _reason_status(page_plan_result.reasons),
                loaded=loaded,
                reasons=page_plan_result.reasons,
            )
        plan = page_plan_result.plan
        if (
            plan.page_id != page_id
            or plan.relative_path != relative_path
            or plan.partition != partition
        ):
            return _result(
                "fail_closed",
                loaded=loaded,
                reasons=("subjective_mem_commit_page_plan_identity_invalid",),
            )
        intent = _build_intent(
            loaded=loaded,
            identity=identity,
            workspace_authority_digest=workspace_authority_digest,
            plan=plan,
            prepared_at=final_time.isoformat(),
        )
        if not apply_enabled:
            return _result(
                "dry_run_ready",
                loaded=loaded,
                intent=intent,
                recovery_outcome="new_intent_ready",
            )
        artifact_result = write_immutable_rendered_artifact(
            workspace_root=workspace_root,
            character_id=character_authority.character_id,
            artifact_id=plan.artifact_id,
            data=plan.rendered_bytes,
        )
        if artifact_result.status not in {"created", "duplicate_existing"}:
            return _result(
                "fail_closed",
                loaded=loaded,
                intent=intent,
                reasons=artifact_result.reasons,
            )
        try:
            _fault(fault_injector, "after_artifact_before_intent")
        except Exception:
            return _result(
                "fail_closed",
                loaded=loaded,
                intent=intent,
                reasons=("subjective_mem_commit_fault_before_intent",),
            )
        persisted_intent, reasons = _persist_intent(
            store=store,
            evidence_space_id=evidence_space_id,
            identity=identity,
            character_authority=character_authority,
            expected_loaded=loaded,
            intent=intent,
        )
        if persisted_intent is None:
            return _result(
                _reason_status(reasons),
                loaded=loaded,
                intent=intent,
                reasons=reasons,
            )
        intent = persisted_intent
    else:
        reasons = _validate_intent_binding(
            intent=intent,
            loaded=loaded,
            identity=identity,
            workspace_authority_digest=workspace_authority_digest,
        )
        if reasons:
            return _result(
                _reason_status(reasons), loaded=loaded, intent=intent, reasons=reasons
            )
        if not apply_enabled:
            return _classify_existing_intent_dry_run(
                loaded=loaded,
                intent=intent,
                workspace_root=workspace_root,
            )

    artifact, reasons = read_immutable_rendered_artifact(
        workspace_root=workspace_root,
        character_id=character_authority.character_id,
        artifact_id=intent.artifact_id,
    )
    if artifact is None:
        return _result(
            "recovery_required",
            loaded=loaded,
            intent=intent,
            reasons=reasons or ("subjective_mem_commit_artifact_missing",),
            recovery_outcome="artifact_unverifiable",
        )
    if (
        canonical_page_digest(artifact) != intent.artifact_digest
        or intent.artifact_digest != intent.post_image_digest
    ):
        return _result(
            "recovery_required",
            loaded=loaded,
            intent=intent,
            reasons=("subjective_mem_commit_artifact_digest_mismatch",),
            recovery_outcome="artifact_unverifiable",
        )

    finalization_outcome = _FinalizationOutcome()

    def verify_installed(data: bytes) -> bool:
        return _verify_exact_post_image(
            data=data, intent=intent, loaded=loaded
        )

    def finalize_installed() -> bool:
        try:
            _fault(fault_injector, "after_page_before_receipt")
        except Exception:
            finalization_outcome.reasons = (
                "subjective_mem_commit_fault_after_page_before_receipt",
            )
            return False
        outcome = _finalize_operations(
            store=store,
            evidence_space_id=evidence_space_id,
            identity=identity,
            character_authority=character_authority,
            expected_loaded=loaded,
            intent=intent,
            finalized_at=intent.prepared_at,
        )
        finalization_outcome.ok = outcome.ok
        finalization_outcome.duplicate = outcome.duplicate
        finalization_outcome.records = outcome.records
        finalization_outcome.reasons = outcome.reasons
        return outcome.ok

    publish = publish_canonical_page(
        workspace_root=workspace_root,
        character_id=character_authority.character_id,
        relative_path=intent.target_relative_path,
        expected_pre_state=intent.pre_image_state,  # type: ignore[arg-type]
        expected_pre_digest=intent.pre_image_digest,
        post_image=artifact,
        expected_post_digest=intent.post_image_digest,
        verify_installed=verify_installed,
        finalize_installed=finalize_installed,
        fault_injector=fault_injector,
    )
    if publish.status == "lock_busy":
        return _result(
            "lock_busy", loaded=loaded, intent=intent, reasons=publish.reasons
        )
    if publish.status == "pre_image_conflict":
        return _result(
            "recovery_required",
            loaded=loaded,
            intent=intent,
            reasons=publish.reasons,
            recovery_outcome="foreign_image",
        )
    if not finalization_outcome.ok:
        inspected = inspect_canonical_page(
            workspace_root=workspace_root,
            character_id=character_authority.character_id,
            relative_path=intent.target_relative_path,
        )
        page_is_post = (
            inspected.snapshot is not None
            and inspected.snapshot.digest == intent.post_image_digest
            and inspected.snapshot.data is not None
            and verify_installed(inspected.snapshot.data)
        )
        if page_is_post:
            return _result(
                "recovery_pending",
                loaded=loaded,
                intent=intent,
                reasons=finalization_outcome.reasons
                or publish.reasons
                or ("subjective_mem_commit_receipt_missing",),
                recovery_outcome="post_image_pending_receipt",
                canonical_published=publish.durability_confirmed,
            )
        return _result(
            "fail_closed",
            loaded=loaded,
            intent=intent,
            reasons=publish.reasons
            or finalization_outcome.reasons
            or ("subjective_mem_commit_publication_failed",),
        )
    assert finalization_outcome.records is not None
    records = finalization_outcome.records
    return _result(
        "duplicate_finalized" if finalization_outcome.duplicate else "committed",
        loaded=loaded,
        intent=intent,
        receipt=records.receipt,
        current_state=records.current_state,
        recovery_outcome=(
            "post_image_rolled_forward"
            if publish.status == "already_post_image"
            else "published_and_finalized"
        ),
        canonical_published=True,
        receipt_present=True,
        persisted=True,
    )


def validate_finalized_subjective_mem_operation(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_config: object,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    sm1_operation_idempotency_key: str,
) -> SubjectiveMemCommitResult:
    """Validate a finalized result after the caller has released store locks."""

    if not _configured_workspace_root_matches(
        character_config=character_config, workspace_root=workspace_root
    ):
        return _result(
            "fail_closed",
            reasons=("subjective_mem_commit_workspace_authority_changed",),
        )
    try:
        identity = derive_subjective_mem_operation_identity(
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            operation_idempotency_key=sm1_operation_idempotency_key,
        )
    except (TypeError, ValueError):
        return _result(
            "fail_closed",
            reasons=("subjective_mem_commit_operation_identity_invalid",),
        )
    resolved, reasons = resolve_subjective_mem_character_authority(
        character_config,
        workspace_or_tenant_ref=character_authority.workspace_or_tenant_ref,
        character_id=character_authority.character_id,
    )
    if reasons or resolved != character_authority:
        return _result(
            "fail_closed",
            reasons=("subjective_mem_commit_character_authority_not_exact_current",),
        )
    loaded, reasons = _load_operation_from_store(
        store=store,
        evidence_space_id=evidence_space_id,
        identity=identity,
        character_authority=character_authority,
    )
    if loaded is None:
        return _result(_reason_status(reasons), reasons=reasons)
    if loaded.bundle.current_state.mutation_state != "none":
        return _result(
            "fail_closed",
            loaded=loaded,
            reasons=("subjective_mem_commit_not_finalized",),
        )
    return _validate_finalized_after_unlock(
        store=store,
        evidence_space_id=evidence_space_id,
        loaded=loaded,
        workspace_root=workspace_root,
        workspace_authority_digest=_workspace_authority_digest(
            workspace_root=workspace_root,
            character_authority=character_authority,
        ),
    )


def _load_operation_from_store(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    identity: SubjectiveMemOperationIdentity,
    character_authority: SubjectiveMemCharacterAuthority,
) -> tuple[_LoadedOperation | None, tuple[str, ...]]:
    try:
        with store.transaction(evidence_space_id) as tx:
            operation = tx.read_record(
                record_kind="subjective_mem_operation",
                record_id=identity.operation_slot_id,
            )
            if operation is None:
                return None, ("subjective_mem_commit_sm1_operation_missing",)
            return _load_operation_locked(
                tx=tx,
                operation=operation,
                identity=identity,
                character_authority=character_authority,
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_commit_store_unavailable",)


def _load_operation_locked(
    *,
    tx: EvidenceStoreTransaction,
    operation: dict,
    identity: SubjectiveMemOperationIdentity,
    character_authority: SubjectiveMemCharacterAuthority,
) -> tuple[_LoadedOperation | None, tuple[str, ...]]:
    if (
        set(operation) != _OPERATION_REQUIRED_FIELDS
        or operation.get("schema") != "relaylm.subjective_mem_operation.v1"
    ):
        return None, ("subjective_mem_commit_sm1_operation_corrupt",)
    if (
        operation.get("operation_slot_id") != identity.operation_slot_id
        or operation.get("operation_id") != identity.operation_id
        or operation.get("operation_idempotency_key_digest")
        != identity.operation_key_digest
        or operation.get("character_authority_digest")
        != identity.character_authority_digest
        or operation.get("character_id") != character_authority.character_id
        or operation.get("evidence_space_id") != tx.evidence_space_id
    ):
        return None, ("subjective_mem_commit_sm1_operation_scope_mismatch",)
    if (
        operation.get("outcome") != "create"
        or operation.get("memory_revision") != 1
        or operation.get("mutation_state") != "prepared"
        or operation.get("retrieval_eligible") is not False
        or operation.get("canonical_publication") is not False
        or operation.get("st1_finalization_required") is not True
    ):
        return None, ("subjective_mem_commit_sm1_operation_unsupported",)
    bundle, reasons = load_subjective_mem_persisted_bundle(
        tx=tx, operation=operation
    )
    if bundle is None:
        return None, reasons
    revision_raw = bundle.revision.to_dict()
    state_raw = bundle.current_state.to_dict()
    manifest_raw = bundle.prepared_manifest.to_dict()
    if (
        revision_raw.get("memory_revision") != 1
        or revision_raw.get("lifecycle_state") != "active"
        or revision_raw.get("retrieval_visible") is not True
        or revision_raw.get("formation_stage") != "primary"
        or revision_raw.get("predecessor_revision_or_null") is not None
        or manifest_raw.get("publication_state") != "prepared_noncanonical"
        or manifest_raw.get("canonical_markdown_published") is not False
        or manifest_raw.get("commit_receipt_present") is not False
        or manifest_raw.get("st1_finalization_required") is not True
    ):
        return None, ("subjective_mem_commit_sm1_prepared_shape_unsupported",)
    if (
        state_raw.get("mutation_state"), state_raw.get("retrieval_eligible")
    ) not in {("prepared", False), ("none", True)}:
        return None, ("subjective_mem_commit_current_state_invalid",)
    if (
        operation.get("decision_id") != bundle.decision.decision_id
        or operation.get("receipt_id") != bundle.formation_receipt.receipt_id
        or operation.get("memory_id") != bundle.revision.memory_id
        or operation.get("prepared_revision_digest")
        != canonical_digest(revision_raw)
        or operation.get("prepared_manifest_digest")
        != manifest_raw.get("manifest_digest")
        or operation.get("prepared_manifest_id")
        != bundle.prepared_manifest.prepared_manifest_id
        or operation.get("prepared_revision_record_id")
        != bundle.prepared_manifest.prepared_revision_record_id
        or operation.get("current_state_key")
        != bundle.current_state.memory_state_id
    ):
        return None, ("subjective_mem_commit_sm1_crosslink_invalid",)
    prepared_state = SubjectiveMemCurrentState(
        memory_state_id=bundle.current_state.memory_state_id,
        memory_id=bundle.current_state.memory_id,
        character_id=bundle.current_state.character_id,
        updated_at=str(operation["committed_at"]),
    )
    crosslink_reasons = validate_subjective_mem_crosslinks(
        receipt=bundle.formation_receipt,
        decision=bundle.decision,
        revision=bundle.revision,
        current_state=prepared_state,
        manifest=bundle.prepared_manifest,
    )
    if crosslink_reasons:
        return None, crosslink_reasons
    uniqueness = validate_subjective_mem_current_state_uniqueness(
        tx=tx,
        expected_key=str(operation["current_state_key"]),
        expected_current_state=bundle.current_state,
        require_expected=True,
    )
    if uniqueness:
        return None, uniqueness
    assessment_raw = tx.read_record(
        record_kind="shared_assessment_revision",
        record_id=shared_assessment_revision_record_id(
            bundle.revision.assessment_id,
            bundle.revision.assessment_revision,
        ),
    )
    if (
        not isinstance(assessment_raw, dict)
        or assessment_raw.get("supported_content")
        != bundle.revision.grounded_content
        or assessment_raw.get("supported_content_digest")
        != bundle.revision.grounded_content_digest
    ):
        return None, ("subjective_mem_commit_grounding_invalid",)
    finalization_id = _opaque("st1fin", identity.operation_id)
    return (
        _LoadedOperation(
            operation=operation,
            bundle=bundle,
            finalization_id=finalization_id,
            intent_id=_opaque("st1intent", finalization_id),
            receipt_id=_opaque("st1receipt", finalization_id),
        ),
        (),
    )


def _build_intent(
    *,
    loaded: _LoadedOperation,
    identity: SubjectiveMemOperationIdentity,
    workspace_authority_digest: str,
    plan: SubjectiveMemPagePlan,
    prepared_at: str,
) -> SubjectiveMemPublicationIntent:
    operation = loaded.operation
    return SubjectiveMemPublicationIntent(
        intent_id=loaded.intent_id,
        finalization_id=loaded.finalization_id,
        sm1_operation_slot_id=identity.operation_slot_id,
        sm1_operation_id=identity.operation_id,
        sm1_operation_key_digest=identity.operation_key_digest,
        evidence_space_id=str(operation["evidence_space_id"]),
        character_id=loaded.bundle.revision.character_id,
        character_authority_digest=identity.character_authority_digest,
        workspace_authority_digest=workspace_authority_digest,
        memory_id=loaded.bundle.revision.memory_id,
        decision_id=loaded.bundle.decision.decision_id,
        prepared_revision_record_id=str(operation["prepared_revision_record_id"]),
        prepared_revision_digest=str(operation["prepared_revision_digest"]),
        prepared_manifest_id=str(operation["prepared_manifest_id"]),
        prepared_manifest_digest=str(operation["prepared_manifest_digest"]),
        target_page_id=plan.page_id,
        target_relative_path=plan.relative_path,
        memory_block_id=plan.block_id,
        memory_block_anchor=plan.anchor,
        pre_image_state=plan.pre_image_state,
        pre_image_digest=plan.pre_image_digest,
        post_image_digest=plan.post_image_digest,
        block_digest=plan.block_digest,
        artifact_id=plan.artifact_id,
        artifact_digest=plan.post_image_digest,
        page_schema=PAGE_SCHEMA,
        renderer_revision=RENDERER_REVISION,
        partition_revision=PAGE_PARTITION_REVISION,
        platform_revision=PLATFORM_REVISION,
        prepared_at=prepared_at,
    )


def _persist_intent(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    identity: SubjectiveMemOperationIdentity,
    character_authority: SubjectiveMemCharacterAuthority,
    expected_loaded: _LoadedOperation,
    intent: SubjectiveMemPublicationIntent,
) -> tuple[SubjectiveMemPublicationIntent | None, tuple[str, ...]]:
    try:
        with store.transaction(evidence_space_id) as tx:
            operation = tx.read_record(
                record_kind="subjective_mem_operation",
                record_id=identity.operation_slot_id,
            )
            if operation is None:
                return None, ("subjective_mem_commit_sm1_operation_missing",)
            loaded, reasons = _load_operation_locked(
                tx=tx,
                operation=operation,
                identity=identity,
                character_authority=character_authority,
            )
            if loaded is None:
                return None, reasons
            if (
                loaded.bundle.current_state.mutation_state != "prepared"
                or loaded.bundle.current_state.retrieval_eligible is not False
                or loaded.operation != expected_loaded.operation
            ):
                return None, ("subjective_mem_commit_sm1_operation_changed",)
            existing = tx.read_record(
                record_kind="subjective_mem_st1_intent",
                record_id=intent.intent_id,
            )
            if existing is not None:
                parsed = _intent_from_dict(existing)
                if parsed is None or parsed.to_dict() != intent.to_dict():
                    return None, ("subjective_mem_commit_intent_conflict",)
                return parsed, ()
            commit = tx.commit(
                transaction_id=_opaque("st1intenttx", intent.finalization_id),
                records=(("subjective_mem_st1_intent", intent.intent_id, intent.to_dict()),),
                logs=(),
            )
            if commit.status == "collision":
                return None, ("subjective_mem_commit_intent_conflict",)
            if commit.status not in {"created", "duplicate_existing"}:
                return None, commit.reasons or (
                    "subjective_mem_commit_intent_persist_failed",
                )
            return intent, ()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_commit_store_unavailable",)


def _finalize_operations(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    identity: SubjectiveMemOperationIdentity,
    character_authority: SubjectiveMemCharacterAuthority,
    expected_loaded: _LoadedOperation,
    intent: SubjectiveMemPublicationIntent,
    finalized_at: str,
) -> _FinalizationOutcome:
    try:
        with store.transaction(evidence_space_id) as tx:
            operation = tx.read_record(
                record_kind="subjective_mem_operation",
                record_id=identity.operation_slot_id,
            )
            if operation is None:
                return _FinalizationOutcome(
                    reasons=("subjective_mem_commit_sm1_operation_missing",)
                )
            loaded, reasons = _load_operation_locked(
                tx=tx,
                operation=operation,
                identity=identity,
                character_authority=character_authority,
            )
            if loaded is None:
                return _FinalizationOutcome(reasons=reasons)
            existing_intent = tx.read_record(
                record_kind="subjective_mem_st1_intent",
                record_id=intent.intent_id,
            )
            if existing_intent != intent.to_dict():
                return _FinalizationOutcome(
                    reasons=("subjective_mem_commit_intent_changed",)
                )
            final_state = SubjectiveMemCurrentState(
                memory_state_id=loaded.bundle.current_state.memory_state_id,
                memory_id=loaded.bundle.current_state.memory_id,
                character_id=loaded.bundle.current_state.character_id,
                updated_at=finalized_at,
                mutation_state="none",
                retrieval_eligible=True,
            )
            records = build_finalization_records(
                intent=intent,
                receipt_id=loaded.receipt_id,
                finalized_at=finalized_at,
                current_state=final_state,
            )
            exact, partial = _inspect_finalization_records_locked(
                tx=tx,
                loaded=loaded,
                intent=intent,
                expected=records,
            )
            if exact:
                return _FinalizationOutcome(
                    ok=True, duplicate=True, records=records
                )
            if partial:
                return _FinalizationOutcome(
                    reasons=("subjective_mem_commit_partial_finalization_conflict",)
                )
            if (
                loaded.bundle.current_state.mutation_state != "prepared"
                or loaded.bundle.current_state.retrieval_eligible is not False
                or loaded.operation != expected_loaded.operation
            ):
                return _FinalizationOutcome(
                    reasons=("subjective_mem_commit_current_state_changed",)
                )
            commit = tx.commit(
                transaction_id=_opaque("st1finaltx", intent.finalization_id),
                records=(
                    (
                        "subjective_mem_st1_commit_receipt",
                        loaded.receipt_id,
                        records.receipt.to_dict(),
                    ),
                    (
                        "subjective_mem_st1_idempotency",
                        intent.finalization_id,
                        records.idempotency,
                    ),
                    (
                        "subjective_mem_st1_manifest_finalization",
                        intent.finalization_id,
                        records.manifest_finalization,
                    ),
                    (
                        "subjective_mem_st1_intent_finalization",
                        intent.finalization_id,
                        records.intent_finalization,
                    ),
                    (
                        "subjective_mem_st1_projection_state",
                        intent.finalization_id,
                        records.projection_state,
                    ),
                ),
                logs=(
                    (
                        "subjective_mem_current_state",
                        final_state.memory_state_id,
                        (final_state.to_dict(),),
                    ),
                ),
            )
            if commit.status == "collision":
                return _FinalizationOutcome(
                    reasons=("subjective_mem_commit_finalization_conflict",)
                )
            if commit.status not in {"created", "duplicate_existing"}:
                return _FinalizationOutcome(
                    reasons=commit.reasons
                    or ("subjective_mem_commit_finalization_failed",)
                )
            return _FinalizationOutcome(
                ok=True,
                duplicate=commit.status == "duplicate_existing",
                records=records,
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return _FinalizationOutcome(
            reasons=("subjective_mem_commit_store_unavailable",)
        )


def _inspect_finalization_records_locked(
    *,
    tx: EvidenceStoreTransaction,
    loaded: _LoadedOperation,
    intent: SubjectiveMemPublicationIntent,
    expected: SubjectiveMemFinalizationRecords,
) -> tuple[bool, bool]:
    observed = (
        tx.read_record(
            record_kind="subjective_mem_st1_commit_receipt",
            record_id=loaded.receipt_id,
        ),
        tx.read_record(
            record_kind="subjective_mem_st1_idempotency",
            record_id=intent.finalization_id,
        ),
        tx.read_record(
            record_kind="subjective_mem_st1_manifest_finalization",
            record_id=intent.finalization_id,
        ),
        tx.read_record(
            record_kind="subjective_mem_st1_intent_finalization",
            record_id=intent.finalization_id,
        ),
        tx.read_record(
            record_kind="subjective_mem_st1_projection_state",
            record_id=intent.finalization_id,
        ),
    )
    expected_values = (
        expected.receipt.to_dict(),
        expected.idempotency,
        expected.manifest_finalization,
        expected.intent_finalization,
        expected.projection_state,
    )
    state = tx.read_log(
        log_kind="subjective_mem_current_state",
        key=expected.current_state.memory_state_id,
    )
    all_absent = all(item is None for item in observed)
    exact = observed == expected_values and state == [expected.current_state.to_dict()]
    before_state = state == [loaded.bundle.current_state.to_dict()]
    partial = not exact and (not all_absent or not before_state)
    return exact, partial


def _validate_finalized_after_unlock(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    loaded: _LoadedOperation,
    workspace_root: str,
    workspace_authority_digest: str,
) -> SubjectiveMemCommitResult:
    try:
        with store.transaction(evidence_space_id) as tx:
            intent_raw = tx.read_record(
                record_kind="subjective_mem_st1_intent",
                record_id=loaded.intent_id,
            )
            intent = _intent_from_dict(intent_raw)
            receipt_raw = tx.read_record(
                record_kind="subjective_mem_st1_commit_receipt",
                record_id=loaded.receipt_id,
            )
            if intent is None or not isinstance(receipt_raw, dict):
                return _result(
                    "fail_closed",
                    loaded=loaded,
                    reasons=("subjective_mem_commit_finalization_records_missing",),
                )
            if intent.workspace_authority_digest != workspace_authority_digest:
                return _result(
                    "fail_closed",
                    loaded=loaded,
                    intent=intent,
                    reasons=("subjective_mem_commit_workspace_authority_changed",),
                )
            finalized_at = receipt_raw.get("finalized_at")
            if not isinstance(finalized_at, str):
                return _result(
                    "fail_closed",
                    loaded=loaded,
                    intent=intent,
                    reasons=("subjective_mem_commit_receipt_corrupt",),
                )
            expected = build_finalization_records(
                intent=intent,
                receipt_id=loaded.receipt_id,
                finalized_at=finalized_at,
                current_state=loaded.bundle.current_state,
            )
            exact, partial = _inspect_finalization_records_locked(
                tx=tx, loaded=loaded, intent=intent, expected=expected
            )
            if not exact or partial:
                return _result(
                    "fail_closed",
                    loaded=loaded,
                    intent=intent,
                    reasons=("subjective_mem_commit_finalization_records_corrupt",),
                )
            records = expected
    except (OSError, RuntimeError, TypeError, ValueError):
        return _result(
            "fail_closed",
            loaded=loaded,
            reasons=("subjective_mem_commit_store_unavailable",),
        )

    artifact, reasons = read_immutable_rendered_artifact(
        workspace_root=workspace_root,
        character_id=loaded.bundle.revision.character_id,
        artifact_id=intent.artifact_id,
    )
    if artifact is None or canonical_page_digest(artifact) != intent.artifact_digest:
        return _result(
            "fail_closed",
            loaded=loaded,
            intent=intent,
            reasons=reasons or ("subjective_mem_commit_artifact_unverifiable",),
            recovery_outcome="receipt_without_verifiable_artifact",
        )
    inspected = inspect_canonical_page(
        workspace_root=workspace_root,
        character_id=loaded.bundle.revision.character_id,
        relative_path=intent.target_relative_path,
    )
    if (
        inspected.snapshot is None
        or inspected.snapshot.data is None
        or inspected.snapshot.digest != intent.post_image_digest
        or not _verify_exact_post_image(
            data=inspected.snapshot.data, intent=intent, loaded=loaded
        )
    ):
        return _result(
            "fail_closed",
            loaded=loaded,
            intent=intent,
            reasons=inspected.reasons
            or ("subjective_mem_commit_receipt_without_page",),
            recovery_outcome="receipt_without_verifiable_page",
        )
    return _result(
        "duplicate_finalized",
        loaded=loaded,
        intent=intent,
        receipt=records.receipt,
        current_state=records.current_state,
        recovery_outcome="exact_finalized_noop",
        canonical_published=True,
        receipt_present=True,
        persisted=True,
    )


def _classify_existing_intent_dry_run(
    *,
    loaded: _LoadedOperation,
    intent: SubjectiveMemPublicationIntent,
    workspace_root: str,
) -> SubjectiveMemCommitResult:
    artifact, reasons = read_immutable_rendered_artifact(
        workspace_root=workspace_root,
        character_id=loaded.bundle.revision.character_id,
        artifact_id=intent.artifact_id,
    )
    if artifact is None or canonical_page_digest(artifact) != intent.artifact_digest:
        return _result(
            "recovery_required",
            loaded=loaded,
            intent=intent,
            reasons=reasons or ("subjective_mem_commit_artifact_unverifiable",),
            recovery_outcome="artifact_unverifiable",
        )
    inspected = inspect_canonical_page(
        workspace_root=workspace_root,
        character_id=loaded.bundle.revision.character_id,
        relative_path=intent.target_relative_path,
    )
    if inspected.snapshot is None:
        return _result(
            "fail_closed", loaded=loaded, intent=intent, reasons=inspected.reasons
        )
    snapshot = inspected.snapshot
    if snapshot.digest == intent.pre_image_digest and snapshot.state == intent.pre_image_state:
        return _result(
            "dry_run_ready",
            loaded=loaded,
            intent=intent,
            recovery_outcome="pre_image_retry_ready",
        )
    if (
        snapshot.digest == intent.post_image_digest
        and snapshot.data is not None
        and _verify_exact_post_image(data=snapshot.data, intent=intent, loaded=loaded)
    ):
        return _result(
            "dry_run_ready",
            loaded=loaded,
            intent=intent,
            recovery_outcome="post_image_pending_receipt",
            canonical_published=True,
        )
    return _result(
        "recovery_required",
        loaded=loaded,
        intent=intent,
        reasons=("subjective_mem_commit_foreign_image",),
        recovery_outcome="foreign_image",
    )


def _verify_exact_post_image(
    *, data: bytes, intent: SubjectiveMemPublicationIntent, loaded: _LoadedOperation
) -> bool:
    if canonical_page_digest(data) != intent.post_image_digest:
        return False
    partition = "episodes" if loaded.bundle.revision.memory_kind == "episodic" else "topics"
    page, reasons = parse_subjective_mem_page_bytes(
        data,
        expected_page_id=intent.target_page_id,
        expected_character_id=intent.character_id,
        expected_partition=partition,  # type: ignore[arg-type]
    )
    if page is None or reasons:
        return False
    matches = [
        block
        for block in page.blocks
        if block.block_id == intent.memory_block_id
        and block.anchor == intent.memory_block_anchor
        and block.revision.memory_id == intent.memory_id
    ]
    return (
        len(matches) == 1
        and matches[0].revision.to_dict() == loaded.bundle.revision.to_dict()
        and matches[0].block_digest == intent.block_digest
    )


def _validate_intent_binding(
    *,
    intent: SubjectiveMemPublicationIntent,
    loaded: _LoadedOperation,
    identity: SubjectiveMemOperationIdentity,
    workspace_authority_digest: str,
) -> tuple[str, ...]:
    operation = loaded.operation
    page_id, relative_path, _partition = subjective_mem_page_identity(
        character_id=loaded.bundle.revision.character_id,
        memory_kind=loaded.bundle.revision.memory_kind,
    )
    if (
        intent.intent_id != loaded.intent_id
        or intent.finalization_id != loaded.finalization_id
        or intent.sm1_operation_slot_id != identity.operation_slot_id
        or intent.sm1_operation_id != identity.operation_id
        or intent.sm1_operation_key_digest != identity.operation_key_digest
        or intent.evidence_space_id != operation["evidence_space_id"]
        or intent.character_id != loaded.bundle.revision.character_id
        or intent.character_authority_digest != identity.character_authority_digest
        or intent.workspace_authority_digest != workspace_authority_digest
        or intent.memory_id != loaded.bundle.revision.memory_id
        or intent.decision_id != loaded.bundle.decision.decision_id
        or intent.prepared_revision_record_id
        != operation["prepared_revision_record_id"]
        or intent.prepared_revision_digest != operation["prepared_revision_digest"]
        or intent.prepared_manifest_id != operation["prepared_manifest_id"]
        or intent.prepared_manifest_digest != operation["prepared_manifest_digest"]
        or intent.target_page_id != page_id
        or intent.target_relative_path != relative_path
        or intent.artifact_digest != intent.post_image_digest
        or intent.page_schema != PAGE_SCHEMA
        or intent.renderer_revision != RENDERER_REVISION
        or intent.partition_revision != PAGE_PARTITION_REVISION
        or intent.platform_revision != PLATFORM_REVISION
    ):
        return ("subjective_mem_commit_intent_binding_invalid",)
    return ()


def _intent_from_dict(raw: object) -> SubjectiveMemPublicationIntent | None:
    if not isinstance(raw, dict) or raw.get("schema") != ST1_INTENT_SCHEMA:
        return None
    memory_ref = raw.get("memory_ref")
    if not isinstance(memory_ref, dict) or memory_ref.get("memory_revision") != 1:
        return None
    try:
        intent = SubjectiveMemPublicationIntent(
            intent_id=raw["intent_id"],
            finalization_id=raw["finalization_id"],
            sm1_operation_slot_id=raw["sm1_operation_slot_id"],
            sm1_operation_id=raw["sm1_operation_id"],
            sm1_operation_key_digest=raw["sm1_operation_key_digest"],
            evidence_space_id=raw["evidence_space_id"],
            character_id=raw["character_id"],
            character_authority_digest=raw["character_authority_digest"],
            workspace_authority_digest=raw["workspace_authority_digest"],
            memory_id=memory_ref["memory_id"],
            decision_id=raw["decision_id"],
            prepared_revision_record_id=raw["prepared_revision_record_id"],
            prepared_revision_digest=raw["prepared_revision_digest"],
            prepared_manifest_id=raw["prepared_manifest_id"],
            prepared_manifest_digest=raw["prepared_manifest_digest"],
            target_page_id=raw["target_page_id"],
            target_relative_path=raw["target_relative_path"],
            memory_block_id=raw["memory_block_id"],
            memory_block_anchor=raw["memory_block_anchor"],
            pre_image_state=raw["pre_image_state"],
            pre_image_digest=raw["pre_image_digest"],
            post_image_digest=raw["post_image_digest"],
            block_digest=raw["block_digest"],
            artifact_id=raw["artifact_id"],
            artifact_digest=raw["artifact_digest"],
            page_schema=raw["page_schema"],
            renderer_revision=raw["renderer_revision"],
            partition_revision=raw["partition_revision"],
            platform_revision=raw["platform_revision"],
            prepared_at=raw["prepared_at"],
        )
    except (KeyError, TypeError, ValueError):
        return None
    return intent if intent.to_dict() == raw else None


def _configured_workspace_root_matches(
    *, character_config: object, workspace_root: str
) -> bool:
    configured = getattr(character_config, "subjective_mem_workspace_root", None)
    return (
        isinstance(configured, str)
        and bool(configured)
        and isinstance(workspace_root, str)
        and bool(workspace_root)
        and Path(configured) == Path(workspace_root)
    )


def _workspace_authority_digest(
    *, workspace_root: str, character_authority: SubjectiveMemCharacterAuthority
) -> str:
    return canonical_digest(
        {
            "schema": "relaylm.subjective_mem_workspace_authority.v1",
            "workspace_root_digest": sha256_hex(workspace_root.encode("utf-8")),
            "character_authority": character_authority.to_dict(),
        }
    )


def _result(
    status: CommitStatus,
    *,
    loaded: _LoadedOperation | None = None,
    intent: SubjectiveMemPublicationIntent | None = None,
    receipt: SubjectiveMemCommitReceipt | None = None,
    current_state: SubjectiveMemCurrentState | None = None,
    reasons: tuple[str, ...] = (),
    recovery_outcome: str | None = None,
    canonical_published: bool = False,
    receipt_present: bool = False,
    persisted: bool = False,
) -> SubjectiveMemCommitResult:
    return SubjectiveMemCommitResult(
        status=status,
        finalization_id=(
            intent.finalization_id
            if intent is not None
            else loaded.finalization_id if loaded is not None else None
        ),
        receipt=receipt,
        current_state=current_state,
        page_id=intent.target_page_id if intent else None,
        block_id=intent.memory_block_id if intent else None,
        memory_id=loaded.bundle.revision.memory_id if loaded else None,
        blocked_reasons=tuple(dict.fromkeys(reasons)),
        recovery_outcome=recovery_outcome,
        canonical_markdown_published=canonical_published,
        commit_receipt_present=receipt_present,
        persisted=persisted,
        _post_image_digest=intent.post_image_digest if intent else None,
    )


def _reason_status(reasons: tuple[str, ...]) -> CommitStatus:
    return (
        "integrity_conflict"
        if any("conflict" in reason or "duplicate" in reason for reason in reasons)
        else "fail_closed"
    )


def _opaque(prefix: str, value: str) -> str:
    return prefix + "_" + sha256_hex(value.encode("utf-8"))


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("subjective_mem_commit_naive_datetime_forbidden")
    return value.astimezone(timezone.utc)


def _fault(injector: FaultInjector | None, stage: str) -> None:
    if injector is not None:
        injector(stage)


__all__ = [
    "CommitStatus",
    "SubjectiveMemCommitGate",
    "SubjectiveMemCommitResult",
    "finalize_subjective_mem_create",
    "resolve_subjective_mem_commit_gate",
    "validate_finalized_subjective_mem_operation",
]
