from __future__ import annotations

from pathlib import Path

from relaylm.actual_model_fast_screening import reference_screening_condition_ids
from relaylm.actual_model_vllm_host import load_vllm_screening_plan


_ROOT = Path(__file__).parents[2]
_SCREENING_ROOT = _ROOT / "evaluation" / "actual_model" / "screenings"


def test_stage_r_reference_plan_is_separate_from_immutable_historical_plan() -> None:
    historical = load_vllm_screening_plan(
        _SCREENING_ROOT / "cogp5-vllm-screening-v1.json"
    )
    current = load_vllm_screening_plan(
        _SCREENING_ROOT / "stage-r0-vllm-reference-v1.json"
    )

    assert historical.screening_id == "cogp5-vllm-screening-v1"
    assert historical.effective_context_window == 1024
    assert historical.capacity_evidence_id is None
    assert current.screening_id == "stage-r0-vllm-reference-v1"
    assert current.target_id == "gemma-4-12b-it-qat-w4a16-google-vllm-v1"
    assert current.effective_context_window == 1616
    assert current.capacity_evidence_id is None
    assert current.scenario_ids == (
        "response-persona-correction-v1",
        "continuity-lifecycle-v1",
    )
    assert reference_screening_condition_ids(current) == ("B",)
    assert current.conditions["B"].cognition_execution.mode == "two_pass"
    assert current.conditions["B"].pass_requests.pass1.reasoning_mode.value == "off"
    assert current.conditions["B"].pass_requests.pass2.reasoning_mode.value == "off"


def test_stage_r_coverage_ledger_keeps_pilot_and_follow_up_explicit() -> None:
    ledger = (
        _ROOT / "docs" / "reference" / "actual-model-stage-r-coverage.md"
    ).read_text(encoding="utf-8")

    assert "This is a Stage R0 pilot, not complete Core 1.0 qualification." in ledger
    for required in (
        "English",
        "mixed language",
        "JSON/control-like user text",
        "quoted prompt-like content",
        "relationship inference trap",
        "rapid next turn / pending extraction",
    ):
        assert required in ledger
