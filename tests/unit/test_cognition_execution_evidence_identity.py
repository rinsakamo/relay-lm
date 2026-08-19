from __future__ import annotations

import pytest

from relaylm.cognition_execution_evidence import (
    BUFFERED_EXECUTION_PATH,
    CONVERSATION_OUTPUT_CONTRACT,
    EXTRACTION_OUTPUT_CONTRACT,
    SINGLE_PASS_OUTPUT_CONTRACT,
    STREAMING_EXECUTION_PATH,
    CognitionExecutionEvidenceIdentity,
)


def test_single_pass_identity_has_one_canonical_output_contract() -> None:
    identity = CognitionExecutionEvidenceIdentity.single_pass(
        execution_path=BUFFERED_EXECUTION_PATH
    )

    assert identity.mode == "single_pass"
    assert identity.canonical_output_contract == SINGLE_PASS_OUTPUT_CONTRACT
    assert identity.conversation_output_contract is None
    assert identity.extraction_output_contract is None
    assert identity.shadow_output_contract is None
    assert identity.canonical_mutation_source == "single_pass"


def test_two_pass_identity_binds_both_pass_contracts() -> None:
    identity = CognitionExecutionEvidenceIdentity.two_pass(
        execution_path=STREAMING_EXECUTION_PATH
    )

    assert identity.mode == "two_pass"
    assert identity.execution_path == "streaming"
    assert identity.canonical_output_contract is None
    assert identity.conversation_output_contract == CONVERSATION_OUTPUT_CONTRACT
    assert identity.extraction_output_contract == EXTRACTION_OUTPUT_CONTRACT
    assert identity.shadow_output_contract is None
    assert identity.canonical_mutation_source == "pass2"


def test_execution_evidence_identity_rejects_auto_and_incoherent_shapes() -> None:
    with pytest.raises(ValueError, match="auto"):
        CognitionExecutionEvidenceIdentity(
            mode="auto",
            execution_path="buffered",
            canonical_output_contract=None,
            conversation_output_contract=None,
            extraction_output_contract=None,
            shadow_output_contract=None,
            canonical_mutation_source="single_pass",
        )

    with pytest.raises(ValueError, match="single_pass identity"):
        CognitionExecutionEvidenceIdentity(
            mode="single_pass",
            execution_path="buffered",
            canonical_output_contract=None,
            conversation_output_contract=None,
            extraction_output_contract=None,
            shadow_output_contract=None,
            canonical_mutation_source="single_pass",
        )
