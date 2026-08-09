"""ST-1 canonical Subjective MEM publication/finalization tests."""
from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path

import pytest

import relaylm._subjective_mem_commit_io as commit_io
import relaylm.subjective_mem_commit_runtime as commit_runtime
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from relaylm.character_workspace import (
    INTERNAL_DIRECTORIES,
    LOWERCASE_WORKSPACE_DIRECTORIES,
    REQUIRED_SOURCE_FILENAMES,
    validate_character_workspace,
)
from relaylm.config import RelayLMConfig
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.portable_lock import acquire_portable_lock, release_portable_lock
from relaylm.subjective_mem import SubjectiveMemCurrentState
from relaylm.subjective_mem_commit_runtime import (
    finalize_subjective_mem_create,
    resolve_subjective_mem_commit_gate,
    validate_finalized_subjective_mem_operation,
)
from relaylm.subjective_mem_markdown import (
    BLOCK_SCHEMA,
    MAX_CANONICAL_PAGE_BLOCKS,
    PAGE_SCHEMA,
    parse_subjective_mem_page_bytes,
    plan_subjective_mem_page,
    subjective_mem_block_identity,
    subjective_mem_page_identity,
)
from test_subjective_mem_runtime import (
    BASE_CONFIG,
    CHARACTER_CONFIG,
    NOW,
    _asm_ready,
    _character,
    _create,
    _proposal,
)


def _make_workspace(root: Path, character_id: str = "char1") -> Path:
    workspace_root = root / "characters"
    character_root = workspace_root / character_id
    character_root.mkdir(parents=True)
    for filename in REQUIRED_SOURCE_FILENAMES:
        (character_root / filename).write_text(f"# {filename}\n", encoding="utf-8")
    for relative in LOWERCASE_WORKSPACE_DIRECTORIES + INTERNAL_DIRECTORIES:
        (character_root / relative).mkdir(parents=True, exist_ok=True)
    result = validate_character_workspace(
        character_root, character_id=character_id, public=False
    )
    assert result.is_valid, result.errors
    return workspace_root.resolve()


@pytest.fixture()
def prepared(tmp_path: Path):
    workspace_root = _make_workspace(tmp_path)
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    captured, assessment_revision, assessment_state = _asm_ready(store)
    sm1 = _create(store, captured, assessment_revision, assessment_state)
    assert sm1.status == "committed"
    assert sm1.revision is not None
    config = CHARACTER_CONFIG.model_copy(
        update={"subjective_mem_workspace_root": str(workspace_root)}
    )
    return {
        "store": store,
        "captured": captured,
        "assessment_revision": assessment_revision,
        "assessment_state": assessment_state,
        "sm1": sm1,
        "workspace_root": workspace_root,
        "config": config,
        "authority": _character(),
    }


def _commit(
    env,
    *,
    apply: bool = True,
    fault=None,
    workspace_root: Path | None = None,
    character_config=None,
    finalized_at=None,
):
    return finalize_subjective_mem_create(
        store=env["store"],
        evidence_space_id=env["captured"].evidence_space_id,
        character_config=character_config or env["config"],
        character_authority=env["authority"],
        workspace_root=str(workspace_root or env["workspace_root"]),
        sm1_operation_idempotency_key="sm1-create-operation",
        apply_enabled=apply,
        finalized_at=finalized_at or NOW + timedelta(seconds=1),
        observed_at=(finalized_at or NOW + timedelta(seconds=1)) + timedelta(seconds=1),
        fault_injector=fault,
    )


def test_markdown_render_parse_roundtrip_is_deterministic(prepared) -> None:
    revision = prepared["sm1"].revision
    assert revision is not None
    first = plan_subjective_mem_page(revision=revision, existing_bytes=None)
    second = plan_subjective_mem_page(revision=revision, existing_bytes=None)
    assert first.plan is not None and second.plan is not None
    assert first.plan.rendered_bytes == second.plan.rendered_bytes
    assert first.plan.post_image_digest == second.plan.post_image_digest
    page, reasons = parse_subjective_mem_page_bytes(
        first.plan.rendered_bytes,
        expected_page_id=first.plan.page_id,
        expected_character_id="char1",
        expected_partition="episodes",
    )
    assert page is not None and not reasons
    assert len(page.blocks) == 1
    assert page.blocks[0].revision.to_dict() == revision.to_dict()
    assert PAGE_SCHEMA.encode() in first.plan.rendered_bytes
    assert BLOCK_SCHEMA.encode() in first.plan.rendered_bytes


