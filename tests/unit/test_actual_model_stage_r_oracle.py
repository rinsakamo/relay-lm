from __future__ import annotations

from pathlib import Path

from relaylm.actual_model_quality import ProposalScoring
from relaylm.actual_model_scenarios import load_actual_model_scenario_set

_REPO_ROOT = Path(__file__).parents[2]
_CANDIDATE = (
    _REPO_ROOT / "evaluation" / "actual_model" / "scenario_sets" / "foundation-v3.json"
)
_CURRENT_STAGE_R = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "stage-r0-vllm-current-v1.json"
)


def test_foundation_v3_separates_oracle_concerns_and_scoring_domains() -> None:
    scenario_set = load_actual_model_scenario_set(_CANDIDATE)

    assert scenario_set.format_version == 2
    assert scenario_set.scenario_set_version == "actual-model-foundation-v3"
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


def test_oracle_candidate_is_not_silently_promoted_to_current_stage_r() -> None:
    text = _CURRENT_STAGE_R.read_text(encoding="utf-8")

    assert "stage-r0-vllm-reference-v2.json" in text
    assert "foundation-v3" not in text
