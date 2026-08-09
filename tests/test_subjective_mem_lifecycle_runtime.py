"""LC-1A Subjective MEM Correct runtime tests."""
from __future__ import annotations

import json
from dataclasses import fields, replace
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from relaylm.config import RelayLMConfig
from relaylm.evidence.common import canonical_digest
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.subjective_mem.commit_io import PLATFORM_REVISION
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA,
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemStrength,
)
from relaylm.subjective_mem.lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    SubjectiveMemCorrectProposal,
    SubjectiveMemCorrectionBoundary,
)
import relaylm.subjective_mem_lifecycle_engine as lifecycle_engine
import relaylm.subjective_mem_lifecycle_runtime as lifecycle_runtime
import relaylm.subjective_mem.markdown as subjective_mem_markdown
from relaylm.subjective_mem_lifecycle_runtime import (
    correct_subjective_mem,
    resolve_subjective_mem_lifecycle_gate,
)
from relaylm.subjective_mem.markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    parse_subjective_mem_page_bytes,
    plan_subjective_mem_revision_successor,
)
from test_subjective_mem_commit_runtime import _commit, _make_workspace
from test_subjective_mem_runtime import (
    BASE_CONFIG,
    CHARACTER_CONFIG,
    NOW,
    _asm_ready,
    _character,
    _create,
)


@pytest.fixture()
def lifecycle_env(tmp_path: Path):
    workspace_root = _make_workspace(tmp_path)
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    captured, assessment_revision, assessment_state = _asm_ready(store)
    sm1 = _create(store, captured, assessment_revision, assessment_state)
    config = CHARACTER_CONFIG.model_copy(update={"subjective_mem_workspace_root": str(workspace_root)})
    env = {
        "store": store,
        "captured": captured,
        "assessment_revision": assessment_revision,
        "assessment_state": assessment_state,
        "sm1": sm1,
        "workspace_root": workspace_root,
        "config": config,
        "authority": _character(),
    }
    st1 = _commit(env)
    assert st1.status == "committed"
    assert st1.current_state is not None and st1.receipt is not None
    page_path = workspace_root / "char1/memory/episodes/subjective-mem-v1.md"
    page, reasons = parse_subjective_mem_page_bytes(page_path.read_bytes())
    assert page is not None and not reasons
    env.update({"st1": st1, "page_path": page_path, "page": page})
    return env


def _proposal(env, **changes):
    st1 = env["st1"]
    page = env["page"]
    state = st1.current_state
    receipt = st1.receipt
    assert state is not None and receipt is not None
    base = SubjectiveMemCorrectProposal(
        expected_memory_id=state.memory_id,
        expected_current_revision=1,
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
        expected_memory_kind=page.blocks[0].revision.memory_kind,
        expected_formation_stage=page.blocks[0].revision.formation_stage,
        expected_scope_binding_digest=canonical_digest(
            page.blocks[0].revision.scope_binding.to_dict()
        ),
        expected_formation_snapshot_digest=canonical_digest(
            page.blocks[0].revision.formation_snapshot.to_dict()
        ),
        expected_revision_schema=SUBJECTIVE_MEM_REVISION_SCHEMA,
        expected_page_schema=PAGE_SCHEMA,
        expected_block_schema=LIFECYCLE_BLOCK_SCHEMA,
        expected_renderer_revision=RENDERER_REVISION,
        expected_partition_revision=PAGE_PARTITION_REVISION,
        expected_platform_revision=PLATFORM_REVISION,
        assessment_revision=env["assessment_revision"],
        assessment_current_state=env["assessment_state"],
        corrected_grounded_content=env["assessment_revision"].supported_content,
        corrected_subjective_meaning="I now remember this more precisely as relief mixed with lingering uncertainty.",
        corrected_strength=SubjectiveMemStrength(
            grounded_confidence=0.8,
            subjective_conviction=0.6,
            salience="medium",
            reinforcement_count=0,
            strength_basis="subjective_interpretation",
        ),
        authorization_class="user_management",
        authorization_id="user-correction-authorization-1",
        reason_category="user_reported_inaccuracy",
        policy_revision=LIFECYCLE_POLICY_REVISION,
        boundary=SubjectiveMemCorrectionBoundary(),
    )
    return replace(base, **changes)


def _correct(env, *, proposal=None, apply=True, fault=None):
    return correct_subjective_mem(
        store=env["store"],
        evidence_space_id=env["captured"].evidence_space_id,
        character_config=env["config"],
        character_authority=env["authority"],
        workspace_root=str(env["workspace_root"]),
        operation_idempotency_key="lc1a-correct-operation",
        proposal=proposal or _proposal(env),
        apply_enabled=apply,
        committed_at=NOW + timedelta(seconds=2),
        observed_at=NOW + timedelta(seconds=3),
        fault_injector=fault,
    )


def test_correct_dry_run_validates_without_writes(lifecycle_env) -> None:
    before = lifecycle_env["page_path"].read_bytes()
    result = _correct(lifecycle_env, apply=False)
    assert result.status == "dry_run_ready", result.blocked_reasons
    assert lifecycle_env["page_path"].read_bytes() == before
    records = lifecycle_env["store"].root.rglob("*lifecycle*")
    assert list(records) == []


