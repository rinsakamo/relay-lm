"""LC-1E Subjective MEM Consolidate proposal and identity contract tests."""
from __future__ import annotations

from dataclasses import replace
import inspect

import relaylm.subjective_mem_consolidate as consolidate_contract
from relaylm.subjective_mem_consolidate import (
    CONSOLIDATE_AUTHORIZATION_CLASS,
    CONSOLIDATE_OPERATION_FAMILY,
    CONSOLIDATE_POLICY_REVISION,
    CONSOLIDATE_PREDECESSOR_AUTHORIZATION_KINDS,
    CONSOLIDATE_REASON_CATEGORY,
    SubjectiveMemConsolidateBoundary,
    SubjectiveMemConsolidateProposal,
    derive_subjective_mem_consolidate_operation_identity,
    subjective_mem_consolidate_transition,
    validate_subjective_mem_consolidate_proposal,
)

HEX = "a" * 64
OTHER_HEX = "b" * 64
THIRD_HEX = "c" * 64
PAGE_DIGEST = "sha256:" + "d" * 64
TIME = "2026-07-27T15:00:00+00:00"


def _proposal(**changes: object) -> SubjectiveMemConsolidateProposal:
    base = SubjectiveMemConsolidateProposal(
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
        expected_current_authorization_kind="subjective_mem_lifecycle_transition",
        expected_current_authorization_id="transition-1",
        expected_current_authorization_digest=THIRD_HEX,
        expected_memory_kind="episodic",
        expected_formation_stage="primary",
        expected_scope_binding_digest=HEX,
        expected_formation_snapshot_digest=OTHER_HEX,
        expected_strength_digest=THIRD_HEX,
        expected_revision_schema="relaylm.subjective_mem_revision.v1",
        expected_page_schema="relaylm.subjective_mem_markdown_page.v1",
        expected_block_schema="relaylm.subjective_mem_markdown_block.v2",
        expected_renderer_revision="relaylm.subjective_mem_markdown_renderer.v1",
        expected_partition_revision="relaylm.subjective_mem_page_partition.v1",
        expected_platform_revision="relaylm.subjective_mem_commit_platform.posix.v1",
        authorization_class=CONSOLIDATE_AUTHORIZATION_CLASS,
        authorization_id="authorization-1",
        reason_category=CONSOLIDATE_REASON_CATEGORY,
        policy_revision=CONSOLIDATE_POLICY_REVISION,
        boundary=SubjectiveMemConsolidateBoundary(),
    )
    return replace(base, **changes)


