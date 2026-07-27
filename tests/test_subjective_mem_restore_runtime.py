"""LC-1D write-free Subjective MEM Restore preflight tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import inspect
import json

from relaylm._subjective_mem_commit_io import PLATFORM_REVISION
from relaylm.evidence_common import canonical_digest
from relaylm.subjective_mem import SUBJECTIVE_MEM_REVISION_SCHEMA
from relaylm.subjective_mem_lifecycle import LIFECYCLE_POLICY_REVISION
from relaylm.subjective_mem_markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    parse_subjective_mem_page_bytes,
)
from relaylm.subjective_mem_lifecycle_engine import validate_lifecycle_plan
from relaylm.subjective_mem_reformation import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
)
from relaylm.subjective_mem_restore import (
    SubjectiveMemRestoreBoundary,
    SubjectiveMemRestoreProposal,
    derive_subjective_mem_restore_operation_identity,
)
import relaylm.subjective_mem_restore_runtime as restore_runtime
from relaylm.subjective_mem_restore_runtime import restore_subjective_mem
from test_subjective_mem_forget_runtime import _forget, _semantic_identity
from test_subjective_mem_lifecycle_runtime import lifecycle_env
from test_subjective_mem_runtime import NOW


def _hidden_env(env):
    forgotten = _forget(env)
    assert forgotten.status == "committed", forgotten.blocked_reasons
    assert forgotten.current_state is not None
    page, reasons = parse_subjective_mem_page_bytes(env["page_path"].read_bytes())
    assert page is not None and not reasons
    state = forgotten.current_state
    block = next(
        item for item in page.blocks
        if item.revision.memory_id == state.memory_id
        and item.revision.memory_revision == state.current_revision
    )
    receipt = env["store"].read_record(
        evidence_space_id=env["captured"].evidence_space_id,
        record_kind="subjective_mem_lifecycle_receipt",
        record_id=state.current_receipt_id,
    )
    assert isinstance(receipt, dict)
    transition = env["store"].read_record(
        evidence_space_id=env["captured"].evidence_space_id,
        record_kind="subjective_mem_lifecycle_transition",
        record_id=receipt["transition_id"],
    )
    assert isinstance(transition, dict)
    tombstone = env["store"].read_record(
        evidence_space_id=env["captured"].evidence_space_id,
        record_kind="subjective_mem_forget_tombstone",
        record_id=forgotten.tombstone_id,
    )
    assert isinstance(tombstone, dict)
    return forgotten, state, page, block, receipt, transition, tombstone


def _proposal(env, **changes):
    forgotten, state, page, block, receipt, transition, tombstone = _hidden_env(env)
    base = SubjectiveMemRestoreProposal(
        expected_memory_id=state.memory_id,
        expected_current_revision=state.current_revision,
        expected_lifecycle_state="hidden",
        expected_mutation_state="none",
        expected_page_id=page.page_id,
        expected_relative_path="memory/episodes/subjective-mem-v1.md",
        expected_block_id=block.block_id,
        expected_page_digest=page.page_digest,
        expected_current_selector_id=state.memory_state_id,
        expected_current_selector_digest=canonical_digest(state.to_dict()),
        expected_current_receipt_id=receipt["receipt_id"],
        expected_current_receipt_digest=receipt["receipt_digest"],
        expected_forget_transition_id=transition["transition_id"],
        expected_forget_transition_digest=canonical_digest(transition),
        expected_forget_tombstone_id=tombstone["tombstone_id"],
        expected_forget_tombstone_digest=tombstone["tombstone_digest"],
        expected_semantic_identity_digest=_semantic_identity(env, block.revision),
        expected_memory_kind=block.revision.memory_kind,
        expected_formation_stage=block.revision.formation_stage,
        expected_scope_binding_digest=canonical_digest(
            block.revision.scope_binding.to_dict()
        ),
        expected_formation_snapshot_digest=canonical_digest(
            block.revision.formation_snapshot.to_dict()
        ),
        expected_revision_schema=SUBJECTIVE_MEM_REVISION_SCHEMA,
        expected_page_schema=PAGE_SCHEMA,
        expected_block_schema=LIFECYCLE_BLOCK_SCHEMA,
        expected_renderer_revision=RENDERER_REVISION,
        expected_partition_revision=PAGE_PARTITION_REVISION,
        expected_platform_revision=PLATFORM_REVISION,
        authorization_class="user_management",
        authorization_id="user-restore-authorization-1",
        reason_category="user_requested_restore",
        policy_revision=LIFECYCLE_POLICY_REVISION,
        boundary=SubjectiveMemRestoreBoundary(),
    )
    return forgotten, replace(base, **changes)


def _restore(env, proposal, *, apply=False, key="lc1d-restore-operation"):
    return restore_subjective_mem(
        store=env["store"],
        evidence_space_id=env["captured"].evidence_space_id,
        character_config=env["config"],
        character_authority=env["authority"],
        workspace_root=str(env["workspace_root"]),
        operation_idempotency_key=key,
        proposal=proposal,
        apply_enabled=apply,
        committed_at=NOW + timedelta(seconds=4),
        observed_at=NOW + timedelta(seconds=5),
    )


def test_restore_dry_run_validates_exact_hidden_forget_lineage_without_writes(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = sorted(
        str(path.relative_to(lifecycle_env["store"].root))
        for path in lifecycle_env["store"].root.rglob("*")
        if path.is_file()
    )
    result = _restore(lifecycle_env, proposal)
    assert result.status == "dry_run_ready", result.blocked_reasons
    assert result.from_revision == 2
    assert result.to_revision == 3
    assert result.transition_id is not None
    assert result.receipt_id is not None
    assert result.release_id is not None
    assert result.current_state is not None
    assert result.current_state.lifecycle_state == "hidden"
    assert result.current_state.retrieval_eligible is False
    assert result.post_image_digest is not None
    assert lifecycle_env["page_path"].read_bytes() == before_page
    after_files = sorted(
        str(path.relative_to(lifecycle_env["store"].root))
        for path in lifecycle_env["store"].root.rglob("*")
        if path.is_file()
    )
    assert after_files == before_files
    assert not any("restore" in item for item in after_files)


def test_restore_changed_forget_lineage_fails_closed(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    invalid = (
        replace(proposal, expected_forget_transition_digest="a" * 64),
        replace(proposal, expected_forget_tombstone_digest="b" * 64),
        replace(proposal, expected_semantic_identity_digest="c" * 64),
    )
    for index, candidate in enumerate(invalid):
        result = _restore(lifecycle_env, candidate, key=f"invalid-{index}")
        assert result.status == "fail_closed"
        assert any(
            "forget" in reason or "semantic" in reason
            for reason in result.blocked_reasons
        )


def test_restore_requires_exact_hidden_selector_and_latest_revision(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    wrong_state = replace(proposal, expected_lifecycle_state="active")
    result = _restore(lifecycle_env, wrong_state, key="wrong-state")
    assert result.status == "fail_closed"
    assert "subjective_mem_restore_transition_direction_invalid" in result.blocked_reasons
    stale = replace(proposal, expected_current_revision=3)
    result = _restore(lifecycle_env, stale, key="stale-revision")
    assert result.status == "fail_closed"


def test_restore_projection_is_content_free(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    raw_key = "caller-secret-restore-key"
    result = _restore(lifecycle_env, proposal, key=raw_key)
    projection = result.to_log_dict()
    text = json.dumps(projection)
    assert projection["content_free"] is True
    assert projection["ordinary_retrieval_wired"] is False
    assert projection["tombstone_release_present"] is False
    assert raw_key not in text
    assert str(lifecycle_env["workspace_root"]) not in text
    assert "I felt relieved" not in text


def test_restore_runtime_uses_shared_authority_without_private_runtime_imports() -> None:
    source = inspect.getsource(restore_runtime)
    assert "subjective_mem_lifecycle_authority import" in source
    assert "subjective_mem_lifecycle_runtime import" not in source
    assert "subjective_mem_forget_runtime import" not in source
    assert "subjective_mem_pin_runtime import" not in source
    assert "relaymem_primary" not in source
    assert "ContextVar" not in source
    assert "publish_canonical_page" not in source


def _prepared_plan(env, proposal, *, key="lc1d-restore-plan"):
    space = env["captured"].evidence_space_id
    committed_at = (NOW + timedelta(seconds=4)).isoformat()
    identity, reasons = derive_subjective_mem_restore_operation_identity(
        evidence_space_id=space,
        character_authority_digest=canonical_digest(env["authority"].to_dict()),
        memory_id=proposal.expected_memory_id,
        operation_idempotency_key=key,
        proposal=proposal,
        operation_time=committed_at,
    )
    assert identity is not None, reasons
    prepared, reasons = restore_runtime._prepare(  # noqa: SLF001
        env["store"], space, env["authority"], str(env["workspace_root"]),
        proposal, identity, committed_at,
    )
    return prepared, reasons, identity, committed_at


def _store_files(env):
    return sorted(
        str(path.relative_to(env["store"].root))
        for path in env["store"].root.rglob("*")
        if path.is_file()
    )


def test_restore_prepares_engine_valid_publication_plan(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared, reasons, identity, committed_at = _prepared_plan(lifecycle_env, proposal)
    assert prepared is not None, reasons

    plan = prepared.plan
    assert validate_lifecycle_plan(plan) == ()
    assert plan.operation_kind == "restore"
    assert plan.evidence_space_id == lifecycle_env["captured"].evidence_space_id
    assert plan.character_id == lifecycle_env["authority"].character_id
    assert plan.from_revision == proposal.expected_current_revision
    assert plan.to_revision == proposal.expected_current_revision + 1
    assert plan.to_lifecycle_state == "active"
    assert plan.operation_slot_id == identity.operation_slot_id
    assert plan.transition_id == identity.transition_id
    assert plan.receipt_id == identity.receipt_id
    assert plan.result_id == identity.result_id
    assert plan.intent_id == identity.intent_id
    assert plan.selector_id == proposal.expected_current_selector_id
    assert plan.page_id == proposal.expected_page_id
    assert plan.page_relative_path == proposal.expected_relative_path
    assert plan.pre_image_state == "present"
    assert plan.pre_image_digest == proposal.expected_page_digest
    assert plan.post_image_digest == prepared.page.post_image_digest
    assert plan.predecessor_revision_digest == canonical_digest(
        prepared.predecessor.to_dict()
    )
    assert plan.successor_revision_digest == canonical_digest(
        prepared.successor.to_dict()
    )
    assert plan.successor_block_id == prepared.page.block_id
    assert plan.artifact_id == prepared.page.artifact_id
    assert plan.prepared_at == committed_at
    assert plan.prepared_intent["release_id"] == identity.release_id
    assert plan.prepared_intent["forget_tombstone_id"] == (
        proposal.expected_forget_tombstone_id
    )
    assert plan.prepared_intent["forget_transition_digest"] == (
        proposal.expected_forget_transition_digest
    )
    assert plan.prepared_intent["semantic_identity_digest"] == (
        proposal.expected_semantic_identity_digest
    )
    assert prepared.successor.lifecycle_state == "active"
    assert prepared.successor.retrieval_visible is True
    assert prepared.successor.memory_revision == prepared.predecessor.memory_revision + 1


def test_restore_prepared_selector_fences_only_reservation_fields(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared, reasons, _identity, committed_at = _prepared_plan(lifecycle_env, proposal)
    assert prepared is not None, reasons

    current, reserved = prepared.current, prepared.prepared
    assert current.mutation_state == "none"
    assert reserved.mutation_state == "prepared"
    assert reserved.updated_at == committed_at
    assert reserved.retrieval_eligible is False
    assert current.retrieval_eligible is False
    assert reserved.lifecycle_state == current.lifecycle_state == "hidden"
    assert replace(
        reserved, mutation_state=current.mutation_state, updated_at=current.updated_at
    ) == current
    for field in (
        "workspace_authority_digest", "scope_binding_digest", "page_id", "block_id",
        "canonical_page_digest", "authorization_kind", "authorization_id",
        "current_receipt_id",
    ):
        assert getattr(reserved, field) == getattr(current, field)
    assert prepared.plan.prepared_state == reserved
    assert prepared.plan.current_state == current


def test_restore_plan_binds_shared_authority_and_forget_tombstone(lifecycle_env) -> None:
    forgotten, proposal = _proposal(lifecycle_env)
    prepared, reasons, _identity, _at = _prepared_plan(lifecycle_env, proposal)
    assert prepared is not None, reasons

    kinds = [kind for kind, _id, _body in prepared.plan.record_bindings]
    assert kinds == [
        "evidence_space_descriptor",
        "subjective_mem_lifecycle_receipt",
        "subjective_mem_lifecycle_transition",
        "subjective_mem_forget_tombstone",
    ]
    bound = {kind: (record_id, body) for kind, record_id, body in prepared.plan.record_bindings}
    tombstone_id, tombstone = bound["subjective_mem_forget_tombstone"]
    assert tombstone_id == proposal.expected_forget_tombstone_id
    assert tombstone["tombstone_digest"] == proposal.expected_forget_tombstone_digest
    assert tombstone["effective"] is True and tombstone["content_free"] is True
    receipt_id, receipt = bound["subjective_mem_lifecycle_receipt"]
    assert receipt_id == proposal.expected_current_receipt_id
    assert receipt["operation_kind"] == "forget"
    assert receipt["tombstone_id"] == forgotten.tombstone_id


def test_restore_plan_binds_singleton_tombstone_state_and_empty_release(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared, reasons, _identity, _at = _prepared_plan(lifecycle_env, proposal)
    assert prepared is not None, reasons

    logs = prepared.plan.log_bindings
    assert [kind for kind, _key, _events in logs] == [
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
    ]
    state_kind, state_key, state_events = logs[0]
    assert state_kind == SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND
    assert state_key == proposal.expected_semantic_identity_digest
    assert len(state_events) == 1
    assert state_events[0]["tombstone_id"] == proposal.expected_forget_tombstone_id
    release_kind, release_key, release_events = logs[1]
    assert release_kind == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND
    assert release_key == proposal.expected_forget_tombstone_id
    assert release_events == ()


def test_restore_dry_run_and_apply_paths_make_no_mutation(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)

    dry = _restore(lifecycle_env, proposal, key="no-mutation-dry")
    assert dry.status == "dry_run_ready", dry.blocked_reasons
    applied = _restore(lifecycle_env, proposal, apply=True, key="no-mutation-apply")
    assert applied.status == "fail_closed"
    assert applied.blocked_reasons == ("subjective_mem_restore_apply_not_implemented",)
    assert applied.persisted is False
    assert applied.current_state is not None
    assert applied.post_image_digest is not None

    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _store_files(lifecycle_env) == before_files
    assert not any("restore" in item for item in _store_files(lifecycle_env))


def test_restore_fails_closed_on_existing_release_or_changed_forget_authority(
    lifecycle_env,
) -> None:
    forgotten, proposal = _proposal(lifecycle_env)
    space = lifecycle_env["captured"].evidence_space_id
    before_page = lifecycle_env["page_path"].read_bytes()

    tombstone_path = lifecycle_env["store"]._record_path(  # noqa: SLF001
        space, "subjective_mem_forget_tombstone", forgotten.tombstone_id
    )
    saved = tombstone_path.read_text(encoding="utf-8")
    tombstone_path.unlink()
    missing = _restore(lifecycle_env, proposal, key="changed-forget-authority")
    assert missing.status == "fail_closed"
    assert (
        "subjective_mem_restore_forget_tombstone_not_exact" in missing.blocked_reasons
        or "subjective_mem_restore_forget_tombstone_not_effective"
        in missing.blocked_reasons
    )
    tombstone_path.write_text(saved, encoding="utf-8")

    written = lifecycle_env["store"].write_log(
        evidence_space_id=space,
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        key=forgotten.tombstone_id,
        events=({"schema": "already-released"},),
    )
    assert written.status == "created"
    before_files = _store_files(lifecycle_env)
    released = _restore(lifecycle_env, proposal, key="already-released")
    assert released.status == "fail_closed"
    # An existing release state is fenced twice: the anti-reformation evaluator
    # stops treating the tombstone as effective, and the plan refuses to bind a
    # non-empty release log. Either fence must stop the operation before a write.
    assert set(released.blocked_reasons) <= {
        "subjective_mem_restore_forget_tombstone_not_effective",
        "subjective_mem_restore_tombstone_release_present",
    }
    assert released.blocked_reasons
    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _store_files(lifecycle_env) == before_files


def test_restore_plans_through_shared_engine_without_direct_publication() -> None:
    source = inspect.getsource(restore_runtime)
    assert "subjective_mem_lifecycle_engine import" in source
    assert "validate_lifecycle_plan(" in source
    assert "LifecyclePublicationPlan(" in source
    for forbidden in (
        "reserve_lifecycle_publication",
        "publish_lifecycle_post_image",
        "resolve_finalized_replay",
        "write_immutable_rendered_artifact",
        "tx.commit(",
        "write_record(",
        "write_log(",
    ):
        assert forbidden not in source
