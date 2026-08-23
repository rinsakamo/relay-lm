from __future__ import annotations

import importlib

import pytest

from relaylm.budget_enforcement import TokenCountMode
from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
)
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity


def _capacity_module():
    return importlib.import_module("relaylm.actual_model_vllm_capacity")


def _request(*, bounded: bool = False) -> CognitionPassRequest:
    return CognitionPassRequest(
        reasoning_mode=(
            CognitionReasoningMode.BOUNDED if bounded else CognitionReasoningMode.OFF
        ),
        reasoning_budget=16 if bounded else None,
        temperature=0,
        top_p=1,
    )


def _counter_identity() -> SerializedInputCounterIdentity:
    return SerializedInputCounterIdentity(
        capability="vllm.serving-tokenizer.serialized-input.v1",
        implementation="vllm-tokenize-endpoint-counter",
        version="1",
        mode=TokenCountMode.EXACT,
        tokenizer_identity="hf-snapshot-tokenizer:sha256:" + "1" * 64,
        parameters=(
            ("backend", "vllm"),
            ("backend_version", "0.27.1"),
            ("chat_template_identity", "hf-snapshot-chat-template:sha256:" + "2" * 64),
            ("context_limit", 2048),
            ("framing_method", "same-message-shape-empty-content-v1"),
            ("renderer_method", "chat-completion-effective-template-kwargs-v1"),
            ("request_model", "gemma-4-12B-it-qat-w4a16"),
            ("target_id", "gemma-4-12b-it-qat-w4a16-vllm-v1"),
        ),
    )


def test_capacity_format_converges_before_any_real_artifact_exists() -> None:
    capacity = _capacity_module()

    assert capacity.VLLM_RUNTIME_CAPACITY_EVIDENCE_FORMAT_VERSION == 3


def test_pass_request_identity_distinguishes_off_from_bounded_without_payload_text() -> None:
    capacity = _capacity_module()
    identify = getattr(capacity, "vllm_capacity_pass_request_id", None)

    assert callable(identify)
    off_id = identify(_request())
    bounded_id = identify(_request(bounded=True))

    assert off_id.startswith("amcpr-")
    assert bounded_id.startswith("amcpr-")
    assert len(off_id) == len("amcpr-") + 64
    assert len(bounded_id) == len("amcpr-") + 64
    assert off_id != bounded_id
    assert identify(_request()) == off_id


def test_coverage_validator_requires_exact_scenario_revision_and_full_required_matrix() -> None:
    capacity = _capacity_module()
    Coverage = getattr(capacity, "VLLMCapacityFootprintCoverage", None)
    validate = getattr(capacity, "validate_capacity_coverage", None)

    assert Coverage is not None
    assert callable(validate)

    pass1_id = capacity.vllm_capacity_pass_request_id(_request())
    pass2_id = capacity.vllm_capacity_pass_request_id(_request(bounded=True))
    scenario_revision = "sha256:" + "a" * 64

    required = (
        Coverage(
            condition_id="C",
            topology="two_pass",
            pass_id="pass1",
            scenario_id="response-persona-correction-v1",
            turn_index=1,
            pass_request_id=pass1_id,
        ),
        Coverage(
            condition_id="C",
            topology="two_pass",
            pass_id="pass2",
            scenario_id="response-persona-correction-v1",
            turn_index=1,
            pass_request_id=pass2_id,
        ),
    )
    observations = tuple(
        capacity.VLLMCapacityFootprintObservation(
            condition_id=item.condition_id,
            topology=item.topology,
            pass_id=item.pass_id,
            scenario_id=item.scenario_id,
            turn_index=item.turn_index,
            pass_request_id=item.pass_request_id,
            total_input_tokens=900 + index,
            required_input_framing_tokens=100,
            count_mode=TokenCountMode.EXACT,
        )
        for index, item in enumerate(required)
    )

    def evidence(footprints):
        return capacity.VLLMRuntimeCapacityEvidence(
            relaylm_commit="b" * 40,
            target_id="gemma-4-12b-it-qat-w4a16-vllm-v1",
            target_revision="sha256:" + "c" * 64,
            tokenizer_identity="hf-snapshot-tokenizer:sha256:" + "1" * 64,
            chat_template_identity="hf-snapshot-chat-template:sha256:" + "2" * 64,
            backend_version="0.27.1",
            request_model="gemma-4-12B-it-qat-w4a16",
            observed_max_model_len=2048,
            scenario_set_revision=scenario_revision,
            counter_identity=_counter_identity(),
            footprints=tuple(footprints),
            model_runner="v2",
        )

    with pytest.raises(capacity.VLLMRuntimeCapacityEvidenceError, match="coverage"):
        validate(
            evidence=evidence(observations[:1]),
            scenario_set_revision=scenario_revision,
            required_coverage=required,
        )

    validate(
        evidence=evidence(observations),
        scenario_set_revision=scenario_revision,
        required_coverage=required,
    )

    with pytest.raises(capacity.VLLMRuntimeCapacityEvidenceError, match="scenario"):
        validate(
            evidence=evidence(observations),
            scenario_set_revision="sha256:" + "d" * 64,
            required_coverage=required,
        )
