from __future__ import annotations

import importlib

import pytest

from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
)


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


def test_capacity_format_converges_before_any_real_artifact_exists() -> None:
    capacity = _capacity_module()

    assert capacity.VLLM_RUNTIME_CAPACITY_EVIDENCE_FORMAT_VERSION == 2


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

    class Evidence:
        scenario_set_revision = scenario_revision
        footprints = (
            type("Observation", (), {"coverage": required[0]})(),
        )

    with pytest.raises(capacity.VLLMRuntimeCapacityEvidenceError, match="coverage"):
        validate(
            evidence=Evidence(),
            scenario_set_revision=scenario_revision,
            required_coverage=required,
        )

    Evidence.footprints = tuple(
        type("Observation", (), {"coverage": item})() for item in required
    )
    validate(
        evidence=Evidence(),
        scenario_set_revision=scenario_revision,
        required_coverage=required,
    )

    with pytest.raises(capacity.VLLMRuntimeCapacityEvidenceError, match="scenario"):
        validate(
            evidence=Evidence(),
            scenario_set_revision="sha256:" + "b" * 64,
            required_coverage=required,
        )
