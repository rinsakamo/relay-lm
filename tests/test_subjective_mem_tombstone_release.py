"""Focused LC-1D Forget-tombstone release evaluator tests."""
from __future__ import annotations

from datetime import timedelta

from relaylm.evidence_common import canonical_digest
from relaylm.subjective_mem_lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
)
from relaylm.subjective_mem_reformation import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA,
)
from test_subjective_mem_forget_runtime import (
    _forget,
    _reformation_pair,
    _semantic_identity,
)
from test_subjective_mem_lifecycle_runtime import lifecycle_env
from test_subjective_mem_runtime import NOW


def _release_payloads(env, predecessor, forgotten, *, released_at: str):
    space = env["captured"].evidence_space_id
    tombstone = env["store"].read_record(
        evidence_space_id=space,
        record_kind="subjective_mem_forget_tombstone",
        record_id=forgotten.tombstone_id,
    )
    assert isinstance(tombstone, dict)
    forget_receipt = env["store"].read_record(
        evidence_space_id=space,
        record_kind="subjective_mem_lifecycle_receipt",
        record_id=str(tombstone["receipt_id"]),
    )
    assert isinstance(forget_receipt, dict)
    semantic_id = _semantic_identity(env, predecessor)
    transition, receipt = _restore_lineage(
        space=space,
        predecessor=predecessor,
        forgotten=forgotten,
        tombstone=tombstone,
        semantic_id=semantic_id,
        released_at=released_at,
    )
    release, state = _release_authority(
        space=space,
        predecessor=predecessor,
        forgotten=forgotten,
        tombstone=tombstone,
        forget_receipt=forget_receipt,
        transition=transition,
        restore_receipt=receipt,
        semantic_id=semantic_id,
        released_at=released_at,
    )
    return transition, receipt, release, state


def _restore_lineage(
    *, space, predecessor, forgotten, tombstone, semantic_id: str, released_at: str
):
    hidden = int(tombstone["hidden_revision"])
    restored = hidden + 1
    transition_id = "smrestoretransition-test-1"
    release_id = "smrestorerelease-test-1"
    receipt_id = "smrestorereceipt-test-1"
    transition = {
        "schema": LIFECYCLE_TRANSITION_SCHEMA,
        "transition_id": transition_id,
        "character_id": predecessor.character_id,
        "memory_id": predecessor.memory_id,
        "from_revision": hidden,
        "to_revision": restored,
        "operation": "restore",
        "from_lifecycle_state": "hidden",
        "to_lifecycle_state": "active",
        "from_formation_stage": predecessor.formation_stage,
        "to_formation_stage": predecessor.formation_stage,
        "authorized_by": "user_management",
        "committed_at": released_at,
    }
    receipt_body = {
        "schema": LIFECYCLE_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "operation_kind": "restore",
        "operation_outcome": "committed",
        "evidence_space_id": space,
        "character_id": predecessor.character_id,
        "memory_ref": {"memory_id": predecessor.memory_id, "memory_revision": restored},
        "predecessor_revision": hidden,
        "transition_id": transition_id,
        "release_id": release_id,
        "tombstone_id": forgotten.tombstone_id,
        "tombstone_digest": tombstone["tombstone_digest"],
        "semantic_identity_digest": semantic_id,
        "authorization_class": "user_management",
        "authorization_id": "user-restore-authorization-1",
        "reason_category": "user_requested_restore",
        "policy_revision": LIFECYCLE_POLICY_REVISION,
        "projection_state": "rebuild_required",
        "ordinary_retrieval_wired": False,
        "finalized_at": released_at,
    }
    return transition, {**receipt_body, "receipt_digest": canonical_digest(receipt_body)}


