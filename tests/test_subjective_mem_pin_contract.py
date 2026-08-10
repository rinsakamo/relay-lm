"""LC-1C Subjective MEM Pin / Unpin proposal and identity contract tests."""
from __future__ import annotations

from dataclasses import replace
import inspect

import pytest

import relaylm.subjective_mem.pin as pin_contract
from relaylm.subjective_mem.pin import (
    PIN_OPERATION_FAMILY,
    SubjectiveMemPinBoundary,
    SubjectiveMemPinProposal,
    derive_subjective_mem_pin_operation_identity,
    subjective_mem_pin_transition,
    validate_subjective_mem_pin_proposal,
)

HEX = "a" * 64
OTHER_HEX = "b" * 64
PAGE_DIGEST = "sha256:" + "c" * 64
TIME = "2026-07-25T02:00:00+00:00"


def _proposal(**changes: object) -> SubjectiveMemPinProposal:
    base = SubjectiveMemPinProposal(
        operation_kind="pin",
        expected_memory_id="memory-1",
        expected_current_revision=1,
        expected_lifecycle_state="active",
        expected_mutation_state="none",
        expected_page_id="page-1",
        expected_relative_path="memory/episodes/subjective-mem-v1.md",
        expected_block_id="block-1",
        expected_page_digest=PAGE_DIGEST,
        expected_current_selector_id="selector-1",
        expected_current_selector_digest=HEX,
        expected_current_receipt_id="receipt-1",
        expected_current_receipt_digest=OTHER_HEX,
        expected_memory_kind="episodic",
        expected_formation_stage="primary",
        expected_scope_binding_digest=HEX,
        expected_formation_snapshot_digest=OTHER_HEX,
        expected_revision_schema="relaylm.subjective_mem_revision.v1",
        expected_page_schema="relaylm.subjective_mem_markdown_page.v1",
        expected_block_schema="relaylm.subjective_mem_markdown_block.v2",
        expected_renderer_revision="relaylm.subjective_mem_markdown_renderer.v1",
        expected_partition_revision="relaylm.subjective_mem_page_partition.v1",
        expected_platform_revision="relaylm.subjective_mem_commit_platform.posix.v1",
        authorization_class="user_management",
        authorization_id="authorization-1",
        reason_category="user_requested_pin",
        policy_revision="relaylm.subjective_mem_lifecycle_policy.v1",
        boundary=SubjectiveMemPinBoundary(),
    )
    return replace(base, **changes)


def _identity(proposal: SubjectiveMemPinProposal, *, key: str = "operation-key-1"):
    identity, reasons = derive_subjective_mem_pin_operation_identity(
        evidence_space_id="evidence-space-1",
        character_authority_digest=HEX,
        memory_id=proposal.expected_memory_id,
        operation_idempotency_key=key,
        proposal=proposal,
        operation_time=TIME,
    )
    assert identity is not None, reasons
    return identity


def test_transition_table_is_exact_and_closed() -> None:
    assert subjective_mem_pin_transition("pin") == ("active", "pinned")
    assert subjective_mem_pin_transition("unpin") == ("pinned", "active")
    with pytest.raises(ValueError, match="operation_kind_invalid"):
        subjective_mem_pin_transition("restore")


def test_valid_pin_and_unpin_proposals_are_content_free() -> None:
    pin = _proposal()
    unpin = _proposal(
        operation_kind="unpin",
        expected_lifecycle_state="pinned",
        reason_category="user_requested_unpin",
    )
    assert validate_subjective_mem_pin_proposal(pin) == ()
    assert validate_subjective_mem_pin_proposal(unpin) == ()
    for proposal in (pin, unpin):
        payload = proposal.to_digest_input()
        assert payload["operation_family"] == PIN_OPERATION_FAMILY
        assert "grounded_content" not in repr(payload)
        assert "subjective_meaning" not in repr(payload)
        assert "pin_state" not in repr(payload)
        assert "memory/mem/pins/v0" not in repr(payload)


def test_direction_reason_and_mutation_state_fail_closed() -> None:
    wrong_direction = _proposal(operation_kind="unpin")
    reasons = validate_subjective_mem_pin_proposal(wrong_direction)
    assert "subjective_mem_pin_transition_direction_invalid" in reasons
    assert "subjective_mem_pin_reason_category_invalid" in reasons

    wrong_reason = _proposal(reason_category="operator_requested_unpin")
    assert "subjective_mem_pin_reason_category_invalid" in validate_subjective_mem_pin_proposal(wrong_reason)

    prepared = _proposal(expected_mutation_state="prepared")
    assert "subjective_mem_pin_mutation_state_invalid" in validate_subjective_mem_pin_proposal(prepared)


