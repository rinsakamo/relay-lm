from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ActualModelRunManifest,
    ActualModelScenario,
    ActualModelTurnEvidence,
    DeterministicRelayObservation,
    RawModelObservation,
)
from relaylm.actual_model_quality import (
    ProposalScoring,
    TurnProposalLabels,
    evaluate_labeled_proposals,
)
from relaylm.actual_model_scenarios import (
    ActualModelScenarioSetError,
    load_actual_model_scenario_set,
)

_REPO_ROOT = Path(__file__).parents[2]
_LEGACY_SCENARIO_SET = (
    _REPO_ROOT / "evaluation" / "actual_model" / "scenario_sets" / "foundation-v2.json"
)


def _evidence() -> ActualModelEvidence:
    candidate = {
        "kind": "referent",
        "key": "blue_notebook",
        "op": "set",
        "value": "the blue notebook",
        "sources": ["evt-user-1"],
        "epistemic_role": "user_assertion",
    }
    return ActualModelEvidence(
        run_id="amr-oracle-scoring",
        manifest=ActualModelRunManifest(
            relaylm_commit="1fea5996dcd89d0858cf89f6ae7da595e81932a2",
            character_fixture_id="actual-model-foundation-v1",
            character_fixture_revision="sha256:fixture",
            provider_identity="test-provider",
            adapter_identity="test-adapter",
            model_artifact="test/model",
            tokenizer_identity="test/tokenizer",
            effective_context_window=4096,
            decoding_configuration=(("temperature", 0.0),),
            structured_output_schema_version="relaylm-cognitive-output-v1",
            scenario_set_version="oracle-scoring-v1",
            condition_id="baseline",
            provider_capabilities=("state_candidates", "continuity_candidates"),
        ),
        scenario=ActualModelScenario(
            scenario_id="oracle-scoring",
            family="response_persona_continuity",
            version="1",
            turns=("青いノートの話を続けたい。",),
        ),
        turns=(
            ActualModelTurnEvidence(
                turn_index=1,
                input="青いノートの話を続けたい。",
                raw_model=RawModelObservation(
                    response="分かった。",
                    state_candidates=(),
                    continuity_candidates=(candidate,),
                ),
                deterministic=DeterministicRelayObservation(
                    state_decisions=(),
                    continuity_decisions=(
                        {
                            "candidate": candidate,
                            "status": "accepted",
                            "action": "admit",
                            "reason": None,
                        },
                    ),
                    resulting_state=(),
                    resulting_continuity=None,
                ),
            ),
        ),
    )


def test_unscored_channel_preserves_raw_observation_without_false_positive() -> None:
    evidence = _evidence()
    metrics = evaluate_labeled_proposals(
        evidence=evidence,
        labels=(TurnProposalLabels(turn_index=1, state=(), continuity=()),),
        scoring=ProposalScoring(state="scored", continuity="unscored"),
    )

    assert evidence.turns[0].raw_model.continuity_candidates[0]["key"] == "blue_notebook"
    assert metrics.state.scored is True
    assert metrics.continuity.scored is False
    assert metrics.continuity.expected_count == 0
    assert metrics.continuity.observed_count == 0
    assert metrics.continuity.false_positive_count == 0
    assert metrics.continuity.false_negative_count == 0
    assert metrics.continuity.precision is None
    assert metrics.continuity.recall is None


def test_scored_empty_channel_still_means_zero_expected() -> None:
    metrics = evaluate_labeled_proposals(
        evidence=_evidence(),
        labels=(TurnProposalLabels(turn_index=1, state=(), continuity=()),),
        scoring=ProposalScoring(state="scored", continuity="scored"),
    )

    assert metrics.continuity.scored is True
    assert metrics.continuity.expected_count == 0
    assert metrics.continuity.observed_count == 1
    assert metrics.continuity.false_positive_count == 1
    assert metrics.continuity.precision == 0.0


def test_legacy_foundation_v2_remains_implicit_scored_scored() -> None:
    legacy = load_actual_model_scenario_set(_LEGACY_SCENARIO_SET)
    response = legacy.scenario("response-persona-correction-v1")

    assert legacy.format_version == 1
    assert response.proposal_scoring is None
    assert response.effective_proposal_scoring == ProposalScoring(
        state="scored",
        continuity="scored",
    )
    assert "proposal_scoring" not in response.to_mapping()


def test_format_v2_requires_explicit_scoring_and_rejects_labels_on_unscored_channel(
    tmp_path: Path,
) -> None:
    base = {
        "format_version": 2,
        "scenario_set_version": "oracle-v2",
        "quality_rubric_version": "actual-model-quality-v1",
        "character_fixture_id": "actual-model-foundation-v1",
        "scenarios": [
            {
                "format_version": 1,
                "id": "neutral-history-fidelity-v1",
                "family": "response_persona_continuity",
                "version": "1",
                "turns": ["履歴にない内容は追加しないで。"],
                "required_provider_capabilities": ["state_candidates"],
                "restart_after_turn_count": None,
                "proposal_scoring": {
                    "state": "scored",
                    "continuity": "unscored",
                },
                "proposal_labels": [
                    {"turn_index": 1, "state": [], "continuity": []},
                ],
            },
        ],
    }
    path = tmp_path / "scenario-set.json"
    path.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")

    loaded = load_actual_model_scenario_set(path)
    definition = loaded.scenario("neutral-history-fidelity-v1")
    assert loaded.format_version == 2
    assert definition.effective_proposal_scoring == ProposalScoring(
        state="scored",
        continuity="unscored",
    )

    missing = json.loads(json.dumps(base))
    del missing["scenarios"][0]["proposal_scoring"]
    path.write_text(json.dumps(missing, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ActualModelScenarioSetError, match="proposal_scoring"):
        load_actual_model_scenario_set(path)

    mislabeled = json.loads(json.dumps(base))
    mislabeled["scenarios"][0]["proposal_labels"][0]["continuity"] = [
        {"kind": "referent", "key": "x", "op": "set"}
    ]
    path.write_text(json.dumps(mislabeled, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ActualModelScenarioSetError, match="unscored continuity"):
        load_actual_model_scenario_set(path)
