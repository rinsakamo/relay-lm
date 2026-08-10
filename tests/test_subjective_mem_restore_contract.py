"""LC-1D Subjective MEM Restore proposal and identity contract tests."""
from __future__ import annotations

from dataclasses import replace
import inspect

import relaylm.subjective_mem_restore as restore_contract
from relaylm.subjective_mem_restore import (
    RESTORE_OPERATION_FAMILY,
    SubjectiveMemRestoreBoundary,
    SubjectiveMemRestoreProposal,
    derive_subjective_mem_restore_operation_identity,
    subjective_mem_restore_transition,
    validate_subjective_mem_restore_proposal,
)

HEX = "a" * 64
OTHER_HEX = "b" * 64
THIRD_HEX = "c" * 64
FOURTH_HEX = "d" * 64
PAGE_DIGEST = "sha256:" + "e" * 64
TIME = "2026-07-26T01:00:00+00:00"


def _proposal(**changes: object) -> SubjectiveMemRestoreProposal:
    base = SubjectiveMemRestoreProposal(
        expected_memory_id="memory-1",
        expected_current_revision=2,
        expected_lifecycle_state="hidden",
        expected_mutation_state="none",
        expected_page_id="page-1",
        expected_relative_path="memory/episodes/subjective-mem-v1.md",
        expected_block_id="block-2",
        expected_page_digest=PAGE_DIGEST,
        expected_current_selector_id="selector-1",
        expected_current_selector_digest=HEX,
        expected_current_receipt_id="forget-receipt-1",
        expected_current_receipt_digest=OTHER_HEX,
        expected_forget_transition_id="forget-transition-1",
        expected_forget_transition_digest=THIRD_HEX,
        expected_forget_tombstone_id="forget-tombstone-1",
        expected_forget_tombstone_digest=FOURTH_HEX,
        expected_semantic_identity_digest=HEX,
        expected_memory_kind="episodic",
        expected_formation_stage="primary",
        expected_scope_binding_digest=OTHER_HEX,
        expected_formation_snapshot_digest=THIRD_HEX,
        expected_revision_schema="relaylm.subjective_mem_revision.v1",
        expected_page_schema="relaylm.subjective_mem_markdown_page.v1",
        expected_block_schema="relaylm.subjective_mem_markdown_block.v2",
        expected_renderer_revision="relaylm.subjective_mem_markdown_renderer.v1",
        expected_partition_revision="relaylm.subjective_mem_page_partition.v1",
        expected_platform_revision="relaylm.subjective_mem_commit_platform.posix.v1",
        authorization_class="user_management",
        authorization_id="authorization-1",
        reason_category="user_requested_restore",
        policy_revision="relaylm.subjective_mem_lifecycle_policy.v1",
        boundary=SubjectiveMemRestoreBoundary(),
    )
    return replace(base, **changes)


def _identity(
    proposal: SubjectiveMemRestoreProposal, *, key: str = "operation-key-1"
):
    identity, reasons = derive_subjective_mem_restore_operation_identity(
        evidence_space_id="evidence-space-1",
        character_authority_digest=HEX,
        memory_id=proposal.expected_memory_id,
        operation_idempotency_key=key,
        proposal=proposal,
        operation_time=TIME,
    )
    assert identity is not None, reasons
    return identity


def test_transition_is_exact_and_closed() -> None:
    assert subjective_mem_restore_transition() == ("hidden", "active")


def test_valid_restore_proposal_is_content_free() -> None:
    proposal = _proposal()
    assert validate_subjective_mem_restore_proposal(proposal) == ()
    payload = proposal.to_digest_input()
    assert payload["operation_family"] == RESTORE_OPERATION_FAMILY
    assert payload["operation_kind"] == "restore"
    assert "grounded_content" not in repr(payload)
    assert "subjective_meaning" not in repr(payload)
    assert "raw_reason" not in repr(payload)
    assert "memory/mem" not in repr(payload)


def test_direction_mutation_and_hidden_revision_fail_closed() -> None:
    invalid = (
        _proposal(expected_lifecycle_state="active"),
        _proposal(expected_mutation_state="prepared"),
        _proposal(expected_current_revision=1),
    )
    expected = (
        "subjective_mem_restore_transition_direction_invalid",
        "subjective_mem_restore_mutation_state_invalid",
        "subjective_mem_restore_current_revision_invalid",
    )
    for proposal, reason in zip(invalid, expected, strict=True):
        assert reason in validate_subjective_mem_restore_proposal(proposal)


def test_authorization_and_reason_pair_must_match() -> None:
    mismatch = _proposal(authorization_class="operator_management")
    assert (
        "subjective_mem_restore_authorization_reason_mismatch"
        in validate_subjective_mem_restore_proposal(mismatch)
    )

    operator = _proposal(
        authorization_class="operator_management",
        reason_category="operator_requested_restore",
    )
    assert validate_subjective_mem_restore_proposal(operator) == ()

    invalid_reason = _proposal(reason_category="user_requested_forget")
    assert (
        "subjective_mem_restore_reason_category_invalid"
        in validate_subjective_mem_restore_proposal(invalid_reason)
    )


