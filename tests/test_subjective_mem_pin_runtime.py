"""LC-1C Subjective MEM Pin / Unpin runtime tests."""
from __future__ import annotations

import inspect
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from relaylm._subjective_mem_commit_io import PLATFORM_REVISION
from relaylm.evidence_common import canonical_digest
from relaylm.evidence_store import EvidenceRecordStore
from relaylm.subjective_mem import SUBJECTIVE_MEM_REVISION_SCHEMA
from relaylm.subjective_mem_lifecycle import LIFECYCLE_POLICY_REVISION
from relaylm.subjective_mem_markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    parse_subjective_mem_page_bytes,
)
from relaylm.subjective_mem_pin import SubjectiveMemPinBoundary, SubjectiveMemPinProposal
import relaylm.subjective_mem_pin_runtime as pin_runtime
from relaylm.subjective_mem_pin_runtime import pin_subjective_mem, unpin_subjective_mem
from test_subjective_mem_commit_runtime import _commit, _make_workspace
from test_subjective_mem_runtime import (
    CHARACTER_CONFIG,
    NOW,
    _asm_ready,
    _character,
    _create,
)


@pytest.fixture()
def pin_env(tmp_path: Path):
    workspace = _make_workspace(tmp_path)
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    captured, assessment_revision, assessment_state = _asm_ready(store)
    sm1 = _create(store, captured, assessment_revision, assessment_state)
    config = CHARACTER_CONFIG.model_copy(
        update={"subjective_mem_workspace_root": str(workspace)}
    )
    env = {
        "store": store,
        "captured": captured,
        "workspace": workspace,
        "workspace_root": workspace,
        "config": config,
        "authority": _character(),
    }
    st1 = _commit({
        **env,
        "assessment_revision": assessment_revision,
        "assessment_state": assessment_state,
        "sm1": sm1,
    })
    assert st1.status == "committed" and st1.current_state is not None
    env.update({"st1": st1, "page_path": workspace / "char1/memory/episodes/subjective-mem-v1.md"})
    return env


def _current_page(env):
    page, reasons = parse_subjective_mem_page_bytes(env["page_path"].read_bytes())
    assert page is not None and not reasons
    return page


def _proposal(env, operation: str, *, state=None, **changes):
    state = state or env["st1"].current_state
    assert state is not None
    page = _current_page(env)
    block = next(
        item
        for item in page.blocks
        if item.revision.memory_id == state.memory_id
        and item.revision.memory_revision == state.current_revision
    )
    if state.current_revision == 1:
        receipt_model = env["st1"].receipt
        assert receipt_model is not None
        receipt_id = receipt_model.receipt_id
        receipt = receipt_model.to_dict()
    else:
        assert state.current_receipt_id is not None
        receipt_id = state.current_receipt_id
        receipt = env["store"].read_record(
            evidence_space_id=env["captured"].evidence_space_id,
            record_kind="subjective_mem_lifecycle_receipt",
            record_id=receipt_id,
        )
        assert isinstance(receipt, dict)
    base = SubjectiveMemPinProposal(
        operation_kind=operation,
        expected_memory_id=state.memory_id,
        expected_current_revision=state.current_revision,
        expected_lifecycle_state=state.lifecycle_state,
        expected_mutation_state="none",
        expected_page_id=page.page_id,
        expected_relative_path="memory/episodes/subjective-mem-v1.md",
        expected_block_id=block.block_id,
        expected_page_digest=page.page_digest,
        expected_current_selector_id=state.memory_state_id,
        expected_current_selector_digest=canonical_digest(state.to_dict()),
        expected_current_receipt_id=receipt_id,
        expected_current_receipt_digest=receipt["receipt_digest"],
        expected_memory_kind=block.revision.memory_kind,
        expected_formation_stage=block.revision.formation_stage,
        expected_scope_binding_digest=canonical_digest(block.revision.scope_binding.to_dict()),
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
        authorization_id=f"user-{operation}-authorization",
        reason_category=f"user_requested_{operation}",
        policy_revision=LIFECYCLE_POLICY_REVISION,
        boundary=SubjectiveMemPinBoundary(),
    )
    return replace(base, **changes)


def _call(env, proposal, *, key="lc1c-operation", seconds=2, apply=True, fault=None):
    operation = pin_subjective_mem if proposal.operation_kind == "pin" else unpin_subjective_mem
    return operation(
        store=env["store"],
        evidence_space_id=env["captured"].evidence_space_id,
        character_config=env["config"],
        character_authority=env["authority"],
        workspace_root=str(env["workspace"]),
        operation_idempotency_key=key,
        proposal=proposal,
        apply_enabled=apply,
        committed_at=NOW + timedelta(seconds=seconds),
        observed_at=NOW + timedelta(seconds=seconds + 1),
        fault_injector=fault,
    )


def _semantic_projection(revision):
    raw = revision.to_dict()
    for key in (
        "memory_revision",
        "lifecycle_state",
        "predecessor_revision_or_null",
        "authorization_ref",
        "created_at",
    ):
        raw.pop(key)
    return raw


def test_pin_dry_run_is_write_free(pin_env) -> None:
    before = pin_env["page_path"].read_bytes()
    result = _call(pin_env, _proposal(pin_env, "pin"), apply=False)
    assert result.status == "dry_run_ready", result.blocked_reasons
    assert pin_env["page_path"].read_bytes() == before
    assert not list(pin_env["store"].root.rglob("*lifecycle_claim*"))


