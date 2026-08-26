from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.actual_model_fast_screening import (
    PASS2_REASONING_ESCALATION_ROLE,
    REFERENCE_BASELINE_ROLE,
    reference_screening_condition_roles,
    screening_condition_key_for_role,
)
from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.actual_model_vllm_host import (
    CANONICAL_SCENARIO_SET_PATH,
    CANONICAL_VLLM_SCREENING_PLAN_PATH,
    ActualModelVLLMHostError,
    _required_capacity_coverage,
    load_vllm_screening_plan,
)
from relaylm.cognition_execution import CognitionStructuredOutputMode


_ROOT = Path(__file__).parents[2]
_SCREENING_ROOT = _ROOT / "evaluation" / "actual_model" / "screenings"
_CURRENT_STAGE_R_FIXTURE_TESTS = (
    "tests/unit/test_actual_model_vllm_host_dispatch.py",
    "tests/unit/test_actual_model_vllm_budget_facade.py",
    "tests/unit/test_actual_model_vllm_host_timing.py",
    "tests/unit/test_actual_model_vllm_bound_timing.py",
)


def test_superseded_current_stage_r_v1_plan_is_not_retained() -> None:
    assert not (_SCREENING_ROOT / "stage-r0-vllm-reference-v1.json").exists()


@pytest.mark.parametrize("relative_path", _CURRENT_STAGE_R_FIXTURE_TESTS)
def test_current_stage_r_fixture_tests_do_not_encode_historical_plan_coordinates(
    relative_path: str,
) -> None:
    source = (_ROOT / relative_path).read_text(encoding="utf-8")

    assert "stage-r0-vllm-reference-v1" not in source
    assert '"B"' not in source


def test_current_stage_r_plan_uses_semantic_roles_without_historical_coordinates() -> None:
    historical = load_vllm_screening_plan(
        _SCREENING_ROOT / "cogp5-vllm-screening-v1.json"
    )
    current = load_vllm_screening_plan(_ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH)

    assert historical.format_version == 1
    assert historical.screening_id == "cogp5-vllm-screening-v1"
    assert historical.effective_context_window == 1024
    assert historical.capacity_evidence_id is None
    assert tuple(historical.conditions) == ("A", "B", "C")

    assert current.format_version == 2
    assert current.screening_id == "stage-r0-vllm-reference-v2"
    assert current.target_id == "gemma-4-12b-it-qat-w4a16-google-vllm-v1"
    assert current.capacity_evidence_id is None
    assert current.scenario_ids == (
        "response-persona-correction-v1",
        "continuity-lifecycle-v1",
    )
    assert tuple(current.conditions) == (
        REFERENCE_BASELINE_ROLE,
        PASS2_REASONING_ESCALATION_ROLE,
    )
    assert all(
        condition.cognition_execution.mode == "two_pass"
        for condition in current.conditions.values()
    )
    assert screening_condition_key_for_role(
        current,
        REFERENCE_BASELINE_ROLE,
    ) == REFERENCE_BASELINE_ROLE
    assert screening_condition_key_for_role(
        current,
        PASS2_REASONING_ESCALATION_ROLE,
    ) == PASS2_REASONING_ESCALATION_ROLE
    assert reference_screening_condition_roles(current) == (REFERENCE_BASELINE_ROLE,)

    reference = current.conditions[REFERENCE_BASELINE_ROLE]
    assert reference.condition_id == "stage-r0-vllm-b-two-pass-off-off"
    assert reference.pass_requests.pass1.reasoning_mode.value == "off"
    assert reference.pass_requests.pass2.reasoning_mode.value == "off"
    assert reference.pass_requests.pass1.structured_output_mode is None
    assert (
        reference.pass_requests.pass2.structured_output_mode
        is CognitionStructuredOutputMode.NATIVE
    )

    escalation = current.conditions[PASS2_REASONING_ESCALATION_ROLE]
    assert escalation.pass_requests.pass1.structured_output_mode is None
    assert (
        escalation.pass_requests.pass2.structured_output_mode
        is CognitionStructuredOutputMode.NATIVE
    )


def test_current_format_v2_loader_accepts_explicit_structured_output_identity(
    tmp_path: Path,
) -> None:
    raw = json.loads(
        (_ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH).read_text(encoding="utf-8")
    )
    raw["capacity_evidence_id"] = None
    for condition in raw["conditions"].values():
        condition["pass_requests"]["pass1"]["structured_output_mode"] = None
        condition["pass_requests"]["pass2"]["structured_output_mode"] = "native"
    path = tmp_path / "native-reference.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    loaded = load_vllm_screening_plan(path)

    assert loaded.capacity_evidence_id is None
    for condition in loaded.conditions.values():
        assert condition.pass_requests.pass1.structured_output_mode is None
        assert (
            condition.pass_requests.pass2.structured_output_mode
            is CognitionStructuredOutputMode.NATIVE
        )