def test_block_identity_does_not_depend_on_path_heading_or_order(prepared) -> None:
    revision = prepared["sm1"].revision
    assert revision is not None
    expected = subjective_mem_block_identity(revision.memory_id)
    page_id, path, partition = subjective_mem_page_identity(
        character_id=revision.character_id, memory_kind=revision.memory_kind
    )
    assert expected == subjective_mem_block_identity(revision.memory_id)
    assert page_id.startswith("smpage_")
    assert path == "memory/episodes/subjective-mem-v1.md"
    assert partition == "episodes"
    assert revision.memory_id not in path


def test_markdown_rejects_duplicate_logical_block_and_invalid_utf8(prepared) -> None:
    revision = prepared["sm1"].revision
    assert revision is not None
    plan = plan_subjective_mem_page(revision=revision, existing_bytes=None).plan
    assert plan is not None
    header, block = plan.rendered_bytes.split(b"## Subjective MEM revision 1", 1)
    duplicate = header + b"## Subjective MEM revision 1" + block + b"## Subjective MEM revision 1" + block
    page, reasons = parse_subjective_mem_page_bytes(duplicate)
    assert page is None
    assert any("duplicate" in item for item in reasons)
    page, reasons = parse_subjective_mem_page_bytes(b"\xff\xfe")
    assert page is None
    assert reasons == ("subjective_mem_markdown_page_not_utf8",)


def test_dry_run_validates_without_writes(prepared) -> None:
    result = _commit(prepared, apply=False)
    assert result.status == "dry_run_ready"
    character_root = prepared["workspace_root"] / "char1"
    assert not (character_root / "memory/episodes/subjective-mem-v1.md").exists()
    assert not (character_root / ".relaylm/state/subjective_mem_st1").exists()
    assert list((prepared["store"].root).rglob("*st1*")) == []


