"""Negative lineage coverage for LC-1D Forget-tombstone releases."""
from __future__ import annotations

from datetime import timedelta

from relaylm.evidence.common import canonical_digest
from relaylm.subjective_mem_reformation import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND,
)
from test_subjective_mem_forget_runtime import _forget, _reformation_pair
from test_subjective_mem_lifecycle_runtime import lifecycle_env
from test_subjective_mem_runtime import NOW
from test_subjective_mem_tombstone_release import _release_payloads


def _commit(env, forgotten, transition, receipt, release, state, *, receipt_key=None):
    space = env["captured"].evidence_space_id
    with env["store"].transaction(space) as tx:
        result = tx.commit(
            transaction_id="smrestore-release-lineage-negative-tx",
            records=(
                (
                    "subjective_mem_lifecycle_transition",
                    transition["transition_id"],
                    transition,
                ),
                (
                    "subjective_mem_lifecycle_receipt",
                    receipt_key or receipt["receipt_id"],
                    receipt,
                ),
                (
                    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND,
                    release["release_id"],
                    release,
                ),
            ),
            logs=((
                SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
                forgotten.tombstone_id,
                (state,),
            ),),
        )
    assert result.status == "created"


def _assert_lineage_invalid(env, predecessor) -> None:
    public, locked = _reformation_pair(env, predecessor)
    assert public == locked
    assert public.status == "fail_closed"
    assert (
        "subjective_mem_reformation_tombstone_release_lineage_invalid"
        in public.blocked_reasons
    )


def test_restore_transition_body_digest_must_match_release(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    transition, receipt, release, state = _release_payloads(
        lifecycle_env,
        predecessor,
        forgotten,
        released_at=(NOW + timedelta(seconds=4)).isoformat(),
    )
    transition = {**transition, "committed_at": (NOW + timedelta(seconds=5)).isoformat()}
    _commit(lifecycle_env, forgotten, transition, receipt, release, state)
    _assert_lineage_invalid(lifecycle_env, predecessor)


def test_restore_receipt_body_id_must_match_release_binding(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    transition, receipt, release, state = _release_payloads(
        lifecycle_env,
        predecessor,
        forgotten,
        released_at=(NOW + timedelta(seconds=4)).isoformat(),
    )
    bound_id = str(release["restore_receipt_id"])
    receipt_body = {
        **{key: value for key, value in receipt.items() if key != "receipt_digest"},
        "receipt_id": "smrestorereceipt-cross-linked",
    }
    receipt = {**receipt_body, "receipt_digest": canonical_digest(receipt_body)}
    release_body = {
        **{key: value for key, value in release.items() if key != "release_digest"},
        "restore_receipt_digest": receipt["receipt_digest"],
    }
    release = {**release_body, "release_digest": canonical_digest(release_body)}
    state = {
        **state,
        "release_digest": release["release_digest"],
        "restore_receipt_digest": receipt["receipt_digest"],
    }
    _commit(
        lifecycle_env,
        forgotten,
        transition,
        receipt,
        release,
        state,
        receipt_key=bound_id,
    )
    _assert_lineage_invalid(lifecycle_env, predecessor)


def test_restore_authorization_and_reason_must_be_a_valid_pair(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    transition, receipt, release, state = _release_payloads(
        lifecycle_env,
        predecessor,
        forgotten,
        released_at=(NOW + timedelta(seconds=4)).isoformat(),
    )
    transition = {**transition, "authorized_by": "operator_management"}
    transition_digest = canonical_digest(transition)
    receipt_body = {
        **{key: value for key, value in receipt.items() if key != "receipt_digest"},
        "authorization_class": "operator_management",
    }
    receipt = {**receipt_body, "receipt_digest": canonical_digest(receipt_body)}
    release_body = {
        **{key: value for key, value in release.items() if key != "release_digest"},
        "authorization_class": "operator_management",
        "restore_transition_digest": transition_digest,
        "restore_receipt_digest": receipt["receipt_digest"],
    }
    release = {**release_body, "release_digest": canonical_digest(release_body)}
    state = {
        **state,
        "release_digest": release["release_digest"],
        "restore_transition_digest": transition_digest,
        "restore_receipt_digest": receipt["receipt_digest"],
    }
    _commit(lifecycle_env, forgotten, transition, receipt, release, state)
    _assert_lineage_invalid(lifecycle_env, predecessor)
