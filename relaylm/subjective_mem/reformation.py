"""Canonical anti-reformation authority for governed Subjective MEM formation.

Public and locked entrypoints delegate to one exact semantic evaluator. A valid
Forget tombstone blocks exact re-formation until its optional immutable Restore
release is proven by the shared release-lineage authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Literal

from relaylm.evidence.common import canonical_digest, utf8_text_digest
from relaylm.evidence.store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.subjective_mem.models import SubjectiveMemScopeBinding
from relaylm.subjective_mem.forget import (
    FORGET_REASON_CATEGORIES,
    FORGET_TOMBSTONE_SCHEMA,
    FORGET_TOMBSTONE_STATE_SCHEMA,
)
from relaylm.subjective_mem.lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
)
from relaylm.subjective_mem.tombstone_release import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA,
    inspect_subjective_mem_forget_tombstone_release_locked,
)

ReformationStatus = Literal["allowed", "blocked", "fail_closed"]
SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND = "subjective_mem_forget_tombstone_state"
_SEMANTIC_IDENTITY_SCHEMA = "relaylm.subjective_mem_semantic_identity.v1"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")

_STATE_FIELDS = frozenset(
    "schema tombstone_id tombstone_digest evidence_space_id character_id "
    "semantic_identity_digest memory_id hidden_revision formation_stage "
    "transition_id transition_digest receipt_id effective "
    "superseded_by_tombstone_id_or_null updated_at content_free".split()
)
_TOMBSTONE_FIELDS = frozenset(
    "schema tombstone_id evidence_space_id character_id memory_id source_revision "
    "hidden_revision formation_stage transition_id transition_digest receipt_id "
    "semantic_identity_digest scope_binding_digest authorization_class "
    "authorization_id reason_category policy_revision effective_at effective "
    "content_free tombstone_digest".split()
)
_RECEIPT_FIELDS = frozenset(
    "schema receipt_id intent_id intent_digest operation_id operation_kind "
    "operation_outcome input_digest evidence_space_id character_id memory_ref "
    "predecessor_revision formation_stage transition_id transition_digest "
    "tombstone_id tombstone_digest semantic_identity_digest authorization_class "
    "authorization_id reason_category policy_revision revision_schema page_schema "
    "block_schema renderer_revision partition_revision platform_revision page_id "
    "successor_block_id pre_image_digest post_image_digest successor_revision_digest "
    "current_state_digest projection_state ordinary_retrieval_wired finalized_at "
    "receipt_digest".split()
)
_TRANSITION_FIELDS = frozenset(
    "schema transition_id character_id memory_id from_revision to_revision operation "
    "from_lifecycle_state to_lifecycle_state from_formation_stage "
    "to_formation_stage authorized_by committed_at".split()
)


@dataclass(frozen=True)
class SubjectiveMemReformationCheck:
    status: ReformationStatus
    semantic_identity_digest: str | None = None
    tombstone_ids: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.status == "allowed"


def subjective_mem_semantic_identity_digest(
    *,
    evidence_space_id: str,
    character_id: str,
    grounded_content_digest: str,
    subjective_meaning: str,
    memory_kind: str,
    scope_binding: SubjectiveMemScopeBinding,
) -> str:
    """Return the exact non-heuristic semantic identity used by tombstones."""

    if not _token(evidence_space_id, 128) or not _token(character_id, 128):
        raise ValueError("subjective_mem_reformation_scope_invalid")
    if not _digest(grounded_content_digest):
        raise ValueError("subjective_mem_reformation_grounded_digest_invalid")
    if type(subjective_meaning) is not str or not 1 <= len(subjective_meaning) <= 4000:
        raise ValueError("subjective_mem_reformation_subjective_meaning_invalid")
    if memory_kind not in {"episodic", "semantic"}:
        raise ValueError("subjective_mem_reformation_memory_kind_invalid")
    if type(scope_binding) is not SubjectiveMemScopeBinding:
        raise ValueError("subjective_mem_reformation_scope_binding_invalid")
    return canonical_digest(
        {
            "schema": _SEMANTIC_IDENTITY_SCHEMA,
            "evidence_space_id": evidence_space_id,
            "character_id": character_id,
            "grounded_content_digest": grounded_content_digest,
            "subjective_meaning_digest": utf8_text_digest(subjective_meaning),
            "memory_kind": memory_kind,
            "scope_binding_digest": canonical_digest(scope_binding.to_dict()),
        }
    )


def check_subjective_mem_reformation(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_id: str,
    grounded_content_digest: str,
    subjective_meaning: str,
    memory_kind: str,
    scope_binding: SubjectiveMemScopeBinding,
) -> SubjectiveMemReformationCheck:
    """Check one exact candidate while acquiring the Evidence-space transaction."""

    if type(store) is not EvidenceRecordStore:
        return _failure("subjective_mem_reformation_store_invalid")
    candidate = _candidate(
        evidence_space_id,
        character_id,
        grounded_content_digest,
        subjective_meaning,
        memory_kind,
        scope_binding,
    )
    if isinstance(candidate, SubjectiveMemReformationCheck):
        return candidate
    try:
        with store.transaction(evidence_space_id) as tx:
            return _evaluate_subjective_mem_reformation_locked(tx, evidence_space_id, character_id, candidate)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        return _failure("subjective_mem_reformation_store_unavailable", candidate)


def check_subjective_mem_reformation_locked(
    *,
    tx: EvidenceStoreTransaction,
    evidence_space_id: str,
    character_id: str,
    grounded_content_digest: str,
    subjective_meaning: str,
    memory_kind: str,
    scope_binding: SubjectiveMemScopeBinding,
) -> SubjectiveMemReformationCheck:
    """Check one exact candidate while the caller owns the transaction."""

    if type(tx) is not EvidenceStoreTransaction or tx.evidence_space_id != evidence_space_id:
        return _failure("subjective_mem_reformation_transaction_invalid")
    candidate = _candidate(
        evidence_space_id,
        character_id,
        grounded_content_digest,
        subjective_meaning,
        memory_kind,
        scope_binding,
    )
    if isinstance(candidate, SubjectiveMemReformationCheck):
        return candidate
    try:
        return _evaluate_subjective_mem_reformation_locked(tx, evidence_space_id, character_id, candidate)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        return _failure("subjective_mem_reformation_store_unavailable", candidate)


def inspect_subjective_mem_reformation_digest_locked(
    *,
    tx: EvidenceStoreTransaction,
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> SubjectiveMemReformationCheck:
    """Inspect one already-derived identity through the canonical evaluator."""

    if type(tx) is not EvidenceStoreTransaction or tx.evidence_space_id != evidence_space_id:
        return _failure("subjective_mem_reformation_transaction_invalid")
    if (
        not _token(evidence_space_id, 128)
        or not _token(character_id, 128)
        or not _digest(semantic_identity_digest)
    ):
        return _failure("subjective_mem_reformation_candidate_invalid")
    try:
        return _evaluate_subjective_mem_reformation_locked(
            tx, evidence_space_id, character_id, semantic_identity_digest
        )
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        return _failure(
            "subjective_mem_reformation_store_unavailable",
            semantic_identity_digest,
        )


def _candidate(
    evidence_space_id: str,
    character_id: str,
    grounded_content_digest: str,
    subjective_meaning: str,
    memory_kind: str,
    scope_binding: SubjectiveMemScopeBinding,
) -> str | SubjectiveMemReformationCheck:
    try:
        return subjective_mem_semantic_identity_digest(
            evidence_space_id=evidence_space_id,
            character_id=character_id,
            grounded_content_digest=grounded_content_digest,
            subjective_meaning=subjective_meaning,
            memory_kind=memory_kind,
            scope_binding=scope_binding,
        )
    except (TypeError, ValueError):
        return _failure("subjective_mem_reformation_candidate_invalid")


def _evaluate_subjective_mem_reformation_locked(
    tx: EvidenceStoreTransaction,
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> SubjectiveMemReformationCheck:
    events = tx.read_log(
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        key=semantic_identity_digest,
    )
    if events in (None, []):
        return SubjectiveMemReformationCheck(
            "allowed", semantic_identity_digest=semantic_identity_digest
        )
    if not isinstance(events, list) or not events:
        return _failure(
            "subjective_mem_reformation_tombstone_state_corrupt",
            semantic_identity_digest,
        )
    seen: set[str] = set()
    blocked: list[str] = []
    for state in events:
        status, tombstone_id, reasons = _evaluate_tombstone(
            tx=tx,
            state=state,
            seen=seen,
            evidence_space_id=evidence_space_id,
            character_id=character_id,
            semantic_identity_digest=semantic_identity_digest,
        )
        if status == "invalid":
            return _failure(
                reasons[0]
                if reasons
                else "subjective_mem_reformation_tombstone_lineage_invalid",
                semantic_identity_digest,
            )
        assert tombstone_id is not None
        if status == "unreleased":
            blocked.append(tombstone_id)
        seen.add(tombstone_id)
    if blocked:
        return SubjectiveMemReformationCheck(
            "blocked",
            semantic_identity_digest=semantic_identity_digest,
            tombstone_ids=tuple(sorted(blocked)),
            blocked_reasons=("subjective_mem_reformation_blocked_by_forget",),
        )
    return SubjectiveMemReformationCheck(
        "allowed", semantic_identity_digest=semantic_identity_digest
    )


def _evaluate_tombstone(
    *,
    tx: EvidenceStoreTransaction,
    state: object,
    seen: set[str],
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> tuple[str, str | None, tuple[str, ...]]:
    if not _valid_state(
        state, evidence_space_id, character_id, semantic_identity_digest
    ):
        return "invalid", None, (
            "subjective_mem_reformation_tombstone_state_corrupt",
        )
    assert isinstance(state, dict)
    tombstone_id = str(state["tombstone_id"])
    if tombstone_id in seen:
        return "invalid", None, (
            "subjective_mem_reformation_tombstone_state_duplicate",
        )
    tombstone = tx.read_record(
        record_kind="subjective_mem_forget_tombstone", record_id=tombstone_id
    )
    receipt = tx.read_record(
        record_kind="subjective_mem_lifecycle_receipt",
        record_id=str(state["receipt_id"]),
    )
    transition = tx.read_record(
        record_kind="subjective_mem_lifecycle_transition",
        record_id=str(state["transition_id"]),
    )
    if not _valid_lineage(
        state,
        tombstone,
        receipt,
        transition,
        evidence_space_id,
        character_id,
        semantic_identity_digest,
    ):
        return "invalid", None, (
            "subjective_mem_reformation_tombstone_lineage_invalid",
        )
    assert isinstance(tombstone, dict) and isinstance(receipt, dict)
    release_status, reasons = inspect_subjective_mem_forget_tombstone_release_locked(
        tx=tx,
        tombstone_state=state,
        tombstone=tombstone,
        forget_receipt=receipt,
        evidence_space_id=evidence_space_id,
        character_id=character_id,
        semantic_identity_digest=semantic_identity_digest,
    )
    return release_status, tombstone_id, reasons

def _valid_state(
    raw: object,
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> bool:
    return (
        isinstance(raw, dict)
        and set(raw) == _STATE_FIELDS
        and raw.get("schema") == FORGET_TOMBSTONE_STATE_SCHEMA
        and raw.get("evidence_space_id") == evidence_space_id
        and raw.get("character_id") == character_id
        and raw.get("semantic_identity_digest") == semantic_identity_digest
        and _token(raw.get("tombstone_id"))
        and _digest(raw.get("tombstone_digest"))
        and _token(raw.get("memory_id"))
        and type(raw.get("hidden_revision")) is int
        and int(raw["hidden_revision"]) >= 2
        and raw.get("formation_stage") in {"primary", "secondary"}
        and _token(raw.get("transition_id"))
        and _digest(raw.get("transition_digest"))
        and _token(raw.get("receipt_id"))
        and raw.get("effective") is True
        and raw.get("superseded_by_tombstone_id_or_null") is None
        and _timestamp(raw.get("updated_at"))
        and raw.get("content_free") is True
    )


def _valid_lineage(
    state: dict[str, object],
    tombstone: object,
    receipt: object,
    transition: object,
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> bool:
    if (
        not isinstance(tombstone, dict)
        or set(tombstone) != _TOMBSTONE_FIELDS
        or not isinstance(receipt, dict)
        or set(receipt) != _RECEIPT_FIELDS
        or not isinstance(transition, dict)
        or set(transition) != _TRANSITION_FIELDS
        or not _self_digest(tombstone, "tombstone_digest")
        or not _self_digest(receipt, "receipt_digest")
    ):
        return False
    source = tombstone.get("source_revision")
    hidden = tombstone.get("hidden_revision")
    at = tombstone.get("effective_at")
    stage = tombstone.get("formation_stage")
    auth = tombstone.get("authorization_class")
    auth_id = tombstone.get("authorization_id")
    reason = tombstone.get("reason_category")
    memory_ref = receipt.get("memory_ref")
    transition_digest = canonical_digest(transition)
    return (
        tombstone.get("schema") == FORGET_TOMBSTONE_SCHEMA
        and tombstone.get("tombstone_id") == state.get("tombstone_id")
        and tombstone.get("tombstone_digest") == state.get("tombstone_digest")
        and tombstone.get("evidence_space_id") == evidence_space_id
        and tombstone.get("character_id") == character_id
        and tombstone.get("semantic_identity_digest") == semantic_identity_digest
        and tombstone.get("memory_id") == state.get("memory_id")
        and hidden == state.get("hidden_revision")
        and stage == state.get("formation_stage")
        and tombstone.get("transition_id") == state.get("transition_id")
        and tombstone.get("transition_digest") == state.get("transition_digest")
        and tombstone.get("transition_digest") == transition_digest
        and tombstone.get("receipt_id") == state.get("receipt_id")
        and type(source) is int
        and type(hidden) is int
        and source >= 1
        and hidden == source + 1
        and stage in {"primary", "secondary"}
        and _digest(tombstone.get("scope_binding_digest"))
        and auth in {"user_management", "operator"}
        and _token(auth_id)
        and reason in FORGET_REASON_CATEGORIES
        and tombstone.get("policy_revision") == LIFECYCLE_POLICY_REVISION
        and _timestamp(at)
        and at == state.get("updated_at")
        and tombstone.get("effective") is True
        and tombstone.get("content_free") is True
        and receipt.get("schema") == LIFECYCLE_RECEIPT_SCHEMA
        and receipt.get("receipt_id") == tombstone.get("receipt_id")
        and receipt.get("operation_kind") == "forget"
        and receipt.get("operation_outcome") == "committed"
        and receipt.get("evidence_space_id") == evidence_space_id
        and receipt.get("character_id") == character_id
        and receipt.get("transition_id") == tombstone.get("transition_id")
        and receipt.get("transition_digest") == transition_digest
        and receipt.get("tombstone_id") == tombstone.get("tombstone_id")
        and receipt.get("tombstone_digest") == tombstone.get("tombstone_digest")
        and receipt.get("semantic_identity_digest") == semantic_identity_digest
        and receipt.get("predecessor_revision") == source
        and receipt.get("formation_stage") == stage
        and receipt.get("authorization_class") == auth
        and receipt.get("authorization_id") == auth_id
        and receipt.get("reason_category") == reason
        and receipt.get("policy_revision") == LIFECYCLE_POLICY_REVISION
        and receipt.get("projection_state") == "rebuild_required"
        and receipt.get("ordinary_retrieval_wired") is False
        and receipt.get("finalized_at") == at
        and isinstance(memory_ref, dict)
        and set(memory_ref) == {"memory_id", "memory_revision"}
        and memory_ref.get("memory_id") == tombstone.get("memory_id")
        and memory_ref.get("memory_revision") == hidden
        and transition.get("schema") == LIFECYCLE_TRANSITION_SCHEMA
        and transition.get("transition_id") == tombstone.get("transition_id")
        and transition.get("character_id") == character_id
        and transition.get("memory_id") == tombstone.get("memory_id")
        and transition.get("from_revision") == source
        and transition.get("to_revision") == hidden
        and transition.get("operation") == "forget"
        and transition.get("from_lifecycle_state") == "active"
        and transition.get("to_lifecycle_state") == "hidden"
        and transition.get("from_formation_stage") == stage
        and transition.get("to_formation_stage") == stage
        and transition.get("authorized_by") == auth
        and transition.get("committed_at") == at
    )


def _self_digest(raw: dict[str, object], field: str) -> bool:
    value = raw.get(field)
    return isinstance(value, str) and value == canonical_digest(
        {key: item for key, item in raw.items() if key != field}
    )


def _failure(
    reason: str, semantic_identity_digest: str | None = None
) -> SubjectiveMemReformationCheck:
    return SubjectiveMemReformationCheck(
        "fail_closed",
        semantic_identity_digest=semantic_identity_digest,
        blocked_reasons=(reason,),
    )


def _token(value: object, max_length: int = 256) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= max_length
        and _TOKEN_RE.fullmatch(value) is not None
    )


def _digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


__all__ = [
    "SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND",
    "SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND",
    "SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND",
    "SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA",
    "SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA",
    "SubjectiveMemReformationCheck",
    "check_subjective_mem_reformation",
    "check_subjective_mem_reformation_locked",
    "inspect_subjective_mem_reformation_digest_locked",
    "subjective_mem_semantic_identity_digest",
]