def test_happy_path_publishes_and_finalizes_exact_state(prepared) -> None:
    result = _commit(prepared)
    assert result.status == "committed", result.blocked_reasons
    assert result.canonical_markdown_published is True
    assert result.commit_receipt_present is True
    assert result.current_state is not None
    assert result.current_state.mutation_state == "none"
    assert result.current_state.retrieval_eligible is True
    assert result.receipt is not None
    assert result.receipt.to_dict()["ordinary_retrieval_wired"] is False
    assert result.receipt.to_dict()["projection_state"] == "rebuild_required"

    page_path = (
        prepared["workspace_root"]
        / "char1/memory/episodes/subjective-mem-v1.md"
    )
    page, reasons = parse_subjective_mem_page_bytes(page_path.read_bytes())
    assert page is not None and not reasons
    assert len(page.blocks) == 1
    assert page.blocks[0].revision.to_dict()["retrieval_visible"] is True

    schema = json.loads(
        Path(
            "docs/contracts/schemas/subjective-mem-v1/relaylm-subjective-mem-v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(
        {
            "records": [
                prepared["sm1"].decision.to_dict(),
                prepared["sm1"].revision.to_dict(),
                result.current_state.to_dict(),
            ]
        }
    )


def test_exact_st1_retry_is_duplicate_finalized(prepared) -> None:
    first = _commit(prepared)
    second = _commit(prepared)
    assert first.status == "committed"
    assert second.status == "duplicate_finalized", second.blocked_reasons
    assert second.finalization_id == first.finalization_id
    assert second.page_id == first.page_id
    assert second.block_id == first.block_id
    assert second.receipt == first.receipt


def test_page_present_receipt_missing_rolls_forward(prepared) -> None:
    def crash(stage: str) -> None:
        if stage == "after_page_before_receipt":
            raise RuntimeError("simulated")

    first = _commit(prepared, fault=crash)
    assert first.status == "recovery_pending"
    assert first.recovery_outcome == "post_image_pending_receipt"
    assert first.canonical_markdown_published is True
    second = _commit(prepared)
    assert second.status == "committed", second.blocked_reasons
    assert second.recovery_outcome == "post_image_rolled_forward"


def test_foreign_image_is_never_overwritten(prepared) -> None:
    def stop_before_staging(stage: str) -> None:
        if stage == "before_staging":
            raise RuntimeError("simulated")

    first = _commit(prepared, fault=stop_before_staging)
    assert first.status == "fail_closed"
    page = (
        prepared["workspace_root"]
        / "char1/memory/episodes/subjective-mem-v1.md"
    )
    page.write_text("# foreign\n", encoding="utf-8")
    second = _commit(prepared)
    assert second.status == "recovery_required"
    assert second.recovery_outcome == "foreign_image"
    assert page.read_text(encoding="utf-8") == "# foreign\n"


def test_receipt_without_page_fails_closed(prepared) -> None:
    committed = _commit(prepared)
    assert committed.status == "committed"
    page = (
        prepared["workspace_root"]
        / "char1/memory/episodes/subjective-mem-v1.md"
    )
    page.unlink()
    result = validate_finalized_subjective_mem_operation(
        store=prepared["store"],
        evidence_space_id=prepared["captured"].evidence_space_id,
        character_config=prepared["config"],
        character_authority=prepared["authority"],
        workspace_root=str(prepared["workspace_root"]),
        sm1_operation_idempotency_key="sm1-create-operation",
    )
    assert result.status == "fail_closed"
    assert result.recovery_outcome == "receipt_without_verifiable_page"


def test_sm1_same_input_retry_returns_finalized_identity(prepared) -> None:
    committed = _commit(prepared)
    assert committed.status == "committed"
    retry = _create(
        prepared["store"],
        prepared["captured"],
        prepared["assessment_revision"],
        prepared["assessment_state"],
        character_config=prepared["config"],
    )
    assert retry.status == "duplicate_finalized", retry.blocked_reasons
    assert retry.finalization_id == committed.finalization_id
    assert retry.canonical_page_id == committed.page_id
    assert retry.canonical_block_id == committed.block_id
    assert retry.current_state is not None
    assert retry.current_state.retrieval_eligible is True


def test_sm1_changed_input_remains_conflict_after_finalization(prepared) -> None:
    assert _commit(prepared).status == "committed"
    retry = _create(
        prepared["store"],
        prepared["captured"],
        prepared["assessment_revision"],
        prepared["assessment_state"],
        character_config=prepared["config"],
        proposal=_proposal(meaning="A changed meaning must conflict."),
    )
    assert retry.status == "integrity_conflict"
    assert retry.blocked_reasons == (
        "subjective_mem_operation_idempotency_conflict",
    )


def test_operations_records_do_not_contain_memory_body(prepared) -> None:
    result = _commit(prepared)
    assert result.status == "committed"
    forbidden = (
        prepared["sm1"].revision.grounded_content,
        prepared["sm1"].revision.subjective_meaning,
    )
    for kind in (
        "subjective_mem_st1_intent",
        "subjective_mem_st1_commit_receipt",
        "subjective_mem_st1_idempotency",
        "subjective_mem_st1_manifest_finalization",
        "subjective_mem_st1_intent_finalization",
        "subjective_mem_st1_projection_state",
    ):
        directory = prepared["store"].root / prepared["captured"].evidence_space_id / "records" / kind
        assert directory.is_dir()
        for path in directory.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            assert all(value not in text for value in forbidden)
    public = json.dumps(result.to_log_dict(), sort_keys=True)
    assert all(value not in public for value in forbidden)
    assert "memory/episodes" not in public


def test_target_page_symlink_is_rejected(prepared, tmp_path: Path) -> None:
    target = prepared["workspace_root"] / "char1/memory/episodes/subjective-mem-v1.md"
    foreign = tmp_path / "foreign.md"
    foreign.write_text("# foreign\n", encoding="utf-8")
    target.symlink_to(foreign)
    result = _commit(prepared)
    assert result.status == "fail_closed"
    assert "subjective_mem_commit_target_symlink" in result.blocked_reasons
    assert foreign.read_text(encoding="utf-8") == "# foreign\n"


def test_writer_lock_contention_is_bounded(prepared) -> None:
    lock_path = prepared["workspace_root"] / "char1/.relaylm/state/subjective_mem_st1.lock"
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        acquire_portable_lock(lock_fd, mode="exclusive", blocking=False)
        result = _commit(prepared)
        assert result.status == "lock_busy"
    finally:
        release_portable_lock(lock_fd)
        os.close(lock_fd)


def test_workspace_authority_change_fails_closed(prepared, tmp_path: Path) -> None:
    assert _commit(prepared).status == "committed"
    other_root = _make_workspace(tmp_path / "other")
    result = validate_finalized_subjective_mem_operation(
        store=prepared["store"],
        evidence_space_id=prepared["captured"].evidence_space_id,
        character_config=prepared["config"],
        character_authority=prepared["authority"],
        workspace_root=str(other_root),
        sm1_operation_idempotency_key="sm1-create-operation",
    )
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "subjective_mem_commit_workspace_authority_changed",
    )


