from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ActualModelScenario,
    ExplicitBudgetConfiguration,
    run_actual_model_scenario,
    stable_actual_model_run_id,
)
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime


class _ModelProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        source = cognitive_input.input.id
        return CognitiveOutput(
            response=self.response,
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
                    value="the evaluation fixture",
                    sources=(source,),
                    epistemic_role="user_assertion",
                ),
            ),
        )


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# Actual Model Evaluation Character\n\nBe grounded.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: actual-eval\n  name: Actual Eval\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _manifest(*, model_artifact: str, condition_id: str = "baseline") -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="a" * 40,
        character_fixture_id="fixture-persistent-character",
        character_fixture_revision="sha256:fixture-v1",
        provider_identity="local-openai-compatible",
        adapter_identity="relaylm.providers.openai_compatible.OpenAICompatibleProvider:v1",
        model_artifact=model_artifact,
        tokenizer_identity="tokenizer-artifact-v1",
        effective_context_window=32768,
        decoding_configuration=(("temperature", 0.0), ("top_p", 1.0)),
        seed=7,
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v1",
        condition_id=condition_id,
        budgets=ExplicitBudgetConfiguration(
            memory_max_chunks=2,
            memory_max_chars=512,
            event_max_events=3,
            event_max_chars=768,
        ),
        provider_capabilities=("state_candidates",),
    )


def _scenario() -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="stable_identity_foundation",
        family="response_persona_continuity",
        version="1",
        turns=("僕の名前はRin。これを覚えて。",),
    )


def test_manifest_requires_exact_identity_and_paired_explicit_budgets() -> None:
    with pytest.raises(ValueError, match="exact 40-character Git SHA"):
        _manifest(model_artifact="model-a").__class__(
            relaylm_commit="v1",
            character_fixture_id="fixture",
            character_fixture_revision="rev",
            provider_identity="provider",
            adapter_identity="adapter",
            model_artifact="model-a",
            tokenizer_identity="tokenizer",
            effective_context_window=4096,
            decoding_configuration=(),
            structured_output_schema_version="schema-v1",
            scenario_set_version="set-v1",
            condition_id="baseline",
        )

    with pytest.raises(ValueError, match="memory budget"):
        ExplicitBudgetConfiguration(memory_max_chunks=1)


def test_stable_run_id_changes_with_model_or_condition_not_fixture_mutation() -> None:
    scenario = _scenario()
    model_a = _manifest(model_artifact="org/model@sha256:111")
    same_model = _manifest(model_artifact="org/model@sha256:111")
    model_b = _manifest(model_artifact="org/model@sha256:222")
    pressure = _manifest(model_artifact="org/model@sha256:111", condition_id="pressure")

    assert stable_actual_model_run_id(manifest=model_a, scenario=scenario) == stable_actual_model_run_id(
        manifest=same_model, scenario=scenario
    )
    assert stable_actual_model_run_id(manifest=model_a, scenario=scenario) != stable_actual_model_run_id(
        manifest=model_b, scenario=scenario
    )
    assert stable_actual_model_run_id(manifest=model_a, scenario=scenario) != stable_actual_model_run_id(
        manifest=pressure, scenario=scenario
    )
    assert scenario.turns == ("僕の名前はRin。これを覚えて。",)


def test_real_turn_harness_separates_raw_proposals_from_deterministic_results(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    provider = _ModelProvider("了解。Rinとして記録するね。")
    continuity_runtime = ContinuityRuntime(
        context=ContinuityContext(max_items=4),
        lifetime_revisions=3,
    )

    evidence = asyncio.run(
        run_actual_model_scenario(
            character=character,
            provider=provider,
            manifest=_manifest(model_artifact="org/model@sha256:111"),
            scenario=_scenario(),
            continuity_runtime=continuity_runtime,
        )
    )

    assert provider.calls == 1
    assert len(evidence.turns) == 1
    turn = evidence.turns[0]
    assert turn.raw_model.response == "了解。Rinとして記録するね。"
    assert len(turn.raw_model.state_candidates) == 2
    assert len(turn.raw_model.continuity_candidates) == 1
    assert [item["status"] for item in turn.deterministic.state_decisions] == [
        "accepted",
        "rejected",
    ]
    assert turn.deterministic.state_decisions[1]["reason"] == "unknown_source"
    assert [item["key"] for item in turn.deterministic.resulting_state] == ["name"]
    assert [item["status"] for item in turn.deterministic.continuity_decisions] == [
        "accepted"
    ]
    assert turn.deterministic.resulting_continuity is not None
    assert turn.deterministic.resulting_continuity["items"][0]["key"] == "current_subject"
    assert turn.product_quality == ()

    serialized = json.loads(evidence.to_json())
    assert serialized["turns"][0]["raw_model"]["state_candidates"][1]["key"] == "unsupported"
    assert serialized["turns"][0]["deterministic_relay"]["state_decisions"][1]["status"] == "rejected"
    assert serialized["turns"][0]["product_quality"] == []


def test_same_semantic_scenario_runs_against_replaceable_model_provider(tmp_path: Path) -> None:
    scenario = _scenario()
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = _ModelProvider("model A response")
    second = _ModelProvider("model B response")

    first_evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(first_root),
            provider=first,
            manifest=_manifest(model_artifact="org/model-a@sha256:111"),
            scenario=scenario,
            continuity_runtime=ContinuityRuntime(
                context=ContinuityContext(max_items=4), lifetime_revisions=3
            ),
        )
    )
    second_evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(second_root),
            provider=second,
            manifest=_manifest(model_artifact="org/model-b@sha256:222"),
            scenario=scenario,
            continuity_runtime=ContinuityRuntime(
                context=ContinuityContext(max_items=4), lifetime_revisions=3
            ),
        )
    )

    assert first_evidence.scenario == second_evidence.scenario == scenario
    assert first_evidence.manifest.model_artifact != second_evidence.manifest.model_artifact
    assert first_evidence.turns[0].raw_model.response == "model A response"
    assert second_evidence.turns[0].raw_model.response == "model B response"
    assert first_evidence.run_id != second_evidence.run_id
