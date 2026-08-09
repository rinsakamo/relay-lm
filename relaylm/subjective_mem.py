"""SM-1 logical records for one prepared Subjective MEM create result.

The target-schema records in this module are deliberately storage-neutral.
SM-1 persists the revision only as a prepared, non-canonical post-image; ST-1
owns canonical Markdown publication and the final durable commit receipt.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from relaylm.evidence.common import canonical_digest, utf8_text_digest
from relaylm.shared_assessment.models import (
    SharedAssessmentCurrentState,
    SharedAssessmentFormationAuthorizationReceipt,
    SharedAssessmentRevision,
)

SUBJECTIVE_MEM_DECISION_SCHEMA = "relaylm.subjective_mem_decision.v1"
SUBJECTIVE_MEM_REVISION_SCHEMA = "relaylm.subjective_mem_revision.v1"
SUBJECTIVE_MEM_CURRENT_STATE_SCHEMA = "relaylm.subjective_mem_current_state.v1"
SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA = "relaylm.subjective_mem_current_state.v2"
SUBJECTIVE_MEM_PREPARED_MANIFEST_SCHEMA = (
    "relaylm.subjective_mem_prepared_manifest.v1"
)

MEMORY_KINDS = frozenset({"episodic", "semantic"})
SALIENCE_VALUES = frozenset({"low", "medium", "high"})
STRENGTH_BASES = frozenset(
    {"assessment_support", "subjective_interpretation"}
)
_SUPPORT_CONFIDENCE_MAX = {
    "supported": 1.0,
    "uncertain": 0.0,
    "contradicted": 0.0,
    "temporally_changed": 0.0,
    "unresolved": 0.0,
    "competing_hypotheses": 0.0,
}


@dataclass(frozen=True)
class SubjectiveMemCharacterAuthority:
    workspace_or_tenant_ref: str
    character_id: str
    authority_revision: str

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_or_tenant_ref": self.workspace_or_tenant_ref,
            "character_id": self.character_id,
            "authority_revision": self.authority_revision,
        }


@dataclass(frozen=True)
class SubjectiveMemScopeBinding:
    scope_kind: str = "character_private"
    participant_id_or_null: str | None = None
    relationship_id_or_null: str | None = None
    scene_id_or_null: str | None = None
    audience_class: str = "private"
    identity_status: str = "known"

    def to_dict(self) -> dict[str, object]:
        return {
            "scope_kind": self.scope_kind,
            "participant_id_or_null": self.participant_id_or_null,
            "relationship_id_or_null": self.relationship_id_or_null,
            "scene_id_or_null": self.scene_id_or_null,
            "audience_class": self.audience_class,
            "identity_status": self.identity_status,
        }


@dataclass(frozen=True)
class SubjectiveMemFormationSnapshot:
    soul_revision: str
    memory_policy_revision: str
    boundary_revision: str
    scene_policy_revision_or_null: str | None
    relationship_revision_or_null: str | None
    formation_schema_version: str
    model_revision: str

    def to_dict(self) -> dict[str, object]:
        return {
            "soul_revision": self.soul_revision,
            "memory_policy_revision": self.memory_policy_revision,
            "boundary_revision": self.boundary_revision,
            "scene_policy_revision_or_null": self.scene_policy_revision_or_null,
            "relationship_revision_or_null": self.relationship_revision_or_null,
            "formation_schema_version": self.formation_schema_version,
            "model_revision": self.model_revision,
        }


@dataclass(frozen=True)
class SubjectiveMemStrength:
    grounded_confidence: float
    subjective_conviction: float
    salience: str
    reinforcement_count: int
    strength_basis: str

    def to_dict(self) -> dict[str, object]:
        return {
            "grounded_confidence": self.grounded_confidence,
            "subjective_conviction": self.subjective_conviction,
            "salience": self.salience,
            "reinforcement_count": self.reinforcement_count,
            "strength_basis": self.strength_basis,
        }


@dataclass(frozen=True)
class SubjectiveMemProposalBoundary:
    """Caller attestation required before deterministic SM-1 apply.

    SM-1 does not run a semantic model.  These exact fixed assertions make the
    producer boundary explicit and prevent unsupported proposal classes from
    silently entering the prepared create path.
    """

    subject_class: str = "personal_subjective_memory"
    grounded_content_preserved: bool = True
    uncertainty_preserved: bool = True
    participant_identity_not_invented: bool = True
    scope_and_audience_preserved: bool = True
    temporal_grounding_not_rewritten: bool = True
    product_knowledge_excluded: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "subject_class": self.subject_class,
            "grounded_content_preserved": self.grounded_content_preserved,
            "uncertainty_preserved": self.uncertainty_preserved,
            "participant_identity_not_invented": (
                self.participant_identity_not_invented
            ),
            "scope_and_audience_preserved": self.scope_and_audience_preserved,
            "temporal_grounding_not_rewritten": (
                self.temporal_grounding_not_rewritten
            ),
            "product_knowledge_excluded": self.product_knowledge_excluded,
        }


@dataclass(frozen=True)
class SubjectiveMemCreateProposal:
    subjective_meaning: str = field(repr=False)
    memory_kind: str
    scope_binding: SubjectiveMemScopeBinding
    formation_snapshot: SubjectiveMemFormationSnapshot
    strength: SubjectiveMemStrength
    boundary: SubjectiveMemProposalBoundary

    def to_dict(self) -> dict[str, object]:
        return {
            "subjective_meaning": self.subjective_meaning,
            "memory_kind": self.memory_kind,
            "scope_binding": self.scope_binding.to_dict(),
            "formation_snapshot": self.formation_snapshot.to_dict(),
            "strength": self.strength.to_dict(),
            "boundary": self.boundary.to_dict(),
        }


@dataclass(frozen=True)
class SubjectiveMemAssessmentAuthorizationProjection:
    current_revision_at_decision: int
    lifecycle_state_at_decision: str
    authorization_state_at_decision: str

    def to_dict(self) -> dict[str, object]:
        return {
            "current_revision_at_decision": self.current_revision_at_decision,
            "lifecycle_state_at_decision": self.lifecycle_state_at_decision,
            "authorization_state_at_decision": (
                self.authorization_state_at_decision
            ),
        }


@dataclass(frozen=True)
class SubjectiveMemDecision:
    decision_id: str
    character_id: str
    assessment_id: str
    assessment_revision: int
    supported_content_digest: str
    assessment_authorization_receipt: SubjectiveMemAssessmentAuthorizationProjection
    scope_binding: SubjectiveMemScopeBinding
    result_memory_id: str
    decided_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SUBJECTIVE_MEM_DECISION_SCHEMA,
            "decision_id": self.decision_id,
            "character_id": self.character_id,
            "assessment_ref": {
                "assessment_id": self.assessment_id,
                "assessment_revision": self.assessment_revision,
                "supported_content_digest": self.supported_content_digest,
            },
            "assessment_authorization_receipt": (
                self.assessment_authorization_receipt.to_dict()
            ),
            "scope_binding": self.scope_binding.to_dict(),
            "candidate_memory_refs": [],
            "similarity_granted_authority": False,
            "outcome": "create",
            "target_memory_ref_or_null": None,
            "result_memory_ref_or_null": {
                "memory_id": self.result_memory_id,
                "memory_revision": 1,
            },
            "result_relation_id_or_null": None,
            "hold_reason_or_null": None,
            "decided_at": self.decided_at,
        }


@dataclass(frozen=True)
class SubjectiveMemRevision:
    """One immutable canonical Subjective MEM revision.

    SM-1 callers may continue using the original constructor: the trailing
    defaults describe the revision-1 active create shape.  LC-1 lifecycle
    callers set the explicit revision, predecessor, lifecycle, and authority
    fields without mutating an earlier revision in place.
    """

    memory_id: str
    character_id: str
    assessment_id: str
    assessment_revision: int
    grounded_content: str = field(repr=False)
    grounded_content_digest: str
    subjective_meaning: str = field(repr=False)
    memory_kind: str
    scope_binding: SubjectiveMemScopeBinding
    formation_snapshot: SubjectiveMemFormationSnapshot
    strength: SubjectiveMemStrength
    decision_id: str
    created_at: str
    memory_revision: int = 1
    formation_stage: str = "primary"
    lifecycle_state: str = "active"
    retrieval_visible: bool = True
    predecessor_revision_or_null: int | None = None
    authorization_kind: str = "formation_decision"

    @property
    def authorization_id(self) -> str:
        return self.decision_id

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SUBJECTIVE_MEM_REVISION_SCHEMA,
            "memory_id": self.memory_id,
            "memory_revision": self.memory_revision,
            "character_id": self.character_id,
            "grounded_assessment_ref": {
                "assessment_id": self.assessment_id,
                "assessment_revision": self.assessment_revision,
                "supported_content_digest": self.grounded_content_digest,
            },
            "grounded_content": self.grounded_content,
            "grounded_content_digest": self.grounded_content_digest,
            "subjective_meaning": self.subjective_meaning,
            "formation_stage": self.formation_stage,
            "memory_kind": self.memory_kind,
            "scope_binding": self.scope_binding.to_dict(),
            "formation_snapshot": self.formation_snapshot.to_dict(),
            "strength": self.strength.to_dict(),
            "lifecycle_state": self.lifecycle_state,
            "retrieval_visible": self.retrieval_visible,
            "predecessor_revision_or_null": self.predecessor_revision_or_null,
            "authorization_ref": {
                "authority_kind": self.authorization_kind,
                "authority_id": self.authorization_id,
            },
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class SubjectiveMemCurrentState:
    memory_state_id: str
    memory_id: str
    character_id: str
    updated_at: str
    mutation_state: str = "prepared"
    retrieval_eligible: bool = False
    current_revision: int = 1
    lifecycle_state: str = "active"
    workspace_authority_digest: str | None = None
    scope_binding_digest: str | None = None
    page_id: str | None = None
    block_id: str | None = None
    canonical_page_digest: str | None = None
    authorization_kind: str | None = None
    authorization_id: str | None = None
    current_receipt_id: str | None = None

    def __post_init__(self) -> None:
        lifecycle_states = {
            "active",
            "pinned",
            "held",
            "hidden",
            "superseded",
            "purged",
        }
        mutation_states = {"none", "prepared", "recovery_required", "corrupt"}
        expected_eligible = (
            self.mutation_state == "none"
            and self.lifecycle_state in {"active", "pinned"}
        )
        authority_values = (
            self.workspace_authority_digest,
            self.scope_binding_digest,
            self.page_id,
            self.block_id,
            self.canonical_page_digest,
            self.authorization_kind,
            self.authorization_id,
            self.current_receipt_id,
        )
        unbound = all(value is None for value in authority_values)
        bound = all(
            isinstance(value, str) and bool(value)
            for value in authority_values
        )
        if bound:
            assert self.workspace_authority_digest is not None
            assert self.scope_binding_digest is not None
            assert self.canonical_page_digest is not None
            if (
                len(self.workspace_authority_digest) != 64
                or len(self.scope_binding_digest) != 64
                or not self.canonical_page_digest.startswith("sha256:")
                or len(self.canonical_page_digest) != 71
            ):
                raise ValueError("subjective_mem_current_state_authority_invalid")
        if (
            self.lifecycle_state not in lifecycle_states
            or self.mutation_state not in mutation_states
            or type(self.current_revision) is not int
            or self.current_revision < 1
            or self.retrieval_eligible is not expected_eligible
            or not (unbound or bound)
        ):
            raise ValueError("subjective_mem_current_state_pair_invalid")

    @property
    def authority_bound(self) -> bool:
        return self.workspace_authority_digest is not None

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": (
                SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA
                if self.authority_bound
                else SUBJECTIVE_MEM_CURRENT_STATE_SCHEMA
            ),
            "memory_state_id": self.memory_state_id,
            "memory_id": self.memory_id,
            "character_id": self.character_id,
            "current_revision": self.current_revision,
            "lifecycle_state": self.lifecycle_state,
            "mutation_state": self.mutation_state,
            "retrieval_eligible": self.retrieval_eligible,
            "updated_at": self.updated_at,
        }
        if self.authority_bound:
            body["authority_binding"] = {
                "workspace_authority_digest": self.workspace_authority_digest,
                "scope_binding_digest": self.scope_binding_digest,
                "page_id": self.page_id,
                "block_id": self.block_id,
                "canonical_page_digest": self.canonical_page_digest,
                "authorization_ref": {
                    "authority_kind": self.authorization_kind,
                    "authority_id": self.authorization_id,
                },
                "current_receipt_id": self.current_receipt_id,
            }
        return body
@dataclass(frozen=True)
class SubjectiveMemPreparedManifest:
    prepared_manifest_id: str
    prepared_revision_record_id: str
    prepared_revision_digest: str
    decision_id: str
    memory_id: str
    character_id: str
    prepared_at: str

    def _digest_input(self) -> dict[str, object]:
        return {
            "schema": SUBJECTIVE_MEM_PREPARED_MANIFEST_SCHEMA,
            "prepared_manifest_id": self.prepared_manifest_id,
            "prepared_revision_record_id": self.prepared_revision_record_id,
            "prepared_revision_digest": self.prepared_revision_digest,
            "decision_id": self.decision_id,
            "memory_ref": {"memory_id": self.memory_id, "memory_revision": 1},
            "character_id": self.character_id,
            "publication_state": "prepared_noncanonical",
            "canonical_markdown_published": False,
            "commit_receipt_present": False,
            "retrieval_eligible": False,
            "st1_finalization_required": True,
            "prepared_at": self.prepared_at,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._digest_input()
        return {**body, "manifest_digest": canonical_digest(body)}


def resolve_subjective_mem_character_authority(
    config: object,
    *,
    workspace_or_tenant_ref: str,
    character_id: str,
) -> tuple[SubjectiveMemCharacterAuthority | None, tuple[str, ...]]:
    """Resolve one character by configured opaque membership, never prose/path.

    The authority token is derived only from the workspace, opaque character
    key, and resolver schema.  Character document paths and content-bearing
    configuration do not participate in logical identity.  Callers must still
    resolve against the current registry on every attempt so removed
    characters fail closed.
    """

    if not _token(workspace_or_tenant_ref) or not _token(character_id):
        return None, ("subjective_mem_character_authority_invalid",)
    characters = getattr(config, "characters", None)
    if not isinstance(characters, dict) or character_id not in characters:
        return None, ("subjective_mem_character_unknown",)
    character = characters[character_id]
    if not hasattr(character, "model_dump") and not isinstance(character, dict):
        return None, ("subjective_mem_character_authority_invalid",)
    revision = "charauth_" + canonical_digest(
        {
            "schema": "relaylm.character_authority.v1",
            "workspace_or_tenant_ref": workspace_or_tenant_ref,
            "character_id": character_id,
            "registry_membership": "current",
        }
    )
    return (
        SubjectiveMemCharacterAuthority(
            workspace_or_tenant_ref=workspace_or_tenant_ref,
            character_id=character_id,
            authority_revision=revision,
        ),
        (),
    )


def validate_subjective_mem_create_inputs(
    *,
    character_authority: SubjectiveMemCharacterAuthority,
    assessment_revision: SharedAssessmentRevision,
    assessment_current_state: SharedAssessmentCurrentState,
    proposal: SubjectiveMemCreateProposal,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if type(character_authority) is not SubjectiveMemCharacterAuthority or any(
        not _token(value)
        for value in (
            character_authority.workspace_or_tenant_ref,
            character_authority.character_id,
            character_authority.authority_revision,
        )
    ):
        reasons.append("subjective_mem_character_authority_invalid")
    if type(assessment_revision) is not SharedAssessmentRevision:
        reasons.append("subjective_mem_assessment_revision_invalid")
    if type(assessment_current_state) is not SharedAssessmentCurrentState:
        reasons.append("subjective_mem_assessment_current_state_invalid")
    if reasons:
        return tuple(reasons)
    if (
        assessment_current_state.assessment_id != assessment_revision.assessment_id
        or assessment_current_state.current_revision
        != assessment_revision.assessment_revision
        or assessment_current_state.lifecycle_state != "active"
        or assessment_current_state.authorization_state != "current_admitted"
    ):
        reasons.append("subjective_mem_assessment_not_exact_current_admitted")
    if type(proposal) is not SubjectiveMemCreateProposal:
        return (*reasons, "subjective_mem_create_proposal_invalid")
    if not _bounded_text(proposal.subjective_meaning, 4000):
        reasons.append("subjective_mem_subjective_meaning_invalid")
    if proposal.memory_kind not in MEMORY_KINDS:
        reasons.append("subjective_mem_memory_kind_invalid")
    if (
        type(proposal.boundary) is not SubjectiveMemProposalBoundary
        or proposal.boundary.to_dict()
        != SubjectiveMemProposalBoundary().to_dict()
    ):
        reasons.append("subjective_mem_proposal_boundary_unattested")
    if (
        type(proposal.scope_binding) is not SubjectiveMemScopeBinding
        or proposal.scope_binding.to_dict()
        != SubjectiveMemScopeBinding().to_dict()
    ):
        reasons.append("subjective_mem_scope_unsupported")
    snapshot = proposal.formation_snapshot
    if type(snapshot) is not SubjectiveMemFormationSnapshot or any(
        not _token(value)
        for value in (
            getattr(snapshot, "soul_revision", None),
            getattr(snapshot, "memory_policy_revision", None),
            getattr(snapshot, "boundary_revision", None),
            getattr(snapshot, "model_revision", None),
        )
    ):
        reasons.append("subjective_mem_formation_snapshot_invalid")
    elif (
        snapshot.scene_policy_revision_or_null is not None
        or snapshot.relationship_revision_or_null is not None
        or snapshot.formation_schema_version != "subjective-mem-v1"
    ):
        reasons.append("subjective_mem_formation_snapshot_unsupported")
    strength = proposal.strength
    if type(strength) is not SubjectiveMemStrength:
        reasons.append("subjective_mem_strength_invalid")
    else:
        for value in (strength.grounded_confidence, strength.subjective_conviction):
            if type(value) not in {int, float} or not 0.0 <= float(value) <= 1.0:
                reasons.append("subjective_mem_strength_invalid")
                break
        if (
            strength.salience not in SALIENCE_VALUES
            or type(strength.reinforcement_count) is not int
            or strength.reinforcement_count != 0
            or strength.strength_basis not in STRENGTH_BASES
        ):
            reasons.append("subjective_mem_strength_invalid")
        maximum = _SUPPORT_CONFIDENCE_MAX.get(assessment_revision.support_state)
        if maximum is None or strength.grounded_confidence > maximum:
            reasons.append("subjective_mem_grounded_confidence_exceeds_assessment")
    return tuple(dict.fromkeys(reasons))


def validate_subjective_mem_crosslinks(
    *,
    receipt: SharedAssessmentFormationAuthorizationReceipt,
    decision: SubjectiveMemDecision,
    revision: SubjectiveMemRevision,
    current_state: SubjectiveMemCurrentState,
    manifest: SubjectiveMemPreparedManifest,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if receipt.decision_id != decision.decision_id:
        reasons.append("subjective_mem_receipt_decision_mismatch")
    expected_receipt_projection = {
        "current_revision_at_decision": receipt.current_revision_at_decision,
        "lifecycle_state_at_decision": receipt.lifecycle_state_at_decision,
        "authorization_state_at_decision": receipt.authorization_state_at_decision,
    }
    if (
        decision.assessment_authorization_receipt.to_dict()
        != expected_receipt_projection
    ):
        reasons.append("subjective_mem_receipt_projection_mismatch")
    if decision.result_memory_id != revision.memory_id:
        reasons.append("subjective_mem_decision_result_mismatch")
    if revision.decision_id != decision.decision_id:
        reasons.append("subjective_mem_result_authorization_mismatch")
    if current_state.memory_id != revision.memory_id:
        reasons.append("subjective_mem_current_state_result_mismatch")
    if len({decision.character_id, revision.character_id, current_state.character_id, manifest.character_id}) != 1:
        reasons.append("subjective_mem_character_crosslink_mismatch")
    if decision.scope_binding.to_dict() != revision.scope_binding.to_dict():
        reasons.append("subjective_mem_scope_crosslink_mismatch")
    if utf8_text_digest(revision.grounded_content) != revision.grounded_content_digest:
        reasons.append("subjective_mem_grounded_content_digest_invalid")
    if (
        manifest.decision_id != decision.decision_id
        or manifest.memory_id != revision.memory_id
        or manifest.prepared_revision_digest != canonical_digest(revision.to_dict())
    ):
        reasons.append("subjective_mem_prepared_manifest_crosslink_mismatch")
    if len(
        {
            receipt.issued_at,
            decision.decided_at,
            revision.created_at,
            current_state.updated_at,
            manifest.prepared_at,
        }
    ) != 1:
        reasons.append("subjective_mem_timestamp_crosslink_mismatch")
    if (
        decision.assessment_id != revision.assessment_id
        or decision.assessment_revision != revision.assessment_revision
        or decision.supported_content_digest != revision.grounded_content_digest
        or receipt.assessment_id != revision.assessment_id
        or receipt.assessment_revision != revision.assessment_revision
        or receipt.supported_content_digest != revision.grounded_content_digest
    ):
        reasons.append("subjective_mem_assessment_crosslink_mismatch")
    return tuple(dict.fromkeys(reasons))


def _bounded_text(value: object, max_length: int) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= max_length
        and "\x00" not in value
    )


def _token(value: object, max_length: int = 128) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= max_length and all(
        ch not in value for ch in ("/", "\\", "\x00")
    )


__all__ = [
    "SubjectiveMemAssessmentAuthorizationProjection",
    "SubjectiveMemCharacterAuthority",
    "SubjectiveMemCreateProposal",
    "SubjectiveMemCurrentState",
    "SubjectiveMemDecision",
    "SubjectiveMemFormationSnapshot",
    "SubjectiveMemPreparedManifest",
    "SubjectiveMemProposalBoundary",
    "SubjectiveMemRevision",
    "SubjectiveMemScopeBinding",
    "SubjectiveMemStrength",
    "resolve_subjective_mem_character_authority",
    "validate_subjective_mem_create_inputs",
    "validate_subjective_mem_crosslinks",
]
