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
from relaylm.subjective_mem_restore import (
    SubjectiveMemRestoreBoundary,
    SubjectiveMemRestoreProposal,
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