def test_pin_and_unpin_append_exact_semantic_preserving_successors(pin_env) -> None:
    original = _current_page(pin_env).blocks[0].revision
    pinned = _call(pin_env, _proposal(pin_env, "pin"), key="pin-key", seconds=2)
    assert pinned.status == "committed", pinned.blocked_reasons
    assert pinned.current_state is not None
    assert pinned.current_state.lifecycle_state == "pinned"
    assert pinned.current_state.current_revision == 2
    assert pinned.current_state.retrieval_eligible is True

    pinned_page = _current_page(pin_env)
    pinned_revision = pinned_page.blocks[-1].revision
    assert _semantic_projection(pinned_revision) == _semantic_projection(original)
    assert pinned_revision.predecessor_revision_or_null == 1

    unpinned = _call(
        pin_env,
        _proposal(pin_env, "unpin", state=pinned.current_state),
        key="unpin-key",
        seconds=4,
    )
    assert unpinned.status == "committed", unpinned.blocked_reasons
    assert unpinned.current_state is not None
    assert unpinned.current_state.lifecycle_state == "active"
    assert unpinned.current_state.current_revision == 3
    revisions = [item.revision for item in _current_page(pin_env).blocks]
    assert [item.lifecycle_state for item in revisions] == ["active", "pinned", "active"]
    assert all(_semantic_projection(item) == _semantic_projection(original) for item in revisions)


def test_exact_retry_replays_without_another_revision(pin_env) -> None:
    proposal = _proposal(pin_env, "pin")
    first = _call(pin_env, proposal)
    second = _call(pin_env, proposal)
    assert first.status == "committed"
    assert second.status == "duplicate_finalized", second.blocked_reasons
    assert second.transition_id == first.transition_id
    assert [item.revision.memory_revision for item in _current_page(pin_env).blocks] == [1, 2]


def test_inverse_direction_reuse_of_same_key_conflicts(pin_env) -> None:
    pinned = _call(pin_env, _proposal(pin_env, "pin"), key="shared-key")
    assert pinned.status == "committed" and pinned.current_state is not None
    inverse = _call(
        pin_env,
        _proposal(pin_env, "unpin", state=pinned.current_state),
        key="shared-key",
        seconds=4,
    )
    assert inverse.status == "integrity_conflict"
    assert "subjective_mem_lifecycle_idempotency_conflict" in inverse.blocked_reasons
    assert [item.revision.memory_revision for item in _current_page(pin_env).blocks] == [1, 2]


def test_wrong_direction_and_stale_selector_fail_closed(pin_env) -> None:
    wrong = _call(pin_env, _proposal(pin_env, "unpin"), key="wrong", apply=False)
    assert wrong.status == "fail_closed"
    stale = _proposal(pin_env, "pin")
    assert _call(pin_env, stale, key="winner").status == "committed"
    loser = _call(pin_env, stale, key="loser", seconds=4)
    assert loser.status == "fail_closed"
    assert any("selector" in reason or "revision" in reason for reason in loser.blocked_reasons)


@pytest.mark.parametrize("stage", ["after_intent_before_page", "after_page_before_receipt"])
def test_pin_recovers_forward_after_bounded_crash(pin_env, stage: str) -> None:
    def crash(current: str) -> None:
        if current == stage:
            raise RuntimeError("simulated")

    proposal = _proposal(pin_env, "pin")
    first = _call(pin_env, proposal, fault=crash)
    assert first.status == "recovery_pending", first.blocked_reasons
    second = _call(pin_env, proposal)
    assert second.status == "committed", second.blocked_reasons
    assert second.current_state is not None
    assert second.current_state.lifecycle_state == "pinned"


def test_foreign_page_is_preserved_and_fenced(pin_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_intent_before_page":
            raise RuntimeError("simulated")

    proposal = _proposal(pin_env, "pin")
    assert _call(pin_env, proposal, fault=crash).status == "recovery_pending"
    pin_env["page_path"].write_text("# foreign\n", encoding="utf-8")
    result = _call(pin_env, proposal)
    assert result.status == "recovery_required"
    assert result.recovery_outcome == "foreign_image"
    assert pin_env["page_path"].read_text(encoding="utf-8") == "# foreign\n"


def test_lifecycle_records_and_result_projection_are_content_free(pin_env) -> None:
    raw_key = "caller-secret-pin-key"
    result = _call(pin_env, _proposal(pin_env, "pin"), key=raw_key)
    assert result.status == "committed"
    forbidden = (raw_key, str(pin_env["workspace"]), "I felt relieved", "safe again")
    for path in pin_env["store"].root.rglob("*.json"):
        if "subjective_mem_lifecycle" not in str(path):
            continue
        text = path.read_text(encoding="utf-8")
        assert all(value not in text for value in forbidden)
    projection = result.to_log_dict()
    assert projection["content_free"] is True
    assert projection["primary_mem_pin_projection_written"] is False
    assert all(value not in json.dumps(projection) for value in forbidden)


def test_runtime_has_one_owner_and_only_uses_shared_publication_engine() -> None:
    source = inspect.getsource(pin_runtime)
    assert source.count("def pin_subjective_mem(") == 1
    assert source.count("def unpin_subjective_mem(") == 1
    assert "subjective_mem_lifecycle_runtime import" not in source
    assert "subjective_mem_forget_runtime import" not in source
    assert "relaymem_primary" not in source
    assert "ContextVar" not in source
    assert "reserve_lifecycle_publication(" in source
    assert "publish_lifecycle_post_image(" in source
    assert "resolve_finalized_replay(" in source
