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
    ContinuityProposalLabel,
    TurnProposalLabels,
    evaluate_labeled_proposals,
)


_FIXTURE_KEY = "check_box_contents"
_ACCEPTED_KEY = "examine_blue_box_contents"
_VALUE = "check the blue box contents"


def _manifest() -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="b32357c2263f974905a1ab31b299babf5463e834",
        character_fixture_id="continuity-key-scoring-fixture",
        character_fixture_revision="sha256:fixture-v1",
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="continuity-key-scoring-v1",
        condition_id="baseline",
        provider_capabilities=("continuity_candidates",),
    )


def _candidate(*, key: str, op: str) -> dict[str, object]:
    candidate: dict[str, object] = {
        "kind": "active_task",
        "key": key,
        "op": op,
        "sources": [f"evt-{op}"],
        "epistemic_role": "user_assertion",
    }
    if op == "set":
        candidate["value"] = _VALUE
    else:
        candidate["value"] = None
    return candidate


def _turn(
    *,
    turn_index: int,
    candidate: dict[str, object],
    status: str,
    action: str | None,
    reason: str | None = None,
) -> ActualModelTurnEvidence:
    return ActualModelTurnEvidence(
        turn_index=turn_index,
        input=f"turn {turn_index}",
        raw_model=RawModelObservation(
            response="ok",
            state_candidates=(),
            continuity_candidates=(candidate,),
        ),
        deterministic=DeterministicRelayObservation(
            state_decisions=(),
            continuity_decisions=(
                {
                    "candidate": candidate,
                    "status": status,
                    "action": action,
                    "reason": reason,
                },
            ),
            resulting_state=(),
            resulting_continuity=None,
        ),
    )


def _evidence(*, resolve_key: str) -> ActualModelEvidence:
    set_candidate = _candidate(key=_ACCEPTED_KEY, op="set")
    resolve_candidate = _candidate(key=resolve_key, op="resolve")
    resolve_matches = resolve_key == _ACCEPTED_KEY
    return ActualModelEvidence(
        run_id="amr-continuity-key-scoring",
        manifest=_manifest(),
        scenario=ActualModelScenario(
            scenario_id="continuity-key-scoring",
            family="continuity_proposal_quality",
            version="1",
            turns=("start checking", "finish checking"),
        ),
        turns=(
            _turn(
                turn_index=1,
                candidate=set_candidate,
                status="accepted",
                action="admit",
            ),
            _turn(
                turn_index=2,
                candidate=resolve_candidate,
                status="accepted" if resolve_matches else "noop",
                action="resolve" if resolve_matches else None,
                reason=None if resolve_matches else "not_found",
            ),
        ),
    )


def _labels() -> tuple[TurnProposalLabels, ...]:
    return (
        TurnProposalLabels(
            turn_index=1,
            continuity=(
                ContinuityProposalLabel(
                    kind="active_task",
                    key=_FIXTURE_KEY,
                    op="set",
                    match_value=True,
                    value=_VALUE,
                ),
            ),
        ),
        TurnProposalLabels(
            turn_index=2,
            continuity=(
                ContinuityProposalLabel(
                    kind="active_task",
                    key=_FIXTURE_KEY,
                    op="resolve",
                ),
            ),
        ),
    )


def test_first_introduction_binds_reasonable_accepted_key_then_scores_strict_reuse() -> None:
    metrics = evaluate_labeled_proposals(
        evidence=_evidence(resolve_key=_ACCEPTED_KEY),
        labels=_labels(),
    )

    assert metrics.continuity.expected_count == 2
    assert metrics.continuity.observed_count == 2
    assert metrics.continuity.true_positive_count == 2
    assert metrics.continuity.false_positive_count == 0
    assert metrics.continuity.false_negative_count == 0
    assert metrics.continuity.precision == 1.0
    assert metrics.continuity.recall == 1.0


def test_later_lifecycle_transition_must_reuse_the_key_accepted_on_introduction() -> None:
    metrics = evaluate_labeled_proposals(
        evidence=_evidence(resolve_key="inspect_box_contents_invented_later"),
        labels=_labels(),
    )

    assert metrics.continuity.true_positive_count == 1
    assert metrics.continuity.false_positive_count == 1
    assert metrics.continuity.false_negative_count == 1
    assert metrics.continuity.precision == 0.5
    assert metrics.continuity.recall == 0.5
