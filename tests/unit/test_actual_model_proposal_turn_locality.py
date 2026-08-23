from __future__ import annotations

from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ActualModelRunManifest,
    ActualModelScenario,
    ActualModelTurnEvidence,
    DeterministicRelayObservation,
    RawModelObservation,
)
from relaylm.actual_model_quality import (
    StateProposalLabel,
    TurnProposalLabels,
    evaluate_labeled_proposals,
)


def _manifest() -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="1f4a2aab163f26a83a774d56385f128ebfe82ef3",
        character_fixture_id="turn-locality-fixture",
        character_fixture_revision="sha256:fixture",
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="turn-locality-v1",
        condition_id="baseline",
        provider_capabilities=("state_candidates",),
    )


def test_delayed_proposal_cannot_satisfy_an_earlier_turn_label() -> None:
    deterministic = DeterministicRelayObservation(
        state_decisions=(),
        continuity_decisions=(),
        resulting_state=(),
        resulting_continuity=None,
    )
    evidence = ActualModelEvidence(
        run_id="amr-turn-locality",
        manifest=_manifest(),
        scenario=ActualModelScenario(
            scenario_id="turn-locality",
            family="state_candidate_quality",
            turns=("僕の名前はRin。", "今は新しい情報はない。"),
            version="1",
        ),
        turns=(
            ActualModelTurnEvidence(
                turn_index=1,
                input="僕の名前はRin。",
                raw_model=RawModelObservation(
                    response="了解。",
                    state_candidates=(),
                    continuity_candidates=(),
                ),
                deterministic=deterministic,
            ),
            ActualModelTurnEvidence(
                turn_index=2,
                input="今は新しい情報はない。",
                raw_model=RawModelObservation(
                    response="そのままにするね。",
                    state_candidates=(
                        {
                            "state_class": "user.identity",
                            "key": "name",
                            "op": "set",
                            "value": "Rin",
                        },
                    ),
                    continuity_candidates=(),
                ),
                deterministic=deterministic,
            ),
        ),
    )

    metrics = evaluate_labeled_proposals(
        evidence=evidence,
        labels=(
            TurnProposalLabels(
                turn_index=1,
                state=(
                    StateProposalLabel(
                        state_class="user.identity",
                        key="name",
                        op="set",
                        match_value=True,
                        value="Rin",
                    ),
                ),
            ),
            TurnProposalLabels(turn_index=2),
        ),
    )

    assert metrics.state.expected_count == 1
    assert metrics.state.observed_count == 1
    assert metrics.state.true_positive_count == 0
    assert metrics.state.false_negative_count == 1
    assert metrics.state.false_positive_count == 1
    assert metrics.state.precision == 0.0
    assert metrics.state.recall == 0.0