def _identity(
    proposal: SubjectiveMemConsolidateProposal, *, key: str = "operation-key-1"
):
    identity, reasons = derive_subjective_mem_consolidate_operation_identity(
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
    assert subjective_mem_consolidate_transition() == (
        "active",
        "active",
        "primary",
        "secondary",
    )


def test_valid_proposal_is_content_free_and_policy_bound() -> None:
    proposal = _proposal()
    assert validate_subjective_mem_consolidate_proposal(proposal) == ()
    payload = proposal.to_digest_input()
    assert payload["operation_family"] == CONSOLIDATE_OPERATION_FAMILY
    assert payload["operation_kind"] == "consolidate"
    assert payload["authorization_class"] == CONSOLIDATE_AUTHORIZATION_CLASS
    assert payload["reason_category"] == CONSOLIDATE_REASON_CATEGORY
    rendered = repr(payload)
    assert "grounded_content" not in rendered
    assert "subjective_meaning" not in rendered
    assert "summary" not in rendered
    assert "retrieval_count" not in rendered


def test_non_proposal_fails_closed() -> None:
    assert validate_subjective_mem_consolidate_proposal(object()) == (
        "subjective_mem_consolidate_proposal_invalid",
    )


def test_state_direction_and_stage_fail_closed() -> None:
    invalid = (
        _proposal(expected_lifecycle_state="pinned"),
        _proposal(expected_formation_stage="secondary"),
        _proposal(expected_mutation_state="prepared"),
        _proposal(expected_current_revision=0),
        _proposal(expected_memory_kind="product"),
    )
    expected = (
        "subjective_mem_consolidate_transition_direction_invalid",
        "subjective_mem_consolidate_formation_stage_invalid",
        "subjective_mem_consolidate_mutation_state_invalid",
        "subjective_mem_consolidate_current_revision_invalid",
        "subjective_mem_consolidate_memory_kind_invalid",
    )
    for proposal, reason in zip(invalid, expected, strict=True):
        assert reason in validate_subjective_mem_consolidate_proposal(proposal)


def test_policy_authorization_has_no_user_or_operator_fallback() -> None:
    invalid = (
        _proposal(authorization_class="user_management"),
        _proposal(authorization_class="operator_management"),
        _proposal(reason_category="user_requested_consolidation"),
        _proposal(reason_category="operator_requested_consolidation"),
    )
    expected = (
        "subjective_mem_consolidate_authorization_class_invalid",
        "subjective_mem_consolidate_authorization_class_invalid",
        "subjective_mem_consolidate_reason_category_invalid",
        "subjective_mem_consolidate_reason_category_invalid",
    )
    for proposal, reason in zip(invalid, expected, strict=True):
        assert reason in validate_subjective_mem_consolidate_proposal(proposal)


def test_exact_consolidate_policy_revision_is_required() -> None:
    assert validate_subjective_mem_consolidate_proposal(
        _proposal(policy_revision=CONSOLIDATE_POLICY_REVISION)
    ) == ()
    for other in (
        "relaylm.subjective_mem_consolidation_policy.v2",
        "relaylm.subjective_mem_lifecycle_policy.v1",
    ):
        assert (
            "subjective_mem_consolidate_policy_revision_invalid"
            in validate_subjective_mem_consolidate_proposal(
                _proposal(policy_revision=other)
            )
        )


def test_revision_one_formation_decision_predecessor_authority_is_accepted() -> None:
    proposal = _proposal(
        expected_current_revision=1,
        expected_current_authorization_kind="subjective_mem_decision",
        expected_current_authorization_id="decision-1",
    )
    assert validate_subjective_mem_consolidate_proposal(proposal) == ()
    payload = proposal.to_digest_input()
    assert payload["expected_current_authorization_kind"] == "subjective_mem_decision"
    assert payload["expected_current_authorization_id"] == "decision-1"


def test_later_lifecycle_transition_predecessor_authority_is_accepted() -> None:
    proposal = _proposal(
        expected_current_revision=4,
        expected_current_authorization_kind="subjective_mem_lifecycle_transition",
        expected_current_authorization_id="transition-4",
    )
    assert validate_subjective_mem_consolidate_proposal(proposal) == ()
    assert CONSOLIDATE_PREDECESSOR_AUTHORIZATION_KINDS == {
        "subjective_mem_decision",
        "subjective_mem_lifecycle_transition",
    }


def test_unsupported_predecessor_authorization_kind_fails_closed() -> None:
    for kind in ("formation_decision", "lifecycle_transition", "user_management"):
        assert (
            "subjective_mem_consolidate_current_authorization_kind_invalid"
            in validate_subjective_mem_consolidate_proposal(
                _proposal(expected_current_authorization_kind=kind)
            )
        )


def test_transition_only_predecessor_fields_are_absent() -> None:
    fields = set(_proposal().to_digest_input())
    assert "expected_current_transition_id" not in fields
    assert "expected_current_transition_digest" not in fields
    assert not hasattr(_proposal(), "expected_current_transition_id")
    assert not hasattr(_proposal(), "expected_current_transition_digest")
    source = inspect.getsource(consolidate_contract)
    assert "expected_current_transition_id" not in source
    assert "expected_current_transition_digest" not in source


def test_operation_authorization_id_is_distinct_from_predecessor_authority() -> None:
    base = _proposal()
    assert base.authorization_id != base.expected_current_authorization_id
    payload = base.to_digest_input()
    assert payload["authorization_id"] == "authorization-1"
    assert payload["expected_current_authorization_id"] == "transition-1"


def test_path_digest_identifier_and_boundary_validation() -> None:
    invalid = (
        _proposal(expected_relative_path="../outside.md"),
        _proposal(expected_relative_path="memory//episodes/subjective-mem-v1.md"),
        _proposal(expected_relative_path="memory/episodes/subjective-mem-v1.md\0bad"),
        _proposal(expected_page_digest=HEX),
        _proposal(expected_strength_digest="not-a-digest"),
        _proposal(expected_current_authorization_id="bad id"),
        _proposal(
            boundary=replace(
                SubjectiveMemConsolidateBoundary(), strength_preserved=False
            )
        ),
    )
    expected = (
        "subjective_mem_consolidate_relative_path_invalid",
        "subjective_mem_consolidate_relative_path_invalid",
        "subjective_mem_consolidate_relative_path_invalid",
        "subjective_mem_consolidate_page_digest_invalid",
        "subjective_mem_consolidate_digest_invalid",
        "subjective_mem_consolidate_identifier_invalid",
        "subjective_mem_consolidate_boundary_invalid",
    )
    for proposal, reason in zip(invalid, expected, strict=True):
        assert reason in validate_subjective_mem_consolidate_proposal(proposal)


def test_proposal_digest_binds_current_authority_strength_and_policy() -> None:
    base = _proposal()
    changed = (
        _proposal(expected_current_revision=2),
        _proposal(expected_current_selector_digest=OTHER_HEX),
        _proposal(expected_current_receipt_digest=HEX),
        _proposal(expected_current_authorization_kind="subjective_mem_decision"),
        _proposal(expected_current_authorization_id="transition-2"),
        _proposal(expected_current_authorization_digest=HEX),
        _proposal(expected_strength_digest=HEX),
        _proposal(policy_revision="relaylm.subjective_mem_consolidation_policy.v2"),
        _proposal(authorization_id="authorization-2"),
    )
    assert all(item.input_digest != base.input_digest for item in changed)


def test_operation_family_slot_detects_changed_proposal_key_reuse() -> None:
    base = _proposal()
    changed = _proposal(expected_current_revision=2)
    first = _identity(base)
    exact_retry = _identity(base)
    changed_identity = _identity(changed)

    assert exact_retry == first
    assert changed_identity.operation_slot_id == first.operation_slot_id
    assert changed_identity.result_id == first.result_id
    assert changed_identity.operation_id != first.operation_id
    assert changed_identity.transition_id != first.transition_id
    assert changed_identity.input_digest != first.input_digest


def test_identity_memory_must_match_proposal() -> None:
    identity, reasons = derive_subjective_mem_consolidate_operation_identity(
        evidence_space_id="evidence-space-1",
        character_authority_digest=HEX,
        memory_id="other-memory",
        operation_idempotency_key="operation-key-1",
        proposal=_proposal(),
        operation_time=TIME,
    )
    assert identity is None
    assert "subjective_mem_consolidate_memory_identity_mismatch" in reasons


def test_operation_time_is_canonicalized_before_identity() -> None:
    proposal = _proposal()
    utc_identity = _identity(proposal)
    offset_identity, reasons = derive_subjective_mem_consolidate_operation_identity(
        evidence_space_id="evidence-space-1",
        character_authority_digest=HEX,
        memory_id=proposal.expected_memory_id,
        operation_idempotency_key="operation-key-1",
        proposal=proposal,
        operation_time="2026-07-28T00:00:00+09:00",
    )
    assert offset_identity is not None, reasons
    assert offset_identity == utc_identity


def test_raw_idempotency_key_is_never_serialized() -> None:
    raw_key = "caller-secret-key"
    identity = _identity(_proposal(), key=raw_key)
    assert raw_key not in repr(identity.to_dict())
    assert identity.operation_key_digest != raw_key


def test_invalid_identity_inputs_return_bounded_reasons() -> None:
    identity, reasons = derive_subjective_mem_consolidate_operation_identity(
        evidence_space_id="../bad",
        character_authority_digest="bad",
        memory_id="memory-1",
        operation_idempotency_key="bad key",
        proposal=_proposal(),
        operation_time="not-a-time",
    )
    assert identity is None
    assert set(reasons) == {
        "subjective_mem_consolidate_operation_identity_invalid",
        "subjective_mem_consolidate_character_authority_digest_invalid",
        "subjective_mem_consolidate_idempotency_key_invalid",
        "subjective_mem_consolidate_operation_time_invalid",
    }


def test_module_has_no_runtime_policy_or_primary_mem_backdoor_import() -> None:
    source = inspect.getsource(consolidate_contract)
    assert "relaymem_primary" not in source
    assert "subjective_mem.lifecycle_runtime" not in source
    assert "subjective_mem_consolidate_runtime" not in source
    assert "relaymem_slp" not in source
    assert "ContextVar" not in source
