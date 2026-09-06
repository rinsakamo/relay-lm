from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.actual_model_stage_r_semantics import (
    CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH,
    StageRSemanticAuthorityError,
    load_current_stage_r_scenario_set,
    load_stage_r_semantic_authority,
)
from relaylm.cognition_execution import (
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)


_ROOT = Path(__file__).parents[2]


def _load():
    authority = load_stage_r_semantic_authority(
        _ROOT / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
    )
    scenario_set = load_current_stage_r_scenario_set(
        repo_root=_ROOT,
        authority=authority,
    )
    return authority, scenario_set


def test_current_stage_r_semantics_are_provider_neutral() -> None:
    authority, scenario_set = _load()

    assert authority.authority_id == "stage-r-current-v1"
    assert "vllm" not in authority.authority_id
    assert "vllm" not in authority.scenario_set_path
    assert authority.scenario_ids == (
        "response-transcript-fidelity-v1",
        "response-false-attribution-resistance-v1",
        "continuity-lifecycle-v1",
    )
    assert tuple(item.scenario.scenario_id for item in scenario_set.scenarios) == (
        "response-transcript-fidelity-v1",
        "response-false-attribution-resistance-v1",
        "continuity-lifecycle-v1",
    )
    assert authority.temperature == 0
    assert authority.top_p == 1
    assert authority.seed is None
    assert authority.execution_path == "buffered"
    assert authority.reasoning_preference == "off"
    assert authority.pass1_structured_output is None
    assert authority.pass2_structured_output == "native"


def test_current_stage_r_requests_record_actual_reasoning_realization() -> None:
    authority, _ = _load()

    explicit_off = authority.pass_requests(reasoning_mode=CognitionReasoningMode.OFF)
    assert explicit_off.pass1 is not None
    assert explicit_off.pass2 is not None
    assert explicit_off.pass1.reasoning_mode is CognitionReasoningMode.OFF
    assert explicit_off.pass2.reasoning_mode is CognitionReasoningMode.OFF
    assert explicit_off.pass1.structured_output_mode is None
    assert (
        explicit_off.pass2.structured_output_mode
        is CognitionStructuredOutputMode.NATIVE
    )

    omitted = authority.pass_requests(reasoning_mode=None)
    assert omitted.pass1 is not None
    assert omitted.pass2 is not None
    assert omitted.pass1.reasoning_mode is None
    assert omitted.pass2.reasoning_mode is None
    assert omitted.pass1.temperature == 0
    assert omitted.pass2.top_p == 1


def test_current_stage_r_semantics_reject_scenario_revision_drift(
    tmp_path: Path,
) -> None:
    raw = json.loads(
        (_ROOT / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH).read_text(
            encoding="utf-8"
        )
    )
    raw["scenario_set_revision"] = "sha256:" + "0" * 64
    authority_path = tmp_path / "authority.json"
    authority_path.write_text(json.dumps(raw), encoding="utf-8")
    authority = load_stage_r_semantic_authority(authority_path)

    with pytest.raises(
        StageRSemanticAuthorityError,
        match="scenario-set revision",
    ):
        load_current_stage_r_scenario_set(
            repo_root=_ROOT,
            authority=authority,
        )


def test_current_stage_r_semantics_reject_backend_specific_extra_field(
    tmp_path: Path,
) -> None:
    raw = json.loads(
        (_ROOT / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH).read_text(
            encoding="utf-8"
        )
    )
    raw["hardware_capability_source"] = "qualified_vllm_token_capacity_reference"
    authority_path = tmp_path / "authority.json"
    authority_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(StageRSemanticAuthorityError, match="unknown"):
        load_stage_r_semantic_authority(authority_path)
