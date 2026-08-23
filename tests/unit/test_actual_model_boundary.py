from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_boundary import (
    ActualModelBoundaryArtifactError,
    evaluate_actual_model_deterministic_boundary,
    load_actual_model_deterministic_boundary_mapping,
    write_actual_model_deterministic_boundary_verdict,
)
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ExplicitContinuityRuntimeConfiguration,
)
from relaylm.actual_model_execution import run_actual_model_scenario_definition
from relaylm.actual_model_restart import RestartBoundaryObservation
from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.state import StateCandidate

_REPO_ROOT = Path(__file__).parents[2]
_SCENARIO_SET_PATH = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "scenario_sets"
    / "foundation-v1.json"
)
_FIXTURE_ROOT = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "characters"
    / "foundation-v1"
)


class _Provider:
    def __init__(self, *, propose_state: bool = False) -> None:
        self.propose_state = propose_state
        self.calls = 0

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        candidates = ()
        if self.propose_state:
            candidates = (
                StateCandidate.set(
                    state_class="user.identity",
                    key="name",
                    value=f"candidate-{self.calls}",
                    sources=(cognitive_input.input.id,),
                ),
            )
        return CognitiveOutput(
            response=f"response-{self.calls}",
            state_candidates=candidates,
        )


def _manifest(*, restart: bool = False) -> ActualModelRunManifest:
    capabilities = ("state_candidates",)
    continuity = None
    if restart:
        capabilities = ("state_candidates", "continuity_candidates")
        continuity = ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=3,
        )
    return ActualModelRunManifest(
        relaylm_commit="41f4877e85095fff453154a311c0d4a2da0cec41",
        character_fixture_id="actual-model-foundation-v1",
        character_fixture_revision=character_fixture_revision(_FIXTURE_ROOT),
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v1",
        condition_id="baseline",
        continuity_runtime=continuity,
        provider_capabilities=capabilities,
    )


async def _run(
    *,
    workspace_root: Path,
    scenario_id: str,
    restart: bool = False,
    propose_state: bool = False,
):
    return await run_actual_model_scenario_definition(
        scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
        scenario_id=scenario_id,
        fixture_root=_FIXTURE_ROOT,
        workspace_root=workspace_root,
        provider=_Provider(propose_state=propose_state),
        manifest=_manifest(restart=restart),
    )


def test_ordinary_boundary_verdict_is_separate_pass_fail_evidence(tmp_path: Path) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "run",
            scenario_id="response-persona-correction-v1",
            propose_state=True,
        )
    )

    verdict = evaluate_actual_model_deterministic_boundary(result=result)

    assert verdict.verdict_id.startswith("amb-")
    assert verdict.execution_id == result.execution_id
    assert verdict.run_id == result.run_id
    assert verdict.scenario_set_revision == result.plan.scenario_set_revision
    assert verdict.outcome == "pass"
    assert tuple(check.invariant for check in verdict.checks) == (
        "ordinary.fixture_turn_alignment",
        "ordinary.state_proposal_decision_coverage",
        "ordinary.continuity_proposal_decision_coverage",
    )
    assert all(check.outcome == "pass" for check in verdict.checks)
    mapping = verdict.to_mapping()
    assert mapping["model_quality"] is None
    assert mapping["score"] is None


def test_boundary_verdict_detects_raw_to_decision_coverage_break_without_rescoring_model(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "run",
            scenario_id="response-persona-correction-v1",
            propose_state=True,
        )
    )
    evidence = result.evidence
    first = evidence.turns[0]
    broken_first = replace(
        first,
        deterministic=replace(first.deterministic, state_decisions=()),
    )
    broken = replace(
        result,
        evidence=replace(evidence, turns=(broken_first, *evidence.turns[1:])),
    )

    verdict = evaluate_actual_model_deterministic_boundary(result=broken)

    assert verdict.outcome == "fail"
    state_check = next(
        check
        for check in verdict.checks
        if check.invariant == "ordinary.state_proposal_decision_coverage"
    )
    assert state_check.outcome == "fail"
    assert state_check.detail == {"failed_turn_indexes": [1]}
    assert verdict.to_mapping()["model_quality"] is None