def test_authority_digest_path_and_boundary_validation() -> None:
    invalid = (
        _proposal(authorization_class="relaymem_policy"),
        _proposal(expected_relative_path="../outside.md"),
        _proposal(expected_relative_path="memory//episodes/subjective-mem-v1.md"),
        _proposal(expected_relative_path="memory/episodes/subjective-mem-v1.md\0evil"),
        _proposal(expected_page_digest=HEX),
        _proposal(expected_current_selector_digest="not-a-digest"),
        _proposal(boundary=replace(SubjectiveMemPinBoundary(), semantic_payload_preserved=False)),
    )
    expected = (
        "subjective_mem_pin_authorization_class_invalid",
        "subjective_mem_pin_relative_path_invalid",
        "subjective_mem_pin_relative_path_invalid",
        "subjective_mem_pin_relative_path_invalid",
        "subjective_mem_pin_page_digest_invalid",
        "subjective_mem_pin_digest_invalid",
        "subjective_mem_pin_boundary_invalid",
    )
    for proposal, reason in zip(invalid, expected, strict=True):
        assert reason in validate_subjective_mem_pin_proposal(proposal)


def test_proposal_digest_binds_direction_and_all_authority_inputs() -> None:
    base = _proposal()
    changed = (
        _proposal(expected_current_revision=2),
        _proposal(authorization_id="authorization-2"),
        _proposal(reason_category="operator_requested_pin", authorization_class="operator_management"),
        _proposal(expected_current_selector_digest=OTHER_HEX),
        _proposal(
            operation_kind="unpin",
            expected_lifecycle_state="pinned",
            reason_category="user_requested_unpin",
        ),
    )
    assert all(item.input_digest != base.input_digest for item in changed)



def test_authorization_reason_pair_must_match() -> None:
    mismatch = _proposal(authorization_class="operator_management")
    assert "subjective_mem_pin_authorization_reason_mismatch" in validate_subjective_mem_pin_proposal(mismatch)


def test_identity_memory_must_match_proposal() -> None:
    identity, reasons = derive_subjective_mem_pin_operation_identity(
        evidence_space_id="evidence-space-1",
        character_authority_digest=HEX,
        memory_id="other-memory",
        operation_idempotency_key="operation-key-1",
        proposal=_proposal(),
        operation_time=TIME,
    )
    assert identity is None
    assert "subjective_mem_pin_memory_identity_mismatch" in reasons

def test_operation_family_slot_detects_cross_direction_key_reuse() -> None:
    pin = _proposal()
    unpin = _proposal(
        operation_kind="unpin",
        expected_lifecycle_state="pinned",
        reason_category="user_requested_unpin",
    )
    pin_identity = _identity(pin)
    exact_retry = _identity(pin)
    unpin_identity = _identity(unpin)

    assert exact_retry == pin_identity
    assert unpin_identity.operation_slot_id == pin_identity.operation_slot_id
    assert unpin_identity.result_id == pin_identity.result_id
    assert unpin_identity.operation_id != pin_identity.operation_id
    assert unpin_identity.transition_id != pin_identity.transition_id
    assert unpin_identity.input_digest != pin_identity.input_digest


def test_operation_time_is_canonicalized_before_identity() -> None:
    proposal = _proposal()
    utc_identity = _identity(proposal)
    offset_identity, reasons = derive_subjective_mem_pin_operation_identity(
        evidence_space_id="evidence-space-1",
        character_authority_digest=HEX,
        memory_id=proposal.expected_memory_id,
        operation_idempotency_key="operation-key-1",
        proposal=proposal,
        operation_time="2026-07-25T11:00:00+09:00",
    )
    assert offset_identity is not None, reasons
    assert offset_identity == utc_identity


def test_raw_idempotency_key_is_never_serialized() -> None:
    raw_key = "caller-secret-key"
    identity = _identity(_proposal(), key=raw_key)
    assert raw_key not in repr(identity.to_dict())
    assert identity.operation_key_digest != raw_key


def test_invalid_identity_inputs_return_bounded_reasons() -> None:
    identity, reasons = derive_subjective_mem_pin_operation_identity(
        evidence_space_id="../bad",
        character_authority_digest="bad",
        memory_id="memory-1",
        operation_idempotency_key="bad key",
        proposal=_proposal(),
        operation_time="not-a-time",
    )
    assert identity is None
    assert set(reasons) == {
        "subjective_mem_pin_operation_identity_invalid",
        "subjective_mem_pin_character_authority_digest_invalid",
        "subjective_mem_pin_idempotency_key_invalid",
        "subjective_mem_pin_operation_time_invalid",
    }


def test_module_has_no_primary_mem_or_runtime_backdoor_import() -> None:
    source = inspect.getsource(pin_contract)
    assert "relaymem_primary" not in source
    assert "subjective_mem.lifecycle_runtime" not in source
    assert "subjective_mem.forget_runtime" not in source
    assert "ContextVar" not in source
