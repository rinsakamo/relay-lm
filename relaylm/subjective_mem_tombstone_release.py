"""Immutable Forget-tombstone release schema and exact lineage validation.

This module validates the optional content-free release for one already-valid
Forget tombstone. It does not decide whether semantic re-formation is allowed;
the canonical reformation evaluator remains the sole decision owner.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from relaylm.evidence.common import canonical_digest
from relaylm.evidence.store import EvidenceStoreTransaction
from relaylm.subjective_mem_lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
)
from relaylm.subjective_mem_restore import (
    RESTORE_AUTHORIZATION_CLASSES,
    RESTORE_REASON_CATEGORIES,
)

ReleaseInspection = Literal["released", "unreleased", "invalid"]
SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA = (
    "relaylm.subjective_mem_forget_tombstone_release.v1"
)
SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA = (
    "relaylm.subjective_mem_forget_tombstone_release_state.v1"
)
SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND = (
    "subjective_mem_forget_tombstone_release"
)
SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND = (
    "subjective_mem_forget_tombstone_release_state"
)

_TRANSITION_FIELDS = frozenset(
    "schema transition_id character_id memory_id from_revision to_revision operation "
    "from_lifecycle_state to_lifecycle_state from_formation_stage "
    "to_formation_stage authorized_by committed_at".split()
)
_RELEASE_STATE_FIELDS = frozenset(
    "schema tombstone_id tombstone_digest release_id release_digest "
    "evidence_space_id character_id semantic_identity_digest memory_id "
    "hidden_revision restored_revision restore_transition_id "
    "restore_transition_digest restore_receipt_id restore_receipt_digest "
    "effective updated_at content_free".split()
)
_RELEASE_FIELDS = frozenset(
    "schema release_id release_digest evidence_space_id character_id "
    "semantic_identity_digest memory_id hidden_revision restored_revision "
    "tombstone_id tombstone_digest forget_transition_id forget_transition_digest "
    "forget_receipt_id forget_receipt_digest restore_transition_id "
    "restore_transition_digest restore_receipt_id restore_receipt_digest "
    "authorization_class authorization_id reason_category policy_revision "
    "released_at content_free".split()
)
_RESTORE_RECEIPT_REQUIRED = frozenset(
    "schema receipt_id operation_kind operation_outcome evidence_space_id character_id "
    "memory_ref predecessor_revision transition_id release_id tombstone_id "
    "tombstone_digest semantic_identity_digest authorization_class authorization_id "
    "reason_category policy_revision projection_state ordinary_retrieval_wired "
    "finalized_at receipt_digest".split()
)


@dataclass(frozen=True)
class SubjectiveMemForgetTombstoneReleaseAuthority:
    release: dict[str, object]
    state: dict[str, object]


def build_subjective_mem_forget_tombstone_release_authority(
    *,
    release_id: str,
    tombstone: dict[str, object],
    forget_receipt: dict[str, object],
    restore_transition: dict[str, object],
    restore_receipt: dict[str, object],
    authorization_class: str,
    authorization_id: str,
    reason_category: str,
    policy_revision: str,
    released_at: str,
) -> tuple[
    SubjectiveMemForgetTombstoneReleaseAuthority | None,
    tuple[str, ...],
]:
    """Build the exact content-free release pair for one immutable Forget tombstone."""

    reasons = _build_inputs_invalid(
        release_id=release_id,
        tombstone=tombstone,
        forget_receipt=forget_receipt,
        restore_transition=restore_transition,
        restore_receipt=restore_receipt,
        authorization_id=authorization_id,
        released_at=released_at,
    )
    if reasons:
        return None, reasons
    if not _authorization_reason_exact(authorization_class, reason_category):
        return None, (
            "subjective_mem_restore_tombstone_release_authorization_unsupported",
        )
    if policy_revision != LIFECYCLE_POLICY_REVISION:
        return None, (
            "subjective_mem_restore_tombstone_release_policy_unsupported",
        )
    if restore_receipt.get("release_id") != release_id:
        return None, ("subjective_mem_restore_tombstone_release_id_mismatch",)
    if not _strictly_after(released_at, str(tombstone.get("effective_at"))):
        return None, ("subjective_mem_restore_tombstone_release_non_monotonic",)

    hidden = tombstone["hidden_revision"]
    release = _compose_release(
        release_id=release_id,
        tombstone=tombstone,
        forget_receipt=forget_receipt,
        restore_transition=restore_transition,
        restore_receipt=restore_receipt,
        hidden=int(hidden),
        authorization_class=authorization_class,
        authorization_id=authorization_id,
        reason_category=reason_category,
        released_at=released_at,
    )
    state = _compose_release_state(
        release=release,
        tombstone=tombstone,
        released_at=released_at,
    )
    if not _composed_pair_exact(
        release=release,
        state=state,
        tombstone=tombstone,
        forget_receipt=forget_receipt,
        restore_transition=restore_transition,
        restore_receipt=restore_receipt,
    ):
        return None, ("subjective_mem_restore_tombstone_release_lineage_invalid",)
    return SubjectiveMemForgetTombstoneReleaseAuthority(release=release, state=state), ()


def _composed_pair_exact(
    *, release: dict[str, object], state: dict[str, object],
    tombstone: dict[str, object], forget_receipt: dict[str, object],
    restore_transition: dict[str, object], restore_receipt: dict[str, object],
) -> bool:
    """Prove the composed pair with the predicates the release evaluator uses."""

    space = str(tombstone["evidence_space_id"])
    character = str(tombstone["character_id"])
    semantic = str(tombstone["semantic_identity_digest"])
    return _valid_release_state(
        state,
        tombstone_state=tombstone,
        evidence_space_id=space,
        character_id=character,
        semantic_identity_digest=semantic,
    ) and _valid_release_lineage(
        release_state=state,
        release=release,
        tombstone=tombstone,
        forget_receipt=forget_receipt,
        restore_transition=restore_transition,
        restore_receipt=restore_receipt,
        evidence_space_id=space,
        character_id=character,
        semantic_identity_digest=semantic,
    )


def _build_inputs_invalid(
    *, release_id: object, tombstone: object, forget_receipt: object,
    restore_transition: object, restore_receipt: object,
    authorization_id: object, released_at: object,
) -> tuple[str, ...]:
    if (
        not _token(release_id)
        or not _token(authorization_id)
        or not _timestamp(released_at)
        or not isinstance(tombstone, dict)
        or not isinstance(forget_receipt, dict)
        or not isinstance(restore_transition, dict)
        or not isinstance(restore_receipt, dict)
        or type(tombstone.get("hidden_revision")) is not int
        or not _token(tombstone.get("tombstone_id"))
        or not _token(tombstone.get("memory_id"))
        or not _token(tombstone.get("evidence_space_id"))
        or not _token(tombstone.get("character_id"))
        or not _digest(tombstone.get("semantic_identity_digest"))
        or not _timestamp(tombstone.get("effective_at"))
    ):
        return ("subjective_mem_restore_tombstone_release_input_invalid",)
    if (
        not _self_digest(tombstone, "tombstone_digest")
        or not _self_digest(forget_receipt, "receipt_digest")
        or not _self_digest(restore_receipt, "receipt_digest")
    ):
        return ("subjective_mem_restore_tombstone_release_input_not_authentic",)
    return ()


def _compose_release(
    *, release_id: str, tombstone: dict[str, object],
    forget_receipt: dict[str, object], restore_transition: dict[str, object],
    restore_receipt: dict[str, object], hidden: int, authorization_class: str,
    authorization_id: str, reason_category: str, released_at: str,
) -> dict[str, object]:
    body = {
        "schema": SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA,
        "release_id": release_id,
        "evidence_space_id": tombstone["evidence_space_id"],
        "character_id": tombstone["character_id"],
        "semantic_identity_digest": tombstone["semantic_identity_digest"],
        "memory_id": tombstone["memory_id"],
        "hidden_revision": hidden,
        "restored_revision": hidden + 1,
        "tombstone_id": tombstone["tombstone_id"],
        "tombstone_digest": tombstone["tombstone_digest"],
        "forget_transition_id": tombstone["transition_id"],
        "forget_transition_digest": tombstone["transition_digest"],
        "forget_receipt_id": tombstone["receipt_id"],
        "forget_receipt_digest": forget_receipt["receipt_digest"],
        "restore_transition_id": restore_transition.get("transition_id"),
        "restore_transition_digest": canonical_digest(restore_transition),
        "restore_receipt_id": restore_receipt["receipt_id"],
        "restore_receipt_digest": restore_receipt["receipt_digest"],
        "authorization_class": authorization_class,
        "authorization_id": authorization_id,
        "reason_category": reason_category,
        "policy_revision": LIFECYCLE_POLICY_REVISION,
        "released_at": released_at,
        "content_free": True,
    }
    return {**body, "release_digest": canonical_digest(body)}


def _compose_release_state(
    *, release: dict[str, object], tombstone: dict[str, object], released_at: str,
) -> dict[str, object]:
    return {
        "schema": SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA,
        "tombstone_id": tombstone["tombstone_id"],
        "tombstone_digest": tombstone["tombstone_digest"],
        "release_id": release["release_id"],
        "release_digest": release["release_digest"],
        "evidence_space_id": tombstone["evidence_space_id"],
        "character_id": tombstone["character_id"],
        "semantic_identity_digest": tombstone["semantic_identity_digest"],
        "memory_id": tombstone["memory_id"],
        "hidden_revision": release["hidden_revision"],
        "restored_revision": release["restored_revision"],
        "restore_transition_id": release["restore_transition_id"],
        "restore_transition_digest": release["restore_transition_digest"],
        "restore_receipt_id": release["restore_receipt_id"],
        "restore_receipt_digest": release["restore_receipt_digest"],
        "effective": True,
        "updated_at": released_at,
        "content_free": True,
    }


def inspect_subjective_mem_forget_tombstone_release_locked(
    *,
    tx: EvidenceStoreTransaction,
    tombstone_state: dict[str, object],
    tombstone: dict[str, object],
    forget_receipt: dict[str, object],
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> tuple[ReleaseInspection, tuple[str, ...]]:
    """Inspect the optional exact release for one valid Forget tombstone."""

    if type(tx) is not EvidenceStoreTransaction or tx.evidence_space_id != evidence_space_id:
        return "invalid", ("subjective_mem_reformation_transaction_invalid",)
    release_state, reasons = _read_release_state(
        tx=tx,
        tombstone_id=tombstone_state.get("tombstone_id"),
    )
    if reasons:
        return "invalid", reasons
    if release_state is None:
        return "unreleased", ()
    if not _valid_release_state(
        release_state,
        tombstone_state=tombstone_state,
        evidence_space_id=evidence_space_id,
        character_id=character_id,
        semantic_identity_digest=semantic_identity_digest,
    ):
        return "invalid", (
            "subjective_mem_reformation_tombstone_release_state_corrupt",
        )

    release = tx.read_record(
        record_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND,
        record_id=str(release_state["release_id"]),
    )
    restore_transition = tx.read_record(
        record_kind="subjective_mem_lifecycle_transition",
        record_id=str(release_state["restore_transition_id"]),
    )
    restore_receipt = tx.read_record(
        record_kind="subjective_mem_lifecycle_receipt",
        record_id=str(release_state["restore_receipt_id"]),
    )
    if not _valid_release_lineage(
        release_state=release_state,
        release=release,
        tombstone=tombstone,
        forget_receipt=forget_receipt,
        restore_transition=restore_transition,
        restore_receipt=restore_receipt,
        evidence_space_id=evidence_space_id,
        character_id=character_id,
        semantic_identity_digest=semantic_identity_digest,
    ):
        return "invalid", (
            "subjective_mem_reformation_tombstone_release_lineage_invalid",
        )
    if not _strictly_after(
        str(release_state["updated_at"]),
        str(tombstone["effective_at"]),
    ):
        return "invalid", (
            "subjective_mem_reformation_tombstone_release_non_monotonic",
        )
    return "released", ()


def _read_release_state(
    *,
    tx: EvidenceStoreTransaction,
    tombstone_id: object,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if not _token(tombstone_id):
        return None, (
            "subjective_mem_reformation_tombstone_release_state_corrupt",
        )
    inventory = tx.list_logs(
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        limit=4096,
    )
    matches = [
        (key, bodies)
        for key, bodies in inventory
        if key == tombstone_id
        or any(body.get("tombstone_id") == tombstone_id for body in bodies)
    ]
    if not matches:
        return None, ()
    if len(matches) != 1:
        return None, (
            "subjective_mem_reformation_tombstone_release_state_duplicate",
        )
    key, bodies = matches[0]
    if key != tombstone_id:
        return None, (
            "subjective_mem_reformation_tombstone_release_state_corrupt",
        )
    if len(bodies) != 1:
        return None, (
            "subjective_mem_reformation_tombstone_release_state_duplicate",
        )
    return bodies[0], ()


def _valid_release_state(
    raw: object,
    *,
    tombstone_state: dict[str, object],
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> bool:
    if not isinstance(raw, dict):
        return False
    hidden = raw.get("hidden_revision")
    restored = raw.get("restored_revision")
    return (
        set(raw) == _RELEASE_STATE_FIELDS
        and raw.get("schema") == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA
        and raw.get("tombstone_id") == tombstone_state.get("tombstone_id")
        and raw.get("tombstone_digest") == tombstone_state.get("tombstone_digest")
        and raw.get("evidence_space_id") == evidence_space_id
        and raw.get("character_id") == character_id
        and raw.get("semantic_identity_digest") == semantic_identity_digest
        and raw.get("memory_id") == tombstone_state.get("memory_id")
        and hidden == tombstone_state.get("hidden_revision")
        and type(hidden) is int
        and type(restored) is int
        and restored == hidden + 1
        and _token(raw.get("release_id"))
        and _digest(raw.get("release_digest"))
        and _token(raw.get("restore_transition_id"))
        and _digest(raw.get("restore_transition_digest"))
        and _token(raw.get("restore_receipt_id"))
        and _digest(raw.get("restore_receipt_digest"))
        and raw.get("effective") is True
        and _timestamp(raw.get("updated_at"))
        and raw.get("content_free") is True
    )


def _valid_release_lineage(
    *,
    release_state: dict[str, object],
    release: object,
    tombstone: dict[str, object],
    forget_receipt: dict[str, object],
    restore_transition: object,
    restore_receipt: object,
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> bool:
    if (
        not isinstance(release, dict)
        or set(release) != _RELEASE_FIELDS
        or not isinstance(restore_transition, dict)
        or set(restore_transition) != _TRANSITION_FIELDS
        or not isinstance(restore_receipt, dict)
        or not _RESTORE_RECEIPT_REQUIRED.issubset(restore_receipt)
        or not _self_digest(release, "release_digest")
        or not _self_digest(forget_receipt, "receipt_digest")
        or not _self_digest(restore_receipt, "receipt_digest")
    ):
        return False
    hidden = release.get("hidden_revision")
    restored = release.get("restored_revision")
    if type(hidden) is not int or type(restored) is not int:
        return False
    transition_digest = canonical_digest(restore_transition)
    return (
        _release_record_exact(
            release=release,
            release_state=release_state,
            tombstone=tombstone,
            forget_receipt=forget_receipt,
            evidence_space_id=evidence_space_id,
            character_id=character_id,
            semantic_identity_digest=semantic_identity_digest,
        )
        and release.get("restore_transition_digest") == transition_digest
        and release_state.get("restore_transition_digest") == transition_digest
        and _restore_receipt_exact(
            receipt=restore_receipt,
            release=release,
            release_state=release_state,
            tombstone=tombstone,
            evidence_space_id=evidence_space_id,
            character_id=character_id,
            semantic_identity_digest=semantic_identity_digest,
        )
        and _transition_exact(
            restore_transition,
            transition_id=str(release["restore_transition_id"]),
            character_id=character_id,
            memory_id=str(release["memory_id"]),
            from_revision=hidden,
            to_revision=restored,
            formation_stage=str(tombstone.get("formation_stage")),
            authorized_by=str(release["authorization_class"]),
            committed_at=str(release["released_at"]),
        )
    )


def _release_record_exact(
    *,
    release: dict[str, object],
    release_state: dict[str, object],
    tombstone: dict[str, object],
    forget_receipt: dict[str, object],
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> bool:
    hidden = release.get("hidden_revision")
    restored = release.get("restored_revision")
    return (
        release.get("schema") == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA
        and release.get("release_id") == release_state.get("release_id")
        and release.get("release_digest") == release_state.get("release_digest")
        and release.get("evidence_space_id") == evidence_space_id
        and release.get("character_id") == character_id
        and release.get("semantic_identity_digest") == semantic_identity_digest
        and release.get("memory_id") == tombstone.get("memory_id")
        and release.get("memory_id") == release_state.get("memory_id")
        and hidden == tombstone.get("hidden_revision")
        and hidden == release_state.get("hidden_revision")
        and type(hidden) is int
        and type(restored) is int
        and restored == hidden + 1
        and restored == release_state.get("restored_revision")
        and release.get("tombstone_id") == tombstone.get("tombstone_id")
        and release.get("tombstone_digest") == tombstone.get("tombstone_digest")
        and release.get("forget_transition_id") == tombstone.get("transition_id")
        and release.get("forget_transition_digest") == tombstone.get("transition_digest")
        and release.get("forget_receipt_id") == tombstone.get("receipt_id")
        and release.get("forget_receipt_id") == forget_receipt.get("receipt_id")
        and release.get("forget_receipt_digest") == forget_receipt.get("receipt_digest")
        and release.get("restore_transition_id") == release_state.get("restore_transition_id")
        and release.get("restore_receipt_id") == release_state.get("restore_receipt_id")
        and release.get("restore_receipt_digest") == release_state.get("restore_receipt_digest")
        and _authorization_reason_exact(
            release.get("authorization_class"),
            release.get("reason_category"),
        )
        and _token(release.get("authorization_id"))
        and release.get("policy_revision") == LIFECYCLE_POLICY_REVISION
        and _timestamp(release.get("released_at"))
        and release.get("released_at") == release_state.get("updated_at")
        and release.get("content_free") is True
    )


def _restore_receipt_exact(
    *,
    receipt: dict[str, object],
    release: dict[str, object],
    release_state: dict[str, object],
    tombstone: dict[str, object],
    evidence_space_id: str,
    character_id: str,
    semantic_identity_digest: str,
) -> bool:
    hidden = release.get("hidden_revision")
    restored = release.get("restored_revision")
    if type(hidden) is not int or type(restored) is not int:
        return False
    return (
        receipt.get("receipt_id") == release.get("restore_receipt_id")
        and receipt.get("receipt_id") == release_state.get("restore_receipt_id")
        and receipt.get("receipt_digest") == release.get("restore_receipt_digest")
        and receipt.get("receipt_digest") == release_state.get("restore_receipt_digest")
        and receipt.get("release_id") == release.get("release_id")
        and receipt.get("tombstone_id") == tombstone.get("tombstone_id")
        and receipt.get("tombstone_digest") == tombstone.get("tombstone_digest")
        and receipt.get("semantic_identity_digest") == semantic_identity_digest
        and _receipt_common(
            receipt,
            evidence_space_id=evidence_space_id,
            character_id=character_id,
            memory_id=str(release["memory_id"]),
            predecessor_revision=hidden,
            restored_revision=restored,
            transition_id=str(release["restore_transition_id"]),
            authorization_class=str(release["authorization_class"]),
            authorization_id=str(release["authorization_id"]),
            reason_category=str(release["reason_category"]),
            finalized_at=str(release["released_at"]),
        )
    )


def _receipt_common(
    raw: dict[str, object],
    *,
    evidence_space_id: str,
    character_id: str,
    memory_id: str,
    predecessor_revision: int,
    restored_revision: int,
    transition_id: str,
    authorization_class: str,
    authorization_id: str,
    reason_category: str,
    finalized_at: str,
) -> bool:
    memory_ref = raw.get("memory_ref")
    return (
        raw.get("schema") == LIFECYCLE_RECEIPT_SCHEMA
        and raw.get("operation_kind") == "restore"
        and raw.get("operation_outcome") == "committed"
        and raw.get("evidence_space_id") == evidence_space_id
        and raw.get("character_id") == character_id
        and raw.get("predecessor_revision") == predecessor_revision
        and raw.get("transition_id") == transition_id
        and raw.get("authorization_class") == authorization_class
        and raw.get("authorization_id") == authorization_id
        and raw.get("reason_category") == reason_category
        and raw.get("policy_revision") == LIFECYCLE_POLICY_REVISION
        and raw.get("projection_state") == "rebuild_required"
        and raw.get("ordinary_retrieval_wired") is False
        and raw.get("finalized_at") == finalized_at
        and isinstance(memory_ref, dict)
        and set(memory_ref) == {"memory_id", "memory_revision"}
        and memory_ref.get("memory_id") == memory_id
        and memory_ref.get("memory_revision") == restored_revision
    )


def _transition_exact(
    raw: dict[str, object],
    *,
    transition_id: str,
    character_id: str,
    memory_id: str,
    from_revision: int,
    to_revision: int,
    formation_stage: str,
    authorized_by: str,
    committed_at: str,
) -> bool:
    return (
        raw.get("schema") == LIFECYCLE_TRANSITION_SCHEMA
        and raw.get("transition_id") == transition_id
        and raw.get("character_id") == character_id
        and raw.get("memory_id") == memory_id
        and raw.get("from_revision") == from_revision
        and raw.get("to_revision") == to_revision
        and raw.get("operation") == "restore"
        and raw.get("from_lifecycle_state") == "hidden"
        and raw.get("to_lifecycle_state") == "active"
        and raw.get("from_formation_stage") == formation_stage
        and raw.get("to_formation_stage") == formation_stage
        and raw.get("authorized_by") == authorized_by
        and raw.get("committed_at") == committed_at
    )


def _authorization_reason_exact(authorization: object, reason: object) -> bool:
    if authorization not in RESTORE_AUTHORIZATION_CLASSES:
        return False
    if reason not in RESTORE_REASON_CATEGORIES:
        return False
    return (
        (authorization == "user_management" and reason == "user_requested_restore")
        or (
            authorization == "operator_management"
            and reason == "operator_requested_restore"
        )
    )


def _self_digest(raw: dict[str, object], field: str) -> bool:
    digest = raw.get(field)
    return isinstance(digest, str) and digest == canonical_digest(
        {key: value for key, value in raw.items() if key != field}
    )


def _token(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 256
        and value not in {".", ".."}
        and all(ch not in value for ch in ("/", "\\", "\x00"))
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


def _strictly_after(candidate: str, earlier: str) -> bool:
    try:
        later = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        before = datetime.fromisoformat(earlier.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return later.tzinfo is not None and before.tzinfo is not None and later > before


__all__ = [
    "SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND",
    "SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND",
    "SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA",
    "SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA",
    "SubjectiveMemForgetTombstoneReleaseAuthority",
    "build_subjective_mem_forget_tombstone_release_authority",
    "inspect_subjective_mem_forget_tombstone_release_locked",
]
