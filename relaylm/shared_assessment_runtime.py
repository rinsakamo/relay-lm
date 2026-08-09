"""ASM-1 deferred Shared Assessment runtime over EV-1 governed Evidence.

The runtime exposes three explicit phases:

1. prepare a character-independent Assessment Pass bundle from currently
   authorized EV-1 SourceEvents;
2. atomically publish one immutable SharedAssessmentRevision and replace the
   single logical SharedAssessmentCurrentState selector;
3. issue an immutable, content-free formation-time authorization receipt for
   the exact current revision.

There is intentionally no Subjective MEM writer or normal response-path hook.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from relaylm.evidence.common import (
    canonical_digest,
    sha256_hex,
    utf8_text_digest,
)
from relaylm.evidence.store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.shared_assessment_evidence import (
    authorized_shared_assessment_sources_match_bundle,
    load_authorized_shared_assessment_sources,
)
from relaylm.shared_assessment import (
    SHARED_ASSESSMENT_CURRENT_STATE_SCHEMA,
    SHARED_ASSESSMENT_FORMATION_RECEIPT_SCHEMA,
    SHARED_ASSESSMENT_PASS_BUNDLE_SCHEMA,
    SharedAssessmentCurrentState,
    SharedAssessmentEvidenceRef,
    SharedAssessmentFormationAuthorizationReceipt,
    SharedAssessmentPassBundle,
    SharedAssessmentProposal,
    SharedAssessmentRevision,
    assessment_id_matches_evidence_space,
    build_shared_assessment_revision,
    validate_shared_assessment_pass_bundle,
    validate_shared_assessment_proposal,
)

PrepareStatus = Literal["ready", "fail_closed"]
CommitStatus = Literal[
    "committed", "duplicate_existing", "dry_run_ready", "fail_closed", "integrity_conflict"
]
ReceiptStatus = Literal["ready", "fail_closed"]

MAX_SHARED_ASSESSMENT_REVISIONS = 4096




@dataclass(frozen=True)
class SharedAssessmentRuntimeGate:
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    store: EvidenceRecordStore | None


def resolve_shared_assessment_gate(config: object) -> SharedAssessmentRuntimeGate:
    """Resolve the default-off deferred-worker gate from RelayLMConfig."""

    enabled = bool(getattr(config, "shared_assessment_enabled", False))
    dry_run_only = bool(
        getattr(config, "shared_assessment_dry_run_only", True)
    )
    apply_enabled = bool(
        getattr(config, "shared_assessment_apply_enabled", False)
    )
    if not enabled:
        return SharedAssessmentRuntimeGate(False, True, False, None)
    root = getattr(config, "evidence_data_root", None)
    if not isinstance(root, str) or not root:
        return SharedAssessmentRuntimeGate(True, dry_run_only, False, None)
    try:
        store = EvidenceRecordStore(root)
    except ValueError:
        store = None
    return SharedAssessmentRuntimeGate(
        True, dry_run_only, apply_enabled and not dry_run_only, store
    )


@dataclass(frozen=True)
class SharedAssessmentPrepareResult:
    status: PrepareStatus
    bundle: SharedAssessmentPassBundle | None = field(default=None, repr=False)
    blocked_reasons: tuple[str, ...] = ()

    def to_log_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "blocked_reasons": list(self.blocked_reasons),
            "assessment_pass_id": (
                self.bundle.assessment_pass_id if self.bundle is not None else None
            ),
            "evidence_ref_count": (
                len(self.bundle.evidence_refs) if self.bundle is not None else 0
            ),
            "part_count": len(self.bundle.parts) if self.bundle is not None else 0,
            "bundle_digest": (
                self.bundle.bundle_digest if self.bundle is not None else None
            ),
            "content_free": True,
        }


@dataclass(frozen=True)
class SharedAssessmentCommitResult:
    status: CommitStatus
    revision: SharedAssessmentRevision | None = field(default=None, repr=False)
    current_state: SharedAssessmentCurrentState | None = None
    blocked_reasons: tuple[str, ...] = ()
    persisted: bool = False

    def to_log_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "assessment_id": (
                self.revision.assessment_id if self.revision is not None else None
            ),
            "assessment_revision": (
                self.revision.assessment_revision if self.revision is not None else None
            ),
            "supported_content_digest": (
                self.revision.supported_content_digest
                if self.revision is not None
                else None
            ),
            "blocked_reasons": list(self.blocked_reasons),
            "persisted": self.persisted,
            "content_free": True,
        }


@dataclass(frozen=True)
class SharedAssessmentReceiptResult:
    status: ReceiptStatus
    receipt: SharedAssessmentFormationAuthorizationReceipt | None = None
    blocked_reasons: tuple[str, ...] = ()



def prepare_shared_assessment_pass(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    source_event_ids: tuple[str, ...],
    assessment_pass_id: str,
    now: datetime | None = None,
) -> SharedAssessmentPrepareResult:
    """Resolve exact current Evidence authority and expose only Pass-A inputs."""

    reasons = _validate_prepare_inputs(
        evidence_space_id=evidence_space_id,
        source_event_ids=source_event_ids,
        assessment_pass_id=assessment_pass_id,
    )
    if reasons:
        return SharedAssessmentPrepareResult("fail_closed", blocked_reasons=reasons)
    try:
        current_time = _utc(now)
        with store.transaction(evidence_space_id) as tx:
            authorized, load_reasons = load_authorized_shared_assessment_sources(
                tx=tx,
                evidence_space_id=evidence_space_id,
                source_event_ids=source_event_ids,
                now=current_time,
            )
    except (OSError, RuntimeError, ValueError):
        return SharedAssessmentPrepareResult(
            "fail_closed", blocked_reasons=("shared_assessment_evidence_store_unavailable",)
        )
    if load_reasons:
        return SharedAssessmentPrepareResult("fail_closed", blocked_reasons=load_reasons)
    assert authorized is not None
    evidence_refs = tuple(item.evidence_ref for item in authorized)
    parts = tuple(part for item in authorized for part in item.parts)
    snapshots = tuple(item.authorization_snapshot for item in authorized)
    digest_input = {
        "schema": SHARED_ASSESSMENT_PASS_BUNDLE_SCHEMA,
        "assessment_pass_id": assessment_pass_id,
        "evidence_space_id": evidence_space_id,
        "evidence_refs": [item.to_dict() for item in evidence_refs],
        "parts": [item.to_dict() for item in parts],
        "authorization_snapshots": [item.to_dict() for item in snapshots],
        "prepared_at": current_time.isoformat(),
    }
    bundle = SharedAssessmentPassBundle(
        schema=SHARED_ASSESSMENT_PASS_BUNDLE_SCHEMA,
        assessment_pass_id=assessment_pass_id,
        evidence_space_id=evidence_space_id,
        evidence_refs=evidence_refs,
        parts=parts,
        authorization_snapshots=snapshots,
        prepared_at=current_time.isoformat(),
        bundle_digest=canonical_digest(digest_input),
    )
    return SharedAssessmentPrepareResult("ready", bundle=bundle)


def commit_shared_assessment_revision(
    *,
    store: EvidenceRecordStore,
    bundle: SharedAssessmentPassBundle,
    proposal: SharedAssessmentProposal,
    operation_idempotency_key: str,
    apply_enabled: bool,
    now: datetime | None = None,
) -> SharedAssessmentCommitResult:
    """Validate Pass-A output and atomically publish revision + one selector."""

    try:
        current_time = _utc(now)
    except ValueError:
        return SharedAssessmentCommitResult(
            "fail_closed", blocked_reasons=("shared_assessment_clock_invalid",)
        )
    reasons = list(
        validate_shared_assessment_pass_bundle(bundle, verify_digest=False)
    )
    reasons.extend(validate_shared_assessment_proposal(proposal))
    if not assessment_id_matches_evidence_space(
        proposal.assessment_id, bundle.evidence_space_id
    ):
        reasons.append("shared_assessment_id_evidence_space_mismatch")
    if not reasons and not bundle.is_self_authenticating():
        reasons.append("shared_assessment_pass_bundle_invalid")
    if not _token(operation_idempotency_key, 256):
        reasons.append("shared_assessment_operation_idempotency_key_invalid")
    if reasons:
        return SharedAssessmentCommitResult("fail_closed", blocked_reasons=tuple(reasons))

    operation_record_id = _opaque_key("asmop", operation_idempotency_key)
    operation_input_digest = canonical_digest(
        {
            "assessment_input": {
                "evidence_refs": [item.to_dict() for item in bundle.evidence_refs],
                "parts": [item.to_dict() for item in bundle.parts],
                "authorization_snapshots": [
                    {
                        "source_event_id": item.source_event_id,
                        "authority_snapshot_digest": item.authority_snapshot_digest,
                        "selected_part_ids": list(item.selected_part_ids),
                        "matched_grant_ids": list(item.matched_grant_ids),
                        "governance_revision": item.governance_revision,
                        "validation_bundle_revision": item.validation_bundle_revision,
                    }
                    for item in bundle.authorization_snapshots
                ],
            },
            "proposal": {
                "assessment_id": proposal.assessment_id,
                "supported_content": proposal.supported_content,
                "support_state": proposal.support_state,
                "uncertainty": list(proposal.uncertainty),
                "temporal_state": proposal.temporal_state,
                "governance_revision": proposal.governance_revision,
                "expected_current_revision_or_null": proposal.expected_current_revision_or_null,
            },
        }
    )
    try:
        with store.transaction(bundle.evidence_space_id) as tx:
            existing_operation = tx.read_record(
                record_kind="shared_assessment_operation",
                record_id=operation_record_id,
            )
            if existing_operation is not None:
                return _resolve_existing_operation(
                    tx=tx,
                    existing=existing_operation,
                    expected_input_digest=operation_input_digest,
                    expected_operation_id=operation_record_id,
                    expected_idempotency_key_digest=sha256_hex(
                        operation_idempotency_key.encode("utf-8")
                    ),
                    expected_assessment_id=proposal.assessment_id,
                    expected_assessment_revision=(
                        1
                        if proposal.expected_current_revision_or_null is None
                        else proposal.expected_current_revision_or_null + 1
                    ),
                )

            authorized, auth_reasons = load_authorized_shared_assessment_sources(
                tx=tx,
                evidence_space_id=bundle.evidence_space_id,
                source_event_ids=tuple(ref.source_event_id for ref in bundle.evidence_refs),
                now=current_time,
            )
            if auth_reasons:
                return SharedAssessmentCommitResult(
                    "fail_closed", blocked_reasons=auth_reasons
                )
            assert authorized is not None
            if not authorized_shared_assessment_sources_match_bundle(authorized, bundle):
                return SharedAssessmentCommitResult(
                    "fail_closed",
                    blocked_reasons=("shared_assessment_evidence_authority_changed",),
                )

            state_key = _opaque_key("asmstate", proposal.assessment_id)
            state_log = tx.read_log(
                log_kind="shared_assessment_current_state", key=state_key
            )
            current_state, state_reasons = _parse_single_current_state(
                state_log, expected_assessment_id=proposal.assessment_id
            )
            if state_reasons:
                return SharedAssessmentCommitResult(
                    "fail_closed", blocked_reasons=state_reasons
                )
            revision_index = tx.read_log(
                log_kind="shared_assessment_revision_index", key=state_key
            )
            index_reasons = _validate_revision_index(
                tx=tx,
                raw=revision_index,
                assessment_id=proposal.assessment_id,
                current_state=current_state,
            )
            if index_reasons:
                return SharedAssessmentCommitResult(
                    "fail_closed", blocked_reasons=index_reasons
                )
            if (
                current_state is not None
                and current_state.current_revision
                >= MAX_SHARED_ASSESSMENT_REVISIONS
            ):
                return SharedAssessmentCommitResult(
                    "fail_closed",
                    blocked_reasons=(
                        "shared_assessment_revision_index_bound_exceeded",
                    ),
                )
            if current_state is not None and (
                current_state.lifecycle_state != "active"
                or current_state.authorization_state != "current_admitted"
            ):
                return SharedAssessmentCommitResult(
                    "fail_closed",
                    blocked_reasons=("shared_assessment_current_state_not_admitted",),
                )
            if current_state is not None and _parse_date_time(
                current_state.updated_at
            ) > current_time:
                return SharedAssessmentCommitResult(
                    "fail_closed",
                    blocked_reasons=("shared_assessment_temporal_non_monotonic",),
                )
            predecessor = None if current_state is None else current_state.current_revision
            if proposal.expected_current_revision_or_null != predecessor:
                return SharedAssessmentCommitResult(
                    "fail_closed",
                    blocked_reasons=("shared_assessment_expected_current_revision_stale",),
                )
            next_revision = 1 if predecessor is None else predecessor + 1
            revision, revision_reasons = build_shared_assessment_revision(
                proposal=proposal,
                evidence_refs=bundle.evidence_refs,
                assessment_revision=next_revision,
                supersedes_assessment_revision_or_null=predecessor,
                created_at=current_time.isoformat(),
            )
            if revision is None:
                return SharedAssessmentCommitResult(
                    "fail_closed", blocked_reasons=revision_reasons
                )
            new_state = SharedAssessmentCurrentState(
                schema=SHARED_ASSESSMENT_CURRENT_STATE_SCHEMA,
                assessment_state_id=_opaque_key("asmselector", proposal.assessment_id),
                assessment_id=proposal.assessment_id,
                current_revision=next_revision,
                lifecycle_state="active",
                authorization_state="current_admitted",
                updated_at=current_time.isoformat(),
            )
            if not apply_enabled:
                return SharedAssessmentCommitResult(
                    "dry_run_ready",
                    revision=revision,
                    current_state=new_state,
                    persisted=False,
                )

            revision_record_id = _revision_record_id(
                proposal.assessment_id, next_revision
            )
            operation_record = {
                "schema": "relaylm.shared_assessment_operation.v1",
                "operation_id": operation_record_id,
                "operation_idempotency_key_digest": sha256_hex(
                    operation_idempotency_key.encode("utf-8")
                ),
                "operation_input_digest": operation_input_digest,
                "assessment_id": proposal.assessment_id,
                "assessment_revision": next_revision,
                "revision_record_id": revision_record_id,
                "committed_at": current_time.isoformat(),
            }
            commit = tx.commit(
                transaction_id=_opaque_key("asmtx", operation_idempotency_key),
                records=(
                    (
                        "shared_assessment_revision",
                        revision_record_id,
                        revision.to_dict(),
                    ),
                    (
                        "shared_assessment_operation",
                        operation_record_id,
                        operation_record,
                    ),
                ),
                logs=(
                    (
                        "shared_assessment_current_state",
                        state_key,
                        (new_state.to_dict(),),
                    ),
                    (
                        "shared_assessment_revision_index",
                        state_key,
                        (
                            *(revision_index or []),
                            {
                                "schema": "relaylm.shared_assessment_revision_index_entry.v1",
                                "assessment_id": proposal.assessment_id,
                                "assessment_revision": next_revision,
                                "revision_record_id": revision_record_id,
                                "recorded_at": current_time.isoformat(),
                            },
                        ),
                    ),
                ),
            )
            if commit.status == "collision":
                return SharedAssessmentCommitResult(
                    "integrity_conflict", blocked_reasons=commit.reasons
                )
            if commit.status not in {"created", "duplicate_existing"}:
                return SharedAssessmentCommitResult(
                    "fail_closed", blocked_reasons=commit.reasons
                )
            return SharedAssessmentCommitResult(
                "committed" if commit.status == "created" else "duplicate_existing",
                revision=revision,
                current_state=new_state,
                persisted=True,
            )
    except (OSError, RuntimeError, ValueError):
        return SharedAssessmentCommitResult(
            "fail_closed", blocked_reasons=("shared_assessment_store_unavailable",)
        )


def build_shared_assessment_formation_receipt(
    *,
    tx: EvidenceStoreTransaction,
    evidence_space_id: str,
    assessment_id: str,
    assessment_revision: int,
    decision_id: str,
    decision_input_digest: str,
    decided_at: datetime,
) -> SharedAssessmentReceiptResult:
    """Build a decision-bound receipt inside the caller-owned decision transaction.

    ASM-1 deliberately does not persist a receipt independently.  SM-1 must call
    this function while holding the same Evidence transaction used to publish the
    exact SubjectiveMemDecision, then commit the decision and receipt together.
    """

    if (
        not _token(assessment_id)
        or type(assessment_revision) is not int
        or assessment_revision < 1
        or not _token(decision_id)
        or not _digest(decision_input_digest)
        or not assessment_id_matches_evidence_space(
            assessment_id, evidence_space_id
        )
    ):
        return SharedAssessmentReceiptResult(
            "fail_closed", blocked_reasons=("shared_assessment_receipt_target_invalid",)
        )
    try:
        current_time = _utc(decided_at)
        state_key = _opaque_key("asmstate", assessment_id)
        state_log = tx.read_log(
            log_kind="shared_assessment_current_state", key=state_key
        )
        current_state, state_reasons = _parse_single_current_state(
            state_log, expected_assessment_id=assessment_id
        )
        if state_reasons or current_state is None:
            return SharedAssessmentReceiptResult(
                "fail_closed",
                blocked_reasons=state_reasons
                or ("shared_assessment_current_state_missing",),
            )
        if (
            current_state.current_revision != assessment_revision
            or current_state.lifecycle_state != "active"
            or current_state.authorization_state != "current_admitted"
        ):
            return SharedAssessmentReceiptResult(
                "fail_closed",
                blocked_reasons=("shared_assessment_receipt_target_not_current_admitted",),
            )
        revision_index = tx.read_log(
            log_kind="shared_assessment_revision_index", key=state_key
        )
        index_reasons = _validate_revision_index(
            tx=tx,
            raw=revision_index,
            assessment_id=assessment_id,
            current_state=current_state,
        )
        if index_reasons:
            return SharedAssessmentReceiptResult(
                "fail_closed", blocked_reasons=index_reasons
            )
        raw_revision = tx.read_record(
            record_kind="shared_assessment_revision",
            record_id=_revision_record_id(assessment_id, assessment_revision),
        )
        revision = (
            _revision_from_dict(raw_revision)
            if isinstance(raw_revision, dict)
            else None
        )
        if revision is None:
            return SharedAssessmentReceiptResult(
                "fail_closed",
                blocked_reasons=("shared_assessment_revision_missing_or_corrupt",),
            )
        if current_time < max(
            _parse_date_time(revision.created_at),
            _parse_date_time(current_state.updated_at),
        ):
            return SharedAssessmentReceiptResult(
                "fail_closed",
                blocked_reasons=("shared_assessment_temporal_non_monotonic",),
            )
        raw_refs = [item.to_dict() for item in revision.evidence_refs]
        source_ids = tuple(item.source_event_id for item in revision.evidence_refs)
        authorized, auth_reasons = load_authorized_shared_assessment_sources(
            tx=tx,
            evidence_space_id=evidence_space_id,
            source_event_ids=source_ids,
            now=current_time,
        )
        if auth_reasons:
            return SharedAssessmentReceiptResult(
                "fail_closed", blocked_reasons=auth_reasons
            )
        assert authorized is not None
        expected_refs = [item.evidence_ref.to_dict() for item in authorized]
        if expected_refs != raw_refs:
            return SharedAssessmentReceiptResult(
                "fail_closed",
                blocked_reasons=("shared_assessment_revision_evidence_authority_changed",),
            )
        supported_digest = revision.supported_content_digest
        if utf8_text_digest(revision.supported_content) != supported_digest:
            return SharedAssessmentReceiptResult(
                "fail_closed",
                blocked_reasons=("shared_assessment_supported_content_digest_invalid",),
            )
        receipt_id = shared_assessment_formation_receipt_id(
            decision_id, decision_input_digest
        )
        digest_input = {
            "schema": SHARED_ASSESSMENT_FORMATION_RECEIPT_SCHEMA,
            "receipt_id": receipt_id,
            "assessment_id": assessment_id,
            "assessment_revision": assessment_revision,
            "supported_content_digest": supported_digest,
            "assessment_authorization_receipt": {
                "current_revision_at_decision": assessment_revision,
                "lifecycle_state_at_decision": "active",
                "authorization_state_at_decision": "current_admitted",
            },
            "evidence_authority_snapshot_digests": [
                item.authorization_snapshot.authority_snapshot_digest
                for item in authorized
            ],
            "decision_id": decision_id,
            "decision_input_digest": decision_input_digest,
            "issued_at": current_time.isoformat(),
        }
        receipt = SharedAssessmentFormationAuthorizationReceipt(
            schema=SHARED_ASSESSMENT_FORMATION_RECEIPT_SCHEMA,
            receipt_id=receipt_id,
            assessment_id=assessment_id,
            assessment_revision=assessment_revision,
            supported_content_digest=supported_digest,
            current_revision_at_decision=assessment_revision,
            lifecycle_state_at_decision="active",
            authorization_state_at_decision="current_admitted",
            evidence_authority_snapshot_digests=tuple(
                item.authorization_snapshot.authority_snapshot_digest
                for item in authorized
            ),
            decision_id=decision_id,
            decision_input_digest=decision_input_digest,
            issued_at=current_time.isoformat(),
            receipt_digest=canonical_digest(digest_input),
        )
        if not receipt.is_self_authenticating():
            return SharedAssessmentReceiptResult(
                "fail_closed",
                blocked_reasons=("shared_assessment_receipt_digest_invalid",),
            )
        return SharedAssessmentReceiptResult("ready", receipt=receipt)
    except (OSError, RuntimeError, TypeError, ValueError):
        return SharedAssessmentReceiptResult(
            "fail_closed", blocked_reasons=("shared_assessment_store_unavailable",)
        )


def _parse_single_current_state(
    raw: list[dict] | None, *, expected_assessment_id: str
) -> tuple[SharedAssessmentCurrentState | None, tuple[str, ...]]:
    if raw is None or raw == []:
        return None, ()
    if len(raw) != 1 or not isinstance(raw[0], dict):
        return None, ("shared_assessment_duplicate_or_corrupt_current_state",)
    item = raw[0]
    if (
        item.get("schema") != SHARED_ASSESSMENT_CURRENT_STATE_SCHEMA
        or not _token(item.get("assessment_state_id"))
        or item.get("assessment_id") != expected_assessment_id
        or type(item.get("current_revision")) is not int
        or item["current_revision"] < 1
        or item.get("lifecycle_state")
        not in {"active", "restricted", "superseded", "purged"}
        or item.get("authorization_state")
        not in {"current_admitted", "restricted", "purged"}
        or not _valid_date_time(item.get("updated_at"))
    ):
        return None, ("shared_assessment_current_state_corrupt",)
    state = SharedAssessmentCurrentState(
        schema=item["schema"],
        assessment_state_id=item["assessment_state_id"],
        assessment_id=item["assessment_id"],
        current_revision=item["current_revision"],
        lifecycle_state=item["lifecycle_state"],
        authorization_state=item["authorization_state"],
        updated_at=item["updated_at"],
    )
    if state.to_dict() != item:
        return None, ("shared_assessment_current_state_corrupt",)
    return state, ()

def _validate_revision_index(
    *,
    tx: EvidenceStoreTransaction,
    raw: list[dict] | None,
    assessment_id: str,
    current_state: SharedAssessmentCurrentState | None,
) -> tuple[str, ...]:
    entries = raw or []
    expected_count = 0 if current_state is None else current_state.current_revision
    if expected_count > MAX_SHARED_ASSESSMENT_REVISIONS:
        return ("shared_assessment_revision_index_bound_exceeded",)
    if len(entries) != expected_count:
        return ("shared_assessment_revision_index_inconsistent",)
    previous_revision_time: datetime | None = None
    previous_recorded_time: datetime | None = None
    for expected_revision, item in enumerate(entries, start=1):
        if not isinstance(item, dict):
            return ("shared_assessment_revision_index_corrupt",)
        record_id = item.get("revision_record_id")
        if (
            item.get("schema")
            != "relaylm.shared_assessment_revision_index_entry.v1"
            or item.get("assessment_id") != assessment_id
            or item.get("assessment_revision") != expected_revision
            or record_id != _revision_record_id(assessment_id, expected_revision)
        ):
            return ("shared_assessment_revision_index_corrupt",)
        if not _valid_date_time(item.get("recorded_at")) or set(item) != {
            "schema",
            "assessment_id",
            "assessment_revision",
            "revision_record_id",
            "recorded_at",
        }:
            return ("shared_assessment_revision_index_corrupt",)
        raw_revision = tx.read_record(
            record_kind="shared_assessment_revision", record_id=str(record_id)
        )
        revision = (
            _revision_from_dict(raw_revision)
            if isinstance(raw_revision, dict)
            else None
        )
        if (
            revision is None
            or revision.assessment_id != assessment_id
            or revision.assessment_revision != expected_revision
        ):
            return ("shared_assessment_revision_index_dangling",)
        revision_time = _parse_date_time(revision.created_at)
        recorded_time = _parse_date_time(str(item["recorded_at"]))
        if revision_time > recorded_time:
            return ("shared_assessment_temporal_non_monotonic",)
        if previous_revision_time is not None and revision_time < previous_revision_time:
            return ("shared_assessment_temporal_non_monotonic",)
        if previous_recorded_time is not None and recorded_time < previous_recorded_time:
            return ("shared_assessment_temporal_non_monotonic",)
        previous_revision_time = revision_time
        previous_recorded_time = recorded_time
    if current_state is not None and previous_recorded_time is not None:
        if _parse_date_time(current_state.updated_at) < previous_recorded_time:
            return ("shared_assessment_temporal_non_monotonic",)
    return ()


def _resolve_existing_operation(
    *,
    tx: EvidenceStoreTransaction,
    existing: dict,
    expected_input_digest: str,
    expected_operation_id: str,
    expected_idempotency_key_digest: str,
    expected_assessment_id: str,
    expected_assessment_revision: int,
) -> SharedAssessmentCommitResult:
    if (
        existing.get("schema") != "relaylm.shared_assessment_operation.v1"
        or existing.get("operation_id") != expected_operation_id
        or existing.get("operation_idempotency_key_digest")
        != expected_idempotency_key_digest
        or not _valid_date_time(existing.get("committed_at"))
        or set(existing)
        != {
            "schema",
            "operation_id",
            "operation_idempotency_key_digest",
            "operation_input_digest",
            "assessment_id",
            "assessment_revision",
            "revision_record_id",
            "committed_at",
        }
    ):
        return SharedAssessmentCommitResult(
            "fail_closed",
            blocked_reasons=("shared_assessment_operation_record_corrupt",),
        )
    if existing.get("operation_input_digest") != expected_input_digest:
        return SharedAssessmentCommitResult(
            "integrity_conflict",
            blocked_reasons=("shared_assessment_operation_idempotency_conflict",),
        )
    record_id = existing.get("revision_record_id")
    assessment_revision = existing.get("assessment_revision")
    if (
        existing.get("assessment_id") != expected_assessment_id
        or assessment_revision != expected_assessment_revision
        or type(assessment_revision) is not int
        or assessment_revision < 1
        or record_id != _revision_record_id(
            expected_assessment_id, assessment_revision
        )
    ):
        return SharedAssessmentCommitResult(
            "fail_closed",
            blocked_reasons=("shared_assessment_operation_result_crosslink_invalid",),
        )
    if not isinstance(record_id, str):
        return SharedAssessmentCommitResult(
            "fail_closed", blocked_reasons=("shared_assessment_operation_record_corrupt",)
        )
    raw_revision = tx.read_record(
        record_kind="shared_assessment_revision", record_id=record_id
    )
    if raw_revision is None:
        return SharedAssessmentCommitResult(
            "fail_closed", blocked_reasons=("shared_assessment_operation_result_missing",)
        )
    revision = _revision_from_dict(raw_revision)
    if revision is None:
        return SharedAssessmentCommitResult(
            "fail_closed", blocked_reasons=("shared_assessment_operation_result_corrupt",)
        )
    if (
        revision.assessment_id != existing.get("assessment_id")
        or revision.assessment_revision != existing.get("assessment_revision")
        or revision.created_at != existing.get("committed_at")
    ):
        return SharedAssessmentCommitResult(
            "fail_closed",
            blocked_reasons=("shared_assessment_operation_result_crosslink_invalid",),
        )
    state_log = tx.read_log(
        log_kind="shared_assessment_current_state",
        key=_opaque_key("asmstate", revision.assessment_id),
    )
    state, state_reasons = _parse_single_current_state(
        state_log, expected_assessment_id=revision.assessment_id
    )
    if state_reasons or state is None or state.current_revision < revision.assessment_revision:
        return SharedAssessmentCommitResult(
            "fail_closed",
            blocked_reasons=state_reasons
            or ("shared_assessment_operation_current_state_missing",),
        )
    revision_index = tx.read_log(
        log_kind="shared_assessment_revision_index",
        key=_opaque_key("asmstate", revision.assessment_id),
    )
    index_reasons = _validate_revision_index(
        tx=tx,
        raw=revision_index,
        assessment_id=revision.assessment_id,
        current_state=state,
    )
    if index_reasons:
        return SharedAssessmentCommitResult(
            "fail_closed", blocked_reasons=index_reasons
        )
    assert revision_index is not None
    entry = revision_index[revision.assessment_revision - 1]
    if entry.get("revision_record_id") != record_id:
        return SharedAssessmentCommitResult(
            "fail_closed",
            blocked_reasons=("shared_assessment_operation_result_crosslink_invalid",),
        )
    return SharedAssessmentCommitResult(
        "duplicate_existing", revision=revision, current_state=state, persisted=True
    )


def _revision_from_dict(raw: dict) -> SharedAssessmentRevision | None:
    if (
        raw.get("schema") != "relaylm.shared_assessment_revision.v1"
        or type(raw.get("assessment_revision")) is not int
        or not isinstance(raw.get("evidence_refs"), list)
        or not isinstance(raw.get("uncertainty"), list)
        or raw.get("character_independent") is not True
        or (
            raw.get("supersedes_assessment_revision_or_null") is not None
            and type(raw.get("supersedes_assessment_revision_or_null")) is not int
        )
    ):
        return None
    refs: list[SharedAssessmentEvidenceRef] = []
    for item in raw["evidence_refs"]:
        if (
            not isinstance(item, dict)
            or type(item.get("lineage_revision")) is not int
        ):
            return None
        try:
            refs.append(
                SharedAssessmentEvidenceRef(
                    source_event_id=item["source_event_id"],
                    evidence_space_id=item["evidence_space_id"],
                    authorization_state=item["authorization_state"],
                    source_origin=item["source_origin"],
                    lineage_revision=item["lineage_revision"],
                )
            )
        except KeyError:
            return None
    predecessor = raw["supersedes_assessment_revision_or_null"]
    try:
        proposal = SharedAssessmentProposal(
            assessment_id=raw["assessment_id"],
            supported_content=raw["supported_content"],
            support_state=raw["support_state"],
            uncertainty=tuple(raw["uncertainty"]),
            temporal_state=raw["temporal_state"],
            governance_revision=raw["governance_revision"],
            expected_current_revision_or_null=predecessor,
        )
        revision, reasons = build_shared_assessment_revision(
            proposal=proposal,
            evidence_refs=tuple(refs),
            assessment_revision=raw["assessment_revision"],
            supersedes_assessment_revision_or_null=predecessor,
            created_at=raw["created_at"],
        )
    except (KeyError, TypeError, ValueError):
        return None
    if revision is None or reasons or revision.to_dict() != raw:
        return None
    return revision

def _validate_prepare_inputs(
    *, evidence_space_id: str, source_event_ids: tuple[str, ...], assessment_pass_id: str
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not _token(evidence_space_id):
        reasons.append("shared_assessment_evidence_space_id_invalid")
    if not 1 <= len(source_event_ids) <= 64:
        reasons.append("shared_assessment_source_event_count_invalid")
    if len(set(source_event_ids)) != len(source_event_ids) or any(
        not _token(item) for item in source_event_ids
    ):
        reasons.append("shared_assessment_source_event_ids_invalid")
    if not _token(assessment_pass_id):
        reasons.append("shared_assessment_pass_id_invalid")
    return tuple(reasons)


def shared_assessment_revision_record_id(assessment_id: str, revision: int) -> str:
    """Return the accepted ASM-1 immutable revision record identifier."""

    return _revision_record_id(assessment_id, revision)


def shared_assessment_formation_receipt_id(
    decision_id: str, decision_input_digest: str
) -> str:
    """Return the accepted decision-bound ASM-1 receipt identifier."""

    return _opaque_key("asmreceipt", f"{decision_id}\0{decision_input_digest}")


def shared_assessment_current_state_key(assessment_id: str) -> str:
    """Return the accepted ASM-1 logical current-state selector key."""

    return _opaque_key("asmstate", assessment_id)


def _revision_record_id(assessment_id: str, revision: int) -> str:
    return _opaque_key("asmrev", f"{assessment_id}\0{revision}")


def _opaque_key(prefix: str, value: str) -> str:
    return f"{prefix}_{sha256_hex(value.encode('utf-8'))}"


def _digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _parse_date_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def _valid_date_time(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = _parse_date_time(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _token(value: object, max_length: int = 128) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= max_length and all(
        ch not in value for ch in ("/", "\\", "\x00")
    )


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("shared_assessment_naive_datetime_forbidden")
    return current.astimezone(timezone.utc)


__all__ = [
    "SharedAssessmentCommitResult",
    "SharedAssessmentPrepareResult",
    "SharedAssessmentReceiptResult",
    "SharedAssessmentRuntimeGate",
    "build_shared_assessment_formation_receipt",
    "commit_shared_assessment_revision",
    "prepare_shared_assessment_pass",
    "resolve_shared_assessment_gate",
    "shared_assessment_current_state_key",
    "shared_assessment_formation_receipt_id",
    "shared_assessment_revision_record_id",
]