def _release_authority(
    *,
    space,
    predecessor,
    forgotten,
    tombstone,
    forget_receipt,
    transition,
    restore_receipt,
    semantic_id: str,
    released_at: str,
):
    hidden = int(tombstone["hidden_revision"])
    restored = hidden + 1
    transition_digest = canonical_digest(transition)
    release_body = {
        "schema": SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA,
        "release_id": restore_receipt["release_id"],
        "evidence_space_id": space,
        "character_id": predecessor.character_id,
        "semantic_identity_digest": semantic_id,
        "memory_id": predecessor.memory_id,
        "hidden_revision": hidden,
        "restored_revision": restored,
        "tombstone_id": forgotten.tombstone_id,
        "tombstone_digest": tombstone["tombstone_digest"],
        "forget_transition_id": tombstone["transition_id"],
        "forget_transition_digest": tombstone["transition_digest"],
        "forget_receipt_id": tombstone["receipt_id"],
        "forget_receipt_digest": forget_receipt["receipt_digest"],
        "restore_transition_id": transition["transition_id"],
        "restore_transition_digest": transition_digest,
        "restore_receipt_id": restore_receipt["receipt_id"],
        "restore_receipt_digest": restore_receipt["receipt_digest"],
        "authorization_class": "user_management",
        "authorization_id": "user-restore-authorization-1",
        "reason_category": "user_requested_restore",
        "policy_revision": LIFECYCLE_POLICY_REVISION,
        "released_at": released_at,
        "content_free": True,
    }
    release = {**release_body, "release_digest": canonical_digest(release_body)}
    state = {
        "schema": SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA,
        "tombstone_id": forgotten.tombstone_id,
        "tombstone_digest": tombstone["tombstone_digest"],
        "release_id": release["release_id"],
        "release_digest": release["release_digest"],
        "evidence_space_id": space,
        "character_id": predecessor.character_id,
        "semantic_identity_digest": semantic_id,
        "memory_id": predecessor.memory_id,
        "hidden_revision": hidden,
        "restored_revision": restored,
        "restore_transition_id": transition["transition_id"],
        "restore_transition_digest": transition_digest,
        "restore_receipt_id": restore_receipt["receipt_id"],
        "restore_receipt_digest": restore_receipt["receipt_digest"],
        "effective": True,
        "updated_at": released_at,
        "content_free": True,
    }
    return release, state

def _commit_release(
    env,
    forgotten,
    transition,
    receipt,
    release,
    state,
    *,
    include_release: bool = True,
    events=None,
    key: str | None = None,
) -> None:
    space = env["captured"].evidence_space_id
    records = [
        ("subjective_mem_lifecycle_transition", transition["transition_id"], transition),
        ("subjective_mem_lifecycle_receipt", receipt["receipt_id"], receipt),
    ]
    if include_release:
        records.append(
            (
                SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND,
                release["release_id"],
                release,
            )
        )
    with env["store"].transaction(space) as tx:
        result = tx.commit(
            transaction_id="smrestore-release-test-tx",
            records=tuple(records),
            logs=((
                SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
                key or forgotten.tombstone_id,
                tuple(events if events is not None else (state,)),
            ),),
        )
    assert result.status == "created"


def test_exact_release_allows_reformation(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    assert forgotten.status == "committed"
    payloads = _release_payloads(
        lifecycle_env,
        predecessor,
        forgotten,
        released_at=(NOW + timedelta(seconds=4)).isoformat(),
    )
    _commit_release(lifecycle_env, forgotten, *payloads)

    public, locked = _reformation_pair(lifecycle_env, predecessor)
    assert public == locked
    assert public.status == "allowed", public.blocked_reasons
    assert public.tombstone_ids == ()


def test_duplicate_release_state_fails_closed(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    payloads = _release_payloads(
        lifecycle_env,
        predecessor,
        forgotten,
        released_at=(NOW + timedelta(seconds=4)).isoformat(),
    )
    transition, receipt, release, state = payloads
    _commit_release(
        lifecycle_env,
        forgotten,
        transition,
        receipt,
        release,
        state,
        events=(state, state),
    )
    result, locked = _reformation_pair(lifecycle_env, predecessor)
    assert result == locked
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_reformation_tombstone_release_state_duplicate"
        in result.blocked_reasons
    )


def test_dangling_release_record_fails_closed(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    payloads = _release_payloads(
        lifecycle_env,
        predecessor,
        forgotten,
        released_at=(NOW + timedelta(seconds=4)).isoformat(),
    )
    _commit_release(lifecycle_env, forgotten, *payloads, include_release=False)
    result, locked = _reformation_pair(lifecycle_env, predecessor)
    assert result == locked
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_reformation_tombstone_release_lineage_invalid"
        in result.blocked_reasons
    )


def test_release_digest_mismatch_fails_closed(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    transition, receipt, release, state = _release_payloads(
        lifecycle_env,
        predecessor,
        forgotten,
        released_at=(NOW + timedelta(seconds=4)).isoformat(),
    )
    release = {**release, "authorization_id": "tampered-authorization"}
    _commit_release(lifecycle_env, forgotten, transition, receipt, release, state)
    result, locked = _reformation_pair(lifecycle_env, predecessor)
    assert result == locked
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_reformation_tombstone_release_lineage_invalid"
        in result.blocked_reasons
    )


def test_non_monotonic_release_fails_closed(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    tombstone = lifecycle_env["store"].read_record(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        record_kind="subjective_mem_forget_tombstone",
        record_id=forgotten.tombstone_id,
    )
    assert isinstance(tombstone, dict)
    payloads = _release_payloads(
        lifecycle_env,
        predecessor,
        forgotten,
        released_at=str(tombstone["effective_at"]),
    )
    _commit_release(lifecycle_env, forgotten, *payloads)
    result, locked = _reformation_pair(lifecycle_env, predecessor)
    assert result == locked
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_reformation_tombstone_release_non_monotonic"
        in result.blocked_reasons
    )
