"""Focused LC-1D Forget-tombstone release evaluator tests."""
from __future__ import annotations

from datetime import timedelta

from relaylm.evidence.common import canonical_digest
from relaylm.subjective_mem.lifecycle import (
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
from relaylm.subjective_mem_tombstone_release import (
    build_subjective_mem_forget_tombstone_release_authority,
)
from test_subjective_mem_forget_runtime import (
    _forget,
    _reformation_pair,
    _semantic_identity,
)
from test_subjective_mem_lifecycle_runtime import lifecycle_env
from test_subjective_mem_runtime import NOW


AUTHORIZATION_CLASS = "user_management"
AUTHORIZATION_ID = "user-restore-authorization-1"
REASON_CATEGORY = "user_requested_restore"


def _release_inputs(env, predecessor, forgotten):
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
    return space, tombstone, forget_receipt, _semantic_identity(env, predecessor)


def _build(tombstone, forget_receipt, transition, receipt, *, released_at: str, **changes):
    arguments = {
        "release_id": receipt["release_id"],
        "tombstone": tombstone,
        "forget_receipt": forget_receipt,
        "restore_transition": transition,
        "restore_receipt": receipt,
        "authorization_class": AUTHORIZATION_CLASS,
        "authorization_id": AUTHORIZATION_ID,
        "reason_category": REASON_CATEGORY,
        "policy_revision": LIFECYCLE_POLICY_REVISION,
        "released_at": released_at,
    }
    return build_subjective_mem_forget_tombstone_release_authority(
        **{**arguments, **changes}
    )


def _release_payloads(env, predecessor, forgotten, *, released_at: str):
    space, tombstone, forget_receipt, semantic_id = _release_inputs(
        env, predecessor, forgotten
    )
    transition, receipt = _restore_lineage(
        space=space,
        predecessor=predecessor,
        forgotten=forgotten,
        tombstone=tombstone,
        semantic_id=semantic_id,
        released_at=released_at,
    )
    authority, reasons = _build(
        tombstone, forget_receipt, transition, receipt, released_at=released_at
    )
    assert authority is not None, reasons
    return transition, receipt, authority.release, authority.state


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


def _non_monotonic_payloads(env, predecessor, forgotten):
    """Restamp exact builder output onto the tombstone's own effective time.

    The builder refuses a non-monotonic release, so the evaluator's monotonic
    fence is exercised by re-timing its output instead of re-deriving one.
    """

    space, tombstone, _forget_receipt, semantic_id = _release_inputs(
        env, predecessor, forgotten
    )
    early = str(tombstone["effective_at"])
    transition, receipt = _restore_lineage(
        space=space,
        predecessor=predecessor,
        forgotten=forgotten,
        tombstone=tombstone,
        semantic_id=semantic_id,
        released_at=early,
    )
    _, _, release, state = _release_payloads(
        env,
        predecessor,
        forgotten,
        released_at=(NOW + timedelta(seconds=4)).isoformat(),
    )
    body = {
        **{key: value for key, value in release.items() if key != "release_digest"},
        "restore_transition_digest": canonical_digest(transition),
        "restore_receipt_digest": receipt["receipt_digest"],
        "released_at": early,
    }
    early_release = {**body, "release_digest": canonical_digest(body)}
    early_state = {
        **state,
        "release_digest": early_release["release_digest"],
        "restore_transition_digest": early_release["restore_transition_digest"],
        "restore_receipt_digest": early_release["restore_receipt_digest"],
        "updated_at": early,
    }
    return transition, receipt, early_release, early_state


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
    payloads = _non_monotonic_payloads(lifecycle_env, predecessor, forgotten)
    assert payloads[2]["released_at"] == str(tombstone["effective_at"])
    _commit_release(lifecycle_env, forgotten, *payloads)
    result, locked = _reformation_pair(lifecycle_env, predecessor)
    assert result == locked
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_reformation_tombstone_release_non_monotonic"
        in result.blocked_reasons
    )


