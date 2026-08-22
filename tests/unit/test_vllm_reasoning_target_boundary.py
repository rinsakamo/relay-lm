from types import SimpleNamespace

from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityStatus,
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
)


def _backend_attestation():
    return attest_vllm_backend(
        request_model="model-id",
        version_response={"version": "0.27.1"},
        models_response={
            "object": "list",
            "data": [
                {
                    "id": "model-id",
                    "object": "model",
                    "root": "/tmp/model",
                    "max_model_len": 1024,
                }
            ],
        },
    )


def _probe(
    controls: VLLMReasoningWireControls,
    *,
    activation_applied: bool = False,
    template_kwargs: tuple[tuple[str, str | int | bool], ...] = (),
) -> VLLMReasoningProbeEvidence:
    return VLLMReasoningProbeEvidence(
        wire_controls=controls,
        http_status=200,
        accepted=True,
        effect_proven=True,
        repeatable=True,
        activation_applied=activation_applied,
        template_kwargs=template_kwargs,
    )


def test_reasoning_attestation_consumes_only_structural_target_identity() -> None:
    target = SimpleNamespace(
        target_id="target-id",
        revision="target-revision",
        model_artifact_identity="artifact-id",
        artifact_repository_revision="artifact-revision",
    )

    attestation = attest_vllm_reasoning_capabilities(
        backend_attestation=_backend_attestation(),
        target=target,
        reasoning_parser="parser",
        template_thinking_control="enable_thinking",
        off_probe=_probe(VLLMReasoningWireControls(reasoning_effort="none")),
        bounded_probe=_probe(
            VLLMReasoningWireControls(thinking_token_budget=32),
            activation_applied=True,
            template_kwargs=(("enable_thinking", True),),
        ),
    )

    assert attestation.target_id == "target-id"
    assert attestation.target_revision == "target-revision"
    assert attestation.model_artifact_identity == "artifact-id"
    assert attestation.artifact_repository_revision == "artifact-revision"
    assert (
        attestation.reasoning_bounded.status
        is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    )