def test_restart_boundary_verdict_distinguishes_durable_and_non_durable_authority(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "restart-run",
            scenario_id="restart-durable-vs-temporary-v1",
            restart=True,
            propose_state=True,
        )
    )

    verdict = evaluate_actual_model_deterministic_boundary(result=result)

    assert verdict.outcome == "pass"
    by_name = {check.invariant: check for check in verdict.checks}
    assert by_name["restart.fixture_phase_alignment"].outcome == "pass"
    assert by_name["restart.durable_state_survives_boundary"].outcome == "pass"
    assert by_name["restart.durable_events_survive_boundary"].outcome == "pass"
    assert by_name["restart.process_local_continuity_resets"].outcome == "pass"
    assert by_name["before_restart.state_proposal_decision_coverage"].outcome == "pass"
    assert by_name["after_restart.state_proposal_decision_coverage"].outcome == "pass"


def test_restart_boundary_corruption_produces_boundary_fail_not_model_quality_fail(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "restart-run",
            scenario_id="restart-durable-vs-temporary-v1",
            restart=True,
            propose_state=True,
        )
    )
    evidence = result.evidence
    boundary = evidence.boundary
    broken_boundary = RestartBoundaryObservation(
        state_before_restart=boundary.state_before_restart,
        state_after_restart=(),
        event_ids_before_restart=boundary.event_ids_before_restart,
        event_ids_after_restart=(),
        continuity_before_restart=boundary.continuity_before_restart,
        continuity_after_restart={
            "max_items": 4,
            "revision": 1,
            "items": [{"unexpected": True}],
        },
    )
    broken = replace(result, evidence=replace(evidence, boundary=broken_boundary))

    verdict = evaluate_actual_model_deterministic_boundary(result=broken)
    by_name = {check.invariant: check for check in verdict.checks}

    assert verdict.outcome == "fail"
    assert by_name["restart.durable_state_survives_boundary"].outcome == "fail"
    assert by_name["restart.durable_events_survive_boundary"].outcome == "fail"
    assert by_name["restart.process_local_continuity_resets"].outcome == "fail"
    assert verdict.to_mapping()["model_quality"] is None


def test_boundary_verdict_sidecar_is_immutable_idempotent_and_loadable(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "run",
            scenario_id="response-persona-correction-v1",
        )
    )
    verdict = evaluate_actual_model_deterministic_boundary(result=result)
    artifact_root = tmp_path / "boundary-artifacts"

    first = write_actual_model_deterministic_boundary_verdict(
        verdict=verdict,
        artifact_root=artifact_root,
    )
    second = write_actual_model_deterministic_boundary_verdict(
        verdict=verdict,
        artifact_root=artifact_root,
    )
    loaded = load_actual_model_deterministic_boundary_mapping(first)

    assert first == second
    assert first.name == f"{verdict.verdict_id}.boundary.json"
    assert loaded["verdict_id"] == verdict.verdict_id
    assert loaded["execution_id"] == result.execution_id
    assert loaded["outcome"] == "pass"
    assert loaded["model_quality"] is None
    assert loaded["score"] is None


def test_boundary_writer_rejects_non_content_derived_verdict_id(tmp_path: Path) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "run",
            scenario_id="response-persona-correction-v1",
        )
    )
    verdict = evaluate_actual_model_deterministic_boundary(result=result)
    forged = replace(verdict, verdict_id="amb-" + "f" * 64)
    artifact_root = tmp_path / "boundary-artifacts"

    with pytest.raises(
        ActualModelBoundaryArtifactError,
        match="verdict_id does not match boundary evidence",
    ):
        write_actual_model_deterministic_boundary_verdict(
            verdict=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()