def test_commit_gate_defaults_off_and_apply_requires_exact_prerequisites(tmp_path: Path) -> None:
    disabled = RelayLMConfig.model_validate(BASE_CONFIG)
    gate = resolve_subjective_mem_commit_gate(disabled)
    assert (gate.enabled, gate.dry_run_only, gate.apply_enabled) == (False, True, False)

    invalid = dict(BASE_CONFIG)
    invalid.update(
        subjective_mem_commit_enabled=True,
        subjective_mem_commit_dry_run_only=False,
        subjective_mem_commit_apply_enabled=True,
        subjective_mem_workspace_root=str((tmp_path / "characters").resolve()),
    )
    with pytest.raises(ValidationError):
        RelayLMConfig.model_validate(invalid)

    root = (tmp_path / "evidence").resolve()
    workspace = (tmp_path / "characters").resolve()
    valid = dict(BASE_CONFIG)
    valid.update(
        evidence_data_root=str(root),
        shared_assessment_enabled=True,
        shared_assessment_dry_run_only=False,
        shared_assessment_apply_enabled=True,
        subjective_mem_create_enabled=True,
        subjective_mem_create_dry_run_only=False,
        subjective_mem_create_apply_enabled=True,
        subjective_mem_commit_enabled=True,
        subjective_mem_commit_dry_run_only=False,
        subjective_mem_commit_apply_enabled=True,
        subjective_mem_workspace_root=str(workspace),
    )
    config = RelayLMConfig.model_validate(valid)
    gate = resolve_subjective_mem_commit_gate(config)
    assert gate.enabled is True
    assert gate.dry_run_only is False
    assert gate.apply_enabled is True


def test_page_capacity_has_no_heuristic_alternate_page(prepared) -> None:
    revision = prepared["sm1"].revision
    assert revision is not None
    first = plan_subjective_mem_page(revision=revision, existing_bytes=None).plan
    assert first is not None
    header, block = first.rendered_bytes.split(b"## Subjective MEM revision 1", 1)
    # The parser rejects duplicate identity before a caller can use a second page.
    full = header + (b"## Subjective MEM revision 1" + block) * (MAX_CANONICAL_PAGE_BLOCKS + 1)
    page, reasons = parse_subjective_mem_page_bytes(full)
    assert page is None
    assert reasons


def test_current_state_rejects_invalid_mutation_eligibility_pairs() -> None:
    with pytest.raises(ValueError, match="subjective_mem_current_state_pair_invalid"):
        SubjectiveMemCurrentState(
            memory_state_id="state",
            memory_id="memory",
            character_id="char1",
            updated_at=NOW.isoformat(),
            mutation_state="prepared",
            retrieval_eligible=True,
        )
    with pytest.raises(ValueError, match="subjective_mem_current_state_pair_invalid"):
        SubjectiveMemCurrentState(
            memory_state_id="state",
            memory_id="memory",
            character_id="char1",
            updated_at=NOW.isoformat(),
            mutation_state="none",
            retrieval_eligible=False,
        )


def test_malformed_unrelated_block_is_rejected(prepared) -> None:
    revision = prepared["sm1"].revision
    assert revision is not None
    plan = plan_subjective_mem_page(revision=revision, existing_bytes=None).plan
    assert plan is not None
    header, body = plan.rendered_bytes.split(b"## Subjective MEM revision 1", 1)
    malformed = header + b"## unrelated\n\ntext\n" + b"## Subjective MEM revision 1" + body
    page, reasons = parse_subjective_mem_page_bytes(malformed)
    assert page is None
    assert reasons == ("subjective_mem_markdown_block_malformed",)


