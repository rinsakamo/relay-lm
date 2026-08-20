from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.actual_model_targets import (
    ActualModelRepositorySnapshotTarget,
    load_actual_model_repository_snapshot_target,
)
from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityStatus,
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)


def _target() -> ActualModelRepositorySnapshotTarget:
    return load_actual_model_repository_snapshot_target(TARGET_PATH)


def _backend_attestation():
    return attest_vllm_backend(
        request_model="gemma-4-12B-it-qat-w4a16",
        version_response={"version": "0.27.1"},
        models_response={
            "object": "list",
            "data": [
                {
                    "id": "gemma-4-12B-it-qat-w4a16",
                    "object": "model",
                    "root": "/tmp/relaylm-unsloth-w4a16-model",
                    "max_model_len": 1024,
                }
            ],
        },
    )


def _probe(
    controls: VLLMReasoningWireControls,
    *,
    accepted: bool = True,
    effect_proven: bool = True,
    repeatable: bool = True,
    activation_applied: bool = False,
    template_kwargs: tuple[tuple[str, str | int | bool], ...] = (),
    ambiguous: bool = False,
    http_status: int = 200,
) -> VLLMReasoningProbeEvidence:
    return VLLMReasoningProbeEvidence(
        wire_controls=controls,
        http_status=http_status,
        accepted=accepted,
        effect_proven=effect_proven,
        repeatable=repeatable,
        activation_applied=activation_applied,
        template_kwargs=template_kwargs,
        ambiguous=ambiguous,
    )


def test_attestation_binds_identity_and_classifies_observed_controls() -> None:
    target = _target()
    attestation = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=target,
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=_probe(
            VLLMReasoningWireControls(reasoning_effort="none"),
        ),
        bounded_probe=_probe(
            VLLMReasoningWireControls(thinking_token_budget=32),
            activation_applied=True,
            template_kwargs=(("enable_thinking", True),),
        ),
    )

    assert attestation.backend_version == "0.27.1"
    assert attestation.request_model == "gemma-4-12B-it-qat-w4a16"
    assert attestation.target_id == "gemma-4-12b-it-qat-w4a16-vllm-v1"
    assert (
        attestation.target_revision
        == "sha256:c0ff75a231cb4214856a2acfab7eea35da2b57c3f19409454b0dfc6ad5d45caa"
    )
    assert attestation.reasoning_parser == "gemma4"
    assert attestation.template_thinking_control == "enable_thinking"
    assert (
        attestation.reasoning_off.status
        is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    )
    assert dict(attestation.reasoning_off.probe_wire) == {
        "reasoning_effort": "none"
    }
    assert (
        attestation.reasoning_bounded.status
        is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    )
    assert dict(attestation.reasoning_bounded.probe_wire) == {
        "thinking_token_budget": 32
    }
    assert dict(attestation.reasoning_bounded.template_kwargs) == {
        "enable_thinking": True
    }
    assert attestation.to_mapping()["off_conflicting_template_kwargs"] == {
        "policy": "provider_must_reject",
        "control": "enable_thinking",
    }
    assert attestation.to_mapping()["reasoning_bounded"]["probe_evidence"] == {
        "http_status": 200,
        "accepted": True,
        "effect_proven": True,
        "repeatable": True,
        "ambiguous": False,
    }


def test_accepted_budget_without_effect_is_not_semantic_support() -> None:
    attestation = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=_target(),
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=_probe(VLLMReasoningWireControls(reasoning_effort="none")),
        bounded_probe=_probe(
            VLLMReasoningWireControls(thinking_token_budget=64),
            effect_proven=False,
            activation_applied=False,
        ),
    )

    assert (
        attestation.reasoning_bounded.status
        is VLLMReasoningCapabilityStatus.ACCEPTED_BUT_EFFECT_UNPROVEN
    )


