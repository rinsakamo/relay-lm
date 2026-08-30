from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ActualModelScenario,
    ProductQualityObservation,
    run_actual_model_scenario,
)
from relaylm.actual_model_quality import (
    ContinuityProposalLabel,
    ProposalScoring,
    StateProposalLabel,
    TurnProposalLabels,
    TurnQualityRating,
    apply_product_quality_ratings,
    evaluate_labeled_proposals,
    required_quality_axes,
)
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime


class _QualityProvider:
    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        source = cognitive_input.input.id
        return CognitiveOutput(
            response="Rinとして自然に返す。",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.identity",
                    key="name",
                    value="Rin",
                    sources=(source,),
                ),
                StateCandidate.set(
                    state_class="user.fact",
                    key="unsupported",
                    value="invented",
                    sources=("missing-event",),
                ),
            ),
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="referent",
                    key="current_subject",
                    value="青い箱",
                    sources=(source,),
                    epistemic_role="user_assertion",
                ),
                ContinuityCandidate.set(
                    kind="unresolved",
                    key="extra_question",
                    value="不要な問い",
                    sources=(source,),
                    epistemic_role="user_assertion",
                ),
            ),
        )


def _character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Quality Fixture\n\nBe grounded.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: quality-fixture\n  name: Quality Fixture\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _manifest() -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="14a7beacb9c2733b14a16a419f2e6bc02608d683",
        character_fixture_id="quality-fixture",
        character_fixture_revision="sha256:fixture-v1",
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="quality-foundation-v1",
        condition_id="baseline",
        provider_capabilities=("state_candidates", "continuity_candidates"),
    )


def _scenario(*, family: str = "state_candidate_quality") -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="quality-fixture",
        family=family,  # type: ignore[arg-type]
        version="1",
        turns=("僕の名前はRin。青い箱の話を続けよう。",),
    )


def _evidence(tmp_path: Path, *, family: str = "state_candidate_quality"):
    return asyncio.run(
        run_actual_model_scenario(
            character=_character(tmp_path),
            provider=_QualityProvider(),
            manifest=_manifest(),
            scenario=_scenario(family=family),
            continuity_runtime=ContinuityRuntime(
                context=ContinuityContext(max_items=4),
                lifetime_revisions=3,
            ),
        )
    )


def test_quality_rubric_axes_are_bounded_by_scenario_family() -> None:
    assert required_quality_axes("response_persona_continuity") == (
        "response_coherence",
        "persona_continuity",
        "correctness",
        "unsupported_recall",
    )
    assert required_quality_axes("state_candidate_quality") == (
        "response_coherence",
        "state_proposal_quality",
    )
    with pytest.raises(ValueError, match="unsupported actual-model scenario family"):
        required_quality_axes("future-unfrozen-family")


def test_product_quality_ratings_attach_without_rewriting_runtime_evidence(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    original_turn = evidence.turns[0]
    rated = apply_product_quality_ratings(
        evidence=evidence,
        ratings=(
            TurnQualityRating(
                turn_index=1,
                observations=(
                    ProductQualityObservation(
                        axis="state_proposal_quality",
                        outcome="fail",
                        note="One unsupported raw proposal was emitted.",
                    ),
                    ProductQualityObservation(
                        axis="response_coherence",
                        outcome="pass",
                    ),
                ),
            ),
        ),
    )

    rated_turn = rated.turns[0]
    assert rated_turn.raw_model == original_turn.raw_model
    assert rated_turn.deterministic == original_turn.deterministic
    assert [item.axis for item in rated_turn.product_quality] == [
        "response_coherence",
        "state_proposal_quality",
    ]
    assert [item.outcome for item in rated_turn.product_quality] == ["pass", "fail"]

    with pytest.raises(ValueError, match="must rate exactly these axes"):
        apply_product_quality_ratings(
            evidence=evidence,
            ratings=(
                TurnQualityRating(
                    turn_index=1,
                    observations=(
                        ProductQualityObservation(
                            axis="response_coherence",
                            outcome="pass",
                        ),
                    ),
                ),
            ),
        )


def test_product_quality_ratings_require_exact_turn_coverage(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    with pytest.raises(ValueError, match="cover every evidence turn"):
        apply_product_quality_ratings(evidence=evidence, ratings=())

    duplicate = TurnQualityRating(
        turn_index=1,
        observations=(
            ProductQualityObservation(axis="response_coherence", outcome="pass"),
            ProductQualityObservation(axis="state_proposal_quality", outcome="pass"),
        ),
    )
    with pytest.raises(ValueError, match="duplicate turn_index"):
        apply_product_quality_ratings(evidence=evidence, ratings=(duplicate, duplicate))


def test_labeled_proposal_metrics_measure_raw_precision_recall(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    metrics = evaluate_labeled_proposals(
        evidence=evidence,
        scoring=ProposalScoring(),
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
                continuity=(
                    ContinuityProposalLabel(
                        kind="referent",
                        key="current_subject",
                        op="set",
                        match_value=True,
                        value="青い箱",
                    ),
                ),
            ),
        ),
    )

    assert metrics.state.expected_count == 1
    assert metrics.state.observed_count == 2
    assert metrics.state.true_positive_count == 1
    assert metrics.state.false_positive_count == 1
    assert metrics.state.false_negative_count == 0
    assert metrics.state.precision == 0.5
    assert metrics.state.recall == 1.0

    assert metrics.continuity.expected_count == 1
    assert metrics.continuity.observed_count == 2
    assert metrics.continuity.true_positive_count == 1
    assert metrics.continuity.false_positive_count == 1
    assert metrics.continuity.false_negative_count == 0
    assert metrics.continuity.precision == 0.5
    assert metrics.continuity.recall == 1.0


def test_labeled_metrics_keep_missing_required_and_unnecessary_proposals_distinct(
    tmp_path: Path,
) -> None:
    evidence = _evidence(tmp_path)
    metrics = evaluate_labeled_proposals(
        evidence=evidence,
        scoring=ProposalScoring(),
        labels=(
            TurnProposalLabels(
                turn_index=1,
                state=(
                    StateProposalLabel(
                        state_class="user.preference",
                        key="preferred_beverage",
                        op="set",
                    ),
                ),
                continuity=(),
            ),
        ),
    )

    assert metrics.state.true_positive_count == 0
    assert metrics.state.false_negative_count == 1
    assert metrics.state.false_positive_count == 2
    assert metrics.state.precision == 0.0
    assert metrics.state.recall == 0.0
    assert metrics.continuity.expected_count == 0
    assert metrics.continuity.false_positive_count == 2
    assert metrics.continuity.precision == 0.0
    assert metrics.continuity.recall is None
