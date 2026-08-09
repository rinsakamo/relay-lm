"""LC-1D Subjective MEM Restore preflight, publication, replay, and recovery tests."""
from __future__ import annotations

import ast
from dataclasses import replace
from datetime import timedelta
import inspect
import json

from relaylm.subjective_mem.commit_io import ARTIFACT_DIRECTORY_PARTS, PLATFORM_REVISION
from relaylm.evidence.common import canonical_digest
from relaylm.subjective_mem.models import SUBJECTIVE_MEM_REVISION_SCHEMA
from relaylm.subjective_mem_lifecycle import LIFECYCLE_POLICY_REVISION
from relaylm.subjective_mem_markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    parse_subjective_mem_page_bytes,
)
from relaylm.subjective_mem_lifecycle_engine import (
    reserve_lifecycle_publication,
    validate_lifecycle_plan,
)
from relaylm.subjective_mem_reformation import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
)
from relaylm.subjective_mem_tombstone_release import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
)
from relaylm.subjective_mem_restore import (
    SubjectiveMemRestoreBoundary,
    SubjectiveMemRestoreProposal,
    derive_subjective_mem_restore_operation_identity,
)
import relaylm.subjective_mem_restore_plan as restore_plan
import relaylm.subjective_mem_restore_replay as restore_replay
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


def test_restore_dry_run_makes_no_mutation(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)

    dry = _restore(lifecycle_env, proposal, key="no-mutation-dry")
    assert dry.status == "dry_run_ready", dry.blocked_reasons
    assert dry.persisted is False
    assert dry.canonical_markdown_published is False
    assert dry.lifecycle_receipt_present is False
    assert dry.tombstone_release_present is False
    assert dry.current_state is not None
    assert dry.post_image_digest is not None

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


def test_restore_publishes_only_through_the_shared_engine() -> None:
    runtime_source = inspect.getsource(restore_runtime)
    plan_source = inspect.getsource(restore_plan)
    assert "subjective_mem_lifecycle_engine import" in runtime_source
    assert "validate_lifecycle_plan(" in runtime_source
    replay_source = inspect.getsource(restore_replay)
    assert "reserve_lifecycle_publication(" in runtime_source
    assert "publish_lifecycle_post_image(" in runtime_source
    assert "resolve_finalized_replay(" in runtime_source
    assert "read_prepared_post_image(" in runtime_source
    assert "lifecycle_claim_record(" in runtime_source
    assert "build_subjective_mem_restore_replay_plan(" in runtime_source
    assert "LifecyclePublicationPlan(" in plan_source
    assert "LifecyclePublicationPlan(" in replay_source
    # no background repair, rollback, or direct durable write in any Restore module
    for source in (runtime_source, plan_source, replay_source):
        for forbidden in (
            "recovery_lifecycle_state",
            "write_immutable_rendered_artifact",
            "tx.commit(",
            "write_record(",
            "write_log(",
            "threading",
            "asyncio",
        ):
            assert forbidden not in source
    for forbidden in ("read_prepared_post_image(", "lifecycle_claim_record("):
        assert forbidden not in plan_source and forbidden not in replay_source
    # only the runtime may drive the shared engine; prose may name it
    for source in (plan_source, replay_source):
        for forbidden in (
            "reserve_lifecycle_publication(",
            "publish_lifecycle_post_image(",
            "resolve_finalized_replay(",
        ):
            assert forbidden not in source


def test_restore_runtime_delegates_plan_construction_to_plan_module() -> None:
    runtime_source = inspect.getsource(restore_runtime)
    assert "from relaylm.subjective_mem_restore_plan import" in runtime_source
    assert "build_subjective_mem_restore_prepared_operation(" in runtime_source
    # the runtime keeps no second intent, plan, successor, or page constructor
    assert "LifecyclePublicationPlan(" not in runtime_source
    assert "LIFECYCLE_INTENT_SCHEMA" not in runtime_source
    assert "SubjectiveMemRestorePlanInputs(" not in runtime_source
    assert "build_subjective_mem_restore_lifecycle_plan(" not in runtime_source
    assert "plan_subjective_mem_revision_successor(" not in runtime_source
    assert "parse_subjective_mem_page_bytes(" not in runtime_source
    assert "subjective_mem_page_identity(" not in runtime_source
    # the operation owner still validates the composed plan through the engine
    assert "validate_lifecycle_plan(" in runtime_source
    assert (
        "from relaylm.subjective_mem_tombstone_release import" in runtime_source
    )