def test_forget_lineage_path_digest_and_boundary_validation() -> None:
    invalid = (
        _proposal(expected_forget_transition_id="bad id"),
        _proposal(expected_forget_transition_digest="not-a-digest"),
        _proposal(expected_forget_tombstone_digest="not-a-digest"),
        _proposal(expected_semantic_identity_digest="not-a-digest"),
        _proposal(expected_relative_path="../outside.md"),
        _proposal(expected_page_digest=HEX),
        _proposal(
            boundary=replace(
                SubjectiveMemRestoreBoundary(),
                immutable_tombstone_release_required=False,
            )
        ),
    )
    expected = (
        "subjective_mem_restore_identifier_invalid",
        "subjective_mem_restore_digest_invalid",
        "subjective_mem_restore_digest_invalid",
        "subjective_mem_restore_digest_invalid",
        "subjective_mem_restore_relative_path_invalid",
        "subjective_mem_restore_page_digest_invalid",
        "subjective_mem_restore_boundary_invalid",
    )
    for proposal, reason in zip(invalid, expected, strict=True):
        assert reason in validate_subjective_mem_restore_proposal(proposal)


def test_proposal_digest_binds_restore_and_forget_authority() -> None:
    base = _proposal()
    changed = (
        _proposal(expected_current_revision=3),
        _proposal(expected_current_selector_digest=OTHER_HEX),
        _proposal(expected_current_receipt_digest=THIRD_HEX),
        _proposal(expected_forget_transition_digest=FOURTH_HEX),
        _proposal(expected_forget_tombstone_id="forget-tombstone-2"),
        _proposal(expected_forget_tombstone_digest=HEX),
        _proposal(expected_semantic_identity_digest=OTHER_HEX),
        _proposal(authorization_id="authorization-2"),
        _proposal(
            authorization_class="operator_management",
            reason_category="operator_requested_restore",
        ),
    )
    assert all(item.input_digest != base.input_digest for item in changed)


def test_identity_memory_must_match_proposal() -> None:
    identity, reasons = derive_subjective_mem_restore_operation_identity(
        evidence_space_id="evidence-space-1",
        character_authority_digest=HEX,
        memory_id="other-memory",
        operation_idempotency_key="operation-key-1",
        proposal=_proposal(),
        operation_time=TIME,
    )
    assert identity is None
    assert "subjective_mem_restore_memory_identity_mismatch" in reasons


def test_exact_retry_and_changed_input_share_only_the_slot() -> None:
    proposal = _proposal()
    exact = _identity(proposal)
    retry = _identity(proposal)
    changed = _identity(_proposal(expected_forget_tombstone_id="forget-tombstone-2"))

    assert retry == exact
    assert changed.operation_slot_id == exact.operation_slot_id
    assert changed.result_id == exact.result_id
    assert changed.operation_id != exact.operation_id
    assert changed.transition_id != exact.transition_id
    assert changed.release_id != exact.release_id
    assert changed.input_digest != exact.input_digest


def test_operation_time_is_canonicalized_before_identity() -> None:
    proposal = _proposal()
    utc_identity = _identity(proposal)
    offset_identity, reasons = derive_subjective_mem_restore_operation_identity(
        evidence_space_id="evidence-space-1",
        character_authority_digest=HEX,
        memory_id=proposal.expected_memory_id,
        operation_idempotency_key="operation-key-1",
        proposal=proposal,
        operation_time="2026-07-26T10:00:00+09:00",
    )
    assert offset_identity is not None, reasons
    assert offset_identity == utc_identity


def test_identity_includes_deterministic_content_free_release_id() -> None:
    identity = _identity(_proposal())
    payload = identity.to_dict()
    assert payload["release_id"].startswith("smrestorerelease_")
    assert payload["release_id"] == identity.release_id
    assert "forget-tombstone-1" not in repr(payload)


def test_raw_idempotency_key_is_never_serialized() -> None:
    raw_key = "caller-secret-key"
    identity = _identity(_proposal(), key=raw_key)
    assert raw_key not in repr(identity.to_dict())
    assert identity.operation_key_digest != raw_key


def test_invalid_identity_inputs_return_bounded_reasons() -> None:
    identity, reasons = derive_subjective_mem_restore_operation_identity(
        evidence_space_id="../bad",
        character_authority_digest="bad",
        memory_id="memory-1",
        operation_idempotency_key="bad key",
        proposal=_proposal(),
        operation_time="not-a-time",
    )
    assert identity is None
    assert set(reasons) == {
        "subjective_mem_restore_operation_identity_invalid",
        "subjective_mem_restore_character_authority_digest_invalid",
        "subjective_mem_restore_idempotency_key_invalid",
        "subjective_mem_restore_operation_time_invalid",
    }


def test_non_proposal_input_fails_without_attribute_access() -> None:
    assert validate_subjective_mem_restore_proposal({}) == (
        "subjective_mem_restore_proposal_invalid",
    )
    identity, reasons = derive_subjective_mem_restore_operation_identity(
        evidence_space_id="evidence-space-1",
        character_authority_digest=HEX,
        memory_id="memory-1",
        operation_idempotency_key="operation-key-1",
        proposal={},  # type: ignore[arg-type]
        operation_time=TIME,
    )
    assert identity is None
    assert reasons == ("subjective_mem_restore_proposal_invalid",)


def test_module_has_no_runtime_primary_mem_or_backdoor_import() -> None:
    source = inspect.getsource(restore_contract)
    assert "relaymem_primary" not in source
    assert "subjective_mem.lifecycle_runtime" not in source
    assert "subjective_mem.forget_runtime" not in source
    assert "subjective_mem_reformation" not in source
    assert "ContextVar" not in source
