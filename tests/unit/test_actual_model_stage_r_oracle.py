from __future__ import annotations

import json
from pathlib import Path

from relaylm.actual_model_quality import ProposalScoring
from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.actual_model_vllm_host import load_vllm_screening_plan

_REPO_ROOT = Path(__file__).parents[2]
_V3_SCENARIO_SET = (
    _REPO_ROOT / "evaluation" / "actual_model" / "scenario_sets" / "foundation-v3.json"
)
_V3_TEMPLATE = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "stage-r0-vllm-reference-v3.json"
)
_HISTORICAL_V2_TEMPLATE = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "stage-r0-vllm-reference-v2.json"
)
_CURRENT_STAGE_R = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "stage-r0-vllm-current-v1.json"
)


def test_foundation_v3_separates_oracle_concerns_and_scoring_domains() -> None:
    scenario_set = load_actual_model_scenario_set(_V3_SCENARIO_SET)

    assert scenario_set.format_version == 2
    assert scenario_set.scenario_set_version == "actual-model-foundation-v3"
    assert scenario_set.revision == (
        "sha256:ad9e1940f9c6c8ae77ef71271ca1fad98a3b0b8b36dda9da6ea69cdf12846cd6"
    )
    assert tuple(item.scenario.scenario_id for item in scenario_set.scenarios) == (
        "response-transcript-fidelity-v1",
        "response-false-attribution-resistance-v1",
        "continuity-lifecycle-v1",
    )

    transcript = scenario_set.scenario("response-transcript-fidelity-v1")
    assert transcript.required_provider_capabilities == ("state_candidates",)
    assert transcript.effective_proposal_scoring == ProposalScoring(
        state="scored",
        continuity="unscored",
    )
    assert "勝手" not in transcript.scenario.turns[-1]
    assert "まだ話していない" in transcript.scenario.turns[-1]

    false_attribution = scenario_set.scenario(
        "response-false-attribution-resistance-v1"
    )
    assert false_attribution.required_provider_capabilities == ()
    assert false_attribution.effective_proposal_scoring == ProposalScoring(
        state="unscored",
        continuity="unscored",
    )
    assert "ミナ" in false_attribution.scenario.turns[-1]

    continuity = scenario_set.scenario("continuity-lifecycle-v1")
    assert continuity.required_provider_capabilities == ("continuity_candidates",)
    assert continuity.effective_proposal_scoring == ProposalScoring(
        state="unscored",
        continuity="scored",
    )


def test_foundation_v3_is_current_stage_r_single_source_identity() -> None:
    current = json.loads(_CURRENT_STAGE_R.read_text(encoding="utf-8"))
    assert current["execution_template_path"] == (
        "evaluation/actual_model/screenings/stage-r0-vllm-reference-v3.json"
    )

    plan = load_vllm_screening_plan(_V3_TEMPLATE)
    assert plan.screening_id == "stage-r0-vllm-reference-v3"
    assert plan.scenario_set_path == (
        "evaluation/actual_model/scenario_sets/foundation-v3.json"
    )
    assert plan.scenario_set_revision == (
        "sha256:ad9e1940f9c6c8ae77ef71271ca1fad98a3b0b8b36dda9da6ea69cdf12846cd6"
    )
    assert plan.scenario_ids == (
        "response-transcript-fidelity-v1",
        "response-false-attribution-resistance-v1",
        "continuity-lifecycle-v1",
    )
    assert _REPO_ROOT / plan.scenario_set_path == _V3_SCENARIO_SET


def test_historical_v2_template_remains_immutable_legacy_identity() -> None:
    raw = json.loads(_HISTORICAL_V2_TEMPLATE.read_text(encoding="utf-8"))

    assert raw["screening_id"] == "stage-r0-vllm-reference-v2"
    assert "scenario_set_path" not in raw
    assert "scenario_set_revision" not in raw
    assert raw["scenario_ids"] == [
        "response-persona-correction-v1",
        "continuity-lifecycle-v1",
    ]