def test_restore_pure_modules_are_storage_neutral_and_write_free() -> None:
    for module in (restore_plan, restore_replay):
        source = inspect.getsource(module)
        imported = {
            node.module
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not any(
            "restore_runtime" in name or "evidence_store" in name
            for name in imported
        )
        for forbidden in (
            "EvidenceRecordStore",
            "EvidenceStoreTransaction",
            "open(",
            "Path(",
            "read_log(",
            "read_record(",
            "inspect_canonical_page",
            "subprocess",
        ):
            assert forbidden not in source
    assert set(restore_replay.__all__) == {
        "build_subjective_mem_restore_replay_plan",
        "subjective_mem_restore_page_binding",
        "subjective_mem_restore_page_predecessor",
    }
    assert set(restore_plan.__all__) == {
        "SubjectiveMemRestorePlanInputs",
        "SubjectiveMemRestorePreparedOperation",
        "build_subjective_mem_restore_final_records",
        "build_subjective_mem_restore_lifecycle_plan",
        "build_subjective_mem_restore_prepared_intent",
        "build_subjective_mem_restore_prepared_operation",
        "subjective_mem_restore_current_state",
        "subjective_mem_restore_predecessor_exact",
        "subjective_mem_restore_predecessor_expectation",
        "subjective_mem_restore_tombstone_exact",
        "subjective_mem_restore_workspace_authority_digest",
    }


def test_restore_plan_builder_is_deterministic(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    first, reasons, _identity, _at = _prepared_plan(
        lifecycle_env, proposal, key="determinism"
    )
    assert first is not None, reasons
    second, reasons, _identity, _at = _prepared_plan(
        lifecycle_env, proposal, key="determinism"
    )
    assert second is not None, reasons
    assert first.plan == second.plan
    assert first.plan.prepared_intent == second.plan.prepared_intent
    assert first.plan.record_bindings == second.plan.record_bindings
    assert first.plan.log_bindings == second.plan.log_bindings
    assert validate_lifecycle_plan(second.plan) == ()


def _record(env, kind: str, record_id: str):
    return env["store"].read_record(
        evidence_space_id=env["captured"].evidence_space_id,
        record_kind=kind,
        record_id=record_id,
    )


def _log(env, kind: str, key: str):
    return env["store"].read_log(
        evidence_space_id=env["captured"].evidence_space_id,
        log_kind=kind,
        key=key,
    )


def test_restore_fresh_apply_publishes_hidden_to_active_successor(
    lifecycle_env,
) -> None:
    forgotten, proposal = _proposal(lifecycle_env)
    tombstone_before = _record(
        lifecycle_env, "subjective_mem_forget_tombstone", forgotten.tombstone_id
    )
    forget_receipt_before = _record(
        lifecycle_env,
        "subjective_mem_lifecycle_receipt",
        proposal.expected_current_receipt_id,
    )

    result = _restore(lifecycle_env, proposal, apply=True, key="fresh-apply")
    assert result.status == "committed", result.blocked_reasons
    assert result.from_revision == 2 and result.to_revision == 3
    assert result.canonical_markdown_published is True
    assert result.lifecycle_receipt_present is True
    assert result.tombstone_release_present is True
    assert result.persisted is True
    assert result.current_state is not None
    assert result.current_state.current_revision == 3
    assert result.current_state.lifecycle_state == "active"
    assert result.current_state.mutation_state == "none"
    assert result.current_state.retrieval_eligible is True

    page, reasons = parse_subjective_mem_page_bytes(
        lifecycle_env["page_path"].read_bytes()
    )
    assert page is not None and not reasons
    revisions = [item.revision for item in page.blocks]
    assert [item.memory_revision for item in revisions] == [1, 2, 3]
    assert [item.lifecycle_state for item in revisions] == ["active", "hidden", "active"]
    assert revisions[1].to_dict() == next(
        item.revision for item in page.blocks if item.revision.memory_revision == 2
    ).to_dict()

    # the original Forget authority stays immutable
    assert _record(
        lifecycle_env, "subjective_mem_forget_tombstone", forgotten.tombstone_id
    ) == tombstone_before
    assert _record(
        lifecycle_env,
        "subjective_mem_lifecycle_receipt",
        proposal.expected_current_receipt_id,
    ) == forget_receipt_before


def test_restore_fresh_apply_persists_exact_final_records(lifecycle_env) -> None:
    forgotten, proposal = _proposal(lifecycle_env)
    result = _restore(lifecycle_env, proposal, apply=True, key="final-records")
    assert result.status == "committed", result.blocked_reasons

    transition = _record(
        lifecycle_env, "subjective_mem_lifecycle_transition", result.transition_id
    )
    assert isinstance(transition, dict)
    assert transition["operation"] == "restore"
    assert transition["from_lifecycle_state"] == "hidden"
    assert transition["to_lifecycle_state"] == "active"
    assert transition["to_revision"] == 3

    receipt = _record(
        lifecycle_env, "subjective_mem_lifecycle_receipt", result.receipt_id
    )
    assert isinstance(receipt, dict)
    assert receipt["operation_kind"] == "restore"
    assert receipt["operation_outcome"] == "committed"
    assert receipt["release_id"] == result.release_id
    assert receipt["tombstone_id"] == forgotten.tombstone_id
    assert receipt["projection_state"] == "rebuild_required"
    assert receipt["receipt_digest"] == canonical_digest(
        {key: value for key, value in receipt.items() if key != "receipt_digest"}
    )

    release = _record(
        lifecycle_env, "subjective_mem_forget_tombstone_release", result.release_id
    )
    assert isinstance(release, dict)
    assert release["restore_receipt_id"] == result.receipt_id
    assert release["restore_transition_id"] == result.transition_id
    assert release["content_free"] is True

    release_state = _log(
        lifecycle_env,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        forgotten.tombstone_id,
    )
    assert isinstance(release_state, list) and len(release_state) == 1
    assert release_state[0]["release_id"] == result.release_id
    assert release_state[0]["effective"] is True

    selector = _log(
        lifecycle_env, "subjective_mem_current_state", proposal.expected_current_selector_id
    )
    assert isinstance(selector, list) and len(selector) == 1
    assert selector[0]["current_revision"] == 3
    assert selector[0]["lifecycle_state"] == "active"
    assert selector[0]["retrieval_eligible"] is True

    tombstone_state = _log(
        lifecycle_env,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        proposal.expected_semantic_identity_digest,
    )
    assert isinstance(tombstone_state, list) and len(tombstone_state) == 1


def test_restore_apply_result_projection_stays_content_free(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    raw_key = "caller-secret-apply-key"
    result = _restore(lifecycle_env, proposal, apply=True, key=raw_key)
    assert result.status == "committed", result.blocked_reasons
    text = json.dumps(result.to_log_dict())
    assert result.to_log_dict()["content_free"] is True
    assert result.to_log_dict()["tombstone_release_present"] is True
    for forbidden in (
        raw_key,
        str(lifecycle_env["workspace_root"]),
        "I felt relieved",
        result.post_image_digest or "sha256:absent",
    ):
        assert forbidden not in text


def test_restore_existing_slot_never_reserves_again(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared, reasons, identity, _at = _prepared_plan(
        lifecycle_env, proposal, key="existing-slot"
    )
    assert prepared is not None, reasons
    plan = prepared.plan
    space = lifecycle_env["captured"].evidence_space_id
    before_page = lifecycle_env["page_path"].read_bytes()

    conflicting = {"input_digest": "conflicting-digest", "schema": "claim"}
    written = lifecycle_env["store"].write_record(
        evidence_space_id=space,
        record_kind="subjective_mem_lifecycle_claim",
        record_id=plan.operation_slot_id,
        payload=conflicting,
    )
    assert written.status == "created"
    conflict = _restore(lifecycle_env, proposal, apply=True, key="existing-slot")
    assert conflict.status == "integrity_conflict"
    assert conflict.canonical_markdown_published is False
    assert conflict.tombstone_release_present is False
    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _record(lifecycle_env, "subjective_mem_lifecycle_intent", plan.intent_id) is None


def test_restore_reservation_or_finalizer_failure_never_commits(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared, reasons, identity, _at = _prepared_plan(
        lifecycle_env, proposal, key="engine-failure"
    )
    assert prepared is not None, reasons
    before_page = lifecycle_env["page_path"].read_bytes()

    broken_plan = replace(prepared.plan, post_image_digest="sha256:" + "0" * 64)
    reservation = restore_runtime._apply(  # noqa: SLF001
        lifecycle_env["store"],
        replace(prepared, plan=broken_plan),
        identity=identity,
        proposal=proposal,
    )
    assert reservation.status != "committed"
    assert reservation.canonical_markdown_published is False
    assert reservation.tombstone_release_present is False
    assert lifecycle_env["page_path"].read_bytes() == before_page

    unbound = replace(
        prepared.plan,
        record_bindings=tuple(
            binding
            for binding in prepared.plan.record_bindings
            if binding[0] != "subjective_mem_forget_tombstone"
        ),
    )
    finalizer = restore_runtime._apply(  # noqa: SLF001
        lifecycle_env["store"],
        replace(prepared, plan=unbound),
        identity=identity,
        proposal=proposal,
    )
    assert finalizer.status != "committed"
    assert finalizer.tombstone_release_present is False
    assert _log(
        lifecycle_env,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        proposal.expected_forget_tombstone_id,
    ) in (None, [])


def _committed_restore(env, *, key="replay-operation"):
    _forgotten, proposal = _proposal(env)
    first = _restore(env, proposal, apply=True, key=key)
    assert first.status == "committed", first.blocked_reasons
    return proposal, first


def test_restore_exact_repeat_replays_without_another_revision(lifecycle_env) -> None:
    proposal, first = _committed_restore(lifecycle_env)
    page_after_commit = lifecycle_env["page_path"].read_bytes()
    files_after_commit = _store_files(lifecycle_env)
    release_after_commit = _log(
        lifecycle_env,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        proposal.expected_forget_tombstone_id,
    )
    tombstone_after_commit = _record(
        lifecycle_env, "subjective_mem_forget_tombstone",
        proposal.expected_forget_tombstone_id,
    )
    forget_receipt_after_commit = _record(
        lifecycle_env, "subjective_mem_lifecycle_receipt",
        proposal.expected_current_receipt_id,
    )

    replay = _restore(lifecycle_env, proposal, apply=True, key="replay-operation")
    assert replay.status == "duplicate_finalized", replay.blocked_reasons
    assert replay.recovery_outcome == "exact_replay"
    assert replay.transition_id == first.transition_id
    assert replay.receipt_id == first.receipt_id
    assert replay.release_id == first.release_id
    assert replay.canonical_markdown_published is True
    assert replay.lifecycle_receipt_present is True
    assert replay.tombstone_release_present is True
    assert replay.persisted is True
    assert replay.current_state is not None
    assert replay.current_state.current_revision == 3
    assert replay.current_state.lifecycle_state == "active"
    assert replay.current_state.retrieval_eligible is True

    assert lifecycle_env["page_path"].read_bytes() == page_after_commit
    assert _store_files(lifecycle_env) == files_after_commit
    page, reasons = parse_subjective_mem_page_bytes(page_after_commit)
    assert page is not None and not reasons
    assert [item.revision.memory_revision for item in page.blocks] == [1, 2, 3]
    assert _log(
        lifecycle_env,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        proposal.expected_forget_tombstone_id,
    ) == release_after_commit
    assert len(release_after_commit) == 1
    assert _record(
        lifecycle_env, "subjective_mem_forget_tombstone",
        proposal.expected_forget_tombstone_id,
    ) == tombstone_after_commit
    assert _record(
        lifecycle_env, "subjective_mem_lifecycle_receipt",
        proposal.expected_current_receipt_id,
    ) == forget_receipt_after_commit


def test_restore_replay_conflicts_on_changed_input_digest(lifecycle_env) -> None:
    proposal, _first = _committed_restore(lifecycle_env, key="replay-conflict")
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)

    changed = replace(proposal, authorization_id="user-restore-authorization-2")
    conflict = _restore(lifecycle_env, changed, apply=True, key="replay-conflict")
    assert conflict.status == "integrity_conflict"
    assert conflict.tombstone_release_present is False
    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _store_files(lifecycle_env) == before_files


def test_restore_replay_with_other_idempotency_key_does_not_replay(
    lifecycle_env,
) -> None:
    proposal, _first = _committed_restore(lifecycle_env, key="replay-key-a")
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)

    other = _restore(lifecycle_env, proposal, apply=True, key="replay-key-b")
    assert other.status == "fail_closed"
    assert other.recovery_outcome != "exact_replay"
    assert other.tombstone_release_present is False
    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _store_files(lifecycle_env) == before_files


def test_restore_replay_fails_closed_on_changed_durable_authority(
    lifecycle_env,
) -> None:
    proposal, first = _committed_restore(lifecycle_env, key="replay-authority")
    space = lifecycle_env["captured"].evidence_space_id
    before_page = lifecycle_env["page_path"].read_bytes()

    cases = (
        ("subjective_mem_forget_tombstone", proposal.expected_forget_tombstone_id),
        ("subjective_mem_lifecycle_receipt", proposal.expected_current_receipt_id),
        ("subjective_mem_lifecycle_intent", first.transition_id.replace(
            "smrestoretransition", "smrestoreintent"
        )),
        ("subjective_mem_forget_tombstone_release", first.release_id),
        ("subjective_mem_lifecycle_transition", first.transition_id),
        ("subjective_mem_lifecycle_receipt", first.receipt_id),
    )
    for index, (kind, record_id) in enumerate(cases):
        path = lifecycle_env["store"]._record_path(space, kind, record_id)  # noqa: SLF001
        if not path.exists():
            continue
        saved = path.read_text(encoding="utf-8")
        path.unlink()
        blocked = _restore(
            lifecycle_env, proposal, apply=True, key="replay-authority"
        )
        assert blocked.status in {"fail_closed", "integrity_conflict"}, (
            f"case {index} {kind} returned {blocked.status}"
        )
        assert blocked.recovery_outcome != "exact_replay"
        assert lifecycle_env["page_path"].read_bytes() == before_page
        path.write_text(saved, encoding="utf-8")

    restored = _restore(lifecycle_env, proposal, apply=True, key="replay-authority")
    assert restored.status == "duplicate_finalized", restored.blocked_reasons


def test_restore_replay_fails_closed_on_changed_release_or_page(lifecycle_env) -> None:
    proposal, _first = _committed_restore(lifecycle_env, key="replay-release")
    space = lifecycle_env["captured"].evidence_space_id
    before_page = lifecycle_env["page_path"].read_bytes()

    lifecycle_env["page_path"].write_text("# foreign\n", encoding="utf-8")
    foreign = _restore(lifecycle_env, proposal, apply=True, key="replay-release")
    assert foreign.status == "fail_closed"
    assert foreign.recovery_outcome != "exact_replay"
    lifecycle_env["page_path"].write_bytes(before_page)

    release_log = lifecycle_env["store"]._log_path(  # noqa: SLF001
        space,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        proposal.expected_forget_tombstone_id,
    )
    saved = release_log.read_text(encoding="utf-8")
    release_log.unlink()
    missing_release = _restore(
        lifecycle_env, proposal, apply=True, key="replay-release"
    )
    assert missing_release.status == "fail_closed"
    assert missing_release.recovery_outcome != "exact_replay"
    assert lifecycle_env["page_path"].read_bytes() == before_page
    release_log.write_text(saved, encoding="utf-8")

    assert _restore(
        lifecycle_env, proposal, apply=True, key="replay-release"
    ).status == "duplicate_finalized"


def test_restore_prepared_claim_dry_run_is_no_write_recovery_pending(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    # an exact reservation written by the shared engine, not a hand-built claim
    _reserved(lifecycle_env, proposal, key="prepared-claim")
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)

    pending = _restore(lifecycle_env, proposal, apply=False, key="prepared-claim")
    assert pending.status == "recovery_pending", pending.blocked_reasons
    assert pending.recovery_outcome == "pre_image_pending_publication"
    assert pending.blocked_reasons == (
        "subjective_mem_restore_prepared_recovery_required",
    )
    assert pending.canonical_markdown_published is False
    assert pending.lifecycle_receipt_present is False
    assert pending.tombstone_release_present is False
    assert pending.persisted is True
    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _store_files(lifecycle_env) == before_files
    assert _release_events(lifecycle_env, proposal) in (None, [])

    # the same exact reservation still recovers forward once apply is enabled
    recovered = _restore(lifecycle_env, proposal, apply=True, key="prepared-claim")
    assert recovered.status == "committed", recovered.blocked_reasons


def test_restore_no_apply_pending_requires_exact_durable_authority(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared = _reserved(lifecycle_env, proposal, key="pending-linkage")
    space = lifecycle_env["captured"].evidence_space_id
    plan = prepared.plan
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)

    cases = (
        ("subjective_mem_lifecycle_claim", plan.operation_slot_id, "claimed_at"),
        ("subjective_mem_lifecycle_intent", plan.intent_id, "prepared_at"),
    )
    for kind, record_id, field in cases:
        original = _record(lifecycle_env, kind, record_id)
        assert isinstance(original, dict)
        # the alteration keeps the exact input digest, so this is not a conflict
        assert original["input_digest"] == plan.input_digest
        path = lifecycle_env["store"]._record_path(space, kind, record_id)  # noqa: SLF001
        saved = path.read_text(encoding="utf-8")
        path.unlink()
        written = lifecycle_env["store"].write_record(
            evidence_space_id=space, record_kind=kind, record_id=record_id,
            payload={**original, field: "2020-01-01T00:00:00+00:00"},
        )
        assert written.status == "created"

        blocked = _restore(
            lifecycle_env, proposal, apply=False, key="pending-linkage"
        )
        assert blocked.status == "fail_closed", f"{kind} returned {blocked.status}"
        assert blocked.recovery_outcome is None
        assert blocked.canonical_markdown_published is False
        assert blocked.lifecycle_receipt_present is False
        assert blocked.tombstone_release_present is False
        assert lifecycle_env["page_path"].read_bytes() == before_page
        assert _store_files(lifecycle_env) == before_files
        assert _release_events(lifecycle_env, proposal) in (None, [])
        path.unlink()
        path.write_text(saved, encoding="utf-8")

    restored = _restore(lifecycle_env, proposal, apply=False, key="pending-linkage")
    assert restored.status == "recovery_pending", restored.blocked_reasons
    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _store_files(lifecycle_env) == before_files


def test_restore_replay_fails_closed_on_altered_tombstone_state_event(
    lifecycle_env,
) -> None:
    proposal, first = _committed_restore(lifecycle_env, key="replay-state")
    space = lifecycle_env["captured"].evidence_space_id
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)
    events = _log(
        lifecycle_env,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        proposal.expected_semantic_identity_digest,
    )
    assert isinstance(events, list) and len(events) == 1
    original = events[0]

    for field, value in (
        ("updated_at", "2020-01-01T00:00:00+00:00"),
        ("formation_stage", "consolidated"),
        ("transition_digest", "d" * 64),
        ("receipt_id", "smfreceipt_foreign"),
        ("effective", False),
        ("superseded_by_tombstone_id_or_null", original["tombstone_id"]),
        ("content_free", False),
        ("hidden_revision", 99),
    ):
        altered = {**original, field: value}
        assert altered["tombstone_id"] == original["tombstone_id"]
        written = lifecycle_env["store"].write_log(
            evidence_space_id=space,
            log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
            key=proposal.expected_semantic_identity_digest,
            events=(altered,),
        )
        assert written.status in {"created", "replaced", "duplicate_existing"}

        blocked = _restore(lifecycle_env, proposal, apply=True, key="replay-state")
        assert blocked.status == "fail_closed", f"{field} returned {blocked.status}"
        assert blocked.recovery_outcome != "exact_replay"
        assert blocked.tombstone_release_present is False
        assert lifecycle_env["page_path"].read_bytes() == before_page
        assert _store_files(lifecycle_env) == before_files
        page, reasons = parse_subjective_mem_page_bytes(before_page)
        assert page is not None and not reasons
        assert [item.revision.memory_revision for item in page.blocks] == [1, 2, 3]
        release_state = _log(
            lifecycle_env,
            SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
            proposal.expected_forget_tombstone_id,
        )
        assert isinstance(release_state, list) and len(release_state) == 1
        assert release_state[0]["release_id"] == first.release_id

    restored = lifecycle_env["store"].write_log(
        evidence_space_id=space,
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        key=proposal.expected_semantic_identity_digest,
        events=(original,),
    )
    assert restored.status in {"created", "replaced", "duplicate_existing"}
    assert _restore(
        lifecycle_env, proposal, apply=True, key="replay-state"
    ).status == "duplicate_finalized"


def _reserved(env, proposal, *, key):
    """Reserve one exact Restore publication through the shared engine only."""

    prepared, reasons, _identity, _at = _prepared_plan(env, proposal, key=key)
    assert prepared is not None, reasons
    reserved = reserve_lifecycle_publication(
        store=env["store"], plan=prepared.plan,
        post_image=prepared.page.rendered_bytes,
    )
    assert reserved.status == "reserved", reserved.reasons
    return prepared


def _artifact_path(env, artifact_id: str):
    return env["workspace_root"].joinpath(
        env["authority"].character_id, *ARTIFACT_DIRECTORY_PARTS, artifact_id + ".md"
    )


def _revisions(page_bytes: bytes) -> list[int]:
    page, reasons = parse_subjective_mem_page_bytes(page_bytes)
    assert page is not None and not reasons
    return [item.revision.memory_revision for item in page.blocks]


def _release_events(env, proposal):
    return _log(
        env,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        proposal.expected_forget_tombstone_id,
    )


def test_restore_recovers_reserved_pre_image_to_one_committed_successor(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared = _reserved(lifecycle_env, proposal, key="recover-pre-image")
    assert _release_events(lifecycle_env, proposal) in (None, [])

    recovered = _restore(
        lifecycle_env, proposal, apply=True, key="recover-pre-image"
    )
    assert recovered.status == "committed", recovered.blocked_reasons
    assert recovered.recovery_outcome == "published_and_finalized"
    assert recovered.canonical_markdown_published is True
    assert recovered.lifecycle_receipt_present is True
    assert recovered.tombstone_release_present is True
    assert recovered.persisted is True
    assert recovered.current_state is not None
    assert recovered.current_state.current_revision == 3
    assert recovered.current_state.lifecycle_state == "active"
    assert recovered.current_state.mutation_state == "none"
    assert recovered.current_state.retrieval_eligible is True

    page_bytes = lifecycle_env["page_path"].read_bytes()
    assert page_bytes == prepared.page.rendered_bytes
    assert _revisions(page_bytes) == [1, 2, 3]
    release = _release_events(lifecycle_env, proposal)
    assert isinstance(release, list) and len(release) == 1
    assert release[0]["release_id"] == recovered.release_id
    assert _record(
        lifecycle_env, "subjective_mem_lifecycle_receipt", recovered.receipt_id
    ) is not None


def test_restore_recovers_installed_post_image_without_another_revision(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared = _reserved(lifecycle_env, proposal, key="recover-post-image")
    # the successor page is already installed; only the final records are missing
    lifecycle_env["page_path"].write_bytes(prepared.page.rendered_bytes)

    recovered = _restore(
        lifecycle_env, proposal, apply=True, key="recover-post-image"
    )
    assert recovered.status == "committed", recovered.blocked_reasons
    assert recovered.recovery_outcome == "post_image_rolled_forward"
    assert recovered.canonical_markdown_published is True
    assert recovered.tombstone_release_present is True
    assert lifecycle_env["page_path"].read_bytes() == prepared.page.rendered_bytes
    assert _revisions(lifecycle_env["page_path"].read_bytes()) == [1, 2, 3]
    release = _release_events(lifecycle_env, proposal)
    assert isinstance(release, list) and len(release) == 1


def test_restore_repeat_after_recovery_replays_without_new_state(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    _reserved(lifecycle_env, proposal, key="recover-then-replay")
    first = _restore(
        lifecycle_env, proposal, apply=True, key="recover-then-replay"
    )
    assert first.status == "committed", first.blocked_reasons
    page_after = lifecycle_env["page_path"].read_bytes()
    files_after = _store_files(lifecycle_env)
    release_after = _release_events(lifecycle_env, proposal)

    again = _restore(
        lifecycle_env, proposal, apply=True, key="recover-then-replay"
    )
    assert again.status == "duplicate_finalized", again.blocked_reasons
    assert again.recovery_outcome == "exact_replay"
    assert again.transition_id == first.transition_id
    assert again.receipt_id == first.receipt_id
    assert again.release_id == first.release_id
    assert again.tombstone_release_present is True
    assert lifecycle_env["page_path"].read_bytes() == page_after
    assert _store_files(lifecycle_env) == files_after
    assert _revisions(page_after) == [1, 2, 3]
    assert _release_events(lifecycle_env, proposal) == release_after
    assert len(release_after) == 1


def test_restore_recovery_requires_exact_claim_and_intent(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared = _reserved(lifecycle_env, proposal, key="recover-linkage")
    space = lifecycle_env["captured"].evidence_space_id
    plan = prepared.plan
    before_page = lifecycle_env["page_path"].read_bytes()

    cases = (
        ("subjective_mem_lifecycle_claim", plan.operation_slot_id, "claimed_at"),
        ("subjective_mem_lifecycle_intent", plan.intent_id, "prepared_at"),
    )
    for kind, record_id, field in cases:
        original = _record(lifecycle_env, kind, record_id)
        assert isinstance(original, dict) and field in original
        path = lifecycle_env["store"]._record_path(space, kind, record_id)  # noqa: SLF001
        saved = path.read_text(encoding="utf-8")
        path.unlink()
        written = lifecycle_env["store"].write_record(
            evidence_space_id=space, record_kind=kind, record_id=record_id,
            payload={**original, field: "2020-01-01T00:00:00+00:00"},
        )
        assert written.status == "created"

        blocked = _restore(
            lifecycle_env, proposal, apply=True, key="recover-linkage"
        )
        assert blocked.status in {"fail_closed", "recovery_required"}, (
            f"{kind} returned {blocked.status}"
        )
        assert blocked.canonical_markdown_published is False
        assert blocked.tombstone_release_present is False
        assert lifecycle_env["page_path"].read_bytes() == before_page
        assert _release_events(lifecycle_env, proposal) in (None, [])
        path.unlink()
        path.write_text(saved, encoding="utf-8")

    conflicting = _restore(lifecycle_env, proposal, apply=True, key="recover-linkage")
    assert conflicting.status == "committed", conflicting.blocked_reasons


def test_restore_recovery_requires_unchanged_forget_authority(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    _reserved(lifecycle_env, proposal, key="recover-forget")
    space = lifecycle_env["captured"].evidence_space_id
    before_page = lifecycle_env["page_path"].read_bytes()

    records = (
        ("subjective_mem_forget_tombstone", proposal.expected_forget_tombstone_id),
        ("subjective_mem_lifecycle_receipt", proposal.expected_current_receipt_id),
    )
    for kind, record_id in records:
        path = lifecycle_env["store"]._record_path(space, kind, record_id)  # noqa: SLF001
        saved = path.read_text(encoding="utf-8")
        path.unlink()
        blocked = _restore(lifecycle_env, proposal, apply=True, key="recover-forget")
        assert blocked.status in {"fail_closed", "recovery_required"}, (
            f"{kind} returned {blocked.status}"
        )
        assert blocked.canonical_markdown_published is False
        assert blocked.tombstone_release_present is False
        assert lifecycle_env["page_path"].read_bytes() == before_page
        path.write_text(saved, encoding="utf-8")

    events = _log(
        lifecycle_env,
        SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        proposal.expected_semantic_identity_digest,
    )
    assert isinstance(events, list) and len(events) == 1
    original = events[0]
    for field, value in (
        ("hidden_revision", 99),
        ("effective", False),
        ("transition_digest", "e" * 64),
        ("content_free", False),
    ):
        written = lifecycle_env["store"].write_log(
            evidence_space_id=space,
            log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
            key=proposal.expected_semantic_identity_digest,
            events=({**original, field: value},),
        )
        assert written.status in {"created", "replaced", "duplicate_existing"}
        blocked = _restore(lifecycle_env, proposal, apply=True, key="recover-forget")
        assert blocked.status == "fail_closed", f"{field} returned {blocked.status}"
        assert blocked.canonical_markdown_published is False
        assert lifecycle_env["page_path"].read_bytes() == before_page
        assert _release_events(lifecycle_env, proposal) in (None, [])

    restored = lifecycle_env["store"].write_log(
        evidence_space_id=space,
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        key=proposal.expected_semantic_identity_digest,
        events=(original,),
    )
    assert restored.status in {"created", "replaced", "duplicate_existing"}
    assert _restore(
        lifecycle_env, proposal, apply=True, key="recover-forget"
    ).status == "committed"


def test_restore_recovery_requires_the_immutable_prepared_artifact(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared = _reserved(lifecycle_env, proposal, key="recover-artifact")
    artifact = _artifact_path(lifecycle_env, prepared.plan.artifact_id)
    assert artifact.is_file()
    saved = artifact.read_bytes()
    before_page = lifecycle_env["page_path"].read_bytes()

    artifact.unlink()
    missing = _restore(lifecycle_env, proposal, apply=True, key="recover-artifact")
    assert missing.status == "recovery_required"
    assert missing.recovery_outcome == "artifact_unavailable"
    assert missing.canonical_markdown_published is False
    assert missing.tombstone_release_present is False
    assert lifecycle_env["page_path"].read_bytes() == before_page

    artifact.write_bytes(b"# corrupt\n")
    corrupt = _restore(lifecycle_env, proposal, apply=True, key="recover-artifact")
    assert corrupt.status == "recovery_required"
    assert corrupt.recovery_outcome == "artifact_unavailable"
    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _release_events(lifecycle_env, proposal) in (None, [])

    artifact.unlink()
    artifact.write_bytes(saved)
    assert _restore(
        lifecycle_env, proposal, apply=True, key="recover-artifact"
    ).status == "committed"


def test_restore_recovery_preserves_a_foreign_canonical_page(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    _reserved(lifecycle_env, proposal, key="recover-foreign")
    foreign = b"# foreign page\n"
    lifecycle_env["page_path"].write_bytes(foreign)

    blocked = _restore(lifecycle_env, proposal, apply=True, key="recover-foreign")
    assert blocked.status == "recovery_required"
    assert blocked.recovery_outcome == "foreign_image"
    assert blocked.canonical_markdown_published is False
    assert blocked.lifecycle_receipt_present is False
    assert blocked.tombstone_release_present is False
    assert lifecycle_env["page_path"].read_bytes() == foreign
    assert _release_events(lifecycle_env, proposal) in (None, [])


def test_restore_recovery_fails_closed_on_a_duplicate_logical_selector(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    _reserved(lifecycle_env, proposal, key="recover-duplicate")
    space = lifecycle_env["captured"].evidence_space_id
    before_page = lifecycle_env["page_path"].read_bytes()
    events = _log(
        lifecycle_env, "subjective_mem_current_state",
        proposal.expected_current_selector_id,
    )
    assert isinstance(events, list) and len(events) == 1

    written = lifecycle_env["store"].write_log(
        evidence_space_id=space,
        log_kind="subjective_mem_current_state",
        key=proposal.expected_current_selector_id + "duplicate",
        events=({**events[0], "memory_state_id": "smstate_duplicate"},),
    )
    assert written.status in {"created", "replaced", "duplicate_existing"}

    blocked = _restore(lifecycle_env, proposal, apply=True, key="recover-duplicate")
    assert blocked.status == "fail_closed"
    assert blocked.blocked_reasons == (
        "subjective_mem_lifecycle_duplicate_logical_current_selector",
    )
    assert blocked.canonical_markdown_published is False
    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _release_events(lifecycle_env, proposal) in (None, [])


def test_restore_recovery_rejects_partial_final_authority(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared = _reserved(lifecycle_env, proposal, key="recover-partial")
    space = lifecycle_env["captured"].evidence_space_id
    written = lifecycle_env["store"].write_record(
        evidence_space_id=space,
        record_kind="subjective_mem_lifecycle_transition",
        record_id=prepared.plan.transition_id,
        payload={"schema": "foreign", "transition_id": prepared.plan.transition_id},
    )
    assert written.status == "created"

    blocked = _restore(lifecycle_env, proposal, apply=True, key="recover-partial")
    assert blocked.status not in {"committed", "duplicate_finalized"}
    assert blocked.lifecycle_receipt_present is False
    assert blocked.tombstone_release_present is False
    assert _release_events(lifecycle_env, proposal) in (None, [])
    assert _record(
        lifecycle_env, "subjective_mem_lifecycle_receipt", prepared.plan.receipt_id
    ) is None


def test_restore_recovery_projection_stays_content_free(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    raw_key = "caller-secret-recovery-key"
    _reserved(lifecycle_env, proposal, key=raw_key)

    recovered = _restore(lifecycle_env, proposal, apply=True, key=raw_key)
    assert recovered.status == "committed", recovered.blocked_reasons
    projection = recovered.to_log_dict()
    text = json.dumps(projection)
    assert projection["content_free"] is True
    assert projection["background_recovery_started"] is False
    assert projection["ordinary_retrieval_wired"] is False
    assert projection["primary_mem_migrated"] is False
    assert projection["digest_values_included"] is False
    assert projection["raw_key_included"] is False
    assert projection["recovery_outcome"] == "published_and_finalized"
    for forbidden in (
        raw_key,
        str(lifecycle_env["workspace_root"]),
        "I felt relieved",
        recovered.post_image_digest or "sha256:absent",
        proposal.expected_semantic_identity_digest,
    ):
        assert forbidden not in text


_PREDECESSOR_BINDING_KINDS = [
    "evidence_space_descriptor",
    "subjective_mem_lifecycle_receipt",
    "subjective_mem_lifecycle_transition",
    "subjective_mem_forget_tombstone",
]


def _record_file(env, kind: str, record_id: str):
    return env["store"]._record_path(  # noqa: SLF001
        env["captured"].evidence_space_id, kind, record_id
    )


def _predecessor_binding_cases(proposal):
    """Missing and altered forms of the two bindings replay must revalidate."""

    transition_id = proposal.expected_forget_transition_id
    stale = "2020-01-01T00:00:00+00:00"
    return (
        ("evidence_space_descriptor", "revision-1", None, None),
        ("evidence_space_descriptor", "revision-1", "created_at", stale),
        ("evidence_space_descriptor", "revision-1", "retired_at_or_null", stale),
        ("subjective_mem_lifecycle_transition", transition_id, None, None),
        ("subjective_mem_lifecycle_transition", transition_id, "committed_at", stale),
        ("subjective_mem_lifecycle_transition", transition_id, "operation", "correct"),
    )


def _with_broken_binding(env, kind: str, record_id: str, field, value):
    """Delete or alter one durable binding in place and return its exact text."""

    space = env["captured"].evidence_space_id
    path = _record_file(env, kind, record_id)
    saved = path.read_text(encoding="utf-8")
    original = _record(env, kind, record_id)
    assert isinstance(original, dict)
    path.unlink()
    if field is not None:
        written = env["store"].write_record(
            evidence_space_id=space, record_kind=kind, record_id=record_id,
            payload={**original, field: value},
        )
        assert written.status == "created"
        # the record ID is unchanged, so only the reconstruction can reject it
        assert _record(env, kind, record_id) != original
    return saved


def _restore_binding(env, kind: str, record_id: str, saved: str) -> None:
    path = _record_file(env, kind, record_id)
    if path.exists():
        path.unlink()
    path.write_text(saved, encoding="utf-8")


def test_restore_durable_plan_rebinds_the_exact_four_predecessor_records(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    prepared, reasons, identity, _at = _prepared_plan(
        lifecycle_env, proposal, key="binding-shape"
    )
    assert prepared is not None, reasons
    reserved = reserve_lifecycle_publication(
        store=lifecycle_env["store"], plan=prepared.plan,
        post_image=prepared.page.rendered_bytes,
    )
    assert reserved.status == "reserved", reserved.reasons
    fresh = prepared.plan
    assert [kind for kind, _id, _body in fresh.record_bindings] == (
        _PREDECESSOR_BINDING_KINDS
    )

    intent = _record(
        lifecycle_env, "subjective_mem_lifecycle_intent", fresh.intent_id
    )
    rebuilt, reasons = restore_runtime._durable_plan(  # noqa: SLF001
        lifecycle_env["store"],
        lifecycle_env["captured"].evidence_space_id,
        lifecycle_env["authority"],
        str(lifecycle_env["workspace_root"]),
        intent=intent, identity=identity, proposal=proposal,
    )
    assert rebuilt is not None, reasons
    # the reconstruction is the originally reserved plan, binding for binding
    assert rebuilt.record_bindings == fresh.record_bindings
    assert rebuilt.log_bindings == fresh.log_bindings
    assert rebuilt.prepared_intent == fresh.prepared_intent


def test_restore_recovery_requires_exact_predecessor_bindings(lifecycle_env) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    _reserved(lifecycle_env, proposal, key="recover-bindings")
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)

    for kind, record_id, field, value in _predecessor_binding_cases(proposal):
        saved = _with_broken_binding(
            lifecycle_env, kind, record_id, field, value
        )
        for apply_enabled in (False, True):
            blocked = _restore(
                lifecycle_env, proposal, apply=apply_enabled, key="recover-bindings"
            )
            assert blocked.status == "fail_closed", (
                f"{kind}/{field} apply={apply_enabled} -> {blocked.status}"
            )
            assert blocked.recovery_outcome is None
            assert blocked.canonical_markdown_published is False
            assert blocked.lifecycle_receipt_present is False
            assert blocked.tombstone_release_present is False
            assert lifecycle_env["page_path"].read_bytes() == before_page
            assert _release_events(lifecycle_env, proposal) in (None, [])
        _restore_binding(lifecycle_env, kind, record_id, saved)
        assert _store_files(lifecycle_env) == before_files

    recovered = _restore(
        lifecycle_env, proposal, apply=True, key="recover-bindings"
    )
    assert recovered.status == "committed", recovered.blocked_reasons
    assert _revisions(lifecycle_env["page_path"].read_bytes()) == [1, 2, 3]
    release = _release_events(lifecycle_env, proposal)
    assert isinstance(release, list) and len(release) == 1


def test_restore_replay_requires_exact_predecessor_bindings(lifecycle_env) -> None:
    proposal, first = _committed_restore(lifecycle_env, key="replay-bindings")
    page_after = lifecycle_env["page_path"].read_bytes()
    files_after = _store_files(lifecycle_env)
    release_after = _release_events(lifecycle_env, proposal)

    for kind, record_id, field, value in _predecessor_binding_cases(proposal):
        saved = _with_broken_binding(
            lifecycle_env, kind, record_id, field, value
        )
        for apply_enabled in (False, True):
            blocked = _restore(
                lifecycle_env, proposal, apply=apply_enabled, key="replay-bindings"
            )
            assert blocked.status == "fail_closed", (
                f"{kind}/{field} apply={apply_enabled} -> {blocked.status}"
            )
            assert blocked.recovery_outcome != "exact_replay"
            assert blocked.tombstone_release_present is False
            assert lifecycle_env["page_path"].read_bytes() == page_after
            assert _release_events(lifecycle_env, proposal) == release_after
        _restore_binding(lifecycle_env, kind, record_id, saved)
        assert _store_files(lifecycle_env) == files_after

    for apply_enabled in (False, True):
        replay = _restore(
            lifecycle_env, proposal, apply=apply_enabled, key="replay-bindings"
        )
        assert replay.status == "duplicate_finalized", replay.blocked_reasons
        assert replay.recovery_outcome == "exact_replay"
        assert replay.release_id == first.release_id
    assert lifecycle_env["page_path"].read_bytes() == page_after
    assert _store_files(lifecycle_env) == files_after
    assert _revisions(page_after) == [1, 2, 3]
    assert _release_events(lifecycle_env, proposal) == release_after
    assert len(release_after) == 1


def _uninspected_binding_cases(proposal):
    """Fields no lineage comparison selects, altered while the digest is kept."""

    return (
        (
            "subjective_mem_lifecycle_receipt",
            proposal.expected_current_receipt_id,
            "renderer_revision",
            "relaylm.subjective_mem_renderer.v0",
        ),
        (
            "subjective_mem_forget_tombstone",
            proposal.expected_forget_tombstone_id,
            "scope_binding_digest",
            "f" * 64,
        ),
        (
            "subjective_mem_forget_tombstone",
            proposal.expected_forget_tombstone_id,
            "reason_category",
            "operator_requested_forget",
        ),
    )


def _alter_keeping_digest(env, kind: str, record_id: str, field: str, value):
    """Alter one uninspected field while retaining the record's stale digest."""

    space = env["captured"].evidence_space_id
    path = _record_file(env, kind, record_id)
    saved = path.read_text(encoding="utf-8")
    original = _record(env, kind, record_id)
    assert isinstance(original, dict) and field in original
    assert original[field] != value
    digest_field = (
        "receipt_digest" if "receipt" in kind else "tombstone_digest"
    )
    path.unlink()
    written = env["store"].write_record(
        evidence_space_id=space, record_kind=kind, record_id=record_id,
        payload={**original, field: value},
    )
    assert written.status == "created"
    altered = _record(env, kind, record_id)
    assert isinstance(altered, dict)
    # the stale self-digest is retained, so only recomputing it detects this
    assert altered[digest_field] == original[digest_field]
    return saved


def test_restore_recovery_rejects_altered_uninspected_binding_fields(
    lifecycle_env,
) -> None:
    _forgotten, proposal = _proposal(lifecycle_env)
    _reserved(lifecycle_env, proposal, key="recover-selfdigest")
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)

    for kind, record_id, field, value in _uninspected_binding_cases(proposal):
        saved = _alter_keeping_digest(
            lifecycle_env, kind, record_id, field, value
        )
        for apply_enabled in (False, True):
            blocked = _restore(
                lifecycle_env, proposal, apply=apply_enabled, key="recover-selfdigest"
            )
            assert blocked.status == "fail_closed", (
                f"{kind}/{field} apply={apply_enabled} -> {blocked.status}"
            )
            assert blocked.recovery_outcome is None
            assert blocked.canonical_markdown_published is False
            assert blocked.lifecycle_receipt_present is False
            assert blocked.tombstone_release_present is False
            assert lifecycle_env["page_path"].read_bytes() == before_page
            assert _release_events(lifecycle_env, proposal) in (None, [])
        _restore_binding(lifecycle_env, kind, record_id, saved)
        assert _store_files(lifecycle_env) == before_files

    recovered = _restore(
        lifecycle_env, proposal, apply=True, key="recover-selfdigest"
    )
    assert recovered.status == "committed", recovered.blocked_reasons
    assert _revisions(lifecycle_env["page_path"].read_bytes()) == [1, 2, 3]


def test_restore_replay_rejects_altered_uninspected_binding_fields(
    lifecycle_env,
) -> None:
    proposal, first = _committed_restore(lifecycle_env, key="replay-selfdigest")
    page_after = lifecycle_env["page_path"].read_bytes()
    files_after = _store_files(lifecycle_env)
    release_after = _release_events(lifecycle_env, proposal)

    for kind, record_id, field, value in _uninspected_binding_cases(proposal):
        saved = _alter_keeping_digest(
            lifecycle_env, kind, record_id, field, value
        )
        for apply_enabled in (False, True):
            blocked = _restore(
                lifecycle_env, proposal, apply=apply_enabled, key="replay-selfdigest"
            )
            assert blocked.status == "fail_closed", (
                f"{kind}/{field} apply={apply_enabled} -> {blocked.status}"
            )
            assert blocked.recovery_outcome != "exact_replay"
            assert blocked.tombstone_release_present is False
            assert lifecycle_env["page_path"].read_bytes() == page_after
            assert _release_events(lifecycle_env, proposal) == release_after
        _restore_binding(lifecycle_env, kind, record_id, saved)
        assert _store_files(lifecycle_env) == files_after

    replay = _restore(lifecycle_env, proposal, apply=True, key="replay-selfdigest")
    assert replay.status == "duplicate_finalized", replay.blocked_reasons
    assert replay.recovery_outcome == "exact_replay"
    assert replay.release_id == first.release_id
    assert lifecycle_env["page_path"].read_bytes() == page_after
    assert _store_files(lifecycle_env) == files_after
    assert _release_events(lifecycle_env, proposal) == release_after