def test_rejected_budget_is_unsupported_and_does_not_fallback() -> None:
    attestation = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=_target(),
        reasoning_parser=None,
        template_thinking_control=None,
        off_probe=_probe(VLLMReasoningWireControls(reasoning_effort="none")),
        bounded_probe=_probe(
            VLLMReasoningWireControls(thinking_token_budget=16),
            accepted=False,
            effect_proven=False,
            repeatable=False,
            http_status=400,
        ),
    )

    assert attestation.reasoning_bounded.status is VLLMReasoningCapabilityStatus.UNSUPPORTED
    assert dict(attestation.reasoning_bounded.probe_wire) == {
        "thinking_token_budget": 16
    }
    assert attestation.reasoning_bounded.fallback_wire == ()


def test_off_without_template_activation_context_is_not_attested() -> None:
    attestation = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=_target(),
        reasoning_parser=None,
        template_thinking_control=None,
        off_probe=_probe(VLLMReasoningWireControls(reasoning_effort="none")),
        bounded_probe=_probe(
            VLLMReasoningWireControls(thinking_token_budget=16),
            accepted=False,
            effect_proven=False,
            repeatable=False,
            http_status=400,
        ),
    )

    assert (
        attestation.reasoning_off.status
        is VLLMReasoningCapabilityStatus.ACCEPTED_BUT_EFFECT_UNPROVEN
    )


def test_conflicting_template_activation_fails_closed_for_off() -> None:
    attestation = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=_target(),
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=_probe(
            VLLMReasoningWireControls(reasoning_effort="none"),
            activation_applied=True,
            template_kwargs=(("enable_thinking", True),),
        ),
        bounded_probe=_probe(
            VLLMReasoningWireControls(thinking_token_budget=32),
            activation_applied=True,
            template_kwargs=(("enable_thinking", True),),
        ),
    )

    assert (
        attestation.reasoning_off.status
        is VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    )


def test_bounded_probe_without_numeric_budget_is_ambiguous() -> None:
    attestation = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=_target(),
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=_probe(VLLMReasoningWireControls(reasoning_effort="none")),
        bounded_probe=_probe(
            VLLMReasoningWireControls(reasoning_effort="low"),
            activation_applied=True,
            template_kwargs=(("enable_thinking", True),),
        ),
    )

    assert (
        attestation.reasoning_bounded.status
        is VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    )


def test_probe_must_match_the_control_it_claims_to_attest() -> None:
    off_mismatch = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=_target(),
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=_probe(VLLMReasoningWireControls(thinking_token_budget=16)),
        bounded_probe=_probe(
            VLLMReasoningWireControls(thinking_token_budget=32),
            activation_applied=True,
            template_kwargs=(("enable_thinking", True),),
        ),
    )
    bounded_mismatch = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=_target(),
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=_probe(VLLMReasoningWireControls(reasoning_effort="none")),
        bounded_probe=_probe(
            VLLMReasoningWireControls(
                reasoning_effort="none",
                thinking_token_budget=32,
            ),
            activation_applied=True,
            template_kwargs=(("enable_thinking", True),),
        ),
    )

    assert (
        off_mismatch.reasoning_off.status
        is VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    )
    assert (
        bounded_mismatch.reasoning_bounded.status
        is VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    )


def test_ambiguous_probe_is_classified_fail_closed() -> None:
    attestation = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=_target(),
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=_probe(
            VLLMReasoningWireControls(reasoning_effort="none"),
            ambiguous=True,
        ),
        bounded_probe=_probe(
            VLLMReasoningWireControls(thinking_token_budget=32),
            activation_applied=True,
            template_kwargs=(("enable_thinking", True),),
        ),
    )

    assert (
        attestation.reasoning_off.status
        is VLLMReasoningCapabilityStatus.MALFORMED_OR_AMBIGUOUS
    )


def test_probe_evidence_rejects_http_success_without_acceptance() -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        _probe(
            VLLMReasoningWireControls(reasoning_effort="none"),
            accepted=False,
            effect_proven=False,
            repeatable=False,
            http_status=200,
        )
