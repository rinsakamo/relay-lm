from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_comparison import (
    run_actual_model_condition_comparison,
    stable_condition_comparison_id,
)
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ActualModelScenario,
    ExplicitBudgetConfiguration,
)
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory


class _ConditionProvider:
    def __init__(self, *, pressure: bool) -> None:
        self.pressure = pressure
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.inputs.append(cognitive_input)
        source = cognitive_input.input.id
        if not self.pressure:
            return CognitiveOutput(
                response="baseline response",
                state_candidates=(
                    StateCandidate.set(
                        state_class="user.identity",
                        key="name",
                        value="Rin",
                        sources=(source,),
                    ),
                ),
            )
        return CognitiveOutput(
            response="pressure response is shorter",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.identity",
                    key="name",
                    value="Rin",
                    sources=(source,),
                ),
                StateCandidate.set(
                    state_class="user.fact",
                    key="unsupported_detail",
                    value="invented",
                    sources=("missing-event",),
                ),
            ),
        )


def _make_fixture(root: Path) -> str:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Pressure Fixture\n\nBe grounded.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: pressure-fixture\n  name: Pressure Fixture\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character_fixture_revision(root)


def _manifest(
    *, revision: str, condition_id: str, budgets: ExplicitBudgetConfiguration
) -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="2081b53ad7ab9fbdbe068f839f39cee4c33dd0e1",
        character_fixture_id="pressure-fixture",
        character_fixture_revision=revision,
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        seed=17,
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="pressure-foundation-v1",
        condition_id=condition_id,
        budgets=budgets,
        provider_capabilities=("state_candidates",),
        replicate_id="0",
    )


def _condition_manifests(revision: str) -> tuple[ActualModelRunManifest, ActualModelRunManifest]:
    return (
        _manifest(
            revision=revision,
            condition_id="baseline",
            budgets=ExplicitBudgetConfiguration(
                memory_max_chunks=4,
                memory_max_chars=2048,
                event_max_events=4,
                event_max_chars=2048,
            ),
        ),
        _manifest(
            revision=revision,
            condition_id="pressure",
            budgets=ExplicitBudgetConfiguration(
                memory_max_chunks=1,
                memory_max_chars=128,
                event_max_events=1,
                event_max_chars=128,
            ),
        ),
    )


def _scenario() -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="same_fixture_under_pressure",
        family="cognitive_pressure_robustness",
        version="1",
        turns=("僕の名前はRin。",),
    )


def test_condition_pair_allows_only_condition_and_explicit_budget_drift(tmp_path: Path) -> None:
    revision = _make_fixture(tmp_path / "fixture")
    baseline, pressure = _condition_manifests(revision)
    scenario = _scenario()

    assert stable_condition_comparison_id(
        baseline_manifest=baseline,
        pressure_manifest=pressure,
        scenario=scenario,
    ).startswith("amc-")

    with pytest.raises(ValueError, match="condition_id"):
        stable_condition_comparison_id(
            baseline_manifest=baseline,
            pressure_manifest=replace(pressure, condition_id="baseline"),
            scenario=scenario,
        )
    with pytest.raises(ValueError, match="budget configurations"):
        stable_condition_comparison_id(
            baseline_manifest=baseline,
            pressure_manifest=replace(pressure, budgets=baseline.budgets),
            scenario=scenario,
        )
    with pytest.raises(ValueError, match="may differ only"):
        stable_condition_comparison_id(
            baseline_manifest=baseline,
            pressure_manifest=replace(pressure, model_artifact="test/model@sha256:DIFFERENT"),
            scenario=scenario,
        )


def test_comparison_runs_same_semantic_fixture_from_independent_workspaces(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    revision = _make_fixture(fixture)
    baseline_manifest, pressure_manifest = _condition_manifests(revision)
    baseline_provider = _ConditionProvider(pressure=False)
    pressure_provider = _ConditionProvider(pressure=True)
    scenario = _scenario()

    evidence = asyncio.run(
        run_actual_model_condition_comparison(
            fixture_root=fixture,
            workspace_root=tmp_path / "runs",
            baseline_provider=baseline_provider,
            pressure_provider=pressure_provider,
            baseline_manifest=baseline_manifest,
            pressure_manifest=pressure_manifest,
            scenario=scenario,
        )
    )

    assert evidence.scenario is scenario
    assert evidence.baseline.scenario == evidence.pressure.scenario == scenario
    assert len(baseline_provider.inputs) == len(pressure_provider.inputs) == 1
    assert baseline_provider.inputs[0].input.payload["content"] == (
        pressure_provider.inputs[0].input.payload["content"]
    )
    assert evidence.baseline.manifest.condition_id == "baseline"
    assert evidence.pressure.manifest.condition_id == "pressure"
    assert evidence.baseline.manifest.budgets != evidence.pressure.manifest.budgets

    assert evidence.baseline_summary.state_candidate_count == 1
    assert evidence.baseline_summary.rejected_state_candidate_count == 0
    assert evidence.pressure_summary.state_candidate_count == 2
    assert evidence.pressure_summary.rejected_state_candidate_count == 1
    assert evidence.pressure_minus_baseline.state_candidate_count == 1
    assert evidence.pressure_minus_baseline.rejected_state_candidate_count == 1
    assert evidence.to_mapping()["score"] is None

    assert character_fixture_revision(fixture) == revision
    assert [event.actor for event in CharacterDirectory(tmp_path / "runs" / "baseline").iter_events()] == [
        "user",
        "assistant",
    ]
    assert [event.actor for event in CharacterDirectory(tmp_path / "runs" / "pressure").iter_events()] == [
        "user",
        "assistant",
    ]


def test_comparison_rejects_non_pressure_scenario(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    revision = _make_fixture(fixture)
    baseline, pressure = _condition_manifests(revision)
    wrong_family = ActualModelScenario(
        scenario_id="wrong-family",
        family="state_candidate_quality",
        version="1",
        turns=("hello",),
    )

    with pytest.raises(ValueError, match="cognitive_pressure_robustness"):
        asyncio.run(
            run_actual_model_condition_comparison(
                fixture_root=fixture,
                workspace_root=tmp_path / "runs",
                baseline_provider=_ConditionProvider(pressure=False),
                pressure_provider=_ConditionProvider(pressure=True),
                baseline_manifest=baseline,
                pressure_manifest=pressure,
                scenario=wrong_family,
            )
        )