def test_target_hardlink_is_rejected(prepared, tmp_path: Path) -> None:
    target = prepared["workspace_root"] / "char1/memory/episodes/subjective-mem-v1.md"
    foreign = tmp_path / "foreign-hardlink.md"
    foreign.write_text("# foreign\n", encoding="utf-8")
    os.link(foreign, target)
    result = _commit(prepared)
    assert result.status == "fail_closed"
    assert "subjective_mem_commit_target_link_count_invalid" in result.blocked_reasons
    assert foreign.read_text(encoding="utf-8") == "# foreign\n"


def test_corrupt_immutable_artifact_requires_reconciliation(prepared) -> None:
    def stop_before_staging(stage: str) -> None:
        if stage == "before_staging":
            raise RuntimeError("simulated")

    first = _commit(prepared, fault=stop_before_staging)
    assert first.status == "fail_closed"
    intents = list(
        (
            prepared["store"].root
            / prepared["captured"].evidence_space_id
            / "records/subjective_mem_st1_intent"
        ).glob("*.json")
    )
    assert len(intents) == 1
    intent = json.loads(intents[0].read_text(encoding="utf-8"))
    artifact = (
        prepared["workspace_root"]
        / "char1/.relaylm/state/subjective_mem_st1/artifacts"
        / f"{intent['artifact_id']}.md"
    )
    artifact.write_text("corrupt\n", encoding="utf-8")
    retry = _commit(prepared)
    assert retry.status == "recovery_required"
    assert retry.recovery_outcome == "artifact_unverifiable"
    assert retry.blocked_reasons == (
        "subjective_mem_commit_artifact_digest_mismatch",
    )


def test_partial_finalization_never_advances_selector(prepared) -> None:
    def crash(stage: str) -> None:
        if stage == "after_page_before_receipt":
            raise RuntimeError("simulated")

    first = _commit(prepared, fault=crash)
    assert first.status == "recovery_pending"
    assert first.finalization_id is not None
    with prepared["store"].transaction(prepared["captured"].evidence_space_id) as tx:
        commit = tx.commit(
            transaction_id="test-partial-st1-finalization",
            records=((
                "subjective_mem_st1_idempotency",
                first.finalization_id,
                {"schema": "test.partial", "status": "partial"},
            ),),
            logs=(),
        )
    assert commit.status == "created"
    retry = _commit(prepared)
    assert retry.status == "recovery_pending"
    assert "subjective_mem_commit_partial_finalization_conflict" in retry.blocked_reasons
    operation_files = list(
        (
            prepared["store"].root
            / prepared["captured"].evidence_space_id
            / "records/subjective_mem_operation"
        ).glob("*.json")
    )
    assert len(operation_files) == 1
    operation = json.loads(operation_files[0].read_text(encoding="utf-8"))
    with prepared["store"].transaction(prepared["captured"].evidence_space_id) as tx:
        state = tx.read_log(
            log_kind="subjective_mem_current_state",
            key=operation["current_state_key"],
        )
    assert state is not None
    latest = state[-1]
    assert latest["mutation_state"] == "prepared"
    assert latest["retrieval_eligible"] is False


def test_recovery_uses_original_intent_time(prepared) -> None:
    def crash(stage: str) -> None:
        if stage == "after_page_before_receipt":
            raise RuntimeError("simulated")

    first_time = NOW + timedelta(seconds=1)
    retry_time = NOW + timedelta(minutes=5)
    first = _commit(prepared, fault=crash, finalized_at=first_time)
    assert first.status == "recovery_pending"
    retry = _commit(prepared, finalized_at=retry_time)
    assert retry.status == "committed"
    assert retry.receipt is not None
    assert retry.receipt.finalized_at == first_time.isoformat()


def test_character_workspace_symlink_is_rejected(prepared, tmp_path: Path) -> None:
    alternate_root = tmp_path / "alternate-characters"
    alternate_root.mkdir()
    (alternate_root / "char1").symlink_to(
        prepared["workspace_root"] / "char1", target_is_directory=True
    )
    alternate = alternate_root.resolve()
    config = prepared["config"].model_copy(
        update={"subjective_mem_workspace_root": str(alternate)}
    )
    result = _commit(
        prepared, workspace_root=alternate, character_config=config
    )
    assert result.status == "fail_closed"
    assert "subjective_mem_commit_character_workspace_symlink" in result.blocked_reasons