def test_builder_output_is_exact_and_content_free(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    assert forgotten.status == "committed"
    _space, tombstone, forget_receipt, semantic_id = _release_inputs(
        lifecycle_env, predecessor, forgotten
    )
    released_at = (NOW + timedelta(seconds=4)).isoformat()
    transition, receipt, release, state = _release_payloads(
        lifecycle_env, predecessor, forgotten, released_at=released_at
    )

    assert release["schema"] == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA
    assert state["schema"] == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA
    assert release["release_id"] == receipt["release_id"] == state["release_id"]
    assert release["release_digest"] == canonical_digest(
        {key: value for key, value in release.items() if key != "release_digest"}
    )
    assert state["release_digest"] == release["release_digest"]
    assert release["evidence_space_id"] == tombstone["evidence_space_id"]
    assert release["character_id"] == predecessor.character_id
    assert release["semantic_identity_digest"] == semantic_id
    assert release["memory_id"] == predecessor.memory_id
    assert release["hidden_revision"] == int(tombstone["hidden_revision"])
    assert release["restored_revision"] == release["hidden_revision"] + 1
    assert release["tombstone_digest"] == tombstone["tombstone_digest"]
    assert release["forget_transition_id"] == tombstone["transition_id"]
    assert release["forget_transition_digest"] == tombstone["transition_digest"]
    assert release["forget_receipt_digest"] == forget_receipt["receipt_digest"]
    assert release["restore_transition_id"] == transition["transition_id"]
    assert release["restore_transition_digest"] == canonical_digest(transition)
    assert release["restore_receipt_digest"] == receipt["receipt_digest"]
    assert release["policy_revision"] == LIFECYCLE_POLICY_REVISION
    assert release["released_at"] == released_at == state["updated_at"]
    assert release["content_free"] is True and state["content_free"] is True
    assert state["effective"] is True
    assert state["tombstone_id"] == forgotten.tombstone_id


def test_builder_output_commits_and_allows_reformation(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    payloads = _release_payloads(
        lifecycle_env,
        predecessor,
        forgotten,
        released_at=(NOW + timedelta(seconds=4)).isoformat(),
    )
    blocked, _locked = _reformation_pair(lifecycle_env, predecessor)
    assert blocked.status == "blocked"

    _commit_release(lifecycle_env, forgotten, *payloads)
    public, locked = _reformation_pair(lifecycle_env, predecessor)
    assert public == locked
    assert public.status == "allowed", public.blocked_reasons


def test_builder_rejects_unsupported_authorization_and_reason(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    space, tombstone, forget_receipt, semantic_id = _release_inputs(
        lifecycle_env, predecessor, forgotten
    )
    released_at = (NOW + timedelta(seconds=4)).isoformat()
    transition, receipt = _restore_lineage(
        space=space,
        predecessor=predecessor,
        forgotten=forgotten,
        tombstone=tombstone,
        semantic_id=semantic_id,
        released_at=released_at,
    )
    for changes in (
        {"authorization_class": "operator_management"},
        {"reason_category": "operator_requested_restore"},
        {"reason_category": "user_requested_forget"},
    ):
        authority, reasons = _build(
            tombstone,
            forget_receipt,
            transition,
            receipt,
            released_at=released_at,
            **changes,
        )
        assert authority is None
        assert reasons == (
            "subjective_mem_restore_tombstone_release_authorization_unsupported",
        )

    authority, reasons = _build(
        tombstone,
        forget_receipt,
        transition,
        receipt,
        released_at=released_at,
        policy_revision="relaylm.subjective_mem_lifecycle_policy.v0",
    )
    assert authority is None
    assert reasons == ("subjective_mem_restore_tombstone_release_policy_unsupported",)


def test_builder_rejects_mismatched_release_id(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    space, tombstone, forget_receipt, semantic_id = _release_inputs(
        lifecycle_env, predecessor, forgotten
    )
    released_at = (NOW + timedelta(seconds=4)).isoformat()
    transition, receipt = _restore_lineage(
        space=space,
        predecessor=predecessor,
        forgotten=forgotten,
        tombstone=tombstone,
        semantic_id=semantic_id,
        released_at=released_at,
    )
    authority, reasons = _build(
        tombstone,
        forget_receipt,
        transition,
        receipt,
        released_at=released_at,
        release_id="smrestorerelease-other-1",
    )
    assert authority is None
    assert reasons == ("subjective_mem_restore_tombstone_release_id_mismatch",)


def test_builder_rejects_tampered_forget_and_restore_lineage(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    space, tombstone, forget_receipt, semantic_id = _release_inputs(
        lifecycle_env, predecessor, forgotten
    )
    released_at = (NOW + timedelta(seconds=4)).isoformat()
    transition, receipt = _restore_lineage(
        space=space,
        predecessor=predecessor,
        forgotten=forgotten,
        tombstone=tombstone,
        semantic_id=semantic_id,
        released_at=released_at,
    )

    foreign_body = {
        key: value for key, value in forget_receipt.items() if key != "receipt_digest"
    }
    foreign_body["receipt_id"] = "smforgetreceipt-foreign-1"
    foreign_receipt = {
        **foreign_body,
        "receipt_digest": canonical_digest(foreign_body),
    }
    authority, reasons = _build(
        tombstone, foreign_receipt, transition, receipt, released_at=released_at
    )
    assert authority is None
    assert reasons == ("subjective_mem_restore_tombstone_release_lineage_invalid",)

    tampered_receipt = {**forget_receipt, "receipt_id": "smforgetreceipt-tampered-1"}
    authority, reasons = _build(
        tombstone, tampered_receipt, transition, receipt, released_at=released_at
    )
    assert authority is None
    assert reasons == (
        "subjective_mem_restore_tombstone_release_input_not_authentic",
    )

    for broken in (
        {**transition, "to_revision": int(tombstone["hidden_revision"]) + 9},
        {**transition, "from_lifecycle_state": "active"},
        {**transition, "operation": "correct"},
        {**transition, "committed_at": (NOW + timedelta(seconds=9)).isoformat()},
    ):
        authority, reasons = _build(
            tombstone, forget_receipt, broken, receipt, released_at=released_at
        )
        assert authority is None
        assert reasons == (
            "subjective_mem_restore_tombstone_release_lineage_invalid",
        )


def test_builder_rejects_non_monotonic_release_without_mutation(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    space, tombstone, forget_receipt, semantic_id = _release_inputs(
        lifecycle_env, predecessor, forgotten
    )
    early = str(tombstone["effective_at"])
    transition, receipt = _restore_lineage(
        space=space,
        predecessor=predecessor,
        forgotten=forgotten,
        tombstone=tombstone,
        semantic_id=semantic_id,
        released_at=early,
    )
    before = sorted(str(path) for path in lifecycle_env["store"].root.rglob("*"))
    page_before = lifecycle_env["page_path"].read_bytes()

    authority, reasons = _build(
        tombstone, forget_receipt, transition, receipt, released_at=early
    )
    assert authority is None
    assert reasons == ("subjective_mem_restore_tombstone_release_non_monotonic",)

    assert sorted(str(path) for path in lifecycle_env["store"].root.rglob("*")) == before
    assert lifecycle_env["page_path"].read_bytes() == page_before
    forbidden = (
        str(lifecycle_env["workspace_root"]),
        predecessor.subjective_meaning,
        predecessor.grounded_content,
        "lc1b-forget-operation",
    )
    assert all(value not in " ".join(reasons) for value in forbidden)
