"""LC-1B Subjective MEM Forget runtime tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path

from relaylm.subjective_mem.commit_io import PLATFORM_REVISION
from relaylm.evidence.common import canonical_digest
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCreateProposal,
    SubjectiveMemProposalBoundary,
)
from relaylm.subjective_mem.forget import (
    SubjectiveMemForgetBoundary,
    SubjectiveMemForgetProposal,
)
from relaylm.subjective_mem.forget_runtime import forget_subjective_mem
from relaylm.subjective_mem.lifecycle import LIFECYCLE_POLICY_REVISION
from relaylm.subjective_mem.markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    parse_subjective_mem_page_bytes,
)
from relaylm.subjective_mem_reformation import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
    check_subjective_mem_reformation,
    check_subjective_mem_reformation_locked,
    subjective_mem_semantic_identity_digest,
)
from relaylm.subjective_mem_runtime import create_subjective_mem
from test_subjective_mem_lifecycle_runtime import _correct, lifecycle_env
from test_subjective_mem_runtime import NOW


def _proposal(env, **changes):
    st1 = env["st1"]
    page = env["page"]
    state = st1.current_state
    receipt = st1.receipt
    assert state is not None and receipt is not None
    predecessor = page.blocks[0].revision
    base = SubjectiveMemForgetProposal(
        expected_memory_id=state.memory_id,
        expected_current_revision=state.current_revision,
        expected_lifecycle_state="active",
        expected_mutation_state="none",
        expected_page_id=page.page_id,
        expected_relative_path="memory/episodes/subjective-mem-v1.md",
        expected_block_id=page.blocks[0].block_id,
        expected_page_digest=page.page_digest,
        expected_current_selector_id=state.memory_state_id,
        expected_current_selector_digest=canonical_digest(state.to_dict()),
        expected_current_receipt_id=receipt.receipt_id,
        expected_current_receipt_digest=receipt.to_dict()["receipt_digest"],
        expected_memory_kind=predecessor.memory_kind,
        expected_formation_stage=predecessor.formation_stage,
        expected_scope_binding_digest=canonical_digest(
            predecessor.scope_binding.to_dict()
        ),
        expected_formation_snapshot_digest=canonical_digest(
            predecessor.formation_snapshot.to_dict()
        ),
        expected_revision_schema=SUBJECTIVE_MEM_REVISION_SCHEMA,
        expected_page_schema=PAGE_SCHEMA,
        expected_block_schema=LIFECYCLE_BLOCK_SCHEMA,
        expected_renderer_revision=RENDERER_REVISION,
        expected_partition_revision=PAGE_PARTITION_REVISION,
        expected_platform_revision=PLATFORM_REVISION,
        authorization_class="user_management",
        authorization_id="user-forget-authorization-1",
        reason_category="user_requested_forget",
        policy_revision=LIFECYCLE_POLICY_REVISION,
        boundary=SubjectiveMemForgetBoundary(),
    )
    return replace(base, **changes)


def _forget(env, *, proposal=None, key="lc1b-forget-operation", apply=True, fault=None):
    return forget_subjective_mem(
        store=env["store"],
        evidence_space_id=env["captured"].evidence_space_id,
        character_config=env["config"],
        character_authority=env["authority"],
        workspace_root=str(env["workspace_root"]),
        operation_idempotency_key=key,
        proposal=proposal or _proposal(env),
        apply_enabled=apply,
        committed_at=NOW + timedelta(seconds=2),
        observed_at=NOW + timedelta(seconds=3),
        fault_injector=fault,
    )


def _reformation_kwargs(env, predecessor):
    return {
        "evidence_space_id": env["captured"].evidence_space_id,
        "character_id": predecessor.character_id,
        "grounded_content_digest": predecessor.grounded_content_digest,
        "subjective_meaning": predecessor.subjective_meaning,
        "memory_kind": predecessor.memory_kind,
        "scope_binding": predecessor.scope_binding,
    }


def _reformation_check(env, predecessor):
    return check_subjective_mem_reformation(
        store=env["store"], **_reformation_kwargs(env, predecessor)
    )


def _reformation_pair(env, predecessor):
    kwargs = _reformation_kwargs(env, predecessor)
    public = check_subjective_mem_reformation(store=env["store"], **kwargs)
    with env["store"].transaction(kwargs["evidence_space_id"]) as tx:
        locked = check_subjective_mem_reformation_locked(tx=tx, **kwargs)
    return public, locked


def _semantic_identity(env, predecessor) -> str:
    return subjective_mem_semantic_identity_digest(
        **_reformation_kwargs(env, predecessor)
    )


def _create_candidate(env, *, key: str, subjective_meaning: str, apply: bool):
    predecessor = env["page"].blocks[0].revision
    return create_subjective_mem(
        store=env["store"],
        evidence_space_id=env["captured"].evidence_space_id,
        character_config=env["config"],
        character_authority=env["authority"],
        assessment_revision=env["assessment_revision"],
        assessment_current_state=env["assessment_state"],
        proposal=SubjectiveMemCreateProposal(
            subjective_meaning=subjective_meaning,
            memory_kind=predecessor.memory_kind,
            scope_binding=predecessor.scope_binding,
            formation_snapshot=predecessor.formation_snapshot,
            strength=predecessor.strength,
            boundary=SubjectiveMemProposalBoundary(),
        ),
        operation_idempotency_key=key,
        apply_enabled=apply,
        decided_at=NOW + timedelta(seconds=4),
        observed_at=NOW + timedelta(seconds=5),
    )


def test_forget_dry_run_validates_without_writes(lifecycle_env) -> None:
    before = lifecycle_env["page_path"].read_bytes()
    result = _forget(lifecycle_env, apply=False)
    assert result.status == "dry_run_ready", result.blocked_reasons
    assert lifecycle_env["page_path"].read_bytes() == before
    assert list(
        lifecycle_env["store"].root.rglob("*subjective_mem_forget_tombstone*")
    ) == []


def test_forget_happy_path_appends_hidden_semantic_clone(lifecycle_env) -> None:
    original = lifecycle_env["page"].blocks[0].revision
    result = _forget(lifecycle_env)
    assert result.status == "committed", result.blocked_reasons
    assert result.current_state is not None
    assert result.current_state.current_revision == 2
    assert result.current_state.lifecycle_state == "hidden"
    assert result.current_state.mutation_state == "none"
    assert result.current_state.retrieval_eligible is False
    assert result.canonical_markdown_published is True
    assert result.lifecycle_receipt_present is True
    assert result.tombstone_present is True

    page, reasons = parse_subjective_mem_page_bytes(
        lifecycle_env["page_path"].read_bytes()
    )
    assert page is not None and not reasons
    revisions = [
        item.revision for item in page.blocks if item.revision.memory_id == result.memory_id
    ]
    assert [item.memory_revision for item in revisions] == [1, 2]
    successor = revisions[1]
    assert successor.predecessor_revision_or_null == 1
    assert successor.lifecycle_state == "hidden"
    assert successor.retrieval_visible is False
    assert successor.authorization_kind == "lifecycle_transition"
    assert successor.grounded_content == original.grounded_content
    assert successor.grounded_content_digest == original.grounded_content_digest
    assert successor.subjective_meaning == original.subjective_meaning
    assert successor.memory_kind == original.memory_kind
    assert successor.formation_stage == original.formation_stage
    assert successor.scope_binding.to_dict() == original.scope_binding.to_dict()
    assert successor.formation_snapshot.to_dict() == original.formation_snapshot.to_dict()
    assert successor.strength.to_dict() == original.strength.to_dict()

    tombstone = lifecycle_env["store"].read_record(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        record_kind="subjective_mem_forget_tombstone",
        record_id=result.tombstone_id,
    )
    assert isinstance(tombstone, dict)
    assert tombstone["content_free"] is True
    assert tombstone["source_revision"] == 1
    assert tombstone["hidden_revision"] == 2
    assert tombstone["formation_stage"] == original.formation_stage
    assert tombstone["transition_digest"]
    forbidden = {
        "grounded_content",
        "subjective_meaning",
        "prompt",
        "raw_reason",
        "workspace_root",
        "relative_path",
    }
    assert forbidden.isdisjoint(tombstone)


def test_forget_exact_retry_returns_same_result_without_third_revision(
    lifecycle_env,
) -> None:
    first = _forget(lifecycle_env)
    second = _forget(lifecycle_env)
    assert first.status == "committed"
    assert second.status == "duplicate_finalized", second.blocked_reasons
    assert second.transition_id == first.transition_id
    assert second.receipt_id == first.receipt_id
    assert second.tombstone_id == first.tombstone_id
    page, reasons = parse_subjective_mem_page_bytes(
        lifecycle_env["page_path"].read_bytes()
    )
    assert page is not None and not reasons
    assert [item.revision.memory_revision for item in page.blocks] == [1, 2]


def test_forget_changed_input_under_same_key_conflicts(lifecycle_env) -> None:
    first = _forget(lifecycle_env)
    assert first.status == "committed"
    changed = _proposal(
        lifecycle_env, authorization_id="different-forget-authorization"
    )
    second = _forget(lifecycle_env, proposal=changed)
    assert second.status == "integrity_conflict"
    assert "subjective_mem_forget_idempotency_conflict" in second.blocked_reasons


def test_forget_rejects_stale_or_non_active_source(lifecycle_env) -> None:
    stale = _proposal(lifecycle_env, expected_current_revision=2)
    result = _forget(lifecycle_env, proposal=stale, apply=False)
    assert result.status == "fail_closed"
    hidden = _proposal(lifecycle_env, expected_lifecycle_state="hidden")
    result = _forget(lifecycle_env, proposal=hidden, apply=False)
    assert result.status == "fail_closed"
    assert any(
        "transition_unsupported" in item or "precondition" in item
        for item in result.blocked_reasons
    )


def test_forget_after_intent_recovers_exact_immutable_post_image(lifecycle_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_intent_before_page":
            raise RuntimeError("simulated")

    first = _forget(lifecycle_env, fault=crash)
    assert first.status == "recovery_pending"
    assert first.current_state is not None
    assert first.current_state.mutation_state == "prepared"
    second = _forget(lifecycle_env)
    assert second.status == "committed", second.blocked_reasons
    assert second.recovery_outcome == "published_and_finalized"
    assert second.current_state is not None
    assert second.current_state.lifecycle_state == "hidden"


def test_forget_page_present_receipt_missing_rolls_forward(lifecycle_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_page_before_receipt":
            raise RuntimeError("simulated")

    first = _forget(lifecycle_env, fault=crash)
    assert first.status == "recovery_pending", first.blocked_reasons
    assert first.canonical_markdown_published is True
    second = _forget(lifecycle_env)
    assert second.status == "committed", second.blocked_reasons
    assert second.recovery_outcome == "post_image_rolled_forward"
    assert second.current_state is not None
    assert second.current_state.lifecycle_state == "hidden"


def test_public_and_locked_reformation_allowed_are_identical(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    public, locked = _reformation_pair(lifecycle_env, predecessor)
    assert public == locked
    assert public.status == "allowed"


def test_forget_tombstone_blocks_only_exact_reformation(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    before = _reformation_check(lifecycle_env, predecessor)
    assert before.status == "allowed"

    forgotten = _forget(lifecycle_env)
    assert forgotten.status == "committed"
    public, locked = _reformation_pair(lifecycle_env, predecessor)
    assert public == locked
    assert public.status == "blocked"
    assert public.tombstone_ids == (forgotten.tombstone_id,)

    near_but_not_exact = check_subjective_mem_reformation(
        store=lifecycle_env["store"],
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        character_id=predecessor.character_id,
        grounded_content_digest=predecessor.grounded_content_digest,
        subjective_meaning=predecessor.subjective_meaning + " A distinct later nuance.",
        memory_kind=predecessor.memory_kind,
        scope_binding=predecessor.scope_binding,
    )
    assert near_but_not_exact.status == "allowed"


def test_forget_blocks_new_exact_sm1_create_but_allows_distinct_meaning(
    lifecycle_env,
) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    assert forgotten.status == "committed"

    blocked = _create_candidate(
        lifecycle_env,
        key="lc1b-reformation-exact-create",
        subjective_meaning=predecessor.subjective_meaning,
        apply=False,
    )
    assert blocked.status == "fail_closed"
    assert (
        "subjective_mem_reformation_blocked_by_forget"
        in blocked.blocked_reasons
    )

    distinct = _create_candidate(
        lifecycle_env,
        key="lc1b-reformation-distinct-create",
        subjective_meaning=predecessor.subjective_meaning + " A distinct later nuance.",
        apply=False,
    )
    assert distinct.status == "dry_run_ready", distinct.blocked_reasons


def test_reformation_checks_reject_dangling_tombstone_state_identically(
    lifecycle_env,
) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    assert forgotten.status == "committed"

    tombstone_path = (
        lifecycle_env["store"].root
        / lifecycle_env["captured"].evidence_space_id
        / "records"
        / "subjective_mem_forget_tombstone"
        / f"{forgotten.tombstone_id}.json"
    )
    tombstone_path.unlink()

    public, locked = _reformation_pair(lifecycle_env, predecessor)
    assert public == locked
    assert public.status == "fail_closed"
    assert (
        "subjective_mem_reformation_tombstone_lineage_invalid"
        in public.blocked_reasons
    )


def test_reformation_checks_reject_duplicate_state_identically(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    forgotten = _forget(lifecycle_env)
    assert forgotten.status == "committed"
    semantic_id = _semantic_identity(lifecycle_env, predecessor)
    events = lifecycle_env["store"].read_log(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        key=semantic_id,
    )
    assert isinstance(events, list) and len(events) == 1
    written = lifecycle_env["store"].write_log(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        key=semantic_id,
        events=(events[0], events[0]),
    )
    assert written.status == "created"

    public, locked = _reformation_pair(lifecycle_env, predecessor)
    assert public == locked
    assert public.status == "fail_closed"
    assert (
        "subjective_mem_reformation_tombstone_state_duplicate"
        in public.blocked_reasons
    )


def test_malformed_existing_tombstone_state_blocks_forget_before_publication(
    lifecycle_env,
) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    semantic_id = _semantic_identity(lifecycle_env, predecessor)
    before = lifecycle_env["page_path"].read_bytes()
    written = lifecycle_env["store"].write_log(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        key=semantic_id,
        events=({"schema": "malformed"},),
    )
    assert written.status == "created"

    result = _forget(lifecycle_env)
    assert result.status == "fail_closed"
    assert lifecycle_env["page_path"].read_bytes() == before
    assert (
        "subjective_mem_reformation_tombstone_state_corrupt"
        in result.blocked_reasons
    )


def _decision_path(env, predecessor) -> Path:
    return env["store"]._record_path(  # noqa: SLF001
        env["captured"].evidence_space_id,
        "subjective_mem_decision",
        predecessor.authorization_id,
    )


def test_forget_owns_predecessor_authority_through_shared_owner() -> None:
    source = Path("relaylm/subjective_mem/forget_runtime.py").read_text(encoding="utf-8")
    assert "from relaylm.subjective_mem.lifecycle_authority import" in source
    assert "load_subjective_mem_predecessor_authority_locked(" in source
    for removed in (
        "_validate_evidence_space_locked",
        "_validate_current_receipt_locked",
        "_validate_predecessor_authority_locked",
    ):
        assert removed not in source


def test_forget_accepts_exact_st1_predecessor_authority(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    assert predecessor.memory_revision == 1
    assert predecessor.authorization_kind == "formation_decision"
    result = _forget(lifecycle_env)
    assert result.status == "committed", result.blocked_reasons
    assert result.current_state is not None
    assert result.current_state.current_revision == 2
    assert result.current_state.lifecycle_state == "hidden"


def test_forget_accepts_committed_correct_predecessor_authority(lifecycle_env) -> None:
    corrected = _correct(lifecycle_env)
    assert corrected.status == "committed", corrected.blocked_reasons
    assert corrected.current_state is not None
    page, reasons = parse_subjective_mem_page_bytes(
        lifecycle_env["page_path"].read_bytes()
    )
    assert page is not None and not reasons
    current_block = next(
        item for item in page.blocks if item.revision.memory_revision == 2
    )
    assert current_block.revision.authorization_kind == "lifecycle_transition"
    receipt = lifecycle_env["store"].read_record(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        record_kind="subjective_mem_lifecycle_receipt",
        record_id=corrected.receipt_id,
    )
    assert isinstance(receipt, dict)
    proposal = _proposal(
        lifecycle_env,
        expected_current_revision=2,
        expected_block_id=current_block.block_id,
        expected_page_digest=page.page_digest,
        expected_current_selector_digest=canonical_digest(
            corrected.current_state.to_dict()
        ),
        expected_current_receipt_id=corrected.receipt_id,
        expected_current_receipt_digest=receipt["receipt_digest"],
        authorization_id="user-forget-authorization-2",
    )
    result = forget_subjective_mem(
        store=lifecycle_env["store"],
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        character_config=lifecycle_env["config"],
        character_authority=lifecycle_env["authority"],
        workspace_root=str(lifecycle_env["workspace_root"]),
        operation_idempotency_key="lc1b-forget-after-correct",
        proposal=proposal,
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=4),
        observed_at=NOW + timedelta(seconds=5),
    )
    assert result.status == "committed", result.blocked_reasons
    assert result.current_state is not None
    assert result.current_state.current_revision == 3
    assert result.current_state.lifecycle_state == "hidden"


def test_forget_missing_predecessor_authorization_fails_closed(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    before = lifecycle_env["page_path"].read_bytes()
    _decision_path(lifecycle_env, predecessor).unlink()

    result = _forget(lifecycle_env)
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_lifecycle_predecessor_authority_missing"
        in result.blocked_reasons
    )
    assert lifecycle_env["page_path"].read_bytes() == before


def test_forget_non_exact_predecessor_authorization_fails_closed(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    before = lifecycle_env["page_path"].read_bytes()
    path = _decision_path(lifecycle_env, predecessor)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["result_memory_ref_or_null"] = {
        "memory_id": predecessor.memory_id,
        "memory_revision": 99,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )

    result = _forget(lifecycle_env)
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_lifecycle_predecessor_authority_not_exact"
        in result.blocked_reasons
    )
    assert lifecycle_env["page_path"].read_bytes() == before