def test_workspace_root_symlink_is_rejected(prepared, tmp_path: Path) -> None:
    linked_root = tmp_path / "linked-characters"
    linked_root.symlink_to(prepared["workspace_root"], target_is_directory=True)
    linked = linked_root.absolute()
    config = prepared["config"].model_copy(
        update={"subjective_mem_workspace_root": str(linked)}
    )
    result = _commit(prepared, workspace_root=linked, character_config=config)
    assert result.status == "fail_closed"
    assert "subjective_mem_commit_workspace_root_symlink" in result.blocked_reasons


def test_non_regular_page_parent_is_rejected(prepared) -> None:
    episodes = prepared["workspace_root"] / "char1/memory/episodes"
    episodes.rmdir()
    episodes.write_text("not a directory\n", encoding="utf-8")
    result = _commit(prepared)
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "subjective_mem_commit_character_workspace_not_valid",
    )


def test_artifact_cleanup_failure_never_reports_success(
    prepared, monkeypatch: pytest.MonkeyPatch
) -> None:
    revision = prepared["sm1"].revision
    assert revision is not None
    plan = plan_subjective_mem_page(revision=revision, existing_bytes=None).plan
    assert plan is not None
    monkeypatch.setattr(commit_io, "_remove_temp_and_sync", lambda **_kwargs: False)
    result = commit_io.write_immutable_rendered_artifact(
        workspace_root=str(prepared["workspace_root"]),
        character_id="char1",
        artifact_id=plan.artifact_id,
        data=plan.rendered_bytes,
    )
    assert result.status == "failed"
    assert result.reasons == ("subjective_mem_commit_artifact_cleanup_failed",)


def test_foreign_image_after_staging_is_not_overwritten(prepared) -> None:
    target = (
        prepared["workspace_root"]
        / "char1/memory/episodes/subjective-mem-v1.md"
    )

    def external_edit(stage: str) -> None:
        if stage == "after_staging_before_replace":
            target.write_text("# foreign after staging\n", encoding="utf-8")

    result = _commit(prepared, fault=external_edit)
    assert result.status == "recovery_required"
    assert result.recovery_outcome == "foreign_image"
    assert target.read_text(encoding="utf-8") == "# foreign after staging\n"


def test_initial_workspace_must_match_configured_authority(
    prepared, tmp_path: Path
) -> None:
    other_root = _make_workspace(tmp_path / "mismatch")
    result = _commit(prepared, workspace_root=other_root)
    assert result.status == "fail_closed"
    assert result.blocked_reasons == (
        "subjective_mem_commit_workspace_authority_changed",
    )


def test_semantically_equivalent_noncanonical_json_is_rejected(prepared) -> None:
    revision = prepared["sm1"].revision
    assert revision is not None
    plan = plan_subjective_mem_page(revision=revision, existing_bytes=None).plan
    assert plan is not None
    changed = plan.rendered_bytes.replace(
        b'"memory_revision": 1', b'"memory_revision":  1', 1
    )
    page, reasons = parse_subjective_mem_page_bytes(changed)
    assert page is None
    assert reasons == ("subjective_mem_markdown_block_noncanonical",)


def test_apply_gate_fails_closed_when_secure_platform_is_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = (tmp_path / "evidence").resolve()
    workspace = (tmp_path / "characters").resolve()
    raw = dict(BASE_CONFIG)
    raw.update(
        evidence_data_root=str(root),
        shared_assessment_enabled=True,
        shared_assessment_dry_run_only=False,
        shared_assessment_apply_enabled=True,
        subjective_mem_create_enabled=True,
        subjective_mem_create_dry_run_only=False,
        subjective_mem_create_apply_enabled=True,
        subjective_mem_commit_enabled=True,
        subjective_mem_commit_dry_run_only=False,
        subjective_mem_commit_apply_enabled=True,
        subjective_mem_workspace_root=str(workspace),
    )
    config = RelayLMConfig.model_validate(raw)
    monkeypatch.setattr(commit_runtime, "secure_platform_supported", lambda: False)
    gate = resolve_subjective_mem_commit_gate(config)
    assert gate.enabled is True
    assert gate.dry_run_only is False
    assert gate.apply_enabled is False