def test_correct_happy_path_appends_one_immutable_successor(lifecycle_env) -> None:
    original = lifecycle_env["page"].blocks[0].revision.to_dict()
    result = _correct(lifecycle_env)
    assert result.status == "committed", result.blocked_reasons
    assert result.current_state is not None
    assert result.current_state.current_revision == 2
    assert result.current_state.lifecycle_state == "active"
    assert result.current_state.mutation_state == "none"
    assert result.current_state.retrieval_eligible is True
    assert result.canonical_markdown_published is True
    assert result.lifecycle_receipt_present is True
    assert result.receipt_id is not None
    receipt = lifecycle_env["store"].read_record(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        record_kind="subjective_mem_lifecycle_receipt",
        record_id=result.receipt_id,
    )
    assert isinstance(receipt, dict)
    assert receipt["policy_revision"] == LIFECYCLE_POLICY_REVISION
    assert receipt["revision_schema"] == SUBJECTIVE_MEM_REVISION_SCHEMA
    assert receipt["page_schema"] == PAGE_SCHEMA
    assert receipt["block_schema"] == LIFECYCLE_BLOCK_SCHEMA
    assert receipt["renderer_revision"] == RENDERER_REVISION
    assert receipt["partition_revision"] == PAGE_PARTITION_REVISION
    assert receipt["platform_revision"] == PLATFORM_REVISION

    page, reasons = parse_subjective_mem_page_bytes(lifecycle_env["page_path"].read_bytes())
    assert page is not None and not reasons
    revisions = [item for item in page.blocks if item.revision.memory_id == result.memory_id]
    assert [item.revision.memory_revision for item in revisions] == [1, 2]
    assert revisions[0].revision.to_dict() == original
    successor = revisions[1].revision
    assert successor.predecessor_revision_or_null == 1
    assert successor.authorization_kind == "lifecycle_transition"
    assert successor.subjective_meaning == _proposal(lifecycle_env).corrected_subjective_meaning
    assert LIFECYCLE_BLOCK_SCHEMA.encode() in lifecycle_env["page_path"].read_bytes()


def test_correct_exact_retry_returns_same_result_without_third_revision(lifecycle_env) -> None:
    first = _correct(lifecycle_env)
    second = _correct(lifecycle_env)
    assert first.status == "committed"
    assert second.status == "duplicate_finalized", second.blocked_reasons
    assert second.transition_id == first.transition_id
    assert second.receipt_id == first.receipt_id
    page, reasons = parse_subjective_mem_page_bytes(lifecycle_env["page_path"].read_bytes())
    assert page is not None and not reasons
    assert [item.revision.memory_revision for item in page.blocks] == [1, 2]


def test_correct_changed_input_under_same_key_conflicts(lifecycle_env) -> None:
    first = _correct(lifecycle_env)
    assert first.status == "committed"
    changed = _proposal(lifecycle_env, corrected_subjective_meaning="A materially different correction.")
    second = _correct(lifecycle_env, proposal=changed)
    assert second.status == "integrity_conflict"
    assert "subjective_mem_lifecycle_idempotency_conflict" in second.blocked_reasons


def test_correct_rejects_stale_selector_and_pinned_transition(lifecycle_env) -> None:
    stale = _proposal(lifecycle_env, expected_current_revision=2)
    result = _correct(lifecycle_env, proposal=stale, apply=False)
    assert result.status == "fail_closed"
    pinned = _proposal(lifecycle_env, expected_lifecycle_state="pinned")
    result = _correct(lifecycle_env, proposal=pinned, apply=False)
    assert result.status == "fail_closed"
    assert any("transition_unsupported" in item or "precondition" in item for item in result.blocked_reasons)


def test_correct_requires_exact_grounding_and_authorization(lifecycle_env) -> None:
    unsupported = _proposal(lifecycle_env, corrected_grounded_content="Unsupported replacement")
    result = _correct(lifecycle_env, proposal=unsupported, apply=False)
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_correct_grounding_invalid" in result.blocked_reasons
    policy = _proposal(lifecycle_env, authorization_class="relaymem_policy")
    result = _correct(lifecycle_env, proposal=policy, apply=False)
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_correct_authorization_invalid" in result.blocked_reasons