def test_current_semantic_plan_rejects_reference_role_semantic_drift(
    tmp_path: Path,
) -> None:
    raw = json.loads(
        (_ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH).read_text(encoding="utf-8")
    )
    pass2 = raw["conditions"][REFERENCE_BASELINE_ROLE]["pass_requests"]["pass2"]
    pass2["reasoning_mode"] = "bounded"
    pass2["reasoning_budget"] = 16
    path = tmp_path / "bad-reference.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ActualModelVLLMHostError, match=REFERENCE_BASELINE_ROLE):
        load_vllm_screening_plan(path)


def test_current_semantic_plan_rejects_reference_pass2_non_native_transport(
    tmp_path: Path,
) -> None:
    raw = json.loads(
        (_ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH).read_text(encoding="utf-8")
    )
    raw["conditions"][REFERENCE_BASELINE_ROLE]["pass_requests"]["pass2"][
        "structured_output_mode"
    ] = "plain"
    path = tmp_path / "bad-reference-transport.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ActualModelVLLMHostError, match=REFERENCE_BASELINE_ROLE):
        load_vllm_screening_plan(path)


def test_current_semantic_plan_rejects_pass1_structured_output_transport(
    tmp_path: Path,
) -> None:
    raw = json.loads(
        (_ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH).read_text(encoding="utf-8")
    )
    raw["conditions"][REFERENCE_BASELINE_ROLE]["pass_requests"]["pass1"][
        "structured_output_mode"
    ] = "native"
    path = tmp_path / "bad-pass1-transport.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ActualModelVLLMHostError, match=REFERENCE_BASELINE_ROLE):
        load_vllm_screening_plan(path)


def test_current_semantic_plan_rejects_escalation_transport_drift(
    tmp_path: Path,
) -> None:
    raw = json.loads(
        (_ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH).read_text(encoding="utf-8")
    )
    raw["conditions"][PASS2_REASONING_ESCALATION_ROLE]["pass_requests"]["pass2"][
        "structured_output_mode"
    ] = "plain"
    path = tmp_path / "bad-escalation-transport.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(
        ActualModelVLLMHostError,
        match=PASS2_REASONING_ESCALATION_ROLE,
    ):
        load_vllm_screening_plan(path)


def test_current_semantic_plan_rejects_escalation_role_without_reasoning_escalation(
    tmp_path: Path,
) -> None:
    raw = json.loads(
        (_ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH).read_text(encoding="utf-8")
    )
    reference_pass2 = raw["conditions"][REFERENCE_BASELINE_ROLE]["pass_requests"][
        "pass2"
    ]
    raw["conditions"][PASS2_REASONING_ESCALATION_ROLE]["pass_requests"]["pass2"] = dict(
        reference_pass2
    )
    path = tmp_path / "bad-escalation.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(
        ActualModelVLLMHostError,
        match=PASS2_REASONING_ESCALATION_ROLE,
    ):
        load_vllm_screening_plan(path)


def test_current_stage_r_requires_fresh_capacity_for_current_transport_identity() -> None:
    current = load_vllm_screening_plan(_ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH)
    scenario_set = load_actual_model_scenario_set(_ROOT / CANONICAL_SCENARIO_SET_PATH)
    reference_key = screening_condition_key_for_role(current, REFERENCE_BASELINE_ROLE)
    required_coverage = _required_capacity_coverage(
        condition=current.conditions[reference_key],
        scenario_set=scenario_set,
        scenario_ids=current.scenario_ids,
    )

    assert current.capacity_evidence_id is None
    assert required_coverage


def test_stage_r_coverage_ledger_keeps_functional_acceptance_and_follow_up_explicit() -> None:
    ledger = (
        _ROOT / "docs" / "reference" / "actual-model-stage-r-coverage.md"
    ).read_text(encoding="utf-8")

    assert "Stage R is a **functional/product acceptance lane first**." in ledger
    assert "This is a Stage R0 functional-acceptance pilot" in ledger
    assert "minimizing its context window" in ledger
    for required in (
        "English",
        "mixed language",
        "JSON/control-like user text",
        "quoted prompt-like content",
        "relationship inference trap",
        "rapid next turn / pending extraction",
    ):
        assert required in ledger
