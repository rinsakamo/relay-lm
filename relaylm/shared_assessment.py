"""ASM-1 character-independent Shared Assessment records and pass boundary.

This module deliberately stops before Subjective MEM.  It owns the exact
runtime shapes for the two Shared Assessment records in Contract 3 plus a
content-bearing, non-durable Assessment Pass input and a content-free
formation-time authorization receipt.  No type in this module carries a
character, SOUL, REL, SCN, EMO, STYLE, or Subjective MEM field.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from relaylm.evidence_common import canonical_digest, utf8_text_digest

SHARED_ASSESSMENT_REVISION_SCHEMA = "relaylm.shared_assessment_revision.v1"
SHARED_ASSESSMENT_CURRENT_STATE_SCHEMA = (
    "relaylm.shared_assessment_current_state.v1"
)
SHARED_ASSESSMENT_PASS_BUNDLE_SCHEMA = "relaylm.shared_assessment_pass_bundle.v1"
SHARED_ASSESSMENT_FORMATION_RECEIPT_SCHEMA = (
    "relaylm.shared_assessment_formation_authorization_receipt.v1"
)

SUPPORT_STATES = frozenset(
    {
        "supported",
        "uncertain",
        "contradicted",
        "temporally_changed",
        "unresolved",
        "competing_hypotheses",
    }
)
TEMPORAL_STATES = frozenset({"current", "historical", "time_bounded", "unknown"})
SOURCE_ORIGINS = frozenset({"user", "assistant", "tool", "operator"})
MAX_ASSESSMENT_PASS_PARTS = 256
MAX_ASSESSMENT_PASS_TEXT_BYTES = 1024 * 1024



@dataclass(frozen=True)
class SharedAssessmentEvidenceRef:
    source_event_id: str
    evidence_space_id: str
    authorization_state: str
    source_origin: str
    lineage_revision: int

    def to_dict(self) -> dict[str, object]:
        return {
            "source_event_id": self.source_event_id,
            "evidence_space_id": self.evidence_space_id,
            "authorization_state": self.authorization_state,
            "source_origin": self.source_origin,
            "lineage_revision": self.lineage_revision,
        }


@dataclass(frozen=True)
class SharedAssessmentPassPart:
    source_event_id: str
    part_id: str
    media_type: str
    text: str = field(repr=False)
    content_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "source_event_id": self.source_event_id,
            "part_id": self.part_id,
            "media_type": self.media_type,
            "text": self.text,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True)
class SharedAssessmentAuthorizationSnapshot:
    source_event_id: str
    access_authorization_id: str
    authority_snapshot_digest: str
    selected_part_ids: tuple[str, ...]
    matched_grant_ids: tuple[str, ...]
    governance_revision: int
    validation_bundle_revision: int
    not_before: str
    not_after: str

    def to_dict(self) -> dict[str, object]:
        return {
            "source_event_id": self.source_event_id,
            "access_authorization_id": self.access_authorization_id,
            "authority_snapshot_digest": self.authority_snapshot_digest,
            "selected_part_ids": list(self.selected_part_ids),
            "matched_grant_ids": list(self.matched_grant_ids),
            "governance_revision": self.governance_revision,
            "validation_bundle_revision": self.validation_bundle_revision,
            "not_before": self.not_before,
            "not_after": self.not_after,
        }


@dataclass(frozen=True)
class SharedAssessmentPassBundle:
    schema: str
    assessment_pass_id: str
    evidence_space_id: str
    evidence_refs: tuple[SharedAssessmentEvidenceRef, ...]
    parts: tuple[SharedAssessmentPassPart, ...]
    authorization_snapshots: tuple[SharedAssessmentAuthorizationSnapshot, ...]
    prepared_at: str
    bundle_digest: str

    def _digest_input(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "assessment_pass_id": self.assessment_pass_id,
            "evidence_space_id": self.evidence_space_id,
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
            "parts": [item.to_dict() for item in self.parts],
            "authorization_snapshots": [
                item.to_dict() for item in self.authorization_snapshots
            ],
            "prepared_at": self.prepared_at,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._digest_input(), "bundle_digest": self.bundle_digest}

    def is_self_authenticating(self) -> bool:
        return self.bundle_digest == canonical_digest(self._digest_input())


@dataclass(frozen=True)
class SharedAssessmentProposal:
    assessment_id: str
    supported_content: str = field(repr=False)
    support_state: str
    uncertainty: tuple[str, ...]
    temporal_state: str
    governance_revision: str
    expected_current_revision_or_null: int | None = None


@dataclass(frozen=True)
class SharedAssessmentRevision:
    schema: str
    assessment_id: str
    assessment_revision: int
    evidence_refs: tuple[SharedAssessmentEvidenceRef, ...]
    supported_content: str = field(repr=False)
    supported_content_digest: str
    support_state: str
    uncertainty: tuple[str, ...]
    temporal_state: str
    character_independent: bool
    governance_revision: str
    supersedes_assessment_revision_or_null: int | None
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "assessment_id": self.assessment_id,
            "assessment_revision": self.assessment_revision,
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
            "supported_content": self.supported_content,
            "supported_content_digest": self.supported_content_digest,
            "support_state": self.support_state,
            "uncertainty": list(self.uncertainty),
            "temporal_state": self.temporal_state,
            "character_independent": self.character_independent,
            "governance_revision": self.governance_revision,
            "supersedes_assessment_revision_or_null": (
                self.supersedes_assessment_revision_or_null
            ),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SharedAssessmentCurrentState:
    schema: str
    assessment_state_id: str
    assessment_id: str
    current_revision: int
    lifecycle_state: str
    authorization_state: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "assessment_state_id": self.assessment_state_id,
            "assessment_id": self.assessment_id,
            "current_revision": self.current_revision,
            "lifecycle_state": self.lifecycle_state,
            "authorization_state": self.authorization_state,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class SharedAssessmentFormationAuthorizationReceipt:
    schema: str
    receipt_id: str
    assessment_id: str
    assessment_revision: int
    supported_content_digest: str
    current_revision_at_decision: int
    lifecycle_state_at_decision: str
    authorization_state_at_decision: str
    evidence_authority_snapshot_digests: tuple[str, ...]
    decision_id: str
    decision_input_digest: str
    issued_at: str
    receipt_digest: str

    def _digest_input(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "receipt_id": self.receipt_id,
            "assessment_id": self.assessment_id,
            "assessment_revision": self.assessment_revision,
            "supported_content_digest": self.supported_content_digest,
            "assessment_authorization_receipt": {
                "current_revision_at_decision": self.current_revision_at_decision,
                "lifecycle_state_at_decision": self.lifecycle_state_at_decision,
                "authorization_state_at_decision": self.authorization_state_at_decision,
            },
            "evidence_authority_snapshot_digests": list(
                self.evidence_authority_snapshot_digests
            ),
            "decision_id": self.decision_id,
            "decision_input_digest": self.decision_input_digest,
            "issued_at": self.issued_at,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._digest_input(), "receipt_digest": self.receipt_digest}

    def is_self_authenticating(self) -> bool:
        return self.receipt_digest == canonical_digest(self._digest_input())


def validate_shared_assessment_proposal(
    proposal: SharedAssessmentProposal,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if type(proposal) is not SharedAssessmentProposal:
        return ("shared_assessment_proposal_type_invalid",)
    if not _token(proposal.assessment_id):
        reasons.append("shared_assessment_id_invalid")
    if not isinstance(proposal.supported_content, str) or not (
        1 <= len(proposal.supported_content) <= 8000
    ):
        reasons.append("shared_assessment_supported_content_invalid")
    if proposal.support_state not in SUPPORT_STATES:
        reasons.append("shared_assessment_support_state_invalid")
    if proposal.temporal_state not in TEMPORAL_STATES:
        reasons.append("shared_assessment_temporal_state_invalid")
    if type(proposal.uncertainty) is not tuple:
        reasons.append("shared_assessment_uncertainty_invalid")
    elif (
        len(proposal.uncertainty) > 32
        or len(set(proposal.uncertainty)) != len(proposal.uncertainty)
        or any(
            not isinstance(item, str) or not 1 <= len(item) <= 256
            for item in proposal.uncertainty
        )
    ):
        reasons.append("shared_assessment_uncertainty_invalid")
    if not _token(proposal.governance_revision):
        reasons.append("shared_assessment_governance_revision_invalid")
    if proposal.expected_current_revision_or_null is not None and (
        type(proposal.expected_current_revision_or_null) is not int
        or proposal.expected_current_revision_or_null < 1
    ):
        reasons.append("shared_assessment_expected_current_revision_invalid")
    return tuple(dict.fromkeys(reasons))


def validate_shared_assessment_pass_bundle(
    bundle: SharedAssessmentPassBundle,
    *,
    verify_digest: bool = True,
) -> tuple[str, ...]:
    """Validate the bounded, character-independent Assessment Pass envelope."""

    reasons: list[str] = []
    if type(bundle) is not SharedAssessmentPassBundle:
        return ("shared_assessment_pass_bundle_type_invalid",)
    if bundle.schema != SHARED_ASSESSMENT_PASS_BUNDLE_SCHEMA:
        reasons.append("shared_assessment_pass_bundle_schema_invalid")
    if not _token(bundle.assessment_pass_id):
        reasons.append("shared_assessment_pass_id_invalid")
    if not _token(bundle.evidence_space_id):
        reasons.append("shared_assessment_evidence_space_id_invalid")
    if not _date_time(bundle.prepared_at):
        reasons.append("shared_assessment_pass_prepared_at_invalid")
    if not _digest(bundle.bundle_digest):
        reasons.append("shared_assessment_pass_bundle_digest_invalid")
    if not 1 <= len(bundle.evidence_refs) <= 64:
        reasons.append("shared_assessment_evidence_ref_count_invalid")
    if any(type(item) is not SharedAssessmentEvidenceRef for item in bundle.evidence_refs):
        return ("shared_assessment_evidence_ref_type_invalid",)
    source_ids = [item.source_event_id for item in bundle.evidence_refs]
    if all(isinstance(item, str) for item in source_ids):
        if len(set(source_ids)) != len(source_ids):
            reasons.append("shared_assessment_evidence_refs_duplicate")
    else:
        reasons.append("shared_assessment_source_event_id_invalid")
    for item in bundle.evidence_refs:
        if not _token(item.source_event_id):
            reasons.append("shared_assessment_source_event_id_invalid")
        if item.evidence_space_id != bundle.evidence_space_id:
            reasons.append("shared_assessment_evidence_space_mismatch")
        if item.authorization_state != "current_admitted":
            reasons.append("shared_assessment_evidence_not_current_admitted")
        if item.source_origin not in SOURCE_ORIGINS:
            reasons.append("shared_assessment_source_origin_invalid")
        if type(item.lineage_revision) is not int or item.lineage_revision < 1:
            reasons.append("shared_assessment_lineage_revision_invalid")

    if len(bundle.authorization_snapshots) != len(bundle.evidence_refs):
        reasons.append("shared_assessment_authorization_snapshot_count_invalid")
    if any(
        type(item) is not SharedAssessmentAuthorizationSnapshot
        for item in bundle.authorization_snapshots
    ):
        return ("shared_assessment_authorization_snapshot_type_invalid",)
    snapshot_source_ids = [item.source_event_id for item in bundle.authorization_snapshots]
    snapshot_ids_unique = all(isinstance(item, str) for item in snapshot_source_ids) and (
        len(set(snapshot_source_ids)) == len(snapshot_source_ids)
    )
    if snapshot_source_ids != source_ids or not snapshot_ids_unique:
        reasons.append("shared_assessment_authorization_snapshot_order_invalid")
    for item in bundle.authorization_snapshots:
        if not _token(item.access_authorization_id):
            reasons.append("shared_assessment_access_authorization_id_invalid")
        if not _digest(item.authority_snapshot_digest):
            reasons.append("shared_assessment_authority_snapshot_digest_invalid")
        if (
            not item.selected_part_ids
            or tuple(sorted(set(item.selected_part_ids))) != item.selected_part_ids
            or any(not _token(part_id) for part_id in item.selected_part_ids)
        ):
            reasons.append("shared_assessment_selected_part_ids_invalid")
        if (
            not item.matched_grant_ids
            or tuple(sorted(set(item.matched_grant_ids))) != item.matched_grant_ids
            or any(not _token(grant_id) for grant_id in item.matched_grant_ids)
        ):
            reasons.append("shared_assessment_matched_grant_ids_invalid")
        if type(item.governance_revision) is not int or item.governance_revision < 1:
            reasons.append("shared_assessment_authorization_governance_revision_invalid")
        if (
            type(item.validation_bundle_revision) is not int
            or item.validation_bundle_revision < 1
        ):
            reasons.append("shared_assessment_validation_bundle_revision_invalid")
        if not _date_time(item.not_before):
            reasons.append("shared_assessment_authorization_not_before_invalid")
        if not _date_time(item.not_after):
            reasons.append("shared_assessment_authorization_not_after_invalid")
        if _date_time(item.not_before) and _date_time(item.not_after):
            if _parse_date_time(item.not_before) >= _parse_date_time(item.not_after):
                reasons.append("shared_assessment_authorization_window_invalid")

    if not 1 <= len(bundle.parts) <= MAX_ASSESSMENT_PASS_PARTS:
        reasons.append("shared_assessment_pass_part_count_invalid")
    if any(type(item) is not SharedAssessmentPassPart for item in bundle.parts):
        return ("shared_assessment_pass_part_type_invalid",)
    part_keys: list[tuple[str, str]] = []
    total_bytes = 0
    part_ids_by_source: dict[str, list[str]] = {source_id: [] for source_id in source_ids}
    for item in bundle.parts:
        part_keys.append((item.source_event_id, item.part_id))
        if item.source_event_id not in part_ids_by_source:
            reasons.append("shared_assessment_pass_part_source_invalid")
        else:
            part_ids_by_source[item.source_event_id].append(item.part_id)
        if not _token(item.part_id):
            reasons.append("shared_assessment_pass_part_id_invalid")
        if not isinstance(item.text, str):
            reasons.append("shared_assessment_pass_part_text_invalid")
            continue
        try:
            encoded_length = len(item.text.encode("utf-8", errors="strict"))
        except UnicodeEncodeError:
            reasons.append("shared_assessment_pass_part_text_invalid")
            continue
        total_bytes += encoded_length
        if encoded_length > 256 * 1024:
            reasons.append("shared_assessment_pass_part_too_large")
        if (
            not isinstance(item.media_type, str)
            or item.media_type.split(";", 1)[0].strip().lower() != "text/plain"
        ):
            reasons.append("shared_assessment_pass_part_media_type_invalid")
        if not _digest(item.content_digest) or utf8_text_digest(item.text) != item.content_digest:
            reasons.append("shared_assessment_pass_part_digest_invalid")
    if len(set(part_keys)) != len(part_keys):
        reasons.append("shared_assessment_pass_parts_duplicate")
    if total_bytes > MAX_ASSESSMENT_PASS_TEXT_BYTES:
        reasons.append("shared_assessment_pass_text_bound_exceeded")
    snapshot_by_source = {
        item.source_event_id: item for item in bundle.authorization_snapshots
    }
    for source_id in source_ids:
        snapshot = snapshot_by_source.get(source_id)
        if snapshot is None:
            continue
        if tuple(sorted(part_ids_by_source[source_id])) != snapshot.selected_part_ids:
            reasons.append("shared_assessment_pass_parts_authorization_mismatch")
    if not reasons and verify_digest and not bundle.is_self_authenticating():
        reasons.append("shared_assessment_pass_bundle_digest_mismatch")
    return tuple(dict.fromkeys(reasons))


def build_shared_assessment_revision(
    *,
    proposal: SharedAssessmentProposal,
    evidence_refs: tuple[SharedAssessmentEvidenceRef, ...],
    assessment_revision: int,
    supersedes_assessment_revision_or_null: int | None,
    created_at: str,
) -> tuple[SharedAssessmentRevision | None, tuple[str, ...]]:
    reasons = list(validate_shared_assessment_proposal(proposal))
    if type(assessment_revision) is not int or assessment_revision < 1:
        reasons.append("shared_assessment_revision_invalid")
    expected_predecessor = None if assessment_revision == 1 else assessment_revision - 1
    if supersedes_assessment_revision_or_null != expected_predecessor:
        reasons.append("shared_assessment_predecessor_not_consecutive")
    if not 1 <= len(evidence_refs) <= 64:
        reasons.append("shared_assessment_evidence_ref_count_invalid")
    evidence_spaces = {item.evidence_space_id for item in evidence_refs}
    if len(evidence_spaces) != 1:
        reasons.append("shared_assessment_evidence_space_mismatch")
    elif not assessment_id_matches_evidence_space(
        proposal.assessment_id, next(iter(evidence_spaces))
    ):
        reasons.append("shared_assessment_id_evidence_space_mismatch")
    ref_keys = [
        (item.source_event_id, item.evidence_space_id, item.lineage_revision)
        for item in evidence_refs
    ]
    if len(set(ref_keys)) != len(ref_keys):
        reasons.append("shared_assessment_evidence_refs_duplicate")
    for item in evidence_refs:
        if item.authorization_state != "current_admitted":
            reasons.append("shared_assessment_evidence_not_current_admitted")
        if item.source_origin not in SOURCE_ORIGINS:
            reasons.append("shared_assessment_source_origin_invalid")
        if type(item.lineage_revision) is not int or item.lineage_revision < 1:
            reasons.append("shared_assessment_lineage_revision_invalid")
    if not _date_time(created_at):
        reasons.append("shared_assessment_created_at_invalid")
    if reasons:
        return None, tuple(dict.fromkeys(reasons))
    return (
        SharedAssessmentRevision(
            schema=SHARED_ASSESSMENT_REVISION_SCHEMA,
            assessment_id=proposal.assessment_id,
            assessment_revision=assessment_revision,
            evidence_refs=evidence_refs,
            supported_content=proposal.supported_content,
            supported_content_digest=utf8_text_digest(proposal.supported_content),
            support_state=proposal.support_state,
            uncertainty=proposal.uncertainty,
            temporal_state=proposal.temporal_state,
            character_independent=True,
            governance_revision=proposal.governance_revision,
            supersedes_assessment_revision_or_null=supersedes_assessment_revision_or_null,
            created_at=created_at,
        ),
        (),
    )


def _digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def derive_shared_assessment_id(evidence_space_id: str, logical_key: str) -> str:
    if not _token(evidence_space_id) or not _token(logical_key):
        raise ValueError("shared_assessment_identity_input_invalid")
    space_prefix = canonical_digest({"evidence_space_id": evidence_space_id})[:32]
    logical_digest = canonical_digest({"logical_key": logical_key})
    return f"asm_{space_prefix}_{logical_digest}"


def assessment_id_matches_evidence_space(assessment_id: object, evidence_space_id: object) -> bool:
    if not isinstance(assessment_id, str) or not _token(evidence_space_id):
        return False
    prefix = f"asm_{canonical_digest({'evidence_space_id': evidence_space_id})[:32]}_"
    suffix = assessment_id[len(prefix):] if assessment_id.startswith(prefix) else ""
    return len(suffix) == 64 and _digest(suffix)


def _parse_date_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _date_time(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = _parse_date_time(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _token(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 128 and all(
        ch not in value for ch in ("/", "\\", "\x00")
    )


__all__ = [
    "SHARED_ASSESSMENT_CURRENT_STATE_SCHEMA",
    "SHARED_ASSESSMENT_FORMATION_RECEIPT_SCHEMA",
    "SHARED_ASSESSMENT_PASS_BUNDLE_SCHEMA",
    "SHARED_ASSESSMENT_REVISION_SCHEMA",
    "SharedAssessmentAuthorizationSnapshot",
    "SharedAssessmentCurrentState",
    "SharedAssessmentEvidenceRef",
    "SharedAssessmentFormationAuthorizationReceipt",
    "SharedAssessmentPassBundle",
    "SharedAssessmentPassPart",
    "SharedAssessmentProposal",
    "SharedAssessmentRevision",
    "assessment_id_matches_evidence_space",
    "build_shared_assessment_revision",
    "derive_shared_assessment_id",
    "validate_shared_assessment_pass_bundle",
    "validate_shared_assessment_proposal",
]