def test_correct_after_intent_recovers_exact_immutable_post_image(lifecycle_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_intent_before_page":
            raise RuntimeError("simulated")

    first = _correct(lifecycle_env, fault=crash)
    assert first.status == "recovery_pending"
    assert first.current_state is not None
    assert first.current_state.mutation_state == "prepared"
    second = _correct(lifecycle_env)
    assert second.status == "committed", second.blocked_reasons
    assert second.recovery_outcome == "published_and_finalized"


def test_correct_page_present_receipt_missing_rolls_forward(lifecycle_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_page_before_receipt":
            raise RuntimeError("simulated")

    first = _correct(lifecycle_env, fault=crash)
    assert first.status == "recovery_pending", first.blocked_reasons
    assert first.canonical_markdown_published is True
    second = _correct(lifecycle_env)
    assert second.status == "committed", second.blocked_reasons
    assert second.recovery_outcome == "post_image_rolled_forward"


def test_correct_foreign_image_is_not_overwritten(lifecycle_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_intent_before_page":
            raise RuntimeError("simulated")

    assert _correct(lifecycle_env, fault=crash).status == "recovery_pending"
    lifecycle_env["page_path"].write_text("# foreign\n", encoding="utf-8")
    result = _correct(lifecycle_env)
    assert result.status == "recovery_required"
    assert result.recovery_outcome == "foreign_image"
    assert lifecycle_env["page_path"].read_text(encoding="utf-8") == "# foreign\n"


def test_lifecycle_operations_records_are_content_free(lifecycle_env) -> None:
    proposal = _proposal(lifecycle_env)
    result = _correct(lifecycle_env, proposal=proposal)
    assert result.status == "committed"
    forbidden = (
        proposal.corrected_grounded_content,
        proposal.corrected_subjective_meaning,
        "lc1a-correct-operation",
        str(lifecycle_env["workspace_root"]),
    )
    for path in lifecycle_env["store"].root.rglob("*.json"):
        if "subjective_mem_lifecycle" not in str(path):
            continue
        text = path.read_text(encoding="utf-8")
        assert all(value not in text for value in forbidden)
    projection = result.to_log_dict()
    assert projection["content_free"] is True
    assert projection["ordinary_retrieval_wired"] is False
    assert projection["purge_authorized"] is False
    assert all(value not in json.dumps(projection) for value in forbidden)


def test_lifecycle_gate_is_default_off_and_requires_st1_apply(tmp_path: Path) -> None:
    default = RelayLMConfig.model_validate(BASE_CONFIG)
    gate = resolve_subjective_mem_lifecycle_gate(default)
    assert gate.enabled is False and gate.apply_enabled is False

    common = {
        **BASE_CONFIG,
        "evidence_data_root": str((tmp_path / "evidence").resolve()),
        "subjective_mem_workspace_root": str((tmp_path / "characters").resolve()),
        "shared_assessment_enabled": True,
        "shared_assessment_dry_run_only": False,
        "shared_assessment_apply_enabled": True,
        "subjective_mem_create_enabled": True,
        "subjective_mem_create_dry_run_only": False,
        "subjective_mem_create_apply_enabled": True,
        "subjective_mem_commit_enabled": True,
        "subjective_mem_commit_dry_run_only": True,
        "subjective_mem_commit_apply_enabled": False,
        "subjective_mem_lifecycle_enabled": True,
        "subjective_mem_lifecycle_dry_run_only": False,
        "subjective_mem_lifecycle_apply_enabled": True,
    }
    with pytest.raises(ValidationError):
        RelayLMConfig.model_validate(common)


def test_no_primary_or_retrieval_runtime_is_modified() -> None:
    # Static scope guard for the LC-1A atomic slice.
    source = Path("relaylm/subjective_mem_lifecycle_runtime.py").read_text(encoding="utf-8")
    assert "relaymem_primary" not in source
    assert "ordinary_retrieval_wired\": True" not in source
    assert "threading" not in source and "asyncio" not in source


def test_correct_competing_key_loses_shared_mutation_fence(lifecycle_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_intent_before_page":
            raise RuntimeError("simulated")

    winner = _correct(lifecycle_env, fault=crash)
    assert winner.status == "recovery_pending"
    proposal = _proposal(lifecycle_env)
    loser = correct_subjective_mem(
        store=lifecycle_env["store"],
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        character_config=lifecycle_env["config"],
        character_authority=lifecycle_env["authority"],
        workspace_root=str(lifecycle_env["workspace_root"]),
        operation_idempotency_key="competing-correct-key",
        proposal=proposal,
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=2),
        observed_at=NOW + timedelta(seconds=3),
    )
    assert loser.status == "fail_closed"
    assert any("selector" in item or "mutation" in item for item in loser.blocked_reasons)


def test_correct_receipt_without_page_never_returns_success(lifecycle_env) -> None:
    first = _correct(lifecycle_env)
    assert first.status == "committed"
    lifecycle_env["page_path"].unlink()
    replay = _correct(lifecycle_env)
    assert replay.status == "fail_closed"
    assert "subjective_mem_lifecycle_receipt_without_exact_page" in replay.blocked_reasons


def test_correct_missing_current_st1_receipt_fails_closed(lifecycle_env) -> None:
    proposal = _proposal(lifecycle_env, expected_current_receipt_id="missing-receipt")
    result = _correct(lifecycle_env, proposal=proposal, apply=False)
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_current_receipt_missing_or_corrupt" in result.blocked_reasons


def test_correct_crash_before_intent_leaves_no_authority_change(lifecycle_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_artifact_before_intent":
            raise RuntimeError("simulated")

    before = lifecycle_env["page_path"].read_bytes()
    first = _correct(lifecycle_env, fault=crash)
    assert first.status == "fail_closed"
    assert lifecycle_env["page_path"].read_bytes() == before
    state = lifecycle_env["store"].read_log(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        log_kind="subjective_mem_current_state",
        key=lifecycle_env["st1"].current_state.memory_state_id,
    )
    assert state == [lifecycle_env["st1"].current_state.to_dict()]
    second = _correct(lifecycle_env)
    assert second.status == "committed", second.blocked_reasons


def test_correct_can_append_a_third_revision_from_exact_lifecycle_receipt(lifecycle_env) -> None:
    first = _correct(lifecycle_env)
    assert first.status == "committed", first.blocked_reasons
    assert first.current_state is not None and first.receipt_id is not None

    page, reasons = parse_subjective_mem_page_bytes(lifecycle_env["page_path"].read_bytes())
    assert page is not None and not reasons
    current_block = next(item for item in page.blocks if item.revision.memory_revision == 2)
    receipt = lifecycle_env["store"].read_record(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        record_kind="subjective_mem_lifecycle_receipt",
        record_id=first.receipt_id,
    )
    assert isinstance(receipt, dict)

    second_proposal = _proposal(
        lifecycle_env,
        expected_current_revision=2,
        expected_block_id=current_block.block_id,
        expected_page_digest=page.page_digest,
        expected_current_selector_digest=canonical_digest(first.current_state.to_dict()),
        expected_current_receipt_id=first.receipt_id,
        expected_current_receipt_digest=receipt["receipt_digest"],
        corrected_subjective_meaning=(
            "I now remember this as relief, with the remaining uncertainty explicitly bounded."
        ),
        authorization_id="user-correction-authorization-2",
    )
    second = correct_subjective_mem(
        store=lifecycle_env["store"],
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        character_config=lifecycle_env["config"],
        character_authority=lifecycle_env["authority"],
        workspace_root=str(lifecycle_env["workspace_root"]),
        operation_idempotency_key="lc1a-correct-operation-2",
        proposal=second_proposal,
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=4),
        observed_at=NOW + timedelta(seconds=5),
    )
    assert second.status == "committed", second.blocked_reasons
    assert second.current_state is not None
    assert second.current_state.current_revision == 3

    final_page, reasons = parse_subjective_mem_page_bytes(
        lifecycle_env["page_path"].read_bytes()
    )
    assert final_page is not None and not reasons
    revisions = [item.revision for item in final_page.blocks]
    assert [item.memory_revision for item in revisions] == [1, 2, 3]
    assert revisions[2].predecessor_revision_or_null == 2
    assert revisions[1].subjective_meaning == _proposal(
        lifecycle_env
    ).corrected_subjective_meaning


def test_correct_before_staging_failure_recovers_from_durable_intent(lifecycle_env) -> None:
    def crash(stage: str) -> None:
        if stage == "before_staging":
            raise RuntimeError("simulated")

    before = lifecycle_env["page_path"].read_bytes()
    first = _correct(lifecycle_env, fault=crash)
    assert first.status == "recovery_pending", first.blocked_reasons
    assert first.recovery_outcome == "pre_image_pending_publication"
    assert lifecycle_env["page_path"].read_bytes() == before

    second = _correct(lifecycle_env)
    assert second.status == "committed", second.blocked_reasons
    assert second.recovery_outcome == "published_and_finalized"


def test_lifecycle_gate_rejects_non_boolean_triple_without_apply(tmp_path: Path) -> None:
    class InvalidConfig:
        subjective_mem_lifecycle_enabled = "yes"
        subjective_mem_lifecycle_dry_run_only = True
        subjective_mem_lifecycle_apply_enabled = False
        evidence_data_root = str((tmp_path / "evidence").resolve())
        subjective_mem_workspace_root = str((tmp_path / "characters").resolve())

    gate = resolve_subjective_mem_lifecycle_gate(InvalidConfig())
    assert gate.enabled is False
    assert gate.apply_enabled is False
    assert gate.dry_run_only is True
    assert gate.store is None
    assert gate.workspace_root is None


def test_correct_exact_replay_rejects_corrupt_transition_record(lifecycle_env) -> None:
    first = _correct(lifecycle_env)
    assert first.status == "committed", first.blocked_reasons
    assert first.transition_id is not None
    path = lifecycle_env["store"]._record_path(  # noqa: SLF001 - corruption fixture
        lifecycle_env["captured"].evidence_space_id,
        "subjective_mem_lifecycle_transition",
        first.transition_id,
    )
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["authorized_by"] = "operator"
    path.write_text(
        json.dumps(raw, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    replay = _correct(lifecycle_env)
    assert replay.status == "fail_closed"
    assert "subjective_mem_lifecycle_final_result_incomplete" in replay.blocked_reasons


def test_correct_requires_exact_scope_and_contract_revisions(lifecycle_env) -> None:
    wrong_scope = _proposal(
        lifecycle_env, expected_scope_binding_digest="0" * 64
    )
    result = _correct(lifecycle_env, proposal=wrong_scope, apply=False)
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_current_revision_invalid" in result.blocked_reasons

    wrong_renderer = _proposal(
        lifecycle_env, expected_renderer_revision="renderer-future"
    )
    result = _correct(lifecycle_env, proposal=wrong_renderer, apply=False)
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_lifecycle_correct_contract_revision_mismatch"
        in result.blocked_reasons
    )


def test_correct_rejects_unknown_policy_revision(lifecycle_env) -> None:
    proposal = _proposal(lifecycle_env, policy_revision="policy-future")
    result = _correct(lifecycle_env, proposal=proposal, apply=False)
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_lifecycle_correct_policy_revision_invalid"
        in result.blocked_reasons
    )


def test_correct_apply_fails_closed_on_unsupported_platform(
    lifecycle_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lifecycle_runtime, "secure_platform_supported", lambda: False)
    result = _correct(lifecycle_env, apply=True)
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_platform_unsupported" in result.blocked_reasons
    page, reasons = parse_subjective_mem_page_bytes(
        lifecycle_env["page_path"].read_bytes()
    )
    assert page is not None and not reasons and len(page.blocks) == 1


def test_correct_rejects_unregistered_or_prose_reason_category(lifecycle_env) -> None:
    proposal = _proposal(
        lifecycle_env, reason_category="please correct this memory with prose"
    )
    result = _correct(lifecycle_env, proposal=proposal, apply=False)
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_lifecycle_correct_reason_category_invalid"
        in result.blocked_reasons
    )


def test_correct_wrong_evidence_space_fails_without_creating_space(lifecycle_env) -> None:
    wrong = "evspace_wrong"
    wrong_path = lifecycle_env["store"].root / wrong
    result = correct_subjective_mem(
        store=lifecycle_env["store"],
        evidence_space_id=wrong,
        character_config=lifecycle_env["config"],
        character_authority=lifecycle_env["authority"],
        workspace_root=str(lifecycle_env["workspace_root"]),
        operation_idempotency_key="lc1a-wrong-space",
        proposal=_proposal(lifecycle_env),
        apply_enabled=False,
        committed_at=NOW + timedelta(seconds=2),
        observed_at=NOW + timedelta(seconds=3),
    )
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_evidence_space_unavailable" in result.blocked_reasons
    assert not wrong_path.exists()


def test_correct_duplicate_current_selector_fails_closed(lifecycle_env) -> None:
    state = lifecycle_env["st1"].current_state
    assert state is not None
    duplicate = lifecycle_env["store"].write_log(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        log_kind="subjective_mem_current_state",
        key="duplicate-current-selector",
        events=(state.to_dict(),),
    )
    assert duplicate.status == "created"
    result = _correct(lifecycle_env, apply=False)
    assert result.status == "fail_closed"
    assert (
        "subjective_mem_lifecycle_duplicate_logical_current_selector"
        in result.blocked_reasons
    )


def test_correct_non_monotonic_operation_time_fails_closed(lifecycle_env) -> None:
    result = correct_subjective_mem(
        store=lifecycle_env["store"],
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        character_config=lifecycle_env["config"],
        character_authority=lifecycle_env["authority"],
        workspace_root=str(lifecycle_env["workspace_root"]),
        operation_idempotency_key="lc1a-old-clock",
        proposal=_proposal(lifecycle_env),
        apply_enabled=False,
        committed_at=NOW,
        observed_at=NOW + timedelta(seconds=3),
    )
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_current_revision_invalid" in result.blocked_reasons


def test_correct_page_capacity_refuses_without_alternate_page(
    lifecycle_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subjective_mem_markdown, "MAX_CANONICAL_PAGE_BLOCKS", 1)
    result = _correct(lifecycle_env, apply=False)
    assert result.status == "fail_closed"
    assert "subjective_mem_markdown_page_capacity_exceeded" in result.blocked_reasons
    page, reasons = parse_subjective_mem_page_bytes(
        lifecycle_env["page_path"].read_bytes()
    )
    assert page is not None and not reasons and len(page.blocks) == 1


def test_correct_rejects_noop_and_weakened_boundary(lifecycle_env) -> None:
    predecessor = lifecycle_env["page"].blocks[0].revision
    noop = _proposal(
        lifecycle_env,
        corrected_subjective_meaning=predecessor.subjective_meaning,
        corrected_strength=predecessor.strength,
    )
    result = _correct(lifecycle_env, proposal=noop, apply=False)
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_correction_no_change" in result.blocked_reasons

    weakened = _proposal(
        lifecycle_env,
        boundary=replace(
            SubjectiveMemCorrectionBoundary(), uncertainty_preserved=False
        ),
    )
    result = _correct(lifecycle_env, proposal=weakened, apply=False)
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_correct_boundary_invalid" in result.blocked_reasons


def test_correct_rejects_future_operation_time_and_wrong_receipt_digest(
    lifecycle_env,
) -> None:
    future = correct_subjective_mem(
        store=lifecycle_env["store"],
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        character_config=lifecycle_env["config"],
        character_authority=lifecycle_env["authority"],
        workspace_root=str(lifecycle_env["workspace_root"]),
        operation_idempotency_key="lc1a-future-clock",
        proposal=_proposal(lifecycle_env),
        apply_enabled=False,
        committed_at=NOW + timedelta(seconds=5),
        observed_at=NOW + timedelta(seconds=4),
    )
    assert future.status == "fail_closed"
    assert "subjective_mem_lifecycle_time_in_future" in future.blocked_reasons

    wrong_receipt = _proposal(
        lifecycle_env, expected_current_receipt_digest="0" * 64
    )
    result = _correct(lifecycle_env, proposal=wrong_receipt, apply=False)
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_current_receipt_not_exact" in result.blocked_reasons


def test_correct_final_selector_binds_exact_canonical_authority(lifecycle_env) -> None:
    result = _correct(lifecycle_env)
    assert result.status == "committed", result.blocked_reasons
    assert result.current_state is not None
    raw = result.current_state.to_dict()
    assert raw["schema"] == SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA
    binding = raw["authority_binding"]
    assert binding["page_id"] == lifecycle_env["page"].page_id
    assert binding["canonical_page_digest"] == result._post_image_digest
    assert binding["authorization_ref"]["authority_id"] == result.transition_id
    assert binding["current_receipt_id"] == result.receipt_id
    receipt = lifecycle_env["store"].read_record(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        record_kind="subjective_mem_lifecycle_receipt",
        record_id=result.receipt_id,
    )
    assert isinstance(receipt, dict)
    assert receipt["current_state_digest"] == canonical_digest(raw)


def test_correct_same_key_changed_operation_time_conflicts(lifecycle_env) -> None:
    first = _correct(lifecycle_env)
    assert first.status == "committed"
    second = correct_subjective_mem(
        store=lifecycle_env["store"],
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        character_config=lifecycle_env["config"],
        character_authority=lifecycle_env["authority"],
        workspace_root=str(lifecycle_env["workspace_root"]),
        operation_idempotency_key="lc1a-correct-operation",
        proposal=_proposal(lifecycle_env),
        apply_enabled=True,
        committed_at=NOW + timedelta(seconds=4),
        observed_at=NOW + timedelta(seconds=5),
    )
    assert second.status == "integrity_conflict"


def test_correct_tampered_durable_intent_fails_closed(lifecycle_env) -> None:
    def crash(stage: str) -> None:
        if stage == "after_intent_before_page":
            raise RuntimeError("simulated")

    assert _correct(lifecycle_env, fault=crash).status == "recovery_pending"
    intent_paths = [
        path for path in lifecycle_env["store"].root.rglob("*.json")
        if "subjective_mem_lifecycle_intent" in str(path)
        and "finalization" not in str(path)
    ]
    assert len(intent_paths) == 1
    raw = json.loads(intent_paths[0].read_text(encoding="utf-8"))
    raw["artifact_id"] = "smartifact_" + "0" * 64
    intent_paths[0].write_text(
        json.dumps(raw, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    retry = _correct(lifecycle_env)
    assert retry.status == "fail_closed"
    assert "subjective_mem_lifecycle_intent_corrupt" in retry.blocked_reasons


def test_correct_pre_image_authority_is_revalidated_under_lock(
    lifecycle_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    def crash(stage: str) -> None:
        if stage == "after_intent_before_page":
            raise RuntimeError("simulated")

    before = lifecycle_env["page_path"].read_bytes()
    assert _correct(lifecycle_env, fault=crash).status == "recovery_pending"
    monkeypatch.setattr(
        lifecycle_engine,
        "_pre_image_authority_current",
        lambda **_kwargs: False,
    )
    retry = _correct(lifecycle_env)
    assert retry.status == "recovery_pending"
    assert "subjective_mem_commit_pre_image_authority_changed" in retry.blocked_reasons
    assert lifecycle_env["page_path"].read_bytes() == before


def test_correct_requires_reachable_predecessor_transition(lifecycle_env) -> None:
    first = _correct(lifecycle_env)
    assert first.status == "committed", first.blocked_reasons
    assert first.transition_id is not None and first.current_state is not None
    transition_path = lifecycle_env["store"]._record_path(  # noqa: SLF001
        lifecycle_env["captured"].evidence_space_id,
        "subjective_mem_lifecycle_transition",
        first.transition_id,
    )
    transition_path.unlink()
    page, reasons = parse_subjective_mem_page_bytes(
        lifecycle_env["page_path"].read_bytes()
    )
    assert page is not None and not reasons
    current_block = next(item for item in page.blocks if item.revision.memory_revision == 2)
    receipt = lifecycle_env["store"].read_record(
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        record_kind="subjective_mem_lifecycle_receipt",
        record_id=first.receipt_id,
    )
    assert isinstance(receipt, dict)
    proposal = _proposal(
        lifecycle_env,
        expected_current_revision=2,
        expected_block_id=current_block.block_id,
        expected_page_digest=page.page_digest,
        expected_current_selector_digest=canonical_digest(first.current_state.to_dict()),
        expected_current_receipt_id=first.receipt_id,
        expected_current_receipt_digest=receipt["receipt_digest"],
        corrected_subjective_meaning="A later exact correction.",
        authorization_id="user-correction-authorization-2",
    )
    result = correct_subjective_mem(
        store=lifecycle_env["store"],
        evidence_space_id=lifecycle_env["captured"].evidence_space_id,
        character_config=lifecycle_env["config"],
        character_authority=lifecycle_env["authority"],
        workspace_root=str(lifecycle_env["workspace_root"]),
        operation_idempotency_key="lc1a-correct-operation-2",
        proposal=proposal,
        apply_enabled=False,
        committed_at=NOW + timedelta(seconds=4),
        observed_at=NOW + timedelta(seconds=5),
    )
    assert result.status == "fail_closed"
    assert "subjective_mem_lifecycle_predecessor_authority_missing" in result.blocked_reasons


def test_markdown_successor_rejects_changed_formation_snapshot(lifecycle_env) -> None:
    first = _correct(lifecycle_env)
    assert first.status == "committed"
    page, reasons = parse_subjective_mem_page_bytes(
        lifecycle_env["page_path"].read_bytes()
    )
    assert page is not None and not reasons
    predecessor = next(item.revision for item in page.blocks if item.revision.memory_revision == 2)
    changed_snapshot = replace(
        predecessor.formation_snapshot,
        soul_revision=predecessor.formation_snapshot.soul_revision + "-changed",
    )
    successor = replace(
        predecessor,
        memory_revision=3,
        predecessor_revision_or_null=2,
        formation_snapshot=changed_snapshot,
        decision_id="transition-changed-snapshot",
        created_at=(NOW + timedelta(seconds=6)).isoformat(),
    )
    planned = plan_subjective_mem_revision_successor(
        predecessor=predecessor,
        successor=successor,
        existing_bytes=lifecycle_env["page_path"].read_bytes(),
    )
    assert planned.plan is None
    assert "subjective_mem_markdown_revision_chain_invalid" in planned.reasons


def test_correct_production_path_executes_through_the_shared_engine(
    lifecycle_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def recorded(name: str):
        real = getattr(lifecycle_engine, name)

        def wrapper(**kwargs):
            calls.append(name)
            return real(**kwargs)

        return wrapper

    for name in (
        "read_lifecycle_reservation",
        "reserve_lifecycle_publication",
        "publish_lifecycle_post_image",
    ):
        monkeypatch.setattr(lifecycle_runtime, name, recorded(name))
    result = _correct(lifecycle_env)
    assert result.status == "committed", result.blocked_reasons
    assert calls == [
        "read_lifecycle_reservation",
        "reserve_lifecycle_publication",
        "publish_lifecycle_post_image",
    ]


def test_shared_engine_never_imports_a_lifecycle_operation_owner() -> None:
    source = Path("relaylm/subjective_mem_lifecycle_engine.py").read_text(encoding="utf-8")
    assert "subjective_mem_lifecycle_runtime" not in source
    assert "subjective_mem_forget_runtime" not in source
    assert "relaymem_primary" not in source
    for dynamic in (
        "Protocol",
        "importlib",
        "sys.modules",
        "ContextVar",
        "monkeypatch",
        "registry",
        "factory",
        "plugin",
    ):
        assert dynamic not in source


def test_moved_publication_bodies_are_absent_from_correct_runtime() -> None:
    source = Path("relaylm/subjective_mem_lifecycle_runtime.py").read_text(encoding="utf-8")
    for moved in (
        "def _persist_prepared(",
        "def _publish_and_finalize(",
        "def _finalize_operations(",
        "def _resolve_final_replay(",
        "def _mark_recovery_required(",
        "def _read_claim_and_intent(",
        "def _state_from_intent(",
        "def _claim_from_intent(",
        "def _final_records_exact_locked(",
        "def _any_final_record_present_locked(",
        "def _validate_pre_image_authority_current(",
    ):
        assert moved not in source
    for owned_by_engine in (
        "publish_canonical_page",
        "write_immutable_rendered_artifact",
        "read_immutable_rendered_artifact",
    ):
        assert owned_by_engine not in source


def test_correct_keeps_one_engine_execution_path_without_fallback() -> None:
    source = Path("relaylm/subjective_mem_lifecycle_runtime.py").read_text(encoding="utf-8")
    assert source.count("from relaylm.subjective_mem_lifecycle_engine import") == 1
    for bypass in ("ImportError", "importlib", "sys.modules", "fallback", "ContextVar"):
        assert bypass not in source


def test_correct_retired_legacy_predecessor_validators() -> None:
    source = Path("relaylm/subjective_mem_lifecycle_runtime.py").read_text(encoding="utf-8")
    assert "from relaylm.subjective_mem.lifecycle_authority import" in source
    assert "load_subjective_mem_predecessor_authority_locked(" in source
    for retired in (
        "_validate_evidence_space_locked",
        "_validate_current_receipt_locked",
        "_validate_predecessor_authority_locked",
        "_receipt_self_authentic",
        "EvidenceSpaceDescriptor",
        "ST1_RECEIPT_SCHEMA",
    ):
        assert retired not in source


def test_shared_engine_records_and_outcomes_stay_content_free() -> None:
    assert {item.name for item in fields(lifecycle_engine.LifecycleExecutionOutcome)} == {
        "status",
        "reasons",
        "current_state",
        "recovery_outcome",
        "canonical_page_published",
        "lifecycle_receipt_present",
        "persisted",
    }
    assert {item.name for item in fields(lifecycle_engine.LifecycleFinalRecords)} == {
        "transition",
        "receipt",
        "finalization",
        "result",
        "projection",
    }


def _reservation_plan(lifecycle_env, monkeypatch):
    """Capture the exact production reservation plan without performing any write."""

    seen: dict[str, object] = {}

    def capture(*, store, plan, post_image, fault_injector=None):
        seen["plan"] = plan
        seen["post_image"] = post_image
        return lifecycle_engine.LifecycleExecutionOutcome(
            "fail_closed", ("subjective_mem_lifecycle_capture_only",)
        )

    monkeypatch.setattr(lifecycle_runtime, "reserve_lifecycle_publication", capture)
    _correct(lifecycle_env)
    plan = seen["plan"]
    assert isinstance(plan, lifecycle_engine.LifecyclePublicationPlan)
    assert plan.current_state is not None
    monkeypatch.undo()
    return plan, seen["post_image"]


def _durable_state(lifecycle_env):
    """Snapshot every durable surface a reservation is allowed to touch."""

    store = lifecycle_env["store"]
    space = lifecycle_env["captured"].evidence_space_id
    selector = lifecycle_env["st1"].current_state
    artifacts = lifecycle_env["workspace_root"] / (
        "char1/.relaylm/state/subjective_mem_st1/artifacts"
    )
    return {
        "artifacts": sorted(item.name for item in artifacts.glob("*")),
        "lifecycle_records": sorted(
            str(item.relative_to(store.root))
            for item in store.root.rglob("*lifecycle*")
        ),
        "selector": store.read_log(
            evidence_space_id=space,
            log_kind="subjective_mem_current_state",
            key=selector.memory_state_id,
        ),
        "page": lifecycle_env["page_path"].read_bytes(),
    }


def test_reservation_rejects_pre_state_not_derived_from_this_plan(
    lifecycle_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, post_image = _reservation_plan(lifecycle_env, monkeypatch)
    before = _durable_state(lifecycle_env)
    bound_current = replace(
        plan.prepared_state, mutation_state="none", retrieval_eligible=True
    )
    substitutions = {
        "subjective_mem_lifecycle_plan_pre_state_missing": None,
        # an unrelated logical memory
        "foreign_memory": replace(plan.current_state, memory_id="smmem-unrelated"),
        # a selector that is already reserved by someone else
        "already_reserved": replace(
            plan.current_state, mutation_state="prepared", retrieval_eligible=False
        ),
        # an already-bound selector whose canonical binding does not carry over
        "rebound": replace(bound_current, block_id="smblock_" + "0" * 64),
        # a selector pointing at a different revision
        "wrong_revision": replace(
            plan.current_state, current_revision=plan.current_state.current_revision + 1
        ),
    }
    for label, candidate in substitutions.items():
        outcome = lifecycle_engine.reserve_lifecycle_publication(
            store=lifecycle_env["store"],
            plan=replace(plan, current_state=candidate),
            post_image=post_image,
        )
        assert outcome.status == "fail_closed", label
        expected = (
            "subjective_mem_lifecycle_plan_pre_state_missing"
            if candidate is None
            else "subjective_mem_lifecycle_plan_pre_state_not_exact"
        )
        assert outcome.reasons == (expected,), (label, outcome.reasons)
        assert outcome.persisted is False, label
        assert _durable_state(lifecycle_env) == before, label


def test_reservation_and_publication_reject_post_image_before_any_write(
    lifecycle_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, post_image = _reservation_plan(lifecycle_env, monkeypatch)
    before = _durable_state(lifecycle_env)
    foreign_block = "smblock_" + "0" * 64
    candidates = {
        "foreign_bytes": (plan, b"# foreign\n"),
        "pre_image_bytes": (plan, lifecycle_env["page_path"].read_bytes()),
        "not_bytes": (plan, "# not bytes\n"),
        # exact digest, but the plan's successor binding no longer matches
        "unbound_successor": (
            replace(
                plan,
                successor_block_id=foreign_block,
                prepared_intent={
                    **plan.prepared_intent,
                    "successor_block_id": foreign_block,
                },
            ),
            post_image,
        ),
    }
    for label, (candidate_plan, candidate_bytes) in candidates.items():
        reserved = lifecycle_engine.reserve_lifecycle_publication(
            store=lifecycle_env["store"],
            plan=candidate_plan,
            post_image=candidate_bytes,
        )
        assert reserved.status == "fail_closed", label
        assert reserved.reasons == (
            "subjective_mem_lifecycle_post_image_not_exact",
        ), (label, reserved.reasons)
        assert reserved.persisted is False, label

        published = lifecycle_engine.publish_lifecycle_post_image(
            store=lifecycle_env["store"],
            plan=candidate_plan,
            post_image=candidate_bytes,
            finalizer=lambda _state: None,
        )
        assert published.status == "fail_closed", label
        assert published.reasons == (
            "subjective_mem_lifecycle_post_image_not_exact",
        ), (label, published.reasons)
        assert published.canonical_page_published is False, label
        assert _durable_state(lifecycle_env) == before, label
